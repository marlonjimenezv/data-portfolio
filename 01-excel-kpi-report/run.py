"""One command to rebuild project 01 from the raw data:  python run.py

1. Download + clean Online Retail II           -> data/clean/
2. Build the Excel report (2 passes)           -> output/ecommerce_kpi_report.xlsx
3. Recalculate in LibreOffice, 0 errors allowed -> output/ecommerce_kpi_report_snapshot.pdf
4. Cross-check the Excel KPIs against pandas
5. SQL bonus (SQLite + 13 queries)             -> output/sql_results.md
6. Upwork package                              -> upwork/
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT.parent / "common"))

import build_workbook  # noqa: E402
import clean  # noqa: E402
import make_upwork  # noqa: E402
import sql_bonus  # noqa: E402
from xlsx_values import lo_recalc, read_values  # noqa: E402

OUT = PROJECT / "output"
XLSX = OUT / "ecommerce_kpi_report.xlsx"
SNAPSHOT = OUT / "ecommerce_kpi_report_snapshot.pdf"


def expected_kpis(lines: pd.DataFrame) -> dict:
    """Same KPIs as the KPIs sheet (default period Dec 2010 - Nov 2011), computed with pandas."""
    cur = lines[(lines["InvoiceDate"] >= "2010-12-01") & (lines["InvoiceDate"] < "2011-12-01")]
    sales = cur[cur["Type"] == "Sale"]
    ident = sales[sales["CustomerID"] != "Guest"]
    orders_per_cust = ident.groupby("CustomerID")["Invoice"].nunique()
    intl = cur[cur["Country"] != "United Kingdom"].groupby("Country")["LineRevenue"].sum()
    prod = cur.groupby("StockCode")["LineRevenue"].sum()
    return {
        "Net revenue": cur["LineRevenue"].sum(),
        "Gross sales": sales["LineRevenue"].sum(),
        "Orders": sales["Invoice"].nunique(),
        "Average order value": sales["LineRevenue"].sum() / sales["Invoice"].nunique(),
        "Active customers": len(orders_per_cust),
        "Repeat customers": int((orders_per_cust > 1).sum()),
        "Top international market": intl.idxmax(),
        "Top product": prod.idxmax(),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print("[1/6] Cleaning data")
    tables = clean.main()

    print("[2/6] Building workbook (pass 1: formulas only)")
    tmp = Path(tempfile.mkdtemp(prefix="p1_"))
    positions = build_workbook.build(tmp / "pass1.xlsx")
    lo_recalc(tmp / "pass1.xlsx", tmp / "pass1_values.xlsx")
    values = read_values(tmp / "pass1_values.xlsx", positions)
    print(f"  pass 2: storing {len(values):,} calculated values")
    build_workbook.build(XLSX, values)

    print("[3/6] Verifying the final workbook in LibreOffice")
    lo_recalc(XLSX, tmp / "final_values.xlsx", pdf=SNAPSHOT, sheets=["KPIs", "Notes"], one_page=["KPIs"])

    print("[4/6] Cross-checking KPIs against pandas")
    got = read_values(tmp / "final_values.xlsx", [("KPIs", r, 3) for r in range(13, 26)]
                      + [("KPIs", 13, 8), ("KPIs", 30, 2)])
    k = {name: got[("KPIs", 13 + i, 3)] for i, name in enumerate(
        ["Net revenue", "Gross sales", "Returns", "Return rate", "Orders", "Average order value", "Units",
         "Active customers", "Repeat customers"])}
    k["Top international market"] = got[("KPIs", 13, 8)]
    k["Top product"] = got[("KPIs", 30, 2)]
    exp = expected_kpis(tables["lines"])
    for name, e in exp.items():
        g = k[name]
        ok = (abs(float(g) - float(e)) < 0.01) if not isinstance(e, str) else (str(g) == e)
        print(f"  {'OK ' if ok else 'BAD'} {name}: excel={g} pandas={e}")
        if not ok:
            raise SystemExit(f"KPI mismatch: {name}")
    shutil.rmtree(tmp, ignore_errors=True)

    print("[5/6] SQL bonus")
    sql_results = sql_bonus.main()

    print("[6/6] Upwork package")
    make_upwork.main(k, sql_results)
    print("Done.")


if __name__ == "__main__":
    main()
