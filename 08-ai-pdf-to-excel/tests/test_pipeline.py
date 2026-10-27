"""Unit tests: parsing rules, validation checks, and the AI step against a local fake API (no key, no cost)."""
from __future__ import annotations

import json
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

import ai_step  # noqa: E402
import validate  # noqa: E402
from parsing import parse_amount, parse_date  # noqa: E402


def test_amounts():
    assert parse_amount("1.234.567") == 1234567
    assert parse_amount("$ 95.000") == 95000
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("1.234,50") == 1234.5
    assert parse_amount("25.00") == 25.0
    assert parse_amount("459.000") == 459000
    assert parse_amount("abc") is None


def test_dates():
    assert parse_date("12/05/2026") == date(2026, 5, 12)
    assert parse_date("17-07-2026") == date(2026, 7, 17)
    assert parse_date("2026-03-01") == date(2026, 3, 1)
    assert parse_date("May 6, 2026") == date(2026, 5, 6)
    assert parse_date("6 de julio de 2026 Señores: Sample Buyer Co.") == date(2026, 7, 6)
    assert parse_date("31/02/2026") is None


def _inv(**kw):
    base = {"file": "a.pdf", "text_layer": True, "supplier": "S", "tax_id": "000.1", "invoice_no": "A-1",
            "issue_date": date(2026, 3, 1), "due_date": date(2026, 3, 31), "currency": "USD", "subtotal": 50.0,
            "tax_rate": 0.0, "tax": 0.0, "total": 50.0,
            "lines": [{"description": "x", "qty": 2.0, "unit_price": 25.0, "amount": 50.0}]}
    base.update(kw)
    return base


def test_validation():
    today = date(2026, 10, 1)
    assert validate.check(_inv(), {}, today) == []
    checks = {i["check"] for i in validate.check(_inv(total=60.0), {}, today)}
    assert checks == {"total"}
    bad_line = _inv(lines=[{"description": "x", "qty": 2.0, "unit_price": 25.0, "amount": 25.0}], subtotal=25.0,
                    total=25.0)
    assert {i["check"] for i in validate.check(bad_line, {}, today)} == {"line_math"}
    assert {i["check"] for i in validate.check(_inv(due_date=date(2026, 2, 1)), {}, today)} == {"dates"}
    seen = {}
    validate.check(_inv(), seen, today)
    assert [i["check"] for i in validate.check(_inv(file="b.pdf"), seen, today)] == ["duplicate"]
    assert [i["check"] for i in validate.check(_inv(text_layer=False), {}, today)] == ["no_text"]


class _FakeAPI(BaseHTTPRequestHandler):
    """Answers like the Messages API and remembers the request body."""
    last_body: dict = {}

    def do_POST(self):  # noqa: N802
        _FakeAPI.last_body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        fields = {"supplier": "Demo Cleaning Co. (Sample)", "tax_id": "000.500.600-3", "invoice_no": "CL/2026/33",
                  "issue_date": "2026-04-02", "due_date": "", "currency": "COP", "subtotal": "1110000",
                  "tax_rate": "19", "tax": "210900", "total": "1320900",
                  "lines": [{"description": "Disinfection service", "qty": 1, "unit_price": 210000, "amount": 210000},
                            {"description": "Office cleaning service (visit)", "qty": 5, "unit_price": 180000,
                             "amount": 900000}]}
        body = json.dumps({"id": "msg_test", "type": "message", "role": "assistant", "model": ai_step.MODEL,
                           "content": [{"type": "text", "text": json.dumps(fields)}], "stop_reason": "end_turn",
                           "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 20}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_ai_step_request_and_mapping(tmp_path=None):
    import anthropic
    server = HTTPServer(("127.0.0.1", 0), _FakeAPI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = anthropic.Anthropic(api_key="test-key", base_url=f"http://127.0.0.1:{server.server_port}",
                                 max_retries=0)
    pdf = PROJECT / "tests" / "_tiny.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%sample\n")
    try:
        fields, note = ai_step.ask_claude(pdf, "", client=client)
    finally:
        server.shutdown()
        pdf.unlink()
    body = _FakeAPI.last_body
    assert body["model"] == "claude-opus-5-5"
    assert body["fallbacks"] == "default"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["messages"][0]["content"][0]["type"] == "document"       # scanned PDF is sent as a document
    inv = ai_step.to_invoice(fields, "SAMPLE.pdf")
    assert inv["method"] == "AI (Claude)" and inv["total"] == 1320900 and len(inv["lines"]) == 2
    assert validate.check(inv, {}, date(2026, 10, 1)) == []


def run_all() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
    return len(tests)


if __name__ == "__main__":
    print(f"{run_all()} tests passed")
