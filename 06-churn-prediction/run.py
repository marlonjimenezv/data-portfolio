"""One command to rebuild project 06:  python run.py

1. Download the Iranian Churn dataset (UCI, CC BY 4.0)          -> data/raw/
2. Execute the modelling notebook (analysis/churn_model.py)      -> analysis/churn_model.ipynb, output/figures/
3. Export the notebook to HTML (with and without code) + one-page PDF summary -> output/
4. Upwork package                                               -> upwork/
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT.parent / "common"))
sys.path.insert(0, str(PROJECT / "src"))
import notebook_tools as nbt  # noqa: E402
from fetch_utils import fetch  # noqa: E402

import make_upwork  # noqa: E402
import one_pager  # noqa: E402

RAW = PROJECT / "data" / "raw"
OUT = PROJECT / "output"
URL = "https://archive.ics.uci.edu/static/public/563/iranian+churn+dataset.zip"


def download() -> None:
    if (RAW / "Customer Churn.csv").exists():
        return
    z = fetch(URL, RAW / "iranian_churn.zip", min_bytes=20_000)
    with zipfile.ZipFile(z) as zf:
        zf.extract("Customer Churn.csv", RAW)


def main() -> None:
    print("[1/4] Data")
    download()
    print("[2/4] Execute the notebook")
    OUT.mkdir(exist_ok=True)
    nb = nbt.execute(nbt.py_to_notebook(PROJECT / "analysis" / "churn_model.py"), PROJECT / "analysis")
    nbformat.write(nb, PROJECT / "analysis" / "churn_model.ipynb")
    print("[3/4] HTML report + one-pager")
    nbt.export_html(nb, OUT / "churn_model.html", "Churn Prediction Notebook", True,
                    "../../common/fonts/Inter-Regular.ttf")
    nbt.export_html(nb, OUT / "churn_report.html", "Churn Prediction Report", False,
                    "../../common/fonts/Inter-Regular.ttf")
    r = json.loads((OUT / "results.json").read_text())
    one_pager.build(r)
    print(f"  best model: {r['best']}; test ROC-AUC {r['test_auc']:.3f}; recall {r['recall']:.2f}; "
          f"precision {r['precision']:.2f}")
    print("[4/4] Upwork package")
    make_upwork.main(r)
    print("Done.")


if __name__ == "__main__":
    main()
