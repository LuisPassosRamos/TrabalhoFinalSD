# src\sensor\sensor.py

import socket
import threading
import time
import random
import sys

# Parte do código no sensor.py que envia status via gRPC
import time
import grpc
from middleware.protos import sensor_status_pb2
from middleware.protos import sensor_status_pb2_grpc

def envia_status_para_monitor(sensor_id, monitor_host="monitor", monitor_port=50051):
    """
    Envia, a cada 10 segundos, uma mensagem com o status do sensor para o monitor via gRPC.
    """
    channel = grpc.insecure_channel(f"{monitor_host}:{monitor_port}")
    stub = sensor_status_pb2_grpc.MonitorServiceStub(channel)
    
    while True:
        timestamp = int(time.time())
        status_msg = "Operando normalmente"
        request = sensor_status_pb2.Status(sensor_id=sensor_id, status=status_msg, timestamp=timestamp)
        try:
            response = stub.SendStatus(request)
            print(f"[Sensor {sensor_id}] Status enviado para o monitor: {status_msg}")
        except Exception as e:
            print(f"[Sensor {sensor_id}] Erro ao enviar status para o monitor: {e}")
        time.sleep(10)

def simula_dados():
    temperatura = round(random.uniform(15.0, 35.0), 1)
    umidade = round(random.uniform(30.0, 80.0), 1)
    pressao = round(random.uniform(990.0, 1020.0), 1)
    return f"{temperatura},{umidade},{pressao}"

def enviar_dados(conn):
    """Envia dados climáticos periodicamente para o cliente."""
    try:
        while True:
            dados = simula_dados()
            conn.sendall(dados.encode())
            print(f"[Sensor] Dados enviados: {dados}")
            time.sleep(5)  # Aguarda 5 segundos antes de enviar os próximos dados
    except ConnectionResetError:
        print("[Sensor] Cliente desconectado abruptamente")
    finally:
        conn.close()

def trata_conexao(conn, addr):
    """Gerencia a conexão com o cliente e chama o método de envio de dados."""
    print(f"[Sensor] Conexão estabelecida com o cliente.")
    enviar_dados(conn)  # Chama o método para enviar dados ao cliente

def main(porta=5000):
    # Identificador único para o sensor (pode ser baseado na porta ou outro parâmetro)
    sensor_id = f"sensor_{porta}"
    
    # Inicia a thread para envio de status para o monitor
    status_thread = threading.Thread(target=envia_status_para_monitor, args=(sensor_id,))
    status_thread.daemon = True
    status_thread.start()
    
    # Código existente: inicia servidor TCP
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("0.0.0.0", porta))
    servidor.listen(1)
    print(f"[Sensor {sensor_id}] Servidor TCP iniciado na porta {porta}")
    while True:
        conn, addr = servidor.accept()
        thread = threading.Thread(target=trata_conexao, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    main(porta)