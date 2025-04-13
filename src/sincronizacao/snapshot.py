# src/sincronizacao/snapshot.py
import threading
import time

class Snapshot:
    def __init__(self, node_id):
        self.node_id = node_id
        self.local_state = {}
        self.recording = False
        self.lock = threading.Lock()
        self.channels_state = {}  # Estado dos canais
        self.markers_received = set()  # Rastreia marcadores recebidos

    def get_application_state(self):
        """
        Método que captura o estado da aplicação.
        Neste exemplo, simulamos com um dicionário simples.
        """
        return {"dummy_state": "valor_exemplo", "node": self.node_id}

    def start_snapshot(self):
        """Inicia o processo de snapshot, registrando o estado local."""
        with self.lock:
            try:
                print(f"Node {self.node_id}: Iniciando snapshot global")
                self.recording = True
                self.local_state = self.get_application_state()
                # Limpa o estado anterior dos canais e marcadores
                self.channels_state = {}
                self.markers_received = set()
                # Notifica o Cloud sobre o início do snapshot
                from nuvem import cloud
                # Certifique-se de que não há bloqueio entre locks diferentes
                self.lock.release()  
                try:
                    cloud.store_event("snapshot_started", {"node_id": self.node_id, "timestamp": time.time()})
                finally:
                    self.lock.acquire()  # Readquire o lock
            except Exception as e:
                print(f"Erro ao iniciar snapshot no nó {self.node_id}: {e}")
                import traceback
                print(traceback.format_exc())
                # Garante que o estado é consistente mesmo em caso de erro
                self.recording = True  # Mantém o estado de recording para que o processo continue

    def complete_snapshot(self):
        """Finaliza o processo de snapshot e exibe o estado capturado."""
        with self.lock:
            if not self.recording:
                return
                
            try:
                self.recording = False
                # Inclui estado dos canais no snapshot final
                full_state = {
                    "local_state": self.local_state,
                    "channels_state": self.channels_state,
                    "completion_time": time.time()
                }
                print(f"Node {self.node_id}: Snapshot completo: estado = {full_state}")
                
                # Armazena o snapshot completo no Cloud
                from nuvem import cloud
                # Libera o lock temporariamente para evitar deadlocks
                self.lock.release()
                try:
                    cloud.store_event("snapshot_completed", {
                        "node_id": self.node_id, 
                        "snapshot_data": full_state
                    })
                finally:
                    self.lock.acquire()  # Readquire o lock
            except Exception as e:
                print(f"Erro ao completar snapshot no nó {self.node_id}: {e}")
                import traceback
                print(traceback.format_exc())
                # Garante que o estado é consistente mesmo em caso de erro
                self.recording = False  # Garante que o snapshot é marcado como completo

    def receive_marker(self, from_node):
        """
        Processa o recebimento de um marcador de snapshot de outro nó.
        Implementa o algoritmo de Chandy-Lamport.
        """
        with self.lock:
            try:
                if not self.recording:
                    # Primeira vez recebendo um marcador - inicia snapshot
                    self.start_snapshot()
                    # Envia marcador para todos os outros nós (simulado)
                    print(f"Node {self.node_id}: Enviando marcadores para outros nós")
                
                # Marca o canal como vazio após receber o marcador
                self.markers_received.add(from_node)
                self.channels_state[from_node] = []
                print(f"Node {self.node_id}: Marcador recebido de {from_node}. Marcadores recebidos: {self.markers_received}")
                
                # Para um sistema com 3 nós (ids 1, 2, 3), cada nó deve receber marcadores dos outros 2 nós
                expected_markers = set([1, 2, 3]) - {self.node_id}
                if self.markers_received.issuperset(expected_markers):
                    print(f"Node {self.node_id}: Todos os marcadores recebidos. Completando snapshot.")
                    self.complete_snapshot()
                else:
                    print(f"Node {self.node_id}: Aguardando mais marcadores. Recebidos: {self.markers_received}, Esperados: {expected_markers}")
            except Exception as e:
                print(f"Erro ao processar marcador no nó {self.node_id}: {e}")
                import traceback
                print(traceback.format_exc())
                # Garante que não deixamos o nó em estado inconsistente
                if len(self.markers_received) >= 2:  # Já recebeu marcadores de todos os outros nós
                    self.complete_snapshot()

    def record_channel_message(self, from_node, message):
        """
        Registra mensagens recebidas em canais durante o snapshot.
        """
        if self.recording and from_node not in self.markers_received:
            if from_node not in self.channels_state:
                self.channels_state[from_node] = []
            self.channels_state[from_node].append(message)

# Exemplo de uso:
if __name__ == "__main__":
    snapshot = Snapshot(node_id=1)
    snapshot.start_snapshot()
    # Simulação de delay para receber mensagens/informações do snapshot
    import time
    time.sleep(1)
    snapshot.complete_snapshot()
