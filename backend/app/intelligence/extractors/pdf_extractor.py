import io
import pdfplumber
from typing import Any

from app.intelligence.contracts.types import ExtractedChunk


class PdfIntelligenceExtractor:
    """PDF Intelligence Extractor: extracts text, page boundaries, headings, tables, and page-level citations."""

    async def extract(self, file_data: bytes) -> dict[str, Any]:
        pages_content = []
        chunks = []
        metadata = {}
        total_pages = 0

        with pdfplumber.open(io.BytesIO(file_data)) as pdf:
            total_pages = len(pdf.pages)
            if pdf.metadata:
                metadata["title"] = pdf.metadata.get("Title") or pdf.metadata.get("title")
                metadata["author"] = pdf.metadata.get("Author") or pdf.metadata.get("author")
                metadata["creator"] = pdf.metadata.get("Creator")

            chunk_idx = 0
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages_content.append(text)

                # Table extraction
                tables = page.extract_tables()
                if tables:
                    for t_idx, table in enumerate(tables):
                        table_str_rows = [" | ".join([str(cell or "").strip() for cell in row]) for row in table if any(row)]
                        if table_str_rows:
                            table_text = f"[TABLE Page {idx} - Table {t_idx + 1}]\n" + "\n".join(table_str_rows)
                            chunks.append(
                                ExtractedChunk(
                                    chunk_index=chunk_idx,
                                    content=table_text,
                                    token_count=len(table_text.split()),
                                    page_number=idx,
                                    chunk_type="table",
                                    metadata={"page": idx, "table_index": t_idx + 1},
                                )
                            )
                            chunk_idx += 1

                # Page text chunking with page citation tag
                if text.strip():
                    chunks.append(
                        ExtractedChunk(
                            chunk_index=chunk_idx,
                            content=f"[PAGE {idx}]\n{text.strip()}",
                            token_count=len(text.split()),
                            page_number=idx,
                            chunk_type="text",
                            metadata={"page": idx, "citation": f"Page {idx}"},
                        )
                    )
                    chunk_idx += 1

        full_text = "\n\n".join(pages_content)
        return {
            "full_text": full_text,
            "page_count": total_pages,
            "chunks": chunks,
            "metadata": metadata,
        }
