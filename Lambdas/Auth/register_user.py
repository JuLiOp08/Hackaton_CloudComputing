import json
import boto3
import bcrypt
import uuid
import jwt
import os
from datetime import datetime, timedelta

# Configuración robusta
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
USERS_TABLE = 't_users'  # Nombre fijo de la tabla
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret-key-2024')
INSTITUTIONAL_DOMAIN = "utec.edu.pe"

def get_body(event):
    body = event.get('body', '{}')
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except Exception:
        return {}

def is_institutional_email(email):
    return email.endswith(f"@{INSTITUTIONAL_DOMAIN}")

def lambda_handler(event, context):
    try:
        # 1. Parsear el body
        body = get_body(event)
        email = body.get('email')
        password = body.get('password')
        nombre = body.get('nombre')
        role = body.get('role', 'estudiante')
        
        # 2. Validaciones básicas
        if not email or not password or not nombre:
            return response(400, "Faltan campos obligatorios")
        
        if role not in ['estudiante', 'autoridad']:
            return response(400, "Rol inválido")
            
        if not is_institutional_email(email):
            return response(400, "Email debe ser institucional (@utec.edu.pe)")
        
        # 3. Conectar a DynamoDB
        table = dynamodb.Table(USERS_TABLE)
        
        # 4. Verificar si el usuario ya existe
        existing = table.get_item(Key={'email': email})
        if 'Item' in existing:
            return response(409, "Usuario ya existe")
        
        # 5. Crear nuevo usuario
        user_id = str(uuid.uuid4())
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.utcnow().isoformat()
        
        user_item = {
            'email': email,
            'tenant_id': user_id,
            'nombre': nombre,
            'contraseña_hash': hashed_password,
            'role': role,
            'createdAt': now
        }
        
        # 6. Guardar en DynamoDB
        table.put_item(Item=user_item)
        
        # 7. Generar token JWT
        token = jwt.encode({
            'userId': user_id,
            'email': email,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=48)
        }, JWT_SECRET, algorithm='HS256')
        
        # 8. Respuesta exitosa
        return response(200, {'token': token})
        
    except Exception as e:
        # Log del error para debugging
        print(f"Error en register_user: {str(e)}")
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
