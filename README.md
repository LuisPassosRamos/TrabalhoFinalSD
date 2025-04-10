# Sistema Integrado Simulado de Distribuição
## Objetivo Geral:
Desenvolver um sistema distribuído completo que simule uma plataforma de consulta e monitoramento de sensores climáticos remotos, utilizando os principais conceitos e técnicas de sistemas distribuídos.
## Descrição Geral:
O sistema será composto por:
- Múltiplos sensores (servidores) simulando dados climáticos (temperatura, umidade, pressão, etc.)
- Um cliente principal que coleta dados dos sensores e exibe informações ao usuário.
- Comunicação via Sockets, gRPC, Multicast e técnicas de replicação, sincronização, eleição tolerância a falhas e segurança.
- A estrutura deve ser capaz de tolerar falhas, sincronizar o tempo dos sensores, e garantir a consistência eventual nas respostas.
