// js/ui.js
export function createUI(app) {
    const ui = {};
    const state = app.state;
    const internal = app.internal || {};
    const api = app.api;

    function formatPrice(v) {
        if (v == null || isNaN(v)) return "—";
        const n = Number(v);
        if (n === 0) return "$0.00";
        if (n >= 1) {
            return (
                "$" +
                n.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })
            );
        }
        return "$" + n.toPrecision(6);
    }

    function formatChange(ch) {
        if (ch == null || isNaN(ch)) return {text: "—", cls: ""};
        const n = Number(ch);
        const text = (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
        const cls =
            n > 0
                ? "text-emerald-500 bg-emerald-500/10"
                : n < 0
                    ? "text-red-500 bg-red-500/10"
                    : "text-gray-500 bg-gray-500/10";
        return {text, cls};
    }

    function formatIndicatorValue(v) {
        if (v == null || isNaN(v)) return "—";
        const n = Number(v);
        if (Math.abs(n) >= 1000) {
            return n.toLocaleString("en-US", {maximumFractionDigits: 2});
        }
        return n.toFixed(2);
    }

    function formatSignal(signalRaw) {
        if (!signalRaw) return {text: "—", cls: "text-gray-500 bg-gray-500/10"};
        const s = String(signalRaw).toUpperCase();
        let cls = "text-gray-500 bg-gray-500/10";
        if (s === "BUY" || s === "STRONG_BUY" || s.includes("BULL")) {
            cls = "text-emerald-500 bg-emerald-500/10";
        } else if (s === "SELL" || s === "STRONG_SELL" || s.includes("BEAR")) {
            cls = "text-red-500 bg-red-500/10";
        } else if (s === "HOLD" || s === "NEUTRAL") {
            cls = "text-amber-500 bg-amber-500/10";
        }
        return {text: s.replace("_", " "), cls};
    }

    function formatUSDCompact(v) {
        if (v == null || isNaN(v)) return "—";
        try {
            return new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
                notation: "compact",
                maximumFractionDigits: 2,
            }).format(Number(v));
        } catch {
            return "$" + Number(v).toLocaleString("en-US", {maximumFractionDigits: 2});
        }
    }

    function esc(str) {
        if (typeof str !== "string") return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getPaginationState() {
        if (!internal.pagination) {
            internal.pagination = {pageSize: 50, currentPage: 1};
        }
        return internal.pagination;
    }

    function ensurePaginationContainer() {
        let container = document.getElementById("pagination-container");
        if (container) return container;

        const panel = document.querySelector("#view-dashboard .panel-clean");
        container = document.createElement("div");
        container.id = "pagination-container";
        container.className =
            "px-4 md:px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-3 text-xs md:text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-transparent";
        if (panel) panel.appendChild(container);
        return container;
    }

    function updateRangeButtons(activeLabel) {
        const buttons = document.querySelectorAll(".range-btn");
        const active = (activeLabel || "").toUpperCase();

        buttons.forEach((btn) => {
            const label = btn.textContent.trim().toUpperCase();
            btn.classList.remove(
                "active-range",
                "bg-brand-orange",
                "text-white",
                "border-brand-orange"
            );
            btn.classList.remove(
                "bg-white",
                "dark:bg-gray-800",
                "text-gray-900",
                "dark:text-white",
                "border-gray-200",
                "dark:border-gray-600"
            );
            btn.classList.add(
                "bg-white",
                "dark:bg-gray-800",
                "text-gray-900",
                "dark:text-white",
                "border-gray-200",
                "dark:border-gray-600"
            );

            if (label === active) {
                btn.classList.remove(
                    "bg-white",
                    "dark:bg-gray-800",
                    "text-gray-900",
                    "border-gray-200",
                    "dark:border-gray-600"
                );
                btn.classList.add(
                    "bg-brand-orange",
                    "text-white",
                    "border-brand-orange",
                    "active-range"
                );
            }
        });
    }

    function buildSparklinePoints(changePercent) {
        const n = 20;
        const base = 100;
        const trendFactor = 1 + (Number(changePercent) || 0) / 100;
        const end = base * trendFactor;

        const points = [];
        for (let i = 0; i < n; i++) {
            const t = i / (n - 1);
            const val = base + (end - base) * t + (Math.random() - 0.5) * 4;
            points.push(val);
        }
        return points;
    }

    function buildSparklinePath(points, width = 100, height = 32) {
        if (!points.length) return {d: "", width, height};

        const min = Math.min(...points);
        const max = Math.max(...points);
        const span = max - min || 1;

        const coords = points.map((p, i) => {
            const x = (i / (points.length - 1)) * width;
            const y = height - ((p - min) / span) * height;
            return [x, y];
        });

        let d = `M ${coords[0][0]} ${coords[0][1]}`;
        for (let i = 1; i < coords.length; i++) {
            const [x, y] = coords[i];
            d += ` L ${x} ${y}`;
        }
        return {d, width, height};
    }

    function renderTopCards() {
        const container = document.getElementById("top-cards-container");
        if (!container) return;

        const allCoins = (
            state.topCoins && state.topCoins.length ? state.topCoins : state.coins || []
        ).slice();

        if (!allCoins.length) {
            container.innerHTML = "";
            return;
        }

        allCoins.sort((a, b) => {
            const ra = a.rank ?? Number.MAX_SAFE_INTEGER;
            const rb = b.rank ?? Number.MAX_SAFE_INTEGER;
            return ra - rb;
        });

        const top = allCoins.slice(0, 5);

        container.innerHTML = top
            .map((coin) => {
                const priceText = formatPrice(coin.price);
                const {text: changeText, cls: changeCls} = formatChange(coin.change);

                const symbolDisplay = coin.symbol || coin.name || coin.fullSymbol || "—";
                const nameDisplay =
                    coin.name && coin.name !== symbolDisplay ? coin.name : symbolDisplay;

                const detailSymbol = encodeURIComponent(
                    coin.fullSymbol || coin.symbol || coin.name || ""
                );

                const pts = buildSparklinePoints(coin.change);
                const path = buildSparklinePath(pts);
                const isUp = (coin.change || 0) >= 0;
                const strokeColor = isUp ? "#22c55e" : "#ef4444";

                return `
<div
  class="bg-white dark:bg-brand-card border border-gray-200 dark:border-gray-800 rounded-3xl px-4 md:px-6 py-4 md:py-5 flex flex-col justify-between shadow-sm cursor-pointer hover:border-brand-orange hover:shadow-[0_10px_25px_rgba(0,0,0,0.15)] dark:hover:shadow-[0_10px_30px_rgba(0,0,0,0.4)] transition-all group"
  data-card-symbol="${detailSymbol}"
>
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 md:w-10 md:h-10 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center text-xs md:text-sm font-bold text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700">
        ${symbolDisplay.charAt(0) || "?"}
      </div>
      <div class="flex flex-col">
        <span class="text-sm md:text-base font-semibold text-gray-900 dark:text-white">
          ${nameDisplay}
        </span>
        <span class="text-[10px] md:text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          ${symbolDisplay}
        </span>
      </div>
    </div>
    <span class="px-2 py-1 rounded-full text-[10px] md:text-xs font-semibold ${changeCls}">
      ${changeText}
    </span>
  </div>
  <div class="flex items-end justify-between gap-3">
    <div class="flex flex-col">
      <span class="text-xl md:text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white font-mono">
        ${priceText}
      </span>
    </div>
    <div class="w-24 md:w-28 h-10">
      <svg viewBox="0 0 ${path.width} ${path.height}" width="100%" height="100%" preserveAspectRatio="none">
        <path d="${path.d}" fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
      </svg>
    </div>
  </div>
</div>`;
            })
            .join("");

        container.querySelectorAll("[data-card-symbol]").forEach((card) => {
            card.addEventListener("click", () => {
                const sym = card.getAttribute("data-card-symbol");
                if (!sym) return;
                window.location.href = `coin.html?symbol=${sym}`;
            });
        });
    }

    ui.renderDashboard = function () {
        const tbody = document.getElementById("market-table-body");
        if (!tbody) return;

        renderTopCards();

        const noResEl = document.getElementById("no-results");
        const coins = state.filteredCoins || [];

        if (!coins.length) {
            tbody.innerHTML = "";
            if (noResEl) {
                noResEl.classList.remove("hidden", "hidden-view");
                noResEl.style.display = "block";
            }
            const pag = ensurePaginationContainer();
            if (pag) pag.innerHTML = "";
            return;
        }

        if (noResEl) {
            noResEl.classList.add("hidden", "hidden-view");
            noResEl.style.display = "none";
        }

        const pagination = getPaginationState();
        const total = typeof state.totalCoins === "number" ? state.totalCoins : coins.length;
        const pageSize = pagination.pageSize || 50;
        const totalPages = Math.max(1, Math.ceil(total / pageSize));

        pagination.currentPage = Math.min(Math.max(pagination.currentPage, 1), totalPages);

        const page = pagination.currentPage;
        const startIndex = (page - 1) * pageSize;
        const endIndex = Math.min(startIndex + coins.length, total);

        tbody.innerHTML = coins
            .map((coin, idx) => {
                const globalIndex = startIndex + idx + 1;
                const priceText = formatPrice(coin.price);
                const {text: changeText, cls: changeCls} = formatChange(coin.change);
                const volText = coin.vol != null ? coin.vol : "—";

                const symbolDisplay = coin.symbol || coin.name || coin.fullSymbol || "—";
                const nameDisplay =
                    coin.name && coin.name !== symbolDisplay ? coin.name : symbolDisplay;

                const detailSymbol = encodeURIComponent(
                    coin.fullSymbol || coin.symbol || coin.name || ""
                );

                return `
<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
  <td class="py-3.5 md:py-4 pl-4 md:pl-8 text-xs md:text-sm text-gray-500 dark:text-gray-400">${globalIndex}</td>
  <td class="py-3.5 md:py-4 px-2 md:px-4">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center text-xs font-bold text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700">
        ${symbolDisplay.charAt(0) || "?"}
      </div>
      <div class="flex flex-col">
        <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm md:text-base">${nameDisplay}</span>
        <span class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">${symbolDisplay}</span>
      </div>
    </div>
  </td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right font-mono text-xs md:text-sm text-gray-900 dark:text-gray-100">${priceText}</td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right">
    <span class="inline-flex items-center justify-end px-2 py-1 rounded-full text-[11px] font-semibold ${changeCls}">
      ${changeText}
    </span>
  </td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right font-mono text-xs md:text-sm text-gray-700 dark:text-gray-400 hidden md:table-cell">${volText}</td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right pr-4 md:pr-6">
    <button data-symbol="${detailSymbol}" class="inline-flex items-center gap-1 px-2 md:px-2.5 py-1 rounded-md text-[11px] md:text-xs font-semibold bg-brand-orange text-white hover:bg-orange-500 transition-colors">
      View
    </button>
  </td>
</tr>`;
            })
            .join("");

        tbody.querySelectorAll("button[data-symbol]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const sym = btn.getAttribute("data-symbol");
                if (!sym) return;
                window.location.href = `coin.html?symbol=${sym}`;
            });
        });

        const pagContainer = ensurePaginationContainer();
        if (!pagContainer) return;

        pagContainer.innerHTML = `
<div class="flex items-center gap-2">
  <span class="uppercase tracking-wide text-[10px] md:text-xs text-gray-500 dark:text-gray-400">Rows per page</span>
  <select id="rows-per-page-select" class="border border-gray-200 dark:border-gray-700 bg-white dark:bg-brand-darker rounded-lg px-2 py-1.5 text-xs md:text-sm text-gray-700 dark:text-gray-100">
    <option value="10" ${pageSize === 10 ? "selected" : ""}>10</option>
    <option value="50" ${pageSize === 50 ? "selected" : ""}>50</option>
    <option value="100" ${pageSize === 100 ? "selected" : ""}>100</option>
  </select>
</div>
<div class="flex items-center gap-3 md:gap-4">
  <span class="text-[11px] md:text-xs text-gray-600 dark:text-gray-400">
    Showing <span class="font-semibold text-gray-900 dark:text-gray-100">${startIndex + 1}</span>–
    <span class="font-semibold text-gray-900 dark:text-gray-100">${endIndex}</span> of
    <span class="font-semibold text-gray-900 dark:text-gray-100">${total}</span>
  </span>
  <div class="flex items-center gap-1">
    <button id="pag-prev" class="px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-brand-darker text-gray-700 dark:text-gray-100 disabled:opacity-40 disabled:cursor-not-allowed text-xs md:text-sm">Prev</button>
    <span class="text-[11px] md:text-xs text-gray-600 dark:text-gray-400 px-1">
      Page <span class="font-semibold text-gray-900 dark:text-gray-100">${page}</span> / ${totalPages}
    </span>
    <button id="pag-next" class="px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-brand-darker text-gray-700 dark:text-gray-100 disabled:opacity-40 disabled:cursor-not-allowed text-xs md:text-sm">Next</button>
  </div>
</div>`;

        const sel = pagContainer.querySelector("#rows-per-page-select");
        const prevBtn = pagContainer.querySelector("#pag-prev");
        const nextBtn = pagContainer.querySelector("#pag-next");

        if (sel) {
            sel.addEventListener("change", async (e) => {
                const v = Number(e.target.value);
                const p = getPaginationState();
                p.pageSize = v || 50;
                p.currentPage = 1;
                await app.loadCoinsPage(p.currentPage, p.pageSize);
                ui.renderDashboard();
            });
        }

        if (prevBtn) {
            prevBtn.disabled = page <= 1;
            prevBtn.addEventListener("click", async () => {
                const p = getPaginationState();
                if (p.currentPage > 1) {
                    p.currentPage -= 1;
                    await app.loadCoinsPage(p.currentPage, p.pageSize);
                    ui.renderDashboard();
                }
            });
        }

        if (nextBtn) {
            nextBtn.disabled = page >= totalPages;
            nextBtn.addEventListener("click", async () => {
                const p = getPaginationState();
                if (p.currentPage < totalPages) {
                    p.currentPage += 1;
                    await app.loadCoinsPage(p.currentPage, p.pageSize);
                    ui.renderDashboard();
                }
            });
        }
    };

    ui.handleSearch = async function (query) {
        state.currentQuery = (query || "").trim();
        const p = getPaginationState();
        p.currentPage = 1;
        await app.loadCoinsPage(p.currentPage, p.pageSize || 50);
        ui.renderDashboard();
    };

    function rangeLabelToTimeframeParam(rangeLabel) {
        const label = (rangeLabel || "").toUpperCase();
        if (label === "1D") return "1d";
        if (label === "1Y") return "1y";
        if (label === "10Y") return "10y";
        return null;
    }


function renderOnchainSentimentSection(symbol, sentimentPayload, onchainPayload, signalPayload) {
    const sentScoreEl = document.getElementById("sentiment-score-box");
    const sentPillEl = document.getElementById("sentiment-pill");
    const feedEl = document.getElementById("sentiment-feed");
    const newsCountEl = document.getElementById("news-count");
    const redditCountEl = document.getElementById("reddit-count");

    const legacySentLabelEl = document.getElementById("sentiment-label");
    const legacySentAvgEl = document.getElementById("sentiment-avg");

    if (sentimentPayload) {
        const sum = sentimentPayload.summary || {};
        const avg = sum.avg || 0;

        if (sentScoreEl) sentScoreEl.textContent = avg.toFixed(2);

        let label = "NEUTRAL";
        let color = "bg-gray-200 text-gray-800";
        if (avg > 0.05) {
            label = "POSITIVE";
            color = "bg-emerald-100 text-emerald-700";
        }
        if (avg < -0.05) {
            label = "NEGATIVE";
            color = "bg-red-100 text-red-700";
        }

        if (sentPillEl) {
            sentPillEl.textContent = label;
            sentPillEl.className = `px-2 py-1 rounded text-xs font-bold ${color}`;
        }

        if (legacySentLabelEl) {
            legacySentLabelEl.textContent = label;
            legacySentLabelEl.className = `inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold ${color}`;
        }
        if (legacySentAvgEl) legacySentAvgEl.textContent = avg.toFixed(3);

        const bySource = sentimentPayload.by_source || {};
        const newsCount = (bySource.google_news || 0) + (bySource.gdelt || 0);
        if (newsCountEl) newsCountEl.textContent = newsCount;
        if (redditCountEl) redditCountEl.textContent = bySource.reddit || 0;

        if (feedEl && Array.isArray(sentimentPayload.items)) {
            const items = sentimentPayload.items.slice(0, 15);
            if (!items.length) {
                feedEl.innerHTML = '<div class="text-gray-400 italic">No news found.</div>';
            } else {
                feedEl.innerHTML = items
                    .map((item) => {
                        const isPos = item.sentiment > 0.05;
                        const isNeg = item.sentiment < -0.05;
                        const sColor = isPos ? "text-emerald-500" : isNeg ? "text-red-500" : "text-gray-400";
                        const scoreDisplay =
                            item.sentiment != null && !isNaN(item.sentiment) ? Number(item.sentiment).toFixed(1) : "0.0";

                        const pubDate = item.published_at ? new Date(item.published_at).toLocaleDateString() : "";
                        const src = (item.source || "").toLowerCase();
                        const icon = src === "reddit" ? "R" : "N";
                        const bgIcon = src === "reddit" ? "bg-orange-100 text-orange-600" : "bg-blue-100 text-blue-600";

                        const safeTitle = esc(item.title || "(untitled)");
                        const safeUrl = item.url || "#";
                        const safeSource = esc(item.source || "source");

                        return `
<div class="flex gap-3 border-b border-gray-100 dark:border-gray-700 pb-2 last:border-0">
  <div class="w-6 h-6 rounded-full ${bgIcon} flex items-center justify-center text-[10px] font-bold shrink-0 mt-1">${icon}</div>
  <div class="min-w-0 flex-1">
    <a href="${safeUrl}" target="_blank" class="hover:text-brand-orange block font-medium text-gray-700 dark:text-gray-300 text-[11px] leading-tight mb-0.5">${safeTitle}</a>
    <div class="flex items-center justify-between">
      <div class="text-[9px] text-gray-400">${safeSource} • ${pubDate}</div>
      <div class="${sColor} font-bold text-[10px]">${scoreDisplay}</div>
    </div>
  </div>
</div>`;
                    })
                    .join("");
            }
        }
    }

    const tvlEl = document.getElementById("oc-tvl");
    const txEl = document.getElementById("oc-tx");
    const addrEl = document.getElementById("oc-addr");
    const nvtEl = document.getElementById("oc-nvt");
    const hashEl = document.getElementById("oc-hash");
    const noteEl = document.getElementById("oc-note");
    const legTvlEl = document.getElementById("onchain-tvl-chain");

    if (onchainPayload && onchainPayload.metrics) {
        const m = onchainPayload.metrics;
        const fmtNum = (v) => (v != null && !isNaN(v) ? Number(v).toLocaleString() : "—");

        if (tvlEl) tvlEl.textContent = formatUSDCompact(m.tvl_chain_usd || m.tvl_protocol_usd);
        if (txEl) txEl.textContent = fmtNum(m.tx_count);
        if (addrEl) addrEl.textContent = fmtNum(m.active_addresses);
        if (nvtEl) nvtEl.textContent = m.nvt ? Number(m.nvt).toFixed(2) : "—";
        if (hashEl) hashEl.textContent = m.hashrate ? Number(m.hashrate).toLocaleString() + " H/s" : "—";
        if (noteEl && onchainPayload.note) noteEl.textContent = onchainPayload.note;

        if (legTvlEl) legTvlEl.textContent = formatUSDCompact(m.tvl_chain_usd || m.tvl_protocol_usd);
    }

    const sigTextEl = document.getElementById("signal-text");
    const sigConfEl = document.getElementById("signal-conf");
    const sigReasonsEl = document.getElementById("signal-reasons");
    const legSigPill = document.getElementById("signal-pill");

    if (signalPayload && signalPayload.signal) {
        const s = signalPayload.signal;
        const dir = s.direction || "NEUTRAL";

        if (sigTextEl) {
            sigTextEl.textContent = dir.replace("_", " ");
            let colorClass = "text-gray-200";
            if (dir.includes("BULL")) colorClass = "text-emerald-400";
            if (dir.includes("BEAR")) colorClass = "text-red-400";
            sigTextEl.className = `text-3xl font-extrabold tracking-tight mb-1 ${colorClass}`;
        }
        if (sigConfEl) sigConfEl.textContent = `Confidence: ${(s.confidence * 100).toFixed(0)}%`;

        if (sigReasonsEl && Array.isArray(signalPayload.explanation)) {
            sigReasonsEl.innerHTML = signalPayload.explanation
                .map((e) => `<p class="flex items-start gap-2"><span class="text-brand-orange">•</span><span>${esc(e)}</span></p>`)
                .join("");
        }

        if (legSigPill) {
            const {cls} = formatSignal(dir);
            legSigPill.textContent = "SIGNAL: " + dir;
            legSigPill.className = `inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold ${cls}`;
        }
    }
}

function renderLstmChart(lstmPayload) {
    const canvas = document.getElementById("lstm-chart-canvas");
    if (!canvas || !window.Chart) return;

    const ctx = canvas.getContext("2d");

    if (internal.lstmChart) {
        internal.lstmChart.destroy();
        internal.lstmChart = null;
    }

    if (!lstmPayload || !Array.isArray(lstmPayload.test_predictions) || !lstmPayload.test_predictions.length) {
        return;
    }

    const labels = lstmPayload.test_predictions.map((p) => p.date);
    const actual = lstmPayload.test_predictions.map((p) => p.actual);
    const predicted = lstmPayload.test_predictions.map((p) => p.predicted);

    internal.lstmChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {label: "Actual", data: actual, borderWidth: 2, pointRadius: 0, tension: 0.15, fill: false},
                {
                    label: "Predicted",
                    data: predicted,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.15,
                    fill: false,
                    borderDash: [4, 4]
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {mode: "index", intersect: false},
            plugins: {
                legend: {display: true},
                tooltip: {
                    enabled: true,
                    mode: "index",
                    intersect: false,
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${formatPrice(ctx.parsed.y)}`,
                    },
                },
            },
            scales: {
                x: {ticks: {maxTicksLimit: 8}},
                y: {
                    ticks: {
                        callback: (value) => {
                            try {
                                return "$" + Number(value).toLocaleString();
                            } catch {
                                return "$" + value;
                            }
                        },
                    },
                },
            },
        },
    });
}

function updateDetailHeader(symbolKey, prices) {
    const params = new URLSearchParams(window.location.search);
    const urlSymbol = params.get("symbol") || symbolKey;

    const coin =
        (state.coins || []).find((c) => c.fullSymbol === urlSymbol || c.symbol === urlSymbol || c.name === urlSymbol) ||
        (state.coins || []).find((c) => c.fullSymbol === symbolKey);

    const nameEl = document.getElementById("detail-name");
    const symEl = document.getElementById("detail-symbol");
    const iconEl = document.getElementById("detail-icon");
    const priceEl = document.getElementById("detail-price");
    const startDateEl = document.getElementById("dataset-start-date");
    const pointsEl = document.getElementById("dataset-points");

    if (coin) {
        const symbolText = coin.fullSymbol || coin.symbol || coin.name || urlSymbol;
        const displayName = coin.name || symbolText;
        if (nameEl) nameEl.textContent = displayName;
        if (symEl) symEl.textContent = symbolText;
        if (iconEl) iconEl.textContent = (displayName[0] || "?").toUpperCase();
    } else {
        if (nameEl) nameEl.textContent = urlSymbol || symbolKey || "Asset";
        if (symEl) symEl.textContent = urlSymbol || symbolKey || "";
        if (iconEl) iconEl.textContent = (urlSymbol || symbolKey || "?").charAt(0).toUpperCase();
    }

    if (priceEl) {
        if (prices && prices.length) {
            const last = prices[prices.length - 1];
            priceEl.textContent = formatPrice(last.close);
        } else if (coin) {
            priceEl.textContent = formatPrice(coin.price);
        } else {
            priceEl.textContent = "$0.00";
        }
    }

    if (prices && prices.length) {
        const first = prices[0];
        if (startDateEl && first.date) startDateEl.textContent = first.date;
        if (pointsEl) pointsEl.textContent = String(prices.length);
    }
}

function renderDetailChart(prices, rangeLabel) {
    const canvas = document.getElementById("detail-chart-canvas");
    if (!canvas || !window.Chart) return;

    internal.detailPrices = prices;
    internal.detailRange = rangeLabel || internal.detailRange || "10Y";

    const labels = (prices || []).map((p) => p.date);
    const values = (prices || []).map((p) => p.close);

    const ctx = canvas.getContext("2d");
    if (internal.detailChart) internal.detailChart.destroy();

    internal.detailChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{label: "Close", data: values, borderWidth: 2, pointRadius: 0, tension: 0.15, fill: false}]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {mode: "index", intersect: false},
            plugins: {
                legend: {display: false},
                tooltip: {
                    enabled: true,
                    mode: "index",
                    intersect: false,
                    callbacks: {label: (ctx) => formatPrice(ctx.parsed.y)}
                },
            },
            scales: {
                x: {ticks: {maxTicksLimit: 8}},
                y: {
                    ticks: {
                        callback: (value) => {
                            try {
                                return "$" + Number(value).toLocaleString();
                            } catch {
                                return "$" + value;
                            }
                        },
                    },
                },
            },
        },
    });

    updateRangeButtons(internal.detailRange);
}

function renderIndicatorsSection(symbol, indicatorsPayload) {
    const tbody = document.getElementById("indicator-table-body");
    if (!tbody) return;

    const tfs = indicatorsPayload?.timeframes;
    if (!tfs || !Object.keys(tfs).length) {
        tbody.innerHTML = `
<tr>
  <td colspan="4" class="py-3 text-xs md:text-sm text-gray-500 dark:text-gray-400 text-center">
    No technical indicator data available for ${symbol}.
  </td>
</tr>`;
        return;
    }

    const order = [
        ["1d", "1D"],
        ["1y", "1Y"],
        ["10y", "10Y"],
    ];

    const firstKey = order.map((x) => x[0]).find((k) => tfs[k]?.indicators);
    const indicatorNames = firstKey ? Object.keys(tfs[firstKey].indicators || {}) : [];
    if (!indicatorNames.length) {
        tbody.innerHTML = `
<tr>
  <td colspan="4" class="py-3 text-xs md:text-sm text-gray-500 dark:text-gray-400 text-center">
    No technical indicator data available for ${symbol}.
  </td>
</tr>`;
        return;
    }

    tbody.innerHTML = indicatorNames
        .sort()
        .map((indName) => {
            const cellsHtml = order
                .map(([key]) => {
                    const entry = tfs[key]?.indicators?.[indName] || null;
                    const valText = formatIndicatorValue(entry?.value);
                    const {text: sigText, cls: sigCls} = formatSignal(entry?.signal);

                    return `
<td class="py-3.5 md:py-3 px-2 md:px-3 text-center text-xs md:text-sm text-gray-900 dark:text-gray-100">
  <div class="flex flex-col items-center gap-1">
    <span class="font-mono">${valText}</span>
    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${sigCls}">
      ${sigText}
    </span>
  </div>
</td>`;
                })
                .join("");

            return `
<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
  <td class="py-3.5 md:py-3 px-2 md:px-3 text-xs md:text-sm font-semibold text-gray-800 dark:text-gray-100">
    ${indName}
  </td>
  ${cellsHtml}
</tr>`;
        })
        .join("");
}

function renderLstmSection(symbol, lstmPayload) {
    const statusEl = document.getElementById("lstm-status-text");
    const nextPriceEl = document.getElementById("lstm-next-price");
    const rmseEl = document.getElementById("lstm-metric-rmse");
    const mapeEl = document.getElementById("lstm-metric-mape");
    const r2El = document.getElementById("lstm-metric-r2");
    const lookbackEl = document.getElementById("lstm-lookback");
    const trainRatioEl = document.getElementById("lstm-train-ratio");
    const weekEl = document.getElementById("lstm-week-forecast");

    if (!statusEl && !nextPriceEl) return;

    if (!lstmPayload) {
        if (statusEl) statusEl.textContent = `LSTM analysis is not available for ${symbol}.`;
        if (nextPriceEl) nextPriceEl.textContent = "—";
        if (rmseEl) rmseEl.textContent = "—";
        if (mapeEl) mapeEl.textContent = "—";
        if (r2El) r2El.textContent = "—";
        if (lookbackEl) lookbackEl.textContent = "—";
        if (trainRatioEl) trainRatioEl.textContent = "—";
        if (weekEl) weekEl.textContent = "No 7-day forecast available.";
        renderLstmChart(null);
        return;
    }

    const lookback = lstmPayload.lookback ?? 30;
    const trainRatio = lstmPayload.train_ratio ?? 0.7;
    const metrics = lstmPayload.metrics || {};

    if (statusEl) {
        statusEl.textContent = `Model trained on ${Math.round(trainRatio * 100)}% of the history with a lookback window of ${lookback} days.`;
    }
    if (nextPriceEl) nextPriceEl.textContent = formatPrice(lstmPayload.next_day_prediction);
    if (rmseEl) rmseEl.textContent = formatIndicatorValue(metrics.rmse);

    if (mapeEl) {
        const m = metrics.mape;
        mapeEl.textContent = m != null && !isNaN(m) ? (m * 100).toFixed(2) + "%" : "—";
    }

    if (r2El) {
        const v = metrics.r2;
        r2El.textContent = v != null && !isNaN(v) ? v.toFixed(3) : "—";
    }

    if (lookbackEl) lookbackEl.textContent = String(lookback);
    if (trainRatioEl) trainRatioEl.textContent = `${Math.round(trainRatio * 100)}%`;

    if (weekEl) {
        const week = Array.isArray(lstmPayload.one_week_forecast) ? lstmPayload.one_week_forecast : [];
        if (!week.length) {
            weekEl.textContent = "No 7-day forecast available.";
        } else {
            weekEl.innerHTML = week
                .map((item) => `Day +${item.day_offset} (${item.date}): <span class="font-mono">${formatPrice(item.predicted)}</span>`)
                .map((line) => `<div>${line}</div>`)
                .join("");
        }
    }

    renderLstmChart(lstmPayload);
}

function attachDownloadButtons(symbol, prices) {
    const btnCsv = document.getElementById("btn-download-csv");
    const btnJson = document.getElementById("btn-download-json");
    const safeSymbol = (symbol || "asset").replace(/[^A-Za-z0-9\-_.]/g, "_");

    if (btnCsv) {
        btnCsv.onclick = () => {
            const header = ["date", "open", "high", "low", "close", "volume"];
            const rows = (prices || []).map((p) => [
                p.date ?? "",
                p.open ?? "",
                p.high ?? "",
                p.low ?? "",
                p.close ?? "",
                p.volume ?? "",
            ]);

            const csvLines = [
                header.join(","),
                ...rows.map((r) =>
                    r
                        .map((val) => {
                            if (val === null || val === undefined) return "";
                            const s = String(val);
                            if (s.includes(",") || s.includes('"')) return `"${s.replace(/"/g, '""')}"`;
                            return s;
                        })
                        .join(",")
                ),
            ];

            const blob = new Blob([csvLines.join("\n")], {type: "text/csv;charset=utf-8;"});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${safeSymbol}_ohlcv.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        };
    }

    if (btnJson) {
        btnJson.onclick = () => {
            const payload = {symbol, prices: prices || []};
            const jsonStr = JSON.stringify(payload, null, 2);
            const blob = new Blob([jsonStr], {type: "application/json;charset=utf-8;"});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${safeSymbol}_ohlcv.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        };
    }
}

async function loadAndRenderDetailRange(symbolKey, effectiveSymbol, rangeLabel) {
    if (!internal.pricesByRange) internal.pricesByRange = {};

    const tfParam = rangeLabelToTimeframeParam(rangeLabel);
    const cacheKey = (rangeLabel || "").toUpperCase();

    let prices = internal.pricesByRange[cacheKey];
    if (!prices) {
        prices = await api.fetchPrices(symbolKey, tfParam);
        internal.pricesByRange[cacheKey] = prices;
    }

    updateDetailHeader(symbolKey, prices);
    renderDetailChart(prices, cacheKey);
    attachDownloadButtons(effectiveSymbol, prices);
}

ui.renderDetailFromUrl = async function () {
    const params = new URLSearchParams(window.location.search);
    const symbolParam = params.get("symbol");

    let symbolKey = symbolParam;
    if (!symbolKey && state.coins?.length) {
        symbolKey = state.coins[0].fullSymbol || state.coins[0].symbol;
    }
    if (!symbolKey) return;

    const effectiveSymbol = symbolParam || symbolKey;
    internal.detailRange = "10Y";

    await loadAndRenderDetailRange(symbolKey, effectiveSymbol, internal.detailRange);

    try {
        renderIndicatorsSection(effectiveSymbol, await api.fetchTechnical(effectiveSymbol));
    } catch {
    }

    try {
        renderLstmSection(effectiveSymbol, await api.fetchLstm(effectiveSymbol, 30));
    } catch {
    }

    try {
        const [sentimentPayload, onchainPayload, signalPayload] = await Promise.all([
            api.fetchSentiment(effectiveSymbol, "1d", 30),
            api.fetchOnchain(effectiveSymbol),
            api.fetchSignal(effectiveSymbol),
        ]);
        renderOnchainSentimentSection(effectiveSymbol, sentimentPayload, onchainPayload, signalPayload);
    } catch {
    }

    document.querySelectorAll(".range-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const label = btn.textContent.trim().toUpperCase();
            internal.detailRange = label;
            await loadAndRenderDetailRange(symbolKey, effectiveSymbol, label);
        });
    });
};

ui.renderWatchlist = function () {
    const tbody = document.getElementById("watchlist-table-body");
    if (!tbody) return;

    const watch = state.watchlist || new Set();
    const coins = (state.coins || []).filter((c) => watch.has(c.fullSymbol || c.symbol || c.name));

    tbody.innerHTML = coins
        .map((coin, idx) => {
            const priceText = formatPrice(coin.price);
            const {text: changeText, cls: changeCls} = formatChange(coin.change);
            const volText = coin.vol != null ? coin.vol : "—";

            const symbolDisplay = coin.symbol || coin.name || coin.fullSymbol || "—";
            const nameDisplay =
                coin.name && coin.name !== symbolDisplay ? coin.name : symbolDisplay;

            return `
<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
  <td class="py-3.5 md:py-4 pl-4 md:pl-8 text-xs md:text-sm text-gray-500 dark:text-gray-400">${idx + 1}</td>
  <td class="py-3.5 md:py-4 px-2 md:px-4">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center text-xs font-bold text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700">
        ${symbolDisplay.charAt(0) || "?"}
      </div>
      <div class="flex flex-col">
        <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm md:text-base">${nameDisplay}</span>
        <span class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">${symbolDisplay}</span>
      </div>
    </div>
  </td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right font-mono text-xs md:text-sm text-gray-900 dark:text-gray-100">${priceText}</td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right">
    <span class="inline-flex items-center justify-end px-2 py-1 rounded-full text-[11px] font-semibold ${changeCls}">
      ${changeText}
    </span>
  </td>
  <td class="py-3.5 md:py-4 px-2 md:px-4 text-right font-mono text-xs md:text-sm text-gray-700 dark:text-gray-400 hidden md:table-cell">${volText}</td>
</tr>`;
        })
        .join("");
};

return ui;
}
