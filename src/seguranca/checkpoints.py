import json
import os
import time
import logging
from nuvem import cloud

CHECKPOINT_FILE = "checkpoint.json"  # Arquivo local para checkpoint
CHECKPOINTS_DIR = "checkpoints"  # Diretório para versões de checkpoints
logger = logging.getLogger("checkpoints")

def save_checkpoint(state: dict) -> bool:
    """
    Salva o estado atual em JSON e registra o checkpoint no Cloud.
    Agora com tratamento de erros e melhor integração com o Cloud.
    
    Args:
        state: Dicionário contendo o estado a ser salvo
        
    Returns:
        bool: True se o checkpoint foi salvo com sucesso, False caso contrário
    """
    try:
        # Cria diretório para checkpoints se não existir
        os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
        
        # Adiciona timestamp e metadata ao estado
        full_state = {
            **state,
            "timestamp": time.time(),
            "checkpoint_version": "1.0",
            "checkpoint_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Nome do arquivo para este checkpoint específico (com timestamp)
        timestamp_str = time.strftime("%Y%m%d%H%M%S")
        checkpoint_filename = f"{CHECKPOINTS_DIR}/checkpoint_{timestamp_str}.json"
        
        # Salva localmente (arquivo único e arquivo com timestamp)
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(full_state, f, indent=2)
        
        with open(checkpoint_filename, "w") as f:
            json.dump(full_state, f, indent=2)
            
        logger.info(f"Checkpoint salvo em {CHECKPOINT_FILE} e {checkpoint_filename}")
        
        # Replica no Cloud para recuperação distribuída
        cloud.store_event("checkpoint", full_state)
        logger.info("Checkpoint replicado no Cloud")
        
        # Verifica se o evento foi realmente armazenado
        checkpoint_events = cloud.get_events_by_type("checkpoint")
        if checkpoint_events and checkpoint_events[-1].get("data") == full_state:
            logger.info("Verificação de replicação: checkpoint confirmado no Cloud")
        else:
            logger.warning("Aviso: checkpoint pode não ter sido corretamente replicado no Cloud")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar checkpoint: {e}")
        return False

def list_checkpoints() -> list:
    """
    Lista todos os checkpoints disponíveis localmente
    
    Returns:
        list: Lista de arquivos de checkpoint ordenados por data
    """
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    
    checkpoint_files = []
    for filename in os.listdir(CHECKPOINTS_DIR):
        if filename.startswith("checkpoint_") and filename.endswith(".json"):
            full_path = os.path.join(CHECKPOINTS_DIR, filename)
            checkpoint_files.append({
                "filename": filename,
                "path": full_path,
                "mtime": os.path.getmtime(full_path)
            })
    
    # Ordena por data de modificação (mais recente primeiro)
    checkpoint_files.sort(key=lambda x: x["mtime"], reverse=True)
    return checkpoint_files

def load_checkpoint(specific_file=None) -> dict:
    """
    Tenta restaurar o estado da aplicação a partir do checkpoint em JSON.
    
    Args:
        specific_file: Caminho específico para um arquivo de checkpoint
                      (se None, usa o arquivo padrão CHECKPOINT_FILE)
                      
    Returns:
        dict: Estado recuperado do checkpoint, ou dicionário vazio se falhar
    """
    filepath = specific_file or CHECKPOINT_FILE
    
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                state = json.load(f)
            logger.info(f"Checkpoint carregado de {filepath}")
            return state
        except json.JSONDecodeError:
            logger.error(f"Arquivo de checkpoint {filepath} está corrompido")
            return {}
        except Exception as e:
            logger.error(f"Erro ao carregar checkpoint: {e}")
            return {}
    else:
        logger.info(f"Nenhum checkpoint encontrado em {filepath}")
        return {}

def rollback(specific_file=None) -> dict:
    """
    Executa o rollback restaurando o estado do checkpoint.
    Verifica primeiro no arquivo local, depois no Cloud se necessário.
    
    Args:
        specific_file: Caminho específico para arquivo de checkpoint
        
    Returns:
        dict: Estado recuperado após rollback
    """
    logger.info("Iniciando processo de rollback...")
    
    # Tenta carregar do arquivo específico, se fornecido
    if specific_file and os.path.exists(specific_file):
        state = load_checkpoint(specific_file)
        if state:
            logger.info(f"Rollback bem-sucedido a partir de {specific_file}")
            return state
    
    # Tenta carregar do arquivo padrão
    state = load_checkpoint()
    
    # Se não encontrar localmente, tenta obter uma lista de checkpoints no diretório
    if not state:
        checkpoint_files = list_checkpoints()
        if checkpoint_files:
            latest_checkpoint = checkpoint_files[0]["path"]
            logger.info(f"Tentando rollback a partir do checkpoint mais recente: {latest_checkpoint}")
            state = load_checkpoint(latest_checkpoint)
            if state:
                logger.info(f"Rollback bem-sucedido a partir de {latest_checkpoint}")
                return state
    
    # Se ainda não tiver recuperado, tenta recuperar do Cloud
    if not state:
        logger.info("Checkpoint local não encontrado. Tentando recuperar do Cloud...")
        checkpoint_event = cloud.get_last_checkpoint()
        if checkpoint_event and "data" in checkpoint_event:
            state = checkpoint_event["data"]
            logger.info(f"Estado recuperado do Cloud: timestamp={checkpoint_event.get('timestamp')}")
            
            # Salva localmente para futuras recuperações
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(state, f, indent=2)
                
            # Também salva no diretório de checkpoints
            os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d%H%M%S")
            recovery_file = f"{CHECKPOINTS_DIR}/recovery_from_cloud_{timestamp_str}.json"
            with open(recovery_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Estado recuperado do Cloud salvo localmente em {recovery_file}")
    
    if state:
        logger.info(f"Rollback realizado com sucesso. Estado de {state.get('checkpoint_time', 'tempo desconhecido')} restaurado.")
    else:
        logger.error("Falha no rollback: nenhum checkpoint encontrado localmente ou no Cloud.")
    
    return state

# Se executado diretamente, demonstra as funcionalidades
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
    
    # Demonstração das funcionalidades
    print("=== Demonstração do módulo de Checkpoints ===")
    
    # Cria um estado de teste
    test_state = {
        "sensor_id": "test_sensor",
        "readings": [{"temperature": 25.3, "humidity": 68.7}],
        "status": "ok"
    }
    
    # Salva o checkpoint
    save_checkpoint(test_state)
    
    # Lista os checkpoints disponíveis
    print("\nCheckpoints disponíveis:")
    for cp in list_checkpoints():
        print(f"- {cp['filename']} (modificado em {time.ctime(cp['mtime'])})")
    
    # Executa um rollback
    print("\nExecutando rollback:")
    restored_state = rollback()
    print(f"Estado restaurado: {json.dumps(restored_state, indent=2)}")