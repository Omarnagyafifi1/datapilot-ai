import sqlite3, os
d = "/app/backend/data"
os.makedirs(d, exist_ok=True)
f = os.path.join(d, "test_sqlite.db")
db = sqlite3.connect(f)
db.execute("CREATE TABLE t(x)")
db.execute("INSERT INTO t VALUES(1)")
print(db.execute("SELECT * FROM t").fetchall())
db.close()
os.remove(f)
print("SQLite OK on local storage")
