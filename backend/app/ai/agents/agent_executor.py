import json
import re
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.tools import ToolExecutionContext, ToolRegistry
from app.services.ai_service import AIService


class AgentExecutionResult:
    def __init__(self, output: str, steps: list[dict], total_tokens: int, duration_ms: int):
        self.output = output
        self.steps = steps
        self.total_tokens = total_tokens
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "output": self.output,
            "steps": self.steps,
            "total_tokens": self.total_tokens,
            "duration_ms": self.duration_ms,
        }


class AgentExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService(db)
        self.tool_registry = ToolRegistry()

    async def run(
        self,
        provider: str,
        model: str,
        system_prompt: str | None,
        user_input: str,
        context: ToolExecutionContext,
        allowed_tools: list[str] | None = None,
        max_steps: int = 5,
    ) -> AgentExecutionResult:
        start_time = time.perf_counter()
        tools_prompt = self.tool_registry.get_tools_prompt(allowed_tools)

        prompt_prefix = system_prompt or "Sen korxona uchun mas'uliyatli AI agentisan."
        base_system = (
            f"{prompt_prefix}\n\n"
            "Siz topshiriqlarni bajarish uchun quyidagi vositalarga (Tools) egasiz:\n"
            f"{tools_prompt}\n\n"
            "FIKRLASH VA HARAKAT QILISH FORMATI (ReAct Pattern):\n"
            "Har bir qadamda quyidagi strukturadan foydalaning:\n"
            "Thought: Topshiriq va keyingi mantiqiy harakat haqida fikringiz.\n"
            "Action: <tool_name>\n"
            "Action Input: <JSON formatidagi parametrlar>\n\n"
            "Agar topilgan ma'lumotlar yetarli bo'lsa yoki vositalar shart bo'lmasa:\n"
            "Thought: Yakuniy xulosaga keldim.\n"
            "Final Answer: <Foydalanuvchi uchun to'liq va aniq javob>\n"
        )

        messages = [{"role": "user", "content": user_input}]
        steps_history = []
        total_tokens = 0

        for step in range(1, max_steps + 1):
            response = await self.ai_service.chat(
                provider=provider,
                model=model,
                messages=messages,
                system_prompt=base_system,
                temperature=0.2,
            )

            content = response.get("content", "")
            total_tokens += response.get("token_count", 0)

            # Parse Final Answer
            if "Final Answer:" in content:
                final_answer = content.split("Final Answer:", 1)[1].strip()
                steps_history.append({
                    "step": step,
                    "type": "final_answer",
                    "content": final_answer,
                })
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return AgentExecutionResult(final_answer, steps_history, total_tokens, duration_ms)

            # Parse Action and Action Input
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", content)
            action_input_match = re.search(r"Action Input:\s*(\{.*\}|[^\n]+)", content, re.DOTALL)

            if action_match:
                tool_name = action_match.group(1).strip()
                input_raw = action_input_match.group(1).strip() if action_input_match else "{}"

                try:
                    params = json.loads(input_raw) if input_raw.startswith("{") else {"query": input_raw}
                except json.JSONDecodeError:
                    params = {"query": input_raw}

                tool = self.tool_registry.get_tool(tool_name)
                if tool:
                    try:
                        observation = await tool.execute(params, context)
                    except Exception as e:
                        observation = f"Xato: Vosita ishlatishda xatolik yuz berdi ({str(e)})"
                else:
                    observation = f"Xato: '{tool_name}' nomli vosita mavjud emas."

                steps_history.append({
                    "step": step,
                    "thought": content,
                    "action": tool_name,
                    "action_input": params,
                    "observation": observation,
                })

                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                # No action found, treat whole content as final answer
                steps_history.append({
                    "step": step,
                    "type": "direct_response",
                    "content": content,
                })
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return AgentExecutionResult(content, steps_history, total_tokens, duration_ms)

        # Fallback if max steps reached
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return AgentExecutionResult(
            "Agent maksimal bajarish qadamlariga erishdi.",
            steps_history,
            total_tokens,
            duration_ms,
        )
