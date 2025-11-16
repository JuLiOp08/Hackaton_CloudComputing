import json
import boto3
import uuid
import jwt
import os
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE')
SNS_TOPIC = os.environ.get('SNS_TOPIC')
JWT_SECRET = os.environ.get('JWT_SECRET', 'alerta-utec-secret')

VALID_TYPES = [
    "Fuga de agua", "Piso mojado", "Daño en utilería de salón", "Daño infraestructura", "Objeto perdido", "Emergencia médica", "Baño dañado"
]

def lambda_handler(event, context):
    try:
        auth = event["requestContext"]["authorizer"]
        
        body = json.loads(event.get('body', '{}'))
        ubicacion = body.get('ubicacion')
        descripcion = body.get('descripcion')
        tipo = body.get('tipo')
        urgencia = body.get('urgencia')
        imagen = body.get('imagen')
        
        if not ubicacion or not descripcion or not tipo or not urgencia:
            return response(400, "Faltan campos obligatorios")
            
        if tipo not in VALID_TYPES:
            return response(400, "Tipo de incidente inválido")
            
        codigo_incidente = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        incidente = {
            'codigo_incidente': codigo_incidente,
            'ubicacion': ubicacion,
            'descripcion': descripcion,
            'estado': 'pendiente',
            'fecha': now,
            'tipo': tipo,
            'urgencia': urgencia,
            'imagen': imagen if imagen else None,
            'reportanteId': auth['userId'],
            'responsableId': None
        }
        
        dynamodb.Table(INCIDENTES_TABLE).put_item(Item=incidente)
        evento_id = str(uuid.uuid4())
        historial = {
            'codigo_incidente': codigo_incidente,
            'uuid_evento': evento_id,
            'tiempo': now,
            'encargado': auth['userId'],
            'estado': 'pendiente',
            'detalles': 'Incidente creado'
        }
        dynamodb.Table(HISTORIAL_TABLE).put_item(Item=historial)
        sns.publish(TopicArn=SNS_TOPIC, Message=json.dumps({
            'evento': 'incidente_creado',
            'codigo_incidente': codigo_incidente,
            'ubicacion': ubicacion,
            'tipo': tipo,
            'urgencia': urgencia,
            'reportanteId': auth['userId'],
            'fecha': now
        }))

    except Exception as e:
        return response(500, str(e))

    try:
        lambda_client = boto3.client('lambda')
        
        lambda_client.invoke(
            FunctionName='notify_handler',
            InvocationType='Event',
            Payload=json.dumps({
                'action': 'new_incident',
                'incident': {
                    'codigo_incidente': codigo_incidente,
                    'ubicacion': ubicacion,
                    'tipo': tipo,
                    'urgencia': urgencia,
                    'reportanteId': auth['userId'],
                    'fecha': now
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        )
    
    except Exception as e:
        print(f"Error invocando notificación: {str(e)}")
        
    return response(200, {
        'codigo_incidente': codigo_incidente,
        'estado': 'pendiente',
        'fecha': now
    })

def response(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': code == 200, 'data': body if code == 200 else None, 'error': None if code == 200 else body})
    }
