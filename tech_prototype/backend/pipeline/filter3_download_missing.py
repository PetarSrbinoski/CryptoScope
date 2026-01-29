from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
import threading
import time
import random

import pandas as pd
import requests

from ..core.config import BASE_DIR
from ..db.init_db import init_db
from ..db.connection import get_conn
from ..repositories.prices_write_repository import PricesWriteRepository, PriceInsertRow
from ..services.market_caps import CoinGeckoMarketCapProvider


DOWNLOAD_PLAN = BASE_DIR / "download_plan.csv"

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


@dataclass(frozen=True)
class DownloadJob:
    symbol: str
    last_date_raw: object  # can be NaN/None/str


def _normalize_last_date(raw_last_date) -> date | None:
    if pd.isna(raw_last_date):
        return None
    s = str(raw_last_date).strip()
    if not s or s.lower() == "none":
        return None
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


def _compute_start_date(last_date: date | None, years_back: int = 10) -> date:
    today = date.today()
    n_years_ago = today - timedelta(days=365 * years_back)
    if last_date is None:
        start = n_years_ago
    else:
        start = max(last_date + timedelta(days=1), n_years_ago)
    return min(start, today)


def _yahoo_fetch_range_rows(session: requests.Session, symbol: str, start_dt: date, end_dt: date) -> list[PriceInsertRow]:
    if start_dt >= end_dt:
        return []

    period1 = int(datetime(start_dt.year, start_dt.month, start_dt.day).timestamp())
    period2 = int(datetime(end_dt.year, end_dt.month, end_dt.day).timestamp())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "period1": period1, "period2": period2}

    # retry with exponential backoff for transient network/errors
    attempts = 3
    backoff_base = 1.0
    data = None
    for attempt in range(1, attempts + 1):
        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                # rate limited: backoff and retry
                time.sleep(backoff_base * (2 ** (attempt - 1)))
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception:
            if attempt == attempts:
                return []
            # jittered sleep
            time.sleep(backoff_base * (2 ** (attempt - 1)) * (1 + random.random()))

    try:
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]
    except Exception:
        return []

    opens = quote.get("open", []) or []
    highs = quote.get("high", []) or []
    lows = quote.get("low", []) or []
    closes = quote.get("close", []) or []
    volumes = quote.get("volume", []) or []

    rows: list[PriceInsertRow] = []
    for t, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if o is None or h is None or l is None or c is None:
            continue
        dt_str = datetime.utcfromtimestamp(t).date().isoformat()
        rows.append(
            PriceInsertRow(
                symbol=symbol,
                date=dt_str,
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v) if v is not None else 0.0,
            )
        )
    return rows


def _fetch_worker(job: DownloadJob) -> tuple[str, list[PriceInsertRow]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    last_dt = _normalize_last_date(job.last_date_raw)
    start_dt = _compute_start_date(last_dt, years_back=10)
    end_dt = date.today() + timedelta(days=1)  # exclusive

    if start_dt >= end_dt:
        return job.symbol, []

    try:
        rows = _yahoo_fetch_range_rows(session, job.symbol, start_dt, end_dt)
        return job.symbol, rows
    except Exception as e:
        # don't let a single symbol failure crash the whole thread pool
        print(f"[DownloadWorker] Failed {job.symbol}: {e}")
        return job.symbol, []


def update_data(workers: int | None = None) -> None:
    if not DOWNLOAD_PLAN.exists():
        raise FileNotFoundError(f"{DOWNLOAD_PLAN} not found. Run Filter 2 first.")

    plan = pd.read_csv(DOWNLOAD_PLAN)
    if "symbol" not in plan.columns:
        raise ValueError("download_plan.csv must contain a 'symbol' column.")

    init_db()

    write_repo = PricesWriteRepository(conn_factory=get_conn)
    write_repo.ensure_prices_table()

    jobs = [
        DownloadJob(symbol=str(sym), last_date_raw=last_date)
        for sym, last_date in zip(plan["symbol"].tolist(), plan.get("last_date", []).tolist())
    ]
    if not jobs:
        print("No symbols in download_plan.csv – nothing to do.")
        return

    # Reduce default concurrency to avoid overwhelming the network / sqlite
    if workers is None:
        cpu = os.cpu_count() or 4
        workers = min(8, len(jobs), max(2, cpu))
    else:
        workers = min(workers, len(jobs))

    print(f"\nFilter 3: Downloading missing OHLCV data with {workers} threads for {len(jobs)} symbols...\n")

    total_inserted = 0
    completed = 0

    # Single-writer queue to avoid concurrent SQLite writes
    write_queue: "Queue[list[PriceInsertRow] | None]" = Queue(maxsize=max(32, workers * 4))
    inserted_counter = {"count": 0}
    inserted_lock = threading.Lock()

    def writer_thread_func():
        batch: list[PriceInsertRow] = []
        BATCH_SIZE = 500
        FLUSH_INTERVAL = 2.0
        last_flush = time.time()

        while True:
            try:
                item = write_queue.get(timeout=1.0)
            except Empty:
                # periodic flush if we have pending items
                if batch and (time.time() - last_flush) >= FLUSH_INTERVAL:
                    try:
                        n = write_repo.insert_ohlcv_ignore_duplicates(batch)
                        with inserted_lock:
                            inserted_counter["count"] += n
                    except Exception as e:
                        print(f"[Writer] Failed to write batch: {e}")
                    batch.clear()
                    last_flush = time.time()
                continue

            if item is None:
                # sentinel -> flush and exit
                if batch:
                    try:
                        n = write_repo.insert_ohlcv_ignore_duplicates(batch)
                        with inserted_lock:
                            inserted_counter["count"] += n
                    except Exception as e:
                        print(f"[Writer] Failed to write final batch: {e}")
                    batch.clear()
                break

            # item is rows list
            rows = item
            if rows:
                batch.extend(rows)

            # flush when batch is large
            if len(batch) >= BATCH_SIZE or (time.time() - last_flush) >= FLUSH_INTERVAL:
                try:
                    n = write_repo.insert_ohlcv_ignore_duplicates(batch)
                    with inserted_lock:
                        inserted_counter["count"] += n
                except Exception as e:
                    print(f"[Writer] Failed to write batch: {e}")
                batch.clear()
                last_flush = time.time()

    writer_thread = threading.Thread(target=writer_thread_func, daemon=True)
    writer_thread.start()

    # Use thread pool but make processing robust to per-task failures
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_worker, job): job for job in jobs}

        for fut in as_completed(futures):
            job = futures[fut]
            try:
                sym, rows = fut.result(timeout=60)
            except Exception as e:
                print(f"[Filter3] Worker exception for {job.symbol}: {e}")
                completed += 1
                continue

            if rows:
                try:
                    # enqueue rows for single-writer to persist
                    write_queue.put(rows, block=True, timeout=10)
                except Exception as e:
                    print(f"[Filter3] Failed to enqueue rows for {sym}: {e}")

            completed += 1
            # read inserted count from writer
            with inserted_lock:
                total_inserted = inserted_counter["count"]

            if completed % 200 == 0 or completed == len(jobs):
                print(f"   Progress: {completed}/{len(jobs)} symbols done (rows fetched: {total_inserted})")

    # signal writer to finish and wait
    write_queue.put(None)
    writer_thread.join()

    # final inserted count
    with inserted_lock:
        total_inserted = inserted_counter["count"]

    print(f"\nFilter 3 complete. Total rows fetched (attempted insert): {total_inserted}")

    # ---- market caps ----
    print("\n=== Filter 3b: Fetching market caps (CoinGecko) and writing into prices.mcap ===")
    provider = CoinGeckoMarketCapProvider()
    caps = provider.get_caps_usd()

    symbol_to_mcap: dict[str, float] = {}
    for full_symbol in plan["symbol"].astype(str).tolist():
        base = full_symbol.split("-")[0].strip().lower()
        mc = caps.get(base)
        if mc is not None:
            symbol_to_mcap[full_symbol] = mc

    updated = write_repo.update_latest_mcap_batch(symbol_to_mcap)
    print(f"[DONE] Updated latest mcap for {updated} symbols.")


if __name__ == "__main__":
    update_data()
