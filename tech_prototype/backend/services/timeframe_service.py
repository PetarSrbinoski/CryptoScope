from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


def slice_timeframe(df: pd.DataFrame, days: Optional[int]) -> pd.DataFrame:
    if days is None or df.empty:
        return df
    end = df["date"].max()
    start = end - pd.Timedelta(days=days)
    out = df[df["date"] >= start]
    return out if not out.empty else df


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    x = df.copy().set_index("date")
    out = x.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna().reset_index()


@dataclass(frozen=True)
class TimeframeSpec:
    key: str             # "1d", "1y", "10y"
    lookback_days: int   # slicing window
    resample_rule: Optional[str]  # None, "W", "M"
    granularity: str     # "daily", "weekly", "monthly"


def get_timeframe_spec(tf: str) -> Optional[TimeframeSpec]:
    tf_norm = (tf or "").lower().strip()
    if tf_norm == "1d":
        return TimeframeSpec(key="1d", lookback_days=180, resample_rule=None, granularity="daily")
    if tf_norm == "1y":
        return TimeframeSpec(key="1y", lookback_days=400, resample_rule="W", granularity="weekly")
    if tf_norm == "10y":
        # use 'ME' (month end) which is supported by recent pandas versions
        return TimeframeSpec(
            key="10y", lookback_days=365 * 10 + 120, resample_rule="ME", granularity="monthly"
        )
    return None


def apply_timeframe(df: pd.DataFrame, spec: TimeframeSpec) -> pd.DataFrame:
    out = slice_timeframe(df, spec.lookback_days)
    if spec.resample_rule:
        out = resample_ohlcv(out, spec.resample_rule)
    return out
