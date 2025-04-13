# src/seguranca/criptografia.py
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.fernet import Fernet

# Funções para RSA

def generate_rsa_keys():
    """
    Gera um par de chaves RSA (privada e pública).
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key

def serialize_private_key(private_key):
    """
    Serializa a chave privada em formato PEM.
    """
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

def serialize_public_key(public_key):
    """
    Serializa a chave pública em formato PEM.
    """
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def rsa_encrypt(public_key, message: bytes) -> bytes:
    """
    Criptografa uma mensagem utilizando a chave pública RSA.
    """
    ciphertext = public_key.encrypt(
        message,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )
    return ciphertext

def rsa_decrypt(private_key, ciphertext: bytes) -> bytes:
    """
    Descriptografa uma mensagem utilizando a chave privada RSA.
    """
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )
    return plaintext

# Criptografia Simétrica com Fernet (AES)

def generate_symmetric_key() -> bytes:
    """
    Gera uma chave simétrica para Fernet.
    """
    return Fernet.generate_key()

def symmetric_encrypt(key: bytes, message: bytes) -> bytes:
    """
    Criptografa uma mensagem usando a chave simétrica.
    """
    f = Fernet(key)
    return f.encrypt(message)

def symmetric_decrypt(key: bytes, token: bytes) -> bytes:
    """
    Descriptografa uma mensagem utilizando a chave simétrica.
    """
    f = Fernet(key)
    return f.decrypt(token)
