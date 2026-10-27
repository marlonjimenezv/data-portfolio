"""One-page PDF for decision makers: model quality, drivers and 5 recommendations."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
import brand  # noqa: E402

OUT = PROJECT / "output"
PDF = OUT / "churn_one_pager.pdf"
LABEL = {"complained": "Complained", "seconds_of_use": "Seconds of use", "calls": "Number of calls",
         "sms": "SMS sent", "distinct_numbers_called": "Distinct numbers called", "inactive": "Non-active status",
         "months_subscribed": "Months subscribed", "charge_level": "Charge level", "call_failures": "Call failures",
         "age_group": "Age group", "contract_plan": "Contract plan", "customer_value": "Customer value"}


def importance_chart(r: dict, path: Path) -> Path:
    brand.apply_mpl_style()
    imp = dict(list(r["importance"].items())[:6])
    fig, ax = plt.subplots(figsize=(4.4, 2.9), dpi=220)
    names = [LABEL[k] for k in imp][::-1]
    ax.barh(names, list(imp.values())[::-1], color=brand.BLUE, height=0.55)
    ax.set_title("Top drivers (permutation importance)", fontsize=10)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("Drop in ROC-AUC when shuffled", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def build(r: dict) -> Path:
    brand.register_fonts_reportlab()
    chart = importance_chart(r, OUT / "figures" / "one_pager_importance.png")
    S = {
        "t": ParagraphStyle("t", fontName="Inter-Bold", fontSize=17, leading=21, textColor=brand.BRAND),
        "s": ParagraphStyle("s", fontName="Inter", fontSize=8.5, leading=11.5, textColor=brand.INK_2),
        "h": ParagraphStyle("h", fontName="Inter-SemiBold", fontSize=10.5, leading=13, textColor=brand.BRAND,
                            spaceBefore=6, spaceAfter=3),
        "b": ParagraphStyle("b", fontName="Inter", fontSize=8.6, leading=11.6, textColor=brand.INK),
        "k": ParagraphStyle("k", fontName="Inter-Bold", fontSize=16, leading=19, textColor=brand.BRAND),
        "kl": ParagraphStyle("kl", fontName="Inter", fontSize=7.2, leading=9, textColor=brand.INK_2),
        "f": ParagraphStyle("f", fontName="Inter", fontSize=6.8, leading=9, textColor=brand.MUTED),
    }
    flagged = r["tp"] + r["fp"]
    n_test = r["n_test"]
    kpi = [(f"{r['test_auc']:.3f}", "ROC-AUC on unseen customers (1.0 = perfect)"),
           (f"{r['recall']:.0%}", f"of churners caught ({r['tp']} of {r['tp'] + r['fn']})"),
           (f"{r['precision']:.0%}", f"of flagged customers really churn ({r['tp']} of {flagged})"),
           (f"{flagged / n_test:.0%}", "of customers flagged for a retention call")]
    kt = Table([[Paragraph(v, S["k"]) for v, _ in kpi], [Paragraph(l, S["kl"]) for _, l in kpi]],
               colWidths=[43.5 * mm] * 4)
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(brand.WASH)),
                            ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white), ("TOPPADDING", (0, 0), (-1, 0), 6),
                            ("BOTTOMPADDING", (0, -1), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    d = r["direction"]
    model_text = Paragraph(
        f"<b>What the model does.</b> Gives each customer a probability of leaving in the next quarter, from 9 "
        f"months of usage data; it can re-score the customer base every month. A gradient-boosting model beat a random forest and a logistic "
        f"regression in 5-fold cross-validation (PR-AUC {r['cv'][r['best']]['PR-AUC (mean)']:.2f}). It was tested "
        f"once on {n_test} customers it had never seen. Customers above the cut-off ({r['threshold']:.2f}) go on the "
        f"retention list; the cut-off was chosen on training data to catch about 80% of churners.<br/><br/>"
        f"<b>Who leaves.</b> The lowest-usage quarter of customers churns at {d['seconds_of_use'][0]:.0%}, the "
        f"highest at {d['seconds_of_use'][1]:.0%}. Customers who complained churn at "
        f"{r['churn_if_complained']:.0%} (vs {r['churn_if_no_complaint']:.0%}).", S["b"])
    top = Table([[Image(str(chart), width=80 * mm, height=80 * mm * 2.9 / 4.4), model_text]],
                colWidths=[84 * mm, 90 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    recs = [
        ("Treat every complaint as a churn alarm.",
         f"{r['churn_if_complained']:.0%} of customers who complained left, against {r['churn_if_no_complaint']:.0%} "
         "of the rest, and complaints are a top-3 driver. Route each complaint to a retention agent and confirm it "
         "was solved."),
        ("Watch for falling usage every month.",
         "Number of calls and seconds of use are the two strongest drivers. A drop in usage is the earliest signal "
         "the company sees: trigger contact when a customer's monthly usage falls well below their own average."),
        ("Re-activate non-active customers.",
         f"{r['churn_if_inactive']:.0%} of customers with non-active status churned, against "
         f"{r['churn_if_active']:.0%} of active ones. A usage-based incentive is a natural test."),
        ("Spend the retention budget on the model's list.",
         f"Flagging {flagged / n_test:.0%} of customers catches {r['recall']:.0%} of the churners, and "
         f"{r['precision']:.0%} of the flagged customers are real churners, so few offers are wasted. Call the "
         "highest scores first."),
        ("Test contract plans with a control group.",
         f"Contract customers churned at {r['churn_contract']:.0%} vs {r['churn_payg']:.0%} on pay-as-you-go, but "
         "the model gives the plan little weight once usage is known. Offer migration to a random half of at-risk "
         "pay-as-you-go customers and compare."),
    ]
    rec_rows = [[Paragraph(f"<b>{i}</b>", S["k"]), Paragraph(f"<b>{t}</b> {b}", S["b"])]
                for i, (t, b) in enumerate(recs, start=1)]
    rt = Table(rec_rows, colWidths=[10 * mm, 164 * mm])
    rt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -2), 0.4,
                                                                   colors.HexColor(brand.GRID)),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))

    def frame(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(brand.BRAND))
        canvas.rect(0, A4[1] - 5 * mm, A4[0], 5 * mm, stroke=0, fill=1)
        canvas.restoreState()

    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm,
                            bottomMargin=12 * mm, title="Churn model: one-page summary", author="Marlon Jiménez Valencia")
    doc.build([
        Paragraph("Customer churn: who is about to leave, and what to do", S["t"]), Spacer(1, 3),
        Paragraph("One-page summary of a predictive model · telecom operator, 2,850 unique customers · "
                  "Sample project built with public data", S["s"]), Spacer(1, 8), kt, Spacer(1, 8),
        top, Paragraph("Five recommendations (based on the model; test each before rolling it out)", S["h"]), rt,
        Spacer(1, 6),
        Paragraph("<b>Data:</b> Iranian Churn Dataset, UCI Machine Learning Repository, DOI 10.24432/C5JW3Z, CC BY 4.0. "
                  "Features cover months 1-9, churn is measured at month 12. 300 duplicate rows removed before the "
                  "train/test split to avoid leakage. <b>Limits:</b> one operator and period; no revenue or offer-cost "
                  "data, so the cut-off is set by a recall target; associations, not causes. Full notebook: "
                  "analysis/churn_model.ipynb.", S["f"]),
    ], onFirstPage=frame)
    return PDF
