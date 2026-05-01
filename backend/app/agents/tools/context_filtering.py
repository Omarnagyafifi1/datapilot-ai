import json
from app.agents.prompts import CONTEXT_FILTER_PROMPT
from app.llm.base_llm import BaseLLM

def filter_schema_context(llm: BaseLLM, full_schema_str: str, question: str) -> str:
    """Uses LLM to filter the schema to only include relevant tables/columns."""
    try:
        prompt = CONTEXT_FILTER_PROMPT.format(
            full_schema=full_schema_str,
            question=question
        )
        response = llm.generate(prompt).strip()
        
        # Simple extraction if LLM wraps in markdown
        if response.startswith("```"):
            lines = response.splitlines()
            if len(lines) >= 3:
                response = "\n".join(lines[1:-1]).strip()

        # Validate JSON
        json.loads(response)
        return response
    except Exception:
        # Fallback to full schema on any error
        return full_schema_str
