import os
import json
import threading
import time
import socket
import struct
import argparse
from sincronizacao.lamport import LamportClock
from comunicacao_grupo import multicast
from nuvem import cloud

# Variáveis globais para armazenar o estado do cliente
client_state = {"sent": [], "received": [], "alerts": []}
CHECKPOINT_FILE_CLIENT = "client_checkpoint.json"  # alterado para JSON
client_clock = LamportClock()

def load_client_checkpoint():
    """Carrega o último checkpoint do cliente salvo localmente"""
    if os.path.exists(CHECKPOINT_FILE_CLIENT):
        with open(CHECKPOINT_FILE_CLIENT, "r") as f:
            state = json.load(f)
        print("Estado do cliente restaurado:", state)
        return state
    else:
        print("Nenhum checkpoint do cliente encontrado.")
        return {"sent": [], "received": [], "alerts": []}

def checkpoint_client():
    """Thread que periodicamente salva o estado do cliente como checkpoint"""
    while True:
        time.sleep(20)  # intervalo de checkpoint (20 segundos)
        with open(CHECKPOINT_FILE_CLIENT, "w") as f:
            json.dump(client_state, f, indent=2)
        print(f"[{time.strftime('%H:%M:%S')}] Checkpoint do cliente salvo.")
        # Replicação do estado no Cloud para recuperação
        cloud.push_data(f"Cliente checkpoint: {client_state}")
        # Registra evento de checkpoint no cloud
        cloud.store_event("client_checkpoint", {
            "state": client_state,
            "timestamp": time.time()
        })

def conectar_ao_servidor(host='localhost', port=5003, cmd="Dados de leitura do sensor"):
    """Conecta ao servidor de sensor via TCP e solicita dados"""
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                send_time = client_clock.tick()
                mensagem = f"{cmd}; timestamp={send_time}"
                s.send(mensagem.encode())
                client_state["sent"].append(mensagem)
                print(f"[clock {client_clock.get_time()}] Enviado: {mensagem}")
                
                data = s.recv(1024)
                client_clock.tick()
                resposta = data.decode()
                client_state["received"].append(resposta)
                print(f"[clock {client_clock.get_time()}] Recebido: {resposta}")
                break
        except socket.error as e:
            print(f"Erro ao conectar com o servidor: {e}. Tentando novamente em 3 segundos...")
            time.sleep(3)

def process_multicast_alert(message):
    """Processa alertas recebidos via multicast"""
    print(f"[ALERTA] {message}")
    # Registra o alerta recebido
    client_state["alerts"].append({
        "message": message,
        "timestamp": time.time()
    })
    # Salva no Cloud
    cloud.store_event("client_alert", {
        "message": message,
        "client_clock": client_clock.get_time(),
        "timestamp": time.time()
    })

def start_multicast_receiver():
    """Inicia receptor de multicast em thread separada"""
    def receiver_thread():
        print("Iniciando receptor multicast para alertas climáticos...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 5007))
        
        group = socket.inet_aton('224.1.1.1')
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                alert = data.decode()
                process_multicast_alert(alert)
            except Exception as e:
                print(f"Erro no receptor multicast: {e}")
    
    threading.Thread(target=receiver_thread, daemon=True).start()

def register_with_monitor(client_id="client1", monitor_host='monitor', monitor_port=6000):
    """
    Registra o cliente com o monitor de heartbeat para ser monitorado
    """
    def send_heartbeats():
        hb_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while True:
            try:
                heartbeat_msg = f"HEARTBEAT:{client_id}"
                hb_socket.sendto(heartbeat_msg.encode(), (monitor_host, monitor_port))
                print(f"[clock {client_clock.get_time()}] Enviado heartbeat do cliente")
            except Exception as e:
                print(f"Erro enviando heartbeat do cliente: {e}")
            time.sleep(2)  # Frequência do heartbeat
    
    # Inicia thread para enviar heartbeats
    threading.Thread(target=send_heartbeats, daemon=True).start()

def main() -> None:
    print("Iniciando cliente principal...")
    
    # Inicia o sistema de checkpoint do cliente
    threading.Thread(target=checkpoint_client, daemon=True).start()
    
    # Carrega o estado anterior, se existir
    global client_state
    client_state = load_client_checkpoint()
    
    # Registra o cliente no monitor para ser monitorado
    register_with_monitor()
    
    # Iniciar receptor multicast em nova thread
    start_multicast_receiver()
    
    # Conecta a todos os sensores conhecidos
    sensors = [
        {"host": "sensor1", "port": 5000},
        {"host": "sensor2", "port": 5001},
        {"host": "sensor3", "port": 5002}
    ]
    
    # Loop para leitura periódica dos sensores
    while True:
        for sensor in sensors:
            try:
                conectar_ao_servidor(host=sensor["host"], port=sensor["port"])
            except Exception as e:
                print(f"Erro ao conectar com {sensor['host']}:{sensor['port']} - {e}")
        time.sleep(5)  # Pausa entre leituras

if __name__ == "__main__":
    main()