"""
Módulo de envio de alertas climáticos via UDP Multicast.

Responsabilidades:
- Enviar mensagens de alerta para um grupo multicast.
- Simular detecção de clima extremo.
"""

import socket
import struct
import time

# Endereço multicast e porta
MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007

def enviar_alerta(mensagem):
    """
    Envia uma mensagem de alerta para o grupo multicast.
    """
    # Cria um socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Define o TTL (Time to Live) para 1 para restringir a mensagem à rede local
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    try:
        sock.sendto(mensagem.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
        print(f"[Sensor Alert] Alerta enviado: {mensagem}")
    finally:
        sock.close()

def main():
    """
    Simula a detecção de clima extremo e envia alertas periodicamente.
    """
    while True:
        # Para exemplo, envia um alerta a cada 30 segundos
        alerta = "ALERTA: Condição climática extrema detectada!"
        enviar_alerta(alerta)
        time.sleep(30)

if __name__ == "__main__":
    # Ponto de entrada do alerta multicast
    main()
