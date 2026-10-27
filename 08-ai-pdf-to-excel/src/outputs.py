"""Excel workbook + CSV files, and the accuracy check against the synthetic answer key."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import xlsxwriter

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "output"
XLSX = OUT / "invoices_extracted.xlsx"
INV_COLS = ["status", "issues", "file", "supplier", "invoice_no", "issue_date", "due_date", "currency", "total",
            "subtotal", "tax_rate", "tax", "tax_id", "n_lines", "method"]
LOG_COLS = ["severity", "file", "invoice_no", "supplier", "check", "problem", "found", "action"]
HOW = [
    ("1. Read", "pdfplumber reads the text layer of each PDF. Watermark and stamp characters (large or rotated "
                "glyphs) are dropped first."),
    ("2. Extract", "Regular-expression rules find each field by its label, in English or Spanish (Invoice No / "
                   "Factura de venta No., Date / Fecha de expedición, VAT / IVA ...). Line items come from table rows "
                   "or from 'qty x item @ price = amount' lines; wrapped descriptions are joined."),
    ("3. Normalise", "Amounts in either convention (1.234.567 or 1,234.56) become numbers; five date formats "
                     "become real dates."),
    ("4. Validate", "Required fields, quantity x price per line, lines vs subtotal, subtotal + tax vs total, tax "
                    "rate, due date after issue date, no future dates, no duplicate supplier + invoice number."),
    ("5. AI step (optional)", "Only if the ANTHROPIC_API_KEY environment variable is set: invoices the rules could "
                              "not read (scanned images, missing fields) are sent to Claude, which returns the "
                              "fields as JSON. Its output goes through the same checks and is marked "
                              "'AI (Claude)'. It never edits values that were read correctly."),
    ("6. Output", "This workbook, plus CSV files of invoices, line items and the error log."),
]


def accuracy(invoices: list[dict], key: pd.DataFrame, key_lines: pd.DataFrame) -> pd.DataFrame:
    """Share of files where each extracted field equals the true value in the synthetic answer key."""
    by_file = {i["file"]: i for i in invoices}
    rows = []
    fields = ["supplier", "tax_id", "invoice_no", "issue_date", "due_date", "currency", "subtotal", "tax", "total"]
    for f in fields + ["line items"]:
        ok = 0
        for _, k in key.iterrows():
            inv = by_file.get(k["file"], {})
            if f == "line items":
                truth = key_lines[key_lines["file"] == k["file"]]
                got = inv.get("lines", [])
                ok += len(got) == len(truth) and all(
                    g["description"] == t["description"] and abs((g["qty"] or 0) - t["qty"]) < 1e-9
                    and abs((g["unit_price"] or 0) - t["unit_price"]) < 0.001
                    and abs((g["amount"] or 0) - t["amount"]) < 0.001
                    for g, (_, t) in zip(got, truth.iterrows()))
            elif f in ("subtotal", "tax", "total"):
                ok += inv.get(f) is not None and abs(inv[f] - float(k[f])) < 0.001
            elif f in ("issue_date", "due_date"):
                ok += (inv[f].isoformat() if inv.get(f) else "") == (k[f] if isinstance(k[f], str) else "")
            else:
                ok += (inv.get(f) or "") == k[f]
        rows.append({"field": f, "correct": ok, "files": len(key), "accuracy": ok / len(key)})
    return pd.DataFrame(rows)


def tables(invoices: list[dict], issues: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inv = pd.DataFrame([{**{k: i.get(k) for k in INV_COLS}, "n_lines": len(i["lines"])} for i in invoices])[INV_COLS]
    lines = pd.DataFrame([{"file": i["file"], "invoice_no": i.get("invoice_no"), "supplier": i.get("supplier"),
                           "line": n, **ln, "currency": i.get("currency")}
                          for i in invoices for n, ln in enumerate(i["lines"], start=1)])
    log = pd.DataFrame(issues, columns=LOG_COLS)
    return inv, lines, log


def write(invoices: list[dict], issues: list[dict], acc: pd.DataFrame, run: dict) -> dict[str, Path]:
    OUT.mkdir(exist_ok=True)
    inv, lines, log = tables(invoices, issues)
    paths = {"invoices": OUT / "invoices.csv", "lines": OUT / "line_items.csv", "log": OUT / "error_log.csv"}
    inv.to_csv(paths["invoices"], index=False, encoding="utf-8-sig")
    lines.to_csv(paths["lines"], index=False, encoding="utf-8-sig")
    log.to_csv(paths["log"], index=False, encoding="utf-8-sig")

    wb = xlsxwriter.Workbook(str(XLSX))
    wb.set_properties({"title": "Invoices extracted from PDF (SAMPLE / SYNTHETIC documents)",
                       "author": "Marlon Jiménez Valencia"})
    base = {"font_name": "Calibri", "font_size": 10, "valign": "top"}
    F = {k: wb.add_format({**base, **v}) for k, v in {
        "head": {"bold": True, "font_color": "#FFFFFF", "bg_color": "#0D366B", "text_wrap": True},
        "title": {"font_size": 18, "bold": True, "font_color": "#0D366B"},
        "h2": {"font_size": 12, "bold": True, "font_color": "#0D366B"},
        "muted": {"font_color": "#52514E"}, "wrap": {"text_wrap": True}, "txt": {},
        "kpi": {"font_size": 20, "bold": True, "font_color": "#0D366B", "bg_color": "#EEF4FC"},
        "kpil": {"font_color": "#52514E", "bg_color": "#EEF4FC", "text_wrap": True},
        "money": {"num_format": "#,##0.00"}, "int": {"num_format": "#,##0"}, "pct": {"num_format": "0.0%"},
        "date": {"num_format": "yyyy-mm-dd", "align": "center"}, "center": {"align": "center"}, "warn": {"bold": True, "font_color": "#B42318"},
        "ok": {"bg_color": "#E3F4E3", "font_color": "#006300"}, "check": {"bg_color": "#FFF3D6"},
        "review": {"bg_color": "#FDE4E1", "font_color": "#9B1C1C"}}.items()}

    # Summary
    sm = wb.add_worksheet("Summary")
    sm.hide_gridlines(2)
    sm.set_column(0, 0, 2); sm.set_column(1, 1, 26); sm.set_column(2, 4, 17); sm.set_column(5, 5, 3); sm.set_column(6, 7, 22)
    sm.write(1, 1, "Invoice PDFs → Excel: extraction and validation", F["title"])
    sm.write(2, 1, f"Run on {run['date']} · {len(inv)} PDF files · SAMPLE / SYNTHETIC invoices generated for a "
                   "portfolio project, not real documents", F["muted"])
    counts = inv["status"].value_counts()
    kpis = [(len(inv), "PDF files processed"), (int(counts.get("OK", 0)), "OK: ready to load"),
            (int(counts.get("Review", 0) + counts.get("Check", 0)), "flagged for a person to review"),
            (len(lines), "line items extracted")]
    for j, (v, lbl) in enumerate(kpis):
        sm.write_number(4, 1 + j, v, F["kpi"])
        sm.write(5, 1 + j, lbl, F["kpil"])
    sm.set_row(5, 28)
    sm.write(7, 1, "Problems found by the checks", F["h2"])
    sm.write_row(8, 1, ["Check", "Severity", "Invoices"], F["head"])
    by = (log.groupby(["check", "severity"]).size().reset_index(name="n").sort_values("n", ascending=False)
          if len(log) else pd.DataFrame(columns=["check", "severity", "n"]))
    names = {"no_text": "Scanned image, no text", "missing": "Required field missing", "line_math": "Qty x price ≠ amount",
             "subtotal": "Lines ≠ subtotal", "total": "Subtotal + tax ≠ total", "tax": "Tax ≠ rate x subtotal",
             "dates": "Due date before issue date", "future": "Date in the future", "duplicate": "Duplicate invoice"}
    for r, row in enumerate(by.itertuples(), start=9):
        sm.write(r, 1, names[row.check], F["txt"]); sm.write(r, 2, row.severity, F["txt"])
        sm.write_number(r, 3, row.n, F["int"])
    r = 10 + len(by)
    sm.write(r, 1, "Extraction accuracy against the answer key", F["h2"])
    sm.write_row(r + 1, 1, ["Field", "Correct", "Files", "Accuracy"], F["head"])
    for k, a in enumerate(acc.itertuples(), start=r + 2):
        sm.write(k, 1, a.field, F["txt"]); sm.write_number(k, 2, a.correct, F["int"])
        sm.write_number(k, 3, a.files, F["int"]); sm.write_number(k, 4, a.accuracy, F["pct"])
    r = r + 3 + len(acc)
    sm.write(r, 1, "AI step: " + run["ai_note"], F["muted"])
    sm.write(r + 1, 1, "The answer key exists only because the invoices are synthetic; with real invoices the "
                       "checks above are what catch reading errors.", F["muted"])
    sm.write(7, 6, "Totals of OK invoices", F["h2"])
    sm.write_row(8, 6, ["Currency", "Total"], F["head"])
    tot = inv[inv["status"] == "OK"].groupby("currency")["total"].sum()
    for k, (cur, v) in enumerate(tot.items(), start=9):
        sm.write(k, 6, cur, F["txt"]); sm.write_number(k, 7, v, F["money"])

    def table_sheet(name: str, df: pd.DataFrame, widths: dict[str, int], formats: dict[str, str]):
        ws = wb.add_worksheet(name)
        ws.freeze_panes(1, 0)
        cols = list(df.columns)
        ws.add_table(0, 0, max(len(df), 1), len(cols) - 1, {
            "name": "tbl_" + name.replace(" ", ""), "style": "Table Style Light 9",
            "columns": [{"header": c, "header_format": F["head"]} for c in cols]})
        for c, col in enumerate(cols):
            fmt = F[formats.get(col, "txt")]
            ws.set_column(c, c, widths.get(col, 14))
            for i, v in enumerate(df[col], start=1):
                if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
                    ws.write_blank(i, c, None, fmt)
                elif isinstance(v, date):
                    ws.write_datetime(i, c, pd.Timestamp(v).to_pydatetime(), fmt)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    ws.write_number(i, c, float(v), fmt)
                else:
                    ws.write(i, c, str(v), fmt)
        return ws

    ws = table_sheet("Invoices", inv, {"status": 9, "issues": 7, "file": 33, "supplier": 34, "tax_id": 14,
                                       "issue_date": 12, "due_date": 12,
                                       "invoice_no": 13, "currency": 8, "method": 12, "n_lines": 8, "tax_rate": 8},
                     {"subtotal": "money", "tax": "money", "total": "money", "issue_date": "date",
                      "due_date": "date", "issues": "center", "n_lines": "center", "tax_rate": "center",
                      "currency": "center"})
    for word, fmt in (("OK", "ok"), ("Check", "check"), ("Review", "review")):
        ws.conditional_format(1, 0, len(inv), 0, {"type": "cell", "criteria": "==", "value": f'"{word}"',
                                                   "format": F[fmt]})
    table_sheet("Line items", lines, {"file": 36, "supplier": 34, "description": 52, "invoice_no": 13, "line": 6},
                {"qty": "int", "unit_price": "money", "amount": "money", "line": "int"})
    log = log[["severity", "file", "invoice_no", "problem", "action", "check", "supplier", "found"]]
    ws = table_sheet("Error log", log, {"severity": 9, "file": 33, "invoice_no": 12, "problem": 34, "action": 34,
                                        "check": 11, "supplier": 32, "found": 30}, {"problem": "wrap", "action": "wrap"})
    ws.conditional_format(1, 0, max(len(log), 1), 0, {"type": "cell", "criteria": "==", "value": '"Error"',
                                                         "format": F["review"]})
    ws.conditional_format(1, 0, max(len(log), 1), 0, {"type": "cell", "criteria": "==", "value": '"Warning"',
                                                         "format": F["check"]})
    hw = wb.add_worksheet("How it works")
    hw.hide_gridlines(2)
    hw.set_column(0, 0, 2); hw.set_column(1, 1, 22); hw.set_column(2, 2, 100)
    hw.write(1, 1, "How the pipeline works", F["title"])
    for k, (step, text) in enumerate(HOW, start=3):
        hw.write(k, 1, step, F["h2"]); hw.write(k, 2, text, F["wrap"]); hw.set_row(k, 44)
    hw.write(len(HOW) + 4, 1, "All PDFs are SAMPLE / SYNTHETIC documents created for a portfolio project.", F["warn"])
    wb.close()
    paths["xlsx"] = XLSX
    return paths
