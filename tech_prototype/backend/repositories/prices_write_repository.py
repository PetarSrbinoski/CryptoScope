from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable, Optional


@dataclass(frozen=True)
class PriceInsertRow:
    symbol: str
    date: str  # ISO yyyy-mm-dd
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class PricesWriteRepository:
    """
    Separate repository for write operations so we do NOT change your existing PricesRepository.
    """
    conn_factory: Callable[[], sqlite3.Connection]

    def ensure_prices_table(self) -> None:
        """
        Creates prices table if missing + ensures mcap column exists.
        Safe to run multiple times.
        """
        conn = self.conn_factory()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS prices (
                    symbol TEXT NOT NULL,
                    date   TEXT NOT NULL,
                    open   REAL,
                    high   REAL,
                    low    REAL,
                    close  REAL,
                    volume REAL,
                    mcap   REAL,
                    PRIMARY KEY(symbol, date)
                );
                """
            )

            cols = {r["name"] for r in cur.execute("PRAGMA table_info(prices);").fetchall()}
            if "mcap" not in cols:
                cur.execute("ALTER TABLE prices ADD COLUMN mcap REAL;")

            conn.commit()
        finally:
            conn.close()

    def get_last_date(self, symbol: str) -> Optional[str]:
        conn = self.conn_factory()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) AS last_date FROM prices WHERE symbol = ?;", (symbol,))
            row = cur.fetchone()
            if not row:
                return None
            return row["last_date"]
        finally:
            conn.close()

    def insert_ohlcv_ignore_duplicates(self, rows: Iterable[PriceInsertRow]) -> int:
        payload = [(r.symbol, r.date, r.open, r.high, r.low, r.close, r.volume) for r in rows]
        if not payload:
            return 0

        conn = self.conn_factory()
        try:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO prices
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )
            conn.commit()
            # sqlite rowcount is unreliable for executemany in some cases; return len(payload) as reasonable
            return len(payload)
        finally:
            conn.close()

    def update_latest_mcap_batch(self, symbol_to_mcap: dict[str, float], batch_size: int = 500) -> int:
        """
        Updates mcap on latest row per symbol.
        Keys must be full symbols: 'BTC-USD'
        """
        if not symbol_to_mcap:
            return 0

        conn = self.conn_factory()
        try:
            cur = conn.cursor()
            total = 0
            batch: list[tuple[float, str, str]] = []

            for sym, mc in symbol_to_mcap.items():
                batch.append((float(mc), sym, sym))
                if len(batch) >= batch_size:
                    cur.executemany(
                        """
                        UPDATE prices
                        SET mcap = ?
                        WHERE symbol = ?
                          AND date = (SELECT MAX(date) FROM prices WHERE symbol = ?);
                        """,
                        batch,
                    )
                    conn.commit()
                    total += len(batch)
                    batch.clear()

            if batch:
                cur.executemany(
                    """
                    UPDATE prices
                    SET mcap = ?
                    WHERE symbol = ?
                      AND date = (SELECT MAX(date) FROM prices WHERE symbol = ?);
                    """,
                    batch,
                )
                conn.commit()
                total += len(batch)

            return total
        finally:
            conn.close()
