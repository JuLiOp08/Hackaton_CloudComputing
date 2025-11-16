import json
import boto3
import jwt
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def handler(event, context):
    try:
        connection_id = event['requestContext']['connectionId']
        
        # 1. Obtener token de query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        token = query_params.get('token')
        
        if not token:
            print("Conexión rechazada: Token no proporcionado")
            return {'statusCode': 401, 'body': 'Token requerido'}
        
        # 2. Validar JWT manualmente
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = decoded['userId']
            user_email = decoded['email']
            user_role = decoded['role']
            
            # Verificar que el token no haya expirado
            if 'exp' in decoded and datetime.fromtimestamp(decoded['exp']) < datetime.utcnow():
                return {'statusCode': 401, 'body': 'Token expirado'}
                
        except jwt.ExpiredSignatureError:
            print("Token expirado")
            return {'statusCode': 401, 'body': 'Token expirado'}
        except jwt.InvalidTokenError as e:
            print(f"Token inválido: {str(e)}")
            return {'statusCode': 401, 'body': 'Token inválido'}
        
        # 3. Guardar conexión con información del usuario
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.put_item(Item={
            'connectionId': connection_id,
            'userId': user_id,
            'email': user_email,
            'role': user_role,
            'authenticated': True,
            'connectedAt': event['requestContext']['connectedAt'],
            'domainName': event['requestContext']['domainName'],
            'stage': event['requestContext']['stage']
        })
        
        print(f"Conexión autenticada: {user_email} ({user_role})")
        
        return {'statusCode': 200, 'body': 'Connected'}
        
    except Exception as e:
        print(f"Error en conexión: {str(e)}")
        return {'statusCode': 500, 'body': 'Error interno del servidor'}
