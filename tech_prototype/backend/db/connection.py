from __future__ import annotations

import sqlite3
from pathlib import Path
import os

from ..core.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    """
    Single place to configure sqlite connection behavior.

    Ensures parent directories exist and creates the file if necessary so
    containers (e.g. Azure App Service) can open/create the sqlite DB.
    """
    db_path = Path(DB_PATH)
    parent = db_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # best-effort; continue and let sqlite raise a clear error if it fails
        pass

    # Ensure the file exists (touch) so sqlite can open it even if the process
    # user has restrictive umask; this is a best-effort non-failing step.
    try:
        if not db_path.exists():
            # create an empty file with permissive mode
            fd = os.open(str(db_path), os.O_CREAT | os.O_RDWR, 0o666)
            os.close(fd)
    except Exception:
        # ignore; sqlite.connect will raise a helpful error if needed
        pass

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row

    # Improve concurrent write behavior for multi-threaded pipeline:
    # - enable WAL mode which allows readers without blocking writers
    # - set a busy timeout so writes wait briefly when DB is locked
    try:
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        try:
            cur.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        cur.close()
    except Exception:
        # non-fatal; continue with the connection
        pass

    return conn
    
