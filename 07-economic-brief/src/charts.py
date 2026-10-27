"""The four charts of the brief (PNG, 220 dpi) from the tidy tables in data/clean/."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, MultipleLocator, NullLocator  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
import brand  # noqa: E402

CLEAN = PROJECT / "data" / "clean"
FIG = PROJECT / "output" / "figures"
DPI = 220
OTHER = "#c9c8c0"     # neutral bars for the countries that are not Colombia


def _save(fig, name: str) -> Path:
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return path


def increases(t: pd.DataFrame, size=(7.2, 3.3)) -> Path:
    """Bars: each year's increase. Dots: the previous year's inflation (the usual reference)."""
    t = t.loc[t["inflation_prev_year_pct"].notna()]
    fig, ax = plt.subplots(figsize=size)
    ax.bar(t.index, t["increase_pct"], width=0.62, color=brand.BLUE, label="Minimum wage increase", zorder=2)
    ax.plot(t.index, t["inflation_prev_year_pct"], linestyle="none", marker="o", markersize=6.5,
            markerfacecolor=brand.ORANGE, markeredgecolor=brand.SURFACE, markeredgewidth=1.6,
            label="Inflation of the previous year (Dec-Dec)", zorder=3)
    for y in t.index[-3:]:
        ax.annotate(f"{t.loc[y, 'increase_pct']:.1f}%", (y, t.loc[y, "increase_pct"]), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color=brand.INK)
    ax.set_xticks(range(int(t.index[0]), int(t.index[-1]) + 1, 2))
    ax.yaxis.set_major_locator(MultipleLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(0, max(t["increase_pct"].max(), t["inflation_prev_year_pct"].max()) * 1.18)
    ax.tick_params(labelsize=9)
    ax.legend(loc="upper left", fontsize=8.8, ncol=1, handlelength=1.2)
    return _save(fig, "chart1_increase_vs_inflation.png")


def real_vs_productivity(t: pd.DataFrame, size=(7.2, 3.3)) -> Path:
    fig, ax = plt.subplots(figsize=size)
    ax.axvspan(2022.5, t.index[-1] + 0.4, color=brand.WASH, zorder=0, lw=0)
    ax.plot(t.index, t["real_wage_index"], color=brand.BLUE, label="Real minimum wage", zorder=3)
    ax.plot(t.index, t["productivity_index"], color=brand.ORANGE, label="GDP per worker (productivity)", zorder=3)
    last = t.index[-1]
    for col, color, dy in (("real_wage_index", brand.BLUE, 6), ("productivity_index", brand.ORANGE, -12)):
        ax.annotate(f"{t.loc[last, col]:.0f}", (last, t.loc[last, col]), xytext=(6, dy / 2),
                    textcoords="offset points", fontsize=9, color=brand.INK, va="center")
    ax.text(2022.7, 101, "2023-2025", fontsize=8.5, color=brand.INK_2)
    ax.axhline(100, color=brand.AXIS, lw=0.8, zorder=1)
    ax.set_xlim(t.index[0] - 0.4, last + 1.4)
    ax.set_xticks(range(int(t.index[0]), int(last) + 1, 3))
    ax.set_ylim(95, max(t["real_wage_index"].max(), t["productivity_index"].max()) + 8)
    ax.set_ylabel(f"Index, {t.index[0]} = 100", fontsize=9)
    ax.tick_params(labelsize=9)
    ax.legend(loc="upper left", fontsize=8.8, handlelength=1.6)
    return _save(fig, "chart2_real_wage_vs_productivity.png")


def ranked_bars(d: pd.DataFrame, value: str, fmt, name: str, xlabel: str, median_label: str,
                size=(3.5, 5.6), tick_fmt=None) -> Path:
    d = d.sort_values(value)
    fig, ax = plt.subplots(figsize=size)
    colors = [brand.BLUE if n == "Colombia" else OTHER for n in d["name"]]
    ax.barh(d["name"], d[value], color=colors, height=0.66, zorder=2)
    med = d[value].median()
    ax.axvline(med, color=brand.INK_2, lw=1, ls=(0, (3, 2)), zorder=3)
    ax.text(med, len(d) - 0.2, f" {median_label} {fmt(med)}", fontsize=8, color=brand.INK_2, va="bottom")
    for i, (n, v) in enumerate(zip(d["name"], d[value])):
        if n == "Colombia" or i in (0, len(d) - 1):
            ax.text(v, i, f" {fmt(v)}", va="center", fontsize=8,
                    color=brand.INK, fontweight="semibold" if n == "Colombia" else "normal")
    for lbl in ax.get_yticklabels():
        if lbl.get_text() == "Colombia":
            lbl.set_fontweight("bold")
            lbl.set_color(brand.INK)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlim(0, d[value].max() * 1.2)
    ax.set_ylim(-0.6, len(d) + 0.4)
    ax.tick_params(axis="y", labelsize=7.8)
    ax.tick_params(axis="x", labelsize=8)
    ax.yaxis.set_minor_locator(NullLocator())
    if tick_fmt:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: tick_fmt(v)))
    ax.set_xlabel(xlabel, fontsize=8.5)
    return _save(fig, name)


def main() -> dict[str, Path]:
    brand.apply_mpl_style()
    t = pd.read_csv(CLEAN / "colombia_minimum_wage.csv", index_col="year")
    oecd = pd.read_csv(CLEAN / "oecd_minimum_to_median.csv")
    latam = pd.read_csv(CLEAN / "latam_minimum_wage_ppp.csv")
    return {
        "increases": increases(t),
        "real": real_vs_productivity(t),
        "oecd": ranked_bars(oecd, "min_to_median_pct", lambda v: f"{v:.0f}%", "chart3_minimum_to_median.png",
                            "Minimum wage as % of the median full-time wage", "median", size=(3.55, 7.3),
                            tick_fmt=lambda v: f"{v:.0f}%"),
        "latam": ranked_bars(latam, "ppp_usd_month", lambda v: f"${v:,.0f}", "chart4_latam_ppp.png",
                             "Monthly minimum wage, 2021 PPP dollars", "median", size=(3.55, 7.3),
                             tick_fmt=lambda v: f"{v:,.0f}"),
    }


if __name__ == "__main__":
    for k, v in main().items():
        print(k, v)
