import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

def handler(event, context):
    try:
        connection_id = event['requestContext']['connectionId']
        
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.delete_item(Key={'connectionId': connection_id})
        
        print(f"Conexión {connection_id} desconectada y limpiada")
        return {'statusCode': 200, 'body': 'Disconnected'}
        
    except Exception as e:
        print(f"Error en desconexión: {str(e)}")
        return {'statusCode': 500, 'body': 'Error interno'}
