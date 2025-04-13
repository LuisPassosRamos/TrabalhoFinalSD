# src/falhas/heartbeat.py
import threading
import time

class HeartbeatMonitor:
    def __init__(self, timeout=5):
        self.sensors = {}  # sensor_id : last_heartbeat_time
        self.timeout = timeout
        self.lock = threading.Lock()

    def receive_heartbeat(self, sensor_id):
        """Atualiza o horário do último heartbeat recebido do sensor."""
        with self.lock:
            self.sensors[sensor_id] = time.time()
            print(f"Recebido heartbeat do sensor {sensor_id}")

    def monitor(self):
        """Executa periodicamente a verificação de sensores inativos."""
        while True:
            time.sleep(self.timeout)
            current_time = time.time()
            with self.lock:
                for sensor_id, last_hb in list(self.sensors.items()):
                    if current_time - last_hb > self.timeout:
                        print(f"Sensor {sensor_id} parece inativo (último heartbeat há {current_time - last_hb:.1f}s).")
                        del self.sensors[sensor_id]

# Exemplo de uso:
if __name__ == "__main__":
    monitor = HeartbeatMonitor(timeout=3)

    # Simulação de recebimento de heartbeats
    def simulate_heartbeat(sensor_id, interval, monitor_obj):
        while True:
            monitor_obj.receive_heartbeat(sensor_id)
            time.sleep(interval)

    # Inicia threads simulando sensores enviando heartbeat
    threading.Thread(target=simulate_heartbeat, args=("sensor1", 1, monitor), daemon=True).start()
    threading.Thread(target=simulate_heartbeat, args=("sensor2", 1, monitor), daemon=True).start()

    monitor.monitor()  # Bloco de monitoramento
