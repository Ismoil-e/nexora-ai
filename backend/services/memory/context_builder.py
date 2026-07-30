from typing import List, Dict, Any


class ContextBuilder:
    @staticmethod
    def build_context(memories: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> str:
        ctx_parts = []
        if memories:
            ctx_parts.append("User Memory Context:\n" + "\n".join([f"- {m.get('key')}: {m.get('value')}" for m in memories]))
        if documents:
            ctx_parts.append("Document Context:\n" + "\n".join([f"- {d.get('title')}: {d.get('content')}" for d in documents]))
        return "\n\n".join(ctx_parts)
