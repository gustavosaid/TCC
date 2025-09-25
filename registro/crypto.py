from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.FERNET_KEY)

def encrypt_string(text):
    return fernet.encrypt(text.encode()).decode()

def decrypt_string(token):
    return fernet.decrypt(token.encode()).decode()