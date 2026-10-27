"""Build the GitHub Pages site (docs/) and PORTAFOLIO_UPWORK.md from the eight project folders.

    python build_site.py

- docs/index.html            landing page with the eight projects
- docs/survey-report/        project 05 report (HTML), docs/churn-report/ project 06 report (HTML)
- docs/assets/               covers (resized) and the Inter font
- PORTAFOLIO_UPWORK.md       every Upwork text ready to copy, with the files to upload in order
Run it after the projects' own run.py (it only copies and lists what they produced).
"""
from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
import brand  # noqa: E402
import config  # noqa: E402
from upwork import check_package  # noqa: E402

DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
PROJECTS = [
    {"folder": "01-excel-kpi-report", "service": "Excel reporting",
     "line": "1.07 million invoice lines turned into a live Excel KPI dashboard with a period selector: "
             "44,001 formulas, 0 errors.",
     "main": ("Download the Excel file", config.file_url("01-excel-kpi-report/output/ecommerce_kpi_report.xlsx"))},
    {"folder": "02-procurement-dashboard", "service": "Dashboards and Power BI",
     "line": "60,902 public contracts in one interactive page with filters, plus a Power BI star schema and "
             "12 DAX measures.",
     "main": ("Open the live dashboard", "procurement-dashboard/")},
    {"folder": "03-data-cleaning", "service": "Data cleaning",
     "line": "4,164 messy supplier records cleaned, deduplicated and checked against the business registry, "
             "with a before/after report.",
     "main": ("Read the quality report (PDF)", config.file_url("03-data-cleaning/output/quality_report.pdf"))},
    {"folder": "04-b2b-lead-list", "service": "Data collection",
     "line": "300 Colombian universities and colleges from the official registry, phones normalised and every "
             "website checked.",
     "main": ("Browse the lead list", config.file_url("04-b2b-lead-list/output/colombia_higher_ed_leads.csv"))},
    {"folder": "05-survey-analysis", "service": "Statistical analysis",
     "line": "A national survey analysed with design-based estimates, chi-square tests and a logistic regression "
             "with its assumptions checked.",
     "main": ("Read the report", "survey-report/")},
    {"folder": "06-churn-prediction", "service": "Predictive analytics",
     "line": "Customer churn model compared and cross-validated without leakage, with a one-page action plan.",
     "main": ("Read the report", "churn-report/")},
    {"folder": "07-economic-brief", "service": "Economic research",
     "line": "Colombia's minimum wage against inflation, productivity and other countries, in a 4-page brief "
             "from official data.",
     "main": ("Read the brief (PDF)", config.file_url("07-economic-brief/output/colombia_minimum_wage_brief.pdf"))},
    {"folder": "08-ai-pdf-to-excel", "service": "AI automation",
     "line": "Synthetic invoice PDFs read, checked and loaded into Excel with an error log; optional AI step for "
             "scanned files.",
     "main": ("See it run", config.file_url("08-ai-pdf-to-excel/output/pipeline_run.gif"))},
]
REPORT_PAGES = {"survey-report": ROOT / "05-survey-analysis" / "output" / "report.html",
                "churn-report": ROOT / "06-churn-prediction" / "output" / "churn_report.html"}
EXTRA_FILES = {"06-churn-prediction": "one-pager.pdf", "07-economic-brief": "research-brief.pdf"}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def copy_reports() -> None:
    for name, src in REPORT_PAGES.items():
        out = DOCS / name / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        text = read(src).replace("../../common/fonts/Inter-Regular.ttf", "../assets/Inter-Regular.ttf")
        if "../../" in text:
            raise SystemExit(f"{src} still points outside docs/")
        out.write_text(text, encoding="utf-8")


def covers() -> None:
    (ASSETS / "covers").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(brand.FONTS["regular"], ASSETS / "Inter-Regular.ttf")
    shutil.copyfile(brand.FONTS["bold"], ASSETS / "Inter-Bold.ttf")
    for p in PROJECTS:
        im = Image.open(ROOT / p["folder"] / "upwork" / "cover.png").convert("RGB")
        im.thumbnail((800, 600))
        im.save(ASSETS / "covers" / f"{p['folder'][:2]}.jpg", quality=86, optimize=True)


def landing() -> None:
    cards = []
    for p in PROJECTS:
        title = read(ROOT / p["folder"] / "upwork" / "title.txt")
        label, url = p["main"]
        cards.append(f"""
      <article class="card">
        <a href="{url}"><img src="assets/covers/{p['folder'][:2]}.jpg" alt="{html.escape(title)}: cover image"
           width="800" height="600" loading="lazy"></a>
        <div class="body">
          <p class="kicker">Project {p['folder'][:2]} · {html.escape(p['service'])}</p>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(p['line'])}</p>
          <p class="links"><a class="primary" href="{url}">{html.escape(label)}</a>
             <a href="{config.folder_url(p['folder'])}">Code and files</a></p>
        </div>
      </article>""")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Portfolio · {config.AUTHOR}</title>
<meta name="description" content="Eight sample data projects built with public data: Excel, dashboards, data cleaning, lead lists, statistics, machine learning, economic research and AI automation.">
<style>
  @font-face {{ font-family: Inter; src: url('assets/Inter-Regular.ttf'); font-weight: 400; }}
  @font-face {{ font-family: Inter; src: url('assets/Inter-Bold.ttf'); font-weight: 700; }}
  :root {{ --page: {brand.PAGE}; --surface: #ffffff; --ink: {brand.INK}; --ink-2: {brand.INK_2};
          --line: {brand.GRID}; --brand: {brand.BRAND}; --accent: {brand.BRAND_2}; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --page: #10141b; --surface: #171c25; --ink: #eef1f5; --ink-2: #a9b1bd; --line: #2a3140;
            --brand: #9ec5f4; --accent: #86b6ef; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--page); color: var(--ink); font: 16px/1.55 Inter, system-ui, sans-serif; }}
  header, main, footer {{ max-width: 1120px; margin: 0 auto; padding: 0 16px; }}
  header {{ padding-top: 48px; padding-bottom: 8px; }}
  .bar {{ height: 6px; background: {brand.BRAND}; }}
  h1 {{ font-size: clamp(28px, 5vw, 44px); line-height: 1.15; margin: 0 0 10px; color: var(--brand); }}
  header p {{ color: var(--ink-2); max-width: 760px; margin: 0 0 6px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 28px 0; }}
  .card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
          display: flex; flex-direction: column; }}
  .card img {{ width: 100%; height: auto; display: block; border-bottom: 1px solid var(--line); }}
  .body {{ padding: 14px 16px 16px; display: flex; flex-direction: column; flex: 1; }}
  .kicker {{ margin: 0; font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--accent);
            font-weight: 700; }}
  h2 {{ font-size: 19px; line-height: 1.3; margin: 6px 0 6px; }}
  .body p {{ margin: 0 0 10px; color: var(--ink-2); font-size: 15px; }}
  .links {{ margin-top: auto !important; display: flex; gap: 14px; flex-wrap: wrap; }}
  a {{ color: var(--accent); }}
  a.primary {{ font-weight: 700; }}
  footer {{ color: var(--ink-2); font-size: 14px; padding-bottom: 40px; border-top: 1px solid var(--line);
           padding-top: 16px; }}
</style>
</head>
<body>
<div class="bar"></div>
<header>
  <h1>Data Portfolio</h1>
  <p><strong>{config.AUTHOR}</strong> · Data analyst · Bogotá, Colombia</p>
  <p>Eight sample projects, each built with public data, from the raw download to the deliverable a client
  receives. Every project rebuilds with one command and documents its sources and licences.</p>
</header>
<main>
  <section class="grid">{''.join(cards)}
  </section>
</main>
<footer>
  <p>Sample projects built with public data. The invoices in project 08 are synthetic and marked as such.
  Sources, licences and code: <a href="{config.REPO_URL}">{config.REPO_URL.replace('https://', '')}</a>.</p>
</footer>
</body>
</html>
"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")


def upwork_md() -> None:
    out = ["# Portafolio Upwork: textos listos para copiar", "",
           "Este archivo se genera con `python build_site.py` a partir de la carpeta `upwork/` de cada proyecto. "
           "Si cambias un texto, cámbialo en el `make_upwork.py` del proyecto y vuelve a correr ese proyecto.", "",
           "**Cómo subir cada proyecto en Upwork:** Perfil → *Portfolio* → *Add a project*. Copia el título, la "
           "descripción y las 5 skills. En *Content*, sube primero `cover.png` (Upwork la usa como miniatura) y "
           "luego las capturas en el orden indicado; si Upwork te deja escribir un texto debajo de cada imagen, "
           "usa el caption. Agrega los links como bloque de link o al final de la descripción. Todos los archivos "
           "están en la carpeta `upwork/` del proyecto. En *Your role* puedes poner: *Data analyst (sample project)*.",
           "", "Orden sugerido para publicar: 02, 01, 03, 08, 06, 05, 04, 07 (los más visuales primero).", ""]
    for p in PROJECTS:
        up = ROOT / p["folder"] / "upwork"
        problems = check_package(up)
        if problems:
            raise SystemExit(f"{p['folder']}: {problems}")
        title, desc = read(up / "title.txt"), read(up / "description.txt")
        skills = read(up / "skills.txt").splitlines()
        caps = [ln.split(": ", 1) for ln in read(up / "captions.txt").splitlines()]
        out += [f"## Proyecto {p['folder'][:2]} · {p['service']}", "",
                f"**Título** ({len(title)}/50 caracteres)", "", "```text", title, "```", "",
                f"**Descripción** ({len(desc)}/500 caracteres)", "", "```text", desc, "```", "",
                "**Skills** (copia una por una)", "", "```text", "\n".join(skills), "```", "",
                "**Imágenes, en este orden** (carpeta `" + p["folder"] + "/upwork/`)", "",
                "1. `cover.png`: portada (sin caption)."]
        out += [f"{k}. `{name}`: {text}" for k, (name, text) in enumerate(caps, start=2)]
        if p["folder"] in EXTRA_FILES:
            out += ["", f"**Archivo adicional:** `{EXTRA_FILES[p['folder']]}` (súbelo como PDF si Upwork lo permite)."]
        out += ["", "**Links**", "", "```text", read(up / "links.txt"), "```", ""]
    (ROOT / "PORTAFOLIO_UPWORK.md").write_text("\n".join(out), encoding="utf-8")


def check_links() -> None:
    """Every relative link in docs/index.html must exist inside docs/."""
    text = read(DOCS / "index.html")
    for href in re.findall(r'(?:href|src)="([^"]+)"', text):
        if href.startswith(("http", "#", "mailto:")):
            continue
        target = DOCS / href
        if href.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            raise SystemExit(f"Broken link in docs/index.html: {href}")


def main() -> None:
    copy_reports()
    covers()
    landing()
    upwork_md()
    check_links()
    size = sum(f.stat().st_size for f in DOCS.rglob("*") if f.is_file())
    print(f"docs/ built ({size / 1e6:.1f} MB): index.html, {', '.join(REPORT_PAGES)}, procurement-dashboard")
    print("PORTAFOLIO_UPWORK.md written")


if __name__ == "__main__":
    main()
