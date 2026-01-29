from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException, Query

from ..core.config import LSTM_MS_URL

router = APIRouter()


@router.get("/api/lstm/{symbol}")
def lstm_price_forecast(symbol: str, lookback: int = Query(30, ge=1, le=3650)):
    try:
        r = requests.get(f"{LSTM_MS_URL}/lstm/{symbol}", params={"lookback": lookback}, timeout=120)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LSTM microservice unavailable: {e}")
