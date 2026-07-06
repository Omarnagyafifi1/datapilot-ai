#!/usr/bin/env python3
"""
Setup demo database from CSV file and register as a data source.
"""
import os
import sys
import sqlite3
import pandas as pd

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

DB_PATH = os.path.join(BACKEND_DIR, "demo_bilingual.db")
CSV_PATH = os.path.join(BACKEND_DIR, "sample_data", "employees_ar_en.csv")

def setup():
    # Create SQLite database from CSV
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    df = pd.read_csv(CSV_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("employees", conn, if_exists="replace", index=False)
    conn.close()
    
    print(f"Created demo database: {DB_PATH}")
    
    # Register as data source
    from app.services.data_source_service import save_source
    
    params = {
        "name": "Demo Bilingual DB (عربي + EN)",
        "db_type": "sqlite",
        "db_name": DB_PATH,
        "host": "",
        "port": None,
        "username": "",
        "password": "",
    }
    result = save_source(params)
    if result.get("success"):
        print(f"[OK] Registered! Source ID: {result['id']}")
    else:
        print(f"[ERROR] {result}")

if __name__ == "__main__":
    setup()