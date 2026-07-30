from typing import List, Dict, Any


class MemoryRanker:
    @staticmethod
    def rank_memories(memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        # Sort by relevance score
        return sorted(memories, key=lambda x: x.get("relevance_score", 0), reverse=True)
