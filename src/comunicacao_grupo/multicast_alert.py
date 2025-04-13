# Este módulo é utilizado exclusivamente para o envio de alertas críticos via multicast.a multicast.
import socket
import struct

MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007

def send_alert(alert_message: str) -> None:
    """
    Envia um alerta via multicast para o grupo.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Configura o TTL para 1 (rede local)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
    try:
        sock.sendto(alert_message.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        print(f"Alerta enviado: {alert_message}")
    except Exception as e:
        print("Erro ao enviar alerta:", e)
    finally:
        sock.close()

if __name__ == '__main__':
    # Exemplo de envio de alerta crítico
    send_alert("Alerta: condição crítica detectada!")
