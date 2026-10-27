"""Upwork package for project 02: cover, screenshots (desktop, filtered, phone, star schema, DAX) and texts."""
from __future__ import annotations

import html
import re
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
DASH = PROJECT / "output" / "dashboard.html"
FOLDER = "02-procurement-dashboard"


def shoot(target: Path, out: Path, w: int, h: int, *extra: str) -> Path:
    res = subprocess.run(["node", str(COMMON / "screenshot.js"), str(target), str(out), str(w), str(h),
                          "--wait", "1500", *extra], capture_output=True, text=True, check=True)
    if '"errors":[]' not in res.stdout:
        raise SystemExit(f"Console errors while taking {out.name}: {res.stdout}")
    return out


def cover_chart(f: pd.DataFrame, path: Path) -> None:
    brand.apply_mpl_style()
    g = f.groupby("modality_group").agg(n=("contract_id", "size"), v=("contract_value", "sum"))
    g = g.sort_values("v", ascending=True)
    g = g[g["v"] > 1e9]
    fig, ax = plt.subplots(figsize=(14.2, 6.2), dpi=100)
    colors = [brand.ORANGE if i == "Direct contracting" else brand.BLUE for i in g.index]
    bars = ax.barh(g.index, g["v"] / 1e9, color=colors, height=0.55)
    for b, (name, row) in zip(bars, g.iterrows()):
        share = 100 * row["n"] / len(f)
        ax.text(b.get_width() + 40, b.get_y() + b.get_height() / 2,
                f"COP {row['v'] / 1e12:.2f} tn · {share:.1f}% of contracts" if row["v"] >= 1e12 else
                f"COP {row['v'] / 1e9:,.0f} bn · {share:.1f}%",
                va="center", fontsize=16, color=brand.INK)
    ax.set_title("Contract value by procurement method, 2025", fontsize=21, loc="left", pad=14)
    ax.tick_params(axis="y", labelsize=17)
    ax.tick_params(axis="x", labelsize=14)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("COP billions", fontsize=14, color=brand.INK_2)
    ax.set_xlim(0, g["v"].max() / 1e9 * 1.55)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def star_schema_html(out: Path) -> None:
    pbi = PROJECT / "powerbi" / "data"
    tables = {name: pd.read_csv(pbi / f"{name}.csv", nrows=1).columns.tolist()
              for name in ("fact_contracts", "dim_entity", "dim_date", "dim_modality", "dim_contract_type", "dim_status")}
    rows = {name: sum(1 for _ in open(pbi / f"{name}.csv", encoding="utf-8")) - 1 for name in tables}

    def box(name: str, cls: str) -> str:
        cols = "".join(f"<li class='{'key' if c.endswith('_key') or c in ('date', 'date_signed') else ''}'>"
                       f"{html.escape(c)}</li>" for c in tables[name])
        return (f"<div class='tbl {cls}' id='{name}'><h3>{name}</h3><p>{rows[name]:,} rows</p><ul>{cols}</ul></div>")

    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face {{ font-family: Inter; src: url('file://{brand.FONTS["regular"]}'); }}
    @font-face {{ font-family: Inter; font-weight: 700; src: url('file://{brand.FONTS["bold"]}'); }}
    body {{ margin: 0; background: {brand.SURFACE}; font-family: Inter, sans-serif; color: {brand.INK}; }}
    .canvas {{ position: relative; width: 1400px; height: 900px; }}
    h1 {{ position: absolute; left: 36px; top: 18px; margin: 0; font-size: 26px; color: {brand.BRAND}; }}
    .sub {{ position: absolute; left: 36px; top: 58px; margin: 0; font-size: 15px; color: {brand.INK_2}; }}
    .tbl {{ position: absolute; background: #fff; border: 1.5px solid {brand.AXIS}; border-radius: 12px;
            padding: 10px 14px; box-shadow: 0 4px 14px rgba(13,54,107,.08); }}
    .tbl h3 {{ margin: 0; font-size: 16px; }} .tbl p {{ margin: 2px 0 6px; font-size: 12px; color: {brand.MUTED}; }}
    .tbl ul {{ margin: 0; padding: 0; list-style: none; font: 12.5px/1.5 'JetBrains Mono', monospace; color: {brand.INK_2}; }}
    .tbl li.key {{ color: {brand.BRAND}; font-weight: 700; }}
    .fact {{ left: 520px; top: 200px; width: 330px; border: 2px solid {brand.BLUE}; }}
    .fact h3 {{ color: {brand.BLUE}; }}
    #dim_entity {{ left: 40px; top: 110px; width: 280px; }}
    #dim_date {{ left: 1060px; top: 110px; width: 260px; }}
    #dim_modality {{ left: 40px; top: 560px; width: 280px; }}
    #dim_contract_type {{ left: 1060px; top: 560px; width: 280px; }}
    #dim_status {{ left: 1060px; top: 370px; width: 260px; }}
    svg {{ position: absolute; left: 0; top: 0; }}
    </style></head><body><div class="canvas">
    <h1>Power BI kit: star schema</h1>
    <p class="sub">1 fact table (one row per contract) and 5 dimensions · CSV files ready to load · relationships many-to-one</p>
    <svg width="1400" height="900" id="lines"></svg>
    {box("fact_contracts", "fact")}{box("dim_entity", "")}{box("dim_date", "")}{box("dim_modality", "")}
    {box("dim_contract_type", "")}{box("dim_status", "")}
    </div><script>
    const svg = document.getElementById('lines');
    const c = (id) => {{ const r = document.getElementById(id).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }};
    const [fx, fy] = c('fact_contracts');
    ['dim_entity', 'dim_date', 'dim_modality', 'dim_contract_type', 'dim_status'].forEach((id) => {{
      const [x, y] = c(id);
      const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      l.setAttribute('x1', fx); l.setAttribute('y1', fy); l.setAttribute('x2', x); l.setAttribute('y2', y);
      l.setAttribute('stroke', '{brand.BLUE_RAMP[4]}'); l.setAttribute('stroke-width', '2.5');
      svg.appendChild(l);
    }});
    </script></body></html>"""
    out.write_text(page, encoding="utf-8")


def dax_html(out: Path) -> None:
    text = (PROJECT / "powerbi" / "dax_measures.md").read_text()
    blocks = re.findall(r"### \d+\. (.+?)\n```DAX\n(.+?)```", text, flags=re.S)
    keep = [b for b in blocks if b[0] in ("Direct Contracting % (contracts)", "Value MoM %", "Entity Rank by Value",
                                          "Paid % of Value")]
    cards = "".join(f"<div class='m'><h3>{html.escape(n)}</h3><pre>{html.escape(code.strip())}</pre></div>"
                    for n, code in keep)
    names = "".join(f"<li>{html.escape(n)}</li>" for n, _ in blocks)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face {{ font-family: Inter; src: url('file://{brand.FONTS["regular"]}'); }}
    @font-face {{ font-family: Inter; font-weight: 700; src: url('file://{brand.FONTS["bold"]}'); }}
    body {{ margin: 0; padding: 26px 34px; background: {brand.SURFACE}; font-family: Inter, sans-serif; color: {brand.INK}; }}
    h1 {{ margin: 0 0 4px; font-size: 26px; color: {brand.BRAND}; }} .sub {{ margin: 0 0 18px; color: {brand.INK_2}; font-size: 15px; }}
    .wrap {{ display: grid; grid-template-columns: 300px 1fr; gap: 24px; }}
    ol {{ margin: 0; padding-left: 22px; font-size: 15px; line-height: 1.9; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .m h3 {{ margin: 0 0 6px; font-size: 15px; }}
    pre {{ margin: 0; background: #0f1b2d; color: #e6edf6; font: 12.5px/1.5 'JetBrains Mono', monospace; padding: 12px;
          border-radius: 10px; white-space: pre-wrap; }}
    </style></head><body><h1>Power BI kit: 12 DAX measures, explained</h1>
    <p class="sub">Copy-paste ready (powerbi/dax_measures.md) · step-by-step build guide · expected values to check the model</p>
    <div class="wrap"><ol>{names}</ol><div class="grid">{cards}</div></div></body></html>"""
    out.write_text(page, encoding="utf-8")


def phone_strip(shots: list[Path], out: Path) -> Path:
    ims = [Image.open(s) for s in shots]
    h = max(i.height for i in ims)
    gap = 40
    canvas = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), brand.PAGE)
    x = 0
    for im in ims:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    canvas.save(out)
    return out


def main(f: pd.DataFrame, vals: dict, meta: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p2up_"))
    cover_chart(f, tmp / "cover_chart.png")
    make_cover(UP / "cover.png", 2, "Dashboards & BI", "Procurement Dashboard",
               f"Colombia, education sector 2025: {len(f):,} public contracts, interactive + Power BI kit",
               tmp / "cover_chart.png", "Python · Plotly · Power BI")

    make_shot(UP / "shot-1.png", shoot(DASH, tmp / "d1.png", 1280, 960, "--scale", "1.5"),
              "Interactive dashboard: filters, KPI tiles and charts")
    make_shot(UP / "shot-2.png", shoot(DASH, tmp / "d2.png", 1280, 960, "--scale", "1.5", "--select", "#fDept=Antioquia"),
              "One click: the same dashboard filtered to Antioquia")
    phones = [shoot(DASH, tmp / f"m{i}.png", 390, 844, "--scale", "2", *(["--scrollto", sel] if sel else []))
              for i, sel in enumerate((None, ".tiles", ".table-card"))]
    make_shot(UP / "shot-3.png", phone_strip(phones, tmp / "phones.png"), "Works on a phone (390 px wide)")
    star_schema_html(tmp / "star.html")
    make_shot(UP / "shot-4.png", shoot(tmp / "star.html", tmp / "star.png", 1400, 900, "--scale", "1.5"),
              "Power BI kit: star schema as CSV files")
    dax_html(tmp / "dax.html")
    make_shot(UP / "shot-5.png", shoot(tmp / "dax.html", tmp / "dax.png", 1400, 900, "--scale", "1.5"),
              "Power BI kit: 12 DAX measures and a build guide")

    title = "Interactive Procurement Dashboard + Power BI"
    desc = (
        "Public-sector teams need to see where contracting money goes. I pulled "
        f"{len(f):,} education-sector contracts signed in 2025 from Colombia's SECOP II open-data API, "
        "modelled them as a star schema and built a one-page interactive dashboard (Python, Plotly.js) with "
        "filters, KPI tiles and 6 charts that work on a phone, plus a Power BI kit with 12 DAX measures. "
        f"Finding: {vals['Direct Contracting % (contracts)']} of contracts were direct awards. "
        "Sample project built with public data."
    )
    skills = ["Dashboard", "Data Visualization", "Microsoft Power BI", "Python", "Data Analysis"]
    captions = [
        f"One-page dashboard on {len(f):,} contracts worth COP {f['contract_value'].sum() / 1e12:.2f} trillion. "
        "Seven filters (month, entity level, department, method, type, supplier) update every KPI, chart and table.",
        "The same page filtered to Antioquia (28,552 contracts, 97.9% direct awards). Numbers are recalculated in "
        "the browser, and an automated test checks them against pandas.",
        "Responsive layout: on a phone the filters, tiles and charts stack in one column, with no horizontal scrolling.",
        "Power BI kit: one fact table (one row per contract) and five dimensions as clean CSV files, with the "
        "relationships described step by step.",
        "Twelve DAX measures (CALCULATE, DIVIDE, TOTALYTD, DATEADD, RANKX) with explanations, a Spanish build guide "
        "and the expected values to check the model.",
    ]
    links = [f"Live dashboard (GitHub Pages): {config.PAGES_URL}/procurement-dashboard/",
             f"GitHub project folder: {config.folder_url(FOLDER)}",
             f"DAX measures: {config.file_url(FOLDER + '/powerbi/dax_measures.md')}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
