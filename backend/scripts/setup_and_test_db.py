"""
DataPilot - Database Setup & Testing Script
==========================================
يقوم هذا السكريبت بـ:
1. إنشاء قاعدة بيانات SQLite شاملة (عربي + إنجليزي)
2. تحميل ملفات CSV إلى الجداول
3. تشغيل أسئلة تجريبية باللغتين العربية والإنجليزية
4. عرض النتائج بشكل منسق
"""

import os
import sys
import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any

# ── Add backend to path ──────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── Paths ────────────────────────────────────────────────────────────────────
SAMPLE_DATA_DIR = BACKEND_DIR / "sample_data"
DB_PATH = BACKEND_DIR / "demo_bilingual.db"
CONN_STRING = f"sqlite:///{DB_PATH}"
SOURCE_ID = "demo_bilingual"

# ANSI colors
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"


def print_header(title: str, emoji: str = "🔷") -> None:
    width = 70
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}{emoji}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")


def print_section(title: str, emoji: str = "▶") -> None:
    print(f"\n{BOLD}{YELLOW}{emoji} {title}{RESET}")
    print(f"{YELLOW}{'─' * 55}{RESET}")


def print_success(msg: str) -> None:
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"{RED}❌ {msg}{RESET}")


def print_info(msg: str) -> None:
    print(f"{BLUE}ℹ  {msg}{RESET}")


def build_database() -> None:
    """إنشاء قاعدة البيانات وتحميل ملفات CSV."""
    print_header("إنشاء قاعدة البيانات / Building Database", "🏗️")

    if DB_PATH.exists():
        DB_PATH.unlink()
        print_info(f"Removed old database: {DB_PATH.name}")

    conn = sqlite3.connect(DB_PATH)

    csv_files = {
        "employees": SAMPLE_DATA_DIR / "employees_ar_en.csv",
        "sales": SAMPLE_DATA_DIR / "sales_ar_en.csv",
        "inventory": SAMPLE_DATA_DIR / "inventory_ar_en.csv",
    }

    for table_name, csv_path in csv_files.items():
        if not csv_path.exists():
            print_error(f"CSV not found: {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print_success(
            f"Table '{table_name}' created — {len(df)} rows, {len(df.columns)} columns"
        )

    # Create a summary view
    conn.execute("""
        CREATE VIEW IF NOT EXISTS dept_summary AS
        SELECT
            department,
            department_ar,
            COUNT(*) AS total_employees,
            ROUND(AVG(salary), 2) AS avg_salary,
            SUM(salary) AS total_salary_budget,
            MAX(salary) AS max_salary,
            MIN(salary) AS min_salary
        FROM employees
        GROUP BY department, department_ar
        ORDER BY total_salary_budget DESC
    """)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS sales_summary AS
        SELECT
            strftime('%Y-%m', sale_date) AS month,
            category,
            category_ar,
            COUNT(*) AS total_transactions,
            SUM(total_amount) AS revenue,
            ROUND(AVG(total_amount), 2) AS avg_deal_size
        FROM sales
        WHERE status = 'Completed'
        GROUP BY month, category
        ORDER BY month, revenue DESC
    """)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS low_stock AS
        SELECT
            product_name,
            product_name_ar,
            category,
            category_ar,
            stock_quantity,
            reorder_level,
            warehouse,
            warehouse_ar,
            (reorder_level - stock_quantity) AS units_needed
        FROM inventory
        WHERE stock_quantity <= reorder_level AND is_active = 1
        ORDER BY units_needed DESC
    """)

    conn.commit()
    conn.close()
    print_success(f"Database ready: {DB_PATH}")
    print_success("Views created: dept_summary, sales_summary, low_stock")


def run_direct_query(query: str, db_path: str = str(DB_PATH)) -> list[dict]:
    """تنفيذ استعلام SQL مباشرة على قاعدة البيانات."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def display_results(results: list[dict], max_rows: int = 10) -> None:
    """عرض النتائج كجدول منسق."""
    if not results:
        print_info("No results returned.")
        return

    df = pd.DataFrame(results[:max_rows])
    print(df.to_string(index=False))
    if len(results) > max_rows:
        print_info(f"... showing {max_rows} of {len(results)} rows")


def run_demo_queries() -> None:
    """تشغيل أسئلة تجريبية مباشرة على قاعدة البيانات."""
    print_header("اختبار الاستعلامات / Demo Queries", "🧪")

    test_cases = [
        # ── English Queries ──────────────────────────────────────────────
        {
            "lang": "EN",
            "question": "Show all employees and their salaries",
            "sql": "SELECT name, job_title, department, salary, location FROM employees ORDER BY salary DESC",
        },
        {
            "lang": "EN",
            "question": "What is the total salary budget per department?",
            "sql": "SELECT department, COUNT(*) as headcount, SUM(salary) as total_budget, ROUND(AVG(salary),0) as avg_salary FROM employees GROUP BY department ORDER BY total_budget DESC",
        },
        {
            "lang": "EN",
            "question": "Who are the top 5 earners?",
            "sql": "SELECT name, job_title, department, salary FROM employees ORDER BY salary DESC LIMIT 5",
        },
        {
            "lang": "EN",
            "question": "Show total sales revenue by category",
            "sql": "SELECT category, category_ar, COUNT(*) as transactions, SUM(total_amount) as revenue FROM sales WHERE status='Completed' GROUP BY category ORDER BY revenue DESC",
        },
        {
            "lang": "EN",
            "question": "Which products are below reorder level?",
            "sql": "SELECT product_name, category, stock_quantity, reorder_level, warehouse FROM inventory WHERE stock_quantity <= reorder_level AND is_active=1 ORDER BY stock_quantity ASC",
        },
        # ── Arabic Queries ───────────────────────────────────────────────
        {
            "lang": "AR",
            "question": "أظهر جميع الموظفين ورواتبهم",
            "sql": "SELECT name_ar AS الاسم, job_title_ar AS الوظيفة, department_ar AS القسم, salary AS الراتب, location_ar AS الموقع FROM employees ORDER BY salary DESC",
        },
        {
            "lang": "AR",
            "question": "ما هو إجمالي الرواتب لكل قسم؟",
            "sql": "SELECT department_ar AS القسم, COUNT(*) AS عدد_الموظفين, SUM(salary) AS إجمالي_الرواتب, ROUND(AVG(salary),0) AS متوسط_الراتب FROM employees GROUP BY department_ar ORDER BY إجمالي_الرواتب DESC",
        },
        {
            "lang": "AR",
            "question": "من هم أعلى 5 موظفين راتباً؟",
            "sql": "SELECT name_ar AS الاسم, job_title_ar AS الوظيفة, department_ar AS القسم, salary AS الراتب FROM employees ORDER BY salary DESC LIMIT 5",
        },
        {
            "lang": "AR",
            "question": "أظهر المبيعات الإجمالية حسب الفئة بالعربية",
            "sql": "SELECT category_ar AS الفئة, COUNT(*) AS عدد_المعاملات, SUM(total_amount) AS الإيراد, region_ar AS المنطقة FROM sales WHERE status='Completed' GROUP BY category_ar ORDER BY الإيراد DESC",
        },
        {
            "lang": "AR",
            "question": "عرض المنتجات التي نفد مخزونها",
            "sql": "SELECT product_name_ar AS المنتج, category_ar AS الفئة, stock_quantity AS الكمية_المتاحة, reorder_level AS حد_إعادة_الطلب, warehouse_ar AS المخزن FROM inventory WHERE stock_quantity <= reorder_level AND is_active=1",
        },
        # ── Mixed / Advanced ─────────────────────────────────────────────
        {
            "lang": "MIXED",
            "question": "Department performance summary (EN+AR combined)",
            "sql": "SELECT department AS Department, department_ar AS القسم, COUNT(*) AS Employees, SUM(salary) AS Total_Budget FROM employees GROUP BY department ORDER BY Total_Budget DESC",
        },
        {
            "lang": "MIXED",
            "question": "Monthly revenue trend",
            "sql": "SELECT strftime('%Y-%m', sale_date) AS Month, SUM(total_amount) AS Revenue, COUNT(*) AS Transactions FROM sales WHERE status='Completed' GROUP BY Month ORDER BY Month",
        },
    ]

    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        lang_badge = {
            "EN": f"{BLUE}[EN]{RESET}",
            "AR": f"{MAGENTA}[AR]{RESET}",
            "MIXED": f"{GREEN}[MIXED]{RESET}",
        }.get(case["lang"], "[?]")

        print(f"\n{BOLD}Test #{i} {lang_badge}{RESET}")
        print(f"  {CYAN}Q: {case['question']}{RESET}")
        print(f"  {YELLOW}SQL: {case['sql'][:80]}{'...' if len(case['sql']) > 80 else ''}{RESET}")

        try:
            results = run_direct_query(case["sql"])
            if results:
                display_results(results, max_rows=5)
                print_success(f"→ {len(results)} rows returned")
                passed += 1
            else:
                print_info("→ Query ran successfully (0 rows)")
                passed += 1
        except Exception as e:
            print_error(f"Query failed: {e}")
            failed += 1

    print_section("Test Results Summary", "📊")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    print(f"  {RED}Failed: {failed}{RESET}")
    print(f"  {CYAN}Total:  {passed + failed}{RESET}")


def run_agent_tests() -> None:
    """تشغيل الاختبارات عبر الـ AI Agent."""
    print_header("اختبار الـ AI Agent / AI Agent Tests", "🤖")

    try:
        from app.core.config import settings
        from app.llm.factory import get_llm
        from app.services.db_service import DBService, get_engine, _SOURCE_CONN_STRINGS
        from app.agents.graph import AgentGraph

        # Register data source
        _SOURCE_CONN_STRINGS[SOURCE_ID] = CONN_STRING
        get_engine(source_id=SOURCE_ID, conn_string=CONN_STRING)
        print_success(f"Data source registered: {SOURCE_ID} → {CONN_STRING}")

        # Init services
        llm = get_llm(provider=settings.LLM_PROVIDER)
        db_service = DBService(source_id=SOURCE_ID, conn_string=CONN_STRING)
        agent = AgentGraph(llm, db_service, None)
        print_success("AgentGraph initialized successfully")

        # Questions to test
        questions = [
            # English
            "Show all employees and their salaries sorted by salary descending",
            "What is the total salary budget per department?",
            "Who are the top 3 highest paid employees?",
            "Show total sales revenue by category",
            # Arabic
            "أظهر جميع الموظفين ورواتبهم",
            "ما هو إجمالي ميزانية الرواتب لكل قسم؟",
            "من هم أعلى 3 موظفين في الراتب؟",
            "أظهر إجمالي المبيعات حسب الفئة",
        ]

        results_summary = []

        for i, question in enumerate(questions, 1):
            is_arabic = any("\u0600" <= c <= "\u06FF" for c in question)
            lang = "AR" if is_arabic else "EN"
            lang_badge = f"{MAGENTA}[AR]{RESET}" if is_arabic else f"{BLUE}[EN]{RESET}"

            print(f"\n{BOLD}Agent Test #{i} {lang_badge}{RESET}")
            print(f"  {CYAN}Question: {question}{RESET}")

            try:
                result = agent.run(question, SOURCE_ID, cli_mode=True)

                sql = result.get("sql", "")
                query_results = result.get("results", [])
                success = bool(query_results) and not result.get("documentation", {}).get("error")
                doc = result.get("documentation", {})
                insights = doc.get("insights", [])
                suggestions = doc.get("suggestions", [])

                status_icon = "✅" if success else "⚠️"
                print(f"  {GREEN if success else YELLOW}SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}{RESET}")
                print(f"  {status_icon} Rows returned: {len(query_results)}")

                if insights:
                    print(f"  {CYAN}💡 Insights:{RESET}")
                    for ins in insights[:2]:
                        if is_arabic:
                            print(f"     AR: {ins.get('ar', '')}")
                        else:
                            print(f"     EN: {ins.get('en', '')}")

                if suggestions:
                    print(f"  {YELLOW}💬 Suggestions:{RESET}")
                    for sug in suggestions[:2]:
                        if is_arabic:
                            print(f"     AR: {sug.get('ar', '')}")
                        else:
                            print(f"     EN: {sug.get('en', '')}")

                if query_results:
                    display_results(query_results, max_rows=3)

                results_summary.append(
                    {
                        "test": i,
                        "lang": lang,
                        "question": question[:50],
                        "sql": sql[:80],
                        "rows": len(query_results),
                        "success": success,
                    }
                )

            except Exception as e:
                print_error(f"Agent failed: {e}")
                results_summary.append(
                    {
                        "test": i,
                        "lang": lang,
                        "question": question[:50],
                        "sql": "",
                        "rows": 0,
                        "success": False,
                        "error": str(e),
                    }
                )

        # Summary table
        print_section("Agent Test Summary", "📋")
        df = pd.DataFrame(results_summary)
        print(df[["test", "lang", "question", "rows", "success"]].to_string(index=False))

        passed = sum(1 for r in results_summary if r["success"])
        print(f"\n  {GREEN}Passed: {passed}/{len(results_summary)}{RESET}")

    except ImportError as e:
        print_error(f"Could not import backend modules: {e}")
        print_info("Make sure the backend environment is activated and dependencies are installed.")
        print_info("Run: pip install -r requirements.txt")


def show_db_schema() -> None:
    """عرض هيكل قاعدة البيانات."""
    print_header("هيكل قاعدة البيانات / Database Schema", "📐")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name")
    objects = cursor.fetchall()

    for obj_name, obj_type in objects:
        print(f"\n  {BOLD}{CYAN}{'📋 TABLE' if obj_type == 'table' else '👁️ VIEW'}: {obj_name}{RESET}")
        schema_cursor = conn.execute(f"PRAGMA table_info({obj_name})")
        columns = schema_cursor.fetchall()
        for col in columns:
            pk_marker = " 🔑" if col[5] else ""
            null_marker = "" if col[3] else " (nullable)"
            print(f"    {col[1]:30s} {YELLOW}{col[2]}{RESET}{pk_marker}{null_marker}")

        if obj_type == "table":
            count = conn.execute(f"SELECT COUNT(*) FROM {obj_name}").fetchone()[0]
            print(f"    {GREEN}  → {count} rows{RESET}")

    conn.close()


def main() -> None:
    print_header("DataPilot - Database Setup & Test Runner", "🚀")
    print(f"  {CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"  {CYAN}DB:   {DB_PATH}{RESET}")

    # Step 1: Build the database
    build_database()

    # Step 2: Show schema
    show_db_schema()

    # Step 3: Run direct SQL tests (no AI needed)
    run_demo_queries()

    # Step 4: Run AI Agent tests
    print_header("هل تريد تشغيل اختبارات الـ AI Agent؟ / Run AI Agent Tests?", "🤖")
    print(f"  {YELLOW}Note: This requires a valid LLM API key in .env{RESET}")
    try:
        choice = input(f"  {BOLD}Run AI Agent tests? [y/N]: {RESET}").strip().lower()
        if choice in {"y", "yes"}:
            run_agent_tests()
        else:
            print_info("Skipping AI Agent tests.")
    except EOFError:
        # Non-interactive mode — skip agent tests
        print_info("Non-interactive mode detected. Skipping AI Agent tests.")

    print_header("تم الانتهاء / Done!", "✨")
    print(f"  {GREEN}Database file: {DB_PATH}{RESET}")
    print(f"  {GREEN}Sample CSVs:   {SAMPLE_DATA_DIR}{RESET}")
    print(f"\n  {CYAN}To use this database in DataPilot:{RESET}")
    print(f"  {YELLOW}  Connection String: {CONN_STRING}{RESET}")
    print(f"  {YELLOW}  Source ID:         {SOURCE_ID}{RESET}\n")


if __name__ == "__main__":
    main()
