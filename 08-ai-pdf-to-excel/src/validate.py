"""Business checks on every extracted invoice. Each problem becomes one row of the error log."""
from __future__ import annotations

from datetime import date

from extract import missing_required

ACTIONS = {
    "no_text": "Scanned image: run OCR or the AI step, or key it in by hand.",
    "missing": "Read the field from the PDF and fill it in.",
    "line_math": "Ask the supplier which is right (quantity, price or amount) before paying.",
    "subtotal": "Lines do not add up to the subtotal: check for a missing or extra line.",
    "total": "Total does not equal subtotal + tax: ask the supplier for a corrected invoice.",
    "tax": "Tax amount does not match the stated rate: check the rate.",
    "dates": "Due date is before the issue date: confirm the payment term.",
    "future": "Issue date is in the future: check the date.",
    "duplicate": "Same supplier and invoice number as another file: do not pay twice.",
}


def _tol(currency: str | None) -> float:
    return 1.0 if currency == "COP" else 0.011


def _money(x: float | None, currency: str | None) -> str:
    if x is None:
        return ""
    return f"{x:,.0f}".replace(",", ".") if currency == "COP" else f"{x:,.2f}"


def check(inv: dict, seen: dict, today: date) -> list[dict]:
    issues = []

    def add(check_name: str, severity: str, problem: str, found: str = ""):
        issues.append({"file": inv["file"], "invoice_no": inv.get("invoice_no") or "", "supplier": inv.get("supplier")
                       or "", "severity": severity, "check": check_name, "problem": problem, "found": found,
                       "action": ACTIONS[check_name]})

    if not inv["text_layer"]:
        add("no_text", "Error", "No text layer: the PDF is a scanned image")
        return issues
    for f in missing_required(inv):
        add("missing", "Error", f"Required field not found: {f}")
    cur, tol = inv.get("currency"), _tol(inv.get("currency"))
    for i, ln in enumerate(inv["lines"], start=1):
        if None in (ln["qty"], ln["unit_price"], ln["amount"]):
            add("missing", "Error", f"Line {i}: quantity, price or amount not readable")
        elif abs(ln["qty"] * ln["unit_price"] - ln["amount"]) > tol:
            add("line_math", "Error", f"Line {i}: {ln['qty']:g} x {_money(ln['unit_price'], cur)} = "
                f"{_money(ln['qty'] * ln['unit_price'], cur)}, but the invoice says {_money(ln['amount'], cur)}",
                ln["description"])
    if inv["lines"] and inv.get("subtotal") is not None:
        s = sum(ln["amount"] or 0 for ln in inv["lines"])
        if abs(s - inv["subtotal"]) > tol:
            add("subtotal", "Error", f"Lines add up to {_money(s, cur)}, subtotal says {_money(inv['subtotal'], cur)}")
    if None not in (inv.get("subtotal"), inv.get("tax"), inv.get("total")):
        if abs(inv["subtotal"] + inv["tax"] - inv["total"]) > tol:
            add("total", "Error", f"Subtotal + tax = {_money(inv['subtotal'] + inv['tax'], cur)}, "
                f"total says {_money(inv['total'], cur)}")
        if inv.get("tax_rate") is not None and abs(inv["subtotal"] * inv["tax_rate"] / 100 - inv["tax"]) > tol:
            add("tax", "Warning", f"{inv['tax_rate']:g}% of the subtotal is "
                f"{_money(inv['subtotal'] * inv['tax_rate'] / 100, cur)}, tax says {_money(inv['tax'], cur)}")
    if inv.get("issue_date") and inv.get("due_date") and inv["due_date"] < inv["issue_date"]:
        add("dates", "Warning", f"Due {inv['due_date']} is before issue {inv['issue_date']}")
    if inv.get("issue_date") and inv["issue_date"] > today:
        add("future", "Warning", f"Issue date {inv['issue_date']} is after the processing date {today}")
    key = (inv.get("tax_id"), inv.get("invoice_no"))
    if all(key):
        if key in seen:
            add("duplicate", "Error", f"Duplicate of {seen[key]}")
        else:
            seen[key] = inv["file"]
    return issues


def status(issues: list[dict]) -> str:
    if any(i["severity"] == "Error" for i in issues):
        return "Review"
    return "Check" if issues else "OK"
