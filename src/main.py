import argparse
import threading
import time
import logging
import socket

# Importa os módulos desenvolvidos
from sensors import sensor as sensor_module
from client import client_main as client_module
from middleware import heartbeat_monitor
from comunicacao_grupo import multicast
from seguranca import autenticacao, criptografia, checkpoints
from falhas import replicacao, mutex  # novos imports para replicação e mutex

# Configuração básica do log
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

def run_sensor(args: argparse.Namespace) -> None:
    """
    Inicia o sensor, que executa o servidor TCP, a inscrição em multicast e o serviço gRPC.
    """
    logging.info(f"Iniciando sensor com ID {args.sensor_id} no host {args.host} em TCP na porta {args.tcp_port} e gRPC na porta {args.grpc_port}")
    sensor_module.iniciar_servidor(
        host=args.host,
        tcp_port=args.tcp_port,
        sensor_id=args.sensor_id,
        grpc_port=args.grpc_port,
        multicast_group=args.multicast_group
    )

def run_client(args: argparse.Namespace) -> None:
    """
    Inicia o cliente que se conecta ao servidor do sensor e utiliza a comunicação
    via Sockets e, possivelmente, os serviços gRPC.
    """
    logging.info(f"Iniciando cliente para se conectar em {args.host}:{args.port}")
    client_module.conectar_ao_servidor(host=args.host, port=args.port)

def run_multi_sensor(args: argparse.Namespace) -> None:
    """
    Inicia múltiplos sensores (servidores) em threads, com IDs e portas diferentes.
    """
    sensors_info = [
        {"sensor_id": 1, "port": 5000},
        {"sensor_id": 2, "port": 5001},
        {"sensor_id": 3, "port": 5002}  # Adicionado o terceiro sensor
    ]
    for info in sensors_info:
        threading.Thread(target=lambda: sensor_module.iniciar_servidor(
            host=args.host, port=info["port"], sensor_id=info["sensor_id"]),
            daemon=True).start()
        logging.info(f"Sensor {info['sensor_id']} iniciado na porta {info['port']}")
    while True:
        time.sleep(1)

def run_multi_client(args: argparse.Namespace) -> None:
    """
    Inicia múltiplos clientes, cada um conectando a um sensor diferente.
    """
    sensors_info = [
        {"port": 5000},
        {"port": 5001},
        {"port": 5002}  # Incluído para conectar no terceiro sensor
    ]
    def connect_sensor(port):
        client_module.conectar_ao_servidor(host=args.host, port=port)
    threads = []
    for info in sensors_info:
        t = threading.Thread(target=connect_sensor, args=(info["port"],))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

def run_monitor(args: argparse.Namespace) -> None:
    """
    Inicia o monitor de heartbeat, que escuta os sinais enviados pelos sensores e
    verifica a disponibilidade dos nós. Em caso de falha do coordenador, inicia a eleição.
    """
    logging.info("Iniciando monitor de heartbeats")
    monitor = heartbeat_monitor.HeartbeatMonitor(
        host=args.monitor_host, port=args.monitor_port, timeout=args.timeout)
    listener_thread = threading.Thread(target=monitor.listen, daemon=True)
    listener_thread.start()
    monitor_thread = threading.Thread(target=monitor.monitor, daemon=True)
    monitor_thread.start()
    while True:
        time.sleep(1)

def run_multicast_sender(args: argparse.Namespace) -> None:
    """
    Envia uma mensagem via multicast para alertar sensores e clientes sobre
    um alerta climático.
    """
    message = input("Digite a mensagem para enviar via multicast: ")
    multicast.multicast_sender(message)

def run_multicast_receiver(args: argparse.Namespace) -> None:
    """
    Inicia o receptor multicast que ficará escutando os alertas enviados.
    """
    multicast.multicast_receiver()

def run_authentication(args: argparse.Namespace) -> None:
    """
    Demonstra a autenticação simples.
    """
    username = args.user
    password = args.password
    if autenticacao.authenticate(username, password):
        token = autenticacao.generate_auth_token(username)
        logging.info("Autenticação realizada com sucesso.")
        logging.info(f"Token gerado: {token}")
    else:
        logging.error("Falha na autenticação!")

def run_crypto(args: argparse.Namespace) -> None:
    """
    Demonstra a criptografia RSA: gera as chaves, criptografa e descriptografa uma mensagem.
    """
    logging.info("Gerando par de chaves RSA...")
    private_key, public_key = criptografia.generate_rsa_keys()
    logging.info("Chave pública gerada:")
    logging.info(criptografia.serialize_public_key(public_key).decode())
    message = args.crypto_message
    ciphertext = criptografia.rsa_encrypt(public_key, message.encode())
    logging.info("Mensagem criptografada:")
    logging.info(ciphertext)
    decrypted = criptografia.rsa_decrypt(private_key, ciphertext)
    logging.info("Mensagem descriptografada:")
    logging.info(decrypted.decode())

def run_rollback(args: argparse.Namespace) -> None:
    """
    Testa o módulo de checkpoints e rollback.
    Primeiro, salva um estado exemplo e depois executa o rollback.
    """
    state_exemplo = {"sensor": "s1", "valor": 42, "timestamp": time.time()}
    checkpoints.save_checkpoint(state_exemplo)
    restored_state = checkpoints.rollback()
    print("Estado restaurado:", restored_state)

def run_replicate(args: argparse.Namespace) -> None:
    """
    Testa a replicação de dados.
    """
    sample_data = {"sensor": "s1", "valor": 42}
    nodes = [1, 2, 3, 4]
    replicacao.replicate_data(sample_data, nodes)

def run_mutex(args: argparse.Namespace) -> None:
    """
    Testa o mutex distribuído.
    """
    dm = mutex.DistributedMutex("recurso_teste")
    dm.acquire()
    print("Operação crítica simulada...")
    dm.release()

# NOVAS FUNÇÕES DE INTEGRAÇÃO
def run_grpc_client(args: argparse.Namespace) -> None:
    from middleware import grpc_client
    grpc_client.run()

def run_grpc_server(args: argparse.Namespace) -> None:
    from middleware import grpc_server
    grpc_server.serve()

def run_pyro_client(args: argparse.Namespace) -> None:
    from middleware import pyro_client
    pyro_client.main()

def run_pyro_server(args: argparse.Namespace) -> None:
    from middleware import pyro_server
    pyro_server.main()

# Adição do módulo de Computação em Nuvem
def run_cloud(args: argparse.Namespace) -> None:
    from nuvem import cloud
    threading.Thread(target=cloud.run_cloud_server, daemon=True).start()
    logging.info("Instância de Computação em Nuvem iniciada.")
    # Mantém o container ativo
    while True:
        time.sleep(1)

def run_show_checkpoint(args: argparse.Namespace) -> None:
    from nuvem import cloud
    data = cloud.get_latest_data()
    print("Último estado armazenado no Cloud:")
    print(data)

def run_all(args: argparse.Namespace) -> None:
    """
    Executa uma simulação integrada de todos os módulos do sistema.
    Inicia sensores, clientes, monitor, servidores gRPC/Pyro, replicação, mutex, rollback e Cloud.
    """
    logging.info("Iniciando simulação integrada de todos os módulos...")
    threading.Thread(target=run_multi_sensor, args=(args,), daemon=True).start()
    threading.Thread(target=run_multi_client, args=(args,), daemon=True).start()
    threading.Thread(target=run_monitor, args=(args,), daemon=True).start()
    threading.Thread(target=run_multicast_receiver, args=(args,), daemon=True).start()
    threading.Thread(target=run_grpc_server, args=(args,), daemon=True).start()
    threading.Thread(target=run_pyro_server, args=(args,), daemon=True).start()
    threading.Thread(target=run_replicate, args=(args,), daemon=True).start()
    threading.Thread(target=run_mutex, args=(args,), daemon=True).start()
    threading.Thread(target=run_rollback, args=(args,), daemon=True).start()
    threading.Thread(target=run_cloud, args=(args,), daemon=True).start()
    while True:
        time.sleep(1)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SISD - Sistema Integrado Simulado de Distribuição - Integração Geral dos Módulos"
    )
    parser.add_argument(
        "role",
        choices=["sensor", "client", "multi_sensor", "multi_client", "monitor", "multicast_sender", "multicast_receiver", "auth", "crypto", "rollback", "replicate", "mutex", "grpc_client", "grpc_server", "pyro_client", "pyro_server", "cloud", "show_checkpoint", "all"],
        help="Define o papel que o nó executará."
    )
    parser.add_argument("--sensor_id", type=int, default=1,
                        help="ID do sensor (apenas para o role 'sensor').")
    parser.add_argument("--host", default="localhost",
                        help="Hostname para os módulos de comunicação (sensor/cliente).")
    parser.add_argument("--port", type=int, default=5000,
                        help="Porta para comunicação via TCP/IP (sensor/cliente).")
    parser.add_argument("--monitor_host", default="localhost",
                        help="Hostname para o monitor de heartbeat.")
    parser.add_argument("--monitor_port", type=int, default=6000,
                        help="Porta para o monitor de heartbeat.")
    parser.add_argument("--timeout", type=int, default=5,
                        help="Timeout (em segundos) para detectar falhas no heartbeat.")
    # Novos argumentos para segurança (não interativos)
    parser.add_argument("--user", default="usuario1", help="Usuário para autenticação")
    parser.add_argument("--password", default="senha123", help="Senha para autenticação")
    parser.add_argument("--crypto_message", default="Mensagem de teste", help="Mensagem para criptografia")
    parser.add_argument("--tcp_port", type=int, default=5000,
                        help="Porta para o servidor TCP do sensor.")
    parser.add_argument("--grpc_port", type=int, default=7001,
                        help="Porta para o serviço gRPC do sensor.")
    parser.add_argument("--multicast_group", default="239.0.0.1",
                        help="Endereço do grupo multicast para alertas.")
    args = parser.parse_args()

    if args.role == "sensor":
        run_sensor(args)
    elif args.role == "client":
        run_client(args)
    elif args.role == "multi_sensor":
        run_multi_sensor(args)
    elif args.role == "multi_client":
        run_multi_client(args)
    elif args.role == "monitor":
        run_monitor(args)
    elif args.role == "multicast_sender":
        run_multicast_sender(args)
    elif args.role == "multicast_receiver":
        run_multicast_receiver(args)
    elif args.role == "auth":
        run_authentication(args)
    elif args.role == "crypto":
        run_crypto(args)
    elif args.role == "rollback":
        run_rollback(args)
    elif args.role == "replicate":
        run_replicate(args)
    elif args.role == "mutex":
        run_mutex(args)
    elif args.role == "grpc_client":
        run_grpc_client(args)
    elif args.role == "grpc_server":
        run_grpc_server(args)
    elif args.role == "pyro_client":
        run_pyro_client(args)
    elif args.role == "pyro_server":
        run_pyro_server(args)
    elif args.role == "cloud":
        run_cloud(args)
    elif args.role == "show_checkpoint":
        run_show_checkpoint(args)
    elif args.role == "all":
        run_all(args)
    else:
        logging.error("Role inválido!")

if __name__ == "__main__":
    main()
