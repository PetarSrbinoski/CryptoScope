from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException

from ..core.config import TECHNICAL_MS_URL

router = APIRouter()


@router.get("/api/technical/{symbol}")
def get_technical(symbol: str):
    try:
        r = requests.get(f"{TECHNICAL_MS_URL}/technical/{symbol}", timeout=20)
        # even if microservice returns 200 with error payload, pass it through
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Technical microservice unavailable: {e}")


@router.get("/api/indicators/{symbol}")
def get_indicators(symbol: str):
    return get_technical(symbol)
