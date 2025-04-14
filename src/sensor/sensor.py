# src/sensor/sensor.py
import socket
import threading
import time
import random
import sys
import grpc
from middleware.protos import sensor_status_pb2
from middleware.protos import sensor_status_pb2_grpc

# Inicializa o relógio de Lamport e um lock para proteger o acesso concorrente
relogio_de_lamport = 0
lamport_lock = threading.Lock()

def incrementa_relogio_de_lamport():
    """
    Incrementa o relógio de Lamport de forma segura (com lock) e retorna o valor atualizado.
    Esse valor será usado como timestamp em cada envio de mensagem.
    """
    global relogio_de_lamport
    with lamport_lock:
        relogio_de_lamport += 1
        print(f"[Sensor] Relógio de Lamport incrementado: {relogio_de_lamport}")
        return relogio_de_lamport

def envia_status_para_monitor(sensor_id, monitor_host="monitor", monitor_port=50051):
    """
    Envia, a cada 10 segundos, uma mensagem com o status do sensor para o monitor via gRPC.
    O timestamp enviado é o valor do relógio de Lamport atualizado.
    """
    channel = grpc.insecure_channel(f"{monitor_host}:{monitor_port}")
    stub = sensor_status_pb2_grpc.MonitorServiceStub(channel)
    
    while True:
        # Incrementa o relógio e utiliza o valor atualizado como timestamp
        incrementa_relogio_de_lamport()
        timestamp = int(time.time()) 
        status_msg = "Operando normalmente"
        request = sensor_status_pb2.Status(sensor_id=sensor_id, status=status_msg, timestamp=timestamp)
        try:
            response = stub.SendStatus(request)
            print(f"[Sensor] Status enviado para o monitor: {status_msg} com timestamp {timestamp}")
            
        except Exception as e:
            print(f"[Sensor] Erro ao enviar status para o monitor: {e}")
        time.sleep(10)

def simula_dados():
    """Simula a leitura de dados climáticos (temperatura, umidade e pressão)."""
    temperatura = round(random.uniform(15.0, 35.0), 1)
    umidade = round(random.uniform(30.0, 80.0), 1)
    pressao = round(random.uniform(990.0, 1020.0), 1)
    return f"{temperatura},{umidade},{pressao}"

def enviar_dados(conn):
    """
    Envia periodicamente os dados simulados para o cliente, incluindo
    o timestamp do relógio de Lamport (no formato "dados|timestamp").
    """
    try:
        while True:
            dados = simula_dados()
            # Incrementa o relógio de Lamport e obtém o valor atualizado
            timestamp = incrementa_relogio_de_lamport()
            # Cria a mensagem contendo os dados e o timestamp, separados por "|"
            mensagem = f"{dados}|{timestamp}"
            conn.sendall(mensagem.encode())
            print(f"[Sensor] Dados enviados: {mensagem}")
            time.sleep(5)  # Aguarda 5 segundos antes de enviar os próximos dados
    except ConnectionResetError:
        print("[Sensor] Cliente desconectado abruptamente")
    finally:
        conn.close()

def trata_conexao(conn, addr):
    """Gerencia a conexão com o cliente e chama o método de envio de dados."""
    print(f"[Sensor] Conexão estabelecida com o cliente {addr}.")
    enviar_dados(conn)

def main(porta=5000):
    # Define um identificador único para o sensor (pode ser baseado na porta, por exemplo)
    sensor_id = f"sensor_{porta}"
    
    # Inicia a thread para envio de status ao monitor via gRPC
    status_thread = threading.Thread(target=envia_status_para_monitor, args=(sensor_id,))
    status_thread.daemon = True
    status_thread.start()
    
    # Inicia o servidor TCP que aceita conexões de clientes
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
    # Permite definir a porta via linha de comando; caso contrário, usa a porta 5000
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    main(porta)
