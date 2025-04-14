# src/middleware/monitor_server.py
import time
from concurrent import futures
import grpc

from middleware.protos import sensor_status_pb2
from middleware.protos import sensor_status_pb2_grpc

# Dicionário para registrar o último horário de status recebido por sensor
sensors_status = {}  # { sensor_id: timestamp }

class MonitorServiceServicer(sensor_status_pb2_grpc.MonitorServiceServicer):
    def SendStatus(self, request, context):
        sensor_id = request.sensor_id
        sensors_status[sensor_id] = time.time()
        print(f"[Monitor] Recebido status de '{sensor_id}': '{request.status}' em {request.timestamp}")
        return sensor_status_pb2.Ack(mensagem="Status recebido")

def monitor_failure_checker():
    """Thread que verifica falhas dos sensores se não houver status em 20 segundos."""
    while True:
        agora = time.time()
        for sensor_id, ultimo in sensors_status.items():
            if agora - ultimo > 20:
                print(f"[Monitor] Falha detectada: Sensor '{sensor_id}' não enviou status nos últimos {agora - ultimo:.1f} segundos!")
        time.sleep(5)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_status_pb2_grpc.add_MonitorServiceServicer_to_server(MonitorServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("[Monitor] gRPC server iniciado na porta 50051")
    
    # Inicia a thread de verificação de falhas
    failure_checker = futures.ThreadPoolExecutor(max_workers=1)
    failure_checker.submit(monitor_failure_checker)
    
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
