"""Shared visual identity for every project in the portfolio.

One palette, one typeface (Inter, SIL Open Font License) and one set of chart
rules, so covers, screenshots, PDFs and charts look like they belong together.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path(__file__).resolve().parent / "fonts"

FONTS = {
    "regular": FONT_DIR / "Inter-Regular.ttf",
    "medium": FONT_DIR / "Inter-Medium.ttf",
    "semibold": FONT_DIR / "Inter-SemiBold.ttf",
    "bold": FONT_DIR / "Inter-Bold.ttf",
    "extrabold": FONT_DIR / "Inter-ExtraBold.ttf",
}

# Surfaces and ink
PAGE = "#f9f9f7"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
WASH = "#eef4fc"  # light blue wash used behind KPI tiles

# Brand accent (deep blue) used for title bars and highlights
BRAND = "#0d366b"
BRAND_2 = "#1c5cab"

# Categorical palette, fixed order (validated for colour-vision deficiency)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = SERIES

# Sequential blue ramp (light -> dark)
BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
             "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

# Status colours (only for good / warning / critical meaning)
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
GOOD_TEXT = "#006300"

AUTHOR = "Marlon Jiménez Valencia"
PORTFOLIO_TAG = "Sample project built with public data"


def register_fonts_matplotlib() -> None:
    from matplotlib import font_manager

    for path in FONTS.values():
        font_manager.fontManager.addfont(str(path))


def apply_mpl_style() -> None:
    """Quiet, consistent matplotlib defaults: thin marks, hairline grid, Inter."""
    import matplotlib as mpl

    register_fonts_matplotlib()
    mpl.rcParams.update({
        "font.family": "Inter",
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.titlesize": 14,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "lines.linewidth": 2,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "legend.fontsize": 10,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })


def register_fonts_reportlab() -> None:
    """Register Inter for reportlab PDFs (family name 'Inter')."""
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if "Inter" in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont("Inter", str(FONTS["regular"])))
    pdfmetrics.registerFont(TTFont("Inter-Medium", str(FONTS["medium"])))
    pdfmetrics.registerFont(TTFont("Inter-SemiBold", str(FONTS["semibold"])))
    pdfmetrics.registerFont(TTFont("Inter-Bold", str(FONTS["bold"])))
    addMapping("Inter", 0, 0, "Inter")
    addMapping("Inter", 1, 0, "Inter-Bold")
    addMapping("Inter", 0, 1, "Inter")
    addMapping("Inter", 1, 1, "Inter-Bold")


def fmt_compact(x: float, prefix: str = "", decimals: int = 1) -> str:
    """1234 -> 1.2K, 3_400_000 -> 3.4M (used for axis ticks and labels)."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if x >= div:
            return f"{sign}{prefix}{x / div:.{decimals}f}{suf}"
    return f"{sign}{prefix}{x:.0f}"
