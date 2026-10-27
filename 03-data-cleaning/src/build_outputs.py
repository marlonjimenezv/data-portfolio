"""Deliverables: clean Excel workbook and the 2-page before/after quality report (PDF)."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import xlsxwriter  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,  # noqa: E402
                                TableStyle)

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
import brand  # noqa: E402

OUT = PROJECT / "output"
XLSX = OUT / "suppliers_clean.xlsx"
PDF = OUT / "quality_report.pdf"
CHART = OUT / "quality_before_after.png"

DICTIONARY = [
    ("supplier_code", "SECOP II supplier code (unique key in the source)", "SECOP II"),
    ("name", "Organisation name, standardised (upper case, one spelling per legal form)", "SECOP II, cleaned"),
    ("name_in_registry", "Legal name in the chamber-of-commerce registry", "RUES"),
    ("nit", "Tax ID (NIT) without check digit, 9 digits", "SECOP II, cleaned"),
    ("nit_formatted", "NIT with dots and the DIAN check digit (900.123.456-7)", "Calculated"),
    ("nit_status", "Result of the NIT validation", "Calculated"),
    ("company_type", "Company type as registered in SECOP II", "SECOP II"),
    ("legal_form", "Legal form from RUES (or from the name suffix when RUES has no record)", "RUES / name"),
    ("sme", "SME flag reported in SECOP II", "SECOP II"),
    ("size", "Company size reported in SECOP II (blank when 'not defined')", "SECOP II"),
    ("municipality", "Official municipality name (DANE)", "DIVIPOLA"),
    ("dane_code", "5-digit DANE municipality code", "DIVIPOLA"),
    ("address", "Address with standard Colombian abbreviations (CL, KR, AV, DG, TV, #)", "SECOP II, cleaned"),
    ("phone", "Phone in +57 format; mobiles partly hidden for privacy", "SECOP II, cleaned"),
    ("phone_type", "mobile / landline", "Calculated"),
    ("email", "E-mail in lower case; personal-looking mailboxes masked for privacy", "SECOP II, cleaned"),
    ("email_type", "own domain / free webmail", "Calculated"),
    ("website", "Website with https://", "SECOP II, cleaned"),
    ("website_note", "Website validation result", "Calculated"),
    ("secop_registration_date", "Date the supplier registered in SECOP II", "SECOP II"),
    ("registry_status", "Status in the chamber-of-commerce registry", "RUES"),
    ("registry_chamber", "Chamber of commerce that holds the registration", "RUES"),
    ("registration_date", "Date of registration in the chamber of commerce", "RUES"),
    ("last_renewal_year", "Last year the registration was renewed (due every year by 31 March)", "RUES"),
    ("ciiu_code", "Main economic activity (CIIU rev. 4)", "RUES"),
    ("issues_count", "Number of problems found for this record", "Calculated"),
    ("issues", "List of problems found (details in the Issues sheet)", "Calculated"),
]


def summary_numbers(res: dict) -> dict:
    steps = res["steps"].set_index("rule")
    excluded = int(steps.loc["Exclude personal ID numbers", "affected"])
    person_detail = steps.loc["Privacy: names that look like a person's name", "detail"]
    excluded_names = int(person_detail.split("; ")[1].split(" ")[0])
    issues = res["issues"]
    return {
        "records_in": len(res["raw"]), "records_out": len(res["clean"]),
        "duplicates": int(steps.loc["Remove duplicate NITs", "affected"]),
        "excluded_personal": excluded + excluded_names,
        "records_with_issues": int((res["clean"]["issues_count"] > 0).sum()),
        "issues_total": len(issues),
        "not_renewed": int(issues["issue"].str.startswith("registration not renewed").sum()),
        "liquidation": int((issues["issue"] == "company is in liquidation (RUES name)").sum()),
        "cancelled": int((res["clean"]["registry_status"] == "Cancelled").sum()),
        "form_corrected": int(steps.loc["Check legal form vs company type", "affected"]),
        "emails_masked": int(steps.loc["Privacy: mask personal-looking e-mails", "affected"]),
    }


def build_excel(res: dict, s: dict) -> Path:
    OUT.mkdir(exist_ok=True)
    wb = xlsxwriter.Workbook(str(XLSX))
    wb.set_properties({"title": "Supplier master data (cleaned) - sample project, public data",
                       "author": "Marlon Jiménez Valencia"})
    base = {"font_name": "Calibri", "font_size": 10, "valign": "top"}
    f_title = wb.add_format({**base, "font_size": 18, "bold": True, "font_color": "#0D366B"})
    f_h2 = wb.add_format({**base, "font_size": 12, "bold": True, "font_color": "#0D366B"})
    f_txt = wb.add_format({**base, "text_wrap": True})
    f_big = wb.add_format({**base, "font_size": 16, "bold": True, "font_color": "#0D366B", "num_format": "#,##0"})
    f_lbl = wb.add_format({**base, "font_color": "#52514E"})
    f_date = wb.add_format({**base, "num_format": "yyyy-mm-dd"})
    f_pct = wb.add_format({**base, "num_format": '0.0"%"'})
    f_head = wb.add_format({**base, "bold": True, "font_color": "#FFFFFF", "bg_color": "#0D366B"})

    sm = wb.add_worksheet("Summary")
    sm.hide_gridlines(2)
    sm.set_column(0, 0, 2); sm.set_column(1, 1, 44); sm.set_column(2, 2, 16); sm.set_column(3, 3, 60)
    sm.write(1, 1, "Supplier master data: cleaned and validated", f_title)
    sm.write(2, 1, "SECOP II registered suppliers in Boyacá (Colombia), cross-checked with the business registry "
                   "(RUES). Sample project built with public data.", f_lbl)
    rows = [("Records in the raw file", s["records_in"]), ("Records in the clean file", s["records_out"]),
            ("Duplicate records removed (same NIT)", s["duplicates"]),
            ("Records excluded for privacy (personal IDs or names)", s["excluded_personal"]),
            ("Records with at least one problem flagged", s["records_with_issues"]),
            ("Legal form corrected from the registry", s["form_corrected"]),
            ("Active registrations not renewed for 2026", s["not_renewed"]),
            ("Companies in liquidation", s["liquidation"]), ("Registrations cancelled", s["cancelled"])]
    for i, (k, v) in enumerate(rows):
        sm.write(4 + i, 1, k, f_lbl)
        sm.write_number(4 + i, 2, v, f_big)
    r = 5 + len(rows)
    sm.write(r, 1, "Sheets", f_h2)
    for i, (k, v) in enumerate([
            ("Clean data", "One row per organisation, standardised and validated (filter on issues_count > 0 to review)."),
            ("Issues", "One row per problem: field, issue and the action taken."),
            ("Cleaning log", "Every rule in the order applied, with the rows or cells it affected."),
            ("Quality before-after", "Share of records with a usable value, before and after cleaning."),
            ("Data dictionary", "What each column means and where it comes from.")]):
        sm.write(r + 1 + i, 1, k, f_lbl); sm.write(r + 1 + i, 3, v, f_txt)
    r += 8
    sm.write(r, 1, "Privacy", f_h2)
    sm.merge_range(r + 1, 1, r + 3, 3, "Only organisations are published. Records whose ID is a personal ID number, or "
                   "whose name looks like a person's name with no registry record, were excluded. E-mails that may "
                   "belong to a person are masked (j*****@gmail.com) and mobile numbers show only the operator prefix "
                   "and the last 2 digits. Legal representatives' names, IDs and contacts were never downloaded.", f_txt)
    sm.write(r + 5, 1, "Sources and licence", f_h2)
    sm.merge_range(r + 6, 1, r + 8, 3, "SECOP II - Proveedores Registrados (Colombia Compra Eficiente) and RUES - Personas "
                   "Naturales, Jurídicas y ESAL (Confecámaras), both on datos.gov.co under CC BY-SA 4.0; DIVIPOLA "
                   "municipality codes (DANE, CC BY-SA 4.0). This file is shared under the same licence. Data extracted "
                   f"on {res['as_of']}.", f_txt)

    f_wrap = wb.add_format({**base, "text_wrap": True})

    def table_sheet(name: str, df: pd.DataFrame, widths: dict, tname: str, wrap: tuple = ()):
        ws = wb.add_worksheet(name)
        df = df.copy()
        ws.add_table(0, 0, len(df), len(df.columns) - 1, {
            "name": tname, "style": "Table Style Medium 2",
            "columns": [{"header": c, "header_format": f_head} for c in df.columns]})
        for c_idx, col in enumerate(df.columns):
            for r_idx, v in enumerate(df[col], start=1):
                if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
                    continue
                if hasattr(v, "year") and not isinstance(v, str):
                    ws.write_datetime(r_idx, c_idx, pd.Timestamp(v).to_pydatetime(), f_date)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    ws.write_number(r_idx, c_idx, v, f_pct if col.endswith("_pct") else None)
                else:
                    ws.write_string(r_idx, c_idx, str(v), f_wrap if col in wrap else None)
            ws.set_column(c_idx, c_idx, widths.get(col, 14))
        ws.freeze_panes(1, 0)
        return ws

    clean = res["clean"].copy()
    clean["last_renewal_year"] = clean["last_renewal_year"].astype("float")
    ws = table_sheet("Clean data", clean, {"name": 42, "name_in_registry": 42, "company_type": 30, "address": 34,
                                           "email": 30, "website": 32, "issues": 60, "registry_status": 22,
                                           "nit_status": 22, "phone": 18}, "tbl_Suppliers")
    n = len(clean)
    ic = clean.columns.get_loc("issues_count")
    ws.conditional_format(1, ic, n, ic, {"type": "cell", "criteria": ">", "value": 0,
                                        "format": wb.add_format({"bg_color": "#FDE7DD", "font_color": "#8A2C0D"})})
    rc = clean.columns.get_loc("registry_status")
    ws.conditional_format(1, rc, n, rc, {"type": "text", "criteria": "containing", "value": "Cancelled",
                                        "format": wb.add_format({"font_color": "#B42318", "bold": True})})
    ws.conditional_format(1, rc, n, rc, {"type": "text", "criteria": "containing", "value": "Not found",
                                        "format": wb.add_format({"font_color": "#898781"})})
    table_sheet("Issues", res["issues"], {"name": 42, "issue": 60, "action": 34, "value_shown": 40, "field": 18},
                "tbl_Issues")
    table_sheet("Cleaning log", res["steps"], {"rule": 40, "detail": 64, "unit": 16}, "tbl_Log",
                wrap=("rule", "detail"))
    q = res["quality"].copy()
    wq = table_sheet("Quality before-after", q, {"field": 36, "usable_before_pct": 18, "usable_after_pct": 18},
                     "tbl_Quality")
    chart = wb.add_chart({"type": "bar"})
    for col, color, nm in ((1, "#9EC5F4", "Before cleaning"), (2, "#2A78D6", "After cleaning")):
        chart.add_series({"name": nm, "categories": ["Quality before-after", 1, 0, len(q), 0],
                          "values": ["Quality before-after", 1, col, len(q), col], "fill": {"color": color},
                          "gap": 60})
    chart.set_title({"name": "Share of records with a usable value (%)", "name_font": {"size": 12, "color": "#0D366B"}})
    chart.set_y_axis({"reverse": True, "num_font": {"size": 9}})
    chart.set_x_axis({"min": 0, "max": 100, "num_font": {"size": 9}, "major_gridlines": {"visible": True,
                      "line": {"color": "#E1E0D9"}}})
    chart.set_legend({"position": "bottom"})
    chart.set_size({"width": 720, "height": 380})
    wq.insert_chart(1, 4, chart)
    table_sheet("Data dictionary", pd.DataFrame(DICTIONARY, columns=["column", "description", "source"]),
                {"column": 24, "description": 80, "source": 18}, "tbl_Dictionary")
    wb.close()
    return XLSX


def chart_png(q: pd.DataFrame, path: Path, big: bool = False) -> Path:
    brand.apply_mpl_style()
    fs = 1.6 if big else 1.0
    fig, ax = plt.subplots(figsize=(14.2, 6.2) if big else (7.4, 4.3), dpi=100 if big else 200)
    y = range(len(q))
    h = 0.36
    ax.barh([i - h / 2 for i in y], q["usable_before_pct"], height=h, color=brand.BLUE_RAMP[3], label="Before cleaning")
    ax.barh([i + h / 2 for i in y], q["usable_after_pct"], height=h, color=brand.BLUE, label="After cleaning")
    for i, (b, a) in enumerate(zip(q["usable_before_pct"], q["usable_after_pct"])):
        ax.text(a + 1, i + h / 2, f"{a:.0f}%", va="center", fontsize=8.5 * fs, color=brand.INK)
        ax.text(b + 1, i - h / 2, f"{b:.0f}%", va="center", fontsize=8.5 * fs, color=brand.INK_2)
    ax.set_yticks(list(y), q["field"], fontsize=9 * fs)
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], fontsize=8 * fs)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.07), ncols=2, fontsize=9 * fs, frameon=False)
    ax.set_title("Records with a usable value, before vs after cleaning", fontsize=11.5 * fs, loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def build_pdf(res: dict, s: dict) -> Path:
    brand.register_fonts_reportlab()
    chart_png(res["quality"], CHART)
    st = {
        "title": ParagraphStyle("t", fontName="Inter-Bold", fontSize=17, leading=21, textColor=brand.BRAND),
        "sub": ParagraphStyle("s", fontName="Inter", fontSize=8.6, leading=12, textColor=brand.INK_2),
        "h2": ParagraphStyle("h", fontName="Inter-SemiBold", fontSize=11, leading=14, textColor=brand.BRAND,
                             spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("b", fontName="Inter", fontSize=8.6, leading=12, textColor=brand.INK, alignment=TA_LEFT),
        "small": ParagraphStyle("sm", fontName="Inter", fontSize=7.4, leading=10, textColor=brand.INK_2),
        "kpi": ParagraphStyle("k", fontName="Inter-Bold", fontSize=15, leading=18, textColor=brand.BRAND),
        "kpil": ParagraphStyle("kl", fontName="Inter", fontSize=7.4, leading=9.5, textColor=brand.INK_2),
        "cell": ParagraphStyle("c", fontName="Inter", fontSize=8, leading=10, textColor=brand.INK),
        "cellb": ParagraphStyle("cb", fontName="Inter-SemiBold", fontSize=8, leading=10, textColor=colors.white),
    }

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Inter", 7)
        canvas.setFillColor(colors.HexColor(brand.MUTED))
        canvas.drawString(18 * mm, 10 * mm, "Sample project built with public data · Marlon Jiménez Valencia")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page} of 2")
        canvas.setFillColor(colors.HexColor(brand.BRAND))
        canvas.rect(0, A4[1] - 5 * mm, A4[0], 5 * mm, stroke=0, fill=1)
        canvas.restoreState()

    def grid(data, widths, header=True, zebra=True):
        t = Table(data, colWidths=widths, hAlign="LEFT")
        style = [("FONT", (0, 0), (-1, -1), "Inter", 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(brand.GRID)),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(brand.BRAND))]
        t.setStyle(TableStyle(style))
        return t

    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title="Supplier data quality report",
                            author="Marlon Jiménez Valencia")
    P = Paragraph
    el = [P("Supplier master data: quality report", st["title"]), Spacer(1, 3),
          P("Before and after cleaning · SECOP II registered suppliers in Boyacá, Colombia, cross-checked with the "
            f"business registry (RUES) · data extracted on {res['as_of']}", st["sub"]), Spacer(1, 10)]
    kpis = [(f"{s['records_in']:,}", "records in the raw file"), (f"{s['records_out']:,}", "organisations in the clean file"),
            (f"{s['duplicates']:,}", "duplicate records removed"), (f"{s['excluded_personal']:,}", "excluded for privacy"),
            (f"{s['records_with_issues']:,}", "records with a problem flagged")]
    kt = Table([[P(v, st["kpi"]) for v, _ in kpis], [P(l, st["kpil"]) for _, l in kpis]],
               colWidths=[34.8 * mm] * 5, hAlign="LEFT")
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(brand.WASH)),
                            ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white),
                            ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    el += [kt, Spacer(1, 6), P("Before vs after: share of records with a usable value", st["h2"])]
    q = res["quality"]
    notes = {
        "NIT (valid, unique)": "Check digit split off and verified; duplicates removed",
        "Name (standard spelling)": "Upper case, one spelling per legal form",
        "Phone (10-digit, dialable)": "Old 7-digit landlines converted to 608 + number",
        "E-mail (valid, lower case)": "Lower case, typos fixed, invalid blanked",
        "Website (valid URL)": "https:// added, typos fixed (most suppliers have none)",
        "Address (standard format)": "CALLE/CRA/No. -> CL/KR/#; rural addresses accepted",
        "Municipality (official DANE code)": "Matched to the DANE list (DIVIPOLA)",
        "Registry status (RUES)": "Status, registration date and renewal added",
    }
    data = [[P("Field", st["cellb"]), P("Before", st["cellb"]), P("After", st["cellb"]), P("What changed", st["cellb"])]]
    for _, row in q.iterrows():
        data.append([P(row["field"], st["cell"]), P(f"{row['usable_before_pct']:.1f}%", st["cell"]),
                     P(f"<b>{row['usable_after_pct']:.1f}%</b>", st["cell"]), P(notes[row["field"]], st["cell"])])
    el += [grid(data, [52 * mm, 18 * mm, 18 * mm, 86 * mm]), Spacer(1, 3),
           P(f"Before = the {s['records_in']:,} raw records, used as they come. After = the {s['records_out']:,} "
             "records in the clean file.", st["small"])]
    el += [P("Main rules applied (full log in the Excel file)", st["h2"])]
    steps = res["steps"]
    pick = steps[steps["rule"].isin([
        "Trim spaces and blank out placeholders", "Split NIT and check digit", "Exclude personal ID numbers",
        "Privacy: names that look like a person's name", "Remove duplicate NITs", "Check legal form vs company type",
        "Standardise phone numbers", "Privacy: mask personal-looking e-mails", "Standardise addresses",
        "Cross-check with the business registry (RUES)"])]
    data = [[P("Rule", st["cellb"]), P("Affected", st["cellb"]), P("Detail", st["cellb"])]]
    for _, row in pick.iterrows():
        data.append([P(row["rule"], st["cell"]), P(f"{int(row['affected']):,} {row['unit']}", st["cell"]),
                     P(row["detail"], st["cell"])])
    el += [grid(data, [50 * mm, 26 * mm, 98 * mm]), PageBreak()]

    el += [P("Quality before and after cleaning", st["h2"]), Image(str(CHART), width=170 * mm, height=170 * mm * 4.3 / 7.4),
           P("Registry cross-check (RUES)", st["h2"])]
    stt = res["status"]
    data = [[P("Registry status", st["cellb"]), P("Organisations", st["cellb"])]]
    data += [[P(r_["registry_status"], st["cell"]), P(f"{r_['suppliers']:,}", st["cell"])] for _, r_ in stt.iterrows()]
    issues = res["issues"]["issue"].str.replace(r"\(last renewal \d+\)", "", regex=True).str.strip()
    top = issues.value_counts().head(8)
    data2 = [[P("Most frequent problems flagged", st["cellb"]), P("Records", st["cellb"])]]
    data2 += [[P(k, st["cell"]), P(f"{v:,}", st["cell"])] for k, v in top.items()]
    tt = Table([[grid(data, [40 * mm, 26 * mm]), grid(data2, [86 * mm, 18 * mm])]], colWidths=[70 * mm, 104 * mm],
               hAlign="LEFT")
    tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el += [tt, Spacer(1, 4),
           P(f"<b>For a procurement team:</b> {s['not_renewed']:,} suppliers with an active registration did not renew it "
             f"for 2026, {s['liquidation']} companies are in liquidation and {s['cancelled']} registrations are cancelled. "
             "These are the first records to check before signing a contract.", st["body"]),
           P("Method and privacy", st["h2"]),
           P("Python (pandas) pipeline with unit-tested rules: NIT check digit (DIAN modulo 11), Colombian phone plan "
             "(2021), e-mail and URL syntax, standard address abbreviations, DANE municipality codes, dates read from "
             "three different formats, and a registry cross-check by NIT. Values that cannot be fixed with certainty "
             "are flagged, never guessed. Only organisations are published: personal IDs and person-like names are "
             f"excluded, {s['emails_masked']:,} personal-looking e-mails are masked and mobile numbers are partly hidden.",
             st["body"]),
           P("Limitations", st["h2"]),
           P("The person-name check is a heuristic and may also remove a few organisations named after people. "
             "Organisations not found in RUES (community action boards, consortia, public bodies) are often registered "
             "elsewhere, so 'not found' is not an error by itself. Phones and websites were not called or visited.",
             st["body"]),
           P("Sources", st["h2"]),
           P("SECOP II - Proveedores Registrados (Colombia Compra Eficiente) and RUES (Confecámaras), datos.gov.co, "
             "CC BY-SA 4.0. DIVIPOLA (DANE), datos.gov.co, CC BY-SA 4.0.", st["small"])]
    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    return PDF
