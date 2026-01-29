from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .lstm_analysis import run_lstm_analysis
from .db import get_conn, get_db_path

app = FastAPI(title="LSTM Forecast Microservice")


# ---------- DB initialization ----------

def init_db() -> None:
    """Initialize database schema on startup."""
    db_path = get_db_path()
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Touch the database file
    db_path.touch(exist_ok=True)
    
    with get_conn() as conn:
        # Enable WAL mode and busy_timeout
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.commit()
        
        # Ensure prices table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                mcap REAL,
                UNIQUE(symbol, date)
            )
            """
        )
        conn.commit()


@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup."""
    init_db()


@app.get("/lstm/{symbol}")
def lstm(symbol: str, lookback: int = Query(30, ge=1, le=3650)):
    try:
        return run_lstm_analysis(symbol=symbol, lookback=lookback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"ok": True}
