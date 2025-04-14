# src\client\client.py

import socket
import threading
import time

def enviar_heartbeat():
    # TODO: Implementar o envio de heartbeat para o servidor enviar mensagens com o status do sensor para o monitor via gRPC
    pass

def receber_dados(s, host, porta):
    """Recebe dados do sensor enquanto a conexão estiver ativa."""
    try:
        while True:
            dados = s.recv(1024)
            if not dados:
                break
            print(f"[Cliente] Dados recebidos de {host}:{porta} -> {dados.decode()}")
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
