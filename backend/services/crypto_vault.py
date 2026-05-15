import base64
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import settings


class CryptoVault:
    """AES-256-GCM based vault for encrypting sensitive user fields.

    Admin-only decryption via `decrypt_admin` which requires an admin user object.
    """

    def __init__(self):
        raw = getattr(settings, 'MASTER_ENCRYPTION_KEY', '') or ''
        # Try to decode base64; otherwise derive 32-byte key via SHA256
        try:
            key = base64.b64decode(raw)
            if len(key) != 32:
                key = hashlib.sha256(raw.encode('utf-8')).digest()
        except Exception:
            key = hashlib.sha256(raw.encode('utf-8')).digest()
        self._key = key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return base64(nonce + ciphertext + tag)."""
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        payload = nonce + ct
        return base64.b64encode(payload).decode('utf-8')

    def decrypt_admin(self, token: str, admin_user) -> str:
        """Decrypt token only if admin_user.is_admin is truthy."""
        if not admin_user or not getattr(admin_user, 'is_admin', False):
            raise PermissionError('Admin privileges required to decrypt')
        try:
            raw = base64.b64decode(token)
            nonce = raw[:12]
            ct = raw[12:]
            aesgcm = AESGCM(self._key)
            pt = aesgcm.decrypt(nonce, ct, None)
            return pt.decode('utf-8')
        except Exception as e:
            raise


vault = CryptoVault()
import base64
import os
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import constant_time
from config import settings


class CryptoVault:
    def __init__(self, master_b64: str = None):
        # MASTER_ENCRYPTION_KEY should be 32 bytes base64-encoded
        b64 = master_b64 or getattr(settings, 'MASTER_ENCRYPTION_KEY', None)
        if not b64:
            raise ValueError("MASTER_ENCRYPTION_KEY not configured")
        self.key = base64.b64decode(b64)
        if len(self.key) not in (16, 24, 32):
            raise ValueError("MASTER_ENCRYPTION_KEY must decode to 16/24/32 bytes")
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return ""
        nonce = os.urandom(12)
        ct = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        payload = nonce + ct
        return base64.b64encode(payload).decode()

    def decrypt_admin(self, encrypted_b64: str, current_user) -> str:
        # Only admins may decrypt
        if not getattr(current_user, 'is_admin', False):
            raise PermissionError("Admin privileges required to decrypt")
        if not encrypted_b64:
            return ""
        data = base64.b64decode(encrypted_b64)
        nonce = data[:12]
        ct = data[12:]
        try:
            pt = self.aesgcm.decrypt(nonce, ct, None)
            return pt.decode('utf-8')
        except Exception as e:
            raise


vault = CryptoVault()
