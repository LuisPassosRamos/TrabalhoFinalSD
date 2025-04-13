# src/falhas/eleicao.py
import time
import logging
from nuvem import cloud  # Importação para integração com o Cloud

class BullyElection:
    def __init__(self, node_id, nodes):
        """
        node_id: identificador deste nó (no início do processo de eleição).
        nodes: lista de IDs de todos os nós do sistema.
        """
        self.node_id = node_id
        self.nodes = sorted(nodes)  # Garante que a lista está ordenada
        self.coordinator = None
        self.election_in_progress = False
        self.logger = logging.getLogger("BullyElection")

    def start_election(self):
        """
        Inicia o processo de eleição, implementando o algoritmo Bully.
        Retorna True se a eleição foi concluída com sucesso.
        """
        if self.election_in_progress:
            self.logger.info(f"Nó {self.node_id}: Eleição já em progresso")
            return False
            
        self.election_in_progress = True
        self.logger.info(f"Nó {self.node_id} iniciando eleição")
        
        # Registra o início da eleição no Cloud
        cloud.store_event("election_started", {
            "initiator": self.node_id,
            "timestamp": time.time(),
            "available_nodes": self.nodes
        })
        
        # Identifica nós com ID maior (potenciais coordenadores)
        higher_nodes = [n for n in self.nodes if n > self.node_id]
        
        if not higher_nodes:
            # Se não há nós com ID maior, este nó se torna coordenador
            self.coordinator = self.node_id
            self.logger.info(f"Nó {self.node_id} se torna o coordenador (maior ID ativo).")
            self.announce_coordinator()
            self.election_in_progress = False
            return True
            
        # Envia mensagem de eleição para nós com ID maior
        responses = self._send_election_messages(higher_nodes)
        
        if not responses:
            # Se nenhum nó com ID maior respondeu, este nó torna-se coordenador
            self.coordinator = self.node_id
            self.logger.info(f"Nó {self.node_id} se torna o coordenador (nenhum nó maior respondeu).")
            self.announce_coordinator()
        else:
            # Se algum nó com ID maior responde, o atual cede a eleição
            self.logger.info(f"Nó {self.node_id} aguardando anúncio de um nó maior. Respostas: {responses}")
            # Simulação: o nó de maior ID entre os respondentes será o coordenador
            self.coordinator = max(responses)
            
        self.election_in_progress = False
        return True

    def _send_election_messages(self, higher_nodes):
        """
        Simula o envio de mensagens de eleição para nós com ID maior.
        Em uma implementação real, isso envolveria comunicação de rede.
        Retorna uma lista de IDs de nós que responderam.
        """
        responses = []
        for node in higher_nodes:
            self.logger.info(f"Nó {self.node_id} envia mensagem de eleição para o nó {node}")
            # Simulação: Pausa para dar tempo ao nó de processar
            time.sleep(0.1)
            
            # Registra evento de comunicação no Cloud
            cloud.store_event("election_message", {
                "from": self.node_id,
                "to": node,
                "type": "ELECTION",
                "timestamp": time.time()
            })
            
            # Simula a resposta - em um sistema real, isso seria assíncrono via rede
            # Para efeitos da simulação, assumimos que nós com ID par respondem
            if node % 2 == 0:  # Simples lógica para demonstração
                responses.append(node)
                self.logger.info(f"Nó {node} respondeu ao nó {self.node_id}")
                
                # Registra a resposta no Cloud
                cloud.store_event("election_message", {
                    "from": node,
                    "to": self.node_id,
                    "type": "ANSWER",
                    "timestamp": time.time()
                })
                
        return responses

    def announce_coordinator(self):
        """
        Simula o anúncio do coordenador para todos os nós.
        Em uma implementação real, isso envolveria broadcast de rede.
        """
        self.logger.info(f"Nó {self.node_id} anuncia: Nó {self.coordinator} é o novo coordenador.")
        
        # Registra o evento de eleição no Cloud
        cloud.store_event("election_completed", {
            "new_coordinator": self.coordinator,
            "announced_by": self.node_id,
            "timestamp": time.time(),
            "participating_nodes": self.nodes
        })
        
        # Atualiza também na categoria genérica "election" para compatibilidade
        cloud.store_event("election", {
            "new_coordinator": self.coordinator, 
            "time": time.time()
        })
        
        # Em um sistema real, enviaria uma mensagem para todos os nós
        for node in self.nodes:
            if node != self.node_id:
                self.logger.info(f"Enviando anúncio de coordenador para o nó {node}")
                # Simulação de mensagem
                time.sleep(0.05)
                
                # Registra evento de comunicação no Cloud
                cloud.store_event("election_message", {
                    "from": self.node_id,
                    "to": node,
                    "type": "COORDINATOR",
                    "coordinator": self.coordinator,
                    "timestamp": time.time()
                })

    def receive_election_message(self, from_node, message_type):
        """
        Processa uma mensagem recebida relacionada à eleição.
        Args:
            from_node: ID do nó que enviou a mensagem
            message_type: Tipo da mensagem ('ELECTION', 'ANSWER', 'COORDINATOR')
        """
        if message_type == "ELECTION":
            # Se receber mensagem de eleição, responde e inicia própria eleição
            self.logger.info(f"Nó {self.node_id} recebeu mensagem ELECTION de {from_node}")
            
            # Registra no Cloud
            cloud.store_event("election_message", {
                "from": from_node,
                "to": self.node_id,
                "type": "ELECTION",
                "timestamp": time.time(),
                "action": "received"
            })
            
            # Se o nó atual tem ID maior, responde e inicia sua própria eleição
            if self.node_id > from_node:
                self.logger.info(f"Nó {self.node_id} responde a {from_node} e inicia própria eleição")
                
                # Registra resposta no Cloud
                cloud.store_event("election_message", {
                    "from": self.node_id,
                    "to": from_node,
                    "type": "ANSWER",
                    "timestamp": time.time()
                })
                
                # Inicia sua própria eleição
                self.start_election()
                
        elif message_type == "COORDINATOR":
            # Se receber mensagem de coordenador, atualiza seu estado
            self.logger.info(f"Nó {self.node_id} recebeu mensagem COORDINATOR: {from_node} é o coordenador")
            self.coordinator = from_node
            
            # Registra no Cloud
            cloud.store_event("election_message", {
                "from": from_node,
                "to": self.node_id,
                "type": "COORDINATOR",
                "coordinator": from_node,
                "timestamp": time.time(),
                "action": "received"
            })

# Exemplo de uso:
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
    
    # Simula uma eleição com 5 nós
    nodes = [1, 2, 3, 4, 5]
    
    # Nó 2 detecta falha e inicia eleição
    election = BullyElection(node_id=2, nodes=nodes)
    election.start_election()
    
    print(f"Coordenador eleito: {election.coordinator}")
