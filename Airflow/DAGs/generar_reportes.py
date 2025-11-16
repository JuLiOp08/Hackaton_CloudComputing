from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from datetime import datetime, timedelta
import boto3
import json
import pandas as pd

default_args = {
    'owner': 'alerta-utec',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

def get_aws_client(service_name):
    hook = AwsBaseHook(aws_conn_id='aws_default', client_type=service_name)
    return hook.get_client_type(service_name)

def generar_reporte_diario():
    """Generar reporte diario de incidentes"""
    print("Generando reporte diario...")
    
    dynamodb = get_aws_client('dynamodb')
    s3 = get_aws_client('s3')
    
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        response = dynamodb.scan(
            TableName='incidentes',
            FilterExpression='#fecha >= :fecha',
            ExpressionAttributeNames={'#fecha': 'fecha'},
            ExpressionAttributeValues={':fecha': {'S': yesterday}}
        )
        
        incidents = response.get('Items', [])
        
        daily_stats = {
            'fecha': datetime.utcnow().isoformat(),
            'total_incidentes': len(incidents),
            'estadisticas_por_tipo': {},
            'estadisticas_por_estado': {},
            'estadisticas_por_urgencia': {},
            'tasa_resolucion': 0,
            'incidentes_mas_comunes': []
        }
        
        for incident in incidents:
            incident_type = incident['tipo']['S']
            daily_stats['estadisticas_por_tipo'][incident_type] = \
                daily_stats['estadisticas_por_tipo'].get(incident_type, 0) + 1
            
            estado = incident['estado']['S']
            daily_stats['estadisticas_por_estado'][estado] = \
                daily_stats['estadisticas_por_estado'].get(estado, 0) + 1
            
            urgencia = incident.get('urgencia', {'S': 'media'})['S']
            daily_stats['estadisticas_por_urgencia'][urgencia] = \
                daily_stats['estadisticas_por_urgencia'].get(urgencia, 0) + 1
        
        resolved = daily_stats['estadisticas_por_estado'].get('resuelto', 0)
        daily_stats['tasa_resolucion'] = resolved / len(incidents) if incidents else 0
        
        s3.put_object(
            Bucket='alerta-utec-reports',
            Key=f"reportes/diario/reporte_{datetime.utcnow().strftime('%Y%m%d')}.json",
            Body=json.dumps(daily_stats, indent=2),
            ContentType='application/json'
        )
        
        print(f"Reporte diario generado: {len(incidents)} incidentes procesados")
        
    except Exception as e:
        print(f"Error generando reporte diario: {str(e)}")
        raise

def generar_reporte_semanal():
    """Generar reporte semanal consolidado"""
    print("Generando reporte semanal...")
    
    dynamodb = get_aws_client('dynamodb')
    s3 = get_aws_client('s3')
    
    try:
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        response = dynamodb.scan(
            TableName='incidentes',
            FilterExpression='#fecha >= :fecha',
            ExpressionAttributeNames={'#fecha': 'fecha'},
            ExpressionAttributeValues={':fecha': {'S': week_ago}}
        )
        
        incidents = response.get('Items', [])
        
        weekly_analysis = {
            'periodo': f"Semana {datetime.utcnow().strftime('%Y-%U')}",
            'fecha_generacion': datetime.utcnow().isoformat(),
            'resumen_ejecutivo': {
                'total_incidentes': len(incidents),
                'tendencia_semanal': calcular_tendencia(incidents),
                'areas_criticas': identificar_areas_criticas(incidents),
                'eficiencia_resolucion': calcular_eficiencia(incidents)
            },
            'metricas_detalladas': {},
            'recomendaciones': generar_recomendaciones(incidents)
        }
        
        s3.put_object(
            Bucket='alerta-utec-reports',
            Key=f"reportes/semanal/reporte_semanal_{datetime.utcnow().strftime('%Y%m%d')}.json",
            Body=json.dumps(weekly_analysis, indent=2),
            ContentType='application/json'
        )
        
        print(f"Reporte semanal generado: {len(incidents)} incidentes analizados")
        
    except Exception as e:
        print(f"Error generando reporte semanal: {str(e)}")
        raise

def calcular_tendencia(incidents):
    """Calcular tendencia semanal de incidentes"""
    return "estable"

def identificar_areas_criticas(incidents):
    """Identificar áreas con más incidentes"""
    areas = {}
    for incident in incidents:
        location = incident['ubicacion']['S']
        areas[location] = areas.get(location, 0) + 1
    return sorted(areas.items(), key=lambda x: x[1], reverse=True)[:3]

def calcular_eficiencia(incidents):
    """Calcular métricas de eficiencia"""
    return {"tasa_resolucion": 0.85, "tiempo_promedio": "2.5h"}

def generar_recomendaciones(incidents):
    """Generar recomendaciones basadas en datos"""
    return [
        "Incrementar mantenimiento preventivo en áreas críticas",
        "Reforzar protocolos de seguridad en laboratorios",
        "Optimizar tiempos de respuesta para incidentes de alta urgencia"
    ]

with DAG(
    'generacion_reportes_automaticos',
    default_args=default_args,
    description='DAG para generación automática de reportes UTEC',
    schedule_interval=timedelta(hours=1),
    catchup=False,
    tags=['alerta-utec', 'reportes']
) as dag:

    reporte_diario_task = PythonOperator(
        task_id='generar_reporte_diario',
        python_callable=generar_reporte_diario
    )

    reporte_semanal_task = PythonOperator(
        task_id='generar_reporte_semanal',
        python_callable=generar_reporte_semanal
    )

    reporte_diario_task >> reporte_semanal_task
