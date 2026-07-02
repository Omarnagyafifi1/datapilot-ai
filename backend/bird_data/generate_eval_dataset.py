"""
Generate BIRD-format evaluation dataset with multiple SQLite databases
and question-SQL pairs for Text-to-SQL evaluation.
"""
import json
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATA_DIR = BACKEND_DIR / "bird_data"
DATABASES_DIR = DATA_DIR / "databases"
DEV_SET_DIR = DATA_DIR / "dev_set"

DATABASES_DIR.mkdir(parents=True, exist_ok=True)
DEV_SET_DIR.mkdir(parents=True, exist_ok=True)

SCHEMAS = {
    "sales_db": {
        "description": "Sales transaction database with customers, products, and orders",
        "sql": """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            city TEXT,
            country TEXT,
            registration_date TEXT,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT,
            unit_price REAL,
            stock_quantity INTEGER,
            supplier TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(customer_id),
            order_date TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'Pending'
        );
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES orders(order_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity INTEGER,
            unit_price REAL
        );
        INSERT INTO customers VALUES
            (1, 'Ahmed Ali', 'ahmed@example.com', 'Cairo', 'Egypt', '2024-01-15', 1),
            (2, 'Sara Lee', 'sara@example.com', 'New York', 'USA', '2024-02-20', 1),
            (3, 'John Smith', 'john@example.com', 'London', 'UK', '2024-03-10', 1),
            (4, 'Nadia Hassan', 'nadia@example.com', 'Dubai', 'UAE', '2024-04-05', 1),
            (5, 'Carlos Ruiz', 'carlos@example.com', 'Madrid', 'Spain', '2024-05-01', 0);
        INSERT INTO products VALUES
            (1, 'Laptop Pro 15', 'Electronics', 1299.99, 50, 'TechSupply Co.'),
            (2, 'Wireless Mouse', 'Electronics', 29.99, 200, 'TechSupply Co.'),
            (3, 'Office Chair', 'Furniture', 399.99, 30, 'FurniPro Ltd.'),
            (4, 'Desk Lamp', 'Furniture', 49.99, 100, 'FurniPro Ltd.'),
            (5, 'Coffee Maker', 'Appliances', 89.99, 75, 'HomeGoods Inc.'),
            (6, 'Bluetooth Speaker', 'Electronics', 79.99, 150, 'TechSupply Co.'),
            (7, 'Standing Desk', 'Furniture', 699.99, 20, 'FurniPro Ltd.');
        INSERT INTO orders VALUES
            (1, 1, '2024-06-01', 1329.98, 'Completed'),
            (2, 2, '2024-06-05', 79.99, 'Completed'),
            (3, 1, '2024-06-10', 49.99, 'Completed'),
            (4, 3, '2024-06-15', 429.98, 'Pending'),
            (5, 4, '2024-07-01', 1399.98, 'Completed'),
            (6, 2, '2024-07-10', 699.99, 'Completed'),
            (7, 1, '2024-07-15', 89.99, 'Cancelled');
        INSERT INTO order_items VALUES
            (1, 1, 1, 1, 1299.99),
            (2, 1, 2, 1, 29.99),
            (3, 2, 6, 1, 79.99),
            (4, 3, 4, 1, 49.99),
            (5, 4, 3, 1, 399.99),
            (6, 4, 2, 1, 29.99),
            (7, 5, 1, 1, 1299.99),
            (8, 5, 4, 1, 49.99),
            (9, 5, 2, 1, 29.99),
            (10, 6, 7, 1, 699.99),
            (11, 7, 5, 1, 89.99);
        """
    },
    "employees_db": {
        "description": "Employee management database with departments and salaries",
        "sql": """
        CREATE TABLE IF NOT EXISTS departments (
            dept_id INTEGER PRIMARY KEY,
            dept_name TEXT NOT NULL,
            dept_name_ar TEXT,
            location TEXT,
            budget REAL
        );
        CREATE TABLE IF NOT EXISTS employees (
            emp_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            dept_id INTEGER REFERENCES departments(dept_id),
            salary REAL,
            hire_date TEXT,
            is_manager INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            dept_id INTEGER REFERENCES departments(dept_id),
            start_date TEXT,
            end_date TEXT,
            budget REAL
        );
        INSERT INTO departments VALUES
            (1, 'Engineering', 'الهندسة', 'Building A', 500000),
            (2, 'Marketing', 'التسويق', 'Building B', 300000),
            (3, 'Sales', 'المبيعات', 'Building A', 400000),
            (4, 'HR', 'الموارد البشرية', 'Building C', 150000),
            (5, 'Finance', 'المالية', 'Building C', 250000);
        INSERT INTO employees VALUES
            (1, 'Omar', 'Hassan', 'omar@company.com', 1, 95000, '2020-03-15', 1),
            (2, 'Layla', 'Mohamed', 'layla@company.com', 1, 85000, '2021-06-01', 0),
            (3, 'Ahmed', 'Khalid', 'ahmed@company.com', 2, 72000, '2022-01-10', 0),
            (4, 'Mona', 'Said', 'mona@company.com', 3, 88000, '2020-09-20', 1),
            (5, 'Youssef', 'Ali', 'youssef@company.com', 3, 65000, '2023-04-01', 0),
            (6, 'Dina', 'Mostafa', 'dina@company.com', 4, 55000, '2022-11-15', 1),
            (7, 'Hossam', 'Gamal', 'hossam@company.com', 5, 78000, '2021-08-01', 0),
            (8, 'Nour', 'Ayman', 'nour@company.com', 1, 92000, '2020-02-01', 0),
            (9, 'Sara', 'Emad', 'sara@company.com', 2, 68000, '2023-07-15', 0),
            (10, 'Khaled', 'Walid', 'khaled@company.com', 5, 82000, '2019-12-01', 1);
        INSERT INTO projects VALUES
            (1, 'AI Platform', 1, '2024-01-01', '2024-12-31', 200000),
            (2, 'Brand Refresh', 2, '2024-03-01', '2024-09-30', 80000),
            (3, 'Q4 Sales Campaign', 3, '2024-10-01', '2024-12-31', 120000),
            (4, 'HR Portal', 4, '2024-05-01', '2025-04-30', 60000),
            (5, 'ERP Migration', 5, '2024-02-01', '2025-06-30', 150000);
        """
    },
    "inventory_db": {
        "description": "Warehouse inventory and supply chain management",
        "sql": """
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_id INTEGER PRIMARY KEY,
            warehouse_name TEXT,
            location TEXT,
            capacity INTEGER
        );
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY,
            supplier_name TEXT,
            contact_email TEXT,
            country TEXT,
            reliability_score REAL
        );
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT,
            category TEXT,
            sku TEXT UNIQUE,
            unit_price REAL,
            supplier_id INTEGER REFERENCES suppliers(supplier_id)
        );
        CREATE TABLE IF NOT EXISTS inventory (
            inv_id INTEGER PRIMARY KEY,
            product_id INTEGER REFERENCES products(product_id),
            warehouse_id INTEGER REFERENCES warehouses(warehouse_id),
            quantity INTEGER,
            reorder_level INTEGER,
            last_restocked TEXT
        );
        INSERT INTO warehouses VALUES
            (1, 'Main Warehouse', 'Cairo', 10000),
            (2, 'East Distribution', 'Dubai', 15000),
            (3, 'West Storage', 'New York', 20000);
        INSERT INTO suppliers VALUES
            (1, 'Global Parts Inc.', 'info@globalparts.com', 'USA', 4.5),
            (2, 'Asia Logistics', 'contact@asialog.com', 'China', 4.2),
            (3, 'EuroSupply GmbH', 'info@eurosupply.de', 'Germany', 4.8),
            (4, 'Local Distributor', 'sales@localdist.com', 'Egypt', 3.9);
        INSERT INTO products VALUES
            (1, 'Steel Bolts M10', 'Hardware', 'HW-001', 0.15, 1),
            (2, 'Aluminum Sheets', 'Raw Materials', 'RM-001', 25.00, 2),
            (3, 'LED Panel 60W', 'Electronics', 'EL-001', 45.00, 3),
            (4, 'PVC Pipes 2m', 'Plumbing', 'PL-001', 8.50, 1),
            (5, 'Copper Wire 100m', 'Electronics', 'EL-002', 35.00, 3),
            (6, 'Wooden Pallets', 'Packaging', 'PK-001', 12.00, 4),
            (7, 'Safety Goggles', 'Safety', 'SF-001', 5.50, 2);
        INSERT INTO inventory VALUES
            (1, 1, 1, 5000, 1000, '2024-06-01'),
            (2, 2, 1, 200, 500, '2024-05-15'),
            (3, 3, 2, 150, 100, '2024-06-10'),
            (4, 4, 1, 800, 200, '2024-06-05'),
            (5, 5, 2, 50, 100, '2024-04-20'),
            (6, 6, 3, 1000, 300, '2024-06-12'),
            (7, 7, 3, 300, 100, '2024-06-08'),
            (8, 1, 2, 3000, 1000, '2024-06-01'),
            (9, 3, 1, 80, 100, '2024-06-10'),
            (10, 5, 1, 30, 100, '2024-04-20');
        """
    },
}

QUESTIONS = {
    "sales_db": [
        {
            "question": "How many customers are from Egypt?",
            "sql": "SELECT COUNT(*) FROM customers WHERE country = 'Egypt'",
            "difficulty": "easy",
        },
        {
            "question": "List all electronic products with their prices",
            "sql": "SELECT product_name, unit_price FROM products WHERE category = 'Electronics'",
            "difficulty": "easy",
        },
        {
            "question": "What is the total revenue from completed orders?",
            "sql": "SELECT SUM(total_amount) FROM orders WHERE status = 'Completed'",
            "difficulty": "easy",
        },
        {
            "question": "Which customer has spent the most on completed orders?",
            "sql": "SELECT c.name, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.status = 'Completed' GROUP BY c.name ORDER BY total_spent DESC LIMIT 1",
            "difficulty": "medium",
        },
        {
            "question": "Show the top 3 most ordered products by quantity",
            "sql": "SELECT p.product_name, SUM(oi.quantity) as total_qty FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.product_name ORDER BY total_qty DESC LIMIT 3",
            "difficulty": "medium",
        },
        {
            "question": "What is the average order value per customer?",
            "sql": "SELECT c.name, ROUND(AVG(o.total_amount), 2) as avg_order FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.name",
            "difficulty": "medium",
        },
        {
            "question": "Which products have never been ordered?",
            "sql": "SELECT p.product_name FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id WHERE oi.product_id IS NULL",
            "difficulty": "hard",
        },
        {
            "question": "Find customers with more than one completed order",
            "sql": "SELECT c.name, COUNT(o.order_id) as order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.status = 'Completed' GROUP BY c.name HAVING order_count > 1",
            "difficulty": "medium",
        },
    ],
    "employees_db": [
        {
            "question": "How many employees are in the Engineering department?",
            "sql": "SELECT COUNT(*) FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE d.dept_name = 'Engineering'",
            "difficulty": "easy",
        },
        {
            "question": "List all employees with salaries above 80000",
            "sql": "SELECT first_name, last_name, salary FROM employees WHERE salary > 80000",
            "difficulty": "easy",
        },
        {
            "question": "What is the average salary per department?",
            "sql": "SELECT d.dept_name, ROUND(AVG(e.salary), 2) as avg_salary FROM employees e JOIN departments d ON e.dept_id = d.dept_id GROUP BY d.dept_name",
            "difficulty": "easy",
        },
        {
            "question": "Find the department with the highest total salary budget",
            "sql": "SELECT d.dept_name, SUM(e.salary) as total_salary FROM employees e JOIN departments d ON e.dept_id = d.dept_id GROUP BY d.dept_name ORDER BY total_salary DESC LIMIT 1",
            "difficulty": "easy",
        },
        {
            "question": "Show departments with their project count and total project budget",
            "sql": "SELECT d.dept_name, COUNT(p.project_id) as project_count, SUM(p.budget) as total_budget FROM departments d LEFT JOIN projects p ON d.dept_id = p.dept_id GROUP BY d.dept_name",
            "difficulty": "medium",
        },
        {
            "question": "Who are the managers and which departments do they manage?",
            "sql": "SELECT e.first_name, e.last_name, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE e.is_manager = 1",
            "difficulty": "easy",
        },
        {
            "question": "Find employees who earn more than their department average",
            "sql": "SELECT e.first_name, e.last_name, e.salary, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE e.salary > (SELECT AVG(e2.salary) FROM employees e2 WHERE e2.dept_id = e.dept_id)",
            "difficulty": "hard",
        },
        {
            "question": "Which departments have no active projects?",
            "sql": "SELECT d.dept_name FROM departments d LEFT JOIN projects p ON d.dept_id = p.dept_id WHERE p.project_id IS NULL",
            "difficulty": "medium",
        },
    ],
    "employees_ar_db": [
        {
            "question": "ما هو متوسط الراتب لكل قسم؟",
            "sql": "SELECT d.dept_name_ar AS 'القسم', ROUND(AVG(e.salary), 2) AS 'متوسط الراتب' FROM employees e JOIN departments d ON e.dept_id = d.dept_id GROUP BY d.dept_name_ar",
            "difficulty": "easy",
        },
        {
            "question": "اعرض الأقسام مع عدد المشاريع وإجمالي ميزانيتها",
            "sql": "SELECT d.dept_name_ar AS 'القسم', COUNT(p.project_id) AS 'عدد المشاريع', SUM(p.budget) AS 'إجمالي الميزانية' FROM departments d LEFT JOIN projects p ON d.dept_id = p.dept_id GROUP BY d.dept_name_ar",
            "difficulty": "medium",
        },
        {
            "question": "من هم المدراء وما هي الأقسام التي يديرونها؟",
            "sql": "SELECT e.first_name AS 'الاسم الأول', e.last_name AS 'اسم العائلة', d.dept_name_ar AS 'القسم' FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE e.is_manager = 1",
            "difficulty": "easy",
        },
        {
            "question": "كم عدد الموظفين في قسم الهندسة؟",
            "sql": "SELECT COUNT(*) FROM employees e JOIN departments d ON e.dept_id = d.dept_id WHERE d.dept_name_ar = 'الهندسة'",
            "difficulty": "easy",
        },
    ],
    "sales_ar_db": [
        {
            "question": "ما إجمالي الإيرادات من الطلبات المكتملة؟",
            "sql": "SELECT SUM(total_amount) FROM orders WHERE status = 'Completed'",
            "difficulty": "easy",
        },
    ],
    "inventory_ar_db": [
        {
            "question": "اعرض المنتجات التي تحتاج إعادة تخزين مع معلومات المورد",
            "sql": "SELECT p.product_name AS 'اسم المنتج', i.quantity AS 'الكمية', i.reorder_level AS 'مستوى إعادة الطلب', s.supplier_name AS 'المورد' FROM products p JOIN inventory i ON p.product_id = i.product_id JOIN suppliers s ON p.supplier_id = s.supplier_id WHERE i.quantity < i.reorder_level",
            "difficulty": "medium",
        },
    ],
    "inventory_db": [
        {"question": "How many products are below their reorder level?", "sql": "SELECT COUNT(*) FROM inventory WHERE quantity < reorder_level", "difficulty": "easy"},
        {"question": "List all suppliers with reliability score above 4.0", "sql": "SELECT supplier_name, reliability_score FROM suppliers WHERE reliability_score > 4.0", "difficulty": "easy"},
        {"question": "What is the total quantity of each product across all warehouses?", "sql": "SELECT p.product_name, SUM(i.quantity) as total_qty FROM products p JOIN inventory i ON p.product_id = i.product_id GROUP BY p.product_name", "difficulty": "easy"},
        {"question": "Find warehouses that have products below reorder level", "sql": "SELECT DISTINCT w.warehouse_name FROM warehouses w JOIN inventory i ON w.warehouse_id = i.warehouse_id WHERE i.quantity < i.reorder_level", "difficulty": "medium"},
        {"question": "Which supplier provides the most expensive product?", "sql": "SELECT s.supplier_name, p.product_name, p.unit_price FROM suppliers s JOIN products p ON s.supplier_id = p.supplier_id ORDER BY p.unit_price DESC LIMIT 1", "difficulty": "medium"},
        {"question": "Show products that need restocking (quantity below reorder level) with supplier info", "sql": "SELECT p.product_name, s.supplier_name, i.quantity, i.reorder_level FROM products p JOIN inventory i ON p.product_id = i.product_id JOIN suppliers s ON p.supplier_id = s.supplier_id WHERE i.quantity < i.reorder_level", "difficulty": "medium"},
        {"question": "What is the total inventory value per warehouse?", "sql": "SELECT w.warehouse_name, SUM(i.quantity * p.unit_price) as total_value FROM warehouses w JOIN inventory i ON w.warehouse_id = i.warehouse_id JOIN products p ON i.product_id = p.product_id GROUP BY w.warehouse_name", "difficulty": "medium"},
        {"question": "Which categories have total stock value exceeding 5000?", "sql": "SELECT p.category, SUM(i.quantity * p.unit_price) as total_value FROM products p JOIN inventory i ON p.product_id = i.product_id GROUP BY p.category HAVING total_value > 5000", "difficulty": "hard"},
    ],
}

SCHEMAS["employees_ar_db"] = {"description": "Employee management database with Arabic column support", "sql": SCHEMAS["employees_db"]["sql"]}
SCHEMAS["sales_ar_db"] = {"description": "Sales database for Arabic question testing", "sql": SCHEMAS["sales_db"]["sql"]}
SCHEMAS["inventory_ar_db"] = {"description": "Inventory database for Arabic question testing", "sql": SCHEMAS["inventory_db"]["sql"]}


def create_databases():
    for db_name, schema in SCHEMAS.items():
        db_path = DATABASES_DIR / f"{db_name}.db"
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(db_path)
        conn.executescript(schema["sql"])
        conn.commit()
        conn.close()
        print(f"Created: {db_path.name}")


def generate_dev_set():
    all_examples = []
    for db_id, questions in QUESTIONS.items():
        for q in questions:
            all_examples.append({
                "db_id": db_id,
                "question": q["question"],
                "sql": q["sql"],
                "difficulty": q["difficulty"],
            })
    output_path = DEV_SET_DIR / "dev.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_examples, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(all_examples)} evaluation examples -> {output_path}")
    return all_examples


def register_sources():
    from app.services.data_source_service import DataSourceService
    svc = DataSourceService()
    for db_name in SCHEMAS:
        db_path = DATABASES_DIR / f"{db_name}.db"
        params = {
            "name": f"BIRD Eval: {SCHEMAS[db_name]['description']}",
            "db_type": "sqlite",
            "db_name": str(db_path),
            "host": "",
            "port": None,
            "username": "",
            "password": "",
        }
        result = svc.save_source(params)
        if result.get("success"):
            print(f"Registered: {db_name} -> source_id={result['id']}")
        else:
            print(f"Failed to register {db_name}: {result}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action in ("all", "databases"):
        create_databases()
    if action in ("all", "questions"):
        generate_dev_set()
    if action in ("all", "register"):
        register_sources()
