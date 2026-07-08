import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

def register_all():
    from app.services.data_source_service import save_source

    sources = [
        {
            "name": "PostgreSQL Docker DB",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "db_name": "datapilot_test",
            "username": "postgres",
            "password": "postgres",
        },
        {
            "name": "MySQL Docker DB",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "db_name": "datapilot_test",
            "username": "mysql_user",
            "password": "mysql_password",
        },
        {
            "name": "MSSQL Docker DB",
            "db_type": "mssql",
            "host": "localhost",
            "port": 1433,
            "db_name": "tempdb",
            "username": "sa",
            "password": "YourStrong@Passw0rd",
        }
    ]

    for params in sources:
        result = save_source(params)
        if result.get("success"):
            print(f"[OK] Registered! Source ID: {result['id']}")
            print(f"     Name: {params['name']}")
        else:
            print(f"[ERROR] Failed to register {params['name']}: {result}")

if __name__ == "__main__":
    register_all()
