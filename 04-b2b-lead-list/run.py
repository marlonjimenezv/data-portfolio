"""One command to rebuild project 04:  python run.py  [--refresh]

1. Download the MEN registry, MEN enrolment figures and Wikidata websites  -> data/raw/ (not in git)
2. Verify every website (robots.txt, pauses, cached)                       -> data/clean/website_checks.json
3. Build the lead list                                                     -> output/*.csv, *.xlsx, METHOD.md
4. Checks: row count, required columns, no personal data, statuses
5. Upwork package                                                          -> upwork/
--refresh re-checks the websites instead of using the cached results.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT.parent / "common"))

import build  # noqa: E402
import make_upwork  # noqa: E402
import outputs  # noqa: E402

REQUIRED = ["institution", "nit", "website", "website_status", "verified_at", "source", "website_source"]


def checks(leads: pd.DataFrame) -> None:
    leads = leads.astype(object).where(leads.notna(), "").astype(str)
    problems = []
    if not 150 <= len(leads) <= 300:
        problems.append(f"{len(leads)} rows (expected 150-300)")
    problems += [f"missing column {c}" for c in REQUIRED if c not in leads.columns]
    nits = leads.loc[leads["nit"] != "", "nit"]
    if nits.duplicated().any():
        problems.append("duplicate NITs")
    text = " ".join(leads.agg(" ".join, axis=1))
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        problems.append("an e-mail address is present")
    online = leads["website_status"].str.startswith("Online")
    if (online & (leads["website"] == "")).any() or (~online & (leads["website"] != "")).any():
        problems.append("website column inconsistent with status")
    if (online & (leads["verified_at"] == "")).any():
        problems.append("verified rows without a verification date")
    print(f"  checks: {len(leads)} rows, {int(online.sum())} verified online, problems: {problems or 'none'}")
    if problems:
        raise SystemExit("Checks failed")


def main(refresh: bool = False) -> None:
    print("[1-2/5] Sources and website verification")
    res = build.build(refresh=refresh)
    leads = res["leads"]
    print(res["log"].to_string(index=False))
    print(leads["website_status"].value_counts().to_string())
    run_date = sorted(d[:10] for d in leads["verified_at"] if d)[-1]
    print("[3/5] Outputs")
    outputs.write(leads, res["log"], res["enr_year"], run_date)
    print("[4/5] Checks")
    checks(leads)
    print("[5/5] Upwork package")
    make_upwork.main(leads, res, run_date)
    print("Done.")


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
