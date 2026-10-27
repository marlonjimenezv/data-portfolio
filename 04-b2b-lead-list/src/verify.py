"""Polite website verification: robots.txt first, then one request to the home page.

- Identifies itself with a descriptive User-Agent.
- Reads robots.txt and skips the site if our agent may not fetch "/".
- At most 2 requests per site (robots.txt + home page), a pause between them, one retry for network errors.
- Never crawls links, never fills forms, reads at most 300 KB of the home page (only to get the <title>).
Results are cached in data/clean/website_checks.json so a re-run does not hit the sites again.
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import requests

PROJECT = Path(__file__).resolve().parent.parent
CACHE = PROJECT / "data" / "clean" / "website_checks.json"
UA = "data-portfolio-site-check/1.0 (+https://github.com/marlonjimenezv/data-portfolio; sample project)"
PAUSE = 1.5      # seconds between the two requests to the same site
WORKERS = 6      # different sites checked in parallel (never the same site twice at once)
TIMEOUT = (10, 20)


def normalise_url(raw: str) -> tuple[str, str]:
    """Registry values look like 'www.site.edu.co', 'https://site.edu.co/', 'no informa'.

    Returns (url, note). Obvious typos are fixed and the fix is reported in the note.
    """
    w = (raw or "").strip().lower().replace(",", ".").replace(" ", "")
    if not w or not re.search(r"[a-z0-9-]+\.[a-z]{2,}", w):
        return "", ""
    w = re.sub(r"^(https?:?)?/*", "", w).rstrip("/")
    host, _, path = w.partition("/")
    fixed = host
    if "@" in fixed:                                  # an e-mail typed as the website
        domain = fixed.split("@")[-1]
        if not re.search(r"\.edu(\.co)?$", domain):  # e.g. an internet provider's mail domain
            return "", "registry lists an e-mail address, not a website"
        fixed = "www." + domain
        return "https://" + fixed, "registry lists an e-mail address; its institutional domain was used"
    fixed = re.sub(r"^w{3,}\.", "www.", fixed)         # wwww.site.edu.co
    fixed = re.sub(r"^www(?=[a-z0-9])(?!\.)", "www.", fixed)  # wwwsite.edu.co
    fixed = fixed.strip(".")
    note = f"fixed typo in registry ({host} -> {fixed})" if fixed != host else ""
    return "https://" + fixed + ("/" + path if path else ""), note


def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", unescape(m.group(1))).strip()[:150] if m else ""


def check(url: str, quick: bool = False) -> dict:
    """Check one site. quick=True (second pass): one attempt on the listed address only."""
    host = urlparse(url).netloc
    out = {"url_checked": url, "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})

    # 1) robots.txt (https first, then http)
    rp = robotparser.RobotFileParser()
    robots_found = False
    for scheme in ("https", "http"):
        try:
            r = session.get(f"{scheme}://{host}/robots.txt", timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and "text" in r.headers.get("Content-Type", "text"):
                rp.parse(r.text.splitlines())
                robots_found = True
            break
        except requests.RequestException:
            continue
    out["robots_txt"] = "found" if robots_found else "not found"
    if robots_found and not rp.can_fetch(UA, f"https://{host}/"):
        out.update(status="Not checked (robots.txt disallows)", http_status="")
        return out
    time.sleep(PAUSE)

    # 2) home page over https (also with/without "www."), one retry on network errors
    last_err = ""
    alt = host[4:] if host.startswith("www.") else "www." + host
    for attempt in range(1 if quick else 2):
        for h in ((host,) if quick else (host, alt)):
            try:
                t0 = time.time()
                with session.get(f"https://{h}/", timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
                    body = r.raw.read(300_000, decode_content=True).decode(r.encoding or "utf-8", errors="ignore")
                    out.update(http_status=r.status_code, final_url=r.url, response_ms=int(1000 * (time.time() - t0)),
                               https=r.url.startswith("https://"), title=_title(body),
                               content_type=r.headers.get("Content-Type", "").split(";")[0])
                    return out
            except requests.exceptions.SSLError:
                last_err = "TLS certificate rejected"
                continue
            except requests.exceptions.ConnectionError:
                last_err = "no connection from the checking server"
                continue
            except requests.exceptions.Timeout:
                last_err = "timeout"
                continue
            except requests.RequestException as err:
                last_err = type(err).__name__
                continue
        if not quick:
            time.sleep(10)
    out.update(http_status="", error=last_err)
    return out


def classify(listed_url: str, res: dict) -> str:
    if not res:
        return "No website listed"
    if res.get("status"):
        return res["status"]
    code = res.get("http_status")
    if not code:
        return f"Not verified ({res.get('error', 'error')})"
    if 200 <= int(code) < 300:
        listed = urlparse(listed_url).netloc.removeprefix("www.")
        final = urlparse(res["final_url"]).netloc.removeprefix("www.")
        if listed and final and listed != final and not final.endswith("." + listed):
            return "Online (redirects to another domain)"
        return "Online"
    if code in (401, 403, 429):
        return f"Online but blocks automated checks (HTTP {code})"
    return f"Site error (HTTP {code})"


def verify_all(urls: list[str], refresh: bool = False) -> dict:
    cache = {} if refresh or not CACHE.exists() else json.loads(CACHE.read_text())
    todo = sorted({u for u in urls if u and u not in cache})
    if todo:
        print(f"  checking {len(todo)} websites ({WORKERS} sites at a time, {PAUSE}s pause per site)...")
        with ThreadPoolExecutor(WORKERS) as ex:
            for url, res in zip(todo, ex.map(check, todo)):
                cache[url] = res
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))  # save progress
        # second pass, one site at a time, for sites that did not answer (network hiccups are common)
        retry = [u for u in todo if not cache[u].get("http_status") and not cache[u].get("status")]
        if retry:
            print(f"  second pass for {len(retry)} sites that did not answer...")
            time.sleep(20)
            for u in retry:
                res = check(u, quick=True)
                if res.get("http_status"):
                    res["note"] = "answered on the second pass"
                    cache[u] = res
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return cache
