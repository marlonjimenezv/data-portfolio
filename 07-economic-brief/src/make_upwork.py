"""Upwork package for project 07."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
COMMON = PROJECT.parent / "common"
sys.path.insert(0, str(COMMON))
import brand  # noqa: E402
import config  # noqa: E402
from upwork import make_cover, make_shot, report, write_texts  # noqa: E402

UP = PROJECT / "upwork"
OUT = PROJECT / "output"
CLEAN = PROJECT / "data" / "clean"
FOLDER = "07-economic-brief"


def cover_chart(path: Path) -> None:
    brand.apply_mpl_style()
    t = pd.read_csv(CLEAN / "colombia_minimum_wage.csv", index_col="year")
    fig, ax = plt.subplots(figsize=(14.2, 6.0), dpi=100)
    ax.plot(t.index, t["real_wage_index"], color=brand.BLUE, lw=3.5, label="Real minimum wage")
    ax.plot(t.index, t["productivity_index"], color=brand.ORANGE, lw=3.5, label="GDP per worker")
    last = t.index[-1]
    for col, dy in (("real_wage_index", 8), ("productivity_index", -8)):
        ax.annotate(f"{t.loc[last, col]:.0f}", (last, t.loc[last, col]), xytext=(10, dy), textcoords="offset points",
                    fontsize=19, va="center")
    ax.set_xlim(t.index[0] - 0.3, last + 1.6)
    ax.set_xticks(range(int(t.index[0]), int(last) + 1, 3))
    ax.tick_params(labelsize=15)
    ax.legend(loc="upper left", fontsize=17)
    ax.set_title(f"Real minimum wage vs productivity, index {t.index[0]} = 100", fontsize=21, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def page_crop(pages: list[Path], page: int, top: float, bottom: float, out: Path) -> Path:
    im = Image.open(pages[page - 1])
    im.crop((0, int(im.height * top), im.width, int(im.height * bottom))).save(out)
    return out


def main(r: dict) -> None:
    UP.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p7up_"))
    pdf = OUT / "colombia_minimum_wage_brief.pdf"
    shutil.copyfile(pdf, UP / "research-brief.pdf")
    cover_chart(tmp / "cover.png")
    make_cover(UP / "cover.png", 7, "Economic research", "Economic Research Brief",
               f"Colombia's minimum wage {r['start']}-{r['end']}: inflation, productivity, peers",
               tmp / "cover.png", "Python · Official APIs · PDF report")
    subprocess.run(["pdftoppm", "-r", "170", "-png", str(pdf), str(tmp / "p")], check=True)
    pages = sorted(tmp.glob("p-*.png"))
    make_shot(UP / "shot-1.png", page_crop(pages, 1, 0.0, 0.592, tmp / "s1.png"),
              "Page 1: key figures and executive summary")
    make_shot(UP / "shot-2.png", page_crop(pages, 2, 0.02, 0.47, tmp / "s2.png"),
              "Increases vs inflation, 2005-2025")
    make_shot(UP / "shot-3.png", page_crop(pages, 2, 0.465, 0.9, tmp / "s3.png"),
              "Real minimum wage vs productivity")
    make_shot(UP / "shot-4.png", page_crop(pages, 3, 0.075, 0.625, tmp / "s4.png"),
              "Comparison with other countries")
    make_shot(UP / "shot-5.png", page_crop(pages, 4, 0.02, 0.5, tmp / "s5.png"),
              "Implications and limitations")

    title = "Economic Research Brief: Colombia Minimum Wage"
    desc = (
        "Policy teams need numbers they can cite. I wrote a 4-page brief on Colombia's minimum wage "
        f"{r['start']}-{r['end']} from official data (DANE, ILO, World Bank, OECD), downloaded and processed with "
        "one Python script. Finding: increases never fell below the previous year's inflation, and since 2022 the "
        f"real wage rose {r['real_growth_2022_2025_pct']:.0f}% while productivity was flat; it is "
        f"{r['oecd_col']:.0f}% of the median wage, the highest of {r['oecd_n']} countries. "
        "Sample project built with public data."
    )
    skills = ["Economic Research", "Economics", "Policy Analysis", "Data Analysis", "Python"]
    rec = {int(k): v for k, v in r["recent"].items()}
    captions = [
        f"Executive summary with four key figures: real minimum wage +{r['real_growth_pct']:.0f}% and GDP per worker "
        f"+{r['productivity_growth_pct']:.0f}% since {r['start']}, {r['oecd_col']:.1f}% of the median wage, "
        f"${r['latam_col']:,.0f} PPP a month.",
        f"Every year the increase matched or beat the previous year's inflation; from 2022 the margin widened, with "
        f"+{rec[2023]['increase']:.0f}% in 2023 against {rec[2023]['prev_inflation']:.1f}% inflation.",
        f"Until 2022 the real minimum wage grew more slowly than GDP per worker; since then it rose "
        f"{r['real_growth_2022_2025_pct']:.1f}% while productivity changed {r['productivity_growth_2022_2025_pct']:+.1f}%.",
        f"Two comparisons, two pictures: the highest minimum-to-median ratio of {r['oecd_n']} countries (OECD), but "
        f"{r['latam_col_rank']}th of {r['latam_n']} in Latin America in purchasing-power dollars (ILO).",
        "Plain-language implications for employers, analysts and researchers, and honest limitations, including a "
        "series break detected in two countries' data. Sources are listed with access date and licence.",
    ]
    links = [f"Brief (PDF): {config.file_url(FOLDER + '/output/colombia_minimum_wage_brief.pdf')}",
             f"GitHub project folder: {config.folder_url(FOLDER)}"]
    write_texts(UP, title, desc, skills, captions, links)
    report(UP)
