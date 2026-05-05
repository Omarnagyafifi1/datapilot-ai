from app.llm.base_llm import BaseLLM

class MockLLM(BaseLLM):
    def generate(self, prompt: str) -> str:
        if "intent classification engine" in prompt.lower():
            return "ADD"
        return f"Mock response for: {prompt}"
