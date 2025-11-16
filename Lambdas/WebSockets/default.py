import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def send_to_connection(connection_id, message, event):
    """Enviar mensaje usando el event (solo funciona en connect/disconnect/default)"""
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    endpoint_url = f"https://{domain_name}/{stage}"
    
    try:
        gatewayapi = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
        gatewayapi.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        print(f"Mensaje enviado a {connection_id}: {message.get('action')}")
    except Exception as e:
        print(f"Error enviando a {connection_id}: {str(e)}")
        if 'GoneException' in str(e):
            table = dynamodb.Table(CONNECTIONS_TABLE)
            table.delete_item(Key={'connectionId': connection_id})

def handler(event, context):
    try:
        connection_id = event['requestContext']['connectionId']
        
        table = dynamodb.Table(CONNECTIONS_TABLE)
        connection = table.get_item(Key={'connectionId': connection_id}).get('Item')
        
        if not connection or not connection.get('authenticated'):
            print(f"Conexión no autenticada: {connection_id}")
            return {'statusCode': 401, 'body': 'No autenticado'}
        
        user_id = connection['userId']
        user_email = connection['email']
        user_role = connection['role']
        
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        print(f"Mensaje de {user_email} ({user_role}): {action}")
        
        if action == 'ping':
            send_to_connection(connection_id, {
                'action': 'pong',
                'timestamp': datetime.utcnow().isoformat(),
                'userRole': user_role,
                'message': 'Servidor funcionando correctamente'
            }, event)
            
        elif action == 'subscribe_dashboard':
            if user_role != 'autoridad':
                send_to_connection(connection_id, {
                    'action': 'error',
                    'message': 'Solo autoridades pueden acceder al panel'
                }, event)
                return {'statusCode': 403, 'body': 'No autorizado'}
            
            table.update_item(
                Key={'connectionId': connection_id},
                UpdateExpression='SET subscribedToDashboard = :val',
                ExpressionAttributeValues={':val': True}
            )
            
            send_to_connection(connection_id, {
                'action': 'subscribed',
                'type': 'dashboard',
                'message': 'Suscrito al panel administrativo',
                'timestamp': datetime.utcnow().isoformat()
            }, event)
            
        elif action == 'unsubscribe_dashboard':
            table.update_item(
                Key={'connectionId': connection_id},
                UpdateExpression='REMOVE subscribedToDashboard'
            )
            
            send_to_connection(connection_id, {
                'action': 'unsubscribed',
                'type': 'dashboard',
                'message': 'Desuscrito del panel administrativo'
            }, event)
            
        elif action == 'subscribe_incident':
            incident_id = body.get('incident_id')
            if not incident_id:
                send_to_connection(connection_id, {
                    'action': 'error',
                    'message': 'Falta incident_id'
                }, event)
                return {'statusCode': 400, 'body': 'incident_id requerido'}
            
            table.update_item(
                Key={'connectionId': connection_id},
                UpdateExpression='ADD subscribedIncidents :incident',
                ExpressionAttributeValues={':incident': {incident_id}}
            )
            
            send_to_connection(connection_id, {
                'action': 'subscribed',
                'type': 'incident',
                'incident_id': incident_id,
                'message': f'Suscrito a updates del incidente {incident_id}'
            }, event)
            
        elif action == 'unsubscribe_incident':
            incident_id = body.get('incident_id')
            if incident_id:
                table.update_item(
                    Key={'connectionId': connection_id},
                    UpdateExpression='DELETE subscribedIncidents :incident',
                    ExpressionAttributeValues={':incident': {incident_id}}
                )
                
            send_to_connection(connection_id, {
                'action': 'unsubscribed', 
                'type': 'incident',
                'incident_id': incident_id,
                'message': f'Desuscrito del incidente {incident_id}'
            }, event)
            
        elif action == 'get_connection_info':
            send_to_connection(connection_id, {
                'action': 'connection_info',
                'user': {
                    'id': user_id,
                    'email': user_email,
                    'role': user_role
                },
                'connectedSince': connection.get('connectedAt'),
                'subscribedToDashboard': connection.get('subscribedToDashboard', False),
                'subscribedIncidents': list(connection.get('subscribedIncidents', set()))
            }, event)             
        else:
            # Acción no reconocida
            send_to_connection(connection_id, {
                'action': 'error',
                'message': f'Acción no reconocida: {action}',
                'available_actions': [
                    'ping', 
                    'subscribe_dashboard', 
                    'unsubscribe_dashboard',
                    'subscribe_incident', 
                    'unsubscribe_incident',
                    'get_connection_info',
                    'typing'
                ]
            }, event)
            return {'statusCode': 400, 'body': 'Acción no reconocida'}
        
        return {'statusCode': 200, 'body': 'Message processed'}
        
    except Exception as e:
        print(f"❌ Error en default handler: {str(e)}")
        return {'statusCode': 500, 'body': 'Error interno del servidor'}
