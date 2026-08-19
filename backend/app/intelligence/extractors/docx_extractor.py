import io
from docx import Document
from typing import Any

from app.intelligence.contracts.types import ExtractedChunk


class DocxIntelligenceExtractor:
    """Word DOC/DOCX Intelligence Extractor: preserves headings, paragraphs, lists, tables, and section structure."""

    async def extract(self, file_data: bytes) -> dict[str, Any]:
        doc = Document(io.BytesIO(file_data))
        chunks = []
        full_text_lines = []
        current_section = "General"
        chunk_idx = 0

        # Paragraphs & Headings
        current_paragraph_block = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            full_text_lines.append(text)

            # Heading detection
            if p.style.name.startswith("Heading"):
                current_section = text
                if current_paragraph_block:
                    block_text = "\n".join(current_paragraph_block)
                    chunks.append(
                        ExtractedChunk(
                            chunk_index=chunk_idx,
                            content=block_text,
                            token_count=len(block_text.split()),
                            section_title=current_section,
                            chunk_type="text",
                            metadata={"section": current_section},
                        )
                    )
                    chunk_idx += 1
                    current_paragraph_block = []
            else:
                current_paragraph_block.append(text)

        if current_paragraph_block:
            block_text = "\n".join(current_paragraph_block)
            chunks.append(
                ExtractedChunk(
                    chunk_index=chunk_idx,
                    content=block_text,
                    token_count=len(block_text.split()),
                    section_title=current_section,
                    chunk_type="text",
                    metadata={"section": current_section},
                )
            )
            chunk_idx += 1

        # Tables in Docx
        for t_idx, table in enumerate(doc.tables, start=1):
            table_rows = []
            for row in table.rows:
                row_cells = [c.text.strip() for c in row.cells]
                if any(row_cells):
                    table_rows.append(" | ".join(row_cells))

            if table_rows:
                table_text = f"[TABLE {t_idx} - Word Document]\n" + "\n".join(table_rows)
                full_text_lines.append(table_text)
                chunks.append(
                    ExtractedChunk(
                        chunk_index=chunk_idx,
                        content=table_text,
                        token_count=len(table_text.split()),
                        section_title=f"Table {t_idx}",
                        chunk_type="table",
                        metadata={"table_index": t_idx},
                    )
                )
                chunk_idx += 1

        # Docx core properties metadata
        metadata = {}
        if doc.core_properties:
            metadata["title"] = doc.core_properties.title
            metadata["author"] = doc.core_properties.author
            metadata["category"] = doc.core_properties.category
            metadata["keywords"] = doc.core_properties.keywords

        return {
            "full_text": "\n".join(full_text_lines),
            "page_count": 1,
            "chunks": chunks,
            "metadata": metadata,
        }
