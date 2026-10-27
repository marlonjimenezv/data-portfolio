"""Build the verified lead list of Colombian higher-education institutions.

One row per institution (main campus record of the MEN registry). Branch campuses are counted, not listed.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))
import download  # noqa: E402
import verify  # noqa: E402

CLEAN = PROJECT / "data" / "clean"
OUT = PROJECT / "output"

# Colombia's 2021 numbering plan: landline = 60 + old area code + 7 digits, by department
AREA = {"601": ["Bogotá", "Cundinamarca"], "602": ["Cauca", "Nariño", "Valle del Cauca"],
        "604": ["Antioquia", "Córdoba", "Chocó"],
        "605": ["Atlántico", "Bolívar", "Cesar", "La Guajira", "Magdalena", "Sucre", "San Andrés"],
        "606": ["Caldas", "Quindío", "Risaralda"], "607": ["Arauca", "Norte de Santander", "Santander"],
        "608": ["Amazonas", "Boyacá", "Casanare", "Caquetá", "Guaviare", "Guainía", "Huila", "Meta", "Putumayo",
                "Tolima", "Vaupés", "Vichada"]}
DEPT_PREFIX = {d: p for p, ds in AREA.items() for d in ds}

TYPE_EN = {"Universidad": "University", "Institución Universitaria/Escuela Tecnológica":
           "University institution / technological school", "Institución Tecnológica": "Technological institution",
           "Institución Técnica Profesional": "Professional technical institution"}
NATURE_EN = {"Fundación": "Foundation", "Corporación": "Corporation", "Nacional": "National public",
             "Departamental": "Departmental public", "Municipal": "Municipal public"}


def key(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def phone(raw: str, dept: str) -> tuple[str, str]:
    d = re.sub(r"\D", "", (raw or "").split("-")[0].split("/")[0])
    if len(d) == 10 and d[0] == "3":
        return f"+57 {d[:3]} {d[3:6]} {d[6:]}", "ok (mobile)"
    if len(d) == 10 and d.startswith("60"):
        return f"+57 {d[:3]} {d[3:6]} {d[6:]}", "ok"
    if len(d) == 7 and d[0] in "2345678":
        pre = DEPT_PREFIX.get(dept.replace("Bogotá D.C.", "Bogotá"))
        if pre:
            return f"+57 {pre} {d[:3]} {d[3:]}", "ok (area prefix added)"
    return "", "invalid or missing" if d else "missing"


def match_wikidata(names: pd.Series, wd: pd.DataFrame) -> pd.DataFrame:
    wd = wd.assign(k=wd["label"].map(key))
    rows = []
    for idx, name in names.items():
        k = key(name)
        best, score = None, 0.0
        for _, w in wd.iterrows():
            s = 1.0 if w["k"] == k else SequenceMatcher(None, k, w["k"]).ratio()
            if s > score:
                best, score = w, s
        if best is not None and score >= 0.9:
            rows.append({"idx": idx, "wd_web": best["web"], "wd_label": best["label"], "wd_score": round(score, 2),
                         "wd_item": best["item"]})
    return pd.DataFrame(rows).set_index("idx") if rows else pd.DataFrame()


def build(refresh: bool = False) -> dict:
    reg = download.registry()
    enr = download.enrolment()
    wd = download.wikidata()
    log = [("Institutions in the MEN registry (main + branch campuses)", len(reg))]

    reg["code"] = reg["c_digo_instituci_n"].str.strip()
    reg["nit_digits"] = reg["n_mero_identificaci_n"].str.replace(r"\D", "", regex=True)
    main = reg[reg["principal_seccional"] == "Principal"].copy()
    branches = reg[reg["principal_seccional"] == "Seccional"].groupby("nit_digits").size()
    log.append(("Main campus records kept (one per institution)", len(main)))

    main["nit"] = main["nit_digits"].str[:9]
    main["branch_campuses"] = main["nit_digits"].map(branches).fillna(0).astype(int)
    norm = main["p_gina_web"].map(verify.normalise_url)
    main["website_listed"] = norm.str[0]
    main["website_note"] = norm.str[1]
    no_web = main["website_listed"] == ""
    log.append(("Main records with no usable website in the registry", int(no_web.sum())))

    wdm = match_wikidata(main.loc[no_web, "nombre_instituci_n"], wd)
    main["website_source"] = "MEN registry"
    main.loc[~no_web, "website_source"] = "MEN registry"
    main.loc[no_web, "website_source"] = ""
    if len(wdm):
        main.loc[wdm.index, "website_listed"] = wdm["wd_web"].map(lambda u: verify.normalise_url(u)[0])
        main.loc[wdm.index, "website_source"] = "Wikidata (name match " + wdm["wd_score"].astype(str) + ")"
    log.append(("Websites added from Wikidata (exact or near-exact name match)", len(wdm)))
    log.append(("Website values corrected (e-mail typed as website, 'wwww.', missing dot)", int((main["website_note"] != "").sum())))

    res = verify.verify_all(main["website_listed"].tolist(), refresh=refresh)
    main["website_status"] = [verify.classify(u, res.get(u, {})) if u else "No website listed"
                              for u in main["website_listed"]]
    main["http_status"] = [res.get(u, {}).get("http_status", "") if u else "" for u in main["website_listed"]]
    main["final_url"] = [res.get(u, {}).get("final_url", "") if u else "" for u in main["website_listed"]]
    main["page_title"] = [res.get(u, {}).get("title", "") if u else "" for u in main["website_listed"]]
    main["verified_at"] = [res.get(u, {}).get("checked_at", "") if u else "" for u in main["website_listed"]]
    main["robots_txt"] = [res.get(u, {}).get("robots_txt", "") if u else "" for u in main["website_listed"]]
    online = main["website_status"].str.startswith("Online")
    main["website"] = [f if (o and f) else "" for f, o in zip(main["final_url"], online)]
    main["website"] = main["website"].str.replace(r"(https?://[^/]+).*", r"\1", regex=True)

    main["phone"], main["phone_status"] = zip(*[phone(p, d) for p, d in
                                                 zip(main["tel_fono_domicilio"], main["departamento_domicilio"])])
    enr_map = dict(zip(enr["code"], pd.to_numeric(enr["students"], errors="coerce")))
    main["students_enrolled"] = main["code"].map(enr_map).astype("Int64")
    enr_year = enr["year"].iloc[0]

    leads = pd.DataFrame({
        "snies_code": main["code"], "institution": main["nombre_instituci_n"].str.strip(), "nit": main["nit"],
        "sector": main["sector"].map({"Oficial": "Public", "Privado": "Private"}),
        "institution_type": main["car_cter_acad_mico"].map(TYPE_EN),
        "legal_nature": main["naturaleza_jur_dica"].map(NATURE_EN),
        "high_quality_accreditation": main["acreditada_alta_calidad"].map({"SI": "Yes", "NO": "No"}),
        "branch_campuses": main["branch_campuses"], f"students_enrolled_{enr_year}": main["students_enrolled"],
        "department": main["departamento_domicilio"].str.strip(), "city": main["municipio_domicilio"].str.strip(),
        "address": main["direcci_n_domicilio"].str.replace("¿", "", regex=False).str.replace(r"\s+", " ", regex=True)
                                              .str.strip(),
        "phone": main["phone"], "website": main["website"], "website_status": main["website_status"],
        "http_status": main["http_status"], "page_title": main["page_title"], "website_listed": main["website_listed"],
        "website_source": main["website_source"], "website_note": main["website_note"],
        "verified_at": main["verified_at"],
        "source": "MEN - Instituciones de Educación Superior (datos.gov.co n5yy-8nav)",
    }).sort_values(["department", "institution"]).reset_index(drop=True)
    first = ["institution", "department", "city", "phone", "website", "website_status", "verified_at", "sector",
             "institution_type", "high_quality_accreditation", f"students_enrolled_{enr_year}", "branch_campuses"]
    leads = leads[first + [c for c in leads.columns if c not in first]]

    status = leads["website_status"].str.replace(r" \(.*\)$", "", regex=True).value_counts()
    CLEAN.mkdir(parents=True, exist_ok=True)
    log.append(("Institutions with a website that answered (verified online)", int(online.sum())))
    log_df = pd.DataFrame(log, columns=["step", "count"])
    log_df.to_csv(CLEAN / "build_log.csv", index=False)
    return {"leads": leads, "log": log_df, "status": status, "enr_year": enr_year, "raw": reg}
