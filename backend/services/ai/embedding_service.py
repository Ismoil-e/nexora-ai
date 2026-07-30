from typing import List


class EmbeddingService:
    def __init__(self, model_name: str = "text-embedding-004"):
        self.model_name = model_name

    async def get_embedding(self, text: str) -> List[float]:
        # Return standard 768-dim mock vector or API embeddings
        return [0.0] * 768
