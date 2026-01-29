from __future__ import annotations

import pandas as pd

from ..core.config import BASE_DIR
from ..db.init_db import init_db
from ..db.connection import get_conn
from ..repositories.prices_write_repository import PricesWriteRepository

SYMBOLS_CSV = BASE_DIR / "symbols.csv"
DOWNLOAD_PLAN = BASE_DIR / "download_plan.csv"


def get_existing_status() -> pd.DataFrame:
    if not SYMBOLS_CSV.exists():
        raise FileNotFoundError(f"{SYMBOLS_CSV} not found. Run Filter 1 first.")

    init_db()

    write_repo = PricesWriteRepository(conn_factory=get_conn)
    write_repo.ensure_prices_table()

    symbols_df = pd.read_csv(SYMBOLS_CSV)
    symbols = symbols_df["symbol"].astype(str).tolist()

    plan_rows = []
    for sym in symbols:
        last_date = write_repo.get_last_date(sym)
        plan_rows.append({"symbol": sym, "last_date": last_date if last_date else pd.NA})

    plan_df = pd.DataFrame(plan_rows)
    plan_df.to_csv(DOWNLOAD_PLAN, index=False)

    print(plan_df.head())
    print(f"Filter 2 output → {DOWNLOAD_PLAN}")
    return plan_df


if __name__ == "main":
    get_existing_status()