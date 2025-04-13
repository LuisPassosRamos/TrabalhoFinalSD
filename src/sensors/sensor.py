# src/sensors/sensor.py
import socket
import threading
import time
import random  # Adicionado para simulação dos dados
from sincronizacao.lamport import LamportClock
from sincronizacao.snapshot import Snapshot
from seguranca import checkpoints  # Adicionado para integração de checkpoints e rollback
from nuvem import cloud  # Adicionado para integração com computação em nuvem
import datetime
import math

# Instanciando o clock de Lamport e o snapshot para este nó (node_id definido aqui como 1 para exemplo)
global_clock = LamportClock()
snapshot_instance = Snapshot(node_id=1)

# Adicionamos um lock para sincronizar os prints
print_lock = threading.Lock()
def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs, flush=True)

# Variável global para armazenar o sensor_id do processo
GLOBAL_SENSOR_ID = None

def heartbeat_sender(sensor_id, monitor_host='localhost', monitor_port=6000, interval=2):
    """
    Envia periodicamente o heartbeat para o monitor via UDP.
    """
    hb_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    retries = 0
    max_retries = 5
    
    while True:
        try:
            heartbeat_msg = f"HEARTBEAT:{sensor_id}"
            hb_socket.sendto(heartbeat_msg.encode(), (monitor_host, monitor_port))
            # Registramos o envio com o clock
            global_clock.tick()
            safe_print(f"[clock {global_clock.get_time()}] Enviado heartbeat: {heartbeat_msg} para {monitor_host}:{monitor_port}")
            # Reset contador de tentativas após sucesso
            retries = 0
        except Exception as e:
            retries += 1
            safe_print(f"Erro enviando heartbeat (tentativa {retries}/{max_retries}): {e}")
            # Se atingir o máximo de tentativas, registrar o problema no Cloud
            if retries >= max_retries:
                cloud.store_event("heartbeat_failure", {
                    "sensor_id": sensor_id,
                    "error": str(e),
                    "timestamp": time.time()
                })
                # Reset contador para continuar tentando
                retries = 0
        time.sleep(interval)

# Adicionamos função de auto-checkpoint para salvamento periódico do estado
def auto_checkpoint(sensor_id, interval=15):
    import time
    while True:
        time.sleep(interval)
        from seguranca import checkpoints  # Importa localmente para garantir atualização
        checkpoints.save_checkpoint({"sensor": sensor_id, "clock": global_clock.get_time()})
        safe_print(f"[clock {global_clock.get_time()}] Auto-checkpoint salvo para sensor {sensor_id}")

def auto_snapshot(sensor_id, interval=30):
    """
    Captura periodicamente o snapshot global do sensor e envia para o Cloud.
    """
    while True:
        time.sleep(interval)
        snapshot_instance.start_snapshot()
        time.sleep(1)  # Simula o delay da captura
        snapshot_instance.complete_snapshot()
        safe_print(f"[clock {global_clock.get_time()}] Auto-snapshot realizado para sensor {sensor_id}")
        cloud.push_data(f"Auto-snapshot do sensor {sensor_id}: {snapshot_instance.local_state}")

# Adiciona simulação mais realista de dados climáticos
def simulate_weather_data(sensor_id):
    """Gera dados climáticos simulados mais realistas"""
    # Base de simulação com variação por sensor
    base_temp = 20.0 + (sensor_id * 1.5)
    base_humidity = 50.0 - (sensor_id * 2.0)
    base_pressure = 1013.0 + (sensor_id * 0.7)
    
    # Adicionando variação temporal
    hour_variation = datetime.datetime.now().hour / 24.0
    
    # Simula variação de temperatura ao longo do dia
    temp = base_temp + (5 * math.sin(hour_variation * 2 * math.pi)) + random.uniform(-1.0, 1.0)
    
    # Simula variação de umidade inversa à temperatura
    humidity = base_humidity - (10 * math.sin(hour_variation * 2 * math.pi)) + random.uniform(-5.0, 5.0)
    humidity = max(30, min(90, humidity))  # Mantém entre 30% e 90%
    
    # Pressão varia menos
    pressure = base_pressure + random.uniform(-2.0, 2.0)
    
    # Gera alerta se condições extremas
    alert = False
    alert_msg = ""
    if temp > 30.0:
        alert = True
        alert_msg = f"ALERTA: Temperatura alta ({temp:.1f}°C) no sensor {sensor_id}!"
    elif humidity > 85:
        alert = True
        alert_msg = f"ALERTA: Umidade elevada ({humidity:.1f}%) no sensor {sensor_id}!"
    
    return {
        "sensor_id": sensor_id,
        "temperature": round(temp, 1),
        "humidity": round(humidity, 1),
        "pressure": round(pressure, 1),
        "timestamp": time.time(),
        "alert": alert,
        "alert_msg": alert_msg
    }

def handle_client(conn, addr):
    safe_print(f"Conexão de {addr}")
    try:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    safe_print(f"Sem dados recebidos de {addr}; encerrando conexão.")
                    break

                # Registro do evento com o clock de Lamport
                global_clock.tick()
                mensagem = data.decode()
                safe_print(f"Recebido de {addr} [clock {global_clock.get_time()}]: {mensagem}")

                if mensagem.strip().upper() == "SNAPSHOT":
                    safe_print(f"[clock {global_clock.get_time()}] Iniciando snapshot global no nó {snapshot_instance.node_id}")
                    snapshot_instance.start_snapshot()
                    time.sleep(1)  # simulação de delay para captura
                    snapshot_instance.complete_snapshot()
                    resposta = f"Snapshot realizado no node {snapshot_instance.node_id} [clock {global_clock.tick()}]"
                    # Envia o estado do snapshot para o Cloud
                    cloud.push_data(f"Snapshot do sensor {snapshot_instance.node_id}: {snapshot_instance.local_state}")
                elif mensagem.strip().upper() == "CHECKPOINT":
                    checkpoints.save_checkpoint({"sensor": snapshot_instance.node_id, "clock": global_clock.get_time()})
                    resposta = f"Checkpoint salvo no sensor {snapshot_instance.node_id}."
                elif mensagem.strip().upper() == "ROLLBACK":
                    restored_state = checkpoints.rollback()
                    resposta = f"Rollback realizado. Estado restaurado: {restored_state}"
                    cloud.push_data(f"Rollback no sensor {snapshot_instance.node_id}: {restored_state}")
                elif mensagem.startswith("Dados de leitura"):
                    # Simulação de dados climáticos mais realistas
                    weather_data = simulate_weather_data(GLOBAL_SENSOR_ID)
                    
                    # Formata a resposta
                    resposta = f"Sensor data -> Temp: {weather_data['temperature']}, Hum: {weather_data['humidity']}, Press: {weather_data['pressure']} [clock {global_clock.tick()}]"
                    
                    # Envia alerta multicast se condição crítica
                    if weather_data["alert"]:
                        from comunicacao_grupo import multicast_alert
                        multicast_alert.send_alert(weather_data["alert_msg"])
                    
                    # Replica e envia para o cloud
                    from falhas import replicador
                    replicador.save_message_replication({
                        "id": global_clock.get_time(), 
                        "data": resposta,
                        "raw_data": weather_data
                    })
                    cloud.push_data(resposta)
                    cloud.store_event("sensor_reading", weather_data)
                else:
                    resposta = f"ACK [clock {global_clock.tick()}]"

                # Envia a resposta usando o módulo exclusivo para alertas multicast
                from comunicacao_grupo import multicast_alert
                multicast_alert.send_alert(resposta)
                # Opcional: replicar e enviar para a nuvem, se necessário
                if resposta.startswith("Sensor data"):
                    from falhas import replicador
                    replicador.save_message_replication({"id": global_clock.get_time(), "data": resposta})
                    cloud.push_data(resposta)
            except socket.error as e:
                safe_print(f"Erro na comunicação com {addr}: {e}")
                break
    finally:
        conn.close()
        safe_print(f"Conexão encerrada: {addr}")

# NOVA FUNÇÃO: Servidor gRPC com porta parametrizada
def iniciar_grpc_server(grpc_port):
    from concurrent import futures
    import grpc
    from middleware import sensor_pb2, sensor_pb2_grpc
    class SensorServiceServicer(sensor_pb2_grpc.SensorServiceServicer):
        def GetSensorData(self, request, context):
            response = sensor_pb2.SensorResponse(
                temperatura=25.3,
                umidade=60.5,
                pressao=1013.25
            )
            return response
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(SensorServiceServicer(), server)
    server.add_insecure_port(f"[::]:{grpc_port}")
    safe_print(f"Servidor gRPC rodando na porta {grpc_port}...")
    server.start()
    server.wait_for_termination()

# MODIFICAÇÃO NA FUNÇÃO iniciar_servidor:
def iniciar_servidor(host='localhost', tcp_port=5000, sensor_id=1, grpc_port=7001, multicast_group="239.0.0.1", monitor_host="monitor"):
    global GLOBAL_SENSOR_ID
    GLOBAL_SENSOR_ID = sensor_id
    from seguranca import checkpoints
    # Restaurar estado do sensor a partir do último checkpoint, se disponível
    saved_state = checkpoints.load_checkpoint()
    if saved_state and "clock" in saved_state:
        global_clock.time = saved_state["clock"]
        safe_print(f"Sensor {sensor_id}: Estado restaurado com clock = {global_clock.get_time()}")
    threading.Thread(target=auto_checkpoint, args=(sensor_id,), daemon=True).start()
    threading.Thread(target=auto_snapshot, args=(sensor_id,), daemon=True).start()
    hb_thread = threading.Thread(target=heartbeat_sender, 
                                args=(sensor_id, monitor_host, 6000), 
                                daemon=True)
    hb_thread.start()

    # Inicia o servidor gRPC na porta configurada em uma nova thread
    grpc_thread = threading.Thread(target=iniciar_grpc_server, args=(grpc_port,), daemon=True)
    grpc_thread.start()

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((host, tcp_port))
        server.listen(5)
        safe_print(f"Servidor TCP rodando em {host}:{tcp_port}")
    except socket.error as e:
        safe_print(f"Erro ao inicializar o servidor TCP: {e}")
        return

    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except socket.error as e:
            safe_print(f"Erro ao aceitar conexão: {e}")

if __name__ == "__main__":
    iniciar_servidor()
