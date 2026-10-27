"""One command to rebuild project 02:  python run.py

1. Download SECOP II contracts (education sector, signed in 2025)  -> data/raw/ (not in git)
2. Clean + star schema for Power BI                                 -> powerbi/data/
3. Interactive dashboard                                            -> output/dashboard.html, ../docs/procurement-dashboard/
4. Expected values for Power BI                                     -> powerbi/VALORES_ESPERADOS.md
5. Browser test: filters, KPIs vs pandas, console errors, phone width
6. Upwork package                                                   -> upwork/
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT.parent / "common"))

import build_dashboard  # noqa: E402
import clean  # noqa: E402
import make_upwork  # noqa: E402

PBI = PROJECT / "powerbi" / "data"


def model() -> pd.DataFrame:
    f = pd.read_csv(PBI / "fact_contracts.csv")
    f = f.merge(pd.read_csv(PBI / "dim_entity.csv"), on="entity_key")
    f = f.merge(pd.read_csv(PBI / "dim_modality.csv"), on="modality_key")
    f = f.merge(pd.read_csv(PBI / "dim_contract_type.csv"), on="contract_type_key")
    f["month"] = pd.to_datetime(f["date_signed"]).dt.month
    return f


def fmt_cop(x: float) -> str:  # same rules as fmtCOP() in the dashboard
    if x >= 1e12:
        return f"{x / 1e12:.2f} tn"
    if x >= 1e9:
        return f"{x / 1e9:.1f} bn"
    if x >= 1e6:
        return f"{x / 1e6:.1f}M"
    return f"{x:,.0f}"


def kpis(df: pd.DataFrame) -> dict:
    n = len(df)
    return {"n": f"{n:,}", "v": fmt_cop(df["contract_value"].sum()),
            "dir": f"{100 * df['is_direct'].sum() / n:.1f}%" if n else "–"}


def test_cases(f: pd.DataFrame) -> list[dict]:
    cases = [
        ("All contracts", {}, f),
        ("Department = Antioquia", {"#fDept": "Antioquia"}, f[f["department"] == "Antioquia"]),
        ("Jan-Mar, direct contracting", {"#fFrom": "Jan 2025", "#fTo": "Mar 2025", "#fGroup": "Direct contracting"},
         f[(f["month"] <= 3) & (f["modality_group"] == "Direct contracting")]),
        ("National level, companies", {"#fLevel": "National", "#fSupp": "Company / organisation"},
         f[(f["level"] == "National") & (f["supplier_type"] == "Company / organisation")]),
    ]
    return [{"name": n, "filters": flt, "expect": kpis(sub)} for n, flt, sub in cases]


def expected_values(f: pd.DataFrame, meta: dict) -> dict:
    n, v = len(f), f["contract_value"].sum()
    direct = f["is_direct"] == 1
    ant = f[f["department"] == "Antioquia"]
    vals = {
        "Total Contracts": f"{n:,}",
        "Total Value": f"{v:,.0f}",
        "Average Contract Value": f"{v / n:,.0f}",
        "Median Contract Value": f"{f['contract_value'].median():,.0f}",
        "Direct Contracting % (contracts)": f"{100 * direct.mean():.1f}%",
        "Direct Contracting % (value)": f"{100 * f.loc[direct, 'contract_value'].sum() / v:.1f}%",
        "Individuals % (contracts)": f"{100 * (f['supplier_type'] == 'Natural person').mean():.1f}%",
        "SME Suppliers %": f"{100 * f['is_sme'].mean():.1f}%",
        "Paid % of Value": f"{100 * f['paid_value'].sum() / v:.1f}%",
        "Value YTD (tarjeta sin filtro de fecha = todo 2025)": f"{v:,.0f}",
    }
    lines = ["# Valores esperados en Power BI", "",
             f"Extracción de datos: {meta['extracted_on']} ({meta['contracts']:,} contratos, {meta['entities']} entidades).",
             "Si vuelves a descargar los datos, estos números pueden cambiar porque SECOP II se actualiza todos los días;",
             "este archivo se regenera con `python run.py`.", "",
             "## Sin filtros", "", "| Medida | Valor esperado |", "|---|---|"]
    lines += [f"| {k} | {val} |" for k, val in vals.items()]
    lines += ["", "## Con el filtro `dim_entity[department]` = Antioquia", "", "| Medida | Valor esperado |", "|---|---|",
              f"| Total Contracts | {len(ant):,} |", f"| Total Value | {ant['contract_value'].sum():,.0f} |",
              f"| Direct Contracting % (contracts) | {100 * ant['is_direct'].mean():.1f}% |", "",
              "Formato: separador de miles con coma (como en Power BI en inglés). En Power BI en español verás puntos.", ""]
    (PROJECT / "powerbi" / "VALORES_ESPERADOS.md").write_text("\n".join(lines), encoding="utf-8")
    return vals


def main() -> None:
    print("[1-2/6] Download, clean and star schema")
    t = clean.build()
    print(t["log"].to_string(index=False))
    print("[3/6] Dashboard")
    build_dashboard.build()
    f = model()
    meta = json.loads((PROJECT / "data" / "clean" / "metadata.json").read_text())
    print("[4/6] Expected values for Power BI")
    vals = expected_values(f, meta)
    print("[5/6] Browser test")
    cases = test_cases(f)
    res = subprocess.run(["node", str(PROJECT / "tests" / "test_dashboard.js"), str(PROJECT / "output" / "dashboard.html"),
                          json.dumps(cases)], capture_output=True, text=True)
    print(res.stdout.rstrip())
    if res.returncode != 0:
        raise SystemExit(res.stderr)
    print("[6/6] Upwork package")
    make_upwork.main(f, vals, meta)
    print("Done.")


if __name__ == "__main__":
    main()
