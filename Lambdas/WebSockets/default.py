import json
import boto3
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')
INCIDENTES_TABLE = os.environ.get('INCIDENTES_TABLE', 'incidentes')
USERS_TABLE = os.environ.get('USERS_TABLE', 'usuarios')
HISTORIAL_TABLE = os.environ.get('HISTORIAL_TABLE', 'historial-incidente')

def send_to_connection(connection_id, message, event):
    """Enviar mensaje usando el event"""
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    endpoint_url = f"https://{domain_name}/{stage}"
    
    try:
        gatewayapi = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
        gatewayapi.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        print(f"Mensaje enviado a {connection_id}: {message.get('action')}")
    except Exception as e:
        print(f"Error enviando a {connection_id}: {str(e)}")
        if 'GoneException' in str(e):
            table = dynamodb.Table(CONNECTIONS_TABLE)
            table.delete_item(Key={'connectionId': connection_id})

def handler(event, context):
    try:
        connection_id = event['requestContext']['connectionId']
        
        table = dynamodb.Table(CONNECTIONS_TABLE)
        connection = table.get_item(Key={'connectionId': connection_id}).get('Item')
        
        if not connection or not connection.get('authenticated'):
            print(f"Conexión no autenticada: {connection_id}")
            return {'statusCode': 401, 'body': 'No autenticado'}
        
        user_id = connection['userId']
        user_email = connection['email']
        user_role = connection['role']
        
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        print(f"{user_role} {user_email}: {action}")
        
        if action == 'ping':
            send_to_connection(connection_id, {
                'action': 'pong',
                'timestamp': datetime.utcnow().isoformat(),
                'userRole': user_role
            }, event)
            
        elif action == 'get_active_incidents':
            handle_get_active_incidents(connection_id, user_role, event)

        elif action == 'get_all_incidents':
            handle_get_all_incidents(connection_id, user_role, event)
            
        elif action == 'subscribe_incidents':
            handle_subscribe_incidents(connection_id, user_role, body, event)
        
        # DASHBOARD ADMINISTRATIVO (solo autoridades y personal administrativo)
        elif action == 'get_dashboard':
            handle_get_dashboard(connection_id, user_role, body, event)
            
        elif action == 'subscribe_dashboard':
            handle_subscribe_dashboard(connection_id, user_role, body, event)
            
        elif action == 'get_stats':
            handle_get_stats(connection_id, user_role, body, event)
            
        elif action == 'get_users':
            handle_get_users(connection_id, user_role, body, event)
            
        
        else:
            send_to_connection(connection_id, {
                'action': 'error',
                'message': f'Acción no reconocida: {action}'
            }, event)
            return {'statusCode': 400, 'body': 'Acción no reconocida'}
        
        return {'statusCode': 200, 'body': 'Message processed'}
        
    except Exception as e:
        print(f"❌ Error en default handler: {str(e)}")
        return {'statusCode': 500, 'body': 'Error interno del servidor'}


def handle_get_active_incidents(connection_id, user_role, event):
    try:
        incidentes_table = dynamodb.Table(INCIDENTES_TABLE)
        
        scan = incidentes_table.scan(
            FilterExpression='estado IN :e',
            ExpressionAttributeValues={':e': 'en proceso'}
        )
        incidentes = scan.get('Items', [])
        
        incidentes.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        send_to_connection(connection_id, {
            'action': 'active_incidents_data',
            'incidents': incidentes,
            'total': len(incidentes),
            'userRole': user_role,
            'timestamp': datetime.utcnow().isoformat()
        }, event)
        
    except Exception as e:
        print(f"Error obteniendo incidentes activos: {str(e)}")
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Error al obtener incidentes activos'
        }, event)

def handle_get_all_incidents(connection_id, user_role, event):
    """Obtener TODOS los incidentes - Solo para autoridades"""
    try:
        if user_role != 'autoridad':
            send_to_connection(connection_id, {
                'action': 'error',
                'message': 'No autorizado - se requiere rol de autoridad'
            }, event)
            return
        
        incidentes_table = dynamodb.Table(INCIDENTES_TABLE)
        
        scan = incidentes_table.scan()
        incidentes = scan.get('Items', [])
        
        incidentes.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        send_to_connection(connection_id, {
            'action': 'all_incidents_data',
            'incidents': incidentes,
            'total': len(incidentes),
            'userRole': user_role,
            'timestamp': datetime.utcnow().isoformat()
        }, event)
        
    except Exception as e:
        print(f"Error obteniendo todos los incidentes: {str(e)}")
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Error al obtener incidentes'
        }, event)

def handle_subscribe_incidents(connection_id, user_role, body, event):
    """Suscribirse a updates de incidentes"""
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    subscription_data = {
        'subscribedToIncidents': True,
        'userRole': user_role,
        'lastSubscription': datetime.utcnow().isoformat()
    }
    
    if user_role == 'estudiante':
        subscription_data['incidentStates'] = ['en proceso']
    elif user_role == 'personal_admin':
        subscription_data['incidentStates'] = ['pendiente', 'en proceso']
    else:
        subscription_data['incidentStates'] = ['pendiente', 'en proceso', 'resuelto']
    
    table.update_item(
        Key={'connectionId': connection_id},
        UpdateExpression='SET subscribedToIncidents = :sub, subscriptionData = :data',
        ExpressionAttributeValues={
            ':sub': True,
            ':data': subscription_data
        }
    )
    
    send_to_connection(connection_id, {
        'action': 'subscribed',
        'type': 'incidents',
        'userRole': user_role,
        'message': f'Suscrito a updates de incidentes ({", ".join(subscription_data["incidentStates"])})',
        'subscriptionData': subscription_data
    }, event)

def handle_get_dashboard(connection_id, user_role, body, event):
    if user_role not in ['autoridad', 'personal_admin']:
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'No autorizado para acceder al dashboard'
        }, event)
        return
    
    try:
        incidentes_table = dynamodb.Table(INCIDENTES_TABLE)
        
        response = incidentes_table.scan()
        all_incidents = response.get('Items', [])
        
        stats = {
            'total': len(all_incidents),
            'pendientes': len([i for i in all_incidents if i.get('estado') == 'pendiente']),
            'en_atencion': len([i for i in all_incidents if i.get('estado') == 'en_atencion']),
            'resueltos': len([i for i in all_incidents if i.get('estado') == 'resuelto']),
            'cerrados': len([i for i in all_incidents if i.get('estado') == 'cerrado']),
            'urgentes': len([i for i in all_incidents if i.get('urgencia') == 'alta']),
        }
        
        yesterday = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        recent_incidents = [
            i for i in all_incidents 
            if i.get('fecha', '') > yesterday
        ]
        
        attention_required = [
            i for i in all_incidents 
            if i.get('estado') in ['pendiente'] and i.get('urgencia') == 'alta'
        ]
        
        incidents_by_type = {}
        for incident in all_incidents:
            tipo = incident.get('tipo', 'General')
            if tipo not in incidents_by_type:
                incidents_by_type[tipo] = 0
            incidents_by_type[tipo] += 1
        
        incidents_by_location = {}
        for incident in all_incidents:
            ubicacion = incident.get('ubicacion', 'Desconocida')
            if ubicacion not in incidents_by_location:
                incidents_by_location[ubicacion] = 0
            incidents_by_location[ubicacion] += 1
        
        dashboard_data = {
            'stats': stats,
            'recent_incidents': recent_incidents[:10],
            'attention_required': attention_required,
            'by_type': incidents_by_type,
            'by_location': incidents_by_location,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        send_to_connection(connection_id, {
            'action': 'dashboard_data',
            'dashboard': dashboard_data,
            'userRole': user_role,
            'timestamp': datetime.utcnow().isoformat()
        }, event)
        
    except Exception as e:
        print(f"Error obteniendo dashboard: {str(e)}")
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Error al cargar el dashboard'
        }, event)

def handle_subscribe_dashboard(connection_id, user_role, body, event):
    if user_role not in ['autoridad', 'personal_admin']:
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'No autorizado para suscribirse al dashboard'
        }, event)
        return
    
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    table.update_item(
        Key={'connectionId': connection_id},
        UpdateExpression='SET subscribedToDashboard = :sub, dashboardSubscriptionTime = :time',
        ExpressionAttributeValues={
            ':sub': True,
            ':time': datetime.utcnow().isoformat()
        }
    )
    
    send_to_connection(connection_id, {
        'action': 'subscribed',
        'type': 'dashboard',
        'message': 'Suscrito a updates del dashboard administrativo',
        'userRole': user_role,
        'timestamp': datetime.utcnow().isoformat()
    }, event)

def handle_get_stats(connection_id, user_role, body, event):
    if user_role not in ['autoridad', 'personal_admin']:
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'No autorizado para ver estadísticas'
        }, event)
        return
    
    try:
        incidentes_table = dynamodb.Table(INCIDENTES_TABLE)
        response = incidentes_table.scan()
        all_incidents = response.get('Items', [])
        
        # Estadísticas por tiempo
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_ago = (now - timedelta(days=7)).isoformat()
        month_ago = (now - timedelta(days=30)).isoformat()
        
        incidents_today = [i for i in all_incidents if i.get('fecha', '') > today]
        incidents_week = [i for i in all_incidents if i.get('fecha', '') > week_ago]
        incidents_month = [i for i in all_incidents if i.get('fecha', '') > month_ago]
        
        resolved_incidents = [i for i in all_incidents if i.get('estado') in ['resuelto', 'cerrado']]
        resolution_times = []
        
        for incident in resolved_incidents:
            if incident.get('fecha') and incident.get('estado'):
                resolution_times.append(1)  # placeholder
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        detailed_stats = {
            'period': {
                'today': len(incidents_today),
                'last_week': len(incidents_week),
                'last_month': len(incidents_month)
            },
            'performance': {
                'avg_resolution_time': avg_resolution_time,
                'resolution_rate': len(resolved_incidents) / len(all_incidents) if all_incidents else 0,
                'urgent_resolution_rate': 0.85
            },
            'trends': {
                'daily_trend': [5, 8, 6, 12, 7, 9, 10],
                'weekly_comparison': 15
            }
        }
        
        send_to_connection(connection_id, {
            'action': 'detailed_stats',
            'stats': detailed_stats,
            'timestamp': datetime.utcnow().isoformat()
        }, event)
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {str(e)}")
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Error al cargar estadísticas'
        }, event)

def handle_get_users(connection_id, user_role, body, event):
    """Obtener lista de usuarios - SOLO AUTORIDADES"""
    if user_role != 'autoridad':
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Solo autoridades pueden ver la lista de usuarios'
        }, event)
        return
    
    try:
        users_table = dynamodb.Table(USERS_TABLE)
        response = users_table.scan()
        users = response.get('Items', [])
        
        safe_users = []
        for user in users:
            safe_users.append({
                'userId': user.get('tenant_id'),
                'email': user.get('email'),
                'nombre': user.get('nombre'),
                'role': user.get('role'),
                'createdAt': user.get('createdAt')
            })
        
        send_to_connection(connection_id, {
            'action': 'users_list',
            'users': safe_users,
            'total': len(safe_users),
            'timestamp': datetime.utcnow().isoformat()
        }, event)
        
    except Exception as e:
        print(f"Error obteniendo usuarios: {str(e)}")
        send_to_connection(connection_id, {
            'action': 'error',
            'message': 'Error al cargar lista de usuarios'
        }, event)

