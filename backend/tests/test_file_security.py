"""Tests for FileSecurityValidator — upload validation, path traversal, dangerous files."""
import pytest
from app.security.core.file_security import FileSecurityValidator


validator = FileSecurityValidator()


class TestFileSecurityValidation:
    def test_valid_pdf(self):
        ok, msg = validator.validate_upload("report.pdf", 1024, "application/pdf")
        assert ok is True

    def test_valid_docx(self):
        ok, msg = validator.validate_upload("doc.docx", 2048, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert ok is True

    def test_dangerous_exe_blocked(self):
        ok, msg = validator.validate_upload("malware.exe", 1024, "application/octet-stream")
        assert ok is False
        assert "ruxsat etilmagan" in msg.lower() or "kengaytma" in msg.lower()

    def test_dangerous_bat_blocked(self):
        ok, msg = validator.validate_upload("script.bat", 100, "text/plain")
        assert ok is False

    def test_dangerous_vbs_blocked(self):
        ok, msg = validator.validate_upload("payload.vbs", 200, "text/plain")
        assert ok is False

    def test_path_traversal_blocked(self):
        ok, msg = validator.validate_upload("../../../etc/passwd.pdf", 1024, "application/pdf")
        assert ok is False
        assert "path traversal" in msg.lower() or "xavfli" in msg.lower()

    def test_backslash_path_traversal_blocked(self):
        ok, msg = validator.validate_upload("..\\..\\windows\\system32.pdf", 1024, "application/pdf")
        assert ok is False

    def test_null_byte_blocked(self):
        ok, msg = validator.validate_upload("file\x00.pdf", 1024, "application/pdf")
        assert ok is False

    def test_empty_file_blocked(self):
        ok, msg = validator.validate_upload("empty.pdf", 0, "application/pdf")
        assert ok is False

    def test_oversized_file_blocked(self):
        # 60MB > default 50MB limit
        ok, msg = validator.validate_upload("huge.pdf", 60 * 1024 * 1024, "application/pdf")
        assert ok is False
        assert "hajmi" in msg.lower() or "MB" in msg

    def test_unsupported_extension_blocked(self):
        ok, msg = validator.validate_upload("archive.zip", 1024, "application/zip")
        assert ok is False

    def test_too_long_filename_blocked(self):
        ok, msg = validator.validate_upload("a" * 600 + ".pdf", 1024, "application/pdf")
        assert ok is False

    def test_sanitize_filename_removes_path(self):
        result = validator.sanitize_filename("/etc/passwd")
        assert "/" not in result

    def test_sanitize_filename_limits_length(self):
        long_name = "a" * 300 + ".pdf"
        result = validator.sanitize_filename(long_name)
        assert len(result) <= 210  # 200 name + ext

    def test_magic_bytes_pdf_valid(self):
        content = b"%PDF-1.4 fake content here..."
        ok, msg = validator.validate_upload("test.pdf", len(content), "application/pdf", content)
        assert ok is True

    def test_magic_bytes_pdf_wrong_header(self):
        content = b"PK\x03\x04 this is actually a zip/docx"
        ok, msg = validator.validate_upload("fake.pdf", len(content), "application/pdf", content)
        assert ok is False

    def test_magic_bytes_png_valid(self):
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        ok, msg = validator.validate_upload("image.png", len(content), "image/png", content)
        assert ok is True
