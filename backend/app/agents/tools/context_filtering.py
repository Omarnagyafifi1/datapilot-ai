import json
import re
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
        response = llm.generate(prompt, max_tokens=1024).strip()
        
        # Extract JSON from the response regardless of markdown wrapping
        json_str = None
        
        # Strategy 1: Extract from ```json ... ``` code block
        m = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', response, re.DOTALL)
        if m:
            json_str = m.group(1)
        
        # Strategy 2: Find first { and last } in the raw response
        if json_str is None:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end > start:
                json_str = response[start:end + 1]
        
        # Strategy 3: Try the raw response as-is
        if json_str is None:
            json_str = response

        filtered = json.loads(json_str)
        if not filtered.get("tables"):
            return full_schema_str

        return json.dumps(filtered)
    except Exception:
        return full_schema_str
