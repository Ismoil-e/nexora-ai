import io
import openpyxl
from typing import Any

from app.intelligence.contracts.types import ExtractedChunk


class ExcelIntelligenceExtractor:
    """Excel Intelligence Extractor: analyzes Workbooks, Worksheets, headers, datasets, and summary metrics."""

    async def extract(self, file_data: bytes) -> dict[str, Any]:
        wb = openpyxl.load_workbook(io.BytesIO(file_data), data_only=True, read_only=True)
        chunks = []
        full_text_lines = []
        sheets_metadata = []
        chunk_idx = 0

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue

            # Identify headers (first non-empty row)
            header_row_idx = 0
            for r_idx, row in enumerate(rows):
                if any(row):
                    header_row_idx = r_idx
                    break

            headers = [str(c or f"Col_{i+1}").strip() for i, c in enumerate(rows[header_row_idx])]
            data_rows = rows[header_row_idx + 1 :]

            # Semantic Column Profiling (Sales, Revenue, Date, Customer, Product)
            metrics_found = []
            for col in headers:
                col_lower = col.lower()
                if any(k in col_lower for k in ("sales", "revenue", "amount", "price", "total", "cost", "budget")):
                    metrics_found.append(col)

            sheet_summary = f"[WORKSHEET: {sheet_name}]\nHeaders: {', '.join(headers)}\nTotal Rows: {len(data_rows)}\nKey Metrics: {', '.join(metrics_found) if metrics_found else 'None'}"
            full_text_lines.append(sheet_summary)

            # Chunk worksheet data
            row_snippets = []
            for r_idx, row in enumerate(data_rows[:500], start=1):  # Sample up to 500 rows
                formatted_row = " | ".join([f"{headers[i] if i < len(headers) else 'col'}: {val}" for i, val in enumerate(row) if val is not None])
                if formatted_row.strip():
                    row_snippets.append(formatted_row)

            worksheet_chunk_text = f"{sheet_summary}\n\n[DATA ROWS SAMPLE]\n" + "\n".join(row_snippets[:100])
            full_text_lines.append(f"{sheet_summary}\n" + "\n".join(row_snippets[:100]))
            chunks.append(
                ExtractedChunk(
                    chunk_index=chunk_idx,
                    content=worksheet_chunk_text,
                    token_count=len(worksheet_chunk_text.split()),
                    section_title=f"Sheet: {sheet_name}",
                    chunk_type="table",
                    metadata={
                        "sheet_name": sheet_name,
                        "columns": headers,
                        "row_count": len(data_rows),
                        "metrics": metrics_found,
                    },
                )
            )
            chunk_idx += 1

            sheets_metadata.append({
                "sheet_name": sheet_name,
                "columns": headers,
                "row_count": len(data_rows),
                "metrics": metrics_found,
            })

        wb.close()
        return {
            "full_text": "\n\n".join(full_text_lines),
            "page_count": len(sheets_metadata),
            "chunks": chunks,
            "metadata": {"sheets": sheets_metadata},
        }
