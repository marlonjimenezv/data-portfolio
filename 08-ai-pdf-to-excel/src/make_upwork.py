"""Upwork package for project 08 (and the animated GIF of the run)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import brand  # noqa: E402
import config  # noqa: E402
import make_gif  # noqa: E402
import outputs  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402
from xlsx_values import lo_recalc  # noqa: E402

UP = PROJECT / "upwork"
SAMPLES = PROJECT / "data" / "sample_invoices"
FOLDER = "08-ai-pdf-to-excel"
SHOW = ["SAMPLE_office_OS-2026-108.pdf", "SAMPLE_tech_TR-1042.pdf", "SAMPLE_cloud_CS-88206.pdf",
        "SAMPLE_cleaning_CL-2026-31.pdf"]


def trim(path: Path, out: Path, pad: int = 30) -> Path:
    im = Image.open(path).convert("RGB")
    bbox = im.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox()
    if bbox:
        im = im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad),
                      min(im.height, bbox[3] + pad)))
    im.save(out)
    return out


def pdf_png(pdf: Path, out_stem: Path, dpi: int = 110) -> Path:
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(pdf), str(out_stem)], check=True)
    return out_stem.with_suffix(".png")


def layouts(tmp: Path) -> Path:
    """The four sample layouts in a 2 x 2 grid (top half of each page)."""
    ims = []
    for f in SHOW:
        im = Image.open(pdf_png(SAMPLES / f, tmp / f.replace(".pdf", ""), 90)).convert("RGB")
        ims.append(im.crop((0, 0, im.width, int(im.height * 0.5))).resize((744, 526)))
    sheet = Image.new("RGB", (744 * 2 + 14, 526 * 2 + 14), (200, 200, 196))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % 2) * (744 + 14), (k // 2) * (526 + 14)))
    sheet.save(tmp / "layouts.png")
    return tmp / "layouts.png"


def before_after(inv: dict, tmp: Path) -> Path:
    """Top: the PDF. Bottom: the fields the pipeline extracted from it."""
    page = Image.open(pdf_png(SAMPLES / inv["file"], tmp / "ba_page", 150)).convert("RGB")
    page = page.crop((int(page.width * 0.07), int(page.height * 0.04), int(page.width * 0.93),
                      int(page.height * 0.42)))
    f = ImageFont.truetype(str(brand.FONTS["regular"]), 27)
    fb = ImageFont.truetype(str(brand.FONTS["semibold"]), 27)
    money = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    rows = [("Status", inv["status"]), ("Tax ID", inv["tax_id"]),
            ("Invoice no.", inv["invoice_no"]), ("Issue date", inv["issue_date"].isoformat()),
            ("Due date", inv["due_date"].isoformat()), ("Currency", inv["currency"]),
            ("Subtotal", money(inv["subtotal"])), (f"Tax ({inv['tax_rate']:g}%)", money(inv["tax"])),
            ("Total", money(inv["total"])), ("Line items", str(len(inv["lines"])))]
    half = (len(rows) + 1) // 2
    panel_h = 132 + half * 42
    im = Image.new("RGB", (page.width, page.height + panel_h), (255, 255, 255))
    im.paste(page, (0, 0))
    d = ImageDraw.Draw(im)
    y0 = page.height + 14
    d.line((30, y0, page.width - 30, y0), fill=(200, 200, 196), width=3)
    d.text((40, y0 + 18), "Extracted by the pipeline", font=ImageFont.truetype(str(brand.FONTS["bold"]), 32),
           fill=brand.BRAND)
    d.text((40, y0 + 72), "Supplier", font=f, fill=brand.INK_2)
    d.text((40 + 175, y0 + 72), inv["supplier"], font=fb, fill=brand.INK)
    for k, (label, v) in enumerate(rows):
        x = 40 + (k // half) * (page.width // 2)
        y = y0 + 114 + (k % half) * 42
        d.text((x, y), label, font=f, fill=brand.INK_2)
        d.text((x + 175, y), str(v), font=fb, fill=brand.GOOD_TEXT if v == "OK" else brand.INK)
    im.save(tmp / "before_after.png")
    return tmp / "before_after.png"


def cover_chart(invoices: list[dict], issues: list[dict], path: Path) -> None:
    brand.apply_mpl_style()
    n = {s: sum(i["status"] == s for i in invoices) for s in ("OK", "Check", "Review")}
    names = {"no_text": "Scanned, no text", "line_math": "Qty x price ≠ amount", "total": "Total ≠ subtotal + tax",
             "dates": "Due before issue", "duplicate": "Duplicate invoice", "missing": "Field missing",
             "subtotal": "Lines ≠ subtotal", "tax": "Tax ≠ rate", "future": "Future date"}
    counts: dict[str, int] = {}
    for i in issues:
        counts[names[i["check"]]] = counts.get(names[i["check"]], 0) + 1
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14.2, 6.0), dpi=100, gridspec_kw={"width_ratios": [1, 1.6]})
    a1.bar(list(n), list(n.values()), color=[brand.GOOD, brand.WARNING, brand.CRITICAL], width=0.6)
    for x, v in enumerate(n.values()):
        a1.text(x, v + 0.6, str(v), ha="center", fontsize=20)
    a1.set_title(f"{len(invoices)} PDFs by status", fontsize=20, loc="left")
    a1.tick_params(labelsize=16)
    a1.set_yticks([])
    a1.grid(False)
    lab = list(counts)[::-1]
    a2.barh(lab, [counts[k] for k in lab], color=brand.ORANGE, height=0.55)
    a2.set_title("Problems caught by the checks", fontsize=20, loc="left")
    a2.tick_params(axis="y", labelsize=16)
    a2.set_xticks([])
    a2.grid(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(invoices: list[dict], issues: list[dict], acc, log: list[str]) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p8up_"))
    n_rows = len(invoices) + 1
    lo_recalc(outputs.XLSX, tmp / "v.xlsx", pdf=tmp / "x.pdf", sheets=["Summary", "Invoices", "Error log"],
              one_page=["Summary", "Invoices", "Error log"],
              areas={"Summary": "A1:H32", "Invoices": f"A1:I{min(n_rows, 32)}", "Error log": "A1:E7"})
    subprocess.run(["pdftoppm", "-r", "220", "-png", str(tmp / "x.pdf"), str(tmp / "x")], check=True)
    pages = sorted(tmp.glob("x-*.png"))
    summary, inv_sheet, log_sheet = (trim(p, tmp / f"s{k}.png") for k, p in enumerate(pages))
    gif = make_gif.main(log, inv_sheet)

    cover_chart(invoices, issues, tmp / "cover.png")
    make_cover(UP / "cover.png", 8, "AI automation", "PDF Invoices to Excel",
               "Python reads, checks and loads invoice PDFs; AI handles what rules can't",
               tmp / "cover.png", "Python · pdfplumber · Claude API · Excel")
    ok_inv = next(i for i in invoices if i["file"] == "SAMPLE_tech_TR-1042.pdf")
    make_shot(UP / "shot-1.png", before_after(ok_inv, tmp), "From PDF to a clean row (sample invoice)")
    make_shot(UP / "shot-2.png", inv_sheet, "Invoices sheet: one row per PDF, with status")
    make_shot(UP / "shot-3.png", summary, "Summary: problems found and accuracy")
    make_shot(UP / "shot-4.png", log_sheet, "Error log: what to check before paying")
    make_shot(UP / "shot-5.png", PROJECT / "output" / "run_console.png", "One command processes the folder")
    figs = PROJECT / "output" / "figures"
    figs.mkdir(exist_ok=True)
    Image.open(layouts(tmp)).save(figs / "sample_layouts.png")

    n_ok = sum(i["status"] == "OK" for i in invoices)
    flagged = len(invoices) - n_ok
    acc_text = acc.set_index("field")["accuracy"]
    title = "PDF Invoices to Excel with Python and AI"
    desc = (
        "Teams lose hours typing invoice PDFs into Excel. I built a Python pipeline that reads each PDF "
        "(pdfplumber + rules, English and Spanish), checks the math, dates and duplicates, and writes an Excel file "
        "with an error log. An optional Claude AI step can read scanned PDFs. On "
        f"{len(invoices)} synthetic invoices: {n_ok} clean, {flagged} flagged, every planted problem caught. "
        "Sample project built with public data."
    )
    skills = ["Data Extraction", "Python", "Automation", "Microsoft Excel", "AI Development"]
    captions = [
        "A sample invoice (synthetic, watermarked) and the fields extracted from it: supplier, tax ID, number, "
        "dates, currency, subtotal, tax, total and line items.",
        f"The Invoices sheet: one row per PDF with status OK, Check or Review. {n_ok} of {len(invoices)} sample "
        "invoices are ready to load; the rest go to a person.",
        f"Summary: files processed, problems by type, and accuracy against the synthetic answer key "
        f"({acc_text['total']:.0%} on totals; the one miss is the scanned image).",
        "The error log explains each problem in plain words and what to do: wrong total, wrong line amount, due date "
        "before issue date, duplicate invoice, scanned image.",
        "One command processes the whole folder and prints a status line per file. Four layouts, English and "
        "Spanish. The AI step runs only when an API key is set.",
    ]
    links = [f"GitHub project folder: {config.folder_url(FOLDER)}",
             f"Excel output: {config.file_url(FOLDER + '/output/invoices_extracted.xlsx')}",
             f"Run animation (GIF): {config.file_url(FOLDER + '/output/pipeline_run.gif')}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
    print(f"  GIF: {gif.relative_to(PROJECT)} ({gif.stat().st_size / 1e6:.1f} MB)")
