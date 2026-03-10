"use client";

const STORAGE_KEY = "personal-website-theme";

export function ThemeToggle() {
  function toggleTheme() {
    const currentTheme =
      document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";

    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem(STORAGE_KEY, nextTheme);
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-elevated)] px-4 py-2 text-sm font-medium text-[color:var(--foreground)] transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-soft)]"
      aria-label="Toggle color theme"
      title="Toggle light or dark theme"
    >
      Theme
    </button>
  );
}
