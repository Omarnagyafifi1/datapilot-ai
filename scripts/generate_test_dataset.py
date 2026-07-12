"""
Generate a large bilingual (Arabic/English) SQLite test database.
Usage: python scripts/generate_test_dataset.py [output_path] [scale_factor]
  output_path  : Path for the .db file (default: backend/data/test_dataset.db)
  scale_factor : Multiplier for row counts (default: 1.0, use 0.1 for quick test)
"""

import sqlite3, os, sys, random, time, json
from datetime import datetime, timedelta, date

random.seed(42)

SCALE = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "backend", "data", "test_dataset.db"
)
OUTPUT = os.path.abspath(OUTPUT)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

# ── Arabic / English word lists ─────────────────────────────────────────────
EN_FIRST = "Ahmed,Omar,Mohamed,Ali,Hassan,Karim,Layla,Noor,Fatima,Aisha,Yusuf,Amir,Khalid,Mariam,Sara,Nadia,Huda,Rami,Tariq,Leila,Samer,Dina,Hani,Mona,Samir,Nada,Bassam,Rana,Adnan,Salma,Jamal,Najat,Rashid,Amal,Hussein,Lina".split(",")
AR_FIRST = "أحمد,عمر,محمد,علي,حسن,كريم,ليلى,نور,فاطمة,عائشة,يوسف,أمير,خالد,مريم,سارة,نادية,هدى,رامي,طارق,ليلى,سامر,دينا,هاني,منى,سمير,ندى,بسام,رنا,عدنان,سلمى,جمال,نجاة,راشد,أمل,حسين,لينا".split(",")

EN_LAST = "Hassan,Mohamed,Ali,Youssef,Khalil,Ibrahim,Ahmed,Omar,Farah,Nader,Shahin,Mansour,Haddad,Najjar,Saleh,Abboud,Rashid,Tannous".split(",")
AR_LAST = "حسن,محمد,علي,يوسف,خليل,إبراهيم,أحمد,عمر,فرح,نادر,شاهين,منصور,حداد,نجار,صالح,عبود,راشد,طنوس".split(",")

EN_CITIES = "Cairo,Dubai,Riyadh,Doha,Muscat,Kuwait City,Manama,Amman,Beirut,Tunis,Algiers,Rabat,Khartoum,Baghdad,Alexandria,Jeddah,Sharjah,Abu Dhabi".split(",")
AR_CITIES = "القاهرة,دبي,الرياض,الدوحة,مسقط,مدينة الكويت,المنامة,عمان,بيروت,تونس,الجزائر,الرباط,الخرطوم,بغداد,الإسكندرية,جدة,الشارقة,أبو ظبي".split(",")

EN_COUNTRIES = "Egypt,UAE,Saudi Arabia,Qatar,Oman,Kuwait,Bahrain,Jordan,Lebanon,Tunisia,Algeria,Morocco".split(",")
AR_COUNTRIES = "مصر,الإمارات,المملكة العربية السعودية,قطر,عمان,الكويت,البحرين,الأردن,لبنان,تونس,الجزائر,المغرب".split(",")

EN_COMP_NAMES = "TechNile,DesertCloud,ArabianData,GulfAI,GreenOasis,SilverWinds,GoldenSands,BlueWave,RedSeaTech,PalmDigital".split(",")
AR_COMP_NAMES = "نايل تك,سحابة الصحراء,البيانات العربية,خليج AI,الواحة الخضراء,الرياح الفضية,الرمال الذهبية,الموجة الزرقاء,تقنية البحر الأحمر,نخلة ديجيتال".split(",")

EN_INDUSTRIES = "Technology,Finance,Healthcare,Education,Retail,Manufacturing,Oil & Gas,Real Estate,Logistics,Agriculture,Telecom,Tourism".split(",")
AR_INDUSTRIES = "تكنولوجيا,مال,رعاية صحية,تعليم,تجزئة,تصنيع,نفط وغاز,عقارات,لوجستيات,زراعة,اتصالات,سياحة".split(",")

EN_DEPT_NAMES = "Engineering,Marketing,Sales,Human Resources,Finance,Operations,Research & Development,Legal,IT Support,Customer Service,Procurement,Quality Assurance".split(",")
AR_DEPT_NAMES = "الهندسة,التسويق,المبيعات,الموارد البشرية,المالية,العمليات,البحث والتطوير,الشؤون القانونية,دعم تقني,خدمة العملاء,المشتريات,ضمان الجودة".split(",")

EN_PROD_CATS = "Electronics,Clothing,Food & Beverages,Furniture,Books,Sports Equipment,Beauty,Automotive,Pharmaceuticals,Office Supplies,Baby Products,Pet Supplies,Jewelry,Home Appliances,Garden".split(",")
AR_PROD_CATS = "إلكترونيات,ملابس,أغذية ومشروبات,أثاث,كتب,معدات رياضية,تجميل,سيارات,أدوية,لوازم مكتبية,منتجات أطفال,لوازم حيوانات أليفة,مجوهرات,أجهزة منزلية,حديقة".split(",")

EN_PROD = "Smartphone,Laptop,Wireless Headphones,Desk Chair,Organic Coffee,Notebook,LED Monitor,Yoga Mat,Sunscreen,Car Battery,Multivitamin,Printer Paper,Baby Stroller,Water Bottle,Cat Food".split(",")
AR_PROD = "هاتف ذكي,حاسوب محمول,سماعات لاسلكية,كرسي مكتب,قهوة عضوية,دفتر ملاحظات,شاشة LED,سجادة يوغا,واقي شمس,بطارية سيارة,فيتامينات متعددة,ورق طابعة,عربة أطفال,زجاجة ماء,طعام قطط".split(",")

EN_SUPPLIER = "GlobalTech Supply,MidEast Logistics,Desert Trade Co,Blue Horizon Imports,Palm Distribution,Gold Crescent Trading,Oasis Wholesale,Sahara Export,Delta Manufacturing,Falcon Trading".split(",")
AR_SUPPLIER = "التوريدات التقنية العالمية,لوجستيات الشرق الأوسط,شركة تجارة الصحراء,واردات الأفق الأزرق,توزيع النخلة,تجارة الهلال الذهبي,جملة الواحة,صادرات الصحراء,تصنيع الدلتا,تجارة الصقر".split(",")

EN_WAREHOUSE = "Main Warehouse,East Distribution Center,West Storage Facility,North Hub,South Depot,Cool Storage,Auto Parts Warehouse,Electronics Vault,Furniture Hall".split(",")
AR_WAREHOUSE = "المستودع الرئيسي,مركز التوزيع الشرقي,منشأة التخزين الغربية,المركز الشمالي,مستودع الجنوب,التخزين المبرد,مستودع قطع السيارات,قبو الإلكترونيات,قاعة الأثاث".split(",")

EN_CARRIER = "Aramex,DHL FedEx,UPS,Naqel Express,SMSA Express,National Shipping,Zajil".split(",")
AR_CARRIER = "أرامكس,دي إتش إل فيديكس,يو بي إس,ناقل إكسبرس,إس إم إس إيه إكسبرس,الشحن الوطني,زاجل".split(",")

EN_ORDER_STATUS = "Pending,Processing,Shipped,Delivered,Cancelled,Refunded".split(",")
AR_ORDER_STATUS = "قيد الانتظار,قيد المعالجة,تم الشحن,تم التوصيل,ملغي,تم الاسترجاع".split(",")

EN_PAYMENT = "Credit Card,Debit Card,Bank Transfer,COD,PayPal,Apple Pay,Google Pay,Stc Pay".split(",")
AR_PAYMENT = "بطاقة ائتمان,بطاقة مدين,تحويل بنكي,الدفع عند الاستلام,باي بال,أبل باي,جوجل باي,إس تي سي باي".split(",")

EN_REVIEW_TITLES = "Great product!,Very good,Excellent quality,Good value,Average product,Not bad,Disappointed,Poor quality,Perfect!,Highly recommended,Would buy again,Not what I expected".split(",")
AR_REVIEW_TITLES = "منتج رائع!,جيد جداً,جودة ممتازة,قيمة جيدة,منتج متوسط,ليس سيئاً,خائب الأمل,جودة سيئة,ممتاز!,موصى به بشدة,سأشتري مجدداً,ليس كما توقعت".split(",")

EN_REVIEW = "I really liked this product. It exceeded my expectations and I would recommend it to anyone. The quality is outstanding and the price is reasonable.", "This product works well for its price point. It gets the job done without any fuss. Good quality materials and solid construction.", "Average quality, nothing special. It does what it's supposed to do but there's room for improvement in terms of durability.", "I was disappointed with this purchase. The product didn't match the description and the quality was below what I expected.", "Excellent product! Arrived on time and in perfect condition. Very happy with my purchase.", "Good product overall. Some minor issues but nothing major. Would consider buying again."
AR_REVIEW = "أعجبني هذا المنتج كثيراً. تجاوز توقعاتي وأنصح به لأي شخص. الجودة ممتازة والسعر معقول.", "هذا المنتج يعمل بشكل جيد مقابل سعره. يؤدي الغرض المطلوب دون أي متاعب. مواد جيدة وبناء متين.", "جودة متوسطة، لا شيء مميز. يقوم بالوظيفة المطلوبة ولكن هناك مجال للتحسين من حيث المتانة.", "كنت محبطاً من هذا الشراء. المنتج لم يطابق الوصف والجودة كانت أدنى مما توقعت.", "منتج ممتاز! وصل في الوقت المحدد وبحالة ممتازة. سعيد جداً بمشترياتي.", "منتج جيد بشكل عام. بعض المشاكل البسيطة لكن لا شيء كبير. سأفكر في الشراء مرة أخرى."

EN_ACTIONS = "CREATE,UPDATE,DELETE,LOGIN,LOGOUT,EXPORT,IMPORT,BACKUP,RESTORE,APPROVE,REJECT,ARCHIVE".split(",")
AR_ACTIONS = "إنشاء,تحديث,حذف,دخول,خروج,تصدير,استيراد,نسخ احتياطي,استعادة,موافقة,رفض,أرشفة".split(",")

TX_TYPES_EN = "Sale,Refund,Partial Refund,Chargeback,Fee,Commission".split(",")
TX_TYPES_AR = "بيع,استرجاع,استرجاع جزئي,رد مبلغ,رسوم,عمولة".split(",")

# ── helpers ──────────────────────────────────────────────────────────────────
def rbool(p=0.5):
    return random.random() < p

def pick(lst):
    return random.choice(lst)

def rdate(start="2020-01-01", end="2026-07-12"):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    return (s + timedelta(seconds=random.randint(0, int((e - s).total_seconds())))).strftime("%Y-%m-%d %H:%M:%S")

def rdate_only(start="2020-01-01", end="2026-07-12"):
    return rdate(start, end)[:10]

def run_sql(db, sql):
    db.execute(sql)

def batch_insert(db, table, cols, rows_gen, batch_size=50000):
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    batch = []
    count = 0
    t0 = time.time()
    for row in rows_gen:
        batch.append(row)
        if len(batch) >= batch_size:
            db.executemany(sql, batch)
            count += len(batch)
            batch = []
            print(f"\r  {table}: {count:,} rows ({time.time()-t0:.1f}s)", end="")
    if batch:
        db.executemany(sql, batch)
        count += len(batch)
    print(f"\r  {table}: {count:,} rows ({time.time()-t0:.1f}s) DONE")
    return count

# ── schema ───────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=OFF;
PRAGMA cache_size=-4000000;
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT,
    industry_en TEXT, industry_ar TEXT,
    founded_date TEXT, revenue REAL, employee_count INTEGER,
    country_en TEXT, country_ar TEXT
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id),
    name_en TEXT, name_ar TEXT,
    city_en TEXT, city_ar TEXT, address TEXT, phone TEXT,
    manager_id INTEGER
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT,
    description_en TEXT, description_ar TEXT,
    budget REAL, company_id INTEGER REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    first_name_en TEXT, first_name_ar TEXT,
    last_name_en TEXT, last_name_ar TEXT,
    email TEXT, phone TEXT, hire_date TEXT,
    salary REAL, department_id INTEGER REFERENCES departments(id),
    branch_id INTEGER REFERENCES branches(id),
    manager_id INTEGER, is_active INTEGER
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    first_name_en TEXT, first_name_ar TEXT,
    last_name_en TEXT, last_name_ar TEXT,
    email TEXT, phone TEXT,
    city_en TEXT, city_ar TEXT,
    country_en TEXT, country_ar TEXT,
    registration_date TEXT, total_purchases REAL, is_vip INTEGER
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT,
    description_en TEXT, description_ar TEXT, parent_id INTEGER
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT,
    description_en TEXT, description_ar TEXT,
    category_id INTEGER REFERENCES categories(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    unit_price REAL, stock_quantity INTEGER,
    reorder_level INTEGER, is_active INTEGER, created_date TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT,
    contact_name_en TEXT, contact_name_ar TEXT,
    email TEXT, phone TEXT,
    city_en TEXT, city_ar TEXT,
    country_en TEXT, country_ar TEXT, rating INTEGER
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TEXT, total_amount REAL,
    status_en TEXT, status_ar TEXT,
    payment_method_en TEXT, payment_method_ar TEXT,
    shipping_address TEXT, notes TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER, unit_price REAL, discount REAL, total_price REAL
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    warehouse_en TEXT, warehouse_ar TEXT,
    quantity INTEGER, last_restock_date TEXT,
    min_quantity INTEGER, max_quantity INTEGER
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    transaction_date TEXT, amount REAL,
    type_en TEXT, type_ar TEXT,
    status_en TEXT, status_ar TEXT, reference_number TEXT
);

CREATE TABLE IF NOT EXISTS shipping (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    carrier_en TEXT, carrier_ar TEXT,
    tracking_number TEXT,
    shipped_date TEXT, delivered_date TEXT,
    status_en TEXT, status_ar TEXT,
    weight REAL, shipping_cost REAL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    customer_id INTEGER REFERENCES customers(id),
    rating INTEGER,
    title_en TEXT, title_ar TEXT,
    review_text_en TEXT, review_text_ar TEXT,
    review_date TEXT, is_verified INTEGER
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    table_name TEXT, record_id INTEGER,
    action_en TEXT, action_ar TEXT,
    changed_by TEXT, changed_at TEXT,
    old_values TEXT, new_values TEXT
);

CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_branch ON employees(branch_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_transactions_order ON transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_shipping_order ON shipping(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_customer ON reviews(customer_id);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_branches_company ON branches(company_id);
CREATE INDEX IF NOT EXISTS idx_departments_company ON departments(company_id);
"""

# ── data generators ─────────────────────────────────────────────────────────
def gen_companies(n=200):
    for i in range(1, n + 1):
        idx = i % len(EN_COMP_NAMES)
        yield (i, f"{EN_COMP_NAMES[idx]} #{i}", f"{AR_COMP_NAMES[idx]} #{i}",
               pick(EN_INDUSTRIES), pick(AR_INDUSTRIES),
               rdate_only("1990-01-01", "2020-01-01"),
               round(random.uniform(1e6, 5e9), 2), random.randint(50, 50000),
               pick(EN_COUNTRIES), pick(AR_COUNTRIES))

def gen_branches(n=1000):
    for i in range(1, n + 1):
        cid = random.randint(1, 200)
        yield (i, cid, f"Branch {i}", f"فرع {i}",
               pick(EN_CITIES), pick(AR_CITIES),
               f"{random.randint(1,999)} {pick(['Main St','Oak Ave','First St','Park Rd','Elm St','King Fahd Rd','Al Khaleej St','Corniche Rd'])}",
               f"+971{random.randint(50,58)}{random.randint(1000000,9999999)}", None)

def gen_dept_desc():
    return "Responsible for planning and execution of all related activities across the organization.", "مسؤولة عن التخطيط والتنفيذ لجميع الأنشطة ذات الصلة في جميع أنحاء المنظمة."

def gen_departments(n=800):
    for i in range(1, n + 1):
        idx = i % len(EN_DEPT_NAMES)
        desc_en, desc_ar = gen_dept_desc()
        yield (i, f"{EN_DEPT_NAMES[idx]} {i}", f"{AR_DEPT_NAMES[idx]} {i}",
               desc_en, desc_ar,
               round(random.uniform(50000, 5e6), 2), random.randint(1, 200))

def gen_employees(n=100000):
    scale = n / 100000
    email_domains = "@company.com,@datapilot.ai,@testcorp.me,@biz.org".split(",")
    for i in range(1, n + 1):
        fn_en = pick(EN_FIRST)
        fn_ar = pick(AR_FIRST)
        ln_en = pick(EN_LAST)
        ln_ar = pick(AR_LAST)
        email = f"{fn_en.lower()}.{ln_en.lower()}{i}@example.com"
        phone = f"+971{random.randint(50,58)}{random.randint(1000000,9999999)}"
        yield (i, fn_en, fn_ar, ln_en, ln_ar, email, phone,
               rdate_only("2015-01-01", "2026-06-01"),
               round(random.uniform(3000, 50000), 2),
               random.randint(1, 800), random.randint(1, 1000),
               None if i < 50 else random.randint(1, n - 1),
               1 if rbool(0.95) else 0)

def gen_customers(n=200000):
    for i in range(1, n + 1):
        fn_en = pick(EN_FIRST)
        fn_ar = pick(AR_FIRST)
        ln_en = pick(EN_LAST)
        ln_ar = pick(AR_LAST)
        email = f"{fn_en.lower()}.{ln_en.lower()}{i}@mail.com"
        phone = f"+971{random.randint(50,58)}{random.randint(1000000,9999999)}"
        yield (i, fn_en, fn_ar, ln_en, ln_ar, email, phone,
               pick(EN_CITIES), pick(AR_CITIES),
               pick(EN_COUNTRIES), pick(AR_COUNTRIES),
               rdate_only("2018-01-01", "2026-06-01"),
               round(random.uniform(0, 50000), 2), 1 if rbool(0.08) else 0)

def gen_categories(n=300):
    def sub_cats(parent, count, prefix_en, prefix_ar):
        for j in range(1, count + 1):
            yield (parent * 100 + j, f"{prefix_en} Sub {j}", f"{prefix_ar} فرعي {j}",
                   f"Subcategory of {prefix_en}", f"فرعي من {prefix_ar}", parent)
    i = 1
    for idx in range(len(EN_PROD_CATS)):
        yield (i, EN_PROD_CATS[idx], AR_PROD_CATS[idx], f"Main category: {EN_PROD_CATS[idx]}", f"فئة رئيسية: {AR_PROD_CATS[idx]}", None)
        i += 1
        for sub in sub_cats(i - 1, random.randint(3, 8), EN_PROD_CATS[idx], AR_PROD_CATS[idx]):
            if i >= n: break
            yield sub
            i += 1
        if i >= n: break

def gen_suppliers(n=5000):
    for i in range(1, n + 1):
        idx = i % len(EN_SUPPLIER)
        yield (i, f"{EN_SUPPLIER[idx]} #{i}", f"{AR_SUPPLIER[idx]} #{i}",
               pick(EN_FIRST) + " " + pick(EN_LAST), pick(AR_FIRST) + " " + pick(AR_LAST),
               f"contact{i}@supplier.com", f"+971{random.randint(50,58)}{random.randint(1000000,9999999)}",
               pick(EN_CITIES), pick(AR_CITIES), pick(EN_COUNTRIES), pick(AR_COUNTRIES),
               random.randint(1, 5))

def gen_products(n=50000, supplier_count=5000):
    for i in range(1, n + 1):
        idx = (i - 1) % len(EN_PROD)
        price = round(random.uniform(5, 5000), 2)
        yield (i, f"{EN_PROD[idx]} Model {i}", f"{AR_PROD[idx]} موديل {i}",
               f"High-quality {EN_PROD[idx].lower()} with latest features and durable construction.",
               f"{AR_PROD[idx]} عالي الجودة بأحدث الميزات والبناء المتين.",
               random.randint(1, 300), random.randint(1, supplier_count),
               price, random.randint(0, 5000),
               random.randint(5, 50), 1 if rbool(0.92) else 0,
               rdate_only("2019-01-01", "2026-01-01"))

def gen_orders(customer_ids, n=500000):
    statuses = list(zip(EN_ORDER_STATUS, AR_ORDER_STATUS))
    payments = list(zip(EN_PAYMENT, AR_PAYMENT))
    for i in range(1, n + 1):
        cid = random.choice(customer_ids)
        s_en, s_ar = pick(statuses)
        p_en, p_ar = pick(payments)
        yield (i, cid, rdate("2021-01-01", "2026-07-12"), 0.0,
               s_en, s_ar, p_en, p_ar,
               f"{random.randint(1,999)} {pick(['Main St','Corniche','King Fahd Rd','Al Nahda St','Sheikh Zayed Rd'])}",
               pick(["", "", "", "Urgent delivery requested", "Gift wrap please", "Leave at reception"]))

def gen_order_items(order_ids, product_prices, n=2000000):
    for i in range(1, n + 1):
        oid = random.choice(order_ids)
        pid = random.randint(1, len(product_prices))
        qty = random.randint(1, 10)
        up = product_prices[pid - 1]
        disc = round(random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2]), 2)
        total = round(qty * up * (1 - disc), 2)
        yield (i, oid, pid, qty, up, disc, total)

def gen_inventory(product_ids, n=50000):
    for i in range(1, n + 1):
        widx = (i - 1) % len(EN_WAREHOUSE)
        qty = random.randint(0, 5000)
        yield (i, product_ids[i - 1],
               EN_WAREHOUSE[widx], AR_WAREHOUSE[widx],
               qty, rdate_only("2023-01-01", "2026-07-01"),
               random.randint(10, 200), random.randint(500, 5000))

def gen_transactions(order_ids, n=500000):
    statuses = list(zip(EN_ORDER_STATUS, AR_ORDER_STATUS))
    types = list(zip(TX_TYPES_EN, TX_TYPES_AR))
    for i in range(1, n + 1):
        oid = random.choice(order_ids)
        t_en, t_ar = pick(types)
        s_en, s_ar = pick(statuses)
        yield (i, oid, rdate("2021-01-01", "2026-07-12"),
               round(random.uniform(10, 50000), 2),
               t_en, t_ar, s_en, s_ar,
               f"TXN{random.randint(1000000,9999999)}")

def gen_shipping(order_ids, n=400000):
    carriers = list(zip(EN_CARRIER, AR_CARRIER))
    statuses = list(zip(EN_ORDER_STATUS, AR_ORDER_STATUS))
    used = set()
    for i in range(1, n + 1):
        oid = random.choice(order_ids)
        while oid in used:
            oid = random.choice(order_ids)
        used.add(oid)
        c_en, c_ar = pick(carriers)
        s_en, s_ar = pick(statuses)
        shipped = rdate("2021-01-02", "2026-07-12")
        delivered = rdate(shipped[:10], "2026-07-12") if rbool(0.85) else None
        yield (i, oid, c_en, c_ar, f"TRK{random.randint(1000000,9999999)}",
               shipped, delivered, s_en, s_ar,
               round(random.uniform(0.5, 50), 2), round(random.uniform(5, 500), 2))

def gen_reviews(product_ids, customer_ids, n=200000):
    for i in range(1, n + 1):
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        r_idx = rating - 1 if rating <= 2 else random.randint(0, 5)
        yield (i, random.choice(product_ids), random.choice(customer_ids),
               rating,
               pick(EN_REVIEW_TITLES), pick(AR_REVIEW_TITLES),
               EN_REVIEW[r_idx % len(EN_REVIEW)], AR_REVIEW[r_idx % len(AR_REVIEW)],
               rdate("2021-01-01", "2026-07-12"), 1 if rbool(0.7) else 0)

def gen_audit_log(n=100000):
    tables = ["employees", "orders", "products", "customers", "inventory"]
    for i in range(1, n + 1):
        tbl = pick(tables)
        yield (i, tbl, random.randint(1, 100000),
               pick(EN_ACTIONS), pick(AR_ACTIONS),
               pick(EN_FIRST) + " " + pick(EN_LAST),
               rdate("2024-01-01", "2026-07-12"),
               json.dumps({"field": pick(["status","price","quantity","name"])}), "{}")

# ── main ─────────────────────────────────────────────────────────────────────
def main():
    t_start = time.time()
    print(f"Generating test dataset at: {OUTPUT}")
    print(f"Scale factor: {SCALE}")
    print(f"Target size: ~{int(4.5 * SCALE)}M rows\n")

    if os.path.exists(OUTPUT):
        print(f"Removing existing database...")
        os.remove(OUTPUT)

    db = sqlite3.connect(OUTPUT, check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("PRAGMA cache_size=-8000000")
    db.execute("PRAGMA temp_store=MEMORY")

    print("Creating schema...")
    db.executescript(SCHEMA_SQL)
    db.commit()

    counts = {}
    row_targets = {
        "companies": int(200 * SCALE), "branches": int(1000 * SCALE),
        "departments": int(800 * SCALE), "employees": int(100000 * SCALE),
        "customers": int(200000 * SCALE), "categories": int(300 * SCALE),
        "suppliers": int(5000 * SCALE), "products": int(50000 * SCALE),
        "orders": int(500000 * SCALE), "order_items": int(2000000 * SCALE),
        "inventory": int(50000 * SCALE), "transactions": int(500000 * SCALE),
        "shipping": int(400000 * SCALE), "reviews": int(200000 * SCALE),
        "audit_log": int(100000 * SCALE),
    }

    print("\nGenerating companies...")
    counts["companies"] = batch_insert(db, "companies",
        ["id","name_en","name_ar","industry_en","industry_ar","founded_date","revenue","employee_count","country_en","country_ar"],
        gen_companies(row_targets["companies"]))
    db.commit()

    print("Generating branches...")
    counts["branches"] = batch_insert(db, "branches",
        ["id","company_id","name_en","name_ar","city_en","city_ar","address","phone","manager_id"],
        gen_branches(row_targets["branches"]))
    db.commit()

    print("Generating departments...")
    counts["departments"] = batch_insert(db, "departments",
        ["id","name_en","name_ar","description_en","description_ar","budget","company_id"],
        gen_departments(row_targets["departments"]))
    db.commit()

    print("Generating employees...")
    counts["employees"] = batch_insert(db, "employees",
        ["id","first_name_en","first_name_ar","last_name_en","last_name_ar","email","phone","hire_date","salary","department_id","branch_id","manager_id","is_active"],
        gen_employees(row_targets["employees"]))
    db.commit()

    print("Generating customers...")
    counts["customers"] = batch_insert(db, "customers",
        ["id","first_name_en","first_name_ar","last_name_en","last_name_ar","email","phone","city_en","city_ar","country_en","country_ar","registration_date","total_purchases","is_vip"],
        gen_customers(row_targets["customers"]))
    db.commit()

    print("Generating categories...")
    counts["categories"] = batch_insert(db, "categories",
        ["id","name_en","name_ar","description_en","description_ar","parent_id"],
        gen_categories(row_targets["categories"]))
    db.commit()

    print("Generating suppliers...")
    counts["suppliers"] = batch_insert(db, "suppliers",
        ["id","name_en","name_ar","contact_name_en","contact_name_ar","email","phone","city_en","city_ar","country_en","country_ar","rating"],
        gen_suppliers(row_targets["suppliers"]))
    db.commit()

    print("Generating products...")
    counts["products"] = batch_insert(db, "products",
        ["id","name_en","name_ar","description_en","description_ar","category_id","supplier_id","unit_price","stock_quantity","reorder_level","is_active","created_date"],
        gen_products(row_targets["products"], row_targets["suppliers"]))
    db.commit()

    # Collect data needed for referential inserts
    print("\nCollecting ID mappings...")
    c = db.execute("SELECT id FROM customers")
    customer_ids = [r[0] for r in c.fetchall()]
    c = db.execute("SELECT id, unit_price FROM products ORDER BY id")
    product_rows = c.fetchall()
    product_ids = [r[0] for r in product_rows]
    product_prices = [r[1] for r in product_rows]
    c = db.execute("SELECT id FROM orders")
    order_ids = [r[0] for r in c.fetchall()]

    print("Note: orders, order_items, transactions, shipping generated in sequence (no pre-existing order_ids)")

    print("Generating orders...")
    counts["orders"] = batch_insert(db, "orders",
        ["id","customer_id","order_date","total_amount","status_en","status_ar","payment_method_en","payment_method_ar","shipping_address","notes"],
        gen_orders(customer_ids, row_targets["orders"]))
    db.commit()

    c = db.execute("SELECT id FROM orders")
    order_ids = [r[0] for r in c.fetchall()]

    print("Generating order items...")
    counts["order_items"] = batch_insert(db, "order_items",
        ["id","order_id","product_id","quantity","unit_price","discount","total_price"],
        gen_order_items(order_ids, product_prices, row_targets["order_items"]))
    db.commit()

    # Update order totals
    print("Updating order totals...")
    db.execute("""
        UPDATE orders SET total_amount = (
            SELECT COALESCE(SUM(total_price), 0) FROM order_items WHERE order_id = orders.id
        )
    """)
    db.commit()

    print("Generating inventory...")
    counts["inventory"] = batch_insert(db, "inventory",
        ["id","product_id","warehouse_en","warehouse_ar","quantity","last_restock_date","min_quantity","max_quantity"],
        gen_inventory(product_ids, row_targets["inventory"]))
    db.commit()

    print("Generating transactions...")
    counts["transactions"] = batch_insert(db, "transactions",
        ["id","order_id","transaction_date","amount","type_en","type_ar","status_en","status_ar","reference_number"],
        gen_transactions(order_ids, row_targets["transactions"]))
    db.commit()

    print("Generating shipping...")
    counts["shipping"] = batch_insert(db, "shipping",
        ["id","order_id","carrier_en","carrier_ar","tracking_number","shipped_date","delivered_date","status_en","status_ar","weight","shipping_cost"],
        gen_shipping(order_ids, row_targets["shipping"]))
    db.commit()

    print("Generating reviews...")
    counts["reviews"] = batch_insert(db, "reviews",
        ["id","product_id","customer_id","rating","title_en","title_ar","review_text_en","review_text_ar","review_date","is_verified"],
        gen_reviews(product_ids, customer_ids, row_targets["reviews"]))
    db.commit()

    print("Generating audit log...")
    counts["audit_log"] = batch_insert(db, "audit_log",
        ["id","table_name","record_id","action_en","action_ar","changed_by","changed_at","old_values","new_values"],
        gen_audit_log(row_targets["audit_log"]))
    db.commit()

    # Vacuum + analyze
    print("\nOptimizing database...")
    db.execute("PRAGMA analysis_limit=10000")
    db.execute("ANALYZE")
    db.execute("VACUUM")
    db.commit()

    db.close()

    elapsed = time.time() - t_start
    total_rows = sum(counts.values())
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    
    print(f"\n{'='*60}")
    print(f"DATASET GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {OUTPUT}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Total rows: {total_rows:,}")
    print(f"Time: {elapsed:.1f}s ({total_rows/elapsed:.0f} rows/s)")
    print(f"\nTable breakdown:")
    for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {name:16s} {cnt:>10,} rows")
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
