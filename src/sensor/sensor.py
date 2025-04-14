# src/sensor/sensor.py
import socket
import threading
import time
import random
import sys
import grpc
from concurrent import futures

from middleware.protos import sensor_status_pb2
from middleware.protos import sensor_status_pb2_grpc
from middleware.protos import bully_pb2
from middleware.protos import bully_pb2_grpc

# Variáveis globais para o Bully Algorithm
sensor_id = None        # Ex: "sensor_5000"
is_coordinator = False  # Flag se este sensor é o coordenador
coordinator_id = None   # Armazena o id do coordenador atual
election_in_progress = False

# Lista ou dicionário de sensores conhecidos (endereço e porta bully)
sensores_conhecidos = {
    "sensor_5000": ("sensor1", 5001),  # sensor1 ou o nome do container correspondente
    "sensor_5001": ("sensor2", 5002),
    "sensor_5002": ("sensor3", 5003)
}

# Inicializa o relógio de Lamport e um lock para proteger o acesso concorrente
relogio_de_lamport = 0
lamport_lock = threading.Lock()

def incrementa_relogio_de_lamport():
    global relogio_de_lamport
    with lamport_lock:
        relogio_de_lamport += 1
        print(f"[Sensor {sensor_id}] Relógio de Lamport incrementado: {relogio_de_lamport}")
        return relogio_de_lamport

def envia_status_para_monitor(sensor_id, monitor_host="monitor", monitor_port=50051):
    """
    Envia, a cada 10 segundos, uma mensagem com o status do sensor para o monitor via gRPC.
    """
    channel = grpc.insecure_channel(f"{monitor_host}:{monitor_port}")
    stub = sensor_status_pb2_grpc.MonitorServiceStub(channel)
    
    while True:
        incrementa_relogio_de_lamport()
        timestamp = int(time.time()) 
        status_msg = "Operando normalmente"
        request = sensor_status_pb2.Status(sensor_id=sensor_id, status=status_msg, timestamp=timestamp)
        try:
            response = stub.SendStatus(request)
            print(f"[Sensor {sensor_id}] Status enviado para o monitor: {status_msg} com timestamp {timestamp}")
        except Exception as e:
            print(f"[Sensor {sensor_id}] Erro ao enviar status para o monitor: {e}")
        time.sleep(10)

def simula_dados():
    """Simula a leitura de dados climáticos (temperatura, umidade e pressão)."""
    temperatura = round(random.uniform(15.0, 35.0), 1)
    umidade = round(random.uniform(30.0, 80.0), 1)
    pressao = round(random.uniform(990.0, 1020.0), 1)
    return f"{temperatura},{umidade},{pressao}"

def enviar_dados(conn):
    """Envia periodicamente os dados simulados para o cliente."""
    try:
        while True:
            dados = simula_dados()
            timestamp = incrementa_relogio_de_lamport()
            mensagem = f"{dados}|{timestamp}"
            conn.sendall(mensagem.encode())
            print(f"[Sensor {sensor_id}] Dados enviados: {mensagem}")
            time.sleep(5)
    except ConnectionResetError:
        print(f"[Sensor {sensor_id}] Cliente desconectado abruptamente")
    finally:
        conn.close()

def trata_conexao(conn, addr):
    print(f"[Sensor {sensor_id}] Conexão estabelecida com o cliente {addr}.")
    enviar_dados(conn)

# --- Implementação do Bully Algorithm via gRPC ---

class BullyServiceServicer(bully_pb2_grpc.BullyServiceServicer):
    def StartElection(self, request, context):
        """
        Método chamado por outro sensor para iniciar uma eleição.
        Se este sensor tiver id maior que o solicitante, envia um OK e inicia sua própria eleição.
        """
        global election_in_progress
        caller_id = request.sensor_id
        print(f"[Bully] Recebido pedido de eleição de '{caller_id}'")
        # Se meu ID for maior que o do solicitante, respondo com OK e, se não estiver em eleição, inicio minha eleição.
        if int(sensor_id.split('_')[-1]) > int(caller_id.split('_')[-1]):
            resposta = bully_pb2.ElectionResponse(ok=True, message="OK")
            # Se ainda não estou em eleição, inicio-a
            if not election_in_progress:
                election_in_progress = True
                threading.Thread(target=inicia_eleicao).start()
            return resposta
        else:
            # Se meu id for menor, não respondo com OK (ou pode responder False)
            return bully_pb2.ElectionResponse(ok=False, message="Meu id é menor")
    
    def AnnounceCoordinator(self, request, context):
        """
        Método para receber o anúncio do novo coordenador.
        """
        global coordinator_id, is_coordinator, election_in_progress
        coordinator_id = request.coordinator_id
        is_coordinator = (coordinator_id == sensor_id)
        election_in_progress = False
        print(f"[Bully] Novo coordenador anunciado: {coordinator_id}")
        return bully_pb2.ElectionResponse(ok=True, message="Coordenador recebido")

def inicia_bully_server(bully_port):
    """
    Inicializa o servidor gRPC para receber mensagens relacionadas ao Bully Algorithm.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    bully_pb2_grpc.add_BullyServiceServicer_to_server(BullyServiceServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{bully_port}")
    server.start()
    print(f"[Bully] Servidor Bully iniciado na porta {bully_port}")
    server.wait_for_termination()

def inicia_eleicao():
    """
    Função que inicia a eleição.
    Envia uma mensagem de ElectionRequest para todos os sensores com id maior.
    Se nenhum responder com OK, declara-se coordenador e anuncia a todos.
    """
    global election_in_progress, is_coordinator, coordinator_id
    print(f"[Bully] {sensor_id} iniciando eleição...")
    recebeu_ok = False
    
    # Percorre sensores conhecidos com id maior
    for s_id, (host, bully_port) in sensores_conhecidos.items():
        if int(s_id.split('_')[-1]) > int(sensor_id.split('_')[-1]):
            try:
                channel = grpc.insecure_channel(f"{host}:{bully_port}")
                stub = bully_pb2_grpc.BullyServiceStub(channel)
                req = bully_pb2.ElectionRequest(sensor_id=sensor_id)
                response = stub.StartElection(req, timeout=5)
                if response.ok:
                    print(f"[Bully] Recebi OK de {s_id}")
                    recebeu_ok = True
            except Exception as e:
                print(f"[Bully] Erro ao contactar {s_id}: {e}")
    
    if not recebeu_ok:
        # Se nenhum sensor com id maior respondeu, este sensor se declara coordenador
        is_coordinator = True
        coordinator_id = sensor_id
        print(f"[Bully] {sensor_id} se declara o novo coordenador!")
        anuncia_coordenador()
    else:
        # Se recebeu OK, espera o anúncio do coordenador
        print(f"[Bully] {sensor_id} aguardando anúncio do coordenador...")
        # Em uma implementação robusta, aguardaríamos um tempo e, se não recebermos o anúncio, reiniciaríamos a eleição.
        time.sleep(10)
        if coordinator_id is None:
            print(f"[Bully] Tempo esgotado sem anúncio de coordenador, reiniciando eleição...")
            inicia_eleicao()
    
    election_in_progress = False

def anuncia_coordenador():
    """
    Anuncia para todos os sensores conhecidos que este sensor é o coordenador.
    """
    for s_id, (host, bully_port) in sensores_conhecidos.items():
        if s_id == sensor_id:
            continue
        try:
            channel = grpc.insecure_channel(f"{host}:{bully_port}")
            stub = bully_pb2_grpc.BullyServiceStub(channel)
            notificacao = bully_pb2.CoordinatorNotification(coordinator_id=coordinator_id)
            response = stub.AnnounceCoordinator(notificacao, timeout=5)
            if response.ok:
                print(f"[Bully] {s_id} confirmou o novo coordenador")
        except Exception as e:
            print(f"[Bully] Erro ao anunciar para {s_id}: {e}")

# --- Fim da implementação do Bully ---

def main(porta=5000):
    global sensor_id, election_in_progress
    # Define o sensor_id baseado na porta
    sensor_id = f"sensor_{porta}"
    election_in_progress = False

    # Define a porta para o Bully gRPC (por exemplo, porta + 1)
    bully_port = porta + 1

    # Inicia a thread para envio de status para o monitor via gRPC
    status_thread = threading.Thread(target=envia_status_para_monitor, args=(sensor_id,))
    status_thread.daemon = True
    status_thread.start()

    # Inicia a thread do servidor gRPC para o Bully
    bully_server_thread = threading.Thread(target=inicia_bully_server, args=(bully_port,))
    bully_server_thread.daemon = True
    bully_server_thread.start()

    # Inicia o servidor TCP para aceitar conexões de clientes
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("0.0.0.0", porta))
    servidor.listen(1)
    print(f"[Sensor {sensor_id}] Servidor TCP iniciado na porta {porta}")
    
    # Opcional: após a inicialização, se este sensor for o de maior id conhecido, pode se declarar coordenador
    # (ou aguardar um timeout para disparar a eleição)
    threading.Timer(5, inicia_eleicao).start()

    while True:
        conn, addr = servidor.accept()
        thread = threading.Thread(target=trata_conexao, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    # Permite definir a porta via linha de comando; caso contrário, usa a porta 5000
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    main(porta)
