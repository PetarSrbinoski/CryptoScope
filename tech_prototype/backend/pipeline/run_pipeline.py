from __future__ import annotations
import time

from .filter1_scrape_symbols import get_symbols
from .filter2_check_existing_data import get_existing_status
from .filter3_download_missing import update_data


def main() -> None:
    """Run the entire data pipeline."""
    start_time = time.perf_counter()

    print("\n=== Filter 1: Scraping and cleaning top 1000 crypto symbols ===")
    get_symbols(limit=1000)

    print("\n=== Filter 2: Checking last available date in the DB ===")
    get_existing_status()

    print("\n=== Filter 3: Downloading missing OHLCV data into DB + updating market caps ===")
    update_data(workers=50)

    elapsed = time.perf_counter() - start_time
    print(f"\nPIPELINE COMPLETE ✔  (Total time: {elapsed:.2f} seconds)")


def run_pipeline() -> None:
    """Legacy alias for main()."""
    main()


if __name__ == "__main__":
    print("[run_pipeline] __main__ block entered")
    run_pipeline()
