import json
import boto3
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

# Configuración robusta
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
USERS_TABLE = 't_users'  # Nombre fijo de la tabla
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret-key-2024')

def get_body(event):
    body = event.get('body', '{}')
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except Exception:
        return {}

def lambda_handler(event, context):
    try:
        body = get_body(event)
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return response(400, "Faltan campos obligatorios")
        
        table = dynamodb.Table(USERS_TABLE)
        
        # Buscar usuario
        user_response = table.get_item(Key={'email': email})
        user = user_response.get('Item')
        
        if not user:
            return response(404, "Usuario no encontrado")
            
        # Verificar contraseña
        if not bcrypt.checkpw(password.encode('utf-8'), user['contraseña_hash'].encode('utf-8')):
            return response(401, "Credenciales inválidas")
        
        # Generar token
        token = jwt.encode({
            'userId': user['tenant_id'],
            'email': email,
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(hours=48)
        }, JWT_SECRET, algorithm='HS256')
        
        return response(200, {'token': token})
        
    except Exception as e:
        print(f"Error en login_user: {str(e)}")
        return response(500, "Error interno del servidor")

def response(code, body):
    return {
        'statusCode': code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps({
            'success': code == 200, 
            'data': body if code == 200 else None, 
            'error': None if code == 200 else body
        })
    }
