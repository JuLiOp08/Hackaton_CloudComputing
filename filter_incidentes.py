import json
import boto3
import jwt
import os

dynamodb = boto3.resource('dynamodb')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')


def validate_token(event):
    headers = event.get('headers', {})
    auth = headers.get('Authorization') or headers.get('authorization')
    if not auth or not auth.startswith('Bearer '):
        return None
    token = auth.split(' ')[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except Exception:
        return None

def lambda_handler(event, context):
    try:
        claims = validate_token(event)
        if not claims:
            return response(401, "Token inválido")
        params = event.get('queryStringParameters', {}) or {}
        table = dynamodb.Table(INCIDENTES_TABLE)
        filter_expr = []
        expr_attr = {}
        if 'urgencia' in params:
            filter_expr.append('urgencia = :u')
            expr_attr[':u'] = params['urgencia']
        if 'ubicacion' in params:
            filter_expr.append('ubicacion = :l')
            expr_attr[':l'] = params['ubicacion']
        if 'tipo' in params:
            filter_expr.append('tipo = :t')
            expr_attr[':t'] = params['tipo']
        if 'fecha' in params:
            filter_expr.append('fecha = :f')
            expr_attr[':f'] = params['fecha']
        if filter_expr:
            scan = table.scan(
                FilterExpression=' AND '.join(filter_expr),
                ExpressionAttributeValues=expr_attr
            )
        else:
            scan = table.scan()
        incidentes = scan.get('Items', [])
        return response(200, incidentes)
    except Exception as e:
        return response(500, str(e))

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
