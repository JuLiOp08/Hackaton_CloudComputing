import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    """
    Lambda que se ejecuta cuando un incidente se actualiza
    Se llama desde otras Lambdas via SNS o directamente
    """
    for record in event['Records']:
        if 'Sns' in record:
            # Mensaje desde SNS
            message = json.loads(record['Sns']['Message'])
        else:
            # Invocación directa
            message = json.loads(record['body'])
        
        # Notificar a todos los clientes conectados
        await broadcast_to_connections({
            'action': 'incident_updated',
            'incident': message
        })
    
    return {'statusCode': 200}

async def broadcast_to_connections(message):
    table = dynamodb.Table(CONNECTIONS_TABLE)
    gatewayapi = boto3.client('apigatewaymanagementapi',
        endpoint_url=f"https://{os.environ['DOMAIN_NAME']}/{os.environ['STAGE']}")
    
    # Obtener todas las conexiones activas
    connections = table.scan()['Items']
    
    for connection in connections:
        try:
            await gatewayapi.post_to_connection(
                ConnectionId=connection['connectionId'],
                Data=json.dumps(message)
            )
        except Exception as e:
            # Si la conexión ya no existe, eliminarla
            if e.response['Error']['Code'] == 'GoneException':
                table.delete_item(Key={'connectionId': connection['connectionId']})
