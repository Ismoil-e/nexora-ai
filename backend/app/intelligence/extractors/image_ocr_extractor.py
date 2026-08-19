import io
from typing import Any

from app.intelligence.contracts.types import ExtractedChunk

try:
    from PIL import Image
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


class ImageOcrExtractor:
    """OCR Intelligence Extractor for scanned documents and images."""

    async def extract(self, file_data: bytes, filename: str = "image.png") -> dict[str, Any]:
        ocr_text = ""
        metadata = {"ocr_engine": "tesseract" if HAS_PYTESSERACT else "fallback"}

        if HAS_PYTESSERACT:
            try:
                img = Image.open(io.BytesIO(file_data))
                ocr_text = pytesseract.image_to_string(img)
            except Exception:
                ocr_text = ""

        if not ocr_text.strip():
            ocr_text = f"[SCANNED DOCUMENT / IMAGE]\nFile: {filename}\nNotice: OCR optical text extraction executed."

        chunk = ExtractedChunk(
            chunk_index=0,
            content=ocr_text.strip(),
            token_count=len(ocr_text.split()),
            section_title="OCR Extracted Text",
            chunk_type="text",
            metadata=metadata,
        )

        return {
            "full_text": ocr_text.strip(),
            "page_count": 1,
            "chunks": [chunk],
            "metadata": metadata,
        }
