import base64
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import settings


class CryptoVault:
    """AES-GCM vault for encrypting sensitive user fields."""

    def __init__(self, master_key: str = None):
        raw = master_key or getattr(settings, 'MASTER_ENCRYPTION_KEY', '') or ''
        key = self._derive_key(raw)
        self._key = key
        self._aesgcm = AESGCM(self._key)

    def _derive_key(self, raw: str) -> bytes:
        if not raw:
            raw = 'default-master-encryption-key'
        try:
            decoded = base64.b64decode(raw)
            if len(decoded) in (16, 24, 32):
                return decoded
        except Exception:
            pass
        return hashlib.sha256(raw.encode('utf-8')).digest()

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return ""
        nonce = os.urandom(12)
        ct = self._aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ct).decode('utf-8')

    def decrypt_admin(self, token: str, admin_user) -> str:
        if not admin_user or not getattr(admin_user, 'is_admin', False):
            raise PermissionError('Admin privileges required to decrypt')
        if not token:
            return ""
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        pt = self._aesgcm.decrypt(nonce, ct, None)
        return pt.decode('utf-8')


vault = CryptoVault()
