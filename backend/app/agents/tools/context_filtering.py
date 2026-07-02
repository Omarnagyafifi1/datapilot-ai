import json
from app.agents.prompts import CONTEXT_FILTER_PROMPT
from app.llm.base_llm import BaseLLM

def filter_schema_context(llm: BaseLLM, full_schema_str: str, question: str) -> str:
    """Uses LLM to filter the schema to only include relevant tables/columns.
    
    For small schemas (< 10 tables), skips filtering to avoid removing needed tables.
    """
    try:
        schema_data = json.loads(full_schema_str)
        tables = schema_data.get("tables", [])
        if len(tables) <= 10:
            return full_schema_str

        prompt = CONTEXT_FILTER_PROMPT.format(
            full_schema=full_schema_str,
            question=question
        )
        response = llm.generate(prompt).strip()
        
        if response.startswith("```"):
            lines = response.splitlines()
            if len(lines) >= 3:
                response = "\n".join(lines[1:-1]).strip()

        filtered = json.loads(response)
        if not filtered.get("tables"):
            return full_schema_str

        return response
    except Exception:
        return full_schema_str
