#!/usr/bin/env python3
"""
Generate mock datasets for DataPilot AI.

Creates both CSV and SQLite versions of:
- Student Management
- University Courses
- Employee Records
- E-commerce Orders
- Library System
"""

import os
import sqlite3
import csv
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "sample_data"
OUTPUT_DIR.mkdir(exist_ok=True)

def create_student_management():
    """Create student management dataset."""
    # Data
    departments = [
        (1, "Computer Science", "Engineering"),
        (2, "Mathematics", "Science"),
        (3, "Physics", "Science"),
        (4, "English", "Arts"),
    ]
    
    students = [
        (1, "Alice Johnson", 1, 2021, 3.85),
        (2, "Bob Smith", 1, 2020, 3.62),
        (3, "Charlie Brown", 2, 2021, 3.91),
        (4, "Diana Ross", 3, 2022, 3.75),
        (5, "Eve Wilson", 1, 2019, 3.45),
        (6, "Frank Miller", 2, 2020, 3.78),
        (7, "Grace Lee", 4, 2021, 3.88),
        (8, "Henry Davis", 1, 2022, 3.56),
        (9, "Ivy Chen", 3, 2020, 3.92),
        (10, "Jack Taylor", 2, 2021, 3.67),
        (11, "Karen White", 1, 2019, 3.41),
        (12, "Leo Garcia", 4, 2022, 3.73),
    ]
    
    enrollments = [
        (1, 1, "CS101", "A", 2021),
        (2, 1, "MATH201", "B+", 2021),
        (3, 2, "CS101", "B", 2020),
        (4, 2, "PHYS101", "A-", 2020),
        (5, 3, "MATH201", "A", 2021),
        (6, 4, "PHYS101", "B+", 2022),
        (7, 5, "CS101", "C+", 2021),
        (8, 5, "MATH201", "B-", 2021),
        (9, 6, "MATH201", "A-", 2020),
        (10, 7, "ENG101", "A", 2021),
        (11, 8, "CS101", "B+", 2022),
        (12, 9, "PHYS101", "A", 2020),
    ]
    
    grades = [
        (1, "CS101", 92, "2021-06-15"),
        (2, "MATH201", 85, "2021-06-15"),
        (3, "CS101", 78, "2020-06-10"),
        (4, "PHYS101", 88, "2020-06-10"),
    ]
    
    # Create CSV files
    with open(OUTPUT_DIR / "student_management_departments.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "faculty"])
        writer.writerows(departments)
    
    # Create combined CSV
    with open(OUTPUT_DIR / "student_management.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "department_id", "enroll_year", "gpa"])
        writer.writerows(students)
    
    # Create SQLite
    db_path = OUTPUT_DIR / "student_management.db"
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, faculty TEXT)")
    cur.executemany("INSERT INTO departments VALUES (?, ?, ?)", departments)
    
    cur.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, department_id INTEGER, enroll_year INTEGER, gpa REAL)")
    cur.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", students)
    
    cur.execute("CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER, course_code TEXT, grade TEXT, year INTEGER)")
    cur.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?, ?)", enrollments)
    
    cur.execute("CREATE TABLE grades (student_id INTEGER, course_code TEXT, score INTEGER, date TEXT)")
    cur.executemany("INSERT INTO grades VALUES (?, ?, ?, ?)", grades)
    
    conn.commit()
    conn.close()
    
    print(f"Created: {db_path}")


def create_university_courses():
    """Create university courses dataset."""
    departments = [
        (1, "Computer Science", "Prof. Anderson"),
        (2, "Mathematics", "Prof. Baker"),
        (3, "Physics", "Prof. Clark"),
    ]
    
    instructors = [
        (1, "Dr. Smith", "CS", "smith@edu"),
        (2, "Dr. Johnson", "CS", "johnson@edu"),
        (3, "Dr. Williams", "MATH", "williams@edu"),
        (4, "Dr. Brown", "PHYS", "brown@edu"),
    ]
    
    courses = [
        (1, "CS101", "Intro to Programming", 1, 1),
        (2, "CS201", "Data Structures", 1, 2),
        (3, "MATH101", "Calculus I", 2, 1),
        (4, "MATH201", "Linear Algebra", 2, 2),
        (5, "PHYS101", "Mechanics", 3, 1),
        (6, "PHYS201", "Thermodynamics", 3, 2),
    ]
    
    # Create CSV
    with open(OUTPUT_DIR / "university_courses.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "code", "name", "department_id", "credits"])
        writer.writerows(courses)
    
    # Create SQLite
    db_path = OUTPUT_DIR / "university_courses.db"
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, head TEXT)")
    cur.executemany("INSERT INTO departments VALUES (?, ?, ?)", departments)
    
    cur.execute("CREATE TABLE instructors (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, email TEXT)")
    cur.executemany("INSERT INTO instructors VALUES (?, ?, ?, ?)", instructors)
    
    cur.execute("CREATE TABLE courses (id INTEGER PRIMARY KEY, code TEXT, name TEXT, department_id INTEGER, credits INTEGER)")
    cur.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?)", courses)
    
    conn.commit()
    conn.close()
    
    print(f"Created: {db_path}")


def create_employee_records():
    """Create employee records dataset."""
    departments = [
        (1, "Engineering"),
        (2, "Marketing"),
        (3, "Sales"),
        (4, "HR"),
    ]
    
    employees = [
        (1, "John Doe", 1, "Developer", 75000, "2020-01-15"),
        (2, "Jane Smith", 1, "Senior Developer", 95000, "2018-03-20"),
        (3, "Mike Johnson", 2, "Marketing Manager", 65000, "2019-06-01"),
        (4, "Sarah Williams", 2, "Designer", 55000, "2021-02-10"),
        (5, "Tom Brown", 3, "Sales Rep", 50000, "2020-11-05"),
        (6, "Lisa Davis", 3, "Sales Lead", 70000, "2019-08-15"),
        (7, "Alex Chen", 1, "QA Engineer", 65000, "2021-04-01"),
        (8, "Maria Garcia", 4, "HR Specialist", 45000, "2022-01-10"),
    ]
    
    salaries = [
        (1, 75000, 2020, "USD"),
        (2, 95000, 2020, "USD"),
        (3, 65000, 2019, "USD"),
        (4, 55000, 2021, "USD"),
        (5, 50000, 2020, "USD"),
        (6, 70000, 2019, "USD"),
        (7, 65000, 2021, "USD"),
        (8, 45000, 2022, "USD"),
    ]
    
    # Create CSV
    with open(OUTPUT_DIR / "employee_records.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "department_id", "position", "salary", "hire_date"])
        writer.writerows(employees)
    
    # Create SQLite
    db_path = OUTPUT_DIR / "employee_records.db"
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT)")
    cur.executemany("INSERT INTO departments VALUES (?, ?)", departments)
    
    cur.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, department_id INTEGER, position TEXT, salary REAL, hire_date TEXT)")
    cur.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", employees)
    
    cur.execute("CREATE TABLE salaries (employee_id INTEGER PRIMARY KEY, amount REAL, year INTEGER, currency TEXT)")
    cur.executemany("INSERT INTO salaries VALUES (?, ?, ?, ?)", salaries)
    
    conn.commit()
    conn.close()
    
    print(f"Created: {db_path}")


def create_ecommerce_orders():
    """Create e-commerce orders dataset."""
    categories = [
        (1, "Electronics", "Gadgets and devices"),
        (2, "Clothing", "Apparel and accessories"),
        (3, "Books", "Educational materials"),
    ]
    
    customers = [
        (1, "Alice Cooper", "alice@example.com", "2020-01-01"),
        (2, "Bob Marley", "bob@example.com", "2020-02-15"),
        (3, "Carol King", "carol@example.com", "2020-03-20"),
        (4, "David Bowie", "david@example.com", "2020-04-10"),
    ]
    
    products = [
        (1, "Laptop", 999.99, 1, 50),
        (2, "Smartphone", 599.99, 1, 100),
        (3, "T-Shirt", 19.99, 2, 200),
        (4, "Jeans", 49.99, 2, 150),
        (5, "Python Book", 29.99, 3, 75),
    ]
    
    orders = [
        (1, 1, "2023-01-15", "completed"),
        (2, 1, "2023-02-20", "completed"),
        (3, 2, "2023-03-10", "pending"),
        (4, 3, "2023-04-05", "completed"),
    ]
    
    order_items = [
        (1, 1, 1, 1, 999.99),
        (2, 1, 2, 1, 599.99),
        (3, 2, 3, 2, 39.98),
        (4, 3, 5, 1, 29.99),
        (5, 4, 4, 1, 49.99),
    ]
    
    # Create CSV
    with open(OUTPUT_DIR / "ecommerce_orders.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "customer_id", "order_date", "status"])
        writer.writerows(orders)
    
    # Create SQLite
    db_path = OUTPUT_DIR / "ecommerce_orders.db"
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT, description TEXT)")
    cur.executemany("INSERT INTO categories VALUES (?, ?, ?)", categories)
    
    cur.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT, created_at TEXT)")
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
    
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, category_id INTEGER, stock INTEGER)")
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)
    
    cur.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT)")
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    
    cur.execute("CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, total REAL)")
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items)
    
    conn.commit()
    conn.close()
    
    print(f"Created: {db_path}")


def create_library_system():
    """Create library system dataset."""
    authors = [
        (1, "J.K. Rowling"),
        (2, "George Orwell"),
        (3, "Jane Austen"),
    ]
    
    publishers = [
        (1, "Penguin Books"),
        (2, "Harper Collins"),
    ]
    
    books = [
        (1, "Harry Potter", 1, 1, 2001),
        (2, "1984", 2, 1, 1949),
        (3, "Pride and Prejudice", 3, 2, 1813),
    ]
    
    members = [
        (1, "Alice Johnson", "alice@library.com", "2019-05-01"),
        (2, "Bob Smith", "bob@library.com", "2020-03-15"),
        (3, "Carol White", "carol@library.com", "2021-01-10"),
    ]
    
    loans = [
        (1, 1, 1, "2023-05-01", "2023-05-15", "returned"),
        (2, 2, 2, "2023-05-10", "2023-05-24", "returned"),
        (3, 3, 3, "2023-06-01", "2023-06-15", "active"),
    ]
    
    # Create CSV
    with open(OUTPUT_DIR / "library_system.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "member_id", "book_id", "loan_date", "due_date", "status"])
        writer.writerows(loans)
    
    # Create SQLite
    db_path = OUTPUT_DIR / "library_system.db"
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT)")
    cur.executemany("INSERT INTO authors VALUES (?, ?)", authors)
    
    cur.execute("CREATE TABLE publishers (id INTEGER PRIMARY KEY, name TEXT)")
    cur.executemany("INSERT INTO publishers VALUES (?, ?)", publishers)
    
    cur.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, author_id INTEGER, publisher_id INTEGER, publish_year INTEGER)")
    cur.executemany("INSERT INTO books VALUES (?, ?, ?, ?, ?)", books)
    
    cur.execute("CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT, email TEXT, joined_date TEXT)")
    cur.executemany("INSERT INTO members VALUES (?, ?, ?, ?)", members)
    
    cur.execute("CREATE TABLE loans (id INTEGER PRIMARY KEY, member_id INTEGER, book_id INTEGER, loan_date TEXT, due_date TEXT, status TEXT)")
    cur.executemany("INSERT INTO loans VALUES (?, ?, ?, ?, ?, ?)", loans)
    
    conn.commit()
    conn.close()
    
    print(f"Created: {db_path}")


if __name__ == "__main__":
    print("Generating mock datasets...")
    create_student_management()
    create_university_courses()
    create_employee_records()
    create_ecommerce_orders()
    create_library_system()
    print("Done! All datasets created in:", OUTPUT_DIR)