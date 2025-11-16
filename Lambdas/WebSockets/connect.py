import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    # Guardar conexión con metadata del usuario
    table.put_item(Item={
        'connectionId': connection_id,
        'connectedAt': event['requestContext']['connectedAt'],
        'domainName': event['requestContext']['domainName'],
        'stage': event['requestContext']['stage']
    })
    
    return {
        'statusCode': 200,
        'body': 'Connected'
    }
