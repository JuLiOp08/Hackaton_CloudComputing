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
        
        query_params = event.get('queryStringParameters', {}) or {}
        token = query_params.get('token')
        
        if not token:
            print("Conexión rechazada: Token no proporcionado")
            return {'statusCode': 401, 'body': 'Token requerido'}
        
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = decoded['userId']
            user_email = decoded['email']
            user_role = decoded['role']
            
            if 'exp' in decoded and datetime.fromtimestamp(decoded['exp']) < datetime.utcnow():
                return {'statusCode': 401, 'body': 'Token expirado'}
                
        except jwt.ExpiredSignatureError:
            return {'statusCode': 401, 'body': 'Token expirado'}
        except jwt.InvalidTokenError as e:
            return {'statusCode': 401, 'body': 'Token inválido'}
        
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.put_item(Item={
            'connectionId': connection_id,
            'userId': user_id,
            'email': user_email,
            'role': user_role,
            'authenticated': True,
            'connectedAt': event['requestContext']['connectedAt'],
            'domainName': event['requestContext']['domainName'],
            'stage': event['requestContext']['stage'],
            'userRole': user_role,
            'isAuthority': user_role == 'autoridad'
        })
        
        print(f"Conexión WebSocket autenticada: {user_email} ({user_role})")
        
        return {'statusCode': 200, 'body': 'Connected'}
        
    except Exception as e:
        print(f"Error en conexión WebSocket: {str(e)}")
        return {'statusCode': 500, 'body': 'Error interno del servidor'}
