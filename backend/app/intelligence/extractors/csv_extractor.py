import csv
import io
from typing import Any

from app.intelligence.contracts.types import ExtractedChunk


class CsvIntelligenceExtractor:
    """CSV & Structured Data Extractor: detects schema, data types, missing values, and columns."""

    async def extract(self, file_data: bytes) -> dict[str, Any]:
        text_content = file_data.decode("utf-8", errors="replace")
        reader = list(csv.reader(io.StringIO(text_content)))
        if not reader:
            return {"full_text": "", "page_count": 1, "chunks": [], "metadata": {}}

        headers = [h.strip() for h in reader[0]]
        data_rows = reader[1:]

        # Schema & Type Inference
        column_types = {}
        for idx, col in enumerate(headers):
            sample_vals = [row[idx] for row in data_rows[:20] if idx < len(row) and row[idx].strip()]
            col_type = "string"
            if sample_vals:
                if all(v.replace(".", "", 1).isdigit() for v in sample_vals):
                    col_type = "numeric"
                elif any("-" in v or "/" in v for v in sample_vals) and any(char.isdigit() for char in sample_vals[0]):
                    col_type = "datetime"
            column_types[col] = col_type

        formatted_rows = [" | ".join([f"{headers[i] if i < len(headers) else 'col'}: {val}" for i, val in enumerate(row)]) for row in data_rows[:100]]

        summary_text = (
            f"[CSV DATASET]\nColumns ({len(headers)}): {', '.join(headers)}\n"
            f"Schema Types: {column_types}\nTotal Rows: {len(data_rows)}\n\n[SAMPLE ROWS]\n" + "\n".join(formatted_rows)
        )

        chunk = ExtractedChunk(
            chunk_index=0,
            content=summary_text,
            token_count=len(summary_text.split()),
            section_title="CSV Dataset",
            chunk_type="table",
            metadata={"columns": headers, "schema": column_types, "total_rows": len(data_rows)},
        )

        return {
            "full_text": summary_text,
            "page_count": 1,
            "chunks": [chunk],
            "metadata": {"columns": headers, "schema": column_types, "total_rows": len(data_rows)},
        }
