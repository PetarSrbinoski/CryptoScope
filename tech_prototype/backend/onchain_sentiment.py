from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crypto.db"

_analyzer = SentimentIntensityAnalyzer()

COINGECKO_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"
DEFILLAMA_CHAINS_URL = "https://api.llama.fi/v2/chains"
DEFILLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"

BLOCKCHAIR_API_BASE = "https://api.blockchair.com"

BLOCKCHAIR_MAPPING = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "DOGE": "dogecoin",
    "BCH": "bitcoin-cash",
    "DASH": "dash",
}

CG_ID_OVERRIDES = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
}


class RateLimited(Exception):
    pass


def init_onchain_sentiment_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sentiment_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT,
            title TEXT,
            url TEXT,
            published_at TEXT,
            sentiment REAL,
            label TEXT,
            raw_json TEXT,
            UNIQUE(symbol, source, source_id) ON CONFLICT IGNORE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS onchain_metrics (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            source TEXT,
            PRIMARY KEY(symbol, date, metric)
        );
        """
    )
    conn.commit()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_utc_date() -> str:
    return _utcnow().date().isoformat()


def _base_symbol(symbol: str) -> str:
    return symbol.split("-")[0].upper() if "-" in symbol else symbol.upper()


def _fetch_json(url: str, params: Optional[dict] = None, timeout: int = 15) -> Any:
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:
            raise RateLimited(f"429 Rate Limited: {url}")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] Fetch failed for {url}: {e}")
        return None


def fetch_blockchair_stats(symbol: str) -> Dict[str, float]:
    base = _base_symbol(symbol)
    chain = BLOCKCHAIR_MAPPING.get(base)
    if not chain:
        return {}

    url = f"{BLOCKCHAIR_API_BASE}/{chain}/stats"
    data = _fetch_json(url)
    if not data or "data" not in data:
        return {}

    stats = data["data"]
    metrics: Dict[str, float] = {}

    if "transactions_24h" in stats:
        metrics["tx_count"] = float(stats["transactions_24h"])
    if "hashrate_24h" in stats:
        metrics["hashrate"] = float(stats["hashrate_24h"])
    if "accounts_active_24h" in stats:
        metrics["active_addresses"] = float(stats["accounts_active_24h"])
    elif "mempool_transactions" in stats:
        metrics["mempool_depth"] = float(stats["mempool_transactions"])

    return metrics


def fetch_defillama_tvl(cg_id: str) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    try:
        chains = _fetch_json(DEFILLAMA_CHAINS_URL) or []
        for c in chains:
            if str(c.get("gecko_id")).lower() == str(cg_id).lower():
                tvl = c.get("tvl")
                if tvl:
                    metrics["tvl_chain_usd"] = float(tvl)
                break

        if "tvl_chain_usd" not in metrics:
            protos = _fetch_json(DEFILLAMA_PROTOCOLS_URL) or []
            for p in protos:
                if str(p.get("gecko_id")).lower() == str(cg_id).lower():
                    tvl = p.get("tvl")
                    if tvl:
                        metrics["tvl_protocol_usd"] = float(tvl)
                    break
    except Exception:
        pass
    return metrics


def get_market_data_for_nvt(
    conn: sqlite3.Connection, symbol: str
) -> Tuple[Optional[float], Optional[float]]:
    row = conn.execute(
        "SELECT mcap, volume FROM prices WHERE symbol=? ORDER BY date DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if row:
        return row["mcap"], row["volume"]
    return None, None


def refresh_onchain_metrics(
    conn: sqlite3.Connection, symbol: str, force: bool = False
) -> Dict[str, Any]:
    today = _today_utc_date()

    if not force:
        cached = conn.execute(
            "SELECT metric, value FROM onchain_metrics WHERE symbol=? AND date=?",
            (symbol, today),
        ).fetchall()
        if cached:
            metrics = {r["metric"]: r["value"] for r in cached}
            return {"symbol": symbol, "metrics": metrics, "source": "cache"}

    base = _base_symbol(symbol)
    cg_id = CG_ID_OVERRIDES.get(base, base.lower())

    new_metrics: Dict[str, float] = {}
    new_metrics.update(fetch_defillama_tvl(cg_id))
    new_metrics.update(fetch_blockchair_stats(symbol))

    mcap, vol = get_market_data_for_nvt(conn, symbol)
    if mcap and vol and vol > 0:
        new_metrics["nvt"] = mcap / vol

    for k, v in new_metrics.items():
        conn.execute(
            """
            INSERT INTO onchain_metrics(symbol, date, metric, value, source)
            VALUES(?,?,?,?,?)
            ON CONFLICT(symbol, date, metric) DO UPDATE SET value=excluded.value
            """,
            (symbol, today, k, v, "aggregator"),
        )
    conn.commit()

    return {
        "symbol": symbol,
        "metrics": new_metrics,
        "note": (
            "Real-time on-chain data fetched from Blockchair & DefiLlama."
            if new_metrics
            else "No public on-chain data available."
        ),
    }


def _analyze_text(text: str) -> Tuple[float, str]:
    if not text:
        return 0.0, "neutral"
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.05:
        return compound, "positive"
    if compound <= -0.05:
        return compound, "negative"
    return compound, "neutral"


def fetch_google_news(symbol: str, limit: int = 15) -> List[Dict]:
    base = _base_symbol(symbol)
    query = f"{base} crypto"
    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://news.google.com/rss/search?q={encoded_query}"
        f"&hl=en-US&gl=US&ceid=US:en"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items: List[Dict] = []

        for item in root.findall(".//item")[:limit]:
            title = item.find("title").text if item.find("title") is not None else "No Title"
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else str(datetime.now())

            score, label = _analyze_text(title)

            items.append(
                {
                    "symbol": symbol,
                    "source": "google_news",
                    "source_id": link,
                    "title": title,
                    "url": link,
                    "published_at": pub_date,
                    "sentiment": score,
                    "label": label,
                    "raw": {},
                }
            )

        return items
    except Exception as e:
        print(f"[WARN] Google News fetch failed: {e}")
        return []


def fetch_reddit_sentiment(symbol: str) -> List[Dict]:
    base = _base_symbol(symbol)
    results: List[Dict] = []
    headers = {"User-Agent": "CryptoScopeEdu/1.0"}

    subs = ["CryptoCurrency", "Bitcoin", "Ethereum"]
    if base not in ["BTC", "ETH"]:
        subs.append(base)

    for sub in subs:
        url = (
            f"https://www.reddit.com/r/{sub}/search.json?"
            f"q={base}&restrict_sr=1&sort=new&limit=5"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                continue

            data = resp.json()
            children = data.get("data", {}).get("children", [])

            for child in children:
                d = child["data"]
                title = d.get("title", "")
                score, label = _analyze_text(title)

                results.append(
                    {
                        "symbol": symbol,
                        "source": "reddit",
                        "source_id": d.get("id"),
                        "title": title,
                        "url": f"https://reddit.com{d.get('permalink')}",
                        "published_at": str(
                            datetime.fromtimestamp(
                                d.get("created_utc", time.time()), timezone.utc
                            )
                        ),
                        "sentiment": score,
                        "label": label,
                        "raw": d,
                    }
                )
        except Exception:
            continue

    return results


def refresh_sentiment(
    conn: sqlite3.Connection, symbol: str, window: str = "1d", limit: int = 30, force: bool = False
) -> Dict[str, Any]:
    if not force:
        last_item = conn.execute(
            "SELECT published_at FROM sentiment_items WHERE symbol=? ORDER BY published_at DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if last_item:
            return get_sentiment_from_db(conn, symbol, limit)

    items: List[Dict] = []
    items.extend(fetch_google_news(symbol, limit=15))
    items.extend(fetch_reddit_sentiment(symbol))

    for i in items:
        conn.execute(
            """
            INSERT OR IGNORE INTO sentiment_items
            (symbol, source, source_id, title, url, published_at, sentiment, label, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                i["symbol"],
                i["source"],
                i["source_id"],
                i["title"],
                i["url"],
                i["published_at"],
                i["sentiment"],
                i["label"],
                json.dumps(i.get("raw", {})),
            ),
        )
    conn.commit()

    return get_sentiment_from_db(conn, symbol, limit)


def get_sentiment_from_db(conn: sqlite3.Connection, symbol: str, limit: int) -> Dict[str, Any]:
    rows = conn.execute(
        """
        SELECT * FROM sentiment_items
        WHERE symbol=?
        ORDER BY published_at DESC LIMIT ?
        """,
        (symbol, limit),
    ).fetchall()

    items = [dict(r) for r in rows]

    avg_score = 0.0
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    by_source = {"google_news": 0, "reddit": 0}

    if items:
        scores = [r["sentiment"] for r in items]
        avg_score = sum(scores) / len(scores)
        for r in items:
            counts[r["label"]] += 1
            src = r["source"]
            by_source[src] = by_source.get(src, 0) + 1

    label = "neutral"
    if avg_score > 0.05:
        label = "positive"
    if avg_score < -0.05:
        label = "negative"

    return {
        "symbol": symbol,
        "summary": {"avg": avg_score, "label": label, "counts": counts},
        "by_source": by_source,
        "items": items,
    }


def compute_signal(conn: sqlite3.Connection, symbol: str) -> Dict[str, Any]:
    sentiment_data = get_sentiment_from_db(conn, symbol, limit=50)
    onchain_data = refresh_onchain_metrics(conn, symbol, force=False)

    s_score = sentiment_data["summary"]["avg"]
    metrics = onchain_data.get("metrics", {})

    tvl = metrics.get("tvl_chain_usd") or metrics.get("tvl_protocol_usd") or 0
    tx_count = metrics.get("tx_count", 0)
    nvt = metrics.get("nvt", 0)

    base_score = 50.0

    sentiment_impact = s_score * 25
    tvl_impact = 5 if tvl > 1_000_000_000 else (2 if tvl > 0 else 0)
    activity_impact = 5 if tx_count > 50_000 else 0

    nvt_impact = 0
    if nvt > 0:
        if nvt < 30:
            nvt_impact = 5
        elif nvt > 100:
            nvt_impact = -5

    final_score = base_score + sentiment_impact + tvl_impact + activity_impact + nvt_impact
    final_score = max(0, min(100, final_score))

    direction = "NEUTRAL"
    if final_score >= 80:
        direction = "STRONG_BULLISH"
    elif final_score >= 60:
        direction = "BULLISH"
    elif final_score <= 20:
        direction = "STRONG_BEARISH"
    elif final_score <= 40:
        direction = "BEARISH"

    confidence = abs(final_score - 50) / 50.0

    return {
        "symbol": symbol,
        "signal": {
            "direction": direction,
            "score": round(final_score, 1),
            "confidence": round(confidence, 2),
        },
        "inputs": {
            "sentiment_score": round(s_score, 3),
            "tvl_usd": tvl,
            "tx_count": tx_count,
            "nvt": round(nvt, 2),
        },
        "explanation": [
            f"Composite Score: {round(final_score, 1)}/100",
            f"Sentiment (News+Social): {round(sentiment_impact, 1)} pts",
            f"On-Chain Health (TVL/Tx): {round(tvl_impact + activity_impact, 1)} pts",
            f"Valuation (NVT): {round(nvt_impact, 1)} pts",
        ],
    }
