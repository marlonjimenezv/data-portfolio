"""LibreOffice helpers (run with the system python, which has the `uno` module).

Usage:
  /usr/bin/python3 common/lo_tools.py recalc  <in.xlsx> <out_values.xlsx> [--pdf out.pdf --sheets KPIs,Notes]
                                               [--one-page KPIs]   (A3 landscape, 1 page, PDF only)
                                               [--areas "Sheet=A1:M30;Other=A1:F20"]  (print areas, PDF only)

`recalc` opens the workbook in headless LibreOffice, recalculates every formula,
fails if any formula returns an error (#REF!, #DIV/0!, #NAME?, #VALUE!, ...),
saves a copy with the calculated values, and optionally exports some sheets to PDF
(used for screenshots).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import uno  # noqa: F401  (system LibreOffice bridge)
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException


def _prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def _connect(pipe: str):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
            return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        except NoConnectException:
            time.sleep(0.5)
    raise RuntimeError("Could not connect to LibreOffice")


def recalc(src: str, out_values: str, pdf: str | None = None, sheets: list[str] | None = None,
           max_rows: int = 45, one_page: list[str] | None = None, areas: dict | None = None) -> int:
    pipe = f"lo_{os.getpid()}"
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    proc = subprocess.Popen([
        "soffice", "--headless", "--invisible", "--nologo", "--norestore", "--nodefault",
        f"-env:UserInstallation=file://{profile}", f"--accept=pipe,name={pipe};urp;",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        desktop = _connect(pipe)
        url = uno.systemPathToFileUrl(str(Path(src).resolve()))
        doc = desktop.loadComponentFromURL(url, "_blank", 0, (_prop("Hidden", True),))
        doc.calculateAll()

        errors = 0
        formulas = 0
        for i in range(doc.Sheets.Count):
            sheet = doc.Sheets.getByIndex(i)
            # FORMULA flag = 16 ; FormulaResult.ERROR = 4
            all_f = sheet.queryContentCells(16)
            formulas += sum(
                (r.EndColumn - r.StartColumn + 1) * (r.EndRow - r.StartRow + 1)
                for r in all_f.getRangeAddresses())
            bad = sheet.queryFormulaCells(4)
            for r in bad.getRangeAddresses():
                n = (r.EndColumn - r.StartColumn + 1) * (r.EndRow - r.StartRow + 1)
                errors += n
                cell = sheet.getCellByPosition(r.StartColumn, r.StartRow)
                print(f"  ERROR in {sheet.Name}!R{r.StartRow + 1}C{r.StartColumn + 1} "
                      f"({n} cells): {cell.getFormula()} -> {cell.getString()}")
        print(f"  LibreOffice recalculation: {formulas} formula cells, {errors} errors")

        out_url = uno.systemPathToFileUrl(str(Path(out_values).resolve()))
        doc.storeToURL(out_url, (_prop("FilterName", "Calc MS Excel 2007 XML"),))

        if pdf:
            from com.sun.star.table import CellRangeAddress
            keep = set(sheets or [])
            for i in range(doc.Sheets.Count):
                sh = doc.Sheets.getByIndex(i)
                sh.IsVisible = (not keep) or sh.Name in keep
                if sh.IsVisible:
                    cur = sh.createCursor()
                    cur.gotoEndOfUsedArea(False)
                    last_row, last_col = cur.RangeAddress.EndRow, cur.RangeAddress.EndColumn
                    if areas and sh.Name in areas:
                        sh.setPrintAreas((sh.getCellRangeByName(areas[sh.Name]).getRangeAddress(),))
                    elif last_row > max_rows and not sh.getPrintAreas():
                        area = CellRangeAddress()
                        area.Sheet, area.StartColumn, area.StartRow = i, 0, 0
                        area.EndColumn, area.EndRow = last_col, max_rows - 1
                        sh.setPrintAreas((area,))
                    if sh.Name in (one_page or []):
                        style = doc.StyleFamilies.getByName("PageStyles").getByName(sh.PageStyle)
                        style.IsLandscape = True
                        style.Width, style.Height = 42000, 29700  # A3 landscape, 1/100 mm
                        style.ScaleToPagesX, style.ScaleToPagesY = 1, 1
            pdf_url = uno.systemPathToFileUrl(str(Path(pdf).resolve()))
            doc.storeToURL(pdf_url, (_prop("FilterName", "calc_pdf_Export"),))
        doc.close(True)
        return errors
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] != "recalc":
        raise SystemExit(__doc__)
    src, out = args[1], args[2]
    pdf = args[args.index("--pdf") + 1] if "--pdf" in args else None
    sheets = args[args.index("--sheets") + 1].split(",") if "--sheets" in args else None
    one = args[args.index("--one-page") + 1].split(",") if "--one-page" in args else None
    areas = (dict(x.split("=") for x in args[args.index("--areas") + 1].split(";"))
             if "--areas" in args else None)
    n_err = recalc(src, out, pdf, sheets, one_page=one, areas=areas)
    sys.exit(1 if n_err else 0)
