import os
import json
from typing import Any, Dict, List, Optional


class LLMService:
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    async def generate_response(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        # High level wrapper for LLM generation
        last_user_msg = messages[-1]["content"] if messages else ""
        return f"[LLM Response for: {last_user_msg}]"
