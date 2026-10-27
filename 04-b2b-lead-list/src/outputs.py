"""Write the lead list (CSV for Google Sheets + Excel) and the method summary."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import xlsxwriter

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "output"
CSV = OUT / "colombia_higher_ed_leads.csv"
XLSX = OUT / "colombia_higher_ed_leads.xlsx"
METHOD = OUT / "METHOD.md"

DICTIONARY = [
    ("snies_code", "Institution code in SNIES, the national higher-education information system"),
    ("institution", "Official name (as in the MEN registry)"),
    ("nit", "Tax ID of the institution (9 digits, no check digit)"),
    ("sector", "Public or Private"),
    ("institution_type", "Academic type: university, university institution, technological, technical"),
    ("legal_nature", "Foundation, corporation, or national / departmental / municipal public body"),
    ("high_quality_accreditation", "Yes if the institution holds high-quality institutional accreditation (registry value)"),
    ("branch_campuses", "Number of branch campuses (seccionales) with the same tax ID"),
    ("students_enrolled_*", "Students enrolled in the first semester of the latest year published by MEN (size indicator)"),
    ("department / city / address", "Main campus location (registry)"),
    ("phone", "Main switchboard in +57 format (2021 numbering plan: 60 + area code + 7 digits)"),
    ("website", "Home page that answered during verification (after redirects)"),
    ("website_status", "Result of the verification (see the Summary sheet)"),
    ("http_status", "HTTP status code returned by the home page"),
    ("page_title", "Title of the home page, to confirm it belongs to the institution"),
    ("website_listed", "Website as listed in the registry (normalised), or from Wikidata when missing"),
    ("website_source", "MEN registry or Wikidata (with the name-match score)"),
    ("website_note", "Typo fixed in the registry value, if any"),
    ("verified_at", "Date and time (UTC) of the verification request"),
    ("source", "Dataset the row comes from"),
]


def write(leads: pd.DataFrame, log: pd.DataFrame, enr_year: str, run_date: str) -> None:
    OUT.mkdir(exist_ok=True)
    leads.to_csv(CSV, index=False, encoding="utf-8-sig")

    wb = xlsxwriter.Workbook(str(XLSX))
    wb.set_properties({"title": "Colombian higher-education institutions - verified lead list (sample, public data)",
                       "author": "Marlon Jiménez Valencia"})
    base = {"font_name": "Calibri", "font_size": 10, "valign": "top"}
    head = wb.add_format({**base, "bold": True, "font_color": "#FFFFFF", "bg_color": "#0D366B", "text_wrap": True})
    title = wb.add_format({**base, "font_size": 18, "bold": True, "font_color": "#0D366B"})
    h2 = wb.add_format({**base, "font_size": 12, "bold": True, "font_color": "#0D366B"})
    txt = wb.add_format({**base, "text_wrap": True})
    num = wb.add_format({**base, "num_format": "#,##0"})
    muted = wb.add_format({**base, "font_color": "#52514E"})

    # Summary
    sm = wb.add_worksheet("Summary")
    sm.hide_gridlines(2)
    sm.set_column(0, 0, 2); sm.set_column(1, 1, 52); sm.set_column(2, 2, 12); sm.set_column(3, 3, 3)
    sm.set_column(4, 4, 30); sm.set_column(5, 5, 12)
    sm.write(1, 1, "Colombian higher-education institutions: verified lead list", title)
    sm.write(2, 1, f"{len(leads)} institutions from the official MEN registry · websites checked on {run_date} · "
                   "Sample project built with public data", muted)
    status = leads["website_status"].value_counts()
    sm.write(4, 1, "Website verification", h2)
    sm.write(5, 1, "Result", head); sm.write(5, 2, "Institutions", head)
    for i, (k, v) in enumerate(status.items()):
        sm.write(6 + i, 1, k, txt); sm.write_number(6 + i, 2, int(v), num)
    end = 6 + len(status)

    r = 4
    for label, col in (("By sector", "sector"), ("By type", "institution_type")):
        sm.write(r, 4, label, h2)
        sm.write(r + 1, 4, "Group", head); sm.write(r + 1, 5, "Institutions", head)
        vc = leads[col].value_counts()
        for i, (k, v) in enumerate(vc.items()):
            sm.write(r + 2 + i, 4, k, txt); sm.write_number(r + 2 + i, 5, int(v), num)
        r += 4 + len(vc)
    sm.write(r, 4, "Top departments", h2)
    sm.write(r + 1, 4, "Department", head); sm.write(r + 1, 5, "Institutions", head)
    for i, (k, v) in enumerate(leads["department"].value_counts().head(8).items()):
        sm.write(r + 2 + i, 4, k, txt); sm.write_number(r + 2 + i, 5, int(v), num)
    r += 2 + 8
    chart = wb.add_chart({"type": "bar"})
    chart.add_series({"name": "Institutions", "categories": ["Summary", 6, 1, end - 1, 1],
                      "values": ["Summary", 6, 2, end - 1, 2], "fill": {"color": "#2A78D6"}, "gap": 60,
                      "data_labels": {"value": True, "font": {"size": 9}}})
    chart.set_title({"name": "Website verification result", "name_font": {"size": 11, "color": "#0D366B"}})
    chart.set_y_axis({"reverse": True, "num_font": {"size": 9}})
    chart.set_x_axis({"visible": False, "major_gridlines": {"visible": False}})
    chart.set_legend({"none": True})
    chart.set_size({"width": 760, "height": 320})
    sm.insert_chart(max(end, r) + 1, 1, chart)

    # Leads
    ws = wb.add_worksheet("Leads")
    cols = list(leads.columns)
    ws.add_table(0, 0, len(leads), len(cols) - 1, {"name": "tbl_Leads", "style": "Table Style Medium 2",
                                                   "columns": [{"header": c, "header_format": head} for c in cols]})
    for c_idx, col in enumerate(cols):
        for r_idx, v in enumerate(leads[col], start=1):
            if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)) or v == "":
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                ws.write_number(r_idx, c_idx, float(v), num)
            elif col == "website" and str(v).startswith("http"):
                ws.write_url(r_idx, c_idx, str(v), string=str(v))
            else:
                ws.write_string(r_idx, c_idx, str(v))
    widths = {"institution": 46, "institution_type": 30, "legal_nature": 18, "address": 34, "website": 34,
              "website_status": 47, "page_title": 40, "website_listed": 34, "website_source": 24, "website_note": 30,
              "source": 44, "department": 18, "city": 16, "phone": 18, "verified_at": 18}
    for c_idx, col in enumerate(cols):
        ws.set_column(c_idx, c_idx, widths.get(col, 12))
    ws.freeze_panes(1, 2)
    sc = cols.index("website_status")
    for text, color in (("Online", "#E3F4E3"), ("Not verified", "#FFF4CC"), ("Site error", "#FDE7DD"),
                        ("No website", "#EEEEEE")):
        ws.conditional_format(1, sc, len(leads), sc, {"type": "text", "criteria": "begins with", "value": text,
                                                      "format": wb.add_format({"bg_color": color})})

    # Method + dictionary
    mt = wb.add_worksheet("Method")
    mt.set_column(0, 0, 2); mt.set_column(1, 1, 120)
    for i, line in enumerate(method_lines(log, enr_year, run_date)):
        mt.write(1 + i, 1, line.lstrip("#- ").replace("**", ""), h2 if line.startswith("#") else txt)
    dd = wb.add_worksheet("Data dictionary")
    dd.set_column(0, 0, 28); dd.set_column(1, 1, 100)
    dd.write(0, 0, "column", head); dd.write(0, 1, "meaning", head)
    for i, (k, v) in enumerate(DICTIONARY, start=1):
        dd.write(i, 0, k, txt); dd.write(i, 1, v, txt)
    wb.close()
    METHOD.write_text("\n".join(method_lines(log, enr_year, run_date)) + "\n", encoding="utf-8")


def method_lines(log: pd.DataFrame, enr_year: str, run_date: str) -> list[str]:
    counts = dict(zip(log["step"], log["count"]))
    lines = [
        "# Method: verified lead list of Colombian higher-education institutions",
        "",
        "Sample project built with public data. Organisation-level data only: no names, e-mails or phones of people.",
        "",
        "## Sources",
        "- MEN - Instituciones de Educación Superior (datos.gov.co, dataset n5yy-8nav, CC BY-SA 4.0): official registry "
        "with name, tax ID, type, sector, accreditation, address, phone and website. Record date in the source: "
        "8 Jul 2022.",
        f"- MEN - Matrícula estadística de educación superior (datos.gov.co, dataset 5wck-szir, CC BY-SA 4.0): enrolled "
        f"students per institution, semester {enr_year} (the latest published), aggregated with SoQL.",
        "- Wikidata (CC0): official website (property P856), used only when the registry had no usable website and the "
        "name matched (similarity >= 0.90). One SPARQL query.",
        "",
        "## Steps",
    ]
    for step, n in counts.items():
        lines.append(f"- {step}: **{n}**")
    lines += [
        "- Phones normalised to +57 with the 2021 numbering plan (60 + area code of the department + 7 digits).",
        "- Each website checked once, see below. The verified home page (after redirects) goes in `website`.",
        "",
        "## How websites were checked (respectful by design)",
        "- A descriptive User-Agent that names the project and links to the repository.",
        "- robots.txt is read first; if it does not allow our agent to fetch the home page, the site is not requested.",
        "- Normally 2 requests per site (robots.txt, then the home page after a 1.5-second pause). Only when the home "
        "page does not answer: the same address with or without 'www.', one retry 10 seconds later, and a second pass "
        "at the end, one site at a time. 6 different sites are checked in parallel; never the same site twice at once.",
        "- Only the home page is requested; no links are followed and no forms are submitted. Only the first 300 KB "
        "are read, to get the page title.",
        f"- Checked on {run_date}. Results are cached, so re-running the script does not contact the sites again "
        "(use `--refresh` to re-check).",
        "",
        "## Reading the status column",
        "- **Online**: the home page answered with HTTP 2xx. **Online (redirects to another domain)**: the institution "
        "moved its site; `website` has the new address.",
        "- **Online but blocks automated checks**: the server answered (HTTP 403/429) but blocks scripts; open it in a "
        "browser.",
        "- **Site error**: the server answered with an error code (HTTP 4xx/5xx).",
        "- **Not verified**: no answer reached our checking server (connection refused or closed, timeout, or TLS "
        "certificate rejected). Many Colombian institutional sites block traffic from foreign cloud servers, so this "
        "does not prove the site is down: re-check from a local connection before using these rows.",
        "- **No website listed**: neither the registry nor Wikidata had a usable website.",
        "",
        "## Limitations",
        "- The registry records are dated 2022; institutions may have changed phone or address since then.",
        "- Enrolment figures are from the latest semester MEN has published as open data, not the current one.",
        "- Verification shows that a site answered at a point in time, not that the contact data inside it is current.",
    ]
    return lines
