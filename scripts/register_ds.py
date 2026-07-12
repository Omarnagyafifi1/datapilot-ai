import sqlite3, os, uuid
from datetime import datetime

# Register the dataset in the app's data_sources.db
db_path = "/app/backend/data_sources.db"
if not os.path.exists(db_path):
    print(f"data_sources.db not found at {db_path}")
    print("Files in /app/backend:", os.listdir("/app/backend"))
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check existing sources
cur.execute("SELECT id, name FROM data_sources")
print("Existing sources:", cur.fetchall())

# Register new source
sid = uuid.uuid4().hex
db_file = "/mnt/uploads/test_dataset_100k.db"
now = datetime.now().isoformat()

cur.execute(
    "INSERT INTO data_sources (id, name, db_type, host, port, db_name, username, enc_password, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
    (sid, "Test Dataset 100K", "sqlite", "", 0, db_file, "", "", now)
)
conn.commit()
print(f"Registered: id={sid}, name=Test Dataset 100K, path={db_file}")

# Verify
cur.execute("SELECT id, name, db_name FROM data_sources WHERE id=?", (sid,))
print("Verified:", cur.fetchone())
conn.close()
print("DONE")
