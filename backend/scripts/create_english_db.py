import sys
import sqlite3
import pandas as pd
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

SAMPLE_DATA_DIR = BACKEND_DIR / "sample_data"
DB_PATH = BACKEND_DIR / "english_only.db"

def build_database():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed old database: {DB_PATH.name}")

    conn = sqlite3.connect(DB_PATH)

    csv_files = {
        "employees": SAMPLE_DATA_DIR / "employees_ar_en.csv",
        "sales": SAMPLE_DATA_DIR / "sales_ar_en.csv",
        "inventory": SAMPLE_DATA_DIR / "inventory_ar_en.csv",
    }

    for table_name, csv_path in csv_files.items():
        if not csv_path.exists():
            print(f"CSV not found: {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        
        # Drop columns ending with _ar
        english_columns = [col for col in df.columns if not col.endswith('_ar')]
        df = df[english_columns]
        
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"Table '{table_name}' created — {len(df)} rows, {len(df.columns)} columns")

    # Create a summary view
    conn.execute("""
        CREATE VIEW IF NOT EXISTS dept_summary AS
        SELECT
            department,
            COUNT(*) AS total_employees,
            ROUND(AVG(salary), 2) AS avg_salary,
            SUM(salary) AS total_salary_budget,
            MAX(salary) AS max_salary,
            MIN(salary) AS min_salary
        FROM employees
        GROUP BY department
        ORDER BY total_salary_budget DESC
    """)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS sales_summary AS
        SELECT
            strftime('%Y-%m', sale_date) AS month,
            category,
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
            category,
            stock_quantity,
            reorder_level,
            warehouse,
            (reorder_level - stock_quantity) AS units_needed
        FROM inventory
        WHERE stock_quantity <= reorder_level AND is_active = 1
        ORDER BY units_needed DESC
    """)

    conn.commit()
    conn.close()
    print(f"Database ready: {DB_PATH}")

def register():
    from app.services.data_source_service import save_source
    
    params = {
        "name": "English Only DB",
        "db_type": "sqlite",
        "db_name": str(DB_PATH),
        "host": "",
        "port": None,
        "username": "",
        "password": "",
    }
    result = save_source(params)
    if result.get("success"):
        print(f"[OK] Registered! Source ID: {result['id']}")
        print(f"     Name: {params['name']}")
        print(f"     DB:   {DB_PATH}")
    else:
        print(f"[ERROR] {result}")

if __name__ == "__main__":
    build_database()
    register()
