"""Upwork package for project 06."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import brand  # noqa: E402
import config  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402

UP = PROJECT / "upwork"
OUT = PROJECT / "output"
FIG = OUT / "figures"
FOLDER = "06-churn-prediction"


def shoot_section(tmp: Path, name: str, heading: str, height: int = 570) -> Path:
    out = tmp / f"{name}.png"
    js = tmp / f"{name}.js"
    js.write_text(f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const p = await b.newPage({{ viewport: {{ width: 760, height: {height} }}, deviceScaleFactor: 2 }});
  await p.goto('file://{OUT / "churn_report.html"}', {{ waitUntil: 'networkidle' }});
  await p.evaluate((t) => {{
    const h = [...document.querySelectorAll('h1,h2,h3')].find((e) => e.textContent.includes(t));
    window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 16);
  }}, {heading!r});
  await p.waitForTimeout(300);
  await p.screenshot({{ path: '{out}' }});
  await b.close();
}})();""")
    subprocess.run(["node", str(js)], check=True, cwd=str(COMMON))
    return out


def cover_chart(r: dict, path: Path) -> None:
    brand.apply_mpl_style()
    d = r["direction"]
    groups = [("Lowest 25% usage", d["seconds_of_use"][0]), ("Highest 25% usage", d["seconds_of_use"][1]),
              ("Complained", r["churn_if_complained"]), ("No complaint", r["churn_if_no_complaint"]),
              ("Non-active", r["churn_if_inactive"]), ("Active", r["churn_if_active"])]
    fig, ax = plt.subplots(figsize=(14.2, 6.0), dpi=100)
    labels = [g for g, _ in groups]
    vals = [100 * v for _, v in groups]
    cols = [brand.ORANGE if i % 2 == 0 else brand.BLUE_RAMP[3] for i in range(len(groups))]
    bars = ax.barh(labels, vals, color=cols, height=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}%", va="center", fontsize=18)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.tick_params(axis="y", labelsize=17)
    ax.tick_params(axis="x", labelsize=13)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title(f"Churn rate by group · model ROC-AUC {r['test_auc']:.3f} on unseen customers", fontsize=21,
                 loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(r: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p6up_"))
    shutil.copyfile(OUT / "churn_one_pager.pdf", UP / "one-pager.pdf")
    cover_chart(r, tmp / "cover.png")
    make_cover(UP / "cover.png", 6, "Predictive analytics", "Customer Churn Prediction",
               "Gradient boosting vs logistic regression, cross-validated, with a one-page action plan",
               tmp / "cover.png", "Python · scikit-learn")
    make_shot(UP / "shot-1.png", shoot_section(tmp, "s1", "4. Model comparison"),
              "Three models compared with 5-fold cross-validation")
    make_shot(UP / "shot-2.png", FIG / "roc_confusion.png", "Test set: ROC curve and confusion matrix")
    make_shot(UP / "shot-3.png", shoot_section(tmp, "s3", "7. What drives"), "What drives churn")
    subprocess.run(["pdftoppm", "-r", "170", "-png", "-singlefile", str(OUT / "churn_one_pager.pdf"),
                    str(tmp / "onepager")], check=True)
    from PIL import Image
    op = Image.open(tmp / "onepager.png")
    op.crop((0, 0, op.width, int(op.height * 0.66))).save(tmp / "onepager_top.png")
    make_shot(UP / "shot-4.png", tmp / "onepager_top.png", "One-pager for managers: 5 recommendations")
    make_shot(UP / "shot-5.png", shoot_section(tmp, "s5", "3. Preparation"), "Preparation: how leakage is avoided")

    title = "Customer Churn Prediction Model (Python)"
    desc = (
        "Subscription businesses need to know who will leave before they do. On a public telecom dataset I built "
        "and compared logistic regression, random forest and gradient boosting with 5-fold cross-validation, "
        "removed duplicates before the split to avoid leakage and set the alert threshold on training data. "
        f"Result on unseen customers: ROC-AUC {r['test_auc']:.3f}; the alert list catches {r['recall']:.0%} of "
        f"churners with {r['precision']:.0%} precision, plus a one-page action plan. "
        "Sample project built with public data."
    )
    skills = ["Machine Learning", "Predictive Analytics", "Python", "scikit-learn", "Data Science"]
    cv = r["cv"]
    captions = [
        f"Cross-validated comparison on the training set: gradient boosting (PR-AUC {cv['Gradient boosting']['PR-AUC (mean)']:.2f}) "
        f"beats random forest ({cv['Random forest']['PR-AUC (mean)']:.2f}) and logistic regression "
        f"({cv['Logistic regression']['PR-AUC (mean)']:.2f}).",
        f"Evaluated once on {r['n_test']} unseen customers: ROC-AUC {r['test_auc']:.3f}. At the chosen threshold, "
        f"{r['tp']} of {r['tp'] + r['fn']} churners are caught and only {r['fp']} loyal customers are flagged.",
        "Permutation importance shows usage (calls, seconds) and complaints drive the predictions; churn rates by "
        "group give the direction of each effect.",
        "A one-page summary for managers: model quality in plain words, the main drivers and five actions to test, "
        "each tied to a number from the data.",
        f"Leakage control: {r['duplicates']} duplicate rows removed before the train/test split, scaling inside the "
        "pipeline, threshold chosen on out-of-fold training predictions.",
    ]
    links = [f"Report (web page): {config.PAGES_URL}/churn-report/",
             f"Notebook with code: {config.file_url(FOLDER + '/analysis/churn_model.ipynb')}",
             f"One-pager (PDF): {config.file_url(FOLDER + '/output/churn_one_pager.pdf')}",
             f"GitHub project folder: {config.folder_url(FOLDER)}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
