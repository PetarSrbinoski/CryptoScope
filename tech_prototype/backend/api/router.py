from __future__ import annotations

from fastapi import APIRouter

from ..api import (
    routes_lstm,
    routes_onchain,
    routes_prices,
    routes_sentiment,
    routes_signal,
    routes_symbols,
    routes_technical,
)

router = APIRouter()

router.include_router(routes_symbols.router)
router.include_router(routes_prices.router)
router.include_router(routes_technical.router)
router.include_router(routes_lstm.router)
router.include_router(routes_sentiment.router)
router.include_router(routes_onchain.router)
router.include_router(routes_signal.router)
