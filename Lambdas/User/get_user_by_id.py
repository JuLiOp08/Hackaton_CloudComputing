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

        if auth["context"]["role"] != "autoridad" or auth["context"]["role"] != personal_admin:
            return response(403, "No autorizado - se requiere rol de autorizacion")
        
        params = event.get('queryStringParameters') or {}
        user_id = params.get('userId')
        
        if not user_id:
            return response(400, "Falta userId")
            
        table = dynamodb.Table(USERS_TABLE)
        scan = table.scan(FilterExpression='tenant_id = :uid', ExpressionAttributeValues={':uid': user_id})
        items = scan.get('Items', [])
        if not items:
            return response(404, "Usuario no encontrado")
        user = items[0]
        del user['contraseña_hash']
        return response(200, user)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
