# Documentação do Projeto

Este documento descreve as funcionalidades implementadas no projeto conforme solicitado na atividade, detalhando como cada uma delas foi desenvolvida e fornecendo instruções para execução e demonstração do funcionamento do código.

## Funcionalidades Implementadas

### 1. Funcionalidades Básicas
- **Leitura e Processamento de Dados:** Módulos implementados para coletar e processar informações dos sensores.
- **Interface de Usuário Simples:** Comunicação via CLI para interação com o sistema.

### 2. Funcionalidades Avançadas
- **Validação e Tratamento de Erros:** Implementados em todos os módulos para garantir robustez e confiabilidade.
- **Modularização do Código:** Projeto estruturado em módulos como sensores, cliente, middleware, segurança, sincronização, comunicação em grupo, entre outros.
- **Replicação e Controle de Concorrência:** Mecanismo de replicação de dados (falhas/replicacao.py) e mutex distribuído (falhas/mutex.py).
- **Integração Contínua:** Código organizado e preparado para pipelines de testes e deploy automáticos.
- **Documentação e Comentários:** Código bem documentado, com explicações detalhadas conforme especificado no ATIVIDADE.md.

### 3. Funcionalidades Específicas (conforme ATIVIDADE.md)
- **Sincronização e Estado Global:**
  - **Clock de Lamport:** Implementado em sincronizacao/lamport.py para registro de eventos.
  - **Snapshot Global:** Implementado em sincronizacao/snapshot.py para captura e exibição do estado dos nós.
- **Comunicação entre Componentes:**
  - **Sockets (TCP/IP):** Comunicação entre o cliente e os sensores, implementada em src/sensors/sensor.py e src/client/client_main.py.
  - **RPC com Pyro4:** Implementação de RMI para acesso remoto aos dados dos sensores (src/middleware/pyro.client.py e src/middleware/pyro_server.py).
  - **Middleware gRPC:** Comunicação via gRPC implementada em src/middleware/grpc_client.py e src/middleware/grpc_server.py, utilizando o arquivo proto em src/middleware/proto/sensor.proto.
  - **Comunicação em Grupo via Multicast:** Envio de alertas climáticos, implementado em comunicacao_grupo/multicast.py.
- **Gerência de Falhas e Eleição:**
  - **Heartbeat:** Monitoramento do estado dos sensores via UDP, implementado em src/middleware/heartbeat_monitor.py e falhas/heartbeat.py.
  - **Algoritmo de Eleição (Bully):** Implementado em falhas/eleicao.py para definição do nó coordenador em caso de inatividade.
- **Segurança e Recuperação:**
  - **Autenticação Simples:** Verificação de credenciais implementada em seguranca/autenticacao.py.
  - **Criptografia RSA e Simétrica:** Implementações de criptografia estão em seguranca/criptografia.py.
  - **Checkpoints e Rollback:** Mecanismo de salvamento e recuperação de estado implementado em seguranca/checkpoints.py.
- **Tolerância a Falhas e Concorrência:**
  - **Replicação de Dados e Mutex Distribuído:** Garantem consistência e integridade dos dados em ambiente distribuído.

## Novas Funcionalidades Integradas

- **Integração via gRPC:**  
  - Servidor: `python src/main.py grpc_server`  
  - Cliente: `python src/main.py grpc_client`

- **Integração via Pyro4 (simulação de RMI):**  
  - Servidor: `python src/main.py pyro_server`  
  - Cliente: `python src/main.py pyro_client`

- **Multi-sensor e Multi-cliente:**  
  - Múltiplos sensores são iniciados com `python src/main.py multi_sensor`  
  - Múltiplos clientes se conectam aos sensores com `python src/main.py multi_client`

- **Checkpoints e Rollback:**  
  - Teste via `python src/main.py rollback`  
  (Realiza salvamento de estado e recuperação com o módulo de checkpoints)

- **Multicast:**  
  - Envio e recebimento de alertas climáticos com `python src/main.py multicast_sender` e `python src/main.py multicast_receiver`

- **Computação em Nuvem (simulada via Docker):**  
  Basta utilizar o comando:
  ```
  docker-compose -f docker/docker-compose.yml up --build
  ```

## Como as Funcionalidades Foram Desenvolvidas

- **Arquitetura do Projeto:** O projeto foi dividido em pacotes/módulos, onde cada módulo concentra uma responsabilidade, seguindo os princípios SOLID e garantindo baixo acoplamento.
- **Uso de Bibliotecas e Frameworks:** As funcionalidades foram implementadas utilizando bibliotecas modernas e frameworks que facilitam a manipulação de dados, a criação de interfaces e a execução de testes.
- **Testes e Validações:** Cada nova funcionalidade foi acompanhada com testes unitários e de integração para assegurar a qualidade e a estabilidade do sistema.
- **Método de Desenvolvimento:** A equipe utilizou metodologias ágeis para definir as funcionalidades e evoluir o projeto por meio de iterações constantes, garantindo entregas incrementais e focadas no cliente.

## Instruções para Execução e Demonstração do Código

1. Pré-requisitos:
   - Docker e Docker Compose instalados na máquina.
   - Build do projeto com:
     ```
     docker-compose -f docker/docker-compose.yml up --build
     ```

2. Execução:
   - O projeto foi desenvolvido para ser executado inteiramente via Docker. Todos os módulos (sensores, monitor, cliente, etc.) serão iniciados automaticamente pelos serviços definidos no arquivo `docker/docker-compose.yml`.
   - Para iniciar a simulação integrada, use o comando:
     ```
     docker-compose -f docker/docker-compose.yml up --build
     ```
   - O Docker Compose criará e iniciará os containers correspondentes a cada serviço registrado (sensor1, sensor2, sensor3, monitor, client, all).
   - Os logs de execução poderão ser acompanhados diretamente no terminal.

---

Esta documentação detalha todas as funcionalidades e o fluxo de desenvolvimento do projeto, atendendo às especificações descritas no ATIVIDADE.md e servindo como guia para desenvolvedores e usuários na execução e compreensão do sistema.
