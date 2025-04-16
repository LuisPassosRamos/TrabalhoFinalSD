"""
Módulo principal do Cliente do sistema SISD.

Responsabilidades:
- Conectar-se aos sensores via TCP e receber dados climáticos.
- Orquestrar snapshots globais e enviar marcadores para os sensores.
- Implementar checkpoint/rollback (snapshots) para tolerância a falhas.
- Replicar logs para o serviço cloud.
- Participar do Token Ring (envio inicial do token).
- Autenticar sensores usando criptografia assimétrica (RSA).
"""

import socket
import threading
import time
import json
import os
import requests
import glob
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

# Inicializa o relógio de Lamport e um lock para ele
relogio_de_lamport = 0
relogio_lock = threading.Lock()

# Diretórios para snapshots e logs
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "client_log.json")
# Garante que o arquivo de log existe
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        json.dump([], f, indent=4)

def criar_snapshot_local():
    """
    Cria um snapshot do estado atual do cliente.
    """
    snapshot = {
        "id": "cliente",
        "timestamp": time.time(),
        "lamport_clock": relogio_de_lamport
    }
    nome_arquivo = os.path.join(SNAPSHOT_DIR, f"snapshot_cliente_{int(time.time())}.json")
    with open(nome_arquivo, "w") as f:
        json.dump(snapshot, f, indent=4)
    print(f"[Cliente] Snapshot local criado: {nome_arquivo}")

def registrar_mensagem(id, mensagem):
    """
    Registra uma mensagem no log local e replica para a nuvem.
    """
    log_entry = {
        "id": id,
        "timestamp": time.time(),
        "mensagem": mensagem
    }

    # Se o arquivo não existir, cria um novo com uma lista vazia
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f, indent=4)

    # Adiciona a nova entrada ao arquivo
    with open(LOG_FILE, "r+") as f:
        logs = json.load(f)
        logs.append(log_entry)
        f.seek(0)
        json.dump(logs, f, indent=4)
        f.truncate()  # <-- ESSA LINHA É FUNDAMENTAL

    # Replica para a nuvem
    replica_para_cloud(log_entry)

def enviar_mensagens(sensores):
    """
    Envia marcadores de snapshot para todos os sensores.
    """
    novo_clock = incrementa_relogio_de_lamport()
    marcador = f"MARKER|{novo_clock}"
    print(f"[Cliente] Enviando marcador: {marcador}")

    for sensor in sensores:
        host = sensor["host"]
        porta_base = sensor["porta"]
        # Considerando que o servidor de snapshot nos sensores está na porta (porta_base + 1000)
        porta_marker = porta_base + 1000
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, porta_marker))
            s.sendall(marcador.encode())
            print(f"[Cliente] Marcador enviado para {host}:{porta_marker}")
            mensagem = f"[Cliente] Marcador enviado para {host}:{porta_marker}"
            registrar_mensagem("client", mensagem)
        except Exception as e:
            print(f"[Cliente] Erro ao enviar marcador para {host}:{porta_marker}: {e}")

        finally:
            s.close()

def snapshot_global_periodico(sensores):
    """
    Periodicamente cria snapshot local e envia marcadores para os sensores.
    """
    while True:
        # Cria o snapshot local do cliente
        criar_snapshot_local()
        # Envia os marcadores para os sensores
        enviar_mensagens(sensores)
        time.sleep(10)

def atualizar_relogio_de_lamport(timestamp_recebido):
    """
    Atualiza o relógio de Lamport com base em timestamp recebido.
    """
    global relogio_de_lamport
    with relogio_lock:
        relogio_de_lamport = max(relogio_de_lamport, timestamp_recebido) + 1
        print(f"[Cliente] Atualizado relógio de Lamport: {relogio_de_lamport}")

def incrementa_relogio_de_lamport():
    """
    Incrementa o relógio de Lamport.
    """
    global relogio_de_lamport
    with relogio_lock:
        relogio_de_lamport += 1
        print(f"[Cliente] Relógio de Lamport incrementado: {relogio_de_lamport}")
        return relogio_de_lamport

def receber_dados(s, host, porta):
    """
    Recebe dados do sensor enquanto a conexão estiver ativa.
    """
    try:
        while True:
            dados = s.recv(1024)
            if not dados:
                break
            mensagem = dados.decode()
            partes = mensagem.split("|")
            if len(partes) == 2:
                dados_climaticos = partes[0]
                try:
                    sensor_timestamp = int(partes[1])
                except ValueError:
                    sensor_timestamp = None
            else:
                dados_climaticos = mensagem
                sensor_timestamp = None

            print(f"[Cliente] Dados recebidos de {host}:{porta} -> {dados_climaticos}")
            registrar_mensagem(f"{host}:{porta}", dados_climaticos)
            
            if sensor_timestamp is not None:
                atualizar_relogio_de_lamport(sensor_timestamp)
            else:
                incrementa_relogio_de_lamport()
    except Exception as e:
        print(f"[Cliente] Erro ao receber dados de {host}:{porta}: {e}")

def conecta_sensor(host, porta):
    """
    Estabelece conexão com o sensor e chama o método de receber dados.
    """
    while True:
        try:
            print(f"[Cliente] Tentando conectar a {host}:{porta} ...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, porta))
            print(f"[Cliente] Conectado ao sensor {host}:{porta}")
            receber_dados(s, host, porta)
        except Exception as e:
            print(f"[Cliente] Erro ao conectar-se a {host}:{porta}: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)  # Aguarda 5 segundos antes de tentar novamente
        finally:
            try:
                s.close()
            except Exception:
                pass

def enviar_token_para_maior_id(sensores):
    """
    Envia o token para o sensor com maior ID (porta).
    """
    # Determina o servidor com o maior ID
    maior_sensor = max(sensores, key=lambda sensor: sensor["porta"])
    host = maior_sensor["host"]
    porta_base = maior_sensor["porta"]
    token_port = porta_base + 2000  # Porta para o token

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, token_port))
        s.sendall("TOKEN".encode())
        print(f"[Cliente] Token enviado para {host}:{token_port}")
        mensagem = f"[Cliente] Token enviado para {host}:{token_port}"
        registrar_mensagem("client", mensagem)
    except Exception as e:
        print(f"[Cliente] Erro ao enviar token para {host}:{token_port}: {e}")
    finally:
        s.close()

def replica_para_cloud(log_entry):
    """
    Replica uma entrada de log para o serviço cloud.
    """
    try:
        requests.post("http://cloud:6000/replica", json=log_entry, timeout=2)
    except Exception as e:
        print(f"[Cloud] Falha ao replicar para nuvem: {e}")

def restaurar_estado_do_ultimo_snapshot():
    """
    Restaura o estado do cliente a partir do último snapshot salvo.
    """
    global relogio_de_lamport
    arquivos = glob.glob(os.path.join(SNAPSHOT_DIR, "snapshot_cliente_*.json"))
    if not arquivos:
        print("[Cliente] Nenhum snapshot encontrado para restaurar.")
        return
    ultimo_snapshot = max(arquivos, key=os.path.getmtime)
    with open(ultimo_snapshot, "r") as f:
        snapshot = json.load(f)
        relogio_de_lamport = snapshot.get("lamport_clock", 0)
    print(f"[Cliente] Estado restaurado do snapshot: {ultimo_snapshot} (Lamport={relogio_de_lamport})")

def load_sensor_public_key(pub_path):
    """
    Carrega a chave pública do sensor.
    """
    with open(pub_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def autentica_com_sensor(sock, sensor_pubkey):
    """
    Autentica o sensor usando criptografia assimétrica.
    """
    segredo = os.urandom(16)
    segredo_cifrado = sensor_pubkey.encrypt(
        segredo,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    sock.sendall(segredo_cifrado)
    resposta = sock.recv(256)
    if resposta == segredo:
        print("[Cliente] Sensor autenticado com sucesso!")
        return True
    else:
        print("[Cliente] Falha na autenticação do sensor.")
        return False

def main():
    """
    Função principal do cliente: inicializa threads, conexões e snapshots.
    """
    restaurar_estado_do_ultimo_snapshot()
    # Sensores disponíveis (nomes de host e porta para conexão de dados)
    sensores = [
        {"host": "sensor1", "porta": 5000},
        {"host": "sensor2", "porta": 5001},
        {"host": "sensor3", "porta": 5002},
    ]

    # Inicia threads para conectar aos sensores e receber dados
    for sensor in sensores:
        t = threading.Thread(target=conecta_sensor, args=(sensor["host"], sensor["porta"]))
        t.daemon = True
        t.start()

    # Inicia thread para o snapshot global com envio de marcadores
    t_snapshot = threading.Thread(target=snapshot_global_periodico, args=(sensores,))
    t_snapshot.daemon = True
    t_snapshot.start()

    # Envia o token para o servidor com o maior ID
    time.sleep(10)  # Aguarda um tempo para garantir que os sensores estejam prontos
    enviar_token_para_maior_id(sensores)

    # Mantém o main vivo
    while True:
        time.sleep(1)

if __name__ == "__main__":
    # Ponto de entrada do cliente
    main()
