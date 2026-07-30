from typing import Any, Dict


class ResponseFormatter:
    @staticmethod
    def format_json_response(data: Any, message: str = "Success", status_code: int = 200) -> Dict[str, Any]:
        return {
            "status": status_code,
            "message": message,
            "data": data,
        }
