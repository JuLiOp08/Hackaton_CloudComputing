import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

def lambda_handler(event, context):
    try:
        
        incidente_id = event['queryStringParameters'].get('codigo_incidente')
        
        if not incidente_id:
            return response(400, "Falta codigo_incidente")
            
        table = dynamodb.Table(HISTORIAL_TABLE)
        scan = table.scan(FilterExpression='codigo_incidente = :cid', ExpressionAttributeValues={':cid': incidente_id})
        historial = scan.get('Items', [])
        
        return response(200, historial)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
