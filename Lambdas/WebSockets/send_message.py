import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    body = json.loads(event.get('body', '{}'))
    
    # Enviar mensaje de vuelta al cliente
    await send_to_connection(connection_id, {
        'action': 'message',
        'message': 'Message received',
        'yourData': body
    })
    
    return {
        'statusCode': 200,
        'body': 'Message sent'
    }

async def send_to_connection(connection_id, message):
    gatewayapi = boto3.client('apigatewaymanagementapi',
        endpoint_url=f"https://{os.environ['DOMAIN_NAME']}/{os.environ['STAGE']}")
    
    await gatewayapi.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(message)
    )
