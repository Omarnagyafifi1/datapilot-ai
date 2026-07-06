import pytest
import os
import pandas as pd
from app.services.db_service import (
    _dialect_from_conn_string,
    _strip_identifier_quotes,
    _rewrite_month_name_like_filters,
    _rewrite_month_extraction_filters,
    _normalize_conn_string_for_sync,
)
from app.services.report_service import build_report
from app.services.visualization_service import (
    _detect_chart_type_from_settings,
    _coerce_columns,
    generate_visualization,
)
from app.services import settings_service

# 1. Database Service Unit Tests
def test_dialect_from_conn_string():
    assert _dialect_from_conn_string("postgresql+psycopg2://localhost/db") == "postgresql"
    assert _dialect_from_conn_string("mysql+pymysql://localhost/db") == "mysql"
    assert _dialect_from_conn_string("sqlite:///dev.db") == "sqlite"
    assert _dialect_from_conn_string("oracle+oracledb://localhost/db") == "oracle"

def test_strip_identifier_quotes():
    assert _strip_identifier_quotes('"employees"') == "employees"
    assert _strip_identifier_quotes("`employees`") == "employees"
    assert _strip_identifier_quotes("[employees]") == "employees"
    assert _strip_identifier_quotes("employees") == "employees"

def test_rewrite_month_name_like_filters():
    sql = "SELECT * FROM employees WHERE date_of_hire LIKE '%May%'"
    rewritten = _rewrite_month_name_like_filters(sql)
    assert "SUBSTR(date_of_hire, 4, 2) = '05'" in rewritten

    sql = "SELECT * FROM employees WHERE name LIKE '%May%'"
    rewritten = _rewrite_month_name_like_filters(sql)
    assert rewritten == sql

def test_rewrite_month_extraction_filters():
    sql = "SELECT * FROM employees WHERE STRFTIME('%m', date_of_hire) = '5'"
    rewritten = _rewrite_month_extraction_filters(sql)
    assert "SUBSTR(date_of_hire, 4, 2) = '05'" in rewritten

def test_normalize_conn_string_for_sync():
    async_conn = "postgresql+asyncpg://user:pass@localhost:5432/db"
    sync_conn = _normalize_conn_string_for_sync(async_conn)
    assert sync_conn.startswith("postgresql+psycopg2://")
    assert _normalize_conn_string_for_sync("sqlite:///dev.db") == "sqlite:///dev.db"

# 2. Report Service Unit Tests
def test_report_builder():
    doc = {
        "question": "Show top engineering salaries",
        "sql": "SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 3",
        "results": [
            {"name": "Omar Nady", "salary": 35000},
            {"name": "Sara Malik", "salary": 18000}
        ],
        "insights": [{"en": "Omar is the highest earner.", "ar": "عمر هو الأعلى راتباً."}]
    }
    report = build_report(doc)
    assert "markdown" in report
    assert "filename" in report
    assert report["filename"] == "datapilot-report.md"
    assert "Show top engineering salaries" in report["markdown"]
    assert "عمر هو الأعلى راتباً." in report["markdown"]

# 3. Settings Service Unit Tests
def test_settings_service_load_save():
    # Fetch initial settings
    settings = settings_service.get_settings()
    assert isinstance(settings, dict)
    assert "features" in settings
    
    # Update settings
    updated = settings_service.update_settings({"features": {"auto_visualization": False}})
    assert updated["features"]["auto_visualization"] is False
    
    # Restore settings
    settings_service.update_settings({"features": {"auto_visualization": True}})
    assert settings_service.get_settings()["features"]["auto_visualization"] is True

# 4. Visualization Service Unit Tests
def test_coerce_columns():
    df = pd.DataFrame({
        "name": ["Ahmed", "Sara", "Omar"],
        "age": [32, 28, 45],
        "hire_date": ["2020-03-15", "2021-06-01", "2018-10-10"]
    })
    numeric, datetime_cols, categorical = _coerce_columns(df)
    assert "name" in categorical
    assert "age" in numeric
    
def test_generate_visualization():
    results = [
        {"name": "Ahmed", "salary": 12000},
        {"name": "Sara", "salary": 18000},
        {"name": "Omar", "salary": 35000}
    ]
    viz = generate_visualization(results, "Show salaries of employees")
    assert viz is not None
    assert "chart_type" in viz
    assert "spec" in viz
    assert "data" in viz["spec"]
