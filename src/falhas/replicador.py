import json
import os

REPLICA_FILES = ["replica1.json", "replica2.json"]

def save_message_replication(message: dict) -> None:
    """Salva a mensagem em todas as réplicas (arquivos JSON)."""
    for filename in REPLICA_FILES:
        data = []
        if os.path.exists(filename):
            with open(filename, "r") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = []
        data.append(message)
        with open(filename, "w") as f:
            json.dump(data, f)
    print("Mensagem replicada em todas as réplicas.")

def reconcile_replicas() -> list:
    """Reconciliar as réplicas e retorna a lista consolidada de mensagens."""
    consolidated = []
    for filename in REPLICA_FILES:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                try:
                    data = json.load(f)
                    consolidated.extend(data)
                except Exception:
                    continue
    # Remover duplicatas (baseado em um campo 'id')
    seen = set()
    unique_messages = []
    for msg in consolidated:
        msg_id = msg.get("id")
        if msg_id not in seen:
            seen.add(msg_id)
            unique_messages.append(msg)
    print("Mensagens reconciliadas:", unique_messages)
    return unique_messages

if __name__ == "__main__":
    # Teste simples
    message = {"id": 1, "content": "Teste de replicação"}
    save_message_replication(message)
    reconcile_replicas()
