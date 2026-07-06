"""
Lightweight BIRD-Style Text-to-SQL Evaluation Runner.
Calls LLM ONCE per query (SQL generation only) -- no graph overhead.
Fits within free-tier limits (~24 LLM calls per full eval).
"""
import json, time, sqlite3, re, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import bird_data.generate_eval_dataset as gen
from app.agents.prompts import SQL_GENERATION_PROMPT, SQL_SYSTEM_MESSAGE
from app.llm.factory import get_llm
from app.core.config import settings

GREEN = "\033[92m"; CYAN = "\033[96m"; YELLOW = "\033[93m"; RED = "\033[91m"; BOLD = "\033[1m"; RESET = "\033[0m"
OK = f"{GREEN}[OK]{RESET}"; FAIL = f"{RED}[FAIL]{RESET}"; WARN = f"{YELLOW}[WARN]{RESET}"

def hdr(t): print(f"\n{BOLD}{CYAN}={'='*70}{RESET}\n{BOLD}{CYAN}  {t}{RESET}\n{BOLD}{CYAN}={'='*70}{RESET}")

def build_schema_str(db_id: str) -> str:
    sql = gen.SCHEMAS[db_id]["sql"]
    tables = {}
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt.upper().startswith("CREATE TABLE"):
            lines = stmt.split("\n")
            table_name = lines[0].split("(")[0].split()[-1].strip()
            cols = []
            for line in lines[1:]:
                line = line.strip().rstrip(",").rstrip(")")
                if not line or line.upper().startswith("PRIMARY KEY") or line.upper().startswith("FOREIGN KEY") or line.upper().startswith("INSERT"):
                    continue
                parts = line.split()
                if parts:
                    col_name = parts[0]
                    col_type = parts[1] if len(parts) > 1 else "TEXT"
                    cols.append(f"  {col_name} {col_type}")
            tables[table_name] = cols
    result = []
    for tname, tcols in tables.items():
        result.append(f"CREATE TABLE {tname} (")
        result.append(",\n".join(tcols))
        result.append(");")
    return "\n".join(result)

def strip_limit(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    sql = re.sub(r'\s+LIMIT\s+\d+(\s*;?\s*)?$', '', sql, flags=re.IGNORECASE)
    return sql.strip()

def normalize_rows(rows) -> list:
    result = []
    for r in rows:
        if isinstance(r, dict):
            result.append(tuple(str(v) for v in r.values()))
        elif isinstance(r, (list, tuple)):
            result.append(tuple(str(v) for v in r))
        else:
            result.append((str(r),))
    return sorted(result)

def execution_match(gen_sql: str, expected_sql: str, db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        gen_clean = strip_limit(gen_sql)
        exp_clean = strip_limit(expected_sql)
        if not gen_clean or not exp_clean:
            conn.close()
            return False
        try:
            gen_rows = normalize_rows(conn.execute(gen_clean).fetchall())
        except Exception as e:
            print(f"    GEN SQL ERROR: {e}")
            conn.close()
            return False
        try:
            exp_rows = normalize_rows(conn.execute(exp_clean).fetchall())
        except Exception as e:
            print(f"    EXP SQL ERROR: {e}")
            conn.close()
            return False
        conn.close()
        if not exp_rows and not gen_rows:
            return True
        if not exp_rows or not gen_rows:
            return False
        return gen_rows == exp_rows
    except Exception as e:
        print(f"    EXEC MATCH ERROR: {e}")
        return False

def main():
    hdr("DataPilot BIRD Eval (Lightweight)")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  Model: {getattr(settings, f'{settings.LLM_PROVIDER.upper()}_MODEL', 'default')}")
    print(f"  Calls needed: 30 (1 per query)\n")

    gen.create_databases()
    gen.generate_dev_set()

    with open(gen.DEV_SET_DIR / "dev.json") as f:
        examples = json.load(f)

    llm = get_llm(provider=settings.LLM_PROVIDER)

    results = []
    total = len(examples)
    passed = failed = 0
    total_latency = 0.0

    for i, ex in enumerate(examples, 1):
        db_id = ex["db_id"]
        question = ex["question"]
        expected_sql = ex["sql"]
        db_path = str(gen.DATABASES_DIR / f"{db_id}.db")

        schema_str = build_schema_str(db_id)
        prompt = SQL_GENERATION_PROMPT.format(schema=schema_str, max_rows=1000, question=question)

        print(f"  [{i}/{total}] {YELLOW}{db_id}{RESET} [{ex['difficulty']}] {question[:70]}")
        start = time.time()

        gen_sql = ""
        ok = False
        last_err = ""
        for retry in range(3):
            try:
                raw = llm.generate(prompt, system_message=SQL_SYSTEM_MESSAGE, max_tokens=2048)
                if raw.strip():
                    gen_sql = raw
                    ok = True
                    break
                if retry < 2:
                    time.sleep(2.0)
            except Exception as e:
                last_err = str(e)[:150]
                if retry < 2:
                    time.sleep(3.0)
                    continue
                gen_sql = ""

        if not ok:
            print(f"    {FAIL} {'LLM error: ' + last_err if last_err else 'Incomplete SQL after 3 retries'}")
            failed += 1
            latency = time.time() - start
            results.append({"db_id": db_id, "question": question, "expected_sql": expected_sql,
                            "generated_sql": "", "execution_match": False, "latency": round(latency, 2),
                            "error": last_err or "Incomplete SQL after 3 retries"})
            time.sleep(3.0)
            continue

        latency = time.time() - start
        total_latency += latency
        gen_sql_clean = gen_sql.strip()
        em = execution_match(gen_sql_clean, expected_sql, db_path)
        if em: passed += 1
        else: failed += 1

        print(f"    {OK} SQL present ({len(gen_sql_clean)} chars)")
        print(f"    {OK if em else FAIL} Exec Match: {'YES' if em else 'NO'}  [{latency:.1f}s]")
        if not em:
            print(f"    SQL: {gen_sql_clean[:120]}")
        time.sleep(3.0)

        results.append({"db_id": db_id, "question": question, "expected_sql": expected_sql,
                        "generated_sql": gen_sql_clean, "execution_match": em, "latency": round(latency, 2)})

    hdr("Results")
    succ_rate = (passed / max(total, 1)) * 100
    avg_lat = total_latency / max(total, 1)
    print(f"\n  {BOLD}Summary:{RESET}")
    print(f"  Total: {total}")
    print(f"  Exec Pass: {passed}")
    print(f"  Exec Fail: {failed}")
    print(f"  Exec Accuracy: {succ_rate:.1f}%")
    print(f"  Avg Latency: {avg_lat:.1f}s")

    by_diff = {"easy": [], "medium": [], "hard": []}
    for ex in examples: by_diff[ex.get("difficulty", "medium")].append(ex)
    for diff, items in by_diff.items():
        d_res = [r for r in results if r.get("question") in [e["question"] for e in items]]
        d_pass = sum(1 for r in d_res if r.get("execution_match"))
        print(f"  {diff:>10}: {d_pass}/{len(d_res)} pass")

    report_path = gen.DATA_DIR / "eval_lightweight_results.json"
    with open(report_path, "w") as f:
        json.dump({"summary": {"total": total, "passed": passed, "failed": failed,
                               "execution_accuracy": round(succ_rate, 2), "avg_latency": round(avg_lat, 2),
                               "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                   "results": results}, f, indent=2)
    print(f"\n  Report: {report_path}")

if __name__ == "__main__":
    main()
