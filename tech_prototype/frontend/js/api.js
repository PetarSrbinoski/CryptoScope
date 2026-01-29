// js/api.js
// Centralized API client (HTTP + response normalization)

export function createApiClient({ baseUrl = "https://cryptoscope-api.azurewebsites.net/api" } = {}) {
  console.log("API baseUrl =", baseUrl);

  const api = {};

  // Microservice URLs (direct calls to avoid proxying through main API)
  const technicalMsUrl = "https://cryptoscope-technical-ms.azurewebsites.net/technical";
  const lstmMsUrl = "https://cryptoscope-lstm-ms.azurewebsites.net/lstm";

  async function getJson(url) {
    const res = await fetch(url);
    if (!res.ok) return null;
    try {
      return await res.json();
    } catch {
      return null;
    }
  }

  function normalizeSymbolsResponse(payload) {
    const items = Array.isArray(payload) ? payload : payload?.items || [];
    const total = Array.isArray(payload)
      ? items.length
      : payload?.total ?? (items ? items.length : 0);
    return { items, total };
  }

  function mapSymbolToCoin(raw) {
    const price = raw?.price != null ? Number(raw.price) : null;
    const change = raw?.change != null ? Number(raw.change) : null;

    return {
      id: raw?.id,
      rank: raw?.rank,

      // Keep both
      symbol: raw?.name,
      fullSymbol: raw?.symbol,
      name: raw?.name,

      price: Number.isFinite(price) ? price : null,
      change: Number.isFinite(change) ? change : null,
      vol: raw?.vol ?? null,
      mcap: raw?.mcap ?? null,
    };
  }

  api.fetchSymbolsPage = async function ({ page = 1, pageSize = 50, q = "" } = {}) {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (q && q.trim()) params.set("q", q.trim());

    const payload = await getJson(`${baseUrl}/symbols?${params.toString()}`);
    if (!payload) return { coins: [], total: 0 };

    const { items, total } = normalizeSymbolsResponse(payload);
    return { coins: items.map(mapSymbolToCoin), total };
  };

  api.fetchAllSymbols = async function ({ pageSize = 500 } = {}) {
    const all = [];
    let page = 1;

    while (true) {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(pageSize));

      const payload = await getJson(`${baseUrl}/symbols?${params.toString()}`);
      if (!payload) break;

      const { items, total } = normalizeSymbolsResponse(payload);
      if (!items.length) break;

      all.push(...items);
      if (!total || all.length >= total) break;
      page += 1;
    }

    return all.map(mapSymbolToCoin);
  };

  api.fetchPrices = async function (symbol, timeframe = null) {
    if (!symbol) return [];
    let url = `${baseUrl}/prices/${encodeURIComponent(symbol)}`;
    if (timeframe) url += `?timeframe=${encodeURIComponent(timeframe)}`;

    const payload = await getJson(url);
    if (!Array.isArray(payload)) return [];
    return payload.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  };

  api.fetchTechnical = async function (symbol) {
    if (!symbol) return null;
    return await getJson(`${technicalMsUrl}/${encodeURIComponent(symbol)}`);
  };

  api.fetchLstm = async function (symbol, lookback = 30) {
    if (!symbol) return null;
    return await getJson(
      `${lstmMsUrl}/${encodeURIComponent(symbol)}?lookback=${encodeURIComponent(lookback)}`
    );
  };

  api.fetchSentiment = async function (symbol, window = "1d", limit = 20) {
    if (!symbol) return null;
    return await getJson(
      `${baseUrl}/sentiment/${encodeURIComponent(symbol)}?window=${encodeURIComponent(window)}&limit=${encodeURIComponent(limit)}`
    );
  };

  api.fetchOnchain = async function (symbol) {
    if (!symbol) return null;
    return await getJson(`${baseUrl}/onchain/${encodeURIComponent(symbol)}`);
  };

  api.fetchSignal = async function (symbol) {
    if (!symbol) return null;
    return await getJson(`${baseUrl}/signal/${encodeURIComponent(symbol)}`);
  };

  return api;
}
