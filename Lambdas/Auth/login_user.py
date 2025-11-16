import json
import boto3
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ.get('USERS_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return response(400, "Faltan campos obligatorios")
            
        table = dynamodb.Table(USERS_TABLE)
        user = table.get_item(Key={'email': email}).get('Item')
        
        if not user:
            return response(404, "Usuario no encontrado")
            
        if not bcrypt.checkpw(password.encode('utf-8'), user['contraseña_hash'].encode('utf-8')):
            return response(401, "Credenciales inválidas")
            
        token = jwt.encode(
            {
                'userId': user['tenant_id'],
                'email': email,
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(hours=48)
            },
            JWT_SECRET,
            algorithm='HS256'
        )
        
        return response(200, {'token': token})
        
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'success': code == 200, 
            'data': body if code == 200 else None, 
            'error': None if code == 200 else body
        })
    }
