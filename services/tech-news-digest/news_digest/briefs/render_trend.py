from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ..config import ASSET_DIR, RuntimeSettings
from ..market.provider import MarketProvider


class TrendChartRenderer:
    def __init__(self, settings: RuntimeSettings, provider: MarketProvider) -> None:
        self.settings = settings
        self.provider = provider

    def render(self, *, brief_date: str, symbols: list[str]) -> list[Path]:
        out_dir = ASSET_DIR / brief_date
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []

        for symbol in symbols:
            bars = self.provider.get_daily_bars(symbol, lookback_days=10)
            if len(bars) < 2:
                continue

            x_values = [bar.ts_ny.strftime("%m-%d") for bar in bars[-10:]]
            y_values = [bar.close for bar in bars[-10:]]
            fig, ax = plt.subplots(figsize=(8, 4.5), dpi=180)
            ax.plot(x_values, y_values, color="#0ea5e9", linewidth=3)
            ax.fill_between(x_values, y_values, [min(y_values)] * len(y_values), color="#0ea5e9", alpha=0.12)
            ax.set_title(symbol, fontsize=18, color="#111827")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(False)
            ax.tick_params(axis="x", labelrotation=25, labelsize=9)
            ax.tick_params(axis="y", labelsize=10)
            fig.tight_layout()
            out_path = out_dir / f"trend-{symbol.lower()}.png"
            fig.savefig(out_path, facecolor="white")
            plt.close(fig)
            paths.append(out_path)

        return paths
