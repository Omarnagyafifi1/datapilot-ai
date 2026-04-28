import psycopg2
import json

class SchemaService:
    def __init__(self):
        self.conn_params = {
            "host": "localhost",
            "database": "test",
            "user": "postgres",
            "password": "12345"
        }

    def get_schema(self) -> dict:
        conn = psycopg2.connect(**self.conn_params)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, column_name
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        schema = {}
        for table, column, dtype in rows:
            if table not in schema:
                schema[table] = []
            schema[table].append({
                "column": column,
                "type": dtype
            })
        
        return {"tables": schema}
