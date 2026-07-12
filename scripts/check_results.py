import sqlite3, os, glob, sys

d = "/app/backend/data"
out = "/mnt/uploads/check_output.txt"

with open(out, "w") as f:
    dbs = sorted(glob.glob(os.path.join(d, "test_dataset_*.db")))
    logs = sorted(glob.glob(os.path.join(d, "test_dataset_*.db.log")))
    f.write(f"Found {len(dbs)} DBs, {len(logs)} logs\n")

    if logs:
        f.write(f"\n--- Latest log: {os.path.basename(logs[-1])} ---\n")
        with open(logs[-1]) as lf:
            f.write(lf.read())

    if dbs:
        db = dbs[-1]
        sz = os.path.getsize(db)
        f.write(f"\n--- Latest DB: {os.path.basename(db)} ({sz/1024/1024:.0f} MB) ---\n")
        try:
            conn = sqlite3.connect(db)
            for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                cnt = conn.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
                f.write(f"  {t[0]:20s} {cnt:>8,}\n")
            conn.close()
        except Exception as e:
            f.write(f"  ERROR: {e}\n")

print(f"Written to {out}", flush=True)
