import json
import boto3
import uuid
import jwt
import os
from datetime import datetime

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
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        if 'exp' in decoded and datetime.fromtimestamp(decoded['exp']) < datetime.utcnow():
            return None
        return decoded
    except:
        return None

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
SNS_TOPIC = os.environ.get('SNS_TOPIC')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

VALID_TYPES = [
    "Fuga de agua", "Fuga de gas", "Piso mojado", "Daño de utilería", "Daño infraestructura", "Objeto perdido", "Emergencia médica", "Baño dañado", "Incendio"
]
VALID_PLACES = ["aula", "cocina", "biblioteca", "laboratorio", "comedor", "cancha", "baños"]

def lambda_handler(event, context):
    try:
        # Verificar token JWT
        user_data = verify_jwt_token(event)
        if not user_data:
            return response(401, "Token inválido o expirado")
            
        body = get_body(event)
        ubicacion = body.get('ubicacion')
        descripcion = body.get('descripcion')
        tipo = body.get('tipo')
        lugar = body.get('lugar')
        urgencia = body.get('urgencia')
        imagen = body.get('imagen')
        
        if not ubicacion or not descripcion or not tipo or not urgencia or not lugar:
            return response(400, "Faltan campos obligatorios")
            
        if tipo not in VALID_TYPES:
            return response(400, "Tipo de incidente inválido")

        if lugar not in VALID_PLACES:
            return response(400, "Lugar del incidente inválido")
            
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
        
        dynamodb.Table(INCIDENTES_TABLE).put_item(Item=incidente)
        evento_id = str(uuid.uuid4())
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': user_data['userId'],
            'estado': 'pendiente',
            'detalles': 'Incidente creado'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        dynamodb.Table(INCIDENTES_TABLE).put_item(Item=incidente)
        
        evento_id = str(uuid.uuid4())
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': user_data['userId'],
            'estado': 'pendiente',
            'detalles': 'Incidente creado'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        
        sns.publish(TopicArn=SNS_TOPIC, Message=json.dumps({
            'evento': 'incidente_creado',
            'codigo_incidente': codigo_incidente,
            'ubicacion': ubicacion,
            'tipo': tipo,
            'lugar': lugar,
            'urgencia': urgencia,
            'reportanteId': user_data['userId'],
            'fecha': now
        }))

        try:
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName='alerta-utec-dev-notifyHandler',
                InvocationType='Event',
                Payload=json.dumps({
                    'action': 'new_incident',
                    'incident': {
                        'codigo_incidente': codigo_incidente,
                        'ubicacion': ubicacion,
                        'tipo': tipo,
                        'lugar': lugar,
                        'urgencia': urgencia,
                        'reportanteId': user_data['userId'],
                        'fecha': now
                    },
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
        except Exception as e:
            print(f"Error invocando notificación: {str(e)}")
        
        return response(200, {
            'codigo_incidente': codigo_incidente,
            'estado': 'pendiente',
            'fecha': now
        })
        
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
