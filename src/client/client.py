# src\client\client.py
import socket
import threading
import time

# Inicializa o relógio de Lamport e um lock para ele
relogio_de_lamport = 0
relogio_lock = threading.Lock()

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
            # Supondo que o sensor envia uma string no formato "valor1,valor2,valor3|timestamp"
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
            
            # Se o sensor enviou um timestamp, utiliza-o para atualizar o relógio de Lamport
            if sensor_timestamp is not None:
                atualizar_relogio_de_lamport(sensor_timestamp)
            else:
                # Se não houver timestamp, apenas incrementa o relógio
                incrementa_relogio_de_lamport()
    except Exception as e:
        print(f"[Cliente] Erro ao receber dados de {host}:{porta}: {e}")

def conecta_sensor(host, porta):
    """Estabelece conexão com o sensor e chama o método de receber dados."""
    while True:
        try:
            print(f"[Cliente] Conectando a {host}:{porta} ...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, porta))
            print(f"[Cliente] Conectado ao sensor {host}:{porta}")
            receber_dados(s, host, porta)  # Chama o método para receber dados
        except Exception as e:
            print(f"[Cliente] Erro ao conectar-se a {host}:{porta}: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)
        finally:
            s.close()

def main():
    # Considerando que os sensores serão disponibilizados via Docker com os nomes:
    sensores = [
        {"host": "sensor1", "porta": 5000},
        {"host": "sensor2", "porta": 5001},
        {"host": "sensor3", "porta": 5002},
    ]
    for sensor in sensores:
        t = threading.Thread(target=conecta_sensor, args=(sensor["host"], sensor["porta"]))
        t.daemon = True
        t.start()
    # Mantém o main vivo
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
