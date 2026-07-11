"""One-time cleanup: remove stale Docker paths from data_sources.db.

Run from the backend directory:
    python clear_docker_paths.py
"""
import sqlite3
import os
import sys

# Locate data_sources.db
candidates = [
    os.path.join(os.getcwd(), "data_sources.db"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_sources.db"),
    os.path.join(os.getcwd(), "backend", "data_sources.db"),
]

db_path = None
for p in candidates:
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    print("data_sources.db not found in any expected location.")
    sys.exit(1)

print(f"Opening {db_path}")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Find entries with Docker paths (/app/) or that don't resolve
cur.execute("SELECT id, name, db_type, db_name FROM data_sources WHERE db_type = 'sqlite'")
rows = cur.fetchall()

docker_ids = []
stale_ids = []

for row in rows:
    sid, name, db_type, db_name = row
    db_name_str = db_name or ""
    # Docker paths
    if db_name_str.startswith("/app/"):
        docker_ids.append((sid, name, db_name_str))
        print(f"  DOCKER PATH: id={sid[:20]} name={name} path={db_name_str}")
    # Non-existent files
    elif not os.path.exists(db_name_str):
        stale_ids.append((sid, name, db_name_str))
        print(f"  STALE PATH: id={sid[:20]} name={name} path={db_name_str}")

if not docker_ids and not stale_ids:
    print("No stale Docker paths found.")
else:
    all_ids = [r[0] for r in docker_ids + stale_ids]
    if all_ids:
        placeholders = ",".join("?" for _ in all_ids)
        # Delete from data_sources
        cur.execute(f"DELETE FROM data_sources WHERE id IN ({placeholders})", all_ids)
        # Also delete from dataset_metadata
        cur.execute(f"DELETE FROM dataset_metadata WHERE source_id IN ({placeholders})", all_ids)
        conn.commit()
        print(f"\nDeleted {len(all_ids)} stale entries ({len(docker_ids)} Docker paths, {len(stale_ids)} non-existent)")

conn.close()
print("Done.")
