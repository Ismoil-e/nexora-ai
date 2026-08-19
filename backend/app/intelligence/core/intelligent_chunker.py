from typing import Any
from app.intelligence.contracts.types import ExtractedChunk


class IntelligentChunker:
    """Structure-aware chunker preserving section headers, page numbers, tables, and traceable source citations."""

    def __init__(self, target_chunk_size: int = 800, overlap: int = 150):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def process_chunks(self, raw_chunks: list[ExtractedChunk]) -> list[ExtractedChunk]:
        if not raw_chunks:
            return []

        processed = []
        chunk_counter = 0

        for r_chunk in raw_chunks:
            # If chunk is already structured (table or page block), keep intact
            if r_chunk.chunk_type in ("table", "heading") or len(r_chunk.content) <= self.target_chunk_size:
                processed.append(
                    ExtractedChunk(
                        chunk_index=chunk_counter,
                        content=r_chunk.content,
                        token_count=len(r_chunk.content.split()),
                        page_number=r_chunk.page_number,
                        section_title=r_chunk.section_title,
                        chunk_type=r_chunk.chunk_type,
                        metadata=r_chunk.metadata,
                    )
                )
                chunk_counter += 1
            else:
                # Sub-chunk text along paragraph/semantic boundaries
                paragraphs = r_chunk.content.split("\n\n")
                current_block = []
                current_len = 0

                for para in paragraphs:
                    para_len = len(para)
                    if current_len + para_len > self.target_chunk_size and current_block:
                        block_text = "\n\n".join(current_block)
                        processed.append(
                            ExtractedChunk(
                                chunk_index=chunk_counter,
                                content=block_text,
                                token_count=len(block_text.split()),
                                page_number=r_chunk.page_number,
                                section_title=r_chunk.section_title,
                                chunk_type="text",
                                metadata=r_chunk.metadata,
                            )
                        )
                        chunk_counter += 1
                        current_block = [para]
                        current_len = para_len
                    else:
                        current_block.append(para)
                        current_len += para_len

                if current_block:
                    block_text = "\n\n".join(current_block)
                    processed.append(
                        ExtractedChunk(
                            chunk_index=chunk_counter,
                            content=block_text,
                            token_count=len(block_text.split()),
                            page_number=r_chunk.page_number,
                            section_title=r_chunk.section_title,
                            chunk_type="text",
                            metadata=r_chunk.metadata,
                        )
                    )
                    chunk_counter += 1

        return processed


intelligent_chunker = IntelligentChunker()
