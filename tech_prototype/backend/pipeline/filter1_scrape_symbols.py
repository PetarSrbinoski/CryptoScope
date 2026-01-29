from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..core.config import BASE_DIR

BASE_URL_TEMPLATE = "https://finance.yahoo.com/markets/crypto/all/?start={start}&count=100"
SYMBOLS_CSV_PATH = BASE_DIR / "symbols.csv"


def _fetch_page(start: int, headers: dict) -> list[str]:
    url = BASE_URL_TEMPLATE.format(start=start)
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table tbody tr")
    page_symbols: list[str] = []

    for row in rows:
        cell = row.find("td", attrs={"data-testid-cell": "ticker"})
        if not cell:
            continue
        span = cell.find("span", class_="symbol")
        if not span:
            continue
        symbol = span.get_text(strip=True)
        if symbol:
            page_symbols.append(symbol)

    return page_symbols


def _is_valid_symbol(symbol: str) -> bool:
    if not symbol.endswith("-USD"):
        return False
    base = symbol.split("-")[0].strip()
    return bool(base) and base.isalpha()


def get_symbols(limit: int = 1000, batch_pages: int = 8, max_pages: int = 100) -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}

    print(f"\nFilter 1: Fetching crypto tickers until we reach {limit} valid coins...\n")

    final_symbols: list[str] = []
    seen_bases: set[str] = set()

    current_page_idx = 0
    any_data = True

    while len(final_symbols) < limit and any_data and current_page_idx < max_pages:
        batch_starts: list[int] = []
        for _ in range(batch_pages):
            if current_page_idx >= max_pages:
                break
            batch_starts.append(current_page_idx * 100)
            current_page_idx += 1

        if not batch_starts:
            break

        any_data = False
        page_results: dict[int, list[str]] = {}

        with ThreadPoolExecutor(max_workers=len(batch_starts)) as executor:
            futures = {executor.submit(_fetch_page, start, headers): start for start in batch_starts}
            for future in as_completed(futures):
                start = futures[future]
                try:
                    page_results[start] = future.result()
                except Exception as e:
                    print(f"\nError fetching page start={start}: {e}")
                    page_results[start] = []

        for start in sorted(page_results.keys()):
            page_symbols = page_results[start]
            if page_symbols:
                any_data = True

            for sym in page_symbols:
                if not _is_valid_symbol(sym):
                    continue
                base = sym.split("-")[0].strip()
                if base in seen_bases:
                    continue
                final_symbols.append(sym)
                seen_bases.add(base)

                if len(final_symbols) >= limit:
                    break

            sys.stdout.write(f"\rtotal_valid={len(final_symbols)}/{limit}")
            sys.stdout.flush()

            if len(final_symbols) >= limit:
                break

    print("\n\nFinished pagination.")
    print(f"Final valid symbols: {len(final_symbols)} (limit was {limit})")