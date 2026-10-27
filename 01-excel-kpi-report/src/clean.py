"""Download and clean the Online Retail II data (UCI, CC BY 4.0).

Input : data/raw/online_retail_II.xlsx (two sheets, 1,067,371 invoice lines)
Output: data/clean/orders.csv          one row per invoice (sales and returns)
        data/clean/product_month.csv   net units and revenue per product and month
        data/clean/products.csv        one clean description per stock code
        data/clean/customers.csv       one row per identified customer
        data/clean/cleaning_log.csv    every rule applied and the rows it removed
        data/clean/order_lines.csv.gz  clean invoice lines (used by the SQL bonus; not in git)
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
from fetch_utils import fetch  # noqa: E402

RAW = PROJECT / "data" / "raw"
CLEAN = PROJECT / "data" / "clean"
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"

PERIOD_START = pd.Timestamp("2009-12-01")
PERIOD_END = pd.Timestamp("2011-12-01")  # exclusive: Dec 2011 is only 9 days, so it is dropped

# Stock codes that are not products: postage, fees, manual adjustments, tests and gift vouchers.
NON_PRODUCT_CODES = {
    "POST": "postage", "DOT": "dotcom postage", "C2": "carriage", "M": "manual adjustment",
    "m": "manual adjustment", "D": "discount", "S": "samples", "B": "bad-debt adjustment",
    "BANK CHARGES": "bank charges", "ADJUST": "manual adjustment", "ADJUST2": "manual adjustment",
    "AMAZONFEE": "Amazon fee", "TEST001": "test", "TEST002": "test", "PADS": "padding (0.001 GBP)",
    "CRUK": "charity commission",
}


def load_raw() -> pd.DataFrame:
    cache = RAW / "online_retail_II.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    zpath = fetch(URL, RAW / "online_retail_ii.zip", min_bytes=40_000_000)
    with zipfile.ZipFile(zpath) as z:
        z.extract("online_retail_II.xlsx", RAW)
    sheets = pd.read_excel(RAW / "online_retail_II.xlsx", sheet_name=None,
                           dtype={"Invoice": str, "StockCode": str, "Description": str})
    df = pd.concat(sheets.values(), ignore_index=True)
    df.to_pickle(cache)
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log = []

    def step(rule: str, new: pd.DataFrame, before: pd.DataFrame, note: str = "") -> pd.DataFrame:
        log.append({"step": len(log), "rule": rule, "rows_before": len(before),
                    "rows_removed": len(before) - len(new), "rows_after": len(new), "note": note})
        return new

    log.append({"step": 0, "rule": "Load both sheets (2009-2010 and 2010-2011)", "rows_before": 0,
                "rows_removed": 0, "rows_after": len(df), "note": "Raw invoice lines"})
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()

    d = step("Remove exact duplicate lines", df.drop_duplicates(), df,
             "Includes 1-9 Dec 2010, which appears in both sheets")
    d = step("Keep 24 full months (Dec 2009 - Nov 2011)",
             d[(d["InvoiceDate"] >= PERIOD_START) & (d["InvoiceDate"] < PERIOD_END)], d,
             "Dec 2011 has only 9 days of data")
    is_nonproduct = d["StockCode"].isin(NON_PRODUCT_CODES) | d["StockCode"].str.startswith("gift_")
    d = step("Remove non-product codes", d[~is_nonproduct], d,
             "Postage, fees, adjustments, tests and gift vouchers (" + ", ".join(sorted(set(NON_PRODUCT_CODES))) + ", gift_*)")
    d = step("Remove lines with price <= 0", d[d["Price"] > 0], d, "Free items and stock write-offs")
    is_return = d["Invoice"].str.startswith("C")
    d = step("Check: sales lines with quantity <= 0", d[is_return | (d["Quantity"] > 0)], d,
             "Validation only: none left after the price rule")

    d = d.copy()
    lower = d["StockCode"].str.contains("[a-z]", regex=True)
    n_codes = d.loc[lower, "StockCode"].nunique()
    d["StockCode"] = d["StockCode"].str.upper()
    log.append({"step": len(log), "rule": "Upper-case stock codes", "rows_before": len(d), "rows_removed": 0,
                "rows_after": len(d),
                "note": f"{lower.sum():,} lines / {n_codes} codes such as 85123a -> 85123A "
                        "(Excel lookups ignore case, so variants would be double-counted)"})
    d["Type"] = d["Invoice"].str.startswith("C").map({True: "Return", False: "Sale"})
    d["CustomerID"] = d["Customer ID"].map(lambda x: "Guest" if pd.isna(x) else str(int(x)))
    d["Country"] = d["Country"].str.strip()
    # One description per product: the most frequent one, trimmed and upper-case.
    desc = (d.assign(Description=d["Description"].fillna("").str.strip().str.upper())
              .query("Description != ''")
              .groupby(["StockCode", "Description"]).size().reset_index(name="n")
              .sort_values(["StockCode", "n"], ascending=[True, False])
              .drop_duplicates("StockCode")[["StockCode", "Description"]])
    n_multi = d.groupby("StockCode")["Description"].nunique().gt(1).sum()
    d = d.drop(columns=["Description"]).merge(desc, on="StockCode", how="left")
    d["Description"] = d["Description"].fillna("(no description)")
    log.append({"step": len(log), "rule": "Standardise text fields", "rows_before": len(d),
                "rows_removed": 0, "rows_after": len(d),
                "note": f"One description per stock code ({n_multi} codes had several); "
                        "missing customer IDs labelled 'Guest'"})
    d["LineRevenue"] = (d["Quantity"] * d["Price"]).round(2)
    d["InvoiceDate"] = d["InvoiceDate"].dt.floor("min")
    return d, pd.DataFrame(log)


def build_tables(lines: pd.DataFrame) -> dict[str, pd.DataFrame]:
    lines = lines.assign(Month=lines["InvoiceDate"].dt.to_period("M").dt.to_timestamp())
    orders = (lines.groupby("Invoice", sort=False)
              .agg(InvoiceDate=("InvoiceDate", "min"), Month=("Month", "first"), Type=("Type", "first"),
                   CustomerID=("CustomerID", "first"), Country=("Country", "first"),
                   Lines=("StockCode", "size"), Units=("Quantity", "sum"), NetRevenue=("LineRevenue", "sum"))
              .reset_index().rename(columns={"Invoice": "InvoiceNo"})
              .sort_values(["InvoiceDate", "InvoiceNo"]))
    orders["InvoiceDate"] = orders["InvoiceDate"].dt.normalize()
    orders["NetRevenue"] = orders["NetRevenue"].round(2)

    sales = lines[lines["Type"] == "Sale"]
    pm = (lines.groupby(["StockCode", "Month"])
          .agg(Units=("Quantity", "sum"), NetRevenue=("LineRevenue", "sum")).reset_index())
    pm_orders = sales.groupby(["StockCode", "Month"])["Invoice"].nunique().rename("Orders")
    pm = pm.merge(pm_orders, on=["StockCode", "Month"], how="left").fillna({"Orders": 0})
    pm["Orders"] = pm["Orders"].astype(int)
    pm["NetRevenue"] = pm["NetRevenue"].round(2)
    pm = pm.sort_values(["StockCode", "Month"])

    products = (lines.drop_duplicates("StockCode")[["StockCode", "Description"]]
                .sort_values("StockCode").reset_index(drop=True))
    cust = lines[lines["CustomerID"] != "Guest"]
    customers = (cust.groupby(["CustomerID", "Country"]).size().reset_index(name="n")
                 .sort_values(["CustomerID", "n"], ascending=[True, False])
                 .drop_duplicates("CustomerID")[["CustomerID", "Country"]])
    customers = customers.assign(_k=customers["CustomerID"].astype(int)).sort_values("_k").drop(columns="_k")
    return {"orders": orders, "product_month": pm, "products": products, "customers": customers}


def main() -> dict[str, pd.DataFrame]:
    CLEAN.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    lines, log = clean(raw)
    tables = build_tables(lines)
    for name, t in tables.items():
        t.to_csv(CLEAN / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    log.to_csv(CLEAN / "cleaning_log.csv", index=False)
    lines[["Invoice", "StockCode", "Description", "Quantity", "Price", "LineRevenue", "InvoiceDate",
           "CustomerID", "Country", "Type"]].to_csv(CLEAN / "order_lines.csv.gz", index=False,
                                                    date_format="%Y-%m-%d %H:%M:%S")
    tables["lines"] = lines
    tables["log"] = log
    print(log[["step", "rule", "rows_removed", "rows_after"]].to_string(index=False))
    return tables


if __name__ == "__main__":
    main()
