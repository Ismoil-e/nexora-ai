from typing import List, Dict, Any


class PromptBuilder:
    @staticmethod
    def build_prompt(user_query: str, context: str = "", role: str = "assistant") -> str:
        prompt = f"Role: {role}\n"
        if context:
            prompt += f"Context:\n{context}\n\n"
        prompt += f"User Question: {user_query}\nAnswer in clear Uzbek language."
        return prompt
