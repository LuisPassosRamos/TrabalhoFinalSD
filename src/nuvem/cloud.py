import json
import threading
import time
import os  # Importação global do módulo os

# Define diretório e arquivo de armazenamento JSON
STORAGE_DIR = "/app/cloud_storage"
STORAGE_FILE = os.path.join(STORAGE_DIR, "cloud_data.json")
_lock = threading.Lock()

def init_storage():
    """Inicializa o diretório e arquivo de armazenamento"""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w") as f:
            json.dump([], f)

def push_data(data: str) -> None:
    """Insere ou atualiza dados no arquivo JSON do Cloud."""
    init_storage()
    with _lock:
        with open(STORAGE_FILE, "r") as f:
            try:
                cloud_data = json.load(f)
            except Exception:
                cloud_data = []
        record = {"data": data, "timestamp": time.time()}
        cloud_data.append(record)
        with open(STORAGE_FILE, "w") as f:
            json.dump(cloud_data, f)
    print("Dados enviados para a nuvem.")

def get_all_data() -> list:
    """Retorna todos os dados armazenados no Cloud"""
    init_storage()
    with open(STORAGE_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def store_event(event_type: str, event_data: dict) -> None:
    """
    Registra eventos críticos (e.g., checkpoint, election, snapshot, falhas) num arquivo JSON.
    """
    # Garante que o diretório existe antes de tentar escrever
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    EVENT_FILE = os.path.join(STORAGE_DIR, "events_log.json")
    with _lock:
        try:
            events = []
            if os.path.exists(EVENT_FILE):
                with open(EVENT_FILE, "r") as f:
                    try:
                        events = json.load(f)
                    except Exception as e:
                        print(f"Erro ao carregar eventos existentes: {e}")
                        events = []
            
            # Adiciona mais metadados ao evento
            record = {
                "type": event_type,
                "data": event_data,
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "event_id": f"{event_type}_{time.time()}"
            }
            events.append(record)
            
            # Garantir que o arquivo não fique muito grande (limite de 1000 eventos)
            if len(events) > 1000:
                events = events[-1000:]  # Mantém os 1000 mais recentes
            
            # Evite transações muito longas com o sistema de arquivos
            temp_file = EVENT_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(events, f, indent=2)
            
            # Operação atômica de renomeação para evitar arquivos corrompidos
            os.replace(temp_file, EVENT_FILE)
            
            print(f"Evento '{event_type}' registrado na nuvem com ID {record['event_id']}.")
            return record
            
        except Exception as e:
            print(f"Erro ao armazenar evento '{event_type}': {e}")
            import traceback
            print(traceback.format_exc())
            return None

def get_all_events() -> list:
    """
    Retorna todos os eventos registrados no arquivo JSON de eventos.
    """
    EVENT_FILE = os.path.join(STORAGE_DIR, "events_log.json")
    if os.path.exists(EVENT_FILE):
        with open(EVENT_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def get_events_by_type(event_type: str) -> list:
    """
    Retorna todos os eventos de um tipo específico registrados no Cloud.
    """
    events = get_all_events()
    filtered = [event for event in events if event.get("type") == event_type]
    return filtered

def get_latest_data() -> dict:
    """
    Retorna o registro de dados mais recente armazenado no Cloud.
    """
    init_storage()
    with open(STORAGE_FILE, "r") as f:
        try:
            data = json.load(f)
            if data:
                return data[-1]
            return {}
        except Exception:
            return {}

def get_last_checkpoint() -> dict:
    """
    Retorna o último checkpoint registrado como evento no Cloud.
    Assume que os checkpoints são registrados com o tipo 'checkpoint'.
    """
    events = get_events_by_type("checkpoint")
    if events:
        return max(events, key=lambda e: e.get("timestamp", 0))
    return {}

def get_last_checkpoint_by_sensor(sensor_id: str) -> dict:
    """
    Retorna o último checkpoint registrado para um sensor específico.
    Filtra os eventos do tipo 'checkpoint' de modo a considerar
    apenas aqueles cujo dado contenha o identificador do sensor.
    """
    events = get_events_by_type("checkpoint")
    sensor_events = [event for event in events if isinstance(event.get("data"), dict) 
                     and event.get("data").get("sensor") == sensor_id]
    if sensor_events:
        return max(sensor_events, key=lambda e: e.get("timestamp", 0))
    return {}

def query_data() -> dict:
    """
    Simula um endpoint de consulta no Cloud.
    Retorna o último checkpoint e os eventos atuais.
    """
    latest = get_latest_data()
    last_checkpoint = get_last_checkpoint()
    events = get_all_events()
    return {"latest_data": latest, "last_checkpoint": last_checkpoint, "events": events}

def verify_data_consistency() -> bool:
    """
    Verifica a consistência dos dados armazenados.
    Útil para confirmar que os dados não foram corrompidos.
    """
    try:
        # Verifica os arquivos de dados
        get_all_data()
        
        # Verifica os eventos
        events = get_all_events()
        
        # Verifica checkpoint mais recente
        latest_checkpoint = get_last_checkpoint()
        
        return True
    except Exception as e:
        print(f"Erro na verificação de consistência: {e}")
        return False

def verify_data_integrity() -> list:
    """
    Verifica a integridade dos dados armazenados.
    Retorna uma lista de problemas encontrados ou uma lista vazia se ok.
    """
    issues = []
    try:
        # Verifica arquivos de dados
        EVENT_FILE = os.path.join(STORAGE_DIR, "events_log.json")
        if os.path.exists(EVENT_FILE):
            with open(EVENT_FILE, "r") as f:
                events = json.load(f)
                # Verifica estrutura básica dos eventos
                for idx, event in enumerate(events):
                    if not isinstance(event, dict) or "type" not in event or "timestamp" not in event:
                        issues.append(f"Evento {idx} tem formato inválido")
        
        # Verifica checkpoints
        checkpoints = get_events_by_type("checkpoint")
        for cp in checkpoints:
            if not isinstance(cp.get("data"), dict):
                issues.append(f"Checkpoint {cp.get('timestamp')} tem formato inválido")
    
    except Exception as e:
        issues.append(f"Erro ao verificar integridade dos dados: {str(e)}")
    
    return issues

def run_cloud_server() -> None:
    """Inicia o servidor de computação em nuvem"""
    init_storage()
    print("Servidor de Computação em Nuvem iniciado.")
    
    # Thread para verificação periódica de consistência e integridade
    def consistency_check():
        while True:
            time.sleep(30)  # Verifica a cada 30 segundos
            is_consistent = verify_data_consistency()
            integrity_issues = verify_data_integrity()
            
            if not is_consistent:
                print("ALERTA: Inconsistência detectada nos dados do Cloud")
            
            if integrity_issues:
                print(f"ALERTA: Problemas de integridade encontrados: {integrity_issues}")
            else:
                print("Verificação de integridade: OK")
    
    threading.Thread(target=consistency_check, daemon=True).start()
    
    while True:
        time.sleep(10)
        dados = get_all_data()
        events = get_all_events()
        consulta = query_data()
        print("Dados armazenados na nuvem:", dados)
        print("Eventos registrados na nuvem:", events)
        print("Consulta de estado via query_data:", consulta)

if __name__ == "__main__":
    run_cloud_server()
