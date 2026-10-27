"""Upwork package for project 01: cover, screenshots and copy-paste texts."""
from __future__ import annotations

import html
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import brand  # noqa: E402
import config  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402

UP = PROJECT / "upwork"
OUT = PROJECT / "output"
FOLDER = "01-excel-kpi-report"


def cover_chart(path: Path) -> None:
    brand.apply_mpl_style()
    o = pd.read_csv(PROJECT / "data" / "clean" / "orders.csv", parse_dates=["Month"])
    m = o.groupby("Month")["NetRevenue"].sum()
    fy10, fy11 = m.iloc[:12].values / 1e3, m.iloc[12:24].values / 1e3
    labels = [d.strftime("%b") for d in m.index[:12]]
    fig, ax = plt.subplots(figsize=(14.2, 6.2), dpi=100)
    x = range(12)
    ax.plot(x, fy10, color=brand.BLUE_RAMP[3], lw=3, marker="o", ms=8, mec=brand.SURFACE, mew=2,
            label="Dec 2009 - Nov 2010")
    ax.plot(x, fy11, color=brand.BLUE, lw=3.5, marker="o", ms=9, mec=brand.SURFACE, mew=2,
            label="Dec 2010 - Nov 2011")
    ax.set_xticks(list(x), labels, fontsize=17)
    ax.tick_params(axis="y", labelsize=16)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"£{v:,.0f}K"))
    ax.set_ylim(0, 1600)
    ax.set_title("Monthly net revenue (GBP), this year vs last year", fontsize=21, loc="left", pad=16)
    ax.annotate(f"£{fy11[-1] / 1e3:.2f}M", (11, fy11[-1]), xytext=(-12, 10), textcoords="offset points",
                ha="right", fontsize=17, fontweight="semibold", color=brand.INK)
    ax.legend(loc="upper left", fontsize=16, ncols=2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def sql_page(path_html: Path, sql_results: dict) -> None:
    """Small HTML page with two queries and their results (rendered for the screenshot)."""
    text = (PROJECT / "sql" / "queries.sql").read_text()
    blocks = {}
    for part in text.split("-- Q")[1:]:
        head, _, body = part.partition("\n")
        blocks["Q" + head.split(":")[0]] = ("Q" + head, body.strip())

    def table(df: pd.DataFrame) -> str:
        th = "".join(f"<th>{html.escape(c)}</th>" for c in df.columns)
        rows = []
        for rec in df.itertuples(index=False):
            tds = []
            for v in rec:
                if isinstance(v, float):
                    tds.append(f"<td class=n>{v:,.1f}</td>")
                elif isinstance(v, int):
                    tds.append(f"<td class=n>{v:,}</td>")
                else:
                    tds.append(f"<td>{html.escape(str(v))}</td>")
            rows.append("<tr>" + "".join(tds) + "</tr>")
        return f"<table><tr>{th}</tr>{''.join(rows)}</table>"

    parts = []
    for q in ("Q6", "Q9"):
        title, body = blocks[q]
        parts.append(f"<section><h2>{html.escape(title)}</h2><pre>{html.escape(body)}</pre>"
                     f"{table(sql_results[q])}</section>")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face {{ font-family: Inter; src: url('file://{brand.FONTS["regular"]}'); }}
    @font-face {{ font-family: Inter; font-weight: 600; src: url('file://{brand.FONTS["semibold"]}'); }}
    body {{ margin: 0; padding: 28px 34px; background: {brand.SURFACE}; font-family: Inter, sans-serif;
           color: {brand.INK}; }}
    h1 {{ font-size: 26px; margin: 0 0 4px; color: {brand.BRAND}; }}
    p.sub {{ margin: 0 0 18px; color: {brand.INK_2}; font-size: 15px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }}
    section {{ min-width: 0; }}
    h2 {{ font-size: 17px; margin: 0 0 8px; }}
    pre {{ background: #0f1b2d; color: #e6edf6; font: 10.5px/1.45 'JetBrains Mono', monospace; padding: 12px;
          border-radius: 10px; margin: 0 0 12px; white-space: pre; overflow: hidden; }}
    table {{ border-collapse: collapse; font-size: 14px; width: 100%; }}
    th {{ background: {brand.BRAND}; color: #fff; text-align: left; padding: 6px 8px; font-weight: 600; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid {brand.GRID}; }}
    td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
    </style></head><body>
    <h1>SQL bonus: 13 business questions in SQLite</h1>
    <p class="sub">Same cleaned data as the Excel report. CTEs, window functions (NTILE, LAG, SUM OVER),
    CASE, self-joins. Full results: output/sql_results.md</p>
    <div class="grid">{''.join(parts)}</div></body></html>"""
    path_html.write_text(page, encoding="utf-8")


def render_pdf(pdf: Path, dpi: int, tmp: Path) -> list[Path]:
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(tmp / "page")], check=True)
    return sorted(tmp.glob("page-*.png"))


def crop_frac(img_path: Path, box: tuple[float, float, float, float], out: Path) -> Path:
    im = Image.open(img_path)
    w, h = im.size
    im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))).save(out)
    return out


def main(kpis: dict, sql_results: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p1up_"))
    cover_chart(tmp / "cover_chart.png")
    make_cover(UP / "cover.png", 1, "Excel reporting", "Excel KPI Dashboard",
               "E-commerce sales report with live formulas, a period selector and SQL",
               tmp / "cover_chart.png", "Excel · Python · SQL")

    pages = render_pdf(OUT / "ecommerce_kpi_report_snapshot.pdf", 220, tmp)
    kpi_page, notes_page = pages[0], pages[1]
    make_shot(UP / "shot-1.png", crop_frac(kpi_page, (0.01, 0.03, 0.86, 0.995), tmp / "c1.png"),
              "The whole KPI sheet: one period selector drives every number")
    make_shot(UP / "shot-2.png", crop_frac(kpi_page, (0.02, 0.045, 0.585, 0.415), tmp / "c2.png"),
              "KPI tiles and summary vs the previous period")
    make_shot(UP / "shot-3.png", crop_frac(kpi_page, (0.02, 0.418, 0.86, 0.995), tmp / "c3.png"),
              "Top products, monthly trend and year-over-year chart")
    make_shot(UP / "shot-4.png", crop_frac(notes_page, (0.07, 0.07, 0.93, 0.45), tmp / "c4.png"),
              "Notes sheet: every KPI defined, with the formula logic behind it")
    sql_page(tmp / "sql.html", sql_results)
    subprocess.run(["node", str(COMMON / "screenshot.js"), str(tmp / "sql.html"), str(tmp / "sql.png"),
                    "1420", "880", "--scale", "1.5"], check=True, capture_output=True)
    make_shot(UP / "shot-5.png", tmp / "sql.png", "SQL bonus: the same data in SQLite, 13 business queries")

    rev_chg = kpis["Net revenue"] / 9156117.49 - 1
    title = "Excel KPI Dashboard for E-commerce Sales"
    desc = (
        "An online retailer needs one Excel file to track sales and customer loyalty without manual work. "
        "I cleaned 1.07M raw invoice lines (duplicates, cancellations, fees) into a 46K-order Excel table "
        "and built a KPI sheet with live SUMIFS, COUNTIFS and INDEX/MATCH formulas, a period selector, "
        "native charts and conditional formatting, plus 13 SQL queries. "
        f"Finding: net revenue grew {rev_chg * 100:.1f}% year over year while orders fell 4.0%. "
        "Sample project built with public data."
    )
    skills = ["Microsoft Excel", "Excel Formula", "Data Analysis", "Data Visualization", "SQL"]
    captions = [
        "One-page KPI sheet. Pick the first and last month in the yellow cells and every KPI, ranking and chart "
        "updates. All values are live formulas (SUMIFS, COUNTIFS, INDEX/MATCH, LARGE) on Excel tables.",
        f"Headline KPIs for Dec 2010 - Nov 2011 vs the previous 12 months: net revenue £{kpis['Net revenue']:,.0f} "
        f"(+{rev_chg * 100:.1f}%), {kpis['Orders']:,} orders (-4.0%), average order value £{kpis['Average order value']:,.2f} (+6.8%).",
        "Top 10 products and the monthly trend. Conditional formatting highlights the selected period, "
        "month-over-month changes and year-over-year changes.",
        "Notes sheet: definition of each KPI and how it is calculated. The same sheet lists the data source and "
        "licence (UCI, CC BY 4.0), the cleaning steps with the rows removed by each rule, and limitations.",
        "The same cleaned data loaded into SQLite with 13 business queries. Example: the top 10% of customers "
        "bring 60% of revenue, and one storage jar had 95% of its sales returned (one bulk order cancelled).",
    ]
    links = [f"GitHub project folder: {config.folder_url(FOLDER)}",
             f"Excel file: {config.file_url(FOLDER + '/output/ecommerce_kpi_report.xlsx')}",
             f"SQL results: {config.file_url(FOLDER + '/output/sql_results.md')}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)


if __name__ == "__main__":
    print("Run through run.py (needs the KPI values).")
