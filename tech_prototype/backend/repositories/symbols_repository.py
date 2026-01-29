from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from typing import Callable

from fastapi import HTTPException


@dataclass(frozen=True)
class SymbolsRepository:
    """
    Repository Pattern: /api/symbols SQL lives here (not in routes).
    """
    conn_factory: Callable[[], sqlite3.Connection]

    def list_symbols(
        self,
        page: int,
        page_size: int,
        q: Optional[str],
    ) -> Dict[str, Any]:
        q_clean = (q or "").strip().lower()
        filter_where = ""
        params: list[Any] = []

        if q_clean:
            filter_where = "WHERE lower(symbol) LIKE ? OR lower(name) LIKE ?"
            like = f"%{q_clean}%"
            params += [like, like]

        limit = page_size
        offset = (page - 1) * page_size

        with self.conn_factory() as conn:
            tbl = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='prices';"
            ).fetchone()
            if not tbl:
                raise HTTPException(
                    status_code=500,
                    detail="Table 'prices' not found. Run the pipeline first.",
                )

            base_cte = f"""
            WITH latest_date AS (
                SELECT symbol, MAX(date) AS max_date
                FROM prices
                GROUP BY symbol
            ),
            latest AS (
                SELECT
                    p.symbol AS symbol,
                    CASE
                        WHEN instr(p.symbol,'-')>0 THEN substr(p.symbol,1,instr(p.symbol,'-')-1)
                        ELSE p.symbol
                    END AS name,
                    p.date   AS date,
                    p.close  AS price,
                    p.volume AS vol,
                    p.mcap   AS mcap,
                    (
                        SELECT p2.close
                        FROM prices p2
                        WHERE p2.symbol = p.symbol
                          AND p2.date < p.date
                        ORDER BY p2.date DESC
                        LIMIT 1
                    ) AS prev_close
                FROM prices p
                JOIN latest_date t
                  ON p.symbol = t.symbol AND p.date = t.max_date
            ),
            filtered AS (
                SELECT
                    symbol,
                    name,
                    price,
                    CASE
                        WHEN prev_close IS NOT NULL AND prev_close != 0
                        THEN (price - prev_close) / prev_close * 100.0
                        ELSE NULL
                    END AS change,
                    vol,
                    mcap
                FROM latest
                {filter_where}
            )
            """

            total = conn.execute(
                base_cte + "SELECT COUNT(*) AS cnt FROM filtered",
                params,
            ).fetchone()["cnt"]

            rows = conn.execute(
                base_cte
                + """
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY (mcap IS NULL) ASC, mcap DESC, vol DESC, symbol ASC
                    ) AS rank,
                    symbol,
                    name,
                    price,
                    change,
                    vol,
                    mcap
                FROM filtered
                ORDER BY rank
                LIMIT ? OFFSET ?;
                """,
                params + [limit, offset],
            ).fetchall()

        items: List[Dict[str, Any]] = [
            {
                "id": int(r["rank"]),
                "rank": int(r["rank"]),
                "symbol": r["symbol"],
                "name": r["name"],
                "price": r["price"],
                "change": r["change"],
                "vol": r["vol"],
                "mcap": r["mcap"],
            }
            for r in rows
        ]

        return {"items": items, "total": total}
