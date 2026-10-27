"""Upwork package for project 04."""
from __future__ import annotations

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
from xlsx_values import lo_recalc  # noqa: E402

import outputs  # noqa: E402

UP = PROJECT / "upwork"
FOLDER = "04-b2b-lead-list"


def status_groups(leads: pd.DataFrame) -> pd.Series:
    s = leads["website_status"]
    g = pd.Series("Not verified from our server", index=s.index)
    g[s.str.startswith("Online") & ~s.str.contains("blocks")] = "Online (verified)"
    g[s.str.contains("blocks")] = "Online, blocks bots"
    g[s.str.startswith("Site error")] = "Site error (4xx/5xx)"
    g[s.str.startswith("No website")] = "No website listed"
    return g


def cover_chart(leads: pd.DataFrame, path: Path) -> None:
    brand.apply_mpl_style()
    order = ["Online (verified)", "Online, blocks bots", "Not verified from our server", "Site error (4xx/5xx)",
             "No website listed"]
    colors = {"Online (verified)": brand.GOOD, "Online, blocks bots": brand.BLUE,
              "Not verified from our server": brand.WARNING, "Site error (4xx/5xx)": brand.CRITICAL,
              "No website listed": brand.AXIS}
    vc = status_groups(leads).value_counts().reindex(order).fillna(0).astype(int)
    vc = vc[vc > 0]
    fig, ax = plt.subplots(figsize=(14.2, 6.0), dpi=100)
    bars = ax.barh(vc.index, vc.values, color=[colors[k] for k in vc.index], height=0.56)
    for b, v in zip(bars, vc.values):
        ax.text(b.get_width() + 3, b.get_y() + b.get_height() / 2, f"{v}  ({100 * v / len(leads):.0f}%)",
                va="center", fontsize=17, color=brand.INK)
    ax.invert_yaxis()
    ax.set_xlim(0, vc.max() * 1.25)
    ax.tick_params(axis="y", labelsize=17)
    ax.tick_params(axis="x", labelsize=13)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title(f"Website check of {len(leads)} institutions (robots.txt respected)", fontsize=21, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def trim(path: Path, out: Path, pad: int = 40) -> Path:
    im = Image.open(path).convert("RGB")
    bbox = im.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox()
    if bbox:
        im = im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad),
                      min(im.height, bbox[3] + pad)))
    im.save(out)
    return out


def md_to_png(md_text: str, tmp: Path, name: str, width: int = 1300, height: int = 980) -> Path:
    css = tmp / "style.css"
    css.write_text(f"""
      @font-face {{ font-family: Inter; src: url('file://{brand.FONTS["regular"]}'); }}
      @font-face {{ font-family: Inter; font-weight: 700; src: url('file://{brand.FONTS["bold"]}'); }}
      body {{ font-family: Inter, sans-serif; color: {brand.INK}; background: {brand.SURFACE}; max-width: none;
             margin: 0; padding: 26px 34px; font-size: 15px; line-height: 1.5; }}
      h1 {{ font-size: 24px; color: {brand.BRAND}; margin: 0 0 8px; }}
      h2 {{ font-size: 17px; color: {brand.BRAND}; margin: 16px 0 4px; }}
      ul {{ margin: 4px 0; padding-left: 22px; }} li {{ margin: 2px 0; }}
      pre, code {{ font-family: 'JetBrains Mono', monospace; font-size: 12.5px; }}
      pre {{ background: #0f1b2d; color: #e6edf6; padding: 14px; border-radius: 10px; line-height: 1.45; }}
      pre code span {{ color: inherit !important; }}
      header, #title-block-header {{ display: none; }}
    """)
    (tmp / f"{name}.md").write_text(md_text, encoding="utf-8")
    subprocess.run(["pandoc", str(tmp / f"{name}.md"), "-s", "--metadata", "title=doc", "-c", str(css),
                    "-o", str(tmp / f"{name}.html")], check=True)
    out = tmp / f"{name}.png"
    subprocess.run(["node", str(COMMON / "screenshot.js"), str(tmp / f"{name}.html"), str(out), str(width),
                    str(height), "--scale", "1.5"], check=True, capture_output=True)
    return out


def main(leads: pd.DataFrame, res: dict, run_date: str) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p4up_"))
    groups = status_groups(leads).value_counts()
    cover_chart(leads, tmp / "cover_chart.png")
    make_cover(UP / "cover.png", 4, "Data collection", "Verified B2B Lead List",
               f"{len(leads)} Colombian universities and colleges: official registry + website check",
               tmp / "cover_chart.png", "Python · APIs · Google Sheets")

    lo_recalc(outputs.XLSX, tmp / "v.xlsx", pdf=tmp / "x.pdf", sheets=["Summary", "Leads"],
              one_page=["Summary", "Leads"], areas={"Summary": "A1:F47", "Leads": "A1:G50"})
    subprocess.run(["pdftoppm", "-r", "300", "-png", str(tmp / "x.pdf"), str(tmp / "x")], check=True)
    pages = sorted(tmp.glob("x-*.png"))
    make_shot(UP / "shot-1.png", trim(pages[1], tmp / "leads.png"), "The lead list: one row per institution")
    make_shot(UP / "shot-2.png", trim(pages[0], tmp / "summary.png"), "Summary sheet: verification results")
    method = outputs.METHOD.read_text(encoding="utf-8")
    method_short = method.split("## Reading the status column")[0]
    make_shot(UP / "shot-3.png", md_to_png(method_short, tmp, "method", 1100, 820), "Method: sources, steps and respectful checks")
    code = (PROJECT / "src" / "verify.py").read_text()
    snippet = code[code.index("def check("):code.index("    # 2) home page")]
    make_shot(UP / "shot-4.png", md_to_png("# Website check: robots.txt first, then one request\n\n```python\n"
                                           + snippet.strip() + "\n```\n", tmp, "code", 960, 690),
              "The verification script (Python, requests)")

    online = int(groups.get("Online (verified)", 0) + groups.get("Online, blocks bots", 0))
    title = "Verified B2B Lead List from Official Sources"
    desc = (
        "Sales teams need lead lists they can trust. I built a list of all "
        f"{len(leads)} Colombian higher-education institutions from the Ministry of Education's open registry, "
        "enriched it with enrolment figures and Wikidata, normalised phones and checked every website with a "
        "respectful Python script (robots.txt, pauses, no crawling). Result: a Google Sheets-ready file with "
        f"source, check date and status per row; {online} sites answered. "
        "Sample project built with public data."
    )
    skills = ["Lead Generation", "Data Mining", "Web Scraping", "Python", "Google Sheets"]
    captions = [
        "One row per institution: city, phone in +57 format, verified website and status, check date, sector, type, "
        "accreditation, enrolment and the source of every value. CSV (UTF-8) for Google Sheets plus Excel.",
        f"Summary of the website check: {int(groups.get('Online (verified)', 0))} online, "
        f"{int(groups.get('Online, blocks bots', 0))} online but blocking bots, "
        f"{int(groups.get('Not verified from our server', 0))} not reachable from the checking server (to re-check "
        "locally), by sector, type and department.",
        "Method summary: official sources and licences, each step with its count, and how the check respects "
        "robots.txt, uses pauses and never crawls beyond the home page.",
        "The core of the verification script: a descriptive User-Agent, robots.txt checked before any page request, "
        "and a pause between requests to the same site.",
    ]
    links = [f"GitHub project folder: {config.folder_url(FOLDER)}",
             f"Lead list (CSV): {config.file_url(FOLDER + '/output/colombia_higher_ed_leads.csv')}",
             f"Method: {config.file_url(FOLDER + '/output/METHOD.md')}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
