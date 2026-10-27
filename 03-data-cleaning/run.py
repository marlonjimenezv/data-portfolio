"""One command to rebuild project 03:  python run.py

1. Unit tests for the cleaning rules (tests/test_rules.py)
2. Download SECOP II suppliers (Boyacá), RUES matches and DANE codes   -> data/raw/ (not in git)
3. Clean, deduplicate, validate, cross-check, apply privacy rules     -> data/clean/
4. Excel workbook + 2-page PDF quality report                         -> output/
5. Privacy check on the published files
6. Upwork package                                                     -> upwork/
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT.parent / "common"))

import build_outputs  # noqa: E402
import clean  # noqa: E402
import make_upwork  # noqa: E402
import rules  # noqa: E402


def privacy_check(res: dict) -> None:
    """Fail if a published file contains an unmasked personal-looking e-mail, a full mobile number or a personal ID."""
    c = res["clean"]
    bad_mobile = c["phone"].str.fullmatch(r"\+57 3\d{2} \d{3} \d{4}")
    full_emails = c["email"].str.contains("@") & ~c["email"].str.contains(r"\*")
    unmasked_personal = [e for e, n in zip(c.loc[full_emails, "email"], c.loc[full_emails, "name"])
                         if not rules.is_organisational_email(e, n)]
    personal_ids = c["nit"].str.fullmatch(r"1\d{9}") | c["nit_status"].str.startswith("personal")
    person_names = c["name"].map(rules.looks_like_person_name) & (c["name_in_registry"] == "")
    issues_text = " ".join(res["issues"]["value_shown"].astype(str))
    leaked_mobile = re.search(r"\b3\d{9}\b", issues_text)
    problems = {"full mobile numbers": int(bad_mobile.sum()), "unmasked personal e-mails": len(unmasked_personal),
                "personal ID numbers": int(personal_ids.sum()), "person-like names": int(person_names.sum()),
                "mobile numbers in the issues table": int(bool(leaked_mobile))}
    print("  privacy check:", problems)
    if any(problems.values()):
        raise SystemExit("Privacy check failed")


def main() -> None:
    print("[1/6] Unit tests")
    subprocess.run([sys.executable, str(PROJECT / "tests" / "test_rules.py")], check=True)
    print("[2-3/6] Download, clean, validate, cross-check")
    res = clean.run()
    print(res["steps"][["step", "rule", "affected", "unit", "rows_after"]].to_string(index=False))
    print(res["quality"].to_string(index=False))
    print("[4/6] Excel + PDF report")
    s = build_outputs.summary_numbers(res)
    build_outputs.build_excel(res, s)
    build_outputs.build_pdf(res, s)
    pages = subprocess.run(["pdfinfo", str(build_outputs.PDF)], capture_output=True, text=True).stdout
    n_pages = int(re.search(r"Pages:\s+(\d+)", pages).group(1))
    print(f"  PDF pages: {n_pages}")
    if n_pages != 2:
        raise SystemExit("The quality report must have exactly 2 pages")
    print("[5/6] Privacy check")
    privacy_check(res)
    pd.DataFrame([s]).T.rename(columns={0: "value"}).to_csv(PROJECT / "data" / "clean" / "summary.csv")
    print("[6/6] Upwork package")
    make_upwork.main(res, s)
    print("Done.")


if __name__ == "__main__":
    main()
