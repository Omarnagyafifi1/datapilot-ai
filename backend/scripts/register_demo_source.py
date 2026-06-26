"""
Register demo_bilingual database as a DataPilot data source
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "demo_bilingual.db"
CONN_STRING = f"sqlite:///{DB_PATH}"

def register():
    from app.services.data_source_service import save_source
    
    params = {
        "name": "Demo Bilingual DB (عربي + EN)",
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
    register()
