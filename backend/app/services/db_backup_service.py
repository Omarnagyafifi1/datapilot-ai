import os
import shutil
import sqlite3
from app.core.logger import get_logger

logger = get_logger(__name__)

BACKUP_DIR = os.getenv("BACKUP_DIR", "/mnt/uploads/db_backups")
LOCAL_DB_DIR = os.getenv("LOCAL_DB_DIR", "")


def _get_local_db_dir() -> str:
    if LOCAL_DB_DIR:
        return LOCAL_DB_DIR
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "uploads")


def backup_path(source_id: str) -> str:
    return os.path.join(BACKUP_DIR, f"{source_id}.db")


def local_path(source_id: str) -> str:
    return os.path.join(_get_local_db_dir(), f"{source_id}.db")


def backup_db(source_id: str) -> str | None:
    src = local_path(source_id)
    if not os.path.exists(src):
        logger.warning("Cannot backup %s: local file not found at %s", source_id, src)
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dst = backup_path(source_id)
    try:
        shutil.copy2(src, dst)
        logger.info("Backed up %s -> %s", src, dst)
        return dst
    except Exception:
        logger.exception("Failed to backup %s to %s", src, dst)
        return None


def _set_pragmas(db_path: str) -> None:
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Failed to set pragmas on %s (non-fatal)", db_path)


def restore_backup(source_id: str) -> str | None:
    dst = local_path(source_id)
    src = backup_path(source_id)
    if not os.path.exists(src):
        logger.warning("Cannot restore %s: backup not found at %s", source_id, src)
        return None
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copy2(src, dst)
        _set_pragmas(dst)
        logger.info("Restored %s -> %s", src, dst)
        return dst
    except Exception:
        logger.exception("Failed to restore %s from %s", source_id, src)
        return None


def restore_all() -> int:
    count = 0
    if not os.path.isdir(BACKUP_DIR):
        logger.info("Backup directory %s does not exist, nothing to restore", BACKUP_DIR)
        return 0
    for entry in os.listdir(BACKUP_DIR):
        if not entry.endswith(".db"):
            continue
        source_id = entry[:-3]
        dst = local_path(source_id)
        if os.path.exists(dst):
            continue
        if restore_backup(source_id):
            count += 1
    if count:
        logger.info("Restored %d SQLite databases from backup", count)
    else:
        logger.info("No SQLite databases needed restoration")
    return count


def backup_exists(source_id: str) -> bool:
    return os.path.exists(backup_path(source_id))
