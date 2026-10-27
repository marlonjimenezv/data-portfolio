"""Turn text found in a PDF into typed values: amounts in either decimal convention, dates in 5 formats."""
from __future__ import annotations

import re
from datetime import date, datetime

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], start=1)}
MONTHS.update({m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                           "septiembre", "octubre", "noviembre", "diciembre"], start=1)})


def parse_amount(text: str | None) -> float | None:
    """'1.234.567' (COP) -> 1234567, '1,234.56' (USD) -> 1234.56, '$ 95.000' -> 95000, '1.234,50' -> 1234.5."""
    if text is None:
        return None
    t = re.sub(r"[^\d.,-]", "", str(text))
    if not re.search(r"\d", t):
        return None
    if "," in t and "." in t:                               # the last separator is the decimal one
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        t = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "." in t:
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):         # dots as thousands separators
            t = t.replace(".", "")
    elif "," in t:
        t = t.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", t) else t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def parse_date(text: str | None) -> date | None:
    """dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, 'March 5, 2026', '5 de marzo de 2026'."""
    if not text:
        return None
    t = text.strip().lower()
    for pat, fmt in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),
                     (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y")):
        m = re.search(pat, t)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt).date()
            except ValueError:
                return None
    m = re.search(r"([a-z]+)\s+(\d{1,2}),\s*(\d{4})", t)                  # March 5, 2026
    if m and m.group(1) in MONTHS:
        return _safe_date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    m = re.search(r"(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})", t)        # 5 de marzo de 2026
    if m and m.group(2) in MONTHS:
        return _safe_date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    return None


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None
