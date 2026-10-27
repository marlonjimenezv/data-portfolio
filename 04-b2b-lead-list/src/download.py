"""Sources for the lead list (all open data, organisation-level only).

1. MEN - Instituciones de Educación Superior (datos.gov.co n5yy-8nav, CC BY-SA 4.0): official registry of
   Colombian higher-education institutions with address, phone and website.
2. MEN - Matrícula estadística de educación superior (datos.gov.co 5wck-szir, CC BY-SA 4.0): enrolled students
   per institution, used as a size indicator (aggregated with SoQL, no student-level data is downloaded).
3. Wikidata (CC0): official websites (property P856) of Colombian higher-education institutions, used only
   to fill websites missing in the registry. One SPARQL query.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
from fetch_utils import USER_AGENT, socrata_json  # noqa: E402

RAW = PROJECT / "data" / "raw"
REGISTRY = RAW / "men_ies_registry.csv"
ENROLMENT = RAW / "men_enrolment_by_ies.csv"
WIKIDATA = RAW / "wikidata_ies_websites.csv"

SPARQL = """
SELECT DISTINCT ?item ?label ?web WHERE {
  ?item wdt:P17 wd:Q739 ;
        wdt:P856 ?web ;
        wdt:P31/wdt:P279* ?type .
  VALUES ?type { wd:Q38723 wd:Q3918 wd:Q875538 wd:Q902104 }
  ?item rdfs:label ?label . FILTER(LANG(?label) = "es")
}"""


def registry() -> pd.DataFrame:
    if not REGISTRY.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(socrata_json("n5yy-8nav", {"$limit": 5000})).to_csv(REGISTRY, index=False)
    return pd.read_csv(REGISTRY, dtype=str, keep_default_na=False)


def enrolment() -> pd.DataFrame:
    """Total enrolled students per institution code, latest first semester available."""
    if not ENROLMENT.exists():
        latest = socrata_json("5wck-szir", {"$select": "max(a_o) as y"})[0]["y"]
        rows = socrata_json("5wck-szir", {
            "$select": "c_digo_de_la_instituci_n as code, sum(matriculados_2015) as students",
            "$where": f"a_o = '{latest}' AND semestre = '1'", "$group": "c_digo_de_la_instituci_n", "$limit": 5000})
        df = pd.DataFrame(rows)
        df["year"] = f"{latest}-1"
        df.to_csv(ENROLMENT, index=False)
    return pd.read_csv(ENROLMENT, dtype=str)


def wikidata() -> pd.DataFrame:
    if not WIKIDATA.exists():
        for attempt in range(4):
            r = requests.get("https://query.wikidata.org/sparql", params={"query": SPARQL},
                             headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
                             timeout=120)
            if r.status_code == 200:
                break
            time.sleep(10 * (attempt + 1))
        r.raise_for_status()
        rows = [{"item": b["item"]["value"], "label": b["label"]["value"], "web": b["web"]["value"]}
                for b in r.json()["results"]["bindings"]]
        pd.DataFrame(rows).to_csv(WIKIDATA, index=False)
    return pd.read_csv(WIKIDATA, dtype=str)


if __name__ == "__main__":
    print(registry().shape, enrolment().shape, wikidata().shape)
