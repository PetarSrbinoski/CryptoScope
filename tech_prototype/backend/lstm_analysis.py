from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error, r2_score

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crypto.db"


def _load_close_series(symbol: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT date, close
            FROM prices
            WHERE symbol = ?
            ORDER BY date ASC
            """,
            conn,
            params=(symbol,),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)
    return df


def _create_sequences(series_scaled: np.ndarray, lookback: int):
    X, y = [], []
    for i in range(lookback, len(series_scaled)):
        X.append(series_scaled[i - lookback:i, 0])
        y.append(series_scaled[i, 0])
    X = np.array(X)
    y = np.array(y)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    return X, y


def _build_model(input_shape) -> Sequential:
    model = Sequential()
    model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(32))
    model.add(Dropout(0.2))
    model.add(Dense(1))
    model.compile(optimizer="adam", loss="mse")
    return model


def _make_week_forecast(
    model: Sequential,
    scaler: MinMaxScaler,
    series_scaled: np.ndarray,
    dates: List[pd.Timestamp],
    lookback: int,
    n_days: int = 7,
):
    if len(series_scaled) < lookback:
        return [], None

    last_seq = series_scaled[-lookback:].reshape(1, lookback, 1)
    preds_scaled = []

    for _ in range(n_days):
        next_scaled = model.predict(last_seq, verbose=0)[0, 0]
        preds_scaled.append(next_scaled)
        last_seq = np.concatenate(
            [last_seq[:, 1:, :], np.array(next_scaled).reshape(1, 1, 1)],
            axis=1,
        )

    preds_scaled = np.array(preds_scaled).reshape(-1, 1)
    preds = scaler.inverse_transform(preds_scaled).flatten()

    last_date = dates[-1]
    future_dates = [
        (last_date + pd.Timedelta(days=i + 1)).strftime("%Y-%m-%d")
        for i in range(n_days)
    ]

    forecast = [
        {
            "day_offset": i + 1,
            "date": future_dates[i],
            "predicted": float(preds[i]),
        }
        for i in range(n_days)
    ]

    next_day = float(preds[0]) if len(preds) else None
    return forecast, next_day


def run_lstm_analysis(
    symbol: str,
    lookback: int = 30,
    train_ratio: float = 0.7,
) -> Optional[Dict[str, Any]]:
    df = _load_close_series(symbol)
    if df.empty or len(df) <= lookback + 10:
        return None

    dates = df["date"].tolist()
    close_values = df["close"].values.astype(float).reshape(-1, 1)

    scaler = MinMaxScaler(feature_range=(0, 1))
    close_scaled = scaler.fit_transform(close_values)

    X, y = _create_sequences(close_scaled, lookback)
    dates_seq = dates[lookback:]

    if len(X) < 10:
        return None

    split_idx = int(len(X) * train_ratio)
    if split_idx <= 0 or split_idx >= len(X) - 1:
        split_idx = max(1, len(X) - 10)

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    dates_test = dates_seq[split_idx:]

    model = _build_model(input_shape=(X_train.shape[1], X_train.shape[2]))

    es = EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
        verbose=0,
    )

    model.fit(
        X_train,
        y_train,
        epochs=100,
        batch_size=32,
        validation_split=0.2,
        callbacks=[es],
        verbose=0,
        shuffle=False,
    )

    y_pred_scaled = model.predict(X_test, verbose=0).flatten()
    y_test_scaled = y_test

    y_test_inv = scaler.inverse_transform(y_test_scaled.reshape(-1, 1)).flatten()
    y_pred_inv = scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()

    rmse = float(np.sqrt(mean_squared_error(y_test_inv, y_pred_inv)))
    mape = float(mean_absolute_percentage_error(y_test_inv, y_pred_inv))
    r2 = float(r2_score(y_test_inv, y_pred_inv))

    test_predictions = []
    for dt, actual, pred in zip(dates_test, y_test_inv, y_pred_inv):
        test_predictions.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "actual": float(actual),
                "predicted": float(pred),
            }
        )

    one_week_forecast, next_day_prediction = _make_week_forecast(
        model=model,
        scaler=scaler,
        series_scaled=close_scaled,
        dates=dates,
        lookback=lookback,
        n_days=7,
    )

    result = {
        "symbol": symbol,
        "lookback": lookback,
        "train_ratio": train_ratio,
        "metrics": {
            "rmse": rmse,
            "mape": mape,
            "r2": r2,
        },
        "test_predictions": test_predictions,
        "next_day_prediction": next_day_prediction,
        "one_week_forecast": one_week_forecast,
    }
    return result


if __name__ == "__main__":
    import json
    sym = "BTC-USD"
    out = run_lstm_analysis(sym, lookback=30)
    print(json.dumps(out, indent=2)[:2000])
