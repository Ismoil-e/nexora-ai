import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from typing import List, Tuple
import uuid

from app.security.contracts.types import MFAEnrollmentResult


class MFAManager:
    """RFC 6238 compliant Multi-Factor Authentication (TOTP) and Recovery Code Manager."""

    TIME_STEP_SECONDS = 30
    DIGITS = 6

    def generate_secret(self) -> str:
        """Generates a random 32-character base32 secret."""
        random_bytes = os.urandom(20)
        return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

    def generate_recovery_codes(self, count: int = 8) -> List[str]:
        """Generates cryptographically random 8-character recovery codes (e.g., 'A1B2-C3D4')."""
        codes = []
        for _ in range(count):
            raw = secrets.token_hex(4).upper()
            formatted = f"{raw[:4]}-{raw[4:]}"
            codes.append(formatted)
        return codes

    def hash_recovery_code(self, code: str) -> str:
        """Hashes recovery code with SHA-256."""
        normalized = code.strip().upper().replace(" ", "")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get_provisioning_uri(self, secret: str, account_name: str, issuer_name: str = "Nexora AI") -> str:
        """Generates the standard otpauth:// URL for scanning into Google Authenticator or 1Password."""
        import urllib.parse

        encoded_issuer = urllib.parse.quote(issuer_name)
        encoded_account = urllib.parse.quote(account_name)
        return (
            f"otpauth://totp/{encoded_issuer}:{encoded_account}"
            f"?secret={secret}&issuer={encoded_issuer}&algorithm=SHA1&digits={self.DIGITS}&period={self.TIME_STEP_SECONDS}"
        )

    def generate_totp_code(self, secret: str, for_time: int | None = None) -> str:
        """Generates the current 6-digit TOTP code for a given secret."""
        t = int(for_time if for_time is not None else time.time())
        counter = t // self.TIME_STEP_SECONDS

        # Normalize secret
        padding = (8 - (len(secret) % 8)) % 8
        padded_secret = secret + ("=" * padding)
        key = base64.b32decode(padded_secret, casefold=True)

        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        binary = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
        otp = binary % (10**self.DIGITS)
        return f"{otp:0{self.DIGITS}d}"

    def verify_totp(self, secret: str, code: str, window: int = 1) -> bool:
        """Verifies TOTP code within +/- window time steps (30s each) to account for clock skew."""
        clean_code = str(code).strip()
        if not clean_code.isdigit() or len(clean_code) != self.DIGITS:
            return False

        current_time = int(time.time())
        for step in range(-window, window + 1):
            t = current_time + (step * self.TIME_STEP_SECONDS)
            expected = self.generate_totp_code(secret, for_time=t)
            if hmac.compare_digest(clean_code, expected):
                return True
        return False

    def enroll(self, email: str, company_name: str = "Nexora AI") -> MFAEnrollmentResult:
        secret = self.generate_secret()
        uri = self.get_provisioning_uri(secret, email, issuer_name=company_name)
        codes = self.generate_recovery_codes()
        return MFAEnrollmentResult(secret=secret, provisioning_uri=uri, recovery_codes=codes)


mfa_manager = MFAManager()
