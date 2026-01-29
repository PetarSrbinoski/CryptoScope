from __future__ import annotations

import os
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException

from .db import get_conn, get_db_path

# ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, CCIIndicator, SMAIndicator, EMAIndicator, WMAIndicator
from ta.volatility import BollingerBands

app = FastAPI(title="Technical Analysis Microservice")


# ---------- DB initialization ----------

def init_db() -> None:
    """Initialize database schema on startup."""
    db_path = get_db_path()
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Touch the database file
    db_path.touch(exist_ok=True)
    
    with get_conn() as conn:
        # Enable WAL mode and busy_timeout
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.commit()
        
        # Ensure prices table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                mcap REAL,
                UNIQUE(symbol, date)
            )
            """
        )
        conn.commit()


@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup."""
    init_db()


# ---------- DB + data loading ----------

def load_prices(symbol: str) -> pd.DataFrame:
    """
    Load OHLCV ascending by date.
    """
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT date, open, high, low, close, volume
            FROM prices
            WHERE symbol = ?
            ORDER BY date ASC
            """,
            conn,
            params=(symbol,),
        )

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Ensure we have prices to compute on
    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)
    return df


def filter_by_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    timeframe: '1d' | '1y' | '10y'
    - 1d: last 1 day (if only daily candles, this becomes last row)
    - 1y: last 365 days
    - 10y: last 3650 days
    """
    if df.empty:
        return df

    tf = timeframe.lower()
    last_dt = df["date"].iloc[-1]

    if tf == "1d":
        # If data is daily bars, "last 1 day" means last row
        return df.tail(1).copy()

    if tf == "1y":
        cutoff = last_dt - pd.Timedelta(days=365)
        out = df[df["date"] >= cutoff].copy()
        return out.reset_index(drop=True)

    if tf == "10y":
        cutoff = last_dt - pd.Timedelta(days=3650)
        out = df[df["date"] >= cutoff].copy()
        return out.reset_index(drop=True)

    # default: no filtering
    return df


# ---------- indicator compute ----------

def safe_last(series: pd.Series) -> Optional[float]:
    if series is None or series.empty:
        return None
    v = series.iloc[-1]
    if pd.isna(v):
        return None
    return float(v)


def compute_indicators(df: pd.DataFrame) -> Dict[str, float | None]:
    """
    Compute indicator values on the provided dataframe.
    Expects df sorted ascending by date.
    """
    if df.empty:
        return {}

    close = df["close"]
    high = df["high"] if "high" in df else close
    low = df["low"] if "low" in df else close
    volume = df["volume"] if "volume" in df else pd.Series([0] * len(df))

    # Some indicators need a minimum window; return None if not enough rows
    def enough(n: int) -> bool:
        return len(df) >= n

    out: Dict[str, float | None] = {}

    # RSI 14
    out["RSI (14)"] = safe_last(RSIIndicator(close, window=14).rsi()) if enough(15) else None

    # MACD & signal
    if enough(35):
        macd_obj = MACD(close, window_slow=26, window_fast=12, window_sign=9)
        out["MACD"] = safe_last(macd_obj.macd())
        out["MACD Signal"] = safe_last(macd_obj.macd_signal())
    else:
        out["MACD"] = None
        out["MACD Signal"] = None

    # Stochastic %K
    out["Stochastic %K"] = (
        safe_last(StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3).stoch())
        if enough(20)
        else None
    )

    # ADX 14
    out["ADX (14)"] = safe_last(ADXIndicator(high=high, low=low, close=close, window=14).adx()) if enough(20) else None

    # CCI 20
    out["CCI (20)"] = safe_last(CCIIndicator(high=high, low=low, close=close, window=20).cci()) if enough(30) else None

    # Moving averages (20)
    out["SMA (20)"] = safe_last(SMAIndicator(close, window=20).sma_indicator()) if enough(21) else None
    out["EMA (20)"] = safe_last(EMAIndicator(close, window=20).ema_indicator()) if enough(21) else None
    out["WMA (20)"] = safe_last(WMAIndicator(close, window=20).wma()) if enough(21) else None

    # Bollinger Bands (20)
    if enough(21):
        bb = BollingerBands(close, window=20, window_dev=2)
        out["Bollinger Upper"] = safe_last(bb.bollinger_hband())
        out["Bollinger Middle"] = safe_last(bb.bollinger_mavg())
        out["Bollinger Lower"] = safe_last(bb.bollinger_lband())
    else:
        out["Bollinger Upper"] = None
        out["Bollinger Middle"] = None
        out["Bollinger Lower"] = None

    # Volume MA (20)
    out["Volume MA (20)"] = safe_last(SMAIndicator(volume.fillna(0), window=20).sma_indicator()) if enough(21) else None

    return out


# ---------- signal logic (UI pills) ----------

def signal_for(name: str, value: Optional[float], ctx: Dict[str, Any]) -> str:
    """
    Return: 'BUY' | 'SELL' | 'HOLD'
    Keep it simple & deterministic.
    """
    if value is None:
        return "HOLD"

    # Common oscillator rules
    if name == "RSI (14)":
        return "BUY" if value < 30 else "SELL" if value > 70 else "HOLD"
    if name == "Stochastic %K":
        return "BUY" if value < 20 else "SELL" if value > 80 else "HOLD"
    if name == "CCI (20)":
        return "BUY" if value < -100 else "SELL" if value > 100 else "HOLD"
    if name == "MACD":
        macd_sig = ctx.get("MACD Signal")
        if macd_sig is None:
            return "HOLD"
        return "BUY" if value > macd_sig else "SELL" if value < macd_sig else "HOLD"

    # MAs + Bollinger need price context for meaningful signals
    last_close = ctx.get("__last_close")
    if last_close is None:
        return "HOLD"

    if name in ("SMA (20)", "EMA (20)", "WMA (20)"):
        return "BUY" if last_close > value else "SELL" if last_close < value else "HOLD"

    if name == "Bollinger Upper":
        return "SELL" if last_close > value else "HOLD"
    if name == "Bollinger Lower":
        return "BUY" if last_close < value else "HOLD"
    if name == "Bollinger Middle":
        return "BUY" if last_close > value else "SELL" if last_close < value else "HOLD"

    return "HOLD"


def build_timeframe_block(df_tf: pd.DataFrame) -> Dict[str, Any]:
    """
    Return UI expected block:
    { indicators: { name: {value, signal} }, summary: {...} }
    """
    if df_tf.empty:
        return {"indicators": {}, "summary": {}}

    last_close = float(df_tf["close"].iloc[-1])
    last_date = df_tf["date"].iloc[-1].strftime("%Y-%m-%d")

    raw = compute_indicators(df_tf)

    # For signals that depend on close, pass context
    ctx = dict(raw)
    ctx["__last_close"] = last_close

    indicators: Dict[str, Dict[str, Any]] = {}
    for name, v in raw.items():
        indicators[name] = {
            "value": v,
            "signal": signal_for(name, v, ctx),
        }

    summary = {
        "date": last_date,
        "close": last_close,
    }

    return {"indicators": indicators, "summary": summary}


@app.get("/technical/{symbol}")
def technical(symbol: str) -> Dict[str, Any]:
    df = load_prices(symbol)
    if df.empty:
        return {
            "symbol": symbol,
            "timeframes": {
                "1d": {"indicators": {}, "summary": {}},
                "1y": {"indicators": {}, "summary": {}},
                "10y": {"indicators": {}, "summary": {}},
            },
        }

    # IMPORTANT: For 1d, indicator windows won't compute on 1 row.
    # So we compute indicators on the relevant history window,
    # but summary reflects the last date/close inside that window.

    df_1d_history = df.tail(3650).copy()  # use enough history for indicators
    df_1y_history = df.tail(365).copy()
    df_10y_history = df.tail(3650).copy()

    # Compute blocks
    block_1d = build_timeframe_block(df_1d_history)
    block_1y = build_timeframe_block(df_1y_history)
    block_10y = build_timeframe_block(df_10y_history)

    return {
        "symbol": symbol,
        "timeframes": {
            "1d": block_1d,
            "1y": block_1y,
            "10y": block_10y,
        },
    }


@app.get("/health")
def health():
    return {"ok": True}
