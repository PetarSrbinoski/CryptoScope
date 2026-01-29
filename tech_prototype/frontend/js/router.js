// js/router.js
export function createRouter(ctx) {
    return {
        current: null,

        go(view, data) {
            switch (view) {
                case 'landing':
                    window.location.href = 'index.html';
                    break;
                case 'dashboard':
                    window.location.href = 'dashboard.html';
                    break;
                case 'watchlist':
                    window.location.href = 'watchlist.html';
                    break;
                case 'detail': {
                    if (!data || !data.symbol) {
                        console.warn('router.go("detail") requires data.symbol');
                        return;
                    }
                    const symbol = encodeURIComponent(data.symbol);
                    window.location.href = `coin.html?symbol=${symbol}`;
                    break;
                }
                default:
                    console.warn('Unknown view:', view);
            }
        },

        back() {
            window.history.back();
        }
    };
}
