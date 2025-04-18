"""
Módulo principal do Sensor do sistema distribuído SISD.

Responsabilidades:
- Simulação de dados climáticos e envio ao cliente via TCP.
- Implementação de checkpoint/rollback (snapshots) para tolerância a falhas.
- Replicação de logs para o serviço cloud.
- Exclusão mútua via Token Ring.
- Eleição de coordenador via algoritmo Bully (gRPC).
- Envio de status (heartbeat) ao monitor via gRPC.
- Autenticação do cliente usando criptografia assimétrica (RSA).
"""

import socket
import threading
import time
import os
import json
import random
import sys
import grpc
from concurrent import futures
from middleware.protos import sensor_status_pb2
from middleware.protos import sensor_status_pb2_grpc
from middleware.protos import bully_pb2
from middleware.protos import bully_pb2_grpc
import requests
import glob
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# Diretórios para snapshots e logs
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

def inicializa_log(sensor_id):
    """
    Inicializa o arquivo de log do sensor.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    log_file = os.path.join(LOG_DIR, f"{sensor_id}_log.json")
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            json.dump([], f, indent=4)
    return log_file

def registrar_mensagem_log(sensor_id, sender_id, mensagem):
    """
    Registra uma mensagem no log local e replica para a nuvem.
    """
    log_file = os.path.join(LOG_DIR, f"{sensor_id}_log.json")
    log_entry = {
        "id": sender_id,
        "timestamp": time.time(),
        "mensagem": mensagem
    }
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            json.dump([], f, indent=4)
    with open(log_file, "r+") as f:
        logs = json.load(f)
        logs.append(log_entry)
        f.seek(0)
        json.dump(logs, f, indent=4)
        f.truncate()  # <-- ESSA LINHA É FUNDAMENTAL
    replica_para_cloud(log_entry)

def replica_para_cloud(log_entry):
    """
    Replica uma entrada de log para o serviço cloud.
    """
    try:
        requests.post("http://cloud:6000/replica", json=log_entry, timeout=2)
    except Exception as e:
        print(f"[Cloud] Falha ao replicar para nuvem: {e}")

def criar_snapshot_local_sensor():
    """
    Cria um snapshot do estado atual do sensor.
    """
    snapshot = {
        "id": sensor_id,
        "timestamp": time.time(),
        "lamport_clock": relogio_de_lamport
    }
    nome_arquivo = os.path.join(SNAPSHOT_DIR, f"snapshot_{sensor_id}_{int(time.time())}.json")
    with open(nome_arquivo, "w") as f:
        json.dump(snapshot, f, indent=4)
    print(f"[Sensor] Snapshot criado: {nome_arquivo}")

def restaurar_estado_do_ultimo_snapshot():
    """
    Restaura o estado do sensor a partir do último snapshot salvo.
    """
    global relogio_de_lamport
    arquivos = glob.glob(os.path.join(SNAPSHOT_DIR, f"snapshot_{sensor_id}_*.json"))
    if not arquivos:
        print("[Sensor] Nenhum snapshot encontrado para restaurar.")
        return
    ultimo_snapshot = max(arquivos, key=os.path.getmtime)
    with open(ultimo_snapshot, "r") as f:
        snapshot = json.load(f)
        relogio_de_lamport = snapshot.get("lamport_clock", 0)
    print(f"[Sensor] Estado restaurado do snapshot: {ultimo_snapshot} (Lamport={relogio_de_lamport})")

# --- Marker Listener (para snapshots globais) ---
def marker_listener(marker_port):
    """
    Escuta por marcadores enviados pelo cliente para iniciar snapshots.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", marker_port))
    server.listen(5)
    print(f"[Sensor] Servidor de snapshot iniciado na porta {marker_port}")
    while True:
        conn, addr = server.accept()
        try:
            data = conn.recv(1024)
            if data:
                mensagem = data.decode().strip()
                registrar_mensagem_log(sensor_id,"client", mensagem)
                if mensagem.startswith("MARKER"):
                    partes = mensagem.split("|")
                    if len(partes) == 2:
                        try:
                            marcador_clock = int(partes[1])
                        except ValueError:
                            marcador_clock = None
                        print(f"[Sensor] Marcador recebido com clock {marcador_clock}")
                        incrementa_relogio_de_lamport()
                        criar_snapshot_local_sensor()
            conn.close()
        except Exception as e:
            print(f"[Sensor] Erro no marker listener: {e}")
            conn.close()

def inicia_marker_listener(porta_base):
    """
    Inicia a thread que escuta por marcadores de snapshot.
    """
    marker_port = porta_base + 1000
    t = threading.Thread(target=marker_listener, args=(marker_port,))
    t.daemon = True
    t.start()

# --- Token Ring para exclusão mútua distribuída ---
has_token = False  # Indica se este nó possui o token

def start_token_listener(token_port):
    """
    Thread que escuta a chegada do token via TCP.
    """
    global has_token
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", token_port))
    server.listen(5)
    print(f"[Token] Sensor {sensor_id} escutando token na porta {token_port}")
    while True:
        conn, addr = server.accept()
        token_message = conn.recv(1024).decode().strip()
        if token_message == "TOKEN":
            print(f"[Token] Sensor {sensor_id} recebeu o token")
            has_token = True
        conn.close()

def inicia_token_listener(porta_base):
    """
    Inicia a thread que escuta o token.
    """
    token_port = porta_base + 2000
    t = threading.Thread(target=start_token_listener, args=(token_port,))
    t.daemon = True
    t.start()

def get_next_sensor():
    """
    Determina o próximo sensor no anel lógico para passagem do token.
    """
    sensor_ids = sorted(sensores_conhecidos.keys())
    idx = sensor_ids.index(sensor_id)
    next_idx = (idx + 1) % len(sensor_ids)
    next_sensor_id = sensor_ids[next_idx]
    next_sensor_host, _ = sensores_conhecidos[next_sensor_id]
    # Para token, supomos que o sensor utiliza: base_port (extraído do id) + 2000
    next_token_port = int(next_sensor_id.split("_")[-1]) + 2000
    return next_sensor_host, next_token_port

def pass_token():
    """
    Envia o token para o próximo sensor no anel.
    Só envia o token se houver uma conexão ativa com o cliente.
    """
    global has_token

    # Verifica se há uma conexão ativa com o cliente
    if not has_token:
        print(f"[Token] Sensor {sensor_id} não possui o token. Aguardando...")
        return

    next_sensor_host, next_token_port = get_next_sensor()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((next_sensor_host, next_token_port))
        s.sendall("TOKEN".encode())
        print(f"[Token] Sensor {sensor_id} passou o token para {next_sensor_host}:{next_token_port}")
    except Exception as e:
        print(f"[Token] Erro ao passar o token: {e}")
    finally:
        s.close()
        has_token = False

# --- Variáveis e funções para Bully e status ---
sensor_id = None        
is_coordinator = False  
coordinator_id = None   
election_in_progress = False

# Dicionário de sensores conhecidos (id: (host, porta_bully))
sensores_conhecidos = {
    "sensor_5000": ("sensor1", 5001),
    "sensor_5001": ("sensor2", 5002),
    "sensor_5002": ("sensor3", 5003)
}

relogio_de_lamport = 0
lamport_lock = threading.Lock()

def incrementa_relogio_de_lamport():
    """
    Incrementa o relógio lógico de Lamport.
    """
    global relogio_de_lamport
    with lamport_lock:
        relogio_de_lamport += 1
        print(f"[Sensor] Relógio de Lamport incrementado: {relogio_de_lamport}")
        return relogio_de_lamport

def envia_status_para_monitor(sensor_id, monitor_host="monitor", monitor_port=50051):
    """
    Envia periodicamente status do sensor ao monitor via gRPC.
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
            print(f"[Sensor] Status enviado para o monitor: {status_msg} com timestamp {timestamp}")
        except Exception as e:
            print(f"[Sensor] Erro ao enviar status para o monitor: {e}")
        time.sleep(10)

def simula_dados():
    """
    Simula dados climáticos (temperatura, umidade, pressão).
    """
    temperatura = round(random.uniform(15.0, 35.0), 1)
    umidade = round(random.uniform(30.0, 80.0), 1)
    pressao = round(random.uniform(990.0, 1020.0), 1)
    return f"{temperatura},{umidade},{pressao}"

def enviar_dados(conn):
    """
    Envia dados ao cliente apenas se possuir o token.
    Após enviar, passa o token ao próximo sensor.
    """
    global has_token
    try:
        while True:
            if not has_token:
                # Se não possui o token, aguarda brevemente
                time.sleep(0.1)
                continue
            # Sensor tem o token – envia dados para o cliente
            dados = simula_dados()
            timestamp = incrementa_relogio_de_lamport()
            mensagem = f"{dados}|{timestamp}"
            conn.sendall(mensagem.encode())
            print(f"[Sensor] Dados enviados: {mensagem}")
            registrar_mensagem_log(sensor_id, sensor_id,f"[Sensor] Dados enviados: {mensagem}")
            time.sleep(1)
            # Após enviar, passa o token para o próximo sensor
            pass_token()
    except ConnectionResetError:
        print(f"[Sensor] Cliente desconectado abruptamente")
    finally:
        conn.close()

def trata_conexao(conn, addr):
    """
    Trata uma nova conexão TCP do cliente.
    """
    print(f"[Sensor] Conexão estabelecida com o cliente {addr}.")
    autentica_cliente(conn)
    enviar_dados(conn)

def autentica_cliente(conn):
    """
    Autentica o cliente usando criptografia assimétrica.
    """
    segredo_cifrado = conn.recv(256)
    segredo = private_key.decrypt(
        segredo_cifrado,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    conn.sendall(segredo)
    # Após isso, conexão autenticada!

# --- Implementação do algoritmo Bully via gRPC ---
class BullyServiceServicer(bully_pb2_grpc.BullyServiceServicer):
    """
    Serviço gRPC para eleição Bully.
    """
    def StartElection(self, request, context):
        global election_in_progress
        caller_id = request.sensor_id
        print(f"[Bully] Recebido pedido de eleição de '{caller_id}'")
        if int(sensor_id.split('_')[-1]) > int(caller_id.split('_')[-1]):
            resposta = bully_pb2.ElectionResponse(ok=True, message="OK")
            if not election_in_progress:
                election_in_progress = True
                threading.Thread(target=inicia_eleicao).start()
            return resposta
        else:
            return bully_pb2.ElectionResponse(ok=False, message="Meu id é menor")
    
    def AnnounceCoordinator(self, request, context):
        global coordinator_id, is_coordinator, election_in_progress
        coordinator_id = request.coordinator_id
        is_coordinator = (coordinator_id == sensor_id)
        election_in_progress = False
        print(f"[Bully] Novo coordenador anunciado: {coordinator_id}")
        return bully_pb2.ElectionResponse(ok=True, message="Coordenador recebido")

def inicia_bully_server(bully_port):
    """
    Inicia o servidor gRPC para o algoritmo Bully.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    bully_pb2_grpc.add_BullyServiceServicer_to_server(BullyServiceServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{bully_port}")
    server.start()
    print(f"[Bully] Servidor Bully iniciado na porta {bully_port}")
    server.wait_for_termination()

def inicia_eleicao():
    """
    Inicia o processo de eleição Bully.
    """
    global election_in_progress, is_coordinator, coordinator_id
    print(f"[Bully] {sensor_id} iniciando eleição...")
    recebeu_ok = False
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
        is_coordinator = True
        coordinator_id = sensor_id
        print(f"[Bully] {sensor_id} se declara o novo coordenador!")
        anuncia_coordenador()
    else:
        print(f"[Bully] {sensor_id} aguardando anúncio do coordenador...")
        time.sleep(10)
        if coordinator_id is None:
            print(f"[Bully] Tempo esgotado sem anúncio de coordenador, reiniciando eleição...")
            inicia_eleicao()
    election_in_progress = False

def anuncia_coordenador():
    """
    Anuncia o novo coordenador para os demais sensores.
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

# --- Geração/carregamento das chaves RSA do sensor ---
def load_or_generate_keys():
    """
    Gera ou carrega as chaves RSA do sensor.
    """
    priv_path = os.path.join(os.path.dirname(__file__), "sensor_private.pem")
    pub_path = os.path.join(os.path.dirname(__file__), "sensor_public.pem")
    if os.path.exists(priv_path):
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    else:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(priv_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        with open(pub_path, "wb") as f:
            f.write(private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    return private_key

# Carrega as chaves ao iniciar o módulo
private_key = load_or_generate_keys()
public_key = private_key.public_key()

# --- Main ---
def main(porta=5000):
    """
    Função principal do sensor: inicializa módulos, threads e servidores.
    """
    global sensor_id, election_in_progress
    sensor_id = f"sensor_{porta}"
    election_in_progress = False

    restaurar_estado_do_ultimo_snapshot()

    # Inicializa o log ao iniciar o sensor
    inicializa_log(sensor_id)

    # Define a porta para o Bully gRPC (por exemplo, porta + 1)
    bully_port = porta + 1

    # Define a porta para o token
    token_port = porta + 2000

    # Inicia a thread para escutar o token
    token_thread = threading.Thread(target=start_token_listener, args=(token_port,))
    token_thread.daemon = True
    token_thread.start()

    # Inicia a thread para envio de status para o monitor via gRPC
    status_thread = threading.Thread(target=envia_status_para_monitor, args=(sensor_id,))
    status_thread.daemon = True
    status_thread.start()

    # Inicia o servidor TCP para aceitar conexões de clientes
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    servidor.bind(("0.0.0.0", porta))
    servidor.listen(5)
    print(f"[Sensor] Servidor TCP iniciado na porta {porta}")

    # Inicia o servidor que escuta por marcadores do cliente
    inicia_marker_listener(porta)

    while True:
        conn, addr = servidor.accept()
        thread = threading.Thread(target=trata_conexao, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    # Ponto de entrada do sensor
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    main(porta)
