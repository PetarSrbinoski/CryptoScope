from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.responses import JSONResponse

from ..db.connection import get_conn
from ..onchain_sentiment import refresh_onchain_metrics

router = APIRouter()


@router.get("/api/onchain/{symbol}")
def api_onchain(symbol: str, refresh: bool = Query(False)):
    with get_conn() as conn:
        try:
            return refresh_onchain_metrics(conn, symbol, force=refresh)
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={"symbol": symbol, "metrics": {}, "note": f"Error: {str(e)}"},
            )
