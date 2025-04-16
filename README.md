# SISD – Sistema Integrado Simulado de Distribuição

## 1. Objetivo Geral

Desenvolver um sistema distribuído completo que simule uma plataforma de consulta e monitoramento de sensores climáticos remotos. O sistema demonstra conceitos de sistemas distribuídos, como comunicação via Sockets, gRPC, Multicast, sincronização, replicação, eleição, tolerância a falhas e segurança.

---

## 2. Descrição Geral do Sistema

O sistema é composto por:

- **Sensores (Servidores):**
  - Simulam leituras de dados climáticos (temperatura, umidade, pressão).
  - Comunicação via Sockets (TCP) para envio periódico de dados ao cliente.
  - Serviço gRPC para controle (heartbeat, sincronização de relógio lógico, snapshot, eleição do coordenador).
  - Participação em Multicast (UDP) para receber alertas climáticos.
  - Implementam checkpoint e rollback para tolerância a falhas.

- **Cliente Principal:**
  - Coleta dados dos sensores via TCP.
  - Orquestra snapshots globais e envia marcadores para os sensores.
  - Implementa checkpoint e rollback.
  - Participa do grupo multicast para receber alertas.

- **Monitor:**
  - Recebe heartbeat/status dos sensores via gRPC.
  - Detecta falhas de sensores e pode iniciar eleição de coordenador.

- **Cloud:**
  - Armazena réplicas dos logs e checkpoints enviados pelos sensores e cliente.
  - Implementado como um serviço Flask com persistência em JSON.

---

## 3. Funcionalidades Implementadas

### 3.1 Comunicação via Sockets (TCP)

- Cada sensor executa um servidor TCP em uma porta específica (5000, 5001, 5002).
- O cliente conecta-se a cada sensor e recebe dados climáticos periodicamente.
- Os dados recebidos são registrados em log e replicados para a nuvem.

### 3.2 Comunicação via gRPC

- Sensores expõem serviços gRPC para:
  - Envio de heartbeat/status ao monitor.
  - Participação no algoritmo de eleição Bully.
- O monitor recebe status dos sensores e detecta falhas.
- O Bully é utilizado para eleição automática de coordenador em caso de falha.

### 3.3 Comunicação Multicast (UDP)

- Um módulo dedicado envia alertas climáticos via UDP multicast.
- Sensores e cliente podem receber e processar esses alertas.

### 3.4 Replicação de Dados

- Todas as mensagens e eventos relevantes são registrados em arquivos JSON individuais por nó.
- Cada registro é replicado para o serviço cloud via requisições HTTP.

### 3.5 Checkpoint e Rollback

- Sensores e cliente salvam periodicamente seu estado (checkpoint) em arquivos JSON.
- Em caso de falha, restauram o último estado salvo (rollback) automaticamente ao reiniciar.
- O checkpoint inclui identificador, timestamp e valor do relógio lógico de Lamport.

### 3.6 Algoritmo de Eleição (Bully)

- Implementação do algoritmo Bully via gRPC para eleição de coordenador entre sensores.
- O sensor com maior identificador se torna coordenador e notifica os demais.

### 3.7 Exclusão Mútua (Token Ring)

- Implementação de um anel lógico para passagem de token entre sensores.
- Apenas o sensor com o token pode enviar dados ao cliente, garantindo exclusão mútua.

### 3.8 Segurança

- Autenticação básica entre cliente e sensor usando criptografia assimétrica (RSA).
- Cada sensor gera ou carrega suas chaves privadas/públicas.

---

## 4. Estrutura do Projeto

```
docker-compose.yml
Dockerfile
requirements.txt
src/
  client/
    client.py
    logs/
    snapshots/
  sensor/
    sensor.py
    logs/
    snapshots/
  cloud/
    cloud_server.py
  middleware/
    monitor_server.py
    protos/
      *.proto, *_pb2.py, *_pb2_grpc.py
  multicast/
    sensor_alert.py
```

---

## 5. Tecnologias Utilizadas

- **Linguagem:** Python 3.9
- **Comunicação:** socket, grpcio, grpcio-tools, protobuf
- **API REST:** Flask
- **Replicação e Concorrência:** requests, filelock
- **Criptografia:** cryptography
- **Containerização:** Docker, Docker Compose

---

## 6. Como Executar com Docker

1. **Pré-requisitos:**  
   - Docker instalado  
   - Docker Compose instalado

2. **Build e execução dos containers:**  
   No diretório raiz do projeto, execute:

   ```sh
   docker-compose up --build
   ```

   Isso irá:
   - Construir a imagem Docker do projeto.
   - Subir os containers: 3 sensores, cliente, monitor, cloud.

3. **Acompanhando a execução:**  
   - Os logs de cada serviço podem ser visualizados no terminal ou com:

     ```sh
     docker-compose logs -f sensor1
     docker-compose logs -f client
     docker-compose logs -f monitor
     docker-compose logs -f cloud
     ```

   - Para acessar os dados replicados na nuvem, utilize a API REST do cloud:

     ```
     GET http://localhost:6000/replica
     ```

---

## 7. Observações sobre Checkpoint e Rollback

- **Checkpoint:**  
  Sensores e cliente salvam periodicamente seu estado em arquivos JSON na pasta `snapshots/`.
- **Rollback:**  
  Ao reiniciar, cada nó restaura automaticamente o último estado salvo, garantindo tolerância a falhas.

---

## 8. Observações Finais

O sistema implementa todos os requisitos de comunicação, replicação, tolerância a falhas, eleição, sincronização e segurança propostos.  
Para detalhes sobre cada módulo, consulte os comentários nos arquivos-fonte.

---
