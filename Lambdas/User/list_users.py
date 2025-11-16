import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ.get('USERS_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')


def lambda_handler(event, context):
    try:
        auth = event["requestContext"]["authorizer"]

        if auth["context"]["role"] != "autoridad":
            return response(403, "No autorizado - se requiere rol de autorizacion")
            
        table = dynamodb.Table(USERS_TABLE)
        scan = table.scan()
        users = scan.get('Items', [])
        for u in users:
            u.pop('contraseña_hash', None)
        return response(200, users)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
