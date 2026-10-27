"""One command to rebuild project 05:  python run.py

1. Download the GSS 2024 microdata (Stata) + codebook from gss.norc.org  -> data/raw/ (not in git)
2. Convert analysis/analysis.py (percent-format cells) into a notebook and execute it
3. Export the report: HTML without code (for clients), HTML with code, and PDF
4. Upwork package
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT.parent / "common"))
sys.path.insert(0, str(PROJECT / "src"))
import notebook_tools as nbt  # noqa: E402
from fetch_utils import fetch  # noqa: E402

import make_upwork  # noqa: E402

RAW = PROJECT / "data" / "raw"
OUT = PROJECT / "output"
URL = "https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/2024_stata.zip"


def download() -> None:
    if (RAW / "GSS2024.dta").exists():
        return
    z = fetch(URL, RAW / "2024_stata.zip", min_bytes=4_000_000)
    with zipfile.ZipFile(z) as zf:
        for name in zf.namelist():
            if name.endswith((".dta", ".pdf")):
                (RAW / Path(name).name).write_bytes(zf.read(name))


def main() -> None:
    print("[1/4] Data")
    download()
    print("[2/4] Execute the analysis notebook")
    nb = nbt.execute(nbt.py_to_notebook(PROJECT / "analysis" / "analysis.py"), PROJECT / "analysis")
    nbformat.write(nb, PROJECT / "analysis" / "analysis.ipynb")
    print("[3/4] Report: HTML (no code), HTML (with code), PDF")
    OUT.mkdir(exist_ok=True)
    for name, code in (("report.html", False), ("report_with_code.html", True)):
        nbt.export_html(nb, OUT / name, "GSS 2024 Happiness Report", code, "../../common/fonts/Inter-Regular.ttf")
    subprocess.run(["node", str(PROJECT / "src" / "html_to_pdf.js"), str(OUT / "report.html"),
                    str(OUT / "report.pdf")], check=True)
    results = json.loads((OUT / "results.json").read_text())
    print(f"  very happy: {results['very_happy']['p']:.3f}; model n={results['model_n']}; AUC={results['auc']:.2f}")
    print("[4/4] Upwork package")
    make_upwork.main(results)
    print("Done.")


if __name__ == "__main__":
    main()
