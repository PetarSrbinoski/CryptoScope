// js/state.js
// Lightweight observable state (Observer pattern).
// - `state` holds the current mutable state.
// - `setState()` applies a patch and notifies subscribers.
// - `subscribe()` lets UI / other modules react to state changes.

export const state = {
  coins: [],
  filteredCoins: [],
  totalCoins: 0,

  // Stored as symbols (string). Keeping Set makes membership checks O(1).
  // (Your current app may seed this from ids; that's fine — Set still works.)
  watchlist: new Set([1, 3]),

  // UI / feature flags
  filter: "",
  currentQuery: "",
  theme: "light",
  fullHistory: [],
  currentSymbol: null,
  topCoins: []
};

export const internal = {
  // Canvas/chart bookkeeping
  smallChartsDrawn: new Set(),
  watchChartsDrawn: new Set(),

  // UI runtime caches (created lazily)
  pagination: null,
  pricesByRange: null,
  detailChart: null,
  lstmChart: null,
  detailPrices: null,
  detailRange: null
};

const listeners = new Set();

/**
 * Subscribe to state changes.
 * @param {(nextState: object, patch: object, prevState: object) => void} fn
 * @returns {() => void} unsubscribe function
 */
export function subscribe(fn) {
  if (typeof fn !== "function") return () => {};
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/**
 * Apply a shallow patch to state and notify subscribers.
 * @param {object} patch
 */
export function setState(patch) {
  if (!patch || typeof patch !== "object") return;

  const prev = { ...state };
  Object.assign(state, patch);

  listeners.forEach((fn) => {
    try {
      fn(state, patch, prev);
    } catch (err) {
      console.error("state subscriber failed:", err);
    }
  });
}
