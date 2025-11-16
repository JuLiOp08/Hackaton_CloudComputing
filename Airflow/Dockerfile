FROM apache/airflow:2.7.0

USER root

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        lsb-release && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar DAGs y scripts
COPY dags/ /opt/airflow/dags/
COPY scripts/ /opt/airflow/scripts/

# Configurar permisos
RUN chmod +x /opt/airflow/scripts/init.sh

# Variables de entorno para Airflow
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor
ENV AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@localhost:5432/airflow
