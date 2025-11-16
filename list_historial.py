import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
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
        if not claims:
            return response(401, "Token inválido")
        params = event.get('queryStringParameters', {}) or {}
        table = dynamodb.Table(HISTORIAL_TABLE)
        scan = table.scan()
        historial = scan.get('Items', [])
        # Paginado simple
        page = int(params.get('page', 1))
        size = int(params.get('size', 10))
        start = (page - 1) * size
        end = start + size
        return response(200, historial[start:end])
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
