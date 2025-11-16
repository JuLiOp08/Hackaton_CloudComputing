import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    table = dynamodb.Table(CONNECTIONS_TABLE)
    table.delete_item(Key={'connectionId': connection_id})
    
    return {
        'statusCode': 200,
        'body': 'Disconnected'
    }
