# src/seguranca/autenticacao.py
import base64
import time

# Base de usuários simples (para demonstração)
USERS = {
    "usuario1": "senha123",
    "usuario2": "senha456"
}

def authenticate(username: str, password: str) -> bool:
    """
    Autentica o usuário comparando com os dados pré-definidos.
    """
    if username in USERS and USERS[username] == password:
        return True
    return False

def generate_auth_token(username: str) -> str:
    """
    Gera um token de autenticação simples com base no nome de usuário e timestamp.
    """
    token_str = f"{username}:{int(time.time())}"
    return base64.urlsafe_b64encode(token_str.encode()).decode()

# Exemplo de uso:
if __name__ == "__main__":
    user = "usuario1"
    password = "senha123"
    if authenticate(user, password):
        token = generate_auth_token(user)
        print("Usuário autenticado. Token:", token)
    else:
        print("Falha na autenticação.")
