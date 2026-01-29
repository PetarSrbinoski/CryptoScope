// js/utils.js
export function createUtils(ctx) {
  const utils = {
    fmtUSD: (n) =>
      new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n),

    /**
     * Draw a lightweight (synthetic) line chart in a canvas.
     * Used as placeholder when we don't have real price series data.
     */
    drawChart: (id, isPositive, isDetail = false) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;

      const g = canvas.getContext("2d");
      const w = canvas.width;
      const h = canvas.height;

      const isDark = ctx.state.theme === "dark";

      g.clearRect(0, 0, w, h);
      g.beginPath();

      const steps = isDetail ? 200 : 25;
      const stepW = w / steps;
      const volatility = isDetail ? 15 : 10;

      let x = 0;
      let y = h / 2;
      g.moveTo(0, y);

      for (let i = 1; i <= steps; i++) {
        x = i * stepW;
        y += (Math.random() - 0.5) * volatility;
        y = Math.max(5, Math.min(h - 5, y));
        g.lineTo(x, y);
      }

      if (isDetail) {
        g.strokeStyle = "#FF8C00";
      } else {
        g.strokeStyle = isPositive
          ? isDark
            ? "#10B981"
            : "#059669"
          : isDark
            ? "#EF4444"
            : "#DC2626";
      }

      g.lineWidth = isDetail ? 4 : 3;
      g.lineCap = "round";
      g.lineJoin = "round";
      g.stroke();

      if (isDetail) {
        g.lineTo(w, h);
        g.lineTo(0, h);
        const grad = g.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, isDark ? "#FF8C0044" : "#FF8C0022");
        grad.addColorStop(1, "transparent");
        g.fillStyle = grad;
        g.fill();
      }
    },

    /**
     * Draw a real (price-series) line chart in a canvas.
     * If prices are missing, falls back to a synthetic detail chart.
     */
    drawRealChart: (id, prices) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;

      const g = canvas.getContext("2d");

      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth || canvas.width;
      const h = canvas.clientHeight || canvas.height;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      g.setTransform(dpr, 0, 0, dpr, 0, 0);

      g.clearRect(0, 0, w, h);

      if (!prices || prices.length === 0) {
        utils.drawChart(id, true, true);
        return;
      }

      const closes = prices.map((p) => Number(p.close)).filter(Number.isFinite);
      if (!closes.length) {
        utils.drawChart(id, true, true);
        return;
      }

      const min = Math.min(...closes);
      const max = Math.max(...closes);
      const span = max - min || 1;

      g.beginPath();
      closes.forEach((value, i) => {
        const x = (i / (closes.length - 1)) * w;
        const y = h - ((value - min) / span) * h;
        if (i === 0) g.moveTo(x, y);
        else g.lineTo(x, y);
      });

      g.strokeStyle = "#FF8C00";
      g.lineWidth = 3;
      g.lineCap = "round";
      g.lineJoin = "round";
      g.stroke();

      g.lineTo(w, h);
      g.lineTo(0, h);
      const grad = g.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "#FF8C0040");
      grad.addColorStop(1, "transparent");
      g.fillStyle = grad;
      g.fill();
    },

    /**
     * Filter price points by an absolute time range.
     * Accepts: "1D", "1M", "1Y", "10Y".
     */
    filterPrices: (prices, range) => {
      const list = Array.isArray(prices) ? prices : [];
      const now = Date.now();

      const ms = {
        "1D": 1 * 24 * 60 * 60 * 1000,
        "1M": 30 * 24 * 60 * 60 * 1000,
        "1Y": 365 * 24 * 60 * 60 * 1000,
        "10Y": 3650 * 24 * 60 * 60 * 1000,
      };

      const windowMs = ms[String(range || "").toUpperCase()];
      if (!windowMs) return list;

      const cutoff = now - windowMs;
      return list.filter((p) => {
        const t = new Date(p?.date).getTime();
        return Number.isFinite(t) && t >= cutoff;
      });
    },
  };

  return utils;
}
