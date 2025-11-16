import json
import boto3
import bcrypt
import uuid
import jwt
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
USERS_TABLE = os.environ.get('USERS_TABLE')
SNS_TOPIC = os.environ.get('SNS_TOPIC')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

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
        body = get_body(event)
        email = body.get('email')
        password = body.get('password')
        nombre = body.get('nombre')
        role = body.get('role', 'estudiante')
        
        if not email or not password or not nombre:
            return response(400, "Faltan campos obligatorios")
        if role not in ['estudiante', 'autoridad']:
            return response(400, "Rol inválido")
        if not is_institutional_email(email):
            return response(400, "Email debe ser institucional")
            
        table = dynamodb.Table(USERS_TABLE)
        existing = table.get_item(Key={'email': email})
        if 'Item' in existing:
            return response(409, "Usuario ya existe")
            
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.utcnow().isoformat()
        
        item = {
            'email': email,
            'tenant_id': user_id,
            'nombre': nombre,
            'contraseña_hash': hashed,
            'role': role,
            'createdAt': now
        }
        table.put_item(Item=item)
        
        # Generar token con expiración
        token = jwt.encode({
            'userId': user_id,
            'email': email, 
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=48)
        }, JWT_SECRET, algorithm='HS256')
        
        sns.publish(TopicArn=SNS_TOPIC, Message=json.dumps({
            'evento': 'usuario_registrado',
            'userId': user_id,
            'email': email,
            'nombre': nombre,
            'role': role,  # 👈 Cambié 'estudiante' por role variable
            'createdAt': now
        }))
        
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
