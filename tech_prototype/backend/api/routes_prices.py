from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query

from ..repositories.prices_repository import PricesRepository
from ..services.timeframe_service import apply_timeframe, get_timeframe_spec
from ..api.dependencies import get_prices_repo

router = APIRouter()


@router.get("/api/prices/{symbol}")
def get_prices(
    symbol: str,
    timeframe: Optional[str] = Query(None),
    prices_repo: PricesRepository = Depends(get_prices_repo),
):
    df = prices_repo.get_prices_df(symbol)
    if df.empty:
        return []

    spec = get_timeframe_spec(timeframe or "")
    sub = apply_timeframe(df, spec) if spec else df

    return [
        {
            "date": d.strftime("%Y-%m-%d"),
            "open": float(o) if o is not None else None,
            "high": float(h) if h is not None else None,
            "low": float(l) if l is not None else None,
            "close": float(c) if c is not None else None,
            "volume": float(v) if v is not None else None,
        }
        for d, o, h, l, c, v in zip(
            sub["date"], sub["open"], sub["high"], sub["low"], sub["close"], sub["volume"]
        )
    ]
