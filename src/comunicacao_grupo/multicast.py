# src/comunicacao_grupo/multicast.py
import socket
import struct
import threading
import time

# Configurações de Multicast
MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007

def multicast_sender(alert_message: str):
    """
    Envia uma mensagem de alerta para o grupo multicast.
    """
    # Cria socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Define o TTL (Time-to-live) para 1 (rede local)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
    
    try:
        sock.sendto(alert_message.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        print(f"Alert enviado: {alert_message}")
    except Exception as e:
        print("Erro ao enviar multicast:", e)
    finally:
        sock.close()

def multicast_receiver():
    """
    Recebe mensagens do grupo multicast e as exibe.
    """
    # Cria socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Permite que múltiplos sockets usem a mesma porta
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTICAST_PORT))
    
    # Adiciona o socket ao grupo multicast
    group = socket.inet_aton(MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    print(f"Recebendo mensagens multicast em {MULTICAST_GROUP}:{MULTICAST_PORT}")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(f"Mensagem multicast recebida de {addr}: {data.decode()}")
        except Exception as e:
            print("Erro no multicast receiver:", e)
            break

if __name__ == "__main__":
    # Inicia a thread do receiver e envia um alerta de teste
    receiver_thread = threading.Thread(target=multicast_receiver, daemon=True)
    receiver_thread.start()
    
    time.sleep(1)
    multicast_sender("Alerta climático: tempestade se aproximando!")
    
    # Mantém o script ativo para continuar recebendo mensagens
    while True:
        time.sleep(1)
