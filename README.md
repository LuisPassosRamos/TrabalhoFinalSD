# SISD – Sistema Integrado Simulado de Distribuição

## 1. Objetivo Geral

Desenvolver um sistema distribuído completo que simule uma plataforma de consulta e monitoramento de sensores climáticos remotos. O sistema deve demonstrar os principais conceitos de sistemas distribuídos por meio da integração de diferentes tecnologias de comunicação (Sockets, gRPC e Multicast) e mecanismos de sincronização, replicação, eleição, tolerância a falhas e segurança.

---

## 2. Descrição Geral do Sistema

O sistema é composto por:

- **Sensores (Servidores):**  
  Simulam leituras de dados climáticos (temperatura, umidade, pressão, etc.) e atuam de forma multifacetada:
  - **Comunicação via Sockets (TCP):** Enviam periodicamente os dados para o cliente principal.
  - **Serviço gRPC:** Expondo métodos para controle e gerenciamento (heartbeat, sincronização de relógio lógico, captura de estado global – snapshot, eleição do coordenador, etc.).
  - **Participação em Multicast (UDP):** Inscrevem-se em um grupo multicast para receber alertas climáticos.

- **Cliente Principal:**  
  É o nó central que:
  - Coleta os dados climáticos dos sensores através de conexões TCP.
  - Invoca serviços gRPC para controle, sincronização e verificação do estado dos sensores.
  - Participa do grupo multicast (como receptor e/ou emissor de alertas) para receber notificações simultâneas de condições críticas.

- **Monitor:**  
  Implementado para centralizar o gerenciamento e a visualização do status dos sensores, além de atuar no controle de heartbeat e na detecção de falhas.

- **Cloud:**  
  Responsável pela replicação dos dados e armazenamento dos checkpoints, simulando a consistência eventual e a recuperação de falhas. Pode ser implementado para demonstrar a replicação dos dados em arquivos JSON.


---

## 3. Módulos de Comunicação e Funcionamento

### 3.1 Comunicação via Sockets (TCP)

**Objetivo:**  
Realizar a coleta contínua de dados climáticos dos sensores para o cliente principal.

**Implementação:**

- **Sensores (Servidores TCP):**
  - Cada sensor inicia um servidor TCP escutando em uma porta configurada (ex.: 5000, 5001, 5002). Para a simulação inicial, deve haver 3 sensores simultâneos individuais. Cada um como se fosse uma máquina individual e diferente.
  - Periodicamente, envia uma mensagem com os dados climáticos simulados (temperatura, umidade, pressão).

- **Cliente Principal:**
  - Estabelece conexões TCP com os sensores (utilizando, por exemplo, os nomes dos containers em Docker).
  - Recebe as mensagens e as exibe ou registra em log para demonstração da comunicação e verificação dos dados recebidos.

**Demonstração:**  
Será verificado que o cliente recebe de forma contínua os dados dos sensores e que a troca de informações funciona conforme o modelo cliente-servidor básico proposto para sistemas distribuídos. Essa vereficação será feita através de um log pelo terminal de execução. Os Sensores (servidores) vão mandar pro log os dados e o cliente deve mostrar esses dados recebidos.

---

### 3.2 Comunicação via gRPC

**Objetivo:**  
Implementar uma camada de middleware que permita chamadas de procedimento remoto para controle e gerenciamento dos sensores.

**Implementação:**

- **Sensores (Serviço gRPC):**
  - Cada sensor expõe um serviço gRPC em uma porta específica (ex.: 7001, 7002, 7003).
  - Os métodos oferecidos podem incluir:
    - **Eleição do Coordenador (Bully):** Quando um sensor detecta a falha do coordenador, inicia o algoritmo de eleição e notifica os demais. Cada sensor tem um identificador único, cada nó do sistema tem um identificador único e pode se tornar o coordenador. Quando o monitor detecta a falha do coordenador, inicia uma eleição. O nó com maior identificador vence e notifica os outros nós.
    - **Heartbeat:** Cada nó envia periodicamente uma mensagem para o monitor contendo informações básicas, como o identificador do nó, um timestamp e possivelmente um status (por exemplo, "ok"). se caso o monitor não receba a mensagem do coordenador por um determinado período, ele inicia uma eleição.
    - **Sincronização com Clocks Lógicos (Lamport):** Cada sensor mantém um contador lógico; o timestamp é enviado junto com as mensagens e atualizado conforme os eventos ocorram.
    - **Snapshot Global (Chandy-Lamport):** O coordenador atual inicia a captura de estado periodicamente, enviando marcadores aos outros nós e salvando o estado local antes de continuar a comunicação. Os outros nós ao receberem o marcador, inicia a captura de estado também.
    
  
- **Cliente Principal:**
  - Atua como orquestrador, invocando os métodos gRPC nos sensores para solicitar o status, iniciar snapshots, verificar heartbeat e disparar eleições conforme necessário.

-**Monitor central:**
  - Atua como monitor, recebe os heartbeat de cada nó e mostra no log que o heartbeat foi recebido. Caso um nó não responda o heartbeat dentro de um tempo limite, o monitor deve detectá-lo como falho. Nesse caso, se o nó que falhou for o coordenador, inicia-se uma votação Bully.

**Demonstração:**  
Nos logs dos sensores e do cliente, deve ser possível identificar a comunicação gRPC e a execução dos métodos de controle (ex.: atualização dos clocks, envio de marcadores para snapshot ou iniciação do algoritmo de eleição). Essa abordagem está em consonância com o conteúdo de “Middlewares com RPC/gRPC” apresentado na atividade.

---

### 3.3 Comunicação em Grupo via Multicast (UDP)

**Objetivo:**  
Permitir o envio simultâneo de alertas climáticos a todos os nós (sensores, clientes e monitor) utilizando UDP multicast. Nessa parte haverá um mais um nó, um sensor que ao identificar condições climáticas críticas, envia mensagem de alerta a todos os sensores e ao cliente.

**Implementação:**

- **Emissor de Alertas:**
  - Ao detectar condições críticas (por exemplo, quando um sensor registra uma temperatura acima de um limiar), uma mensagem de alerta é enviada via UDP para um grupo multicast (ex.: IP 239.0.0.1 na porta 5007). Será feito por um módulo único.

- **Participantes Multicast:**
  - **Sensores e Cliente:** Todos os nós se inscrevem no grupo multicast para receber alertas.  
  - Quando o alerta é recebido, cada nó pode, por exemplo, registrar o evento ou executar ações predefinidas de emergência.
  
**Demonstração:**  
Durante a simulação, a ativação de um alerta disparado pelo sensor de alertas climáticos ao detectar uma condição extrema deve resultar na distribuição simultânea da mensagem para todos os nós inscritos. Essa parte é baseada na atividade de comunicação em grupo via multicast.

---

### 3.4 Replicação de Dados e Tolerância a Falhas

**Objetivo:**  
Garantir a consistência eventual dos dados e possibilitar a recuperação em caso de falhas.

**Implementação:**

- **Replicação e Consistência:**
  - Cada mensagem recebida dos sensores pode ser gravada em múltiplos arquivos locais (em formato JSON). Cada nó deve ser seu arquivo único individual. Isso é necessário para que caso ocorra uma falha, possa verificar cada arquivo para achar a inconsistência. Nesse caso, todos os arquivos devem estar armazenando todas as mensagens da comunicação, e caso algum dos arquivos tenha uma mensagem a menos ou alguma inconsistencia, significa que o problema está naquele nó.
  - Um processo reconciliador deverá sincronizar as réplicas, mesmo considerando delays artificiais para simular entrega fora de ordem.

- **Checkpoint e Rollback:**
  - Periodicamente, o estado do cliente (ou dos sensores) é salvo (checkpoint no formato json). Dessa forma, caso algum dos nós dê problema, podemos saber onde ele parou de funcionar e voltar no ultimo checkpoint.
  - Em caso de falha, o sistema restaura o último estado salvo, demonstrando a tolerância a falhas.

**Demonstração:**  
A implementação deve permitir visualizar, por exemplo, o arquivo de checkpoints sendo atualizado e a restauração do estado após uma simulação de falha, conforme orientações da atividade de Recuperação e Segurança.

---

## 4. Integração e Relação Entre as Comunicações

### Relação dos Componentes:
- **Sensores:**  
  Cada sensor atua em três vertentes no mesmo processo/container:
  1. **Servidor TCP:** Para enviar dados climáticos continuamente.
  2. **Servidor gRPC:** Para receber comandos e realizar operações de controle (heartbeat, sincronização, snapshot, eleição).
  3. **Participante Multicast:** Para receber alertas climáticos enviados em grupo.
  
- **Cliente Principal:**
  1. **Coleta de Dados via TCP:** Conecta-se a cada sensor para captar as leituras.
  2. **Orquestração via gRPC:** Invoca serviços dos sensores para sincronização, monitoramento e controle de falhas.
  3. **Multicast:** Atua como receptor (e/ou emissor) de alertas climáticos, possibilitando uma comunicação em grupo eficaz.
  
- **Monitor e Cloud:**
  - O **monitor** pode ser usado para centralizar informações de heartbeat e status dos sensores.
  - O **cloud** armazena dados replicados e checkpoints, possibilitando a recuperação e a consistência eventual entre réplicas.

### Fluxo de Comunicação:

1. **Inicialização:**  
   Cada sensor inicia os três serviços (TCP, gRPC e Multicast). O cliente principal se conecta aos sensores via TCP e também se inscreve no grupo multicast.
   
2. **Operação Normal:**  
   - Os sensores enviam dados via TCP periodicamente.
   - O cliente coleta esses dados e, em paralelo, pode fazer chamadas gRPC para monitorar o estado dos sensores (atualização de clocks, snapshots, heartbeat).
   - Em caso de detecção de condição crítica, um alerta multicast é disparado para notificar todos os nós simultaneamente.
   
3. **Tolerância a Falhas:**  
   - Os sensores e o cliente registram seus estados periodicamente via checkpoints.
   - Se for detectada uma falha (ex.: não resposta do heartbeat), o algoritmo de eleição é iniciado (Bully ou Anel) para selecionar um novo coordenador.
   - O sistema utiliza a replicação e o reconciliador para garantir consistência dos dados.

> Essa integração detalhada baseia-se na combinação dos requisitos apresentados nas atividades do projeto SISD, Comunicação, Replicação e Tolerância a Falhas, e Implementação de Algoritmos Distribuídos.

---

## 5. Tecnologias e Ferramentas

- **Linguagem:** Python (utilizando módulos: `socket`, `grpc`, `threading`, `multiprocessing`)
- **Frameworks:**  
  - gRPC (para comunicação RPC)
  - Bibliotecas de criptografia (ex.: `cryptography` para autenticação simples)
- **Ambiente de Execução:** Docker e Docker Compose para simular as múltiplas instâncias e a rede distribuída.
- **Outros:** Utilização de mecanismos de replicação (arquivos JSON) e checkpoints para recuperação.

---

## 6. Fluxo de Demonstração e Critérios de Avaliação

### Demonstração Prática
1. **Coleta via Sockets:**  
   O cliente conecta-se aos sensores, coletando e exibindo dados climáticos contínuos.

2. **Gerenciamento via gRPC:**  
   Através de chamadas remotas, são invocados métodos de heartbeat, sincronização (Lamport), snapshot global e eleição do coordenador. Os logs devem evidenciar a atualização dos contadores lógicos e o disparo dos algoritmos de eleição quando necessário.

3. **Alertas Multicast:**  
   Ao atingir condições definidas (por exemplo, temperatura acima de um certo limiar), um alerta multicast é disparado e recebido simultaneamente por todos os nós inscritos (sensores, cliente, monitor).

4. **Replicação e Tolerância a Falhas:**  
   Os dados são replicados e salvos em checkpoints; testes de falha demonstram a recuperação dos estados utilizando o último checkpoint registrado.

### Critérios de Avaliação
- **Arquitetura e Documentação:** Clareza na definição dos módulos e das relações entre as tecnologias.
- **Implementação das Comunicações:** Funcionamento adequado dos canais via TCP, gRPC e Multicast, conforme demonstrado pela coleta de dados, gerenciamento e alertas.
- **Sincronização e Estado Global:** Correta implementação dos clocks lógicos e do algoritmo de snapshot.
- **Eleições e Detecção de Falhas:** Implementação do algoritmo de eleição (Bully ou Anel) e do mecanismo de heartbeat.
- **Replicação, Tolerância a Falhas e Segurança:** Implementação da replicação dos dados, dos checkpoints e das funções de autenticação/criptografia simples.

> Esse conjunto de critérios abrange os aspectos avaliados conforme descrito nos documentos e nos critérios de avaliação do projeto.

---

## 7. Instruções para Execução e Entrega

1. **Código-Fonte:**  
   Organize o código em módulos (ex.: `src/sensor.py`, `src/client.py`, `src/monitor.py`, etc.), com comentários explicativos para cada parte do sistema.

2. **Execução via Docker:**  
   Certifique-se de ter o Docker e o Docker Compose instalados. No diretório raiz do projeto, execute:
   ```
   docker-compose up --build
   ```
   Isso iniciará todos os containers, permitindo a demonstração da comunicação e integração entre os nós.

3. **Documentação e Relatório:**  
   Prepare um relatório técnico que detalhe a arquitetura, os modelos implementados, as decisões de projeto e os resultados dos testes. Inclua capturas de tela e/ou vídeos demonstrativos conforme os critérios de avaliação.

4. **Entrega Final:**  
   - Código-fonte devidamente comentado.
   - Documentação técnica (README.md, relatório).
   - Apresentação (vídeo de demonstração).
   - Envio via email para: felipe_silva@ifba.edu.br, contendo a identificação do aluno, disciplina e turma.

---

## 8. Considerações Finais

Este README.md detalha como o sistema distribuído SISD integra comunicações via Sockets, gRPC e Multicast, além de implementar sincronização, eleição e tolerância a falhas. Ao seguir essas orientações, você demonstrará na prática os conceitos de sistemas distribuídos e atenderá aos critérios de avaliação definidos pelo projeto.