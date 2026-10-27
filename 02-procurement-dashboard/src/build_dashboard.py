"""Build the one-page interactive dashboard (HTML + Plotly.js) from the star schema.

The data is embedded in the page (compact column arrays), so the file works on GitHub Pages
and when opened locally. Output: output/dashboard.html and ../docs/procurement-dashboard/index.html
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
PBI = PROJECT / "powerbi" / "data"
OUT = PROJECT / "output" / "dashboard.html"
DOCS = PROJECT.parent / "docs" / "procurement-dashboard" / "index.html"
PLOTLY = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


def compact_data() -> dict:
    f = pd.read_csv(PBI / "fact_contracts.csv")
    ent = pd.read_csv(PBI / "dim_entity.csv")
    mod = pd.read_csv(PBI / "dim_modality.csv")
    typ = pd.read_csv(PBI / "dim_contract_type.csv")
    meta = json.loads((PROJECT / "data" / "clean" / "metadata.json").read_text())

    levels = sorted(ent["level"].unique())
    depts = sorted(ent["department"].unique(), key=lambda x: (x == "Not defined", x))
    groups = (f.merge(mod, on="modality_key").groupby("modality_group")["contract_value"].sum()
              .sort_values(ascending=False).index.tolist())
    types = typ.sort_values("contract_type")["contract_type"].tolist()
    suppliers = ["Natural person", "Company / organisation", "Other / not defined"]

    ent = ent.set_index("entity_key")
    ent_keys = ent.index.tolist()
    ent_idx = {k: i for i, k in enumerate(ent_keys)}
    entities = [[ent.loc[k, "entity_name"], levels.index(ent.loc[k, "level"]), depts.index(ent.loc[k, "department"])]
                for k in ent_keys]
    f = f.merge(mod[["modality_key", "modality_group"]], on="modality_key")
    f = f.merge(typ[["contract_type_key", "contract_type"]], on="contract_type_key")
    return {
        "meta": meta,
        "levels": levels, "depts": depts, "groups": groups, "types": types, "suppliers": suppliers,
        "entities": entities,
        "mo": pd.to_datetime(f["date_signed"]).dt.month.tolist(),
        "en": f["entity_key"].map(ent_idx).tolist(),
        "mg": f["modality_group"].map(groups.index).tolist(),
        "ct": f["contract_type"].map(types.index).tolist(),
        "st": f["supplier_type"].map(suppliers.index).tolist(),
        "sm": f["is_sme"].tolist(),
        "v": f["contract_value"].astype("int64").tolist(),
    }


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Education Procurement Dashboard</title>
<meta name="description" content="Interactive dashboard of Colombia's public procurement in the education sector, contracts signed in 2025 (SECOP II open data). Sample project built with public data.">
<script src="__PLOTLY__"></script>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10); --brand: #0d366b;
  --series-1: #2a78d6; --series-2: #eb6834; --wash: #eef4fc; --focus: #2a78d6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10); --brand: #9ec5f4;
    --series-1: #3987e5; --series-2: #d95926; --wash: #16243a; --focus: #86b6ef;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10); --brand: #9ec5f4;
  --series-1: #3987e5; --series-2: #d95926; --wash: #16243a; --focus: #86b6ef;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", Inter, Roboto, sans-serif; }
.wrap { max-width: 1280px; margin: 0 auto; padding: 24px 24px 40px; }
header h1 { font-size: 26px; line-height: 1.2; margin: 0 0 6px; color: var(--brand); }
header p { margin: 0; color: var(--ink-2); font-size: 14px; line-height: 1.5; }
.tag { display: inline-block; font-size: 12px; font-weight: 600; color: var(--ink-2);
  border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; margin-top: 10px; }
.filters { display: flex; flex-wrap: wrap; gap: 10px 12px; align-items: flex-end; margin: 22px 0 18px; }
.filters label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--ink-2); }
.filters select, .filters button { font: inherit; font-size: 14px; color: var(--ink); background: var(--surface);
  border: 1px solid var(--axis); border-radius: 8px; padding: 7px 10px; min-width: 140px; max-width: 240px; }
.filters button { cursor: pointer; min-width: 0; }
.filters select:focus-visible, .filters button:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }
.status { font-size: 13px; color: var(--ink-2); margin: -6px 0 14px; min-height: 18px; }
.tiles { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.tile .label { font-size: 13px; color: var(--ink-2); }
.tile .value { font-size: 28px; font-weight: 650; margin: 6px 0 2px; color: var(--ink); }
.tile .sub { font-size: 12px; color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 14px 6px;
  min-width: 0; }
.card h2 { font-size: 15px; margin: 0 0 2px; }
.card p.note { font-size: 12px; color: var(--muted); margin: 0 0 4px; }
.chart { width: 100%; height: 330px; }
.table-card { margin-top: 16px; }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--grid); }
th { color: var(--ink-2); font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
footer { margin-top: 22px; font-size: 12.5px; color: var(--ink-2); line-height: 1.6; }
footer h3 { font-size: 13px; margin: 14px 0 4px; color: var(--ink); }
footer a { color: var(--series-1); }
@media (max-width: 1100px) { .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 760px) {
  .wrap { padding: 16px 16px 32px; }
  header h1 { font-size: 21px; }
  .grid { grid-template-columns: minmax(0, 1fr); }
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .tile .value { font-size: 22px; }
  .filters { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filters select, .filters button { min-width: 0; max-width: none; width: 100%; }
  .chart { height: 300px; }
  .hide-sm { display: none; }
  td:first-child { font-size: 12px; overflow-wrap: anywhere; }
  th { font-size: 11.5px; white-space: normal; }
  th, td { padding: 6px 5px; }
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Colombia public procurement: education sector, 2025</h1>
  <p>Contracts signed in 2025 by public entities of the education sector, from SECOP II open data
     (Colombia Compra Eficiente). Values in Colombian pesos (COP).</p>
  <span class="tag">Sample project built with public data</span>
</header>

<section class="filters" aria-label="Filters">
  <label>From month<select id="fFrom"></select></label>
  <label>To month<select id="fTo"></select></label>
  <label>Entity level<select id="fLevel"></select></label>
  <label>Department<select id="fDept"></select></label>
  <label>Procurement method<select id="fGroup"></select></label>
  <label>Contract type<select id="fType"></select></label>
  <label>Supplier<select id="fSupp"></select></label>
  <button id="reset" type="button">Reset filters</button>
</section>
<div class="status" id="status" aria-live="polite"></div>

<section class="tiles" aria-label="Key figures">
  <div class="tile"><div class="label">Contracts</div><div class="value" id="kN"></div><div class="sub" id="kNs"></div></div>
  <div class="tile"><div class="label">Total value (COP)</div><div class="value" id="kV"></div><div class="sub" id="kVs"></div></div>
  <div class="tile"><div class="label">Median contract (COP)</div><div class="value" id="kMed"></div><div class="sub">half of contracts are smaller</div></div>
  <div class="tile"><div class="label">Direct contracting</div><div class="value" id="kDir"></div><div class="sub" id="kDirs"></div></div>
  <div class="tile"><div class="label">Contracts with individuals</div><div class="value" id="kNat"></div><div class="sub" id="kNats"></div></div>
  <div class="tile"><div class="label">SME suppliers</div><div class="value" id="kSme"></div><div class="sub">share of contracts</div></div>
</section>

<section class="grid">
  <div class="card"><h2>Contract value by month signed</h2><p class="note">COP billions · hover for the number of contracts</p><div class="chart" id="cMonth"></div></div>
  <div class="card"><h2>Value by procurement method</h2><p class="note">COP billions · direct contracting highlighted</p><div class="chart" id="cGroup"></div></div>
  <div class="card"><h2>Top 10 entities by contract value</h2><p class="note">COP billions</p><div class="chart" id="cEnt"></div></div>
  <div class="card"><h2>Contracts by type</h2><p class="note">Number of contracts (top 8 types)</p><div class="chart" id="cType"></div></div>
  <div class="card"><h2>Top 10 departments by contract value</h2><p class="note">Department of the contracting entity · COP billions</p><div class="chart" id="cDept"></div></div>
  <div class="card"><h2>Contract size distribution</h2><p class="note">Number of contracts by value band (COP)</p><div class="chart" id="cSize"></div></div>
</section>

<section class="card table-card">
  <h2>Table view: top 15 entities</h2>
  <p class="note">Same filters as the charts</p>
  <div class="table-scroll"><table id="tEnt" aria-label="Top 15 entities"><thead><tr>
    <th>Entity</th><th class="hide-sm">Level</th><th class="hide-sm">Department</th><th class="n">Contracts</th><th class="n">Value (COP bn)</th><th class="n">Direct %</th>
  </tr></thead><tbody></tbody></table></div>
</section>

<footer>
  <h3>About the data</h3>
  Source: <a href="https://www.datos.gov.co/d/jbjy-vk9h" rel="noopener">SECOP II – Contratos Electrónicos</a>,
  Agencia Nacional de Contratación Pública – Colombia Compra Eficiente, published on datos.gov.co under
  <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>.
  Filter used: sector = "Educación Nacional" and signing date in 2025. Data extracted on <span id="extracted"></span>;
  SECOP II is updated continuously, so later extractions can differ.
  <h3>Method notes</h3>
  Procurement methods are grouped from SECOP's "modalidad de contratación" (for example, "Contratación directa" and
  "Contratación Directa (con ofertas)" are both <em>direct contracting</em>). "Individuals" are contractors identified with a
  personal ID (cédula, passport). Department and level are those of the contracting entity, as reported by SECOP.
  Contracts with a value of 0 are counted but do not change the totals. Names of people are not included anywhere in this project.
  <h3>Limitations</h3>
  Values are contract values at signing (plus registered changes), not payments. Sector and level classifications come from
  the source and can contain errors. This is a sample analysis of open data, not an audit.
  <p>Built by Marlon Jiménez Valencia · Python (pandas) + Plotly.js · Sample project built with public data.</p>
</footer>
</div>

<script>
const D = __DATA__;
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const BANDS = [["Value 0", 0, 1], ["< 5M", 1, 5e6], ["5M – 20M", 5e6, 2e7], ["20M – 50M", 2e7, 5e7],
               ["50M – 100M", 5e7, 1e8], ["100M – 1bn", 1e8, 1e9], ["≥ 1bn", 1e9, Infinity]];
const $ = (id) => document.getElementById(id);

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function fmtInt(x) { return Math.round(x).toLocaleString("en-US"); }
function fmtBn(x) { return (x / 1e9).toLocaleString("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 }); }
function fmtCOP(x) {
  if (x >= 1e12) return (x / 1e12).toFixed(2) + " tn";
  if (x >= 1e9) return (x / 1e9).toFixed(1) + " bn";
  if (x >= 1e6) return (x / 1e6).toFixed(1) + "M";
  return fmtInt(x);
}
function pct(a, b) { return b ? (100 * a / b).toFixed(1) + "%" : "–"; }
function truncate(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

function fillSelect(el, options, allLabel) {
  if (allLabel) { const o = document.createElement("option"); o.value = "all"; o.textContent = allLabel; el.appendChild(o); }
  options.forEach((label, i) => { const o = document.createElement("option"); o.value = String(i); o.textContent = label; el.appendChild(o); });
}
fillSelect($("fFrom"), MONTHS.map((m) => m + " 2025"));
fillSelect($("fTo"), MONTHS.map((m) => m + " 2025"));
$("fTo").value = "11";
fillSelect($("fLevel"), D.levels, "All levels");
fillSelect($("fDept"), D.depts, "All departments");
fillSelect($("fGroup"), D.groups, "All methods");
fillSelect($("fType"), D.types, "All types");
fillSelect($("fSupp"), D.suppliers, "All suppliers");
$("extracted").textContent = D.meta.extracted_on;

function current() {
  return { from: +$("fFrom").value + 1, to: +$("fTo").value + 1, level: $("fLevel").value, dept: $("fDept").value,
           group: $("fGroup").value, type: $("fType").value, supp: $("fSupp").value };
}

function aggregate(f) {
  const n = D.v.length;
  const A = { n: 0, v: 0, dirN: 0, dirV: 0, natN: 0, natV: 0, sme: 0, vals: [],
              month: new Array(12).fill(0), monthN: new Array(12).fill(0),
              group: new Array(D.groups.length).fill(0), groupN: new Array(D.groups.length).fill(0),
              type: new Array(D.types.length).fill(0), dept: new Array(D.depts.length).fill(0),
              band: new Array(BANDS.length).fill(0), ent: new Map() };
  const dirIdx = D.groups.indexOf("Direct contracting");
  for (let i = 0; i < n; i++) {
    const m = D.mo[i];
    if (m < f.from || m > f.to) continue;
    const e = D.entities[D.en[i]];
    if (f.level !== "all" && e[1] !== +f.level) continue;
    if (f.dept !== "all" && e[2] !== +f.dept) continue;
    if (f.group !== "all" && D.mg[i] !== +f.group) continue;
    if (f.type !== "all" && D.ct[i] !== +f.type) continue;
    if (f.supp !== "all" && D.st[i] !== +f.supp) continue;
    const v = D.v[i];
    A.n++; A.v += v; A.vals.push(v);
    if (D.mg[i] === dirIdx) { A.dirN++; A.dirV += v; }
    if (D.st[i] === 0) { A.natN++; A.natV += v; }
    A.sme += D.sm[i];
    A.month[m - 1] += v; A.monthN[m - 1]++;
    A.group[D.mg[i]] += v; A.groupN[D.mg[i]]++;
    A.type[D.ct[i]]++;
    A.dept[e[2]] += v;
    for (let b = 0; b < BANDS.length; b++) { if (v >= BANDS[b][1] && v < BANDS[b][2]) { A.band[b]++; break; } }
    let r = A.ent.get(D.en[i]);
    if (!r) { r = { n: 0, v: 0, dir: 0 }; A.ent.set(D.en[i], r); }
    r.n++; r.v += v; if (D.mg[i] === dirIdx) r.dir++;
  }
  return A;
}

function median(arr) {
  if (!arr.length) return 0;
  const s = Float64Array.from(arr).sort();
  const h = Math.floor(s.length / 2);
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}

function baseLayout(extra) {
  const ink2 = css("--ink-2"), grid = css("--grid"), axis = css("--axis");
  return Object.assign({
    margin: { l: 10, r: 16, t: 8, b: 36 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "system-ui, -apple-system, Segoe UI, Inter, sans-serif", size: 12, color: ink2 },
    hoverlabel: { bgcolor: css("--surface"), bordercolor: axis, font: { color: css("--ink"), size: 13 } },
    xaxis: { gridcolor: grid, linecolor: axis, zeroline: false, automargin: true, fixedrange: true },
    yaxis: { gridcolor: grid, linecolor: axis, zeroline: false, automargin: true, fixedrange: true },
    showlegend: false, bargap: 0.35,
  }, extra);
}
const CONFIG = { displayModeBar: false, responsive: true };

function hbar(id, labels, values, hover, colors, xTitle) {
  // Categories are positions (0..n-1) with text labels, so two truncated names that look the
  // same never merge into one bar.
  const pos = labels.map((_, i) => i);
  const trace = { type: "bar", orientation: "h", y: pos, x: values, customdata: hover,
                  marker: { color: colors, cornerradius: 4 }, hovertemplate: "%{customdata}<extra></extra>",
                  text: values.map((v) => v.toLocaleString("en-US", { maximumFractionDigits: 1 })),
                  textposition: "outside", textfont: { color: css("--ink-2"), size: 11 }, cliponaxis: false };
  Plotly.react(id, [trace], baseLayout({
    yaxis: { autorange: "reversed", automargin: true, gridcolor: "rgba(0,0,0,0)", linecolor: css("--axis"), fixedrange: true,
             tickmode: "array", tickvals: pos, ticktext: labels, zeroline: false },
    xaxis: { title: { text: xTitle, font: { size: 11 } }, gridcolor: css("--grid"), zeroline: false, fixedrange: true,
             range: [0, Math.max(1e-9, ...values) * (window.innerWidth < 760 ? 1.35 : 1.18)],
             automargin: true, nticks: window.innerWidth < 760 ? 4 : 6, tickangle: 0 },
    margin: { l: 10, r: 40, t: 4, b: 40 },
  }), CONFIG);
}

function render() {
  const f = current();
  if (f.from > f.to) { $("status").textContent = "The 'From' month is after the 'To' month: no contracts match."; }
  else { $("status").textContent = ""; }
  const A = aggregate(f);
  const narrow = window.innerWidth < 760;
  const s1 = css("--series-1"), s2 = css("--series-2");

  $("kN").textContent = fmtInt(A.n);
  $("kNs").textContent = A.n ? "signed " + MONTHS[f.from - 1] + "–" + MONTHS[f.to - 1] + " 2025" : "no contracts match";
  $("kV").textContent = fmtCOP(A.v);
  $("kVs").textContent = "average " + fmtCOP(A.n ? A.v / A.n : 0);
  $("kMed").textContent = fmtCOP(median(A.vals));
  $("kDir").textContent = pct(A.dirN, A.n);
  $("kDirs").textContent = "of contracts · " + pct(A.dirV, A.v) + " of value";
  $("kNat").textContent = pct(A.natN, A.n);
  $("kNats").textContent = "of contracts · " + pct(A.natV, A.v) + " of value";
  $("kSme").textContent = pct(A.sme, A.n);

  Plotly.react("cMonth", [{
    type: "bar", x: MONTHS, y: A.month.map((v) => v / 1e9), marker: { color: s1, cornerradius: 4 },
    customdata: A.monthN.map((n, i) => [fmtInt(n), fmtBn(A.month[i])]),
    hovertemplate: "<b>COP %{customdata[1]} bn</b><br>%{x} 2025 · %{customdata[0]} contracts<extra></extra>",
  }], baseLayout({ yaxis: { title: { text: "COP bn", font: { size: 11 } }, gridcolor: css("--grid"),
                     zeroline: false, fixedrange: true, automargin: true, rangemode: "tozero" },
                   xaxis: { linecolor: css("--axis"), fixedrange: true, tickangle: 0, tickfont: { size: narrow ? 10 : 12 } } }), CONFIG);

  const gIdx = D.groups.map((_, i) => i).filter((i) => A.groupN[i] > 0).sort((a, b) => A.group[b] - A.group[a]);
  hbar("cGroup", gIdx.map((i) => D.groups[i]), gIdx.map((i) => A.group[i] / 1e9),
       gIdx.map((i) => `<b>COP ${fmtBn(A.group[i])} bn</b> (${pct(A.group[i], A.v)} of value)<br>${D.groups[i]} · ${fmtInt(A.groupN[i])} contracts`),
       gIdx.map((i) => D.groups[i] === "Direct contracting" ? s2 : s1), "COP bn");

  const ents = [...A.ent.entries()].sort((a, b) => b[1].v - a[1].v);
  const topE = ents.slice(0, 10);
  hbar("cEnt", topE.map(([k]) => truncate(D.entities[k][0], narrow ? 24 : 36)), topE.map(([, r]) => r.v / 1e9),
       topE.map(([k, r]) => `<b>COP ${fmtBn(r.v)} bn</b><br>${D.entities[k][0]}<br>${fmtInt(r.n)} contracts`),
       s1, "COP bn");

  const tIdx = D.types.map((_, i) => i).filter((i) => A.type[i] > 0).sort((a, b) => A.type[b] - A.type[a]).slice(0, 8);
  hbar("cType", tIdx.map((i) => truncate(D.types[i], narrow ? 26 : 40)), tIdx.map((i) => A.type[i]),
       tIdx.map((i) => `<b>${fmtInt(A.type[i])} contracts</b> (${pct(A.type[i], A.n)})<br>${D.types[i]}`), s1, "Contracts");

  const dIdx = D.depts.map((_, i) => i).filter((i) => A.dept[i] > 0).sort((a, b) => A.dept[b] - A.dept[a]).slice(0, 10);
  hbar("cDept", dIdx.map((i) => truncate(D.depts[i], narrow ? 22 : 30)), dIdx.map((i) => A.dept[i] / 1e9),
       dIdx.map((i) => `<b>COP ${fmtBn(A.dept[i])} bn</b> (${pct(A.dept[i], A.v)} of value)<br>${D.depts[i]}`), s1, "COP bn");

  Plotly.react("cSize", [{
    type: "bar", x: BANDS.map((b) => b[0]), y: A.band, marker: { color: s1, cornerradius: 4 },
    customdata: A.band.map((c) => pct(c, A.n)),
    hovertemplate: "<b>%{y:,} contracts</b> (%{customdata})<br>%{x}<extra></extra>",
  }], baseLayout({ yaxis: { title: { text: "Contracts", font: { size: 11 } }, gridcolor: css("--grid"),
                     zeroline: false, fixedrange: true, automargin: true, rangemode: "tozero" },
                   xaxis: { linecolor: css("--axis"), fixedrange: true, tickfont: { size: narrow ? 10 : 12 } } }), CONFIG);

  const tbody = document.querySelector("#tEnt tbody");
  tbody.replaceChildren();
  ents.slice(0, 15).forEach(([k, r]) => {
    const tr = document.createElement("tr");
    const e = D.entities[k];
    [[e[0], ""], [D.levels[e[1]], "hide-sm"], [D.depts[e[2]], "hide-sm"], [fmtInt(r.n), "n"], [fmtBn(r.v), "n"],
     [pct(r.dir, r.n), "n"]].forEach(([text, cls]) => {
      const td = document.createElement("td"); td.textContent = text; if (cls) td.className = cls; tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  if (!ents.length) {
    const tr = document.createElement("tr"); const td = document.createElement("td");
    td.colSpan = 6; td.textContent = "No contracts match the filters."; tr.appendChild(td); tbody.appendChild(tr);
  }
}

["fFrom", "fTo", "fLevel", "fDept", "fGroup", "fType", "fSupp"].forEach((id) => $(id).addEventListener("change", render));
$("reset").addEventListener("click", () => {
  $("fFrom").value = "0"; $("fTo").value = "11";
  ["fLevel", "fDept", "fGroup", "fType", "fSupp"].forEach((id) => { $(id).value = "all"; });
  render();
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
let resizeTimer;
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 200); });
render();
</script>
</body>
</html>
"""


def build() -> Path:
    data = compact_data()
    html = TEMPLATE.replace("__PLOTLY__", PLOTLY).replace("__DATA__", json.dumps(data, separators=(",", ":"),
                                                                                  ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT, DOCS)
    print(f"  dashboard: {OUT.stat().st_size / 1e6:.1f} MB -> {OUT.relative_to(PROJECT)} and docs/procurement-dashboard/")
    return OUT


if __name__ == "__main__":
    build()
