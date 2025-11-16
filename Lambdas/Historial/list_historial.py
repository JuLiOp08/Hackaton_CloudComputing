import json
import boto3
import jwt
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def verify_jwt_token(event):
    """Verifica el token JWT del header Authorization (opcional para este endpoint)"""
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
        # Verificación opcional de token (puedes hacerla obligatoria si quieres)
        user_data = verify_jwt_token(event)
        
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
