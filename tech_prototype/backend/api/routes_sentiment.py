from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.responses import JSONResponse

from ..db.connection import get_conn
from ..onchain_sentiment import refresh_sentiment, get_sentiment_from_db

router = APIRouter()


@router.get("/api/sentiment/{symbol}")
def api_sentiment(
    symbol: str,
    window: str = Query("1d"),
    limit: int = Query(30, ge=1, le=100),
    refresh: bool = Query(False),
):
    with get_conn() as conn:
        try:
            return refresh_sentiment(conn, symbol, window=window, limit=limit, force=refresh)
        except Exception as e:
            cached = get_sentiment_from_db(conn, symbol, limit=limit)
            cached["error"] = str(e)
            return JSONResponse(status_code=200, content=cached)
