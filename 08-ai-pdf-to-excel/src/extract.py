"""Rule-based extraction: pdfplumber reads the text layer, regular expressions find each field.

The rules are written for label families, not for one supplier: English ("Invoice No", "Issue date", "VAT") and
Spanish ("Factura de venta No.", "Fecha de expedición", "IVA") labels, tables with or without ruling lines, and
plain-text invoices with "qty x item @ price = amount" lines.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from parsing import parse_amount, parse_date

INVOICE_NO = re.compile(r"(?:Invoice\s*(?:No\.?|number|#)|FACTURA\s+DE\s+VENTA\s+No\.?)\s*:?\s*([A-Z]{1,4}[-/A-Z0-9]*\d)",
                        re.I)
TAX_ID = re.compile(r"(?:NIT|Tax ID)\s*:?\s*(\d[\d.\-]{6,}\d)")
ISSUE = [r"Issue date\s*:", r"Invoice date\s*:", r"Fecha de expedici[oó]n\s*:", r"(?<![Dd]ue )\bDate\s*:"]
DUE = [r"Due date\s*:", r"Payment due\s*:", r"Fecha de vencimiento\s*:"]
SUBTOTAL = re.compile(r"Subtotal\s*:?\s*\$?\s*([\d.,]+)")
TAX = re.compile(r"\b(?:VAT|IVA|Tax)\s*\(?\s*(\d+(?:[.,]\d+)?)\s*%\s*\)?\s*:?\s*\$?\s*([\d.,]+)")
TOTAL = re.compile(r"(?<![A-Za-z])(?:Total a pagar|Total due(?: [A-Z]{3})?|Total(?: [A-Z]{3})?|TOTAL)\s*:?\s*\$?\s*"
                   r"([\d.,]+)")
CURRENCY = re.compile(r"\b(USD|COP|EUR)\b")
TABLE_HEADER = re.compile(r"^(Description|Descripción|Item)\b.*\b(Qty|Cant\.|Quantity)", re.I)
TABLE_ROW = re.compile(r"^(?P<desc>.+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s+\$?\s?(?P<price>[\d.,]+)\s+\$?\s?(?P<amount>[\d.,]+)$")
PLAIN_ROW = re.compile(r"^(?P<qty>\d+(?:[.,]\d+)?)\s*x\s+(?P<desc>.+?)\s+@\s+(?P<price>[\d.,]+)\s*=\s*(?P<amount>[\d.,]+)")
FIELDS = ["supplier", "tax_id", "invoice_no", "issue_date", "due_date", "currency", "subtotal", "tax_rate", "tax",
          "total"]
REQUIRED = ["supplier", "tax_id", "invoice_no", "issue_date", "total"]


def read_text(path: Path) -> str:
    """Text of all pages, without watermark or stamp characters (large or rotated glyphs)."""
    keep = lambda o: o.get("object_type") != "char" or (o.get("upright", True) and o.get("size", 0) < 30)  # noqa: E731
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.filter(keep).extract_text() or "") for p in pdf.pages).strip()


def _after_label(text: str, patterns: list[str]):
    for pat in patterns:
        m = re.search(pat + r"(.*)$", text, flags=re.M)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


def _lines(text: str) -> list[dict]:
    rows, in_table = [], False
    for raw in text.splitlines():
        line = raw.strip()
        m = PLAIN_ROW.match(line)
        if m:
            rows.append(m.groupdict())
            continue
        if TABLE_HEADER.match(line):
            in_table = True
            continue
        if not in_table:
            continue
        if re.match(r"^(Subtotal|Total)", line, re.I):
            in_table = False
            continue
        m = TABLE_ROW.match(line)
        if m:
            rows.append(m.groupdict())
        elif rows and len(line) > 3 and not re.fullmatch(r"[\d.,$ ]+", line):
            rows[-1]["desc"] += " " + line                       # description wrapped onto the next line
    return [{"description": r["desc"].strip(), "qty": parse_amount(r["qty"]), "unit_price": parse_amount(r["price"]),
             "amount": parse_amount(r["amount"])} for r in rows]


def extract(path: Path) -> dict:
    text = read_text(path)
    out = {"file": path.name, "method": "rules", "text_layer": bool(text), "lines": []}
    out.update({f: None for f in FIELDS})
    if not text:
        return out
    lines = [ln.strip() for ln in text.splitlines()]
    m = TAX_ID.search(text)
    if m:
        out["tax_id"] = m.group(1)
        idx = next(i for i, ln in enumerate(lines) if m.group(0) in ln)
        cand = [ln for ln in lines[:idx] if ln and not re.fullmatch(r"(INVOICE|FACTURA.*)", ln, re.I)]
        out["supplier"] = cand[-1] if cand else None
    m = INVOICE_NO.search(text)
    out["invoice_no"] = m.group(1) if m else None
    out["issue_date"] = _after_label(text, ISSUE)
    out["due_date"] = _after_label(text, DUE)
    m = CURRENCY.search(text)
    out["currency"] = m.group(1) if m else ("COP" if "NIT" in text else None)
    m = SUBTOTAL.search(text)
    out["subtotal"] = parse_amount(m.group(1)) if m else None
    m = TAX.search(text)
    if m:
        out["tax_rate"], out["tax"] = parse_amount(m.group(1)), parse_amount(m.group(2))
    m = TOTAL.search(text)
    out["total"] = parse_amount(m.group(1)) if m else None
    out["lines"] = _lines(text)
    return out


def missing_required(inv: dict) -> list[str]:
    return [f for f in REQUIRED if inv.get(f) in (None, "")] + ([] if inv["lines"] else ["line items"])
