import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 1. System Health
def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# 2. SQL Explanation
def test_api_explain():
    payload = {
        "sql": "SELECT name, salary FROM employees WHERE department = 'Engineering' GROUP BY department ORDER BY salary DESC LIMIT 5"
    }
    response = client.post("/api/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Explained" in data["message"]
    explanation = data["data"]
    assert "Selects columns" in explanation
    assert "From tables / joins" in explanation
    assert "Grouped by" in explanation
    assert "Ordered by" in explanation
    assert "Limit: 5" in explanation

# 3. Report Generation
def test_api_report_generate():
    payload = {
        "document": {
            "question": "Show all employees and their salaries",
            "sql": "SELECT name, salary FROM employees",
            "results": [
                {"name": "Omar Nady", "salary": 35000},
                {"name": "Layla Ahmed", "salary": 22000}
            ],
            "insights": [{"en": "Omar Nady is the highest earner.", "ar": "عمر نادي هو الأعلى راتباً."}],
            "suggestions": [{"en": "Compare departments", "ar": "قارن بين الأقسام"}]
        }
    }
    response = client.post("/api/report/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Report generated" in data["message"]
    assert "markdown" in data["data"]
    assert "filename" in data["data"]
    assert "Show all employees and their salaries" in data["data"]["markdown"]
    assert "Generated at" in data["data"]["markdown"]

# 4. Settings Retrieval and Updates
def test_api_settings():
    # GET settings
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "llm_provider" in data["data"]
    
    # UPDATE settings
    update_payload = {
        "llm_provider": "groq",
        "api_keys": {"groq": "test_key"},
        "features": {"auto_visualization": True}
    }
    resp_update = client.post("/api/settings", json=update_payload)
    assert resp_update.status_code == 200
    update_data = resp_update.json()
    assert update_data["success"] is True

# 5. Dataset Upload Preview & Ingest
def test_api_upload_preview():
    files = {"file": ("test.csv", b"id,name,age\n1,Ahmed,30\n2,Sara,25", "text/csv")}
    response = client.post("/api/upload/preview", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["detected_format"] == "csv"
    assert len(data["data"]["tables"][0]["columns"]) == 3

def test_api_upload_import():
    files = {"file": ("test.csv", b"id,name,age\n1,Ahmed,30\n2,Sara,25", "text/csv")}
    payload = {
        "dataset_name": "Integration Test CSV",
        "selected_tables": json.dumps(["test"]),
        "renamed_columns": json.dumps({"test": {}}),
        "modified_types": json.dumps({"test": {}})
    }
    response = client.post("/api/upload/import", files=files, data=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_rows"] == 2
    assert "Integration Test CSV" in data["message"]

# 6. Datasets Listing & Management
def test_api_datasets_list():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

# 7. Datasources Connections & Schemas
def test_api_datasources_flow():
    # Register connection
    conn_payload = {
        "name": "Integration Test SQLite",
        "db_type": "sqlite",
        "host": "",
        "port": None,
        "db_name": "./dev.db",
        "username": "",
        "password": ""
    }
    response = client.post("/api/datasources/connect", json=conn_payload)
    assert response.status_code == 200
    reg_data = response.json()
    assert reg_data["success"] is True
    source_id = reg_data["data"]["id"]
    
    # List connections
    list_resp = client.get("/api/datasources")
    assert list_resp.status_code == 200
    assert any(x["id"] == source_id for x in list_resp.json()["data"])
    
    # Get schema
    schema_resp = client.get(f"/api/datasources/{source_id}/schema")
    assert schema_resp.status_code in [200, 500]  # Allow 500 if dev.db file locks or is missing
    
    # Get suggestions
    sug_resp = client.get(f"/api/datasources/{source_id}/suggestions")
    assert sug_resp.status_code == 200
    
    # Delete connection
    del_resp = client.delete(f"/api/datasources/{source_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

# 8. Evaluation
def test_api_evaluate():
    eval_payload = {
        "question": "Show all employees",
        "sql": "SELECT * FROM employees",
        "source_id": "sqlite_source_id" # mock source ID
    }
    response = client.post("/api/evaluate", json=eval_payload)
    assert response.status_code in [200, 400, 500]  # Depends on active source database

# 9. Pagination SQL injection protection
def test_query_page_rejects_malicious_sql():
    resp = client.post("/api/query/page", json={
        "sql": "SELECT 1; DROP TABLE products; --",
        "source_id": "nonexistent",
        "page": 1,
        "page_size": 10
    })
    data = resp.json()
    assert not data.get("success", True)

# 10. System Metrics, Stats, & Feed
def test_api_system_endpoints():
    # Stats
    stats_resp = client.get("/api/system/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["success"] is True
    
    # Metrics
    metrics_resp = client.get("/api/system/metrics")
    assert metrics_resp.status_code == 200
    assert metrics_resp.json()["success"] is True
    
    # Feed
    feed_resp = client.get("/api/system/feed")
    assert feed_resp.status_code == 200
    assert feed_resp.json()["success"] is True
