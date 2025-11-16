import json
import boto3
import jwt
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ.get('USERS_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

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
            
        if user_data.get('role') != 'autoridad':
            return response(403, "No autorizado - se requiere rol de autoridad")
        
        params = event.get('queryStringParameters') or {}
        user_id = params.get('userId')
        
        if not user_id:
            return response(400, "Falta userId")
            
        table = dynamodb.Table(USERS_TABLE)
        scan = table.scan(FilterExpression='tenant_id = :uid', ExpressionAttributeValues={':uid': user_id})
        items = scan.get('Items', [])
        if not items:
            return response(404, "Usuario no encontrado")
        user = items[0]
        if 'contraseña_hash' in user:
            del user['contraseña_hash']
        return response(200, user)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
