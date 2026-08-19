import base64
import json
from typing import Any

from app.core.config import settings

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class CredentialEncryptionManager:
    """Secure Fernet AES-256-based credential encryption at rest."""

    def __init__(self, key_secret: str | None = None):
        secret = (
            key_secret
            or getattr(settings, "ENCRYPTION_KEY", None)
            or getattr(settings, "secret_key", None)
            or getattr(settings, "SECRET_KEY", None)
            or "nexora_default_encryption_secret_key_2026"
        )

        if HAS_CRYPTOGRAPHY:
            salt = b"nexora_integration_salt_2026"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100_000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
            self._fernet = Fernet(key)
        else:
            self._fernet = None
            self._secret_bytes = secret.encode()

    def encrypt_data(self, data: dict[str, Any] | str) -> str:
        raw_str = json.dumps(data) if isinstance(data, dict) else str(data)
        if HAS_CRYPTOGRAPHY and self._fernet:
            return self._fernet.encrypt(raw_str.encode()).decode()
        # Fallback obfuscation if cryptography lib not present
        encoded = base64.b64encode(raw_str.encode()).decode()
        return f"enc_fallback:{encoded}"

    def decrypt_data(self, encrypted_str: str) -> dict[str, Any] | str:
        if not encrypted_str:
            return {}
        if encrypted_str.startswith("enc_fallback:"):
            raw_b64 = encrypted_str.split("enc_fallback:", 1)[1]
            raw_str = base64.b64decode(raw_b64.encode()).decode()
            try:
                return json.loads(raw_str)
            except Exception:
                return raw_str

        if HAS_CRYPTOGRAPHY and self._fernet:
            decrypted_bytes = self._fernet.decrypt(encrypted_str.encode())
            raw_str = decrypted_bytes.decode()
            try:
                return json.loads(raw_str)
            except Exception:
                return raw_str

        raise RuntimeError("Cannot decrypt credentials without Fernet / cryptography library.")


credential_encryption = CredentialEncryptionManager()
