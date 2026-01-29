from __future__ import annotations

from abc import ABC, abstractmethod
import time
import requests


class MarketCapProvider(ABC):
    @abstractmethod
    def get_caps_usd(self) -> dict[str, float]:
        """
        Returns mapping: lowercase base ticker -> market cap USD.
        Example: {'btc': 123.0, 'eth': 456.0}
        """
        raise NotImplementedError


class CoinGeckoMarketCapProvider(MarketCapProvider):
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )

    def _get_caps_usd_paged(self, pages: int = 12, per_page: int = 250) -> dict[str, float]:
        """
        Internal helper that supports paging parameters.
        """
        caps: dict[str, float] = {}

        for page in range(1, pages + 1):
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            }

            resp = None
            for attempt in range(6):
                try:
                    r = self.session.get(url, params=params, timeout=20)
                    if r.status_code == 429:
                        time.sleep(2 ** attempt)
                        continue
                    r.raise_for_status()
                    resp = r
                    break
                except Exception:
                    time.sleep(2 ** attempt)

            if resp is None:
                break

            items = resp.json()
            if not isinstance(items, list) or not items:
                break

            for it in items:
                sym = str(it.get("symbol") or "").strip().lower()
                mc = it.get("market_cap")
                if not sym or mc is None or sym in caps:
                    continue
                try:
                    caps[sym] = float(mc)
                except Exception:
                    pass

            # be polite to the API
            time.sleep(0.35)

        return caps

    def get_caps_usd(self) -> dict[str, float]:
        """
        Public method required by the interface (no kwargs).
        """
        return self._get_caps_usd_paged(pages=12, per_page=250)
