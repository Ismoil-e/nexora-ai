from typing import Any, Dict


class ExcelReader:
    @staticmethod
    def read_excel(file_path: str) -> Dict[str, Any]:
        return {"file_path": file_path, "sheets": [], "data": []}
