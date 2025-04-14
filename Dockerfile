# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos do projeto para o container
COPY ./src ./src

# Define o PYTHONPATH para incluir os diretórios necessários
ENV PYTHONPATH=/app/src:/app/src/middleware/protos

# Comando padrão para execução (sensor). Esse comando será sobrescrito no docker-compose.
CMD ["python", "-u", "src/sensor/sensor.py", "5000"]
