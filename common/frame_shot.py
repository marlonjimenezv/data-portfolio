"""Put any screenshot on a 1600x1200 (4:3) canvas with the portfolio style.

Usage:  python common/frame_shot.py <input.png> <output.png> "Short label"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from upwork import make_shot  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    out = make_shot(Path(sys.argv[2]), Path(sys.argv[1]), sys.argv[3])
    print(f"Saved {out} (1600x1200)")
