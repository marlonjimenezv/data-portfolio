"""Small, polite download helper shared by the projects."""
from __future__ import annotations

import time
from pathlib import Path

import requests

USER_AGENT = "data-portfolio/1.0 (sample analytics project; contact via GitHub)"


def fetch(url: str, dest: Path, min_bytes: int = 1, params: dict | None = None,
          retries: int = 4, timeout: int = 300) -> Path:
    """Download `url` to `dest` unless it already exists. Retries with backoff."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(retries):
        try:
            with requests.get(url, params=params, stream=True, timeout=timeout,
                              headers={"User-Agent": USER_AGENT}) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            if tmp.stat().st_size < min_bytes:
                raise IOError(f"Downloaded file is too small ({tmp.stat().st_size} bytes)")
            tmp.replace(dest)
            return dest
        except Exception as err:  # network hiccups: wait and retry
            last_err = err
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Could not download {url}: {last_err}")


def socrata_json(dataset: str, params: dict, domain: str = "www.datos.gov.co",
                 retries: int = 4, timeout: int = 300) -> list[dict]:
    """Query a Socrata (datos.gov.co) dataset with SoQL parameters."""
    url = f"https://{domain}/resource/{dataset}.json"
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            return r.json()
        except Exception as err:
            last_err = err
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Socrata query failed for {dataset}: {last_err}")
