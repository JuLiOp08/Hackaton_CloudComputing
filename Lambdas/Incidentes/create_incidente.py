import json
import boto3
import uuid
import jwt
import os
from datetime import datetime, timedelta  # ← AGREGA timedelta

def get_body(event):
    body = event.get('body', '{}')
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except Exception:
        return {}

def verify_jwt_token(event):
    """Verifica el token JWT del header Authorization"""
    try:
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ')[1]
        JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')  # ← DEFINE JWT_SECRET AQUÍ
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # CORREGIR: datetime.utcnow() en lugar de datetime.fromtimestamp
        if 'exp' in decoded and datetime.utcnow() > datetime.fromtimestamp(decoded['exp']):
            return None
        return decoded
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
SNS_TOPIC = os.environ.get('SNS_TOPIC')

VALID_TYPES = [
    "Fuga de agua", "Fuga de gas", "Piso mojado", "Daño de utilería", 
    "Daño infraestructura", "Objeto perdido", "Emergencia médica", 
    "Baño dañado", "Incendio"
]
VALID_PLACES = ["aula", "cocina", "biblioteca", "laboratorio", "comedor", "cancha", "baños"]

def lambda_handler(event, context):
    # HEADERS CORS - AGREGA ESTO
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token',
        'Access-Control-Allow-Credentials': 'true'
    }
    
    # MANEJAR OPTIONS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        print("🔐 Verificando token...")
        # Verificar token JWT
        user_data = verify_jwt_token(event)
        if not user_data:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({
                    'success': False, 
                    'error': 'Token inválido o expirado'
                })
            }
            
        print("📦 Parseando body...")
        body = get_body(event)
        ubicacion = body.get('ubicacion')
        descripcion = body.get('descripcion')
        tipo = body.get('tipo')
        lugar = body.get('lugar')
        urgencia = body.get('urgencia')
        imagen = body.get('imagen')
        
        print(f"📝 Datos recibidos: ubicacion={ubicacion}, tipo={tipo}, lugar={lugar}")
        
        # Validaciones
        if not all([ubicacion, descripcion, tipo, urgencia, lugar]):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False, 
                    'error': 'Faltan campos obligatorios'
                })
            }
            
        if tipo not in VALID_TYPES:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False, 
                    'error': f'Tipo de incidente inválido. Válidos: {VALID_TYPES}'
                })
            }

        if lugar not in VALID_PLACES:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False, 
                    'error': f'Lugar del incidente inválido. Válidos: {VALID_PLACES}'
                })
            }
            
        # Crear incidente
        codigo_incidente = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        incidente = {
            'codigo_incidente': codigo_incidente,
            'ubicacion': ubicacion,
            'descripcion': descripcion,
            'estado': 'pendiente',
            'fecha': now,
            'tipo': tipo,
            'lugar': lugar,
            'urgencia': urgencia,
            'imagen': imagen if imagen else None,
            'reportanteId': user_data['userId'],
            'responsableId': None
        }
        
        print(f"💾 Guardando incidente: {codigo_incidente}")
        dynamodb.Table(INCIDENTES_TABLE).put_item(Item=incidente)
        
        # Crear historial (SOLO UNA VEZ)
        evento_id = str(uuid.uuid4())
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': user_data['userId'],  # ← CORREGIDO: user_data en lugar de auth
            'estado': 'pendiente',
            'detalles': 'Incidente creado'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        
        # Notificaciones (opcional, puedes comentar si falla)
        try:
            sns.publish(
                TopicArn=SNS_TOPIC, 
                Message=json.dumps({
                    'evento': 'incidente_creado',
                    'codigo_incidente': codigo_incidente,
                    'ubicacion': ubicacion,
                    'tipo': tipo,
                    'lugar': lugar,
                    'urgencia': urgencia,
                    'reportanteId': user_data['userId'],
                    'fecha': now
                })
            )
            
            # Notificación WebSocket
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName='alerta-utec-dev-notify_handler',  # ← CORREGIDO: notify_handler
                InvocationType='Event',
                Payload=json.dumps({
                    'action': 'new_incident',
                    'incident': incidente,
                    'timestamp': now
                })
            )
        except Exception as e:
            print(f"⚠️ Error en notificaciones: {str(e)}")
            # No fallar si las notificaciones fallan
        
        print(f"✅ Incidente creado exitosamente: {codigo_incidente}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'data': {
                    'codigo_incidente': codigo_incidente,
                    'estado': 'pendiente',
                    'fecha': now
                }
            })
        }
        
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': f'Error interno del servidor: {str(e)}'
            })
        }
