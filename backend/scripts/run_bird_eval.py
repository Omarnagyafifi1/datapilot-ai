"""
DataPilot BIRD-Style Text-to-SQL Evaluation Runner
"""
import json, time, sqlite3, re, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import bird_data.generate_eval_dataset as gen
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.schema_service import SchemaService
from app.services.data_source_service import DataSourceService
from app.services.evaluation_service import evaluate_sql, post_evaluation_to_langsmith
from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends

GREEN = "\033[92m"; CYAN = "\033[96m"; YELLOW = "\033[93m"; RED = "\033[91m"; BOLD = "\033[1m"; RESET = "\033[0m"
OK = f"{GREEN}[OK]{RESET}"; FAIL = f"{RED}[FAIL]{RESET}"; WARN = f"{YELLOW}[WARN]{RESET}"

def hdr(t): print(f"\n{BOLD}{CYAN}={'='*70}{RESET}\n{BOLD}{CYAN}  {t}{RESET}\n{BOLD}{CYAN}={'='*70}{RESET}")

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
    hdr("DataPilot BIRD-Style Text-to-SQL Evaluation")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")

    # Recreate databases with updated schema
    hdr("Recreating Databases")
    gen.create_databases()
    gen.generate_dev_set()

    # Register sources
    hdr("Registering & Warming Data Sources")
    svc = DataSourceService()
    for s in svc.list_sources():
        if "BIRD Eval" in s.get("name", ""):
            svc.delete_source(str(s["id"]))
    gen.register_sources()

    db_to_source = {}
    for s in svc.list_sources():
        if "BIRD Eval" in s.get("name", ""):
            sid = str(s["id"])
            try:
                svc.get_conn_string(sid)
                for d in gen.SCHEMAS:
                    if gen.SCHEMAS[d]["description"] == s["name"].split(": ", 1)[1]:
                        db_to_source[d] = sid
                        break
                print(f"  Ready: {s['name']} ({sid})")
            except Exception as e:
                print(f"  FAIL: {s['name']}: {e}")

    print(f"\n  {len(db_to_source)} sources ready: {list(db_to_source.keys())}")

    with open(gen.DEV_SET_DIR / "dev.json") as f:
        examples = json.load(f)
    print(f"  {len(examples)} test examples\n")

    llm = get_llm(provider=settings.LLM_PROVIDER)
    mem = GraphMemoryBackends()
    graph = AgentGraph(llm=llm, db_service=DBService(), schema_service=SchemaService(), checkpointer=mem.checkpointer, store=mem.store)

    results = []
    total = len(examples)
    passed = failed = 0
    total_score = 0.0

    for i, ex in enumerate(examples, 1):
        db_id = ex["db_id"]
        question = ex["question"]
        expected_sql = ex["sql"]
        source_id = db_to_source.get(db_id)
        if not source_id:
            print(f"  {FAIL} [{i}/{total}] No source for {db_id}, skip")
            continue

        print(f"\n  [{i}/{total}] {YELLOW}{db_id}{RESET} [{ex['difficulty']}] {question[:70]}...")
        start = time.time()
        try:
            result = graph.run(question, source_id, preview_only=False)
            gen_sql = result.get("sql", "")
            latency = time.time() - start

            eval_scores = evaluate_sql(question=question, sql=gen_sql, results=result.get("results", []), llm=llm)

            db_path = str(gen.DATABASES_DIR / f"{db_id}.db")
            ex_match = execution_match(gen_sql, expected_sql, db_path)

            score = eval_scores.get("overall", 0.0)
            total_score += score
            if ex_match: passed += 1
            else: failed += 1

            diff_ok = score > 0.5
            gen_ok = bool(gen_sql.strip())

            print(f"    {OK if gen_ok else FAIL} SQL present")
            print(f"    {OK if diff_ok else WARN} Score: {score:.2f}")
            print(f"    {OK if ex_match else FAIL if gen_ok else WARN} Exec Match: {'YES' if ex_match else 'NO'}")
            print(f"    Latency: {latency:.1f}s")
            if gen_sql:
                print(f"    SQL: {gen_sql[:100]}...")

            post_evaluation_to_langsmith(question=question, sql=gen_sql, source_id=source_id, thread_id=result.get("thread_id", f"eval-{i}"), scores=eval_scores, latency=latency, results_count=len(result.get("results", [])), has_visualization=result.get("visualization") is not None, insight_count=len(result.get("insights", [])))

            results.append({"db_id": db_id, "question": question, "expected_sql": expected_sql, "generated_sql": gen_sql, "score": score, "execution_match": ex_match, "latency": round(latency, 2)})

            time.sleep(1.0)

        except Exception as e:
            failed += 1
            import traceback
            print(f"    {FAIL} Error: {str(e)[:200]}")
            traceback.print_exc()
            results.append({"db_id": db_id, "question": question, "expected_sql": expected_sql, "generated_sql": "", "score": 0.0, "execution_match": False, "latency": round(time.time() - start, 2), "error": str(e)[:200]})

    hdr("Results")
    avg_score = total_score / max(total, 1)
    succ_rate = (passed / max(total, 1)) * 100
    print(f"\n  {BOLD}Summary:{RESET}")
    print(f"  Total: {total}")
    print(f"  Exec Pass: {passed}")
    print(f"  Exec Fail: {failed}")
    print(f"  Avg Score: {avg_score:.2f}")
    print(f"  Exec Accuracy: {succ_rate:.1f}%")

    by_diff = {"easy": [], "medium": [], "hard": []}
    for ex in examples: by_diff[ex.get("difficulty", "medium")].append(ex)
    for diff, items in by_diff.items():
        d_res = [r for r in results if r.get("question") in [e["question"] for e in items]]
        d_pass = sum(1 for r in d_res if r.get("execution_match"))
        d_avg = sum(r.get("score", 0) for r in d_res) / max(len(d_res), 1) if d_res else 0
        print(f"  {diff:>10}: {d_pass}/{len(d_res)} pass, avg {d_avg:.2f}")

    report_path = gen.DATA_DIR / "eval_results.json"
    with open(report_path, "w") as f:
        json.dump({"summary": {"total": total, "passed": passed, "failed": failed, "execution_accuracy": round(succ_rate, 2), "avg_overall_score": round(avg_score, 2), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, "results": results}, f, indent=2)
    print(f"\n  Report: {report_path}")

if __name__ == "__main__":
    main()
