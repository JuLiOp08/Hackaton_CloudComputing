from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from datetime import datetime, timedelta
import boto3
import json
import pandas as pd
from sklearn.ensemble import IsolationForest

default_args = {
    'owner': 'alerta-utec',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

def get_aws_client(service_name):
    """Obtener cliente AWS con credenciales de Airflow"""
    hook = AwsBaseHook(aws_conn_id='aws_default', client_type=service_name)
    return hook.get_client_type(service_name)

def clasificar_incidentes_automaticamente():
    """Clasificación automática de incidentes por urgencia"""
    print("Clasificando incidentes automáticamente...")
    
    dynamodb = get_aws_client('dynamodb')
    
    try:
        response = dynamodb.scan(
            TableName='incidentes',
            FilterExpression='#estado = :estado',
            ExpressionAttributeNames={'#estado': 'estado'},
            ExpressionAttributeValues={':estado': {'S': 'pendiente'}}
        )
        
        incidents = response.get('Items', [])
        print(f"Encontrados {len(incidents)} incidentes pendientes para clasificar")
        
        for incident in incidents:
            incident_id = incident['codigo_incidente']['S']
            incident_type = incident['tipo']['S']
            location = incident['ubicacion']['S'].lower()
            
            urgency = determinar_urgencia_automatica(incident_type, location)
            
            current_urgency = incident.get('urgencia', {'S': 'media'})['S']
            if urgency != current_urgency:
                dynamodb.update_item(
                    TableName='incidentes',
                    Key={'codigo_incidente': incident['codigo_incidente']},
                    UpdateExpression='SET urgencia = :urgencia',
                    ExpressionAttributeValues={':urgencia': {'S': urgency}}
                )
                print(f"Incidente {incident_id} clasificado como {urgency}")
                
    except Exception as e:
        print(f"Error en clasificación automática: {str(e)}")
        raise

def determinar_urgencia_automatica(incident_type, location):
    """Determinar urgencia basado en tipo y ubicación"""
    high_urgency_types = ['Emergencia médica', 'Fuga de agua', 'Incendio', 'Fuga de gas']
    high_urgency_locations = ['laboratorio', 'cocina', 'aula', 'biblioteca']
    
    medium_urgency_types = ['Baño dañado', 'Daño infraestructura', 'Piso mojado']
    
    if incident_type in high_urgency_types:
        return 'alta'
    elif any(loc in location for loc in high_urgency_locations):
        return 'alta'
    elif incident_type in medium_urgency_types:
        return 'media'
    else:
        return 'baja'

def enviar_alertas_automaticas():
    """Enviar alertas automáticas para incidentes de alta urgencia"""
    print("🚨 Enviando alertas automáticas...")
    
    dynamodb = get_aws_client('dynamodb')
    sns = get_aws_client('sns')
    
    try:
        response = dynamodb.scan(
            TableName='incidentes',
            FilterExpression='urgencia = :urgencia AND #estado = :estado',
            ExpressionAttributeNames={'#estado': 'estado'},
            ExpressionAttributeValues={
                ':urgencia': {'S': 'alta'},
                ':estado': {'S': 'pendiente'}
            }
        )
        
        high_urgency_incidents = response.get('Items', [])
        print(f"Encontrados {len(high_urgency_incidents)} incidentes de alta urgencia")
        
        for incident in high_urgency_incidents:
            incident_id = incident['codigo_incidente']['S']
            incident_type = incident['tipo']['S']
            location = incident['ubicacion']['S']
            
            message = {
                'evento': 'alerta_urgencia_alta',
                'codigo_incidente': incident_id,
                'tipo': incident_type,
                'ubicacion': location,
                'mensaje': f'Incidente de alta urgencia requiere atención inmediata: {incident_type} en {location}',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            sns.publish(
                TopicArn='arn:aws:sns:us-east-1:123456789012:alerta-utec-notifications',
                Message=json.dumps(message),
                Subject='🚨 Alerta UTEC - Incidente de Alta Urgencia'
            )
            print(f"Alerta enviada para incidente {incident_id}")
            
    except Exception as e:
        print(f"Error enviando alertas: {str(e)}")
        raise

def detectar_anomalias_patrones():
    """Detección de patrones anómalos usando Machine Learning"""
    print("Detectando patrones anómalos...")
    
    dynamodb = get_aws_client('dynamodb')
    
    try:
        response = dynamodb.scan(TableName='incidentes')
        incidents_data = []
        
        for item in response['Items']:
            try:
                incident_date = datetime.fromisoformat(item['fecha']['S'].replace('Z', '+00:00'))
                incidents_data.append({
                    'hora': incident_date.hour,
                    'dia_semana': incident_date.weekday(),
                    'tipo': item['tipo']['S'],
                    'ubicacion': item['ubicacion']['S'],
                    'urgencia': item.get('urgencia', {'S': 'media'})['S']
                })
            except Exception as e:
                continue
        
        if len(incidents_data) > 10:
            df = pd.DataFrame(incidents_data)
            
            df_encoded = pd.get_dummies(df[['tipo', 'ubicacion', 'urgencia']])
            
            model = IsolationForest(contamination=0.1, random_state=42)
            predictions = model.fit_predict(df_encoded)
            
            anomalies = sum(predictions == -1)
            print(f"🔍 Detectadas {anomalies} anomalías en los datos")
            
            if anomalies > 0:
                print("Patrones anómalos detectados - revisar posibles issues")
                
    except Exception as e:
        print(f"Error en detección de anomalías: {str(e)}")

with DAG(
    'gestion_automatizada_incidentes',
    default_args=default_args,
    description='DAG para gestión automatizada de incidentes UTEC',
    schedule_interval=timedelta(minutes=30),
    catchup=False,
    tags=['alerta-utec', 'incidentes']
) as dag:

    clasificar_task = PythonOperator(
        task_id='clasificar_incidentes_automaticamente',
        python_callable=clasificar_incidentes_automaticamente
    )

    alertas_task = PythonOperator(
        task_id='enviar_alertas_automaticas',
        python_callable=enviar_alertas_automaticas
    )

    anomalias_task = PythonOperator(
        task_id='detectar_anomalias_patrones',
        python_callable=detectar_anomalias_patrones
    )

    clasificar_task >> [alertas_task, anomalias_task]
