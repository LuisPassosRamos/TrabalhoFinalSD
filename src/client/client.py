# src/client/client.py
import socket
import threading
import time
import json
import os

# Inicializa o relógio de Lamport e um lock para ele
relogio_de_lamport = 0
relogio_lock = threading.Lock()

# Pasta onde os snapshots do cliente serão armazenados
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
    Cria um snapshot do estado atual do cliente e salva em JSON.
    O snapshot inclui:
      - Identificador (neste caso "cliente")
      - Timestamp atual (time.time())
      - Valor do relógio de Lamport
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
    Registra uma mensagem no arquivo JSON de replicação de dados.
    :param id: Identificador do sensor ou cliente.
    :param mensagem: Mensagem a ser registrada.
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

def enviar_mensagens(sensores):
    """
    Envia um marcador para cada sensor. O marcador pode ser uma mensagem simples indicando
    que o sensor deve efetuar um snapshot. Antes de enviar, incrementa o relógio de Lamport.
    Cada sensor deverá estar escutando em uma porta específica para os marcadores (por exemplo, porta + 1000).
    
    :param sensores: lista de dicionários, e.g.,
       [{"host": "sensor1", "porta": 5000}, ...]
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
    """Função que a cada 10 segundos cria um snapshot global e envia marcadores para os sensores."""
    while True:
        # Cria o snapshot local do cliente
        criar_snapshot_local()
        # Envia os marcadores para os sensores
        enviar_mensagens(sensores)
        time.sleep(10)


def atualizar_relogio_de_lamport(timestamp_recebido):
    """Atualiza o relógio de Lamport com base no timestamp recebido."""
    global relogio_de_lamport
    with relogio_lock:
        relogio_de_lamport = max(relogio_de_lamport, timestamp_recebido) + 1
        print(f"[Cliente] Atualizado relógio de Lamport: {relogio_de_lamport}")

def incrementa_relogio_de_lamport():
    """Incrementa o relógio de Lamport se não houver timestamp recebido."""
    global relogio_de_lamport
    with relogio_lock:
        relogio_de_lamport += 1
        print(f"[Cliente] Relógio de Lamport incrementado: {relogio_de_lamport}")
        return relogio_de_lamport

def receber_dados(s, host, porta):
    """Recebe dados do sensor enquanto a conexão estiver ativa.
       Espera que os dados sejam enviados no formato: <dados>|<timestamp>
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
    """Estabelece conexão com o sensor e chama o método de receber dados."""
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
    Envia o token para o servidor com o maior ID.
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

def main():
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
    main()
