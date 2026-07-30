from typing import Any, Dict, List


class DatabaseReader:
    def __init__(self, connection_string: str = ""):
        self.connection_string = connection_string

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        return []
