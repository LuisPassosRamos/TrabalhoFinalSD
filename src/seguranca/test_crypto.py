"""
Teste de ponta a ponta para funcionalidades de criptografia e segurança.
Este script testa a funcionalidade de criptografia RSA e simétrica,
a autenticação básica e o salvamento/recuperação de checkpoints.
"""

import os
import time
from criptografia import (generate_rsa_keys, serialize_private_key, serialize_public_key,
                          rsa_encrypt, rsa_decrypt, generate_symmetric_key, 
                          symmetric_encrypt, symmetric_decrypt)
from autenticacao import authenticate, generate_auth_token
from checkpoints import save_checkpoint, rollback

def test_rsa():
    print("==== Teste de Criptografia RSA ====")
    private_key, public_key = generate_rsa_keys()
    print("Chaves RSA geradas com sucesso")
    
    mensagem = "Informação confidencial: temperatura crítica detectada"
    print(f"Mensagem original: {mensagem}")
    
    encrypted = rsa_encrypt(public_key, mensagem.encode())
    print(f"Mensagem criptografada: {encrypted[:20]}...")
    
    decrypted = rsa_decrypt(private_key, encrypted)
    print(f"Mensagem descriptografada: {decrypted.decode()}")
    
    assert mensagem == decrypted.decode(), "Falha: A mensagem descriptografada não corresponde à original!"
    print("✓ Teste RSA bem-sucedido")

def test_symmetric():
    print("\n==== Teste de Criptografia Simétrica ====")
    key = generate_symmetric_key()
    print(f"Chave simétrica gerada: {key.decode()}")
    
    mensagem = "Dados do sensor: temperatura=25.3, umidade=70.2, pressão=1013.2"
    print(f"Mensagem original: {mensagem}")
    
    encrypted = symmetric_encrypt(key, mensagem.encode())
    print(f"Mensagem criptografada: {encrypted[:20]}...")
    
    decrypted = symmetric_decrypt(key, encrypted)
    print(f"Mensagem descriptografada: {decrypted.decode()}")
    
    assert mensagem == decrypted.decode(), "Falha: A mensagem descriptografada não corresponde à original!"
    print("✓ Teste de criptografia simétrica bem-sucedido")

def test_authentication():
    print("\n==== Teste de Autenticação ====")
    user = "usuario1"
    valid_password = "senha123"
    invalid_password = "senha_errada"
    
    assert authenticate(user, valid_password), "Falha: Autenticação com senha válida falhou!"
    print("✓ Autenticação com senha válida bem-sucedida")
    
    assert not authenticate(user, invalid_password), "Falha: Autenticação com senha inválida deveria falhar!"
    print("✓ Autenticação com senha inválida corretamente rejeitada")
    
    token = generate_auth_token(user)
    print(f"Token gerado para {user}: {token}")
    print("✓ Teste de autenticação bem-sucedido")

def test_checkpoint_rollback():
    print("\n==== Teste de Checkpoint e Rollback ====")
    # Salva checkpoint com dados simulados
    state = {
        "sensor_id": "test1",
        "readings": [
            {"temperature": 25.3, "humidity": 68.7, "pressure": 1012.5},
            {"temperature": 25.5, "humidity": 68.2, "pressure": 1012.4}
        ],
        "status": "normal",
        "last_update": time.time()
    }
    
    print("Salvando checkpoint com estado:", state)
    save_checkpoint(state)
    
    # Recuperando dados com rollback
    recovered_state = rollback()
    print("Estado recuperado:", recovered_state)
    
    assert recovered_state.get("sensor_id") == state["sensor_id"], "Falha: ID do sensor não corresponde após rollback!"
    print("✓ Teste de checkpoint/rollback bem-sucedido")

if __name__ == "__main__":
    print("Iniciando testes de segurança e recuperação...\n")
    test_rsa()
    test_symmetric()
    test_authentication()
    test_checkpoint_rollback()
    print("\nTodos os testes concluídos com sucesso!")
