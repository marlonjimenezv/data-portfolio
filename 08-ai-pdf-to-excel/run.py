"""One command to run project 08:  python run.py  [--input FOLDER] [--no-ai]

Without --input it first (re)creates the SAMPLE / SYNTHETIC invoices in data/sample_invoices/ and, at the end,
measures accuracy against their answer key and rebuilds the Upwork package. With --input it processes your own
folder of PDFs and writes the same Excel and CSV outputs.

1. Sample invoices (synthetic)            -> data/sample_invoices/
2. Unit tests (rules, checks, AI step with a local fake API)
3. Extract every PDF with pdfplumber + rules
4. Validate (business checks, duplicates)
5. AI step for unreadable invoices: only if ANTHROPIC_API_KEY is set
6. Excel + CSV outputs                     -> output/
7. Accuracy, run log, animated GIF, Upwork package
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "tests"))

import ai_step  # noqa: E402
import extract  # noqa: E402
import outputs  # noqa: E402
import validate  # noqa: E402

LOG: list[str] = []


def say(line: str = "") -> None:
    print(line, flush=True)
    LOG.append(line)


def money(v, cur) -> str:
    if v is None:
        return "-"
    return f"{cur} {v:,.0f}".replace(",", ".") if cur == "COP" else f"{cur} {v:,.2f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=None, help="folder with your own PDF invoices")
    ap.add_argument("--no-ai", action="store_true", help="never call the AI step, even if a key is set")
    args = ap.parse_args()
    demo = args.input is None
    today = date.today()

    say("$ python run.py")
    if demo:
        import make_samples
        key = make_samples.main()
        folder = make_samples.OUT
        say(f"[1/6] Sample invoices: {len(key)} SAMPLE / SYNTHETIC PDFs created")
    else:
        folder = args.input
        say(f"[1/6] Input folder: {folder}")
    import test_pipeline
    say(f"[2/6] Unit tests: {test_pipeline.run_all()} passed")

    pdfs = sorted(folder.glob("*.pdf"))
    say(f"[3/6] Extracting {len(pdfs)} PDFs (pdfplumber + rules)")
    invoices = [extract.extract(p) for p in pdfs]

    say("[4/6] Validating")
    use_ai = ai_step.available(args.no_ai)
    ai_files = []
    seen: dict = {}
    issues_by_file = {}
    for inv in invoices:
        issues = validate.check(inv, seen, today)
        gaps = [i for i in issues if i["check"] in ("no_text", "missing")]
        if gaps and use_ai:
            fields, note = ai_step.ask_claude(folder / inv["file"], extract.read_text(folder / inv["file"]))
            if fields:
                name = inv["file"]
                inv.clear()
                inv.update(ai_step.to_invoice(fields, name))
                ai_files.append(name)
                seen = {k: v for k, v in seen.items() if v != name}     # re-check this file from scratch
                issues = validate.check(inv, seen, today)
            else:
                say(f"  {inv['file']}: {note}")
        inv["issues"] = len(issues)
        inv["status"] = validate.status(issues)
        issues_by_file[inv["file"]] = issues
        n_lines = len(inv["lines"])
        first = issues[0]["problem"] if issues else f"{n_lines} line{'s' if n_lines != 1 else ''}"
        say(f"  {inv['file']:<38} {inv['status']:<6} {money(inv.get('total'), inv.get('currency')):>17}  {first[:58]}")
    issues = [i for f in issues_by_file.values() for i in f]

    if use_ai:
        ai_note = f"run with Claude on {len(ai_files)} file(s): {', '.join(ai_files) or 'none needed'}"
    else:
        ai_note = ("not run (no ANTHROPIC_API_KEY set). Unreadable files stay in the error log for manual entry."
                   if not args.no_ai else "disabled with --no-ai")
    say(f"[5/6] AI step: {ai_note}")

    acc = pd.DataFrame(columns=["field", "correct", "files", "accuracy"])
    if demo:
        key = pd.read_csv(folder / "answer_key.csv", dtype=str, keep_default_na=False)
        key_lines = pd.read_csv(folder / "answer_key_lines.csv")
        acc = outputs.accuracy(invoices, key, key_lines)
    run = {"date": today.isoformat(), "ai_note": ai_note}
    paths = outputs.write(invoices, issues, acc, run)
    n = pd.Series([i["status"] for i in invoices]).value_counts()
    say(f"[6/6] Excel: {paths['xlsx'].relative_to(PROJECT)} | OK {n.get('OK', 0)}, "
        f"flagged {n.get('Review', 0) + n.get('Check', 0)}, error-log rows {len(issues)}")
    if demo:
        say(f"  Accuracy vs answer key: every field correct in at least {int(acc['correct'].min())} of "
            f"{int(acc['files'].iloc[0])} files")
        planted = dict(zip(key["file"], key["planted_issue"]))
        status = {i["file"]: i["status"] for i in invoices}
        missed = [f for f, p in planted.items() if p and status[f] == "OK"]
        false_alarms = [f for f, p in planted.items() if not p and status[f] != "OK"]
        say(f"  Planted problems caught: {sum(1 for p in planted.values() if p) - len(missed)} of "
            f"{sum(1 for p in planted.values() if p)}; clean invoices wrongly flagged: {len(false_alarms)}")
        if missed or false_alarms:
            raise SystemExit(f"Check failed: missed {missed}, false alarms {false_alarms}")
        (PROJECT / "output" / "run_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
        import make_upwork
        make_upwork.main(invoices, issues, acc, LOG)
    say("Done.")


if __name__ == "__main__":
    main()
