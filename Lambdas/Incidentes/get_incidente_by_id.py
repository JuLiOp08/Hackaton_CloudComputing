import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def lambda_handler(event, context):
    try:

        auth = event["requestContext"]["authorizer"]
        
        incidente_id = event['queryStringParameters'].get('codigo_incidente')
        
        if not incidente_id:
            return response(400, "Falta codigo_incidente")
            
        table = dynamodb.Table(INCIDENTES_TABLE)
        incidente = table.get_item(Key={'codigo_incidente': incidente_id}).get('Item')
        
        if not incidente:
            return response(404, "Incidente no encontrado")
        return response(200, incidente)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
