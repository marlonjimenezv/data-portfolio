"""Upwork package for project 05."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import config  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402

UP = PROJECT / "upwork"
OUT = PROJECT / "output"
FIG = OUT / "figures"
FOLDER = "05-survey-analysis"


def shoot_section(tmp: Path, name: str, heading: str, height: int = 570) -> Path:
    """Screenshot the report starting at a given section heading."""
    out = tmp / f"{name}.png"
    js = tmp / f"{name}.js"
    js.write_text(f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const p = await b.newPage({{ viewport: {{ width: 760, height: {height} }}, deviceScaleFactor: 2 }});
  await p.goto('file://{OUT / "report.html"}', {{ waitUntil: 'networkidle' }});
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


def cover_chart(path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import brand
    brand.apply_mpl_style()
    t = pd.read_csv(OUT / "very_happy_by_group.csv")
    t = t[t["variable"].isin(["health", "finances"])]
    t["label"] = t["group"].replace({"More or less satisfied": "Finances: so-so", "Not satisfied at all":
                                     "Finances: not satisfied", "Satisfied": "Finances: satisfied"})
    t.loc[t["variable"] == "health", "label"] = "Health: " + t.loc[t["variable"] == "health", "group"].str.lower()
    fig, ax = plt.subplots(figsize=(14.2, 6.2), dpi=100)
    y = range(len(t))
    ax.hlines(y, 100 * t["lo"], 100 * t["hi"], color=brand.BLUE_RAMP[5], lw=9)
    ax.plot(100 * t["share"], y, "o", color=brand.BLUE, ms=17, mec=brand.SURFACE, mew=3)
    for i, (_, row) in enumerate(t.iterrows()):
        ax.text(100 * row["hi"] + 1.2, i, f"{100 * row['share']:.0f}%", va="center", fontsize=18)
    ax.set_yticks(list(y), t["label"], fontsize=17)
    ax.invert_yaxis()
    ax.set_xlim(0, 55)
    ax.tick_params(axis="x", labelsize=14)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title("% of US adults who are “very happy” (dot) with 95% CI (bar)", fontsize=21, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(r: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p5up_"))
    cover_chart(tmp / "cover_chart.png")
    make_cover(UP / "cover.png", 5, "Statistical analysis", "Survey Analysis Report",
               "What goes with happiness? GSS 2024: chi-square, confidence intervals, logistic regression",
               tmp / "cover_chart.png", "Python · statsmodels · Jupyter")
    make_shot(UP / "shot-1.png", shoot_section(tmp, "s1", "1. Data and method"),
              "Report opening: data, weights and method")
    make_shot(UP / "shot-2.png", shoot_section(tmp, "s2", "4. Cross-tabulations"),
              "Cross-tabs with chi-square tests and Cramér's V")
    make_shot(UP / "shot-3.png", FIG / "very_happy_by_group.png", "Shares with 95% confidence intervals")
    make_shot(UP / "shot-4.png", shoot_section(tmp, "s4", "6. Logistic regression"),
              "Logistic regression: odds ratios and effects")
    make_shot(UP / "shot-5.png", shoot_section(tmp, "s5", "Checking the model"),
              "Assumption checks and plain-language results")

    vh, ame = r["very_happy"], r["ame_pp"]
    title = "Survey Data Analysis: Chi-square & Regression"
    desc = (
        "Thesis students and researchers need survey results that are correct and easy to read. Using the "
        "public 2024 General Social Survey (3,986 US adults), I wrote a report on what goes with happiness: "
        "weighted estimates with design-based 95% CIs, cross-tabs with chi-square tests and a logistic regression "
        "with assumption checks (Python, statsmodels, Jupyter). Finding: people in fair health are "
        f"{abs(ame['Fair health (vs excellent)']):.0f} points less likely to be very happy. "
        "Sample project built with public data."
    )
    skills = ["Statistical Analysis", "Survey Data Analysis", "Regression Analysis", "Python", "Data Analysis"]
    captions = [
        "Every number uses the official survey weight, and the confidence intervals account for the stratified, "
        "clustered sample design (68 strata, 137 sampling units), as in Stata svy or R survey.",
        "Cross-tabulations with row percentages, chi-square tests of independence and Cramér's V, with the "
        "expected-count assumption checked for each table.",
        f"{100 * vh['p']:.0f}% of US adults say they are very happy (95% CI {100 * vh['lo']:.1f}% to "
        f"{100 * vh['hi']:.1f}%), from {100 * r['very_happy_poor_health']:.0f}% of people in poor health to "
        f"{100 * r['very_happy_excellent_health']:.0f}% of those in excellent health.",
        "Weighted logistic regression with cluster-robust errors: odds ratios, 95% CIs and average marginal effects "
        "in percentage points, so the results are easy to explain.",
        "Assumptions checked and reported: events per predictor, multicollinearity (VIF), influential cases, "
        "calibration and goodness of fit, followed by the results in plain language and the limitations.",
    ]
    links = [f"Report (web page): {config.PAGES_URL}/survey-report/",
             f"Report (PDF): {config.file_url(FOLDER + '/output/report.pdf')}",
             f"Notebook with code: {config.file_url(FOLDER + '/analysis/analysis.ipynb')}",
             f"GitHub project folder: {config.folder_url(FOLDER)}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
