"""One command to rebuild project 07:  python run.py

1. Download the official series (DANE, ILOSTAT, World Bank, OECD)   -> data/raw/, data/clean/sources_accessed.json
2. Process them into tidy tables and the figures quoted in the brief -> data/clean/
3. Draw the four charts                                              -> output/figures/
4. Write the 4-page PDF brief                                         -> output/colombia_minimum_wage_brief.pdf
5. Upwork package                                                    -> upwork/
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))

import brief  # noqa: E402
import charts  # noqa: E402
import download  # noqa: E402
import make_upwork  # noqa: E402
import process  # noqa: E402


def check_pdf(pdf: Path, r: dict) -> None:
    pages = int(next(line.split()[-1] for line in subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                                                                text=True).stdout.splitlines()
                     if line.startswith("Pages:")))
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    problems = []
    if not 3 <= pages <= 4:
        problems.append(f"{pages} pages (expected 3-4)")
    for needed in ("Executive summary", "Context", "Limitations", "Sources", "Sample project built with public data",
                   f"{r['oecd_col']:.1f}%", f"{r['wage_end']:,}"):
        if needed not in text:
            problems.append(f"missing text: {needed}")
    if "nan" in text.lower().split():
        problems.append("a 'nan' value is printed")
    print(f"  brief: {pages} pages, problems: {problems or 'none'}")
    if problems:
        raise SystemExit("Brief check failed")


def main() -> None:
    print("[1/5] Download")
    for k, v in download.main().items():
        print(f"  {k:20s} accessed {v['accessed']}")
    print("[2/5] Process")
    r = process.main()
    print(f"  real minimum wage {r['start']}-{r['end']}: +{r['real_growth_pct']}%; productivity "
          f"+{r['productivity_growth_pct']}%; minimum/median {r['oecd_col']}% ({r['oecd_year']})")
    print("[3/5] Charts")
    charts.main()
    print("[4/5] Brief")
    check_pdf(brief.build(), r)
    print("[5/5] Upwork package")
    make_upwork.main(r)
    print("Done.")


if __name__ == "__main__":
    main()
