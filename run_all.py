"""Rebuild the whole portfolio:  python run_all.py  [--skip 01,04]

Runs each project's run.py in order (stopping at the first failure), then build_site.py.
Project 04 reuses its cached website checks; run `python 04-b2b-lead-list/run.py --refresh` to re-check them.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name[:2].isdigit() and (p / "run.py").exists())


def main() -> None:
    skip = set(sys.argv[sys.argv.index("--skip") + 1].split(",")) if "--skip" in sys.argv else set()
    for p in PROJECTS:
        if p.name[:2] in skip:
            print(f"== {p.name}: skipped")
            continue
        t0 = time.time()
        print(f"== {p.name}", flush=True)
        res = subprocess.run([sys.executable, "run.py"], cwd=p)
        if res.returncode != 0:
            raise SystemExit(f"{p.name} failed (exit code {res.returncode})")
        print(f"== {p.name}: done in {time.time() - t0:.0f} s", flush=True)
    subprocess.run([sys.executable, "build_site.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
