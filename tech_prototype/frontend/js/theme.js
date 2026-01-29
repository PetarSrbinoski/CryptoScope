// js/theme.js
export function createTheme(ctx) {
  const theme = {
    init: () => {
      const prefersDark =
        window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

      if (localStorage.theme === "dark" || (!("theme" in localStorage) && prefersDark)) {
        theme.set("dark");
      } else {
        theme.set("light");
      }
    },

    set: (val) => {
      const next = val === "dark" ? "dark" : "light";

      // Observer-friendly update if the app provides setState().
      if (typeof ctx.setState === "function") ctx.setState({ theme: next });
      else ctx.state.theme = next;

      localStorage.theme = next;

      if (next === "dark") document.documentElement.classList.add("dark");
      else document.documentElement.classList.remove("dark");
    },

    toggle: () => {
      theme.set(ctx.state.theme === "dark" ? "light" : "dark");
    },
  };

  return theme;
}
