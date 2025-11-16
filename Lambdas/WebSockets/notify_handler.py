import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    """Lambda que recibe notificaciones y las envía via WebSocket"""
    print("🔔 Procesando notificación")
    
    try:
        message = event
        
        await broadcast_to_subscribers(message)
        
        return {'statusCode': 200, 'body': 'Notificación enviada'}
        
    except Exception as e:
        print(f"❌ Error en notificación: {str(e)}")
        return {'statusCode': 500, 'body': 'Error'}

async def broadcast_to_subscribers(message):
    table = dynamodb.Table(CONNECTIONS_TABLE)
    connections = table.scan().get('Items', [])
    
    api_id = os.environ.get('WEBSOCKET_API_ID')
    if not api_id:
        print("⚠️ WEBSOCKET_API_ID no configurado")
        return
    
    region = os.environ.get('AWS_REGION', 'us-east-1')
    stage = os.environ.get('STAGE', 'dev')
    endpoint_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}"
    
    gatewayapi = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
    
    for connection in connections:
        if connection.get('authenticated') and should_notify(connection, message):
            try:
                gatewayapi.post_to_connection(
                    ConnectionId=connection['connectionId'],
                    Data=json.dumps(message)
                )
            except Exception as e:
                if 'GoneException' in str(e):
                    table.delete_item(Key={'connectionId': connection['connectionId']})

def should_notify(connection, message):
    """Determinar si esta conexión debe recibir la notificación"""
    user_role = connection.get('role')
    action = message.get('action')
    
    if action == 'new_incident':
        return user_role in ['autoridad', 'personal']
    
    elif action == 'status_changed':
        return True
    
    return False
