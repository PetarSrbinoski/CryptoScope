from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    raw = os.getenv("DB_PATH", "/app/crypto.db")
    return Path(raw).resolve()


def get_conn() -> sqlite3.Connection:
    db_path = get_db_path()
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Touch the database file
    db_path.touch(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode and busy_timeout
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.commit()
    
    return conn
