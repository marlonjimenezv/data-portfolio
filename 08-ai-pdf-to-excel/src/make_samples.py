"""Generate the SAMPLE / SYNTHETIC invoices used to demonstrate the pipeline.

These are not real invoices. Suppliers, buyer, tax IDs and amounts are invented (tax IDs start with zeros so they
cannot belong to a real company), every page carries a "SAMPLE / SYNTHETIC" watermark and footer, and file names
start with SAMPLE_. Four layout families imitate what an accounts-payable team receives: an English invoice with a
ruled table (COP), a Spanish "factura de venta" (COP), a US-style invoice (USD) and a plain-text invoice with no
table. A few problems are planted on purpose so the validation step has something to find; they are listed in
data/sample_invoices/answer_key.csv together with the true value of every field.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "data" / "sample_invoices"
SEED = 2026
N_PER_SUPPLIER = 10
WATERMARK = "SAMPLE / SYNTHETIC"
FOOTER = "Sample / synthetic document generated for a portfolio project. Not a real invoice."
BUYER = ("Sample Buyer Co.", "000.900.800-5")
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]

SUPPLIERS = [
    {"key": "office", "name": "Demo Office Supplies S.A.S. (Sample)", "tax_id": "000.100.200-1", "layout": "classic",
     "currency": "COP", "vat": 19, "prefix": "OS-2026-", "start": 101,
     "items": [("Printer paper A4, box of 10 reams", 98000), ("Ballpoint pens, pack of 12", 18500),
               ("Heavy-duty stapler", 32000), ("Toner cartridge, black", 285000), ("Sticky notes, pack of 12", 9800),
               ("Suspension folders, pack of 25", 24000), ("Whiteboard markers, set of 4", 21500)]},
    {"key": "tech", "name": "Demo Tech Rentals S.A.S. (Sample)", "tax_id": "000.300.400-2", "layout": "factura",
     "currency": "COP", "vat": 19, "prefix": "TR-", "start": 1041,
     "items": [("Alquiler portátil (mes)", 320000), ("Alquiler monitor 24 pulgadas (mes)", 95000),
               ("Alquiler videobeam (día)", 150000), ("Soporte técnico (hora)", 85000),
               ("Instalación y configuración", 120000)]},
    {"key": "cloud", "name": "Demo Cloud Services LLC (Sample)", "tax_id": "00-0005678", "layout": "modern",
     "currency": "USD", "vat": 0, "prefix": "CS-", "start": 88201,
     "items": [("Cloud server, standard plan (month)", 89.00), ("Managed database (month)", 145.00),
               ("Backup storage 500 GB (month)", 25.00), ("Support hours", 60.00), ("Domain and SSL renewal", 39.99)]},
    {"key": "cleaning", "name": "Demo Cleaning Co. (Sample)", "tax_id": "000.500.600-3", "layout": "plain",
     "currency": "COP", "vat": 19, "prefix": "CL/2026/", "start": 31,
     "items": [("Office cleaning service (visit)", 180000), ("Window cleaning (per floor)", 240000),
               ("Carpet deep clean (m2)", 6500), ("Disinfection service", 210000), ("Cleaning supplies kit", 75000)]},
]


# ---------- number and date formats ----------
def fmt_cop(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def fmt_usd(x: float) -> str:
    return f"{x:,.2f}"


def fmt_date(d: date, style: str) -> str:
    return {"dmy_slash": d.strftime("%d/%m/%Y"), "iso": d.isoformat(), "long_en": f"{d:%B} {d.day}, {d.year}",
            "dmy_dash": d.strftime("%d-%m-%Y"), "long_es": f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"}[style]


# ---------- invoice data ----------
def make_invoices(rng: random.Random) -> list[dict]:
    invoices = []
    for s in SUPPLIERS:
        for i in range(N_PER_SUPPLIER):
            issue = date(2026, 1, 5) + timedelta(days=rng.randint(0, 250))
            n_lines = rng.randint(1, 5)
            lines = []
            for desc, price in rng.sample(s["items"], n_lines):
                qty = rng.choice([1, 1, 2, 3, 4, 5, 10]) if price < 200 or s["currency"] == "COP" else 1
                if desc.startswith("Carpet"):
                    qty = rng.choice([40, 60, 85, 120])
                lines.append({"description": desc, "qty": qty, "unit_price": price,
                              "amount": round(qty * price, 2)})
            inv = {"supplier_key": s["key"], "supplier": s["name"], "tax_id": s["tax_id"], "layout": s["layout"],
                   "currency": s["currency"], "vat_rate": s["vat"], "invoice_no": f"{s['prefix']}{s['start'] + i}",
                   "issue_date": issue, "due_date": None if s["layout"] == "plain" else issue + timedelta(days=30),
                   "lines": lines, "planted_issue": "", "file_note": ""}
            invoices.append(inv)
    groups = {s["key"]: [v for v in invoices if v["supplier_key"] == s["key"]] for s in SUPPLIERS}

    # Planted problems (the kind an accounts-payable team really meets)
    groups["office"][3]["planted_issue"] = "total_mismatch"           # printed total is off by COP 10,000
    groups["office"][7]["lines"][0]["description"] = ("Ergonomic office chair with adjustable armrests and lumbar "
                                                      "support, black mesh")  # long text that wraps in the cell
    groups["office"][7]["lines"][0]["unit_price"] = 459000
    groups["office"][7]["lines"][0]["amount"] = groups["office"][7]["lines"][0]["qty"] * 459000
    groups["cloud"][5]["planted_issue"] = "line_amount_mismatch"      # one line: qty x price != amount
    groups["tech"][8]["planted_issue"] = "due_before_issue"           # due date typed one month early
    groups["tech"][8]["due_date"] = groups["tech"][8]["issue_date"] - timedelta(days=1)
    groups["cleaning"][2]["planted_issue"] = "scanned_image"          # paper invoice scanned, no text layer

    for v in invoices:
        if v["planted_issue"] == "line_amount_mismatch":
            ln = v["lines"][0]
            ln["qty"] = max(ln["qty"], 2)
            ln["amount"] = round((ln["qty"] - 1) * ln["unit_price"], 2)   # billed one unit less than stated qty
        sub = round(sum(ln["amount"] for ln in v["lines"]), 2)
        tax = round(sub * v["vat_rate"] / 100, 0 if v["currency"] == "COP" else 2)
        v["subtotal"], v["tax"] = sub, tax
        v["total"] = round(sub + tax + (10000 if v["planted_issue"] == "total_mismatch" else 0), 2)
    return invoices


# ---------- drawing ----------
def _watermark(c: Canvas, w: float, h: float) -> None:
    c.saveState()
    c.setFillColor(colors.Color(0.85, 0.15, 0.15, alpha=0.10))
    c.setFont("Helvetica-Bold", 64)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, WATERMARK)
    c.restoreState()
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.Color(0.6, 0.1, 0.1))
    c.drawCentredString(w / 2, 10 * mm, FOOTER)
    c.setFillColor(colors.black)


def _table(c: Canvas, x: float, y: float, widths: list[float], header: list[str], rows: list[list[str]],
           ruled: bool = True, wrap: int = 46) -> float:
    """Draw a simple table; long descriptions wrap onto a second line. Returns the y below the table."""
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#e8ecf2"))
    c.rect(x, y - 6 * mm, sum(widths), 6 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    cx = x
    for i, (w, t) in enumerate(zip(widths, header)):
        if i == 0:
            c.drawString(cx + 2 * mm, y - 4.2 * mm, t)
        else:
            c.drawRightString(cx + w - 2 * mm, y - 4.2 * mm, t)
        cx += w
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for r in rows:
        desc = r[0]
        parts = [desc] if len(desc) <= wrap else [desc[:desc.rfind(" ", 0, wrap)], desc[desc.rfind(" ", 0, wrap) + 1:]]
        row_h = 6 * mm + (len(parts) - 1) * 4 * mm
        cx = x
        for i, (w, t) in enumerate(zip(widths, r)):
            if i == 0:
                for k, p in enumerate(parts):
                    c.drawString(cx + 2 * mm, y - 4.2 * mm - k * 4 * mm, p)
            else:
                c.drawRightString(cx + w - 2 * mm, y - 4.2 * mm, t)
            cx += w
        y -= row_h
        if ruled:
            c.setStrokeColor(colors.HexColor("#b9c2cf"))
            c.line(x, y, x + sum(widths), y)
    return y


def draw_classic(c: Canvas, v: dict) -> None:
    w, h = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 25 * mm, v["supplier"])
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 31 * mm, f"NIT {v['tax_id']}")
    c.drawString(20 * mm, h - 36 * mm, "Sample address, Bogotá D.C., Colombia")
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(w - 20 * mm, h - 25 * mm, "INVOICE")
    c.setFont("Helvetica", 9.5)
    c.drawRightString(w - 20 * mm, h - 32 * mm, f"Invoice No: {v['invoice_no']}")
    c.drawRightString(w - 20 * mm, h - 37 * mm, f"Date: {fmt_date(v['issue_date'], 'dmy_slash')}")
    c.drawRightString(w - 20 * mm, h - 42 * mm, f"Due date: {fmt_date(v['due_date'], 'dmy_slash')}")
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(20 * mm, h - 52 * mm, "Bill to:")
    c.setFont("Helvetica", 9.5)
    c.drawString(20 * mm, h - 57 * mm, f"{BUYER[0]} · NIT {BUYER[1]}")
    rows = [[ln["description"], str(ln["qty"]), fmt_cop(ln["unit_price"]), fmt_cop(ln["amount"])] for ln in v["lines"]]
    y = _table(c, 20 * mm, h - 68 * mm, [95 * mm, 15 * mm, 30 * mm, 30 * mm],
               ["Description", "Qty", "Unit price", "Amount"], rows)
    y -= 8 * mm
    for label, val, bold in (("Subtotal", fmt_cop(v["subtotal"]), False), (f"VAT {v['vat_rate']}%", fmt_cop(v["tax"]), False),
                             ("Total COP", fmt_cop(v["total"]), True)):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        c.drawString(130 * mm, y, label)
        c.drawRightString(w - 20 * mm, y, val)
        y -= 6 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(20 * mm, 30 * mm, "Payment terms: 30 days. Bank transfer to the account on file (sample).")


def draw_factura(c: Canvas, v: dict) -> None:
    w, h = A4
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 22 * mm, v["supplier"])
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 27 * mm, f"NIT: {v['tax_id']} · Régimen común · Medellín, Antioquia")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, h - 40 * mm, f"FACTURA DE VENTA No. {v['invoice_no']}")
    c.setFont("Helvetica", 9.5)
    c.drawString(20 * mm, h - 47 * mm, f"Fecha de expedición: {fmt_date(v['issue_date'], 'long_es')}")
    c.drawString(20 * mm, h - 52 * mm, f"Fecha de vencimiento: {fmt_date(v['due_date'], 'long_es')}")
    c.drawString(115 * mm, h - 47 * mm, f"Señores: {BUYER[0]}")
    c.drawString(115 * mm, h - 52 * mm, f"NIT: {BUYER[1]}")
    rows = [[ln["description"], str(ln["qty"]), "$ " + fmt_cop(ln["unit_price"]), "$ " + fmt_cop(ln["amount"])]
            for ln in v["lines"]]
    y = _table(c, 20 * mm, h - 62 * mm, [90 * mm, 15 * mm, 32 * mm, 33 * mm],
               ["Descripción", "Cant.", "Valor unitario", "Valor total"], rows)
    y -= 8 * mm
    for label, val, bold in (("Subtotal", fmt_cop(v["subtotal"]), False), (f"IVA {v['vat_rate']}%", fmt_cop(v["tax"]), False),
                             ("Total a pagar", fmt_cop(v["total"]), True)):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        c.drawString(125 * mm, y, label)
        c.drawRightString(w - 20 * mm, y, "$ " + val)
        y -= 6 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(20 * mm, 30 * mm, "Esta factura de venta es un ejemplo sintético (sample / synthetic).")


def draw_modern(c: Canvas, v: dict) -> None:
    w, h = letter
    c.setFillColor(colors.HexColor("#1f3a5f"))
    c.rect(0, h - 32 * mm, w, 32 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(18 * mm, h - 17 * mm, v["supplier"])
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, h - 24 * mm, f"Tax ID: {v['tax_id']} · Sample address, Austin, TX")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9.5)
    y0 = h - 45 * mm
    for i, (k, val) in enumerate((("Invoice #", v["invoice_no"]), ("Issue date", fmt_date(v["issue_date"], "long_en")),
                                  ("Payment due", fmt_date(v["due_date"], "long_en")), ("Currency", "USD"))):
        c.drawString(18 * mm, y0 - i * 5.5 * mm, f"{k}: {val}")
    c.drawString(120 * mm, y0, "Billed to")
    c.drawString(120 * mm, y0 - 5.5 * mm, BUYER[0])
    rows = [[ln["description"], str(ln["qty"]), fmt_usd(ln["unit_price"]), fmt_usd(ln["amount"])] for ln in v["lines"]]
    y = _table(c, 18 * mm, h - 75 * mm, [92 * mm, 22 * mm, 30 * mm, 33 * mm],
               ["Item", "Quantity", "Price", "Line total"], rows)
    y -= 8 * mm
    for label, val, bold in (("Subtotal", fmt_usd(v["subtotal"]), False), (f"Tax ({v['vat_rate']}%)", fmt_usd(v["tax"]), False),
                             ("Total due USD", fmt_usd(v["total"]), True)):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        c.drawString(130 * mm, y, label)
        c.drawRightString(w - 18 * mm, y, val)
        y -= 6 * mm


def draw_plain(c: Canvas, v: dict) -> None:
    w, h = A4
    c.setFont("Courier-Bold", 12)
    c.drawString(20 * mm, h - 25 * mm, v["supplier"])
    c.setFont("Courier", 10)
    lines = [f"NIT {v['tax_id']}", "", f"Invoice number: {v['invoice_no']}",
             f"Date: {fmt_date(v['issue_date'], 'dmy_dash')}", f"Customer: {BUYER[0]}", "Payment: cash on delivery",
             "", "Services:"]
    lines += [f"  {ln['qty']} x {ln['description']} @ {fmt_cop(ln['unit_price'])} = {fmt_cop(ln['amount'])}"
              for ln in v["lines"]]
    lines += ["", f"Subtotal: {fmt_cop(v['subtotal'])}", f"IVA ({v['vat_rate']}%): {fmt_cop(v['tax'])}",
              f"TOTAL: {fmt_cop(v['total'])}"]
    for i, t in enumerate(lines):
        c.drawString(20 * mm, h - 33 * mm - i * 5.2 * mm, t)


DRAW = {"classic": (draw_classic, A4), "factura": (draw_factura, A4), "modern": (draw_modern, letter),
        "plain": (draw_plain, A4)}


def file_name(v: dict) -> str:
    return f"SAMPLE_{v['supplier_key']}_{v['invoice_no'].replace('/', '-')}.pdf"


def render(v: dict, path: Path) -> None:
    draw, size = DRAW[v["layout"]]
    c = Canvas(str(path), pagesize=size)
    c.setTitle(f"SAMPLE / SYNTHETIC invoice {v['invoice_no']}")
    c.setAuthor("Synthetic data generator (portfolio sample)")
    draw(c, v)
    _watermark(c, *size)
    c.showPage()
    c.save()


def scan(path: Path, rng: random.Random) -> None:
    """Turn a PDF into an image-only PDF (like a paper invoice that was scanned): no text layer left."""
    from PIL import Image, ImageFilter
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["pdftoppm", "-r", "110", "-gray", "-png", "-singlefile", str(path), str(tmp / "p")], check=True)
    im = Image.open(tmp / "p.png").convert("L").rotate(rng.uniform(-1.2, 1.2), fillcolor=255, expand=False)
    im = im.filter(ImageFilter.GaussianBlur(0.4))
    im.convert("RGB").save(path, "PDF", resolution=110)
    shutil.rmtree(tmp)


def main() -> pd.DataFrame:
    rng = random.Random(SEED)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    invoices = make_invoices(rng)
    rows, line_rows = [], []
    for v in invoices:
        path = OUT / file_name(v)
        render(v, path)
        if v["planted_issue"] == "scanned_image":
            scan(path, rng)
        rows.append({"file": path.name, **{k: v[k] for k in ("supplier", "tax_id", "invoice_no", "currency",
                                                             "subtotal", "tax", "total", "planted_issue")},
                     "issue_date": v["issue_date"].isoformat(),
                     "due_date": v["due_date"].isoformat() if v["due_date"] else "", "n_lines": len(v["lines"])})
        line_rows += [{"file": path.name, "line": i + 1, **ln} for i, ln in enumerate(v["lines"])]
    # The same invoice sent twice (a common accounts-payable problem)
    dup = next(v for v in invoices if v["supplier_key"] == "tech" and v["invoice_no"].endswith("1042"))
    dup_name = file_name(dup).replace(".pdf", "_resent.pdf")
    shutil.copyfile(OUT / file_name(dup), OUT / dup_name)
    rows.append({**next(r for r in rows if r["file"] == file_name(dup)), "file": dup_name,
                 "planted_issue": "duplicate"})
    line_rows += [{**ln, "file": dup_name} for ln in line_rows if ln["file"] == file_name(dup)]
    key = pd.DataFrame(rows)
    key.to_csv(OUT / "answer_key.csv", index=False)
    pd.DataFrame(line_rows).to_csv(OUT / "answer_key_lines.csv", index=False)
    (OUT / "README.md").write_text(
        "# SAMPLE / SYNTHETIC invoices\n\nEvery PDF in this folder was generated by `src/make_samples.py` for a "
        "portfolio project. They are **not real invoices**: suppliers, buyer, tax IDs (all starting with zeros) and "
        "amounts are invented, and each page is watermarked \"SAMPLE / SYNTHETIC\".\n\n`answer_key.csv` and "
        "`answer_key_lines.csv` hold the true values, used only to measure extraction accuracy. The column "
        "`planted_issue` lists the problems added on purpose (wrong total, wrong line amount, due date before issue "
        "date, scanned image without text, duplicate invoice).\n", encoding="utf-8")
    return key


if __name__ == "__main__":
    k = main()
    print(f"{len(k)} sample PDFs in {OUT}")
    print(k["planted_issue"].value_counts().to_string())
