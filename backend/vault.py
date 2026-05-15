from cryptography.fernet import Fernet
from config import settings

class Vault:
    def __init__(self):
        self.fernet = Fernet(settings.MASTER_ENCRYPTION_KEY)

    def encrypt(self, data: str) -> str:
        if not data: return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if not encrypted_data: return ""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

vault = Vault()
