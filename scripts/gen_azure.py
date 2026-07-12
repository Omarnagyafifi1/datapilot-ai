"""
Azure-optimized version: generates test dataset directly on Azure Files.
Uses DELETE journal mode (WAL doesn't work on SMB/Azure Files).
"""
import sqlite3, os, sys, random, time, json
from datetime import datetime, timedelta

random.seed(42)

SCALE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/mnt/uploads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT = os.path.join(OUTPUT_DIR, f"test_dataset_{TIMESTAMP}.db")
LOG = os.path.join(OUTPUT_DIR, f"gen_azure_{TIMESTAMP}.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")
    print(msg, flush=True)

EN_FIRST = "Ahmed,Omar,Mohamed,Ali,Hassan,Karim,Layla,Noor,Fatima,Aisha".split(",")
AR_FIRST = "أحمد,عمر,محمد,علي,حسن,كريم,ليلى,نور,فاطمة,عائشة".split(",")
EN_LAST = "Hassan,Mohamed,Ali,Youssef,Khalil,Ibrahim".split(",")
AR_LAST = "حسن,محمد,علي,يوسف,خليل,إبراهيم".split(",")
EN_CITIES = "Cairo,Dubai,Riyadh,Doha,Muscat,Kuwait,Manama,Amman".split(",")
AR_CITIES = "القاهرة,دبي,الرياض,الدوحة,مسقط,الكويت,المنامة,عمان".split(",")
EN_COUNTRIES = "Egypt,UAE,Saudi,Qatar,Oman,Kuwait,Bahrain".split(",")
AR_COUNTRIES = "مصر,الإمارات,السعودية,قطر,عمان,الكويت,البحرين".split(",")
EN_DEPT = "Engineering,Marketing,Sales,HR,Finance,Operations,R&D".split(",")
AR_DEPT = "الهندسة,التسويق,المبيعات,الموارد البشرية,المالية,العمليات,البحث".split(",")
EN_PROD = "Smartphone,Laptop,Headphones,Chair,Coffee,Notebook,Monitor".split(",")
AR_PROD = "هاتف,حاسوب,سماعات,كرسي,قهوة,مفكرة,شاشة".split(",")
EN_CATS = "Electronics,Clothing,Food,Furniture,Books,Sports,Beauty".split(",")
AR_CATS = "إلكترونيات,ملابس,أغذية,أثاث,كتب,رياضة,تجميل".split(",")
EN_PAY = "Credit Card,Cash,Transfer,PayPal".split(",")
AR_PAY = "بطاقة,نقدي,تحويل,باي بال".split(",")
EN_ST = "Pending,Processing,Shipped,Delivered,Cancelled".split(",")
AR_ST = "قيد الانتظار,قيد المعالجة,تم الشحن,تم التوصيل,ملغي".split(",")

def pick(lst): return lst[random.randint(0, len(lst)-1)]
def _fix_date(d):
    if len(d) == 4: return d + "-01-01"
    return d
def rdate(s="2020-01-01", e="2026-07-12"):
    s = _fix_date(s); e = _fix_date(e)
    ss = datetime.strptime(s, "%Y-%m-%d")
    ee = datetime.strptime(e, "%Y-%m-%d")
    return (ss + timedelta(seconds=random.randint(0, int((ee-ss).total_seconds())))).strftime("%Y-%m-%d %H:%M:%S")
def rdonly(s="2020-01-01", e="2026-07-12"):
    return rdate(s, e)[:10]

def batch_insert(db, table, cols, rows_gen, bs=25000):
    ph = ",".join(["?"]*len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph})"
    batch, cnt, t0 = [], 0, time.time()
    for row in rows_gen:
        batch.append(row)
        if len(batch) >= bs:
            db.executemany(sql, batch); cnt += len(batch); batch = []
            log(f"  {table}: {cnt:,}")
    if batch: db.executemany(sql, batch); cnt += len(batch)
    log(f"  {table}: {cnt:,} DONE ({time.time()-t0:.1f}s)")
    return cnt

def main():
    t0 = time.time()
    log(f"Starting: OUTPUT={OUTPUT} SCALE={SCALE}")
    if os.path.exists(OUTPUT): os.remove(OUTPUT)

    db = sqlite3.connect(OUTPUT)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA cache_size=-2000000")
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("PRAGMA locking_mode=NORMAL")

    schema = """
    CREATE TABLE companies(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, industry_en TEXT, industry_ar TEXT, founded_date TEXT, revenue REAL, employee_count INTEGER, country_en TEXT, country_ar TEXT);
    CREATE TABLE branches(id INTEGER PRIMARY KEY, company_id INTEGER, name_en TEXT, name_ar TEXT, city_en TEXT, city_ar TEXT, address TEXT, phone TEXT, manager_id INTEGER);
    CREATE TABLE departments(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, description_en TEXT, description_ar TEXT, budget REAL, company_id INTEGER);
    CREATE TABLE employees(id INTEGER PRIMARY KEY, first_name_en TEXT, first_name_ar TEXT, last_name_en TEXT, last_name_ar TEXT, email TEXT, phone TEXT, hire_date TEXT, salary REAL, department_id INTEGER, branch_id INTEGER, manager_id INTEGER, is_active INTEGER);
    CREATE TABLE customers(id INTEGER PRIMARY KEY, first_name_en TEXT, first_name_ar TEXT, last_name_en TEXT, last_name_ar TEXT, email TEXT, phone TEXT, city_en TEXT, city_ar TEXT, country_en TEXT, country_ar TEXT, registration_date TEXT, total_purchases REAL, is_vip INTEGER);
    CREATE TABLE categories(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, description_en TEXT, description_ar TEXT, parent_id INTEGER);
    CREATE TABLE products(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, description_en TEXT, description_ar TEXT, category_id INTEGER, supplier_id INTEGER, unit_price REAL, stock_quantity INTEGER, reorder_level INTEGER, is_active INTEGER, created_date TEXT);
    CREATE TABLE suppliers(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, contact_name_en TEXT, contact_name_ar TEXT, email TEXT, phone TEXT, city_en TEXT, city_ar TEXT, country_en TEXT, country_ar TEXT, rating INTEGER);
    CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, total_amount REAL, status_en TEXT, status_ar TEXT, payment_method_en TEXT, payment_method_ar TEXT, shipping_address TEXT, notes TEXT);
    CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL, discount REAL, total_price REAL);
    CREATE TABLE inventory(id INTEGER PRIMARY KEY, product_id INTEGER, warehouse_en TEXT, warehouse_ar TEXT, quantity INTEGER, last_restock_date TEXT, min_quantity INTEGER, max_quantity INTEGER);
    CREATE TABLE transactions(id INTEGER PRIMARY KEY, order_id INTEGER, transaction_date TEXT, amount REAL, type_en TEXT, type_ar TEXT, status_en TEXT, status_ar TEXT, reference_number TEXT);
    CREATE TABLE shipping(id INTEGER PRIMARY KEY, order_id INTEGER, carrier_en TEXT, carrier_ar TEXT, tracking_number TEXT, shipped_date TEXT, delivered_date TEXT, status_en TEXT, status_ar TEXT, weight REAL, shipping_cost REAL);
    CREATE TABLE reviews(id INTEGER PRIMARY KEY, product_id INTEGER, customer_id INTEGER, rating INTEGER, title_en TEXT, title_ar TEXT, review_text_en TEXT, review_text_ar TEXT, review_date TEXT, is_verified INTEGER);
    CREATE TABLE audit_log(id INTEGER PRIMARY KEY, table_name TEXT, record_id INTEGER, action_en TEXT, action_ar TEXT, changed_by TEXT, changed_at TEXT, old_values TEXT, new_values TEXT);
    """
    for stmt in schema.strip().split(";"):
        s = stmt.strip()
        if s: db.execute(s + ";")

    n_cos = int(200 * SCALE)
    n_br = int(1000 * SCALE)
    n_dept = int(800 * SCALE)
    n_emp = int(100000 * SCALE)
    n_cust = int(200000 * SCALE)
    n_cat = int(150 * SCALE)
    n_sup = int(5000 * SCALE)
    n_prod = int(50000 * SCALE)
    n_ord = int(500000 * SCALE)
    n_oi = int(2000000 * SCALE)
    n_inv = int(50000 * SCALE)
    n_tx = int(500000 * SCALE)
    n_shp = int(400000 * SCALE)
    n_rev = int(200000 * SCALE)
    n_audit = int(100000 * SCALE)

    log("--- companies ---")
    batch_insert(db, "companies", ["id","name_en","name_ar","industry_en","industry_ar","founded_date","revenue","employee_count","country_en","country_ar"],
        ((i, f"Company {i}", f"شركة {i}", pick(EN_CATS), pick(AR_CATS), rdonly("1990-01-01","2020-01-01"), round(random.uniform(1e6,5e9),2), random.randint(50,50000), pick(EN_COUNTRIES), pick(AR_COUNTRIES)) for i in range(1, n_cos+1)))
    db.commit()

    log("--- branches ---")
    batch_insert(db, "branches", ["id","company_id","name_en","name_ar","city_en","city_ar","address","phone","manager_id"],
        ((i, random.randint(1,n_cos), f"Branch {i}", f"فرع {i}", pick(EN_CITIES), pick(AR_CITIES), f"Addr {i}", f"+971{50+i%8}{i:07d}", None) for i in range(1, n_br+1)))
    db.commit()

    log("--- departments ---")
    batch_insert(db, "departments", ["id","name_en","name_ar","description_en","description_ar","budget","company_id"],
        ((i, f"{pick(EN_DEPT)} {i}", f"{pick(AR_DEPT)} {i}", f"Dept desc {i}", f"وصف {i}", round(random.uniform(50000,5e6),2), random.randint(1,n_cos)) for i in range(1, n_dept+1)))
    db.commit()

    log("--- employees ---")
    batch_insert(db, "employees", ["id","first_name_en","first_name_ar","last_name_en","last_name_ar","email","phone","hire_date","salary","department_id","branch_id","manager_id","is_active"],
        ((i, pick(EN_FIRST), pick(AR_FIRST), pick(EN_LAST), pick(AR_LAST), f"emp{i}@co.com", f"+971{50+i%8}{i:07d}", rdonly("2015","2026"), round(random.uniform(3000,50000),2), random.randint(1,n_dept), random.randint(1,n_br), None if i<50 else random.randint(1,n_emp-1), 1 if random.random()<0.95 else 0) for i in range(1, n_emp+1)))
    db.commit()

    log("--- customers ---")
    batch_insert(db, "customers", ["id","first_name_en","first_name_ar","last_name_en","last_name_ar","email","phone","city_en","city_ar","country_en","country_ar","registration_date","total_purchases","is_vip"],
        ((i, pick(EN_FIRST), pick(AR_FIRST), pick(EN_LAST), pick(AR_LAST), f"cust{i}@ml.com", f"+971{50+i%8}{i:07d}", pick(EN_CITIES), pick(AR_CITIES), pick(EN_COUNTRIES), pick(AR_COUNTRIES), rdonly("2018","2026"), round(random.uniform(0,50000),2), 1 if random.random()<0.08 else 0) for i in range(1, n_cust+1)))
    db.commit()

    log("--- categories ---")
    cat_ids = []
    for i in range(1, n_cat+1):
        ci = ((i-1) % len(EN_CATS))
        cat_ids.append(i)
        db.execute("INSERT INTO categories VALUES(?,?,?,?,?,?)", (i, f"{EN_CATS[ci]} {i}", f"{AR_CATS[ci]} {i}", f"Cat {i}", f"فئة {i}", None if i<=len(EN_CATS) else random.choice(cat_ids[:-1])))
    db.commit()
    log(f"  categories: {n_cat} DONE")

    log("--- suppliers ---")
    batch_insert(db, "suppliers", ["id","name_en","name_ar","contact_name_en","contact_name_ar","email","phone","city_en","city_ar","country_en","country_ar","rating"],
        ((i, f"Supplier {i}", f"مورد {i}", f"Contact {i}", f"جهة اتصال {i}", f"sup{i}@sp.com", f"+971{50+i%8}{i:07d}", pick(EN_CITIES), pick(AR_CITIES), pick(EN_COUNTRIES), pick(AR_COUNTRIES), random.randint(1,5)) for i in range(1, n_sup+1)))
    db.commit()

    log("--- products ---")
    batch_insert(db, "products", ["id","name_en","name_ar","description_en","description_ar","category_id","supplier_id","unit_price","stock_quantity","reorder_level","is_active","created_date"],
        ((i, f"{pick(EN_PROD)} {i}", f"{pick(AR_PROD)} {i}", f"Desc {i}", f"وصف {i}", random.choice(cat_ids), random.randint(1,n_sup), round(random.uniform(5,5000),2), random.randint(0,5000), random.randint(5,50), 1 if random.random()<0.92 else 0, rdonly("2019","2026")) for i in range(1, n_prod+1)))
    db.commit()

    log("--- orders ---")
    batch_insert(db, "orders", ["id","customer_id","order_date","total_amount","status_en","status_ar","payment_method_en","payment_method_ar","shipping_address","notes"],
        ((i, random.randint(1,n_cust), rdate("2021","2026"), 0.0, pick(EN_ST), pick(AR_ST), pick(EN_PAY), pick(AR_PAY), f"Addr {i}", "") for i in range(1, n_ord+1)))
    db.commit()

    log("--- order_items ---")
    batch_insert(db, "order_items", ["id","order_id","product_id","quantity","unit_price","discount","total_price"],
        ((i, random.randint(1,n_ord), random.randint(1,n_prod), random.randint(1,10), round(random.uniform(5,5000),2), round(random.choice([0,0,0,0.05,0.1,0.15]),2), 0.0) for i in range(1, n_oi+1)), bs=100000)
    db.commit()

    log("Updating order totals...")
    db.execute("UPDATE orders SET total_amount = (SELECT COALESCE(ROUND(SUM(total_price * (1-discount)),2),0) FROM order_items WHERE order_id = orders.id)")
    db.commit()

    log("--- inventory ---")
    batch_insert(db, "inventory", ["id","product_id","warehouse_en","warehouse_ar","quantity","last_restock_date","min_quantity","max_quantity"],
        ((i, i, f"WH {i%9}", f"مستودع {i%9}", random.randint(0,5000), rdonly("2023","2026"), random.randint(10,200), random.randint(500,5000)) for i in range(1, n_inv+1)))
    db.commit()

    log("--- transactions ---")
    batch_insert(db, "transactions", ["id","order_id","transaction_date","amount","type_en","type_ar","status_en","status_ar","reference_number"],
        ((i, random.randint(1,n_ord), rdate("2021","2026"), round(random.uniform(10,50000),2), pick(["Sale","Refund"]), pick(["بيع","استرجاع"]), pick(EN_ST), pick(AR_ST), f"TXN{i:08d}") for i in range(1, n_tx+1)))
    db.commit()

    log("--- shipping ---")
    batch_insert(db, "shipping", ["id","order_id","carrier_en","carrier_ar","tracking_number","shipped_date","delivered_date","status_en","status_ar","weight","shipping_cost"],
        ((i, random.randint(1,n_ord), pick(["Aramex","DHL","UPS"]), pick(["أرامكس","دي إتش إل","يو بي إس"]), f"TRK{i:08d}", rdate("2021","2026"), rdate("2021","2026"), pick(EN_ST), pick(AR_ST), round(random.uniform(0.5,50),2), round(random.uniform(5,500),2)) for i in range(1, n_shp+1)))
    db.commit()

    log("--- reviews ---")
    ratings = [1]*5 + [2]*10 + [3]*20 + [4]*35 + [5]*30
    batch_insert(db, "reviews", ["id","product_id","customer_id","rating","title_en","title_ar","review_text_en","review_text_ar","review_date","is_verified"],
        ((i, random.randint(1,n_prod), random.randint(1,n_cust), random.choice(ratings), f"Review {i}", f"مراجعة {i}", f"Review text {i}", f"نص المراجعة {i}", rdate("2021","2026"), 1 if random.random()<0.7 else 0) for i in range(1, n_rev+1)))
    db.commit()

    log("--- audit_log ---")
    batch_insert(db, "audit_log", ["id","table_name","record_id","action_en","action_ar","changed_by","changed_at","old_values","new_values"],
        ((i, pick(["employees","orders","products"]), random.randint(1,100000), pick(["UPDATE","CREATE","DELETE"]), pick(["تحديث","إنشاء","حذف"]), f"user{i%100}", rdate("2024","2026"), "{}", "{}") for i in range(1, n_audit+1)))
    db.commit()

    log("Indexing...")
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department_id)",
        "CREATE INDEX IF NOT EXISTS idx_emp_branch ON employees(branch_id)",
        "CREATE INDEX IF NOT EXISTS idx_ord_cust ON orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_oi_order ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_oi_prod ON order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_prod_cat ON products(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_rev_prod ON reviews(product_id)",
    ]:
        db.execute(idx)
    db.commit()

    db.execute("ANALYZE")
    db.execute("VACUUM")
    db.commit()
    db.close()

    sz = os.path.getsize(OUTPUT) / (1024*1024)
    total = n_cos + n_br + n_dept + n_emp + n_cust + n_cat + n_sup + n_prod + n_ord + n_oi + n_inv + n_tx + n_shp + n_rev + n_audit
    elapsed = time.time() - t0
    log(f"\n{'='*50}")
    log(f"DONE: {sz:.0f}MB, {total:,} rows in {elapsed:.0f}s")
    log(f"{'='*50}")

if __name__ == "__main__":
    main()
