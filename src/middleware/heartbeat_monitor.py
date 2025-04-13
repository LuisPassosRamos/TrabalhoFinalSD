# src/middleware/heartbeat_monitor.py
import socket
import threading
import time
from falhas.eleicao import BullyElection
from nuvem import cloud  # nova import

class HeartbeatMonitor:
    def __init__(self, host='localhost', port=6000, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sensors = {}  # sensor_id : last heartbeat timestamp
        self.lock = threading.Lock()
        # Para a simulação: lista de todos os nós (IDs) conhecidos
        self.all_sensor_ids = [1, 2, 3, 4]  
        self.coordinator = None

    def listen(self):
        """Escuta mensagens de heartbeat via UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"Heartbeat Monitor rodando em {self.host}:{self.port}")
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode()
                if message.startswith("HEARTBEAT:"):
                    sensor_id = int(message.split(":")[1])
                    self.receive_heartbeat(sensor_id)
            except Exception as e:
                print(f"Erro recebendo heartbeat: {e}")

    def receive_heartbeat(self, sensor_id):
        with self.lock:
            self.sensors[sensor_id] = time.time()
            print(f"Heartbeat recebido do sensor {sensor_id}.")
            # Registra o evento de heartbeat no Cloud
            cloud.store_event("heartbeat", {"sensor_id": sensor_id, "timestamp": time.time()})

    def monitor(self):
        """Verifica periodicamente a disponibilidade dos sensores e inicia eleição se necessário."""
        while True:
            time.sleep(self.timeout)
            current_time = time.time()
            missing = []
            
            with self.lock:
                # Verifica cada sensor que já enviou heartbeat
                for sensor_id, last_hb in list(self.sensors.items()):
                    if current_time - last_hb > self.timeout:
                        msg = f"Sensor {sensor_id} inativo (último heartbeat há {current_time - last_hb:.1f}s)."
                        print(msg)
                        missing.append(sensor_id)
                        del self.sensors[sensor_id]
                        # Registra evento de falha no Cloud
                        cloud.store_event("failure", {
                            "sensor_id": sensor_id, 
                            "timestamp": current_time,
                            "msg": msg
                        })
            
            # Se o coordenador estiver inativo, inicia eleição
            if self.coordinator is None or self.coordinator in missing:
                print("Coordenador inativo detectado. Iniciando eleição (algoritmo Bully).")
                
                # Obtém lista de sensores ativos
                active_sensors = list(self.sensors.keys())
                if not active_sensors:
                    print("Não há sensores ativos para eleição.")
                    continue
                    
                # Inicia a eleição com o sensor de menor ID ativo
                election = BullyElection(node_id=min(active_sensors), nodes=self.all_sensor_ids)
                election.start_election()
                self.coordinator = election.coordinator
                
                # Registra o resultado da eleição no Cloud
                cloud.store_event("coordinator_election", {
                    "new_coordinator": self.coordinator,
                    "active_nodes": active_sensors,
                    "timestamp": time.time()
                })
                
                print(f"Novo coordenador definido: {self.coordinator}")

if __name__ == "__main__":
    monitor = HeartbeatMonitor(timeout=5)
    listener_thread = threading.Thread(target=monitor.listen, daemon=True)
    listener_thread.start()
    monitor_thread = threading.Thread(target=monitor.monitor, daemon=True)
    monitor_thread.start()
    # Mantém o monitor ativo
    while True:
        time.sleep(1)
