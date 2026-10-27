"""Load the cleaned data into SQLite and run the business queries in sql/queries.sql.

Output: output/retail.db (not in git, rebuilt by run.py)
        output/sql_results.md (each question, its SQL and the result table)
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
CLEAN = PROJECT / "data" / "clean"
SQL = PROJECT / "sql"
OUT = PROJECT / "output"


def build_db(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript((SQL / "schema.sql").read_text())
    lines = pd.read_csv(CLEAN / "order_lines.csv.gz", dtype={"Invoice": str, "StockCode": str, "CustomerID": str})
    cust = pd.read_csv(CLEAN / "customers.csv", dtype=str)
    prod = pd.read_csv(CLEAN / "products.csv", dtype=str)

    inv = (lines.groupby("Invoice", sort=False)
           .agg(invoice_date=("InvoiceDate", "min"), type=("Type", "first"),
                customer_id=("CustomerID", "first"), country=("Country", "first"))
           .reset_index().rename(columns={"Invoice": "invoice_no"}))
    inv["month"] = inv["invoice_date"].str[:7]
    inv.loc[inv["customer_id"] == "Guest", "customer_id"] = None

    con.executemany("INSERT INTO customers VALUES (?, ?)", cust[["CustomerID", "Country"]].itertuples(index=False))
    con.executemany("INSERT INTO products VALUES (?, ?)", prod[["StockCode", "Description"]].itertuples(index=False))
    con.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?)",
                    inv[["invoice_no", "invoice_date", "month", "type", "customer_id", "country"]]
                    .itertuples(index=False))
    con.executemany("INSERT INTO invoice_lines VALUES (?, ?, ?, ?, ?)",
                    lines[["Invoice", "StockCode", "Quantity", "Price", "LineRevenue"]].itertuples(index=False))
    con.commit()
    return con


def split_queries(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^-- (Q\d+: .+)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        sql = parts[i + 1].strip()
        out.append((parts[i].strip(), sql))
    return out


def to_markdown(df: pd.DataFrame, max_rows: int = 25) -> str:
    df = df.head(max_rows)
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for rec in df.itertuples(index=False):
        cells = []
        for v in rec:
            if isinstance(v, float):
                cells.append("" if pd.isna(v) else f"{v:,.2f}")
            elif isinstance(v, int):
                cells.append(f"{v:,}")
            else:
                cells.append("" if v is None else str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def main() -> dict[str, pd.DataFrame]:
    OUT.mkdir(exist_ok=True)
    con = build_db(OUT / "retail.db")
    queries = split_queries((SQL / "queries.sql").read_text())
    md = ["# SQL results: business questions on the Online Retail II data", "",
          "Sample project built with public data (Online Retail II, UCI ML Repository, CC BY 4.0).",
          "Database: SQLite, built by `src/sql_bonus.py` from the cleaned data. Queries: `sql/queries.sql`.",
          "FY2011 = December 2010 to November 2011. Amounts in GBP.", ""]
    results = {}
    for title, sql in queries:
        df = pd.read_sql_query(sql, con)
        results[title.split(":")[0]] = df
        md += [f"## {title}", "", "```sql", sql, "```", "", to_markdown(df), ""]
    (OUT / "sql_results.md").write_text("\n".join(md), encoding="utf-8")
    con.close()
    print(f"  SQL: {len(queries)} queries run, results in output/sql_results.md")
    return results


if __name__ == "__main__":
    main()
