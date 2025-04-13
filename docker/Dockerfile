FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código fonte para garantir que o diretório src/middleware/proto esteja disponível
COPY . .

# Gera os arquivos gRPC a partir do .proto
RUN python -m grpc_tools.protoc -I./src/middleware/proto --python_out=./src/middleware --grpc_python_out=./src/middleware ./src/middleware/proto/sensor.proto

# Define PYTHONPATH para incluir o diretório src
ENV PYTHONPATH=/app/src

# Exposição de porta opcional; a configuração final é definida no docker-compose
EXPOSE 5000

# Comando para iniciar a aplicação (o papel do container é decidido no docker-compose)
CMD ["python", "src/main.py", "sensor"]