"""Build the Excel KPI report (XlsxWriter).

Every number on the KPIs sheet is a live formula (SUMIFS, COUNTIFS, INDEX/MATCH,
MINIFS, LARGE) that points to Excel tables. Two yellow cells choose the report
period; all KPIs, rankings and charts update when they change.

The workbook is built twice: the first pass is recalculated in LibreOffice, and
the second pass stores those results as cached values, so the numbers are visible
even in Excel's Protected View or in file previews (before any recalculation).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_col_to_name

PROJECT = Path(__file__).resolve().parent.parent
CLEAN = PROJECT / "data" / "clean"

NAVY, BLUE, ORANGE, AQUA = "#0D366B", "#2A78D6", "#EB6834", "#1BAF7A"
INK, INK2, MUTED, GRID, WASH = "#0B0B0B", "#52514E", "#898781", "#E1E0D9", "#EEF4FC"
INPUT_FILL = "#FFF4CC"
GOOD_TXT, BAD_TXT = "#006300", "#B42318"
FONT = "Calibri"

DEFAULT_START = dt.date(2010, 12, 1)
DEFAULT_END = dt.date(2011, 11, 1)


class Writer:
    """Wraps write_formula so every formula gets its cached value (pass 2)."""

    def __init__(self, values: dict | None):
        self.values = values or {}
        self.positions: list[tuple[str, int, int]] = []

    def f(self, ws, row, col, formula, fmt=None):
        self.positions.append((ws.name, row, col))
        v = self.values.get((ws.name, row, col))
        if v is None:
            ws.write_formula(row, col, formula, fmt)
        else:
            ws.write_formula(row, col, formula, fmt, v)


def load_tables():
    parse = {"orders": ["InvoiceDate", "Month"], "product_month": ["Month"]}
    t = {}
    for name in ("orders", "product_month", "products", "customers", "cleaning_log"):
        t[name] = pd.read_csv(CLEAN / f"{name}.csv", parse_dates=parse.get(name, False),
                              dtype={"InvoiceNo": str, "CustomerID": str, "StockCode": str})
    return t


def build(out: Path, values: dict | None = None) -> list[tuple[str, int, int]]:
    """Write the workbook. Returns the (sheet, row, col) position of every formula."""
    t = load_tables()
    W = Writer(values)
    wb = xlsxwriter.Workbook(str(out), {"use_future_functions": True, "strings_to_numbers": False})
    wb.set_properties({"title": "E-commerce KPI Report (sample project, public data)",
                       "author": "Marlon Jiménez Valencia",
                       "comments": "Built with public data: Online Retail II, UCI ML Repository (CC BY 4.0)."})
    wb.set_calc_mode("auto")

    base = {"font_name": FONT, "font_size": 10, "font_color": INK, "valign": "vcenter"}

    def fmt(**kw):
        return wb.add_format({**base, **kw})

    F = {
        "title": fmt(font_size=20, bold=True, font_color=NAVY),
        "subtitle": fmt(font_size=10, font_color=INK2),
        "h2": fmt(font_size=12, bold=True, font_color=NAVY),
        "label": fmt(font_color=INK2),
        "note": fmt(font_size=9, font_color=MUTED, italic=True),
        "warn": fmt(font_size=10, bold=True, font_color=BAD_TXT),
        "input": fmt(bg_color=INPUT_FILL, bold=True, num_format="mmm yyyy", border=1, border_color="#E0B400",
                     align="center"),
        "month_out": fmt(num_format="mmm yyyy", bold=True, align="center", font_color=INK2),
        "int": fmt(num_format="#,##0"),
        "gbp": fmt(num_format="£#,##0"),
        "gbp2": fmt(num_format="£#,##0.00"),
        "pct": fmt(num_format="0.0%"),
        "pct_signed": fmt(num_format="+0.0%;-0.0%;0.0%"),
        "date": fmt(num_format="yyyy-mm-dd"),
        "month": fmt(num_format="mmm yyyy"),
        "text": fmt(),
        "th": fmt(bold=True, font_color="#FFFFFF", bg_color=NAVY, border=0, text_wrap=True),
        "th_r": fmt(bold=True, font_color="#FFFFFF", bg_color=NAVY, align="right", text_wrap=True),
        "tile_label": fmt(font_size=9, font_color=INK2, bg_color=WASH, indent=1),
        "tile_gbp": fmt(font_size=20, bold=True, font_color=NAVY, bg_color=WASH, num_format="£#,##0", indent=1,
                        align="left"),
        "tile_gbp2": fmt(font_size=20, bold=True, font_color=NAVY, bg_color=WASH, num_format="£#,##0.00",
                         indent=1, align="left"),
        "tile_int": fmt(font_size=20, bold=True, font_color=NAVY, bg_color=WASH, num_format="#,##0", indent=1,
                        align="left"),
        "tile_pct": fmt(font_size=20, bold=True, font_color=NAVY, bg_color=WASH, num_format="0.0%", indent=1,
                        align="left"),
        "tile_delta": fmt(font_size=9, font_color=INK2, bg_color=WASH, indent=1),
        "wrap": fmt(text_wrap=True, valign="top"),
        "wrap_b": fmt(text_wrap=True, valign="top", bold=True),
        "rank": fmt(align="center", font_color=INK2),
    }

    F_NUM = {"gbp": "£#,##0", "gbp2": "£#,##0.00", "int": "#,##0", "pct": "0.0%"}

    # ------------------------------------------------------------------ Lists (helper)
    months = pd.date_range("2009-12-01", "2011-11-01", freq="MS")
    wb.define_name("MonthList", f"=Lists!$A$2:$A${len(months) + 1}")
    wb.define_name("FirstMonth", "=Lists!$A$2")
    wb.define_name("LastMonth", f"=Lists!$A${len(months) + 1}")

    # ------------------------------------------------------------------ KPIs sheet (first tab)
    k = wb.add_worksheet("KPIs")
    k.activate()
    k.hide_gridlines(2)
    k.set_zoom(90)
    k.set_column(0, 0, 2)
    k.set_column(1, 16, 12.5)
    k.set_column(2, 2, 13)
    k.set_row(1, 30)

    k.write(1, 1, "E-commerce KPI Report", F["title"])
    k.write(2, 1, "UK online gift retailer (wholesale and retail customers)  ·  Source: Online Retail II, "
                  "UCI ML Repository (CC BY 4.0)  ·  Sample project built with public data", F["subtitle"])

    # Period selector
    k.write(4, 1, "Report period", F["h2"])
    k.write_datetime(4, 2, dt.datetime.combine(DEFAULT_START, dt.time()), F["input"])
    k.write(4, 3, "to", F["label"])
    k.write_datetime(4, 4, dt.datetime.combine(DEFAULT_END, dt.time()), F["input"])
    k.write(4, 6, "Compared with", F["h2"])
    W.f(k, 4, 8, "=EDATE(StartMonth,-NMonths)", F["month_out"])
    k.write(4, 9, "to", F["label"])
    W.f(k, 4, 10, "=EDATE(StartMonth,-1)", F["month_out"])
    k.write(4, 12, "Months", F["label"])
    W.f(k, 4, 13, "=(YEAR(EndMonth)-YEAR(StartMonth))*12+MONTH(EndMonth)-MONTH(StartMonth)+1", F["int"])
    W.f(k, 4, 14, "=AND(PrevStart>=FirstMonth,NMonths>0)", wb.add_format({**base, "num_format": ";;;"}))
    k.write(5, 1, "Choose the first and last month in the yellow cells. Every KPI, ranking and chart below "
                  "updates automatically.", F["note"])
    W.f(k, 5, 8, '=IF(EndMonth<StartMonth,"End month must be after the start month",'
                 'IF(NOT(CompOK),"No comparison: data starts in Dec 2009",""))', F["warn"])
    for name, cell in (("StartMonth", "$C$5"), ("EndMonth", "$E$5"), ("PrevStart", "$I$5"),
                       ("PrevEnd", "$K$5"), ("NMonths", "$N$5"), ("CompOK", "$O$5")):
        wb.define_name(name, f"=KPIs!{cell}")
    k.write_comment(4, 14, "TRUE when the comparison period is fully inside the data (Dec 2009 - Nov 2011).")
    for col in (2, 4):
        k.data_validation(4, col, 4, col, {"validate": "list", "source": "=MonthList",
                                          "input_title": "Pick a month",
                                          "input_message": "Months available: Dec 2009 to Nov 2011",
                                          "error_title": "Invalid month",
                                          "error_message": "Pick a month from the list (Dec 2009 - Nov 2011)."})

    in_cur = 'tbl_Orders[Month],">="&StartMonth,tbl_Orders[Month],"<="&EndMonth'
    in_prev = 'tbl_Orders[Month],">="&PrevStart,tbl_Orders[Month],"<="&PrevEnd'

    # KPI summary table (rows 12..), columns B..F
    r0 = 12
    k.write(r0 - 1, 1, "KPI summary", F["h2"])
    for j, h in enumerate(["KPI", "", "Current period", "Comparison period", "Change"]):
        k.write(r0, 1 + j, h, F["th_r"] if j >= 2 else F["th"])
    kpis = [
        ("Net revenue", "gbp", f"=SUMIFS(tbl_Orders[NetRevenue],{in_cur})",
         f"=SUMIFS(tbl_Orders[NetRevenue],{in_prev})"),
        ("Gross sales", "gbp", f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Sale",{in_cur})',
         f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Sale",{in_prev})'),
        ("Returns", "gbp", f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Return",{in_cur})',
         f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Return",{in_prev})'),
        ("Return rate (% of gross sales)", "pct", "=IFERROR(-{c}16/{c}15,0)", "=IFERROR(-{c}16/{c}15,0)"),
        ("Orders", "int", f'=COUNTIFS(tbl_Orders[Type],"Sale",{in_cur})',
         f'=COUNTIFS(tbl_Orders[Type],"Sale",{in_prev})'),
        ("Average order value", "gbp2", "=IFERROR({c}15/{c}18,0)", "=IFERROR({c}15/{c}18,0)"),
        ("Units sold (net)", "int", f"=SUMIFS(tbl_Orders[Units],{in_cur})", f"=SUMIFS(tbl_Orders[Units],{in_prev})"),
        ("Active customers", "int", '=COUNTIF(tbl_Customers[OrdersCur],">0")',
         '=COUNTIF(tbl_Customers[OrdersPrev],">0")'),
        ("Repeat customers (2+ orders)", "int", '=COUNTIF(tbl_Customers[OrdersCur],">1")',
         '=COUNTIF(tbl_Customers[OrdersPrev],">1")'),
        ("Repeat customer rate", "pct", "=IFERROR({c}22/{c}21,0)", "=IFERROR({c}22/{c}21,0)"),
        ("Revenue from repeat customers", "pct",
         '=IFERROR(SUMIFS(tbl_Customers[RevenueCur],tbl_Customers[OrdersCur],">1")/SUM(tbl_Customers[RevenueCur]),0)',
         '=IFERROR(SUMIFS(tbl_Customers[RevenuePrev],tbl_Customers[OrdersPrev],">1")/SUM(tbl_Customers[RevenuePrev]),0)'),
        ("Revenue from guest checkouts", "pct",
         f'=IFERROR(SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[CustomerID],"Guest",{in_cur})/{{c}}14,0)',
         f'=IFERROR(SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[CustomerID],"Guest",{in_prev})/{{c}}14,0)'),
        ("UK share of net revenue", "pct",
         f'=IFERROR(SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Country],"United Kingdom",{in_cur})/{{c}}14,0)',
         f'=IFERROR(SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Country],"United Kingdom",{in_prev})/{{c}}14,0)'),
    ]
    for i, (name, kind, cur, prev) in enumerate(kpis):
        r = r0 + 1 + i
        k.merge_range(r, 1, r, 2, name, F["text"])
        W.f(k, r, 3, cur.replace("{c}", "D"), F[kind])
        W.f(k, r, 4, f'=IF(CompOK,{prev.replace("{c}", "E")[1:]},"n/a")', F[kind] if kind == "pct" else
            wb.add_format({**base, "num_format": F_NUM[kind], "align": "right"}))
        if kind == "pct":
            W.f(k, r, 5, f'=IF(CompOK,(D{r + 1}-E{r + 1})*100,"n/a")', wb.add_format(
                {**base, "num_format": '+0.0" pp";-0.0" pp";0.0" pp"', "align": "right"}))
        else:
            W.f(k, r, 5, f'=IF(AND(CompOK,E{r + 1}<>0),D{r + 1}/E{r + 1}-1,"n/a")',
                wb.add_format({**base, "num_format": "+0.0%;-0.0%;0.0%", "align": "right"}))
    last_kpi_row = r0 + len(kpis)
    k.conditional_format(r0 + 1, 4, last_kpi_row, 5, {"type": "formula", "criteria": f"=NOT(ISNUMBER(E{r0 + 2}))",
                                                         "format": wb.add_format({"font_color": MUTED})})
    # Green / red change column (returns and return rate: lower is better)
    good_up = [i for i, (kname, *_) in enumerate(kpis) if kname not in ("Returns", "Return rate (% of gross sales)",
                                                                  "Revenue from guest checkouts")]
    for i in range(len(kpis)):
        r = r0 + 1 + i
        up_good = i in good_up
        name = kpis[i][0]
        if name in ("UK share of net revenue",):
            continue
        cell = f"$F${r + 1}"
        k.conditional_format(r, 5, r, 5, {"type": "formula", "criteria": f"=AND(ISNUMBER({cell}),{cell}>0)",
                                          "format": wb.add_format({"font_color": GOOD_TXT if up_good else BAD_TXT,
                                                                   "bold": True})})
        k.conditional_format(r, 5, r, 5, {"type": "formula", "criteria": f"=AND(ISNUMBER({cell}),{cell}<0)",
                                          "format": wb.add_format({"font_color": BAD_TXT if up_good else GOOD_TXT,
                                                                   "bold": True})})
    k.write(last_kpi_row + 1, 1, "Returns are negative values. 'pp' = percentage points. Definitions: Notes sheet.",
            F["note"])

    # KPI tiles (rows 7-9) reading the summary table
    tiles = [("Net revenue", "D14", "F14", "tile_gbp"), ("Orders", "D18", "F18", "tile_int"),
             ("Average order value", "D19", "F19", "tile_gbp2"), ("Active customers", "D21", "F21", "tile_int"),
             ("Repeat customer rate", "D23", "F23", "tile_pct")]
    for j, (label, vcell, dcell, kind) in enumerate(tiles):
        c0 = 1 + j * 3
        k.merge_range(7, c0, 7, c0 + 2, label, F["tile_label"])
        k.merge_range(8, c0, 8, c0 + 2, "", F[kind])
        W.f(k, 8, c0, f"={vcell}", F[kind])
        shown = f"ABS({dcell})" if kind == "tile_pct" else f"ABS({dcell})*100"
        unit = "pp" if kind == "tile_pct" else "%"
        delta = (f'=IF(ISNUMBER({dcell}),IF({dcell}>=0,"▲ ","▼ ")&TEXT({shown},"0.0")&" {unit} vs comparison"'
                 f',"No comparison period")')
        k.merge_range(9, c0, 9, c0 + 2, "", F["tile_delta"])
        W.f(k, 9, c0, delta, F["tile_delta"])
        k.conditional_format(9, c0, 9, c0, {"type": "formula", "criteria": f"=AND(ISNUMBER({dcell}),{dcell}>0)",
                                            "format": wb.add_format({"font_color": GOOD_TXT, "bold": True})})
        k.conditional_format(9, c0, 9, c0, {"type": "formula", "criteria": f"=AND(ISNUMBER({dcell}),{dcell}<0)",
                                            "format": wb.add_format({"font_color": BAD_TXT, "bold": True})})
    k.set_row(7, 18)
    k.set_row(8, 34)
    k.set_row(9, 18)

    # Top 10 international markets (H..L), rows 12..
    k.write(r0 - 1, 7, "Top 10 international markets (excluding the UK)", F["h2"])
    for j, h in enumerate(["#", "Country", "", "Net revenue", "Orders", "Share of total"]):
        k.write(r0, 7 + j, h, F["th_r"] if j >= 3 else F["th"])
    for i in range(10):
        r = r0 + 1 + i
        k.write(r, 7, i + 1, F["rank"])
        k.merge_range(r, 8, r, 9, "", F["text"])
        W.f(k, r, 8, f"=INDEX(tbl_Countries[Country],MATCH(LARGE(tbl_Countries[RankKey],{i + 1}),"
                     f"tbl_Countries[RankKey],0))", F["text"])
        W.f(k, r, 10, f"=INDEX(tbl_Countries[RevenueCur],MATCH($I{r + 1},tbl_Countries[Country],0))", F["gbp"])
        W.f(k, r, 11, f"=INDEX(tbl_Countries[OrdersCur],MATCH($I{r + 1},tbl_Countries[Country],0))", F["int"])
        W.f(k, r, 12, f"=IFERROR(K{r + 1}/$D$14,0)", F["pct"])
    k.conditional_format(r0 + 1, 10, r0 + 10, 10, {"type": "data_bar", "bar_color": "#9EC5F4", "bar_solid": True,
                                                   "bar_no_border": True})

    # Top 10 products, rows 28..
    p0 = 29
    k.write(p0 - 1, 1, "Top 10 products by net revenue", F["h2"])
    for j, h in enumerate(["#", "Stock code", "Description", "", "", "Units", "Net revenue", "Share of total"]):
        k.write(p0, 1 + j, h, F["th_r"] if j >= 5 else F["th"])
    for i in range(10):
        r = p0 + 1 + i
        k.write(r, 1, i + 1, F["rank"])
        W.f(k, r, 2, f"=INDEX(tbl_Products[StockCode],MATCH(LARGE(tbl_Products[RankKey],{i + 1}),"
                     f"tbl_Products[RankKey],0))", F["text"])
        k.merge_range(r, 3, r, 5, "", F["text"])
        W.f(k, r, 3, f"=INDEX(tbl_Products[Description],MATCH($C{r + 1},tbl_Products[StockCode],0))", F["text"])
        W.f(k, r, 6, f"=INDEX(tbl_Products[UnitsCur],MATCH($C{r + 1},tbl_Products[StockCode],0))", F["int"])
        W.f(k, r, 7, f"=INDEX(tbl_Products[RevenueCur],MATCH($C{r + 1},tbl_Products[StockCode],0))", F["gbp"])
        W.f(k, r, 8, f"=IFERROR(H{r + 1}/$D$14,0)", F["pct"])
    k.conditional_format(p0 + 1, 7, p0 + 10, 7, {"type": "data_bar", "bar_color": "#9EC5F4", "bar_solid": True,
                                                 "bar_no_border": True})

    # Monthly trend (all 24 months), rows 43..
    m0 = 43
    k.write(m0 - 1, 1, "Monthly trend (all months; the selected period is highlighted)", F["h2"])
    heads = ["Month", "Gross sales", "Returns", "Net revenue", "Orders", "Avg order value", "New customers*",
             "Change vs previous month", "Change vs same month last year"]
    for j, h in enumerate(heads):
        k.write(m0, 1 + j, h, F["th_r"] if j else F["th"])
    k.set_row(m0, 30)
    for i, m in enumerate(months):
        r = m0 + 1 + i
        rr = r + 1
        W.f(k, r, 1, f"=INDEX(MonthList,{i + 1})", F["month"])
        W.f(k, r, 2, f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Sale",tbl_Orders[Month],$B{rr})', F["gbp"])
        W.f(k, r, 3, f'=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Type],"Return",tbl_Orders[Month],$B{rr})', F["gbp"])
        W.f(k, r, 4, f"=C{rr}+D{rr}", F["gbp"])
        W.f(k, r, 5, f'=COUNTIFS(tbl_Orders[Type],"Sale",tbl_Orders[Month],$B{rr})', F["int"])
        W.f(k, r, 6, f"=IFERROR(C{rr}/F{rr},0)", F["gbp2"])
        W.f(k, r, 7, f'=COUNTIFS(tbl_Customers[FirstOrder],">="&$B{rr},tbl_Customers[FirstOrder],"<="&EOMONTH($B{rr},0))',
            F["int"])
        if i == 0:
            k.write(r, 8, "n/a", wb.add_format({**base, "align": "right", "font_color": MUTED}))
        else:
            W.f(k, r, 8, f"=IFERROR(E{rr}/E{rr - 1}-1,0)", F["pct_signed"])
        if i < 12:
            k.write(r, 9, "n/a", wb.add_format({**base, "align": "right", "font_color": MUTED}))
        else:
            W.f(k, r, 9, f"=IFERROR(E{rr}/E{rr - 12}-1,0)", F["pct_signed"])
    m_last = m0 + len(months)
    k.conditional_format(m0 + 1, 1, m_last, 9, {
        "type": "formula", "criteria": f"=AND($B{m0 + 2}>=StartMonth,$B{m0 + 2}<=EndMonth)",
        "format": wb.add_format({"bg_color": WASH})})
    k.conditional_format(m0 + 1, 4, m_last, 4, {"type": "data_bar", "bar_color": "#86B6EF", "bar_solid": True,
                                                "bar_no_border": True})
    for col in (8, 9):
        k.conditional_format(m0 + 1, col, m_last, col, {"type": "3_color_scale", "min_color": "#F4B9B2",
                                                        "mid_type": "num", "mid_value": 0, "mid_color": "#FFFFFF",
                                                        "max_color": "#B7E1C1"})
    k.write(m_last + 1, 1, "* New customers = identified customers whose first order in the data falls in that "
                           "month. Dec 2009 counts every customer active that month, because earlier history "
                           "is not in the dataset.", F["note"])

    # Year-over-year helper (for the line chart)
    y0 = m0
    k.write(y0 - 1, 11, "Same months, two years", F["h2"])
    for j, h in enumerate(["Month", "Dec 09 - Nov 10", "Dec 10 - Nov 11"]):
        k.write(y0, 11 + j, h, F["th_r"] if j else F["th"])
    for i in range(12):
        r = y0 + 1 + i
        W.f(k, r, 11, f'=TEXT(B{m0 + 2 + i},"mmm")', F["text"])
        W.f(k, r, 12, f"=E{m0 + 2 + i}", F["gbp"])
        W.f(k, r, 13, f"=E{m0 + 14 + i}", F["gbp"])

    # ---------------- Charts
    def style_axis(ax_opts, num_format=None):
        ax = {"line": {"color": "#C3C2B7"}, "num_font": {"name": FONT, "size": 9, "color": INK2},
              "major_gridlines": {"visible": False}}
        if num_format:
            ax["num_format"] = num_format
        ax.update(ax_opts)
        return ax

    line = wb.add_chart({"type": "line"})
    for col, color, name in ((12, "#9EC5F4", "Dec 2009 - Nov 2010"), (13, BLUE, "Dec 2010 - Nov 2011")):
        line.add_series({
            "name": name,
            "categories": ["KPIs", y0 + 1, 11, y0 + 12, 11],
            "values": ["KPIs", y0 + 1, col, y0 + 12, col],
            "line": {"color": color, "width": 2.25},
            "marker": {"type": "circle", "size": 5, "fill": {"color": color}, "border": {"color": "#FFFFFF"}},
        })
    line.set_title({"name": "Monthly net revenue: this year vs last year",
                    "name_font": {"name": FONT, "size": 12, "bold": True, "color": NAVY}})
    line.set_x_axis(style_axis({}))
    line.set_y_axis(style_axis({"major_gridlines": {"visible": True, "line": {"color": GRID}},
                                "line": {"none": True}}, "£#,##0,\"K\""))
    line.set_legend({"position": "top", "font": {"name": FONT, "size": 9, "color": INK2}})
    line.set_chartarea({"border": {"none": True}})
    line.set_size({"width": 620, "height": 300})
    k.insert_chart(y0 + 13, 11, line, {"x_offset": 4, "y_offset": 10})

    bar_c = wb.add_chart({"type": "bar"})
    bar_c.add_series({"name": "Net revenue", "categories": ["KPIs", r0 + 1, 8, r0 + 10, 8],
                      "values": ["KPIs", r0 + 1, 10, r0 + 10, 10], "fill": {"color": BLUE}, "gap": 80,
                      "data_labels": {"value": True, "num_format": "£#,##0,\"K\"",
                                      "font": {"name": FONT, "size": 8, "color": INK2}}})
    bar_c.set_title({"name": "Top international markets (selected period)",
                     "name_font": {"name": FONT, "size": 12, "bold": True, "color": NAVY}})
    bar_c.set_y_axis(style_axis({"reverse": True}))
    bar_c.set_x_axis(style_axis({"visible": False}, "£#,##0,\"K\""))
    bar_c.set_legend({"none": True})
    bar_c.set_chartarea({"border": {"none": True}})
    bar_c.set_size({"width": 470, "height": 330})
    k.insert_chart(r0 - 1, 14, bar_c, {"x_offset": 10, "y_offset": 0})

    bar_p = wb.add_chart({"type": "bar"})
    bar_p.add_series({"name": "Net revenue", "categories": ["KPIs", p0 + 1, 3, p0 + 10, 3],
                      "values": ["KPIs", p0 + 1, 7, p0 + 10, 7], "fill": {"color": ORANGE}, "gap": 80,
                      "data_labels": {"value": True, "num_format": "£#,##0,\"K\"",
                                      "font": {"name": FONT, "size": 8, "color": INK2}}})
    bar_p.set_title({"name": "Top 10 products (selected period)",
                     "name_font": {"name": FONT, "size": 12, "bold": True, "color": NAVY}})
    bar_p.set_y_axis(style_axis({"reverse": True, "num_font": {"name": FONT, "size": 8, "color": INK2}}))
    bar_p.set_x_axis(style_axis({"visible": False}))
    bar_p.set_legend({"none": True})
    bar_p.set_chartarea({"border": {"none": True}})
    bar_p.set_size({"width": 620, "height": 280})
    k.insert_chart(p0 - 1, 10, bar_p, {"x_offset": 10, "y_offset": 0})

    k.freeze_panes(6, 0)
    k.set_landscape()
    k.set_paper(9)
    k.fit_to_pages(1, 0)
    k.print_area(0, 0, m_last + 4, 18)
    k.set_margins(0.3, 0.3, 0.4, 0.4)

    # ------------------------------------------------------------------ Data (orders table)
    o = t["orders"]
    d = wb.add_worksheet("Data")
    cols = ["InvoiceNo", "InvoiceDate", "Month", "Type", "CustomerID", "Country", "Lines", "Units", "NetRevenue"]
    d.add_table(0, 0, len(o), len(cols) - 1, {
        "name": "tbl_Orders", "style": "Table Style Medium 2",
        "columns": [{"header": c} for c in cols]})
    fmts = [None, F["date"], F["month"], None, None, None, F["int"], F["int"], F["gbp2"]]
    for c, (name, f_) in enumerate(zip(cols, fmts)):
        series = o[name]
        if name in ("InvoiceDate", "Month"):
            for r, v in enumerate(series, start=1):
                d.write_datetime(r, c, v.to_pydatetime(), f_)
        elif name in ("Lines", "Units", "NetRevenue"):
            for r, v in enumerate(series, start=1):
                d.write_number(r, c, float(v), f_)
        else:
            for r, v in enumerate(series, start=1):
                d.write_string(r, c, str(v))
    d.set_column(0, 0, 11); d.set_column(1, 2, 12); d.set_column(3, 3, 8); d.set_column(4, 4, 11)
    d.set_column(5, 5, 20); d.set_column(6, 7, 8); d.set_column(8, 8, 12)
    d.freeze_panes(1, 0)

    # ------------------------------------------------------------------ Customers
    cu = t["customers"]
    cs = wb.add_worksheet("Customers")
    ccols = ["CustomerID", "Country", "FirstOrder", "OrdersCur", "RevenueCur", "OrdersPrev", "RevenuePrev"]
    cs.add_table(0, 0, len(cu), len(ccols) - 1, {
        "name": "tbl_Customers", "style": "Table Style Medium 2",
        "columns": [{"header": c} for c in ccols]})
    tr = "tbl_Customers[[#This Row],[CustomerID]]"
    cust_f = {
        2: (f'=MINIFS(tbl_Orders[InvoiceDate],tbl_Orders[CustomerID],{tr},tbl_Orders[Type],"Sale")',
            wb.add_format({**base, "num_format": 'yyyy-mm-dd;;""'})),
        3: (f'=COUNTIFS(tbl_Orders[CustomerID],{tr},tbl_Orders[Type],"Sale",{in_cur})', F["int"]),
        4: (f"=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[CustomerID],{tr},{in_cur})", F["gbp2"]),
        5: (f'=IF(CompOK,COUNTIFS(tbl_Orders[CustomerID],{tr},tbl_Orders[Type],"Sale",{in_prev}),0)', F["int"]),
        6: (f"=IF(CompOK,SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[CustomerID],{tr},{in_prev}),0)", F["gbp2"]),
    }
    for r, (cid, country) in enumerate(zip(cu["CustomerID"], cu["Country"]), start=1):
        cs.write_string(r, 0, cid)
        cs.write_string(r, 1, country)
        for c, (form, f_) in cust_f.items():
            W.f(cs, r, c, form, f_)
    cs.set_column(0, 0, 11); cs.set_column(1, 1, 20); cs.set_column(2, 6, 12)
    cs.freeze_panes(1, 0)
    cs.write_comment(0, 3, "Orders in the selected report period (KPIs sheet).")
    cs.write_comment(0, 5, "Orders in the comparison period (KPIs sheet).")

    # ------------------------------------------------------------------ Countries
    countries = sorted(o["Country"].unique())
    ct = wb.add_worksheet("Countries")
    tcols = ["Country", "RevenueCur", "OrdersCur", "RevenuePrev", "RankKey"]
    ct.add_table(0, 0, len(countries), len(tcols) - 1, {
        "name": "tbl_Countries", "style": "Table Style Medium 2", "columns": [{"header": c} for c in tcols]})
    trc = "tbl_Countries[[#This Row],[Country]]"
    for r, name in enumerate(countries, start=1):
        ct.write_string(r, 0, name)
        W.f(ct, r, 1, f"=SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Country],{trc},{in_cur})", F["gbp"])
        W.f(ct, r, 2, f'=COUNTIFS(tbl_Orders[Country],{trc},tbl_Orders[Type],"Sale",{in_cur})', F["int"])
        W.f(ct, r, 3, f"=IF(CompOK,SUMIFS(tbl_Orders[NetRevenue],tbl_Orders[Country],{trc},{in_prev}),0)", F["gbp"])
        W.f(ct, r, 4, f'=IF({trc}="United Kingdom",-1E+15,tbl_Countries[[#This Row],[RevenueCur]]-ROW()/1000000)',
            wb.add_format({**base, "num_format": "0.000000", "font_color": MUTED}))
    ct.set_column(0, 0, 22); ct.set_column(1, 4, 13)
    ct.write_comment(0, 4, "Helper for the ranking: net revenue minus a tiny row-based amount to break ties. "
                           "The UK is excluded from the international ranking.")
    ct.freeze_panes(1, 0)

    # ------------------------------------------------------------------ Products and ProductData
    pmo = t["product_month"]
    pdws = wb.add_worksheet("ProductData")
    pcols = ["StockCode", "Month", "Units", "NetRevenue", "Orders"]
    pdws.add_table(0, 0, len(pmo), len(pcols) - 1, {
        "name": "tbl_ProductMonth", "style": "Table Style Medium 2", "columns": [{"header": c} for c in pcols]})
    for r, row in enumerate(pmo.itertuples(index=False), start=1):
        pdws.write_string(r, 0, row.StockCode)
        pdws.write_datetime(r, 1, row.Month.to_pydatetime(), F["month"])
        pdws.write_number(r, 2, float(row.Units), F["int"])
        pdws.write_number(r, 3, float(row.NetRevenue), F["gbp2"])
        pdws.write_number(r, 4, float(row.Orders), F["int"])
    pdws.set_column(0, 4, 12)
    pdws.freeze_panes(1, 0)

    pr = t["products"]
    ps = wb.add_worksheet("Products")
    prcols = ["StockCode", "Description", "UnitsCur", "RevenueCur", "RankKey"]
    ps.add_table(0, 0, len(pr), len(prcols) - 1, {
        "name": "tbl_Products", "style": "Table Style Medium 2", "columns": [{"header": c} for c in prcols]})
    trp = "tbl_Products[[#This Row],[StockCode]]"
    pm_cur = 'tbl_ProductMonth[Month],">="&StartMonth,tbl_ProductMonth[Month],"<="&EndMonth'
    for r, (code, desc) in enumerate(zip(pr["StockCode"], pr["Description"]), start=1):
        ps.write_string(r, 0, code)
        ps.write_string(r, 1, desc)
        W.f(ps, r, 2, f"=SUMIFS(tbl_ProductMonth[Units],tbl_ProductMonth[StockCode],{trp},{pm_cur})", F["int"])
        W.f(ps, r, 3, f"=SUMIFS(tbl_ProductMonth[NetRevenue],tbl_ProductMonth[StockCode],{trp},{pm_cur})", F["gbp2"])
        W.f(ps, r, 4, f"=tbl_Products[[#This Row],[RevenueCur]]-ROW()/1000000",
            wb.add_format({**base, "num_format": "0.000000", "font_color": MUTED}))
    ps.set_column(0, 0, 11); ps.set_column(1, 1, 40); ps.set_column(2, 4, 12)
    ps.freeze_panes(1, 0)

    # ------------------------------------------------------------------ Notes
    n = wb.add_worksheet("Notes")
    n.hide_gridlines(2)
    n.set_column(0, 0, 2); n.set_column(1, 1, 32); n.set_column(2, 2, 70); n.set_column(3, 3, 48)
    n.write(1, 1, "Notes: KPI definitions, data and method", F["title"])
    n.write(2, 1, "Sample project built with public data. Prepared by Marlon Jiménez Valencia.", F["subtitle"])
    row = 4
    n.write(row, 1, "KPI definitions", F["h2"]); row += 1
    for j, h in enumerate(["KPI", "Definition", "How it is calculated"]):
        n.write(row, 1 + j, h, F["th"])
    row += 1
    defs = [
        ("Net revenue", "Sales minus returns, in GBP, for invoices dated in the period.",
         "SUMIFS on tbl_Orders[NetRevenue] (returns are negative)."),
        ("Gross sales", "Value of sales invoices only (quantity × unit price).", "SUMIFS with Type = \"Sale\"."),
        ("Returns", "Value of cancelled / returned items (shown as a negative number).",
         "SUMIFS with Type = \"Return\" (invoice numbers starting with C)."),
        ("Return rate", "Returns as a share of gross sales.", "-Returns / Gross sales."),
        ("Orders", "Number of sales invoices.", "COUNTIFS with Type = \"Sale\"."),
        ("Average order value (AOV)", "Average value of a sales invoice.", "Gross sales / Orders."),
        ("Units sold (net)", "Units sold minus units returned.", "SUMIFS on tbl_Orders[Units]."),
        ("Active customers", "Identified customers with at least one sales invoice in the period.",
         "COUNTIF on tbl_Customers[OrdersCur] > 0. Guest checkouts are excluded."),
        ("Repeat customers", "Active customers with two or more orders in the period.",
         "COUNTIF on tbl_Customers[OrdersCur] > 1."),
        ("Repeat customer rate", "Share of active customers who ordered more than once.",
         "Repeat customers / Active customers."),
        ("Revenue from repeat customers", "Share of identified-customer revenue that comes from repeat customers.",
         "SUMIFS on tbl_Customers[RevenueCur] where OrdersCur > 1, divided by total."),
        ("Revenue from guest checkouts", "Share of net revenue from invoices without a customer ID.",
         "SUMIFS with CustomerID = \"Guest\" / Net revenue."),
        ("New customers", "Identified customers whose first order in the data is in that month.",
         "MINIFS gives each customer's first order date; COUNTIFS counts them by month."),
        ("Top markets / products", "Ranking by net revenue in the selected period.",
         "LARGE on a ranking helper column, then INDEX/MATCH to fetch the name and values."),
        ("Comparison period", "The same number of months right before the report period.",
         "EDATE(StartMonth, -NMonths). Shown as n/a if it starts before Dec 2009."),
    ]
    for kpi, dfn, how in defs:
        n.write(row, 1, kpi, F["wrap_b"]); n.write(row, 2, dfn, F["wrap"]); n.write(row, 3, how, F["wrap"])
        n.set_row(row, 30)
        row += 1
    row += 1
    n.write(row, 1, "Data source", F["h2"]); row += 1
    src = [
        ("Dataset", "Online Retail II: all transactions of a UK-based online retailer of gift-ware, "
                    "Dec 2009 - Dec 2011. Many customers are wholesalers."),
        ("Publisher", "UCI Machine Learning Repository (Daqing Chen, 2012). DOI: 10.24432/C5CG6D"),
        ("Licence", "Creative Commons Attribution 4.0 International (CC BY 4.0)."),
        ("Period used", "24 full months: Dec 2009 - Nov 2011 (Dec 2011 has only 9 days and is excluded)."),
        ("Currency", "GBP (pounds sterling). Values are invoice values: quantity × unit price."),
    ]
    for a, b in src:
        n.write(row, 1, a, F["wrap_b"]); n.merge_range(row, 2, row, 3, b, F["wrap"]); n.set_row(row, 28)
        row += 1
    row += 1
    n.write(row, 1, "Cleaning steps (from the raw file to the Data sheet)", F["h2"]); row += 1
    for j, h in enumerate(["Rule", "Note", "Rows removed / rows after"]):
        n.write(row, 1 + j, h, F["th"])
    row += 1
    for _, lg in t["cleaning_log"].iterrows():
        n.write(row, 1, lg["rule"], F["wrap"])
        n.write(row, 2, "" if pd.isna(lg["note"]) else lg["note"], F["wrap"])
        n.write(row, 3, f"{int(lg['rows_removed']):,} removed  /  {int(lg['rows_after']):,} rows", F["wrap"])
        n.set_row(row, 30)
        row += 1
    n.write(row, 1, f"Invoice lines are then grouped into {len(o):,} invoices (Data sheet).", F["note"])
    row += 2
    n.write(row, 1, "Limitations", F["h2"]); row += 1
    for lim in [
        "About a fifth of invoice lines have no customer ID ('Guest'). They count for revenue and orders, "
        "but not for customer KPIs.",
        "Returns are counted in the month they were processed, which may differ from the month of the original sale.",
        "First-order dates only see history from Dec 2009, so 'new customers' are overstated in the first months.",
        "This is a sample analysis of a public dataset, not a client engagement.",
    ]:
        n.merge_range(row, 1, row, 3, "•  " + lim, F["wrap"]); n.set_row(row, 28)
        row += 1
    n.print_area(0, 0, row, 3)
    n.fit_to_pages(1, 0)
    n.set_portrait()
    n.set_paper(9)

    ls = wb.add_worksheet("Lists")
    ls.write(0, 0, "Month", F["th"])
    for i, m in enumerate(months, start=1):
        ls.write_datetime(i, 0, m.to_pydatetime(), F["month"])
    ls.set_column(0, 0, 14)
    ls.hide()
    wb.close()
    return W.positions


if __name__ == "__main__":
    print(build(PROJECT / "output" / "ecommerce_kpi_report.xlsx"))
