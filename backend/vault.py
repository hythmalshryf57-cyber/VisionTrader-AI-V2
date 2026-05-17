import base64
import hashlib
from cryptography.fernet import Fernet
from config import settings


def _derive_fernet_key(raw: str) -> bytes:
    if not raw:
        raw = 'default-master-encryption-key'
    try:
        key = base64.urlsafe_b64decode(raw)
        if len(key) == 32:
            return base64.urlsafe_b64encode(key)
    except Exception:
        pass
    digest = hashlib.sha256(raw.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


class Vault:
    def __init__(self):
        raw = getattr(settings, 'MASTER_ENCRYPTION_KEY', '') or ''
        key = _derive_fernet_key(raw)
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if not encrypted_data:
            return ""
        return self.fernet.decrypt(encrypted_data.encode()).decode()


vault = Vault()
