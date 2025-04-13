import threading

class DistributedMutex:
    """
    Mutex distribuído simulado.
    Em uma implementação real, o lock seria obtido via um sistema de chave distribuída.
    """
    _global_lock = threading.Lock()

    def __init__(self, resource_id: str):
        self.resource_id = resource_id

    def acquire(self):
        DistributedMutex._global_lock.acquire()
        print(f"Mutex adquirido para o recurso {self.resource_id}.")

    def release(self):
        DistributedMutex._global_lock.release()
        print(f"Mutex liberado para o recurso {self.resource_id}.")

# Exemplo de uso:
if __name__ == "__main__":
    mutex = DistributedMutex("recurso1")
    mutex.acquire()
    # ... realizar operações críticas ...
    mutex.release()
