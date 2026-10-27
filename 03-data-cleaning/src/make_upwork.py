"""Upwork package for project 03."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import config  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402
from xlsx_values import lo_recalc  # noqa: E402

import build_outputs  # noqa: E402

UP = PROJECT / "upwork"
FOLDER = "03-data-cleaning"


def pdf_pages(pdf: Path, dpi: int, prefix: Path) -> list[Path]:
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(prefix)], check=True)
    return sorted(prefix.parent.glob(prefix.name + "-*.png"))


def crop_frac(path: Path, box: tuple, out: Path) -> Path:
    im = Image.open(path)
    w, h = im.size
    im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))).save(out)
    return out


def trim(path: Path, out: Path, pad: int = 40) -> Path:
    """Crop the white page margins around the printed cells."""
    im = Image.open(path).convert("RGB")
    ink = im.convert("L").point(lambda v: 255 if v < 245 else 0)  # anything darker than near-white
    bbox = ink.getbbox()
    if bbox:
        im = im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad),
                      min(im.height, bbox[3] + pad)))
    im.save(out)
    return out


def main(res: dict, s: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p3up_"))
    build_outputs.chart_png(res["quality"], tmp / "cover_chart.png", big=True)
    make_cover(UP / "cover.png", 3, "Data cleaning", "Data Cleaning & Validation",
               f"{s['records_in']:,} raw supplier records → {s['records_out']:,} clean, deduplicated organisations",
               tmp / "cover_chart.png", "Python · pandas · Excel")

    # Real renders of the Excel deliverable (LibreOffice -> PDF -> PNG)
    sheets = ["Clean data", "Issues", "Cleaning log"]
    lo_recalc(build_outputs.XLSX, tmp / "v.xlsx", pdf=tmp / "xlsx.pdf", sheets=sheets, one_page=sheets,
              areas={"Clean data": "A1:I42", "Issues": "B1:E40", "Cleaning log": "B1:E21"})
    xl = pdf_pages(tmp / "xlsx.pdf", 300, tmp / "xl")
    for i, (label, name) in enumerate([("Clean Excel table: one row per organisation", "shot-1.png"),
                                       ("Issues sheet: every problem, field and action", "shot-2.png"),
                                       ("Cleaning log: 20 rules with the rows each one changed", "shot-5.png")]):
        make_shot(UP / name, trim(xl[i], tmp / f"x{i}.png"), label)
    rep = pdf_pages(build_outputs.PDF, 220, tmp / "rep")
    make_shot(UP / "shot-3.png", crop_frac(rep[0], (0.05, 0.03, 0.95, 0.50), tmp / "r1.png"),
              "Quality report, page 1: before vs after")
    make_shot(UP / "shot-4.png", crop_frac(rep[1], (0.05, 0.03, 0.95, 0.66), tmp / "r2.png"),
              "Quality report, page 2: registry cross-check")

    title = "Data Cleaning, Deduplication & Validation"
    desc = (
        "Supplier lists get messy: duplicates, placeholders, broken phones, IDs that fail validation. I cleaned "
        f"{s['records_in']:,} public supplier records from Colombia's SECOP II with Python: 20 logged rules, tax-ID "
        "check digits, phone, e-mail and address standards, DANE codes and a cross-check with the business "
        f"registry. Result: {s['records_out']:,} clean organisations, {s['duplicates']} duplicates removed and "
        f"{s['not_renewed']} suppliers whose registration was not renewed for 2026. "
        "Sample project built with public data."
    )
    skills = ["Data Cleaning", "Data Entry", "Python", "Microsoft Excel", "Data Analysis"]
    q = res["quality"].set_index("field")
    captions = [
        f"The clean Excel file: {s['records_out']:,} organisations with a validated tax ID (NIT with check digit), "
        "standard name, +57 phone, e-mail, website, address, DANE municipality code and registry status.",
        "Issues sheet: one row per problem found (field, issue, action taken), ready to filter and assign. "
        "Values that could not be fixed with certainty are flagged, never guessed.",
        f"Two-page quality report. Example: records with a standard address went from "
        f"{q.loc['Address (standard format)', 'usable_before_pct']:.0f}% to "
        f"{q.loc['Address (standard format)', 'usable_after_pct']:.0f}%, and a valid unique tax ID from "
        f"{q.loc['NIT (valid, unique)', 'usable_before_pct']:.0f}% to {q.loc['NIT (valid, unique)', 'usable_after_pct']:.0f}%.",
        f"Cross-check with the chamber-of-commerce registry: {s['not_renewed']} active registrations not renewed for "
        f"2026, {s['liquidation']} companies in liquidation and {s['cancelled']} cancelled registrations.",
        "Every rule is logged with the rows or cells it changed, including the privacy rules: personal IDs excluded, "
        "personal-looking e-mails masked and mobile numbers partly hidden.",
    ]
    links = [f"GitHub project folder: {config.folder_url(FOLDER)}",
             f"Quality report (PDF): {config.file_url(FOLDER + '/output/quality_report.pdf')}",
             f"Clean Excel file: {config.file_url(FOLDER + '/output/suppliers_clean.xlsx')}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
