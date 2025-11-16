echo "Inicializando Airflow..."

airflow db init

airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@alerta-utec.com \
    --password admin

# Iniciar scheduler y webserver
echo "Airflow inicializado correctamente"
