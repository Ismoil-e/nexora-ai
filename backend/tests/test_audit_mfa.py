"""Tests for AuditLogger secret sanitization and MFA Manager TOTP."""
import pytest
from app.security.core.audit_logger import AuditLogger
from app.security.core.mfa_manager import MFAManager


audit = AuditLogger()
mfa = MFAManager()


class TestAuditLoggerSanitization:
    def test_password_redacted(self):
        result = audit.sanitize_payload({"password": "supersecret123"})
        assert result["password"] == "[REDACTED_SECRET]"

    def test_token_redacted(self):
        result = audit.sanitize_payload({"access_token": "eyJhbGciOiJIUzI1NiJ9"})
        assert result["access_token"] == "[REDACTED_SECRET]"

    def test_nested_secrets_redacted(self):
        data = {"user": {"name": "John", "api_key": "sk-123"}}
        result = audit.sanitize_payload(data)
        assert result["user"]["name"] == "John"
        assert result["user"]["api_key"] == "[REDACTED_SECRET]"

    def test_deeply_nested_secret_redacted(self):
        data = {"outer": {"inner": {"secret_key": "my-secret"}}}
        result = audit.sanitize_payload(data)
        assert result["outer"]["inner"]["secret_key"] == "[REDACTED_SECRET]"

    def test_jwt_token_in_string_redacted(self):
        long_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = audit.sanitize_payload({"data": long_jwt})
        assert result["data"] == "[REDACTED_TOKEN_STRING]"

    def test_normal_data_preserved(self):
        data = {"action": "login", "user_id": "12345", "ip": "192.168.1.1"}
        result = audit.sanitize_payload(data)
        assert result == data

    def test_list_sanitization(self):
        data = [{"password": "secret"}, {"name": "safe"}]
        result = audit.sanitize_payload(data)
        assert result[0]["password"] == "[REDACTED_SECRET]"
        assert result[1]["name"] == "safe"

    def test_secret_key_redacted(self):
        result = audit.sanitize_payload({"secret_key": "my-secret"})
        assert result["secret_key"] == "[REDACTED_SECRET]"

    def test_bearer_in_long_string_redacted(self):
        # Must be > 60 chars to trigger redaction
        long_auth = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature_here"
        data = {"auth": long_auth}
        result = audit.sanitize_payload(data)
        assert result["auth"] == "[REDACTED_TOKEN_STRING]"

    def test_credentials_key_redacted(self):
        result = audit.sanitize_payload({"credentials": {"user": "admin"}})
        # "credentials" is in REDACT_KEYS, so the entire value is redacted
        assert result["credentials"] == "[REDACTED_SECRET]"

    def test_authorization_key_redacted(self):
        result = audit.sanitize_payload({"authorization": "Bearer token123"})
        assert result["authorization"] == "[REDACTED_SECRET]"

    def test_empty_dict(self):
        assert audit.sanitize_payload({}) == {}

    def test_none_passthrough(self):
        assert audit.sanitize_payload(None) is None

    def test_int_passthrough(self):
        assert audit.sanitize_payload(42) == 42


class TestMFAManager:
    def test_secret_generation(self):
        secret = mfa.generate_secret()
        assert len(secret) >= 16
        assert secret.isalnum()

    def test_recovery_codes_format(self):
        codes = mfa.generate_recovery_codes(8)
        assert len(codes) == 8
        for code in codes:
            assert "-" in code
            assert len(code) == 9  # AAAA-BBBB

    def test_recovery_code_hash_deterministic(self):
        code = "ABCD-1234"
        hash1 = mfa.hash_recovery_code(code)
        hash2 = mfa.hash_recovery_code(code)
        assert hash1 == hash2

    def test_recovery_code_hash_case_insensitive(self):
        hash1 = mfa.hash_recovery_code("ABCD-1234")
        hash2 = mfa.hash_recovery_code("abcd-1234")
        assert hash1 == hash2

    def test_totp_generate_and_verify(self):
        secret = mfa.generate_secret()
        code = mfa.generate_totp_code(secret)
        assert len(code) == 6
        assert code.isdigit()
        assert mfa.verify_totp(secret, code) is True

    def test_totp_wrong_code_fails(self):
        secret = mfa.generate_secret()
        assert mfa.verify_totp(secret, "000000") is False

    def test_totp_non_numeric_fails(self):
        secret = mfa.generate_secret()
        assert mfa.verify_totp(secret, "abcdef") is False

    def test_totp_wrong_length_fails(self):
        secret = mfa.generate_secret()
        assert mfa.verify_totp(secret, "12345") is False
        assert mfa.verify_totp(secret, "1234567") is False

    def test_provisioning_uri_format(self):
        secret = mfa.generate_secret()
        uri = mfa.get_provisioning_uri(secret, "user@test.com", "Nexora AI")
        assert "otpauth://totp/" in uri
        assert "secret=" in uri
        assert "Nexora" in uri

    def test_enrollment_returns_all_fields(self):
        result = mfa.enroll("user@test.com", "Nexora AI")
        assert result.secret
        assert result.provisioning_uri
        assert len(result.recovery_codes) == 8
