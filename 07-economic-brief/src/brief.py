"""The 4-page research brief (PDF). Every number comes from data/clean/results.json or the clean tables."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
import brand  # noqa: E402

CLEAN = PROJECT / "data" / "clean"
PDF = PROJECT / "output" / "colombia_minimum_wage_brief.pdf"
TITLE = "Colombia's minimum wage, 2004-2025"
W = A4[0] - 36 * mm      # text width


def styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="Inter", textColor=brand.INK)
    return {
        "title": ParagraphStyle("title", fontName="Inter-Bold", fontSize=21, leading=25, textColor=brand.BRAND),
        "sub": ParagraphStyle("sub", fontName="Inter", fontSize=9, leading=12, textColor=brand.INK_2),
        "h1": ParagraphStyle("h1", fontName="Inter-Bold", fontSize=12.5, leading=16, textColor=brand.BRAND,
                             spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Inter-SemiBold", fontSize=9.5, leading=12, textColor=brand.INK,
                             spaceAfter=2),
        "body": ParagraphStyle("body", fontSize=9.2, leading=13.2, spaceAfter=5, **base),
        "bullet": ParagraphStyle("bullet", fontSize=9.2, leading=13, leftIndent=11, bulletIndent=0, spaceAfter=3.5,
                                 **base),
        "small": ParagraphStyle("small", fontName="Inter", fontSize=7.6, leading=10, textColor=brand.INK_2),
        "src": ParagraphStyle("src", fontName="Inter", fontSize=7.9, leading=10.6, textColor=brand.INK,
                              leftIndent=10, bulletIndent=0, spaceAfter=2.5),
        "kv": ParagraphStyle("kv", fontName="Inter-Bold", fontSize=17, leading=20, textColor=brand.BRAND),
        "kl": ParagraphStyle("kl", fontName="Inter", fontSize=7.6, leading=9.6, textColor=brand.INK_2),
        "box": ParagraphStyle("box", fontSize=9.2, leading=13, **base),
    }


def img(path: Path, width: float) -> Image:
    w, h = PILImage.open(path).size
    return Image(str(path), width=width, height=width * h / w)


def cop(x: float) -> str:
    return f"COP {x:,.0f}"


def build() -> Path:
    brand.register_fonts_reportlab()
    S = styles()
    r = json.loads((CLEAN / "results.json").read_text())
    src = json.loads((CLEAN / "sources_accessed.json").read_text())
    t = pd.read_csv(CLEAN / "colombia_minimum_wage.csv", index_col="year")
    fig = PROJECT / "output" / "figures"
    s, e = r["start"], r["end"]
    rec = {int(k): v for k, v in r["recent"].items()}
    match = r["years_matching_prev_inflation"]
    match_txt = "; ".join(f"in {y} it equalled it ({v[0]:.2f}% against {v[1]:.2f}%)" for y, v in match.items())
    accessed = max(v["accessed"] for v in src.values())
    acc_txt = date.fromisoformat(accessed).strftime("%d %B %Y").lstrip("0")
    cross = int(t.index[(t["real_wage_index"] > t["productivity_index"]) & (t.index > 2010)][0])
    gap_med = r["latam_col"] - r["latam_median"]
    position = "the median" if abs(gap_med) < 1 else ("above the median" if gap_med > 0 else "below the median")

    def bullet(text: str) -> Paragraph:
        return Paragraph(text, S["bullet"], bulletText="•")

    story = [
        Spacer(1, 2),
        Paragraph(TITLE + ": above inflation every year, and now ahead of productivity", S["title"]),
        Spacer(1, 4),
        Paragraph(f"Economic research brief · {brand.PORTFOLIO_TAG} · Data to December {e}, sources accessed "
                  f"{acc_txt} · {brand.AUTHOR}", S["sub"]),
        Spacer(1, 10),
    ]
    kpi = [(f"+{r['real_growth_pct']:.0f}%", f"real minimum wage, {s}-{e}"),
           (f"+{r['productivity_growth_pct']:.0f}%", f"GDP per worker, {s}-{e}"),
           (f"{r['oecd_col']:.1f}%", f"of the median full-time wage in {r['oecd_year']}: highest of "
                                    f"{r['oecd_n']} countries"),
           (f"${r['latam_col']:,.0f}", f"PPP dollars a month in {r['latam_year']}: {r['latam_col_rank']}th of "
                                       f"{r['latam_n']} in Latin America")]
    kt = Table([[Paragraph(v, S["kv"]) for v, _ in kpi], [Paragraph(lbl, S["kl"]) for _, lbl in kpi]],
               colWidths=[W / 4] * 4)
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(brand.WASH)),
                            ("LINEAFTER", (0, 0), (-2, -1), 2.5, colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story += [kt, Spacer(1, 6), Paragraph("Executive summary", S["h1"])]
    story += [
        bullet(f"Between {s} and {e} the monthly minimum wage rose from {cop(r['wage_start'])} to "
               f"{cop(r['wage_end'])} (+{r['nominal_growth_pct']:.0f}%). Consumer prices rose "
               f"{r['prices_growth_pct']:.0f}%, so its purchasing power grew <b>{r['real_growth_pct']:.0f}%</b>."),
        bullet(f"The yearly increase never fell below the previous year's inflation: it was higher in "
               f"{r['years_above_prev_inflation']} of the {r['compare_years']} years from {r['compare_first']} to {e}, "
               f"and {match_txt}. The real gain averaged {r['avg_gap_to_2021_pp']:.1f} percentage points a year from "
               f"{r['compare_first']} to 2021 and <b>{r['avg_gap_2022_on_pp']:.1f} points in 2022-{e}</b>."),
        bullet(f"For most of the period the real minimum wage grew more slowly than output per worker. That changed "
               f"after 2022: from 2022 to {e} the real minimum wage rose <b>{r['real_growth_2022_2025_pct']:.1f}%</b> "
               f"while GDP per worker changed {r['productivity_growth_2022_2025_pct']:+.1f}%. Since {cross} the wage "
               f"index is above the productivity index."),
        bullet(f"In {r['oecd_year']} Colombia's minimum wage was <b>{r['oecd_col']:.1f}% of the median full-time "
               f"wage</b>, the highest of the {r['oecd_n']} countries with OECD data (median {r['oecd_median']:.0f}%; "
               f"next: {r['oecd_second'][0]}, {r['oecd_second'][1]:.0f}%). In {r['col_ratio_first'][0]} it was "
               f"{r['col_ratio_first'][1]:.1f}%."),
        bullet(f"In dollars of equal purchasing power it is not high for the region: ${r['latam_col']:,.0f} a month "
               f"in {r['latam_year']}, {r['latam_col_rank']}th of {r['latam_n']} Latin American countries "
               f"({position.replace('the median', 'the regional median')})."),
    ]
    box = Table([[Paragraph("<b>Key message.</b> Colombia's minimum wage is average for Latin America in purchasing "
                            "power, but very high compared with what a typical Colombian worker earns. Since 2022, "
                            "increases well above inflation have not been matched by productivity gains.", S["box"])]],
                colWidths=[W])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor(brand.BRAND_2)),
                             ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                             ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [Spacer(1, 4), box, Paragraph("Context", S["h1"])]
    story += [
        Paragraph("Colombia sets one national minimum wage each December for the following year, by agreement of "
                  "government, employers and unions in a tripartite commission or, when they do not agree, by "
                  "government decree. Ley 278 de 1996 asks the decision to consider the inflation target, "
                  "productivity, GDP growth and the consumer price index; in practice, as the data below show, the "
                  "previous year's inflation works as a floor.", S["body"]),
        Paragraph("The decision matters beyond the lowest-paid formal workers: the minimum pension cannot be lower "
                  "than the minimum wage, and many fees, fines and thresholds are set as multiples of it. "
                  f"For 2026 the government decreed {cop(r['wage_2026'])}, a <b>{r['increase_2026_pct']:.1f}%</b> "
                  "increase (Decreto 1469 de 2025), the largest in the series; at the time of writing the decree is "
                  "under review by the Consejo de Estado. 2026 is not in the charts because its inflation is not "
                  "complete yet.", S["body"]),
        PageBreak(),
    ]

    # Page 2
    story += [
        Paragraph("1. Increases have matched or beaten inflation every year", S["h1"]),
        Paragraph(f"Minimum wage increase and the previous year's inflation (December to December), "
                  f"{r['compare_first']}-{e}", S["h2"]),
        img(fig / "chart1_increase_vs_inflation.png", W),
        Paragraph("Sources: ILOSTAT and Decreto 1572 de 2024 (minimum wage); DANE (consumer price index).", S["small"]),
        Spacer(1, 5),
        Paragraph(f"Each bar is above or level with its dot: the minimum wage has kept its purchasing power against "
                  f"the inflation known when it was set. From 2022 the margin became much wider: "
                  f"+{rec[2022]['increase']:.1f}% in 2022 (previous inflation {rec[2022]['prev_inflation']:.1f}%), "
                  f"+{rec[2023]['increase']:.1f}% in 2023 ({rec[2023]['prev_inflation']:.1f}%, the peak), "
                  f"+{rec[2024]['increase']:.1f}% in 2024 ({rec[2024]['prev_inflation']:.1f}%) and "
                  f"+{rec[2025]['increase']:.1f}% in 2025 ({rec[2025]['prev_inflation']:.1f}%). In 2022 the gain "
                  f"was eaten by that year's {rec[2022]['inflation']:.1f}% inflation; from 2023, with inflation "
                  f"falling ({rec[2025]['inflation']:.1f}% during 2025), it became a real gain.", S["body"]),
        Spacer(1, 4),
        Paragraph("2. Since 2023 the real minimum wage has outgrown productivity", S["h1"]),
        Paragraph(f"Real minimum wage (deflated by the annual average CPI) and GDP per person employed, "
                  f"index {s} = 100", S["h2"]),
        img(fig / "chart2_real_wage_vs_productivity.png", W),
        Paragraph("Sources: ILOSTAT, Decreto 1572 de 2024, DANE; World Bank WDI, GDP per person employed "
                  "(constant 2021 PPP $).", S["small"]),
        Spacer(1, 5),
        Paragraph(f"Over the whole period both lines end close together: +{r['real_growth_pct']:.0f}% for the real "
                  f"minimum wage and +{r['productivity_growth_pct']:.0f}% for GDP per worker. The path differs: until "
                  f"2022 the wage lagged behind (index {t.loc[2022, 'real_wage_index']:.0f} against "
                  f"{t.loc[2022, 'productivity_index']:.0f}); in the last three years it gained "
                  f"{r['real_growth_2022_2025_pct']:.1f}% while output per worker did not grow. In {e} a minimum-wage "
                  f"worker could buy {cop(t.loc[e, 'real_wage_cop_2025_prices'] - t.loc[s, 'real_wage_cop_2025_prices'])}"
                  f" more a month (at {e} prices) than in {s}.", S["body"]),
        PageBreak(),
    ]

    # Page 3
    left = [Paragraph(f"Minimum wage as % of the median full-time wage, {r['oecd_year']}", S["h2"]),
            img(fig / "chart3_minimum_to_median.png", W / 2 - 4 * mm),
            Paragraph(f"Source: OECD, Minimum relative to average wages of full-time workers. {r['oecd_n']} countries "
                      f"with data for {r['oecd_year']}.", S["small"])]
    right = [Paragraph(f"Monthly minimum wage in 2021 PPP dollars, {r['latam_year']}", S["h2"]),
             img(fig / "chart4_latam_ppp.png", W / 2 - 4 * mm),
             Paragraph(f"Source: ILOSTAT, statutory nominal gross monthly minimum wage. "
                       f"{', '.join(r['latam_breaks'])} excluded (series break, see Limitations).", S["small"])]
    two = Table([[left, right]], colWidths=[W / 2, W / 2])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (0, -1), 8)]))
    story += [
        Paragraph("3. High against local wages, average in purchasing power", S["h1"]),
        Paragraph("Two ways to compare a minimum wage across countries give opposite pictures of Colombia.",
                  S["body"]),
        two, Spacer(1, 6),
        Paragraph(f"<b>Relative to typical wages</b> (left), Colombia's minimum is {r['oecd_col']:.1f}% of the "
                  f"median wage of full-time workers, far above the median of {r['oecd_median']:.0f}% among the "
                  f"{r['oecd_n']} countries and above Costa Rica and Mexico, the other Latin American members. The "
                  f"ratio rose from {r['col_ratio_first'][1]:.1f}% in {r['col_ratio_first'][0]}. A ratio near 100% "
                  f"means the legal floor and the wage of the typical full-time worker are almost the same.",
                  S["body"]),
        Paragraph(f"<b>In purchasing power</b> (right), the same wage buys about ${r['latam_col']:,.0f} a month in "
                  f"2021 international dollars, {position} of {r['latam_n']} Latin American countries "
                  f"(${r['latam_median']:,.0f}), below {r['latam_top'][0]} (${r['latam_top'][1]:,.0f}) and above "
                  f"{r['latam_bottom'][0]} (${r['latam_bottom'][1]:,.0f}). Read together, the two charts suggest that "
                  "the ratio is high mainly because typical full-time wages are low, rather than because the floor "
                  "is high by regional standards.", S["body"]),
        PageBreak(),
    ]

    # Page 4
    story += [
        Paragraph("What this means for decision makers", S["h1"]),
        bullet("<b>Employers and budget planners.</b> The data show a stable rule: the increase is at least last "
               f"year's inflation plus a premium (about {r['avg_gap_to_2021_pp']:.1f} points a year up to 2021, "
               f"{r['avg_gap_2022_on_pp']:.1f} points since 2022). Wage budgets for minimum-wage staff should plan "
               "for that premium, and for 2026 the decreed increase is far above it."),
        bullet("<b>Policy analysts.</b> With the minimum close to the median wage, each increase affects a large "
               "share of formal wages, not only the lowest. The minimum-to-median ratio, formal employment and "
               "labour productivity are the indicators to follow together."),
        bullet(f"<b>Researchers.</b> The {r['increase_2026_pct']:.0f}% increase of 2026 will push the ratio further "
               "up unless median wages grow as fast. The 2026 household survey and inflation data will show by how "
               "much."),
        Paragraph("Limitations", S["h1"]),
        bullet("Productivity is GDP per person employed (World Bank). It includes informal work and is not the "
               "productivity measure used in the wage negotiation."),
        bullet("The real wage uses the annual average CPI. Other deflators (December CPI, low-income CPI) move the "
               "results by one or two points but do not change the pattern."),
        bullet("The OECD ratio compares with the median wage of full-time employees from each country's own data "
               "sources; countries without a statutory minimum wage are not in the chart."),
        bullet(f"In ILOSTAT, the {r['latam_year']} values for {' and '.join(r['latam_breaks'])} fall by more than 80% "
               "from the previous year together with a change of source, which signals a series break; they are "
               "excluded. Venezuela has no recent data."),
        bullet("This brief is descriptive. It does not estimate the effect of the minimum wage on employment or "
               "informality."),
        Paragraph("Method", S["h1"]),
        Paragraph(f"A Python script downloads every series from the official APIs and files, checks that each year "
                  f"from {s - 1} to {e} is complete, and computes: the December-to-December inflation; each year's "
                  f"increase against the previous year's inflation; the real minimum wage at {e} prices (annual "
                  f"average CPI); and indexes with {s} = 100. ILOSTAT ends in 2024, so the {e} value comes from the "
                  "decree. All tables and charts are rebuilt with one command (<font name='Courier'>python run.py"
                  "</font>).", S["body"]),
        Paragraph(f"Sources (accessed {acc_txt})", S["h1"]),
    ]
    sources = [
        ("DANE, Índice de Precios al Consumidor (IPC), index series 2003-2026, Dec 2018 = 100. "
         "Free reuse citing \"Fuente: DANE\".", src["dane_ipc"]["url"]),
        ("ILO, ILOSTAT, Statutory nominal gross monthly minimum wage (DF_EAR_INEE_CUR_NB), local currency and "
         "2021 PPP $. CC BY 4.0.", "https://ilostat.ilo.org/data/"),
        ("Presidencia de la República, Decreto 1572 de 2024 (minimum wage 2025: COP 1,423,500) and Decreto 1469 "
         "de 2025 (minimum wage 2026: COP 1,750,905).", "https://dapre.presidencia.gov.co/normativa/decretos"),
        ("World Bank, World Development Indicators, GDP per person employed, constant 2021 PPP $ "
         "(SL.GDP.PCAP.EM.KD). CC BY 4.0.", "https://data.worldbank.org/indicator/SL.GDP.PCAP.EM.KD"),
        ("OECD, Minimum relative to average wages of full-time workers (DSD_EARNINGS@MIN2AVE), median. "
         "CC BY 4.0.", "https://data-explorer.oecd.org/"),
    ]
    story += [Paragraph(f"{txt} <font color='{brand.BRAND_2}'>{url}</font>", S["src"], bulletText="•")
              for txt, url in sources]
    story += [Spacer(1, 6), Paragraph(f"{brand.PORTFOLIO_TAG}. Figures computed by the author from the sources "
                                      "above; any error is the author's.", S["small"])]

    def frame(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(brand.BRAND))
        canvas.rect(0, A4[1] - 5 * mm, A4[0], 5 * mm, stroke=0, fill=1)
        canvas.setFont("Inter", 7.5)
        canvas.setFillColor(colors.HexColor(brand.MUTED))
        canvas.drawString(18 * mm, 10 * mm, f"{TITLE} · {brand.PORTFOLIO_TAG}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm,
                            bottomMargin=17 * mm, title=TITLE + ": research brief", author=brand.AUTHOR,
                            subject=brand.PORTFOLIO_TAG)
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return PDF


if __name__ == "__main__":
    print(build())
