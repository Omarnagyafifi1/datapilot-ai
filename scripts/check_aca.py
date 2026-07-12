import sqlite3, os, shutil, glob

d = "/app/backend/data"
logs = glob.glob(os.path.join(d, "test_dataset_*.db.log"))
dbs = glob.glob(os.path.join(d, "test_dataset_*.db"))
logs.sort(); dbs.sort()

print(f"Found {len(dbs)} DB files, {len(logs)} log files")

if logs:
    print(f"\nLatest log ({logs[-1]}):")
    with open(logs[-1]) as f:
        print(f.read()[-2000:])

if dbs:
    db_path = dbs[-1]
    sz = os.path.getsize(db_path)
    print(f"\nLatest DB: {db_path} ({sz//1024//1024} MB)")
    try:
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for t in tables:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
            print(f"  {t[0]:15s} {cnt:>8,} rows")
        conn.close()
        # Copy to Azure Files for persistence
        dest = f"/mnt/uploads/{os.path.basename(db_path)}"
        shutil.copy2(db_path, dest)
        print(f"\nCopied to Azure Files: {dest}")
    except Exception as e:
        print(f"Error: {e}")
