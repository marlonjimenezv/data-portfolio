"""Optional AI step: ask Claude to read the invoices the rules could not read.

It runs only when the ANTHROPIC_API_KEY environment variable is set (and not with --no-ai). It is used for
extraction gaps only: scanned PDFs without a text layer (the PDF itself is sent, Claude reads the image) and invoices
where a required field or the line items were not found (the text is sent). It never "corrects" an invoice that was
read fine but fails a business check: a wrong total on the document stays a wrong total. Every value it returns goes
through the same validation, and its rows are marked "AI (Claude)" in the output so a person can review them.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from parsing import parse_amount, parse_date

MODEL = "claude-opus-5-5"
SYSTEM = ("You extract data from supplier invoices for an accounts-payable team. Copy values exactly as printed on "
          "the document; do not correct arithmetic or fill in values that are not printed. Use an empty string for "
          "any field that is not on the document. Dates as YYYY-MM-DD. Amounts as plain numbers with a dot as the "
          "decimal separator and no thousands separators. The supplier is the company that issued the invoice, not "
          "the customer.")
_STR = {"type": "string"}
_NUM = {"type": "number"}
SCHEMA = {
    "type": "object",
    "properties": {
        "supplier": _STR, "tax_id": _STR, "invoice_no": _STR, "issue_date": _STR, "due_date": _STR,
        "currency": _STR, "subtotal": _STR, "tax_rate": _STR, "tax": _STR, "total": _STR,
        "lines": {"type": "array", "items": {
            "type": "object",
            "properties": {"description": _STR, "qty": _NUM, "unit_price": _NUM, "amount": _NUM},
            "required": ["description", "qty", "unit_price", "amount"], "additionalProperties": False}},
    },
    "required": ["supplier", "tax_id", "invoice_no", "issue_date", "due_date", "currency", "subtotal", "tax_rate",
                 "tax", "total", "lines"],
    "additionalProperties": False,
}


def available(disabled: bool = False) -> bool:
    return not disabled and bool(os.environ.get("ANTHROPIC_API_KEY"))


def _content(pdf: Path, text: str) -> list[dict]:
    if text:
        return [{"type": "text", "text": f"Invoice text extracted from {pdf.name}:\n\n{text}\n\nExtract the fields."}]
    data = base64.standard_b64encode(pdf.read_bytes()).decode("ascii")
    return [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
            {"type": "text", "text": "This is a scanned supplier invoice. Extract the fields."}]


def ask_claude(pdf: Path, text: str, client=None) -> tuple[dict | None, str]:
    """Returns (fields, note). fields is None when Claude declined or the call failed."""
    import anthropic
    client = client or anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": _content(pdf, text)}],
        )
    except anthropic.RateLimitError:
        return None, "AI step: rate limited, try again later"
    except anthropic.APIStatusError as e:
        return None, f"AI step: API error {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "AI step: no connection to the API"
    if response.stop_reason == "refusal":
        return None, "AI step: request declined"
    if response.stop_reason == "max_tokens":
        return None, "AI step: answer cut off"
    raw = next((b.text for b in response.content if b.type == "text"), "")
    return json.loads(raw), "AI step: fields read by Claude"


def to_invoice(fields: dict, file: str) -> dict:
    """Map Claude's JSON onto the same structure the rules produce."""
    inv = {"file": file, "method": "AI (Claude)", "text_layer": True,
           "supplier": fields["supplier"] or None, "tax_id": fields["tax_id"] or None,
           "invoice_no": fields["invoice_no"] or None, "currency": fields["currency"] or None,
           "issue_date": parse_date(fields["issue_date"]), "due_date": parse_date(fields["due_date"])}
    for k in ("subtotal", "tax_rate", "tax", "total"):
        inv[k] = parse_amount(fields[k])
    inv["lines"] = [{"description": ln["description"], "qty": float(ln["qty"]), "unit_price": float(ln["unit_price"]),
                     "amount": float(ln["amount"])} for ln in fields["lines"]]
    return inv
