import os
from typing import Optional, Tuple


# Try to import settings; fall back to defaults for testing
try:
    from app.core.config import settings
    # Normalize: strip leading dots from extensions (e.g. ".pdf" -> "pdf")
    _ALLOWED_EXTENSIONS = [e.lstrip(".").lower() for e in settings.allowed_extensions_list]
    _MAX_FILE_SIZE_BYTES = settings.max_file_size_bytes
except Exception:
    _ALLOWED_EXTENSIONS = ["pdf", "docx", "doc", "xlsx", "csv", "txt", "png", "jpg", "jpeg", "webp"]
    _MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


# Dangerous file extensions that should never be uploaded
DANGEROUS_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "msi", "scr", "pif", "vbs", "vbe", "js", "jse",
    "wsf", "wsh", "ps1", "psm1", "psd1", "reg", "inf", "hta", "cpl", "lnk",
    "application", "gadget", "msp", "mst", "paf", "rgs", "sct", "shb", "shs",
    "iso", "img", "vhd", "vhdx",
}

# MIME type to extension mapping for validation
SAFE_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/webp",
}


class FileSecurityValidator:
    """Validates uploaded files for security: type, size, extension, path traversal."""

    def validate_upload(
        self,
        filename: str,
        file_size: int,
        mime_type: str,
        file_content: Optional[bytes] = None,
    ) -> Tuple[bool, str]:
        """
        Validates file upload. Returns (is_valid, error_message).
        """
        # 1. Filename validation
        if not filename or len(filename) > 512:
            return False, "Fayl nomi yaroqsiz yoki juda uzun."

        # 2. Path traversal check
        if ".." in filename or "/" in filename or "\\" in filename:
            return False, "Fayl nomida xavfli belgilar aniqlandi (path traversal)."

        # 3. Null byte check
        if "\x00" in filename:
            return False, "Fayl nomida yashirin belgilar mavjud."

        # 4. Extension check
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if not ext:
            return False, "Fayl kengaytmasi aniqlanmadi."

        if ext in DANGEROUS_EXTENSIONS:
            return False, f"'{ext}' kengaytmasi yuklash uchun ruxsat etilmagan."

        allowed_exts = _ALLOWED_EXTENSIONS
        if ext not in allowed_exts:
            return False, f"'{ext}' kengaytmasi qo'llab-quvvatlanmaydi. Ruxsat etilgan: {', '.join(allowed_exts)}"

        # 5. Size check
        max_size = _MAX_FILE_SIZE_BYTES
        if file_size > max_size:
            max_mb = _MAX_FILE_SIZE_BYTES // (1024 * 1024)
            return False, f"Fayl hajmi {max_mb} MB dan oshmasligi kerak."

        if file_size == 0:
            return False, "Fayl bo'sh."

        # 6. MIME type validation
        if mime_type and mime_type not in SAFE_MIME_TYPES:
            return False, f"'{mime_type}' MIME turi ruxsat etilmagan."

        # 7. Content-based extension spoofing check (magic bytes)
        if file_content and len(file_content) >= 4:
            is_valid_magic, magic_msg = self._validate_magic_bytes(file_content, ext)
            if not is_valid_magic:
                return False, magic_msg

        return True, ""

    def _validate_magic_bytes(self, content: bytes, declared_ext: str) -> Tuple[bool, str]:
        """Checks file header bytes against declared extension."""
        header = content[:16]

        magic_map = {
            "pdf": b"%PDF",
            "doc": b"\xd0\xcf\x11\xe0",
            "docx": b"PK\x03\x04",
            "xlsx": b"PK\x03\x04",
            "png": b"\x89PNG",
            "jpg": b"\xff\xd8\xff",
            "jpeg": b"\xff\xd8\xff",
            "csv": None,  # Text-based, skip magic check
            "txt": None,  # Text-based, skip magic check
        }

        expected_magic = magic_map.get(declared_ext)
        if expected_magic is None:
            return True, ""

        if not header.startswith(expected_magic):
            return False, f"Fayl tarkibi '{declared_ext}' kengaytmasi bilan mos kelmaydi."

        return True, ""

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes filename for safe storage."""
        # Remove path components
        filename = os.path.basename(filename)
        # Remove null bytes
        filename = filename.replace("\x00", "")
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        return f"{name}{ext}"


file_security = FileSecurityValidator()
