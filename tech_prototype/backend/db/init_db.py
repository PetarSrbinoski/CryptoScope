from __future__ import annotations

from ..db.connection import get_conn
from ..onchain_sentiment import init_onchain_sentiment_schema
from ..repositories.prices_write_repository import PricesWriteRepository


def init_db() -> None:
    """
    Run at startup: indexes + dependent schema init.
    Does NOT change your existing schema (only adds indexes / ensures tables).
    """
    # Ensure core tables exist before creating indexes
    repo = PricesWriteRepository(conn_factory=get_conn)
    repo.ensure_prices_table()

    with get_conn() as conn:
        # Create indexes (safe to run multiple times)
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prices_symbol_date_desc ON prices(symbol, date DESC);"
            )
        except Exception:
            # If prices table isn't present or another issue occurs, ignore here
            pass

        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_mcap ON prices(mcap DESC);")
        except Exception:
            pass

        init_onchain_sentiment_schema(conn)
        conn.commit()
