import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

VALID_STATES = ['pendiente', 'en_proceso']

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
        if not claims:
            return response(401, "Token inválido")
        table = dynamodb.Table(INCIDENTES_TABLE)
        scan = table.scan(
            FilterExpression='estado IN (:p, :e)',
            ExpressionAttributeValues={':p': 'pendiente', ':e': 'en_proceso'}
        )
        incidentes = scan.get('Items', [])
        return response(200, incidentes)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
