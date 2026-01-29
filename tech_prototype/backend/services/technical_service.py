from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd
from fastapi import HTTPException

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator, EMAIndicator, WMAIndicator, ADXIndicator
from ta.volatility import BollingerBands

from ..repositories.prices_repository import PricesRepository
from ..services.timeframe_service import TimeframeSpec, apply_timeframe


IndicatorsDict = Dict[str, Dict[str, Any]]


def compute_indicators_for_df(df: pd.DataFrame) -> IndicatorsDict:
    if df.empty or len(df) < 30:
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]

    indicators: IndicatorsDict = {}

    rsi_val = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
    indicators["RSI (14)"] = {
        "value": rsi_val,
        "signal": "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "hold",
    }

    macd_ind = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    macd_val = float(macd_ind.macd().iloc[-1])
    macd_sigv = float(macd_ind.macd_signal().iloc[-1])
    indicators["MACD (12,26,9)"] = {
        "value": macd_val,
        "signal": "buy" if macd_val > macd_sigv else "sell" if macd_val < macd_sigv else "hold",
    }

    k_val = float(
        StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        .stoch()
        .iloc[-1]
    )
    indicators["Stochastic %K"] = {
        "value": k_val,
        "signal": "buy" if k_val < 20 else "sell" if k_val > 80 else "hold",
    }

    adx_ind = ADXIndicator(high=high, low=low, close=close, window=14)
    adx_val = float(adx_ind.adx().iloc[-1])
    plus_di = float(adx_ind.adx_pos().iloc[-1])
    minus_di = float(adx_ind.adx_neg().iloc[-1])

    if adx_val > 25 and plus_di > minus_di:
        adx_sig = "buy"
    elif adx_val > 25 and plus_di < minus_di:
        adx_sig = "sell"
    else:
        adx_sig = "hold"

    typical_price = (high + low + close) / 3.0
    cci = (typical_price - typical_price.rolling(20).mean()) / (
        0.015 * typical_price.rolling(20).std()
    )
    cci_val = float(cci.iloc[-1])
    indicators["CCI (20)"] = {
        "value": cci_val,
        "signal": "buy" if cci_val < -100 else "sell" if cci_val > 100 else "hold",
    }

    last_close = float(close.iloc[-1])

    sma_val = float(SMAIndicator(close=close, window=20).sma_indicator().iloc[-1])
    diff_sma = (last_close - sma_val) / sma_val * 100 if sma_val else 0
    indicators["SMA 20"] = {
        "value": sma_val,
        "signal": "buy" if diff_sma > 1 else "sell" if diff_sma < -1 else "hold",
    }

    ema_val = float(EMAIndicator(close=close, window=20).ema_indicator().iloc[-1])
    diff_ema = (last_close - ema_val) / ema_val * 100 if ema_val else 0
    indicators["EMA 20"] = {
        "value": ema_val,
        "signal": "buy" if diff_ema > 1 else "sell" if diff_ema < -1 else "hold",
    }

    wma_val = float(WMAIndicator(close=close, window=20).wma().iloc[-1])
    diff_wma = (last_close - wma_val) / wma_val * 100 if wma_val else 0
    indicators["WMA 20"] = {
        "value": wma_val,
        "signal": "buy" if diff_wma > 1 else "sell" if diff_wma < -1 else "hold",
    }

    bb = BollingerBands(close=close, window=20, window_dev=2)
    upper = float(bb.bollinger_hband().iloc[-1])
    lower = float(bb.bollinger_lband().iloc[-1])
    indicators["Bollinger Bands"] = {
        "value": last_close,
        "signal": "buy" if last_close < lower else "sell" if last_close > upper else "hold",
    }

    vol_ma_val = float(vol.rolling(20).mean().iloc[-1])
    vol_val = float(vol.iloc[-1])
    if vol_val > vol_ma_val * 1.2 and last_close > sma_val:
        vol_sig = "buy"
    elif vol_val < vol_ma_val * 0.8 and last_close < sma_val:
        vol_sig = "sell"
    else:
        vol_sig = "hold"

    indicators["Volume MA 20"] = {"value": vol_ma_val, "signal": vol_sig}

    return indicators


def summarize_signals(indicators: IndicatorsDict) -> Dict[str, Any]:
    if not indicators:
        return {"buy": 0, "sell": 0, "hold": 0, "overall": "not-enough-data"}

    buy = sum(1 for x in indicators.values() if x["signal"] == "buy")
    sell = sum(1 for x in indicators.values() if x["signal"] == "sell")
    hold = sum(1 for x in indicators.values() if x["signal"] == "hold")

    if buy > sell and buy >= hold:
        overall = "buy"
    elif sell > buy and sell >= hold:
        overall = "sell"
    else:
        overall = "hold"

    return {"buy": buy, "sell": sell, "hold": hold, "overall": overall}


@dataclass
class TechnicalAnalysisService:
    """
    Orchestrates the workflow for /api/technical.
    Keeps routes thin and removes duplicated computations.
    """
    prices_repo: PricesRepository

    def compute_for_symbol(self, symbol: str, specs: list[TimeframeSpec]) -> Dict[str, Any]:
        df = self.prices_repo.get_prices_df(symbol)
        if df.empty:
            raise HTTPException(status_code=404, detail="Symbol not found or no price data")

        result: Dict[str, Any] = {"symbol": symbol, "timeframes": {}}

        for spec in specs:
            sub = apply_timeframe(df, spec)
            indicators = compute_indicators_for_df(sub)  # computed ONCE
            result["timeframes"][spec.key] = {
                "from": sub["date"].min().strftime("%Y-%m-%d") if not sub.empty else None,
                "to": sub["date"].max().strftime("%Y-%m-%d") if not sub.empty else None,
                "indicators": indicators,
                "summary": summarize_signals(indicators),
                "granularity": spec.granularity,
            }

        return result
