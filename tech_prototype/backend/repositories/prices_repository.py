from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class PricesRepository:
    conn_factory: Callable[[], sqlite3.Connection]

    def get_prices_df(self, symbol: str) -> pd.DataFrame:
        conn = self.conn_factory()
        try:
            df = pd.read_sql_query(
                """
                SELECT date, open, high, low, close, volume
                FROM prices
                WHERE symbol = ?
                ORDER BY date
                """,
                conn,
                params=(symbol,),
            )
        finally:
            conn.close()

        if df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
