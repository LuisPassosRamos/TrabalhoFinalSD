# src/sincronizacao/lamport.py

class LamportClock:
    def __init__(self):
        self.time = 0

    def tick(self):
        """Incrementa o clock para cada evento local."""
        self.time += 1
        return self.time

    def update(self, received_time):
        """
        Atualiza o clock ao receber uma mensagem.
        Garante que o clock local seja sempre maior que o recebido.
        """
        self.time = max(self.time, received_time) + 1
        return self.time

    def get_time(self):
        """Retorna o valor atual do clock."""
        return self.time

# Exemplo de uso:
if __name__ == "__main__":
    clock = LamportClock()
    print("Clock inicial:", clock.get_time())
    clock.tick()  # Evento local
    print("Após tick:", clock.get_time())
    clock.update(10)  # Mensagem recebida com timestamp 10
    print("Após update com 10:", clock.get_time())
