import json
import boto3
import uuid
import jwt
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def validate_token(event):
    auth = event['headers'].get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None
    token = auth.split(' ')[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except Exception:
        return None

def lambda_handler(event, context):
    try:
        claims = validate_token(event)
        if not claims or claims.get('role') != 'autoridad':
            return response(403, "No autorizado")
        body = json.loads(event.get('body', '{}'))
        codigo_incidente = body.get('codigo_incidente')
        responsableId = body.get('responsableId')
        if not codigo_incidente or not responsableId:
            return response(400, "Datos inválidos")
        table = dynamodb.Table(INCIDENTES_TABLE)
        incidente = table.get_item(Key={'codigo_incidente': codigo_incidente}).get('Item')
        if not incidente:
            return response(404, "Incidente no encontrado")
        table.update_item(
            Key={'codigo_incidente': codigo_incidente},
            UpdateExpression='SET responsableId = :r',
            ExpressionAttributeValues={':r': responsableId}
        )
        evento_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': claims['userId'],
            'estado': incidente['estado'],
            'detalles': f'Responsable asignado: {responsableId}'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        return response(200, {'codigo_incidente': codigo_incidente, 'responsableId': responsableId})
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
