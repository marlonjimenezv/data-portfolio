"""Turn the raw downloads into tidy tables and the numbers quoted in the brief.

Outputs (data/clean/):
- colombia_minimum_wage.csv     one row per year 2004-2025: wage, increase, inflation, real wage, productivity
- latam_minimum_wage_ppp.csv    latest comparable year, 2021 PPP dollars per month
- oecd_minimum_to_median.csv    latest year, minimum wage as % of the median full-time wage
- results.json                  every figure quoted in the brief
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw"
CLEAN = PROJECT / "data" / "clean"
MANUAL = PROJECT / "data" / "manual" / "minimum_wage_decrees.csv"
START, END = 2004, 2025          # base year of the indexes; last year with complete inflation data
MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
          "Noviembre", "Diciembre"]
LATAM_NAMES = {"ARG": "Argentina", "BOL": "Bolivia", "BRA": "Brazil", "CHL": "Chile", "COL": "Colombia",
               "CRI": "Costa Rica", "DOM": "Dominican Rep.", "ECU": "Ecuador", "GTM": "Guatemala", "HND": "Honduras",
               "MEX": "Mexico", "NIC": "Nicaragua", "PAN": "Panama", "PER": "Peru", "PRY": "Paraguay",
               "SLV": "El Salvador", "URY": "Uruguay", "VEN": "Venezuela"}


def dane_cpi() -> pd.DataFrame:
    """Monthly CPI from the DANE annex: a 'Mes' header row with years, then one row per month."""
    ws = openpyxl.load_workbook(RAW / "dane_ipc_indices.xlsx", data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if r and r[0] == "Mes")
    years = [(j, int(y)) for j, y in enumerate(rows[h]) if isinstance(y, (int, float))]
    recs = []
    for r in rows[h + 1:h + 13]:
        m = MONTHS.index(r[0]) + 1
        recs += [{"year": y, "month": m, "cpi": float(r[j])} for j, y in years if isinstance(r[j], (int, float))]
    cpi = pd.DataFrame(recs)
    if cpi.groupby("year").size().loc[START - 1:END].lt(12).any():
        raise SystemExit("DANE CPI: a year in the study period is incomplete")
    return cpi


def ilo_series(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, dtype={"TIME_PERIOD": int})
    return d[["REF_AREA", "CUR", "TIME_PERIOD", "OBS_VALUE", "SOURCE"]].rename(
        columns={"REF_AREA": "country", "CUR": "unit", "TIME_PERIOD": "year", "OBS_VALUE": "value", "SOURCE": "source"})


def colombia_table(cpi: pd.DataFrame) -> pd.DataFrame:
    ilo = ilo_series(RAW / "ilo_min_wage_col.csv")
    mw = ilo[ilo["unit"] == "CUR_TYPE_LCU"].set_index("year")["value"].astype(float)
    manual = pd.read_csv(MANUAL).set_index("year")
    for y in manual.index:
        if y <= END and y not in mw.index:
            mw.loc[y] = float(manual.loc[y, "minimum_wage_cop"])
    mw = mw.sort_index()
    if list(mw.loc[START - 1:END].index) != list(range(START - 1, END + 1)):
        raise SystemExit("Minimum wage series has gaps")

    dec = cpi[cpi["month"] == 12].set_index("year")["cpi"]
    avg = cpi.groupby("year")["cpi"].mean()
    wb = json.loads((RAW / "wb_gdp_per_worker_col.json").read_text())[1]
    prod = pd.Series({int(x["date"]): x["value"] for x in wb if x["value"] is not None}).sort_index()

    t = pd.DataFrame(index=pd.RangeIndex(START, END + 1, name="year"))
    t["minimum_wage_cop"] = mw
    t["increase_pct"] = (mw / mw.shift(1) - 1).loc[t.index] * 100
    t["inflation_dec_dec_pct"] = (dec / dec.shift(1) - 1).loc[t.index] * 100
    t["inflation_prev_year_pct"] = t["inflation_dec_dec_pct"].shift(1)
    t.loc[START, "inflation_prev_year_pct"] = (dec.loc[START - 1] / dec.loc[START - 2] - 1) * 100 \
        if START - 2 in dec.index else float("nan")
    t["real_increase_vs_prev_inflation_pp"] = t["increase_pct"] - t["inflation_prev_year_pct"]
    t["cpi_annual_avg"] = avg.loc[t.index]
    t["real_wage_cop_2025_prices"] = t["minimum_wage_cop"] * avg.loc[END] / t["cpi_annual_avg"]
    t["real_wage_index"] = t["real_wage_cop_2025_prices"] / t.loc[START, "real_wage_cop_2025_prices"] * 100
    t["gdp_per_worker_ppp2021"] = prod.reindex(t.index)
    t["productivity_index"] = t["gdp_per_worker_ppp2021"] / t.loc[START, "gdp_per_worker_ppp2021"] * 100
    t["source_wage"] = ["Decreto 1572 de 2024" if y in manual.index else "ILOSTAT" for y in t.index]
    return t.round({"increase_pct": 2, "inflation_dec_dec_pct": 2, "inflation_prev_year_pct": 2,
                    "real_increase_vs_prev_inflation_pp": 2, "cpi_annual_avg": 3, "real_wage_cop_2025_prices": 0,
                    "real_wage_index": 1, "gdp_per_worker_ppp2021": 1, "productivity_index": 1})


def latam_table() -> tuple[pd.DataFrame, int, list[str]]:
    d = ilo_series(RAW / "ilo_min_wage_latam_ppp.csv")
    p = d.pivot_table(index="country", columns="year", values="value")
    src = d.pivot_table(index="country", columns="year", values="source", aggfunc="first")
    year = int(p.columns.max())
    # Series breaks: a fall of more than 80% in one year together with a change of source is not a real change.
    breaks = [c for c in p.index if pd.notna(p.loc[c, year]) and pd.notna(p.loc[c, year - 1])
              and p.loc[c, year] < 0.2 * p.loc[c, year - 1] and src.loc[c, year] != src.loc[c, year - 1]]
    out = p[[year, year - 1]].drop(index=breaks).dropna(subset=[year]).rename(
        columns={year: "ppp_usd_month", year - 1: "ppp_usd_month_prev_year"})
    out.insert(0, "name", [LATAM_NAMES[c] for c in out.index])
    out["year"] = year
    return out.sort_values("ppp_usd_month", ascending=False).round(1), year, [LATAM_NAMES[c] for c in breaks]


def oecd_table() -> tuple[pd.DataFrame, int, pd.Series]:
    d = pd.read_csv(RAW / "oecd_min_to_median.csv")
    d = d[d["AGGREGATION_OPERATION"] == "MEDIAN"]
    p = d.pivot_table(index=["REF_AREA", "Reference area"], columns="TIME_PERIOD", values="OBS_VALUE")
    counts = p.notna().sum()
    year = int(counts[counts >= 0.9 * counts.max()].index.max())   # latest year with near-full coverage
    out = p[year].dropna().reset_index().rename(columns={"REF_AREA": "country", "Reference area": "name",
                                                        year: "min_to_median_pct"})
    out["year"] = year
    col = p.xs("COL", level=0).iloc[0].dropna()
    return out.sort_values("min_to_median_pct", ascending=False).round(1), year, col


def main() -> dict:
    CLEAN.mkdir(parents=True, exist_ok=True)
    cpi = dane_cpi()
    t = colombia_table(cpi)
    latam, l_year, breaks = latam_table()
    oecd, o_year, col_ratio = oecd_table()
    t.to_csv(CLEAN / "colombia_minimum_wage.csv")
    latam.to_csv(CLEAN / "latam_minimum_wage_ppp.csv")
    oecd.to_csv(CLEAN / "oecd_minimum_to_median.csv", index=False)

    manual = pd.read_csv(MANUAL).set_index("year")
    gap = t["real_increase_vs_prev_inflation_pp"].dropna()
    recent = t.loc[2022:END]
    r = {
        "start": START, "end": END,
        "wage_start": int(t.loc[START, "minimum_wage_cop"]), "wage_end": int(t.loc[END, "minimum_wage_cop"]),
        "nominal_growth_pct": round((t.loc[END, "minimum_wage_cop"] / t.loc[START, "minimum_wage_cop"] - 1) * 100, 1),
        "prices_growth_pct": round((t.loc[END, "cpi_annual_avg"] / t.loc[START, "cpi_annual_avg"] - 1) * 100, 1),
        "real_growth_pct": round(t.loc[END, "real_wage_index"] - 100, 1),
        "productivity_growth_pct": round(t.loc[END, "productivity_index"] - 100, 1),
        "productivity_last_year": int(t["gdp_per_worker_ppp2021"].last_valid_index()),
        "compare_first": int(gap.index[0]), "compare_years": int(len(gap)),
        "years_above_prev_inflation": int((gap >= 0.05).sum()),
        "years_matching_prev_inflation": {int(y): [float(t.loc[y, "increase_pct"]), float(t.loc[y, "inflation_prev_year_pct"])]
                                          for y in gap.index[gap.abs() < 0.05]},
        "years_below_prev_inflation": [int(y) for y in gap.index[gap <= -0.05]],
        "avg_gap_to_2021_pp": round(float(gap.loc[:2021].mean()), 2),
        "avg_gap_2022_on_pp": round(float(gap.loc[2022:].mean()), 2),
        "recent": {int(y): {"increase": float(recent.loc[y, "increase_pct"]),
                            "prev_inflation": float(recent.loc[y, "inflation_prev_year_pct"]),
                            "inflation": float(recent.loc[y, "inflation_dec_dec_pct"])} for y in recent.index},
        "real_growth_2022_2025_pct": round((t.loc[END, "real_wage_index"] / t.loc[2022, "real_wage_index"] - 1) * 100, 1),
        "productivity_growth_2022_2025_pct": round((t.loc[END, "productivity_index"] / t.loc[2022, "productivity_index"] - 1) * 100, 1),
        "inflation_peak": {"year": int(t["inflation_dec_dec_pct"].idxmax()),
                           "value": float(t["inflation_dec_dec_pct"].max())},
        "latam_year": l_year, "latam_n": int(len(latam)), "latam_breaks": breaks,
        "latam_col": float(latam.loc["COL", "ppp_usd_month"]),
        "latam_col_rank": int(list(latam.index).index("COL") + 1),
        "latam_median": round(float(latam["ppp_usd_month"].median()), 1),
        "latam_top": [latam.iloc[0]["name"], float(latam.iloc[0]["ppp_usd_month"])],
        "latam_bottom": [latam.iloc[-1]["name"], float(latam.iloc[-1]["ppp_usd_month"])],
        "oecd_year": o_year, "oecd_n": int(len(oecd)),
        "oecd_col": float(oecd.loc[oecd["country"] == "COL", "min_to_median_pct"].iloc[0]),
        "oecd_col_rank": int(list(oecd["country"]).index("COL") + 1),
        "oecd_median": round(float(oecd["min_to_median_pct"].median()), 1),
        "oecd_second": [oecd.iloc[1]["name"], float(oecd.iloc[1]["min_to_median_pct"])],
        "col_ratio_first": [int(col_ratio.index[0]), round(float(col_ratio.iloc[0]), 1)],
        "col_ratio_last": [int(col_ratio.index[-1]), round(float(col_ratio.iloc[-1]), 1)],
        "wage_2026": int(manual.loc[2026, "minimum_wage_cop"]),
        "increase_2026_pct": round((manual.loc[2026, "minimum_wage_cop"] / t.loc[END, "minimum_wage_cop"] - 1) * 100, 1),
        "cpi_latest": {"year": int(cpi.iloc[-1]["year"]), "month": int(cpi.iloc[-1]["month"])},
    }
    (CLEAN / "results.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    return r


if __name__ == "__main__":
    res = main()
    print(json.dumps(res, indent=1, ensure_ascii=False))
    print(pd.read_csv(CLEAN / "colombia_minimum_wage.csv").to_string())
