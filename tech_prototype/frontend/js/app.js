// js/app.js
import { state, internal, setState } from "./state.js";
import { createUtils } from "./utils.js";
import { createTheme } from "./theme.js";
import { createRouter } from "./router.js";
import { createUI } from "./ui.js";
import { createApiClient } from "./api.js";

const app = {
  state,
  internal,
  setState,
};

// Use correct API endpoint (separate from frontend server)
const apiHost = window.location.hostname;
const apiBaseUrl = apiHost === 'localhost' || apiHost === '127.0.0.1'
  ? `http://localhost:8000/api`
  : `https://cryptoscope-api.azurewebsites.net/api`;
app.api = createApiClient({ baseUrl: apiBaseUrl });

app.utils = createUtils(app);
app.theme = createTheme(app);
app.router = createRouter(app);
app.ui = createUI(app);

/**
 * Render the top ticker row on the dashboard page.
 * Kept here because it's purely "data -> small piece of DOM".
 */
function renderTicker(coinsPage, { onlyFirstPage = true, page = 1 } = {}) {
  const tick = document.getElementById("ticker");
  if (!tick) return;
  if (onlyFirstPage && page !== 1) return;

  if (!coinsPage.length) {
    tick.innerHTML = "";
    return;
  }

  let html = "";
  coinsPage.slice(0, 20).forEach((c) => {
    const change = c.change ?? 0;
    const cls = change >= 0 ? "text-emerald-400" : "text-red-400";
    const pct =
      c.change != null && !Number.isNaN(change) ? Number(change).toFixed(2) : "0.00";
    html += `<span class="mx-8 font-mono">${c.symbol} <span class="${cls}">${pct}%</span></span>`;
  });

  tick.innerHTML = html + html;
}

app.loadCoinsPage = async function (page, pageSize) {
  const q = app.state.currentQuery || "";

  try {
    const { coins, total } = await app.api.fetchSymbolsPage({
      page: page || 1,
      pageSize: pageSize || 50,
      q,
    });

    setState({
      coins,
      filteredCoins: coins,
      totalCoins: total,
    });

    // Cache "top coins" once.
    if (page === 1 && (!app.state.topCoins || !app.state.topCoins.length)) {
      setState({ topCoins: coins.slice() });
    }

    renderTicker(coins, { page });
  } catch (err) {
    console.error("Failed to load symbols page", err);
    setState({ coins: [], filteredCoins: [], totalCoins: 0 });
    renderTicker([], { page });
  }
};

app.loadAllCoins = async function () {
  try {
    const coins = await app.api.fetchAllSymbols({ pageSize: 500 });

    setState({
      coins,
      filteredCoins: coins,
      totalCoins: coins.length,
    });

    if (!app.state.topCoins || !app.state.topCoins.length) {
      setState({ topCoins: coins.slice(0, 100) });
    }
  } catch (err) {
    console.error("Failed to load all coins", err);
    setState({ coins: [], filteredCoins: [], totalCoins: 0 });
  }
};

app.init = async function () {
  const pagination = app.internal.pagination || { pageSize: 50, currentPage: 1 };
  app.internal.pagination = pagination;

  if (!pagination.pageSize) pagination.pageSize = 50;
  if (!pagination.currentPage) pagination.currentPage = 1;

  await app.loadCoinsPage(pagination.currentPage, pagination.pageSize);
};

window.app = app;

window.addEventListener("load", async () => {
  app.theme.init();

  const page = document.body.dataset.page || "landing";

  if (page === "dashboard") {
    await app.init();
    app.ui.renderDashboard();
  } else if (page === "watchlist") {
    await app.loadAllCoins();
    app.ui.renderWatchlist();
  } else if (page === "detail") {
    await app.init();
    await app.ui.renderDetailFromUrl();
  }

  if (window.lucide) window.lucide.createIcons();
});
