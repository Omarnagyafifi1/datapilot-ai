"""Debug evaluation scores - test syntax check and LLM eval"""
import json, sqlite3, sys
sys.path.insert(0, ".")

from app.services.evaluation_service import (
    _syntax_check, SQL_CORRECTNESS_PROMPT, _llm_eval,
    evaluate_sql, post_evaluation_to_langsmith
)
from app.core.config import settings

# Test syntax check with real generated SQL patterns
test_cases = [
    "SELECT count(country) FROM customers WHERE country = 'Egypt' LIMIT 1000;",
    "SELECT product_name, unit_price FROM products WHERE category = 'Electronics' LIMIT 1000",
    "SELECT SUM(total_amount) FROM orders WHERE status = 'Completed' LIMIT 1000;",
    "SELECT t1.dept_name, AVG(t2.salary) AS average_salary FROM departments AS t1 JOIN employees AS t2 ON t1.dept_id = t2.dept_id GROUP BY t1.dept_name LIMIT 1000;",
]

print("=== Syntax Check ===")
for sql in test_cases:
    result = _syntax_check(sql, "sqlite")
    print(f'  valid={result["valid"]}, error={result["error"]}')
    print(f'  sql={sql[:60]}...')

# Test LLM evaluation if key is available
print(f"\n=== LLM Eval Test ===")
print(f"API key available: {bool(settings.OPENROUTER_API_KEY)}")

if settings.OPENROUTER_API_KEY:
    from app.llm.factory import get_llm
    llm = get_llm(provider=settings.LLM_PROVIDER)
    
    # Test 1: LLM as judge
    prompt = SQL_CORRECTNESS_PROMPT.format(
        question="How many customers are from Egypt?",
        sql="SELECT count(*) FROM customers WHERE country = 'Egypt' LIMIT 1000",
        results=[{"count(*)": 1}],
    )
    print(f"\n  Prompt (first 200 chars): {prompt[:200]}...")
    result = _llm_eval(prompt, llm)
    print(f"  Eval result: {result}")

    # Test 2: Full evaluate_sql
    scores = evaluate_sql(
        question="How many customers are from Egypt?",
        sql="SELECT count(*) FROM customers WHERE country = 'Egypt' LIMIT 1000",
        results=[{"count(*)": 1}],
        llm=llm,
    )
    print(f"\n  Full eval scores: {json.dumps(scores, indent=2)}")
else:
    print("  Skipping LLM tests - no API key configured")
    print("  Set OPENROUTER_API_KEY in .env to test LLM evaluation")
