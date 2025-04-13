import logging

def replicate_data(data: dict, nodes: list) -> None:
    """
    Simula a replicação de dados para os nós informados.
    Em uma implementação real, este método enviaria os dados via rede.
    """
    for node in nodes:
        # ...enviar dados para o nó 'node'...
        logging.info(f"Replicando dados para o nó {node}: {data}")

# Exemplo de uso:
if __name__ == "__main__":
    sample_data = {"sensor": "s1", "valor": 42}
    replicate_data(sample_data, nodes=[1,2,3,4])
