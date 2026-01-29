from __future__ import annotations

from fastapi import APIRouter

from ..db.connection import get_conn
from ..onchain_sentiment import compute_signal

router = APIRouter()


@router.get("/api/signal/{symbol}")
def api_signal(symbol: str):
    with get_conn() as conn:
        return compute_signal(conn, symbol)
