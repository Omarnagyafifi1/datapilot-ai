from app.llm.base_llm import BaseLLM
from typing import Optional
import re

class MockLLM(BaseLLM):
    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        prompt_lower = prompt.lower()
        if "intent classification engine" in prompt_lower:
            return "ADD"
        if "generate the sql" in prompt_lower or "rewrite sql" in prompt_lower or "correct sql" in prompt_lower:
            lines = prompt.split("\n")
            for line in reversed(lines):
                stripped = line.strip().upper()
                if stripped.startswith("SELECT") and "FROM" in stripped:
                    return line.strip()
            return "SELECT 1"
        if "insights" in prompt_lower or "insight" in prompt_lower:
            return '["Mock insight 1", "Mock insight 2", "Mock insight 3"]'
        if "suggestion" in prompt_lower:
            return '["Try filtering by date range", "Group results by category", "Sort by descending value"]'
        if "lesson" in prompt_lower or "scenario" in prompt_lower:
            return "What Went Wrong\nThe generated query failed.\nCorrect Approach\nUse the correct table alias.\nCorrect SQL\nSELECT 1\nKey Lesson\nAlways verify table names before querying."
        return f"Mock response for: {prompt}"
