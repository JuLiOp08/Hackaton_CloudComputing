import json
import boto3
import uuid
import jwt
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
SNS_TOPIC = os.environ.get('SNS_TOPIC')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')
VALID_STATES = ['pendiente', 'en_proceso', 'resuelto']

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

def lambda_handler(event, context):
    try:
        # Verificar token JWT
        user_data = verify_jwt_token(event)
        if not user_data:
            return response(401, "Token inválido o expirado")
            
        if user_data.get('role') not in ['autoridad', 'personal_admin']:
            return response(403, "No autorizado - se requiere rol de autoridad o personal admin")
            
        body = get_body(event)
        codigo_incidente = body.get('codigo_incidente')
        nuevo_estado = body.get('estado')
        
        if not codigo_incidente or nuevo_estado not in VALID_STATES:
            return response(400, "Datos inválidos")
            
        table = dynamodb.Table(INCIDENTES_TABLE)
        incidente = table.get_item(Key={'codigo_incidente': codigo_incidente}).get('Item')
        
        if not incidente:
            return response(404, "Incidente no encontrado")
            
        table.update_item(
            Key={'codigo_incidente': codigo_incidente},
            UpdateExpression='SET estado = :e',
            ExpressionAttributeValues={':e': nuevo_estado}
        )
        evento_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': user_data['userId'],
            'estado': nuevo_estado,
            'detalles': f'Estado actualizado a {nuevo_estado}'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        
        sns.publish(TopicArn=SNS_TOPIC, Message=json.dumps({
            'evento': 'estado_actualizado',
            'codigo_incidente': codigo_incidente,
            'nuevo_estado': nuevo_estado,
            'reportanteId': incidente['reportanteId'],
            'fecha': now
        }))
        
        try:
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName='alerta-utec-dev-notifyHandler',
                InvocationType='Event',
                Payload=json.dumps({
                    'action': 'status_changed',
                    'incident': {
                        'codigo_incidente': codigo_incidente,
                        'estado': nuevo_estado,
                        'reportanteId': incidente['reportanteId'],
                        'updatedBy': user_data['userId']
                    },
                    'timestamp': now
                })
            )
        except Exception as e:
            print(f"Error invocando notificación: {str(e)}")
            
        return response(200, {'codigo_incidente': codigo_incidente, 'estado': nuevo_estado})
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
