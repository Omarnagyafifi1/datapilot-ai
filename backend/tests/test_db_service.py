import unittest
import os
from app.services.db_service import DBService, execute_query, upload_csv_to_sqlite, close_engine

class TestDBService(unittest.TestCase):
    def setUp(self):
        self.source_id = "test_source_db"
        self.csv_path = "test_temp_data.csv"
        # Create a simple CSV file for testing
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("id,name,value\n1,Alice,100\n2,Bob,200\n")

    def tearDown(self):
        # Cleanup
        close_engine(self.source_id)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        db_file = f"{self.source_id}.db"
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

    def test_upload_and_query(self):
        conn_string, table_name = upload_csv_to_sqlite(self.csv_path, self.source_id)
        self.assertTrue(conn_string.startswith("sqlite:///"))
        self.assertEqual(table_name, "test_temp_data")

        # Test execute_query
        results = execute_query("SELECT * FROM test_temp_data ORDER BY id ASC", self.source_id)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Alice")
        self.assertEqual(results[1]["value"], 200)

        # Test DBService wrapper
        db = DBService(source_id=self.source_id)
        self.assertEqual(db.get_dialect(), "sqlite")
        db_results = db.run_query("SELECT COUNT(*) as count FROM test_temp_data")
        self.assertEqual(db_results[0]["count"], 2)

if __name__ == "__main__":
    unittest.main()
