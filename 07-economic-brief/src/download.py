"""Download the official series used in the brief into data/raw/ and record where and when each came from.

Sources (all public, reuse allowed with citation):
- DANE, IPC index series 2003-today (monthly, Dec 2018 = 100). The annex file name changes every month, so its
  link is read from the DANE IPC page.
- ILOSTAT (ILO SDMX API): statutory nominal gross monthly minimum wage, local currency and 2021 PPP dollars.
- World Bank WDI API: GDP per person employed, constant 2021 PPP $ (SL.GDP.PCAP.EM.KD).
- OECD Data Explorer API: minimum wage relative to the median wage of full-time workers.
The 2025 minimum wage (not yet in ILOSTAT) is a manual input from the decree: data/manual/minimum_wage_decrees.csv.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
from fetch_utils import USER_AGENT, fetch  # noqa: E402

RAW = PROJECT / "data" / "raw"
SOURCES = PROJECT / "data" / "clean" / "sources_accessed.json"

DANE_PAGE = ("https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/"
             "indice-de-precios-al-consumidor-ipc")
ILO = "https://sdmx.ilo.org/rest/data/ILO,DF_EAR_INEE_CUR_NB,1.0/{key}?startPeriod={start}"
LATAM = ["ARG", "BOL", "BRA", "CHL", "COL", "CRI", "DOM", "ECU", "GTM", "HND", "MEX", "NIC", "PAN", "PER", "PRY",
         "SLV", "URY", "VEN"]
WB = "https://api.worldbank.org/v2/country/COL/indicator/SL.GDP.PCAP.EM.KD?format=json&per_page=100&date=2000:2030"
OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.ELS.SAE,DSD_EARNINGS@MIN2AVE,1.0/......."
        "?startPeriod=2015&format=csvfilewithlabels")
CSV_ACCEPT = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0", "User-Agent": USER_AGENT}


def _get(url: str, dest: Path, headers: dict | None = None, min_bytes: int = 500) -> str:
    """Download with custom headers (SDMX APIs need an Accept header). Returns the URL used."""
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return url
    r = requests.get(url, headers=headers or {"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    if len(r.content) < min_bytes:
        raise RuntimeError(f"{url} returned only {len(r.content)} bytes")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return url


def dane_annex_url() -> str:
    html = requests.get(DANE_PAGE, headers={"User-Agent": "Mozilla/5.0 " + USER_AGENT}, timeout=60).text
    links = re.findall(r'href="([^"]*anex-IPC-Indices-[^"]*\.xlsx)"', html)
    if not links:
        raise RuntimeError("IPC index annex link not found on the DANE page")
    return "https://www.dane.gov.co" + links[0] if links[0].startswith("/") else links[0]


def main() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    previous = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    used = {}

    dest = RAW / "dane_ipc_indices.xlsx"
    url = previous.get("dane_ipc", {}).get("url") if dest.exists() else dane_annex_url()
    fetch(url, dest, min_bytes=10_000)
    used["dane_ipc"] = url

    used["ilo_col"] = _get(ILO.format(key="COL.A.EAR_INEE_NB.", start=2000), RAW / "ilo_min_wage_col.csv",
                           CSV_ACCEPT)
    used["ilo_latam_ppp"] = _get(ILO.format(key="+".join(LATAM) + ".A.EAR_INEE_NB.CUR_TYPE_PPP", start=2019),
                                 RAW / "ilo_min_wage_latam_ppp.csv", CSV_ACCEPT)
    used["wb_productivity"] = _get(WB, RAW / "wb_gdp_per_worker_col.json")
    used["oecd_min_to_median"] = _get(OECD, RAW / "oecd_min_to_median.csv", {"User-Agent": USER_AGENT})

    # Keep the first access date of each file that has not changed; new downloads get today's date.
    record = {k: {"url": u, "accessed": previous.get(k, {}).get("accessed", today)
                  if previous.get(k, {}).get("url") == u else today} for k, u in used.items()}
    SOURCES.parent.mkdir(parents=True, exist_ok=True)
    SOURCES.write_text(json.dumps(record, indent=1))
    return record


if __name__ == "__main__":
    for k, v in main().items():
        print(f"{k:20s} {v['accessed']}  {v['url']}")
