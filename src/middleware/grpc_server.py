from concurrent import futures
import grpc
import time
# Alterado para usar o pacote middleware
from middleware import sensor_pb2  
from middleware import sensor_pb2_grpc

class SensorServiceServicer(sensor_pb2_grpc.SensorServiceServicer):
    def GetSensorData(self, request, context):
        # Simular dados do sensor
        response = sensor_pb2.SensorResponse(
            temperatura=25.3,
            umidade=60.5,
            pressao=1013.25
        )
        return response

def serve():
    # Cria o servidor usando o módulo grpc nativo
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(SensorServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Servidor gRPC rodando na porta 50051...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
