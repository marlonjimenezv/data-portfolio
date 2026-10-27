"""Clean, deduplicate and validate the Boyacá supplier file (SECOP II) and cross-check it with RUES.

Every rule writes one line to the cleaning log (rows or cells affected) and one line per problem
to the issues table. Personal data is never published: records whose ID is a personal ID number
are excluded, e-mails that look personal are masked and mobile numbers are partly hidden.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT.parent / "common"))
import download  # noqa: E402
import rules as R  # noqa: E402
from fetch_utils import socrata_json  # noqa: E402

CLEAN = PROJECT / "data" / "clean"
DIVIPOLA = PROJECT / "data" / "raw" / "divipola_boyaca.csv"

ACTIVE_STATUS = {"ACTIVA": "Active", "MATRÍCULA NUEVA, CONSTITUCIÓN POR TRASLADO": "Active (moved from another chamber)"}
OTHER_STATUS = {"CANCELADA": "Cancelled", "MATRÍCULA CANCELADA POR TRASLADO DE DOMICILIO": "Moved to another chamber",
                "NO MATRICULADO": "Not registered"}


@dataclass
class Log:
    steps: list = field(default_factory=list)
    issues: list = field(default_factory=list)

    def step(self, rule: str, detail: str, affected: int, unit: str = "rows", rows_after: int | None = None):
        self.steps.append({"step": len(self.steps) + 1, "rule": rule, "detail": detail, "affected": affected,
                           "unit": unit, "rows_after": rows_after})

    def issue(self, rec: pd.Series, fld: str, problem: str, action: str, shown_value: str = ""):
        self.issues.append({"supplier_code": rec["supplier_code"], "name": rec.get("name", ""), "field": fld,
                            "issue": problem, "action": action, "value_shown": shown_value})


def divipola() -> pd.DataFrame:
    if not DIVIPOLA.exists():
        rows = socrata_json("gdxc-w37w", {"$where": "cod_dpto='15'", "$limit": 500})
        pd.DataFrame(rows)[["cod_mpio", "nom_mpio"]].to_csv(DIVIPOLA, index=False)
    d = pd.read_csv(DIVIPOLA, dtype=str)
    d["key"] = d["nom_mpio"].map(lambda s: R.strip_accents(s).upper())
    return d


def best_registry_record(reg: pd.DataFrame) -> pd.DataFrame:
    """One registry row per NIT: active first, then the most recent renewal."""
    reg = reg.copy()
    reg["rank"] = reg["estado_matricula"].map(lambda s: 0 if s in ACTIVE_STATUS else 1)
    reg["renewal"] = reg["fecha_renovacion"].map(R.parse_date)
    reg = reg.sort_values(["nit", "rank", "renewal"], ascending=[True, True, False], na_position="last")
    return reg.drop_duplicates("nit")


def completeness(rec: pd.Series) -> int:
    return sum(bool(rec[c]) for c in ("telefono", "correo", "sitio_web", "direccion", "municipio"))


def usable_before(raw: pd.DataFrame, mun_keys: set) -> dict:
    """Share of raw records whose value can be used as-is, without any cleaning (strict)."""
    n = len(raw)
    def pct(mask) -> float:
        return round(100 * mask.sum() / n, 1)
    nit_ok = raw["nit"].str.fullmatch(r"[89]\d{8}") & ~raw["nit"].duplicated(keep=False)
    phone = raw["telefono"].str.fullmatch(r"3\d{9}|60\d{8}")
    email = raw["correo"].map(lambda e: bool(R.EMAIL_RE.match(e)) and e == e.strip().lower()
                              and e.split("@")[-1] not in R.DOMAIN_TYPOS)
    web = raw["sitio_web"].map(lambda w: w.startswith("http") and R.parse_website(w)["website_status"] == "ok")
    addr = raw["direccion"].map(lambda a: a == R.standard_address(a) and R.address_status(a) == "ok")
    mun = pd.Series(False, index=raw.index)  # the raw file has no municipality code
    name = raw["nombre"].map(lambda s: s == R.standard_name(s))
    return {"NIT (valid, unique)": pct(nit_ok), "Name (standard spelling)": pct(name),
            "Phone (10-digit, dialable)": pct(phone), "E-mail (valid, lower case)": pct(email),
            "Website (valid URL)": pct(web), "Address (standard format)": pct(addr),
            "Municipality (official DANE code)": pct(mun), "Registry status (RUES)": 0.0}


def run(as_of: date | None = None) -> dict:
    raw = download.suppliers()
    as_of = as_of or pd.Timestamp(download.SUPPLIERS.stat().st_mtime, unit="s").date()
    mun = divipola()
    mun_map = dict(zip(mun["key"], zip(mun["cod_mpio"], mun["nom_mpio"])))
    log = Log()
    log.step("Load raw file", "SECOP II registered suppliers in Boyacá, organisation company types", len(raw),
             rows_after=len(raw))
    before = usable_before(raw, set(mun_map))

    d = raw.rename(columns={"codigo": "supplier_code", "nit": "nit_raw"}).copy()
    d["name"] = d["nombre"]

    # 1. Text: trim spaces, placeholders -> empty
    changed = placeholders = 0
    for c in ("nombre", "telefono", "fax", "correo", "sitio_web", "direccion", "municipio", "tama_o_entidad",
              "descripcion_categoria_principal", "codigo_categoria_principal"):
        new = d[c].map(R.clean_text)
        placeholders += int(((new == "") & (d[c] != "")).sum())
        changed += int(((new != d[c]) & (new != "")).sum())
        d[c] = new
    log.step("Trim spaces and blank out placeholders", f"{placeholders:,} placeholder cells ('No Provisto', "
             f"'No Definido'...) set to empty; {changed:,} cells had extra spaces", placeholders + changed, "cells",
             len(d))

    # 2. NIT
    nit = d["nit_raw"].map(R.parse_nit).apply(pd.Series)
    d = pd.concat([d, nit], axis=1)
    n_dv = int((d["nit_status"] == "ok (check digit removed)").sum())
    log.step("Split NIT and check digit", "10-digit values were NIT + check digit; check digit verified with the "
             "DIAN modulo-11 rule", n_dv, "rows", len(d))
    for _, rec in d[d["nit_status"].isin(["check digit does not match", "invalid length", "missing"])].iterrows():
        log.issue(rec, "nit", rec["nit_status"], "kept, flagged for review", rec["nit_digits"])

    # 3. Privacy: personal ID numbers
    personal = d["nit_status"].str.startswith("personal ID")
    d = d[~personal].copy()
    log.step("Exclude personal ID numbers", "Records whose ID is a personal ID (cédula), not an organisation NIT: "
             "excluded so no personal data is published", int(personal.sum()), "rows", len(d))

    # 4. Registry cross-check (RUES)
    reg_all = download.registry(d.loc[d["nit"] != "", "nit"].tolist())
    natural = set(reg_all.loc[reg_all["categoria_matricula"] == "PERSONA NATURAL", "nit"])
    in_natural = d["nit"].isin(natural) & ~d["nit"].isin(
        set(reg_all.loc[reg_all["categoria_matricula"] != "PERSONA NATURAL", "nit"]))
    d = d[~in_natural].copy()
    log.step("Check: NITs registered to a natural person", "Safety check: RUES says the NIT belongs to a person "
             "(none found after the previous rule)" if not in_natural.any() else "RUES says the NIT belongs to a person",
             int(in_natural.sum()),
             "rows", len(d))
    reg = best_registry_record(reg_all[reg_all["categoria_matricula"] != "PERSONA NATURAL"])
    reg = reg.drop(columns=["rank", "renewal"]).astype(str)
    d = d.merge(reg.add_prefix("rues_"), left_on="nit", right_on="rues_nit", how="left")
    d[[c for c in d.columns if c.startswith("rues_")]] = d[[c for c in d.columns if c.startswith("rues_")]].fillna("")

    # 4b. Privacy: organisation records whose name field holds a person's name
    person = d["nombre"].map(R.looks_like_person_name)
    fixable = person & (d["rues_razon_social"] != "")
    d.loc[fixable, "nombre"] = d.loc[fixable, "rues_razon_social"]
    d = d[~(person & ~fixable)].copy()
    log.step("Privacy: names that look like a person's name", f"{int(fixable.sum())} replaced with the legal name from "
             f"RUES; {int((person & ~fixable).sum())} without a registry record excluded (heuristic: 2-4 plain words, "
             "no acronym and no word that organisations use)", int(person.sum()), "rows", len(d))

    # 5. Duplicates: same NIT -> keep the most complete, most recent record
    d["score"] = d.apply(completeness, axis=1)
    d["created"] = d["fecha_creacion"].map(R.parse_date)
    d["has_nit"] = d["nit_status"].str.startswith("ok") | (d["nit_status"] == "check digit does not match")
    dup_groups = d[d["has_nit"] & d["nit"].duplicated(keep=False)]
    d = d.sort_values(["score", "created"], ascending=[False, False], na_position="last")
    keep = ~(d["has_nit"] & d["nit"].duplicated(keep="first"))
    removed = d[~keep]
    d = d[keep].sort_values("supplier_code").copy()
    log.step("Remove duplicate NITs", f"{dup_groups['nit'].nunique()} NITs appeared more than once; kept the record "
             "with the most contact fields, then the most recent", len(removed), "rows", len(d))

    # 6. Names
    d["name"] = d["nombre"].map(R.standard_name)
    log.step("Standardise names", "Upper case, single spaces, one spelling per legal form (SAS / S.A.S -> S.A.S.)",
             int((d["name"] != d["nombre"]).sum()), "rows", len(d))
    d["form_registry"] = d["rues_organizacion_juridica"].map(R.legal_form_from_registry)
    d["form_name"] = d["name"].map(R.legal_form_from_name)
    d["legal_form"] = d["form_registry"].where(d["form_registry"] != "", d["form_name"])
    d["form_secop"] = d["tipo_empresa"].map(R.TYPE_TO_FORM).fillna("")
    mism = (d["legal_form"] != "") & (d["form_secop"] != "") & (d["legal_form"] != d["form_secop"])
    for _, rec in d[mism].iterrows():
        src = "registry" if rec["form_registry"] else "name"
        log.issue(rec, "company_type", f"SECOP type '{rec['tipo_empresa']}' but the {src} says {rec['legal_form']}",
                  "legal_form column set from the " + src, rec["tipo_empresa"])
    log.step("Check legal form vs company type", "SECOP company type disagrees with the legal form in RUES (or in "
             "the name suffix when RUES has no record); legal_form column holds the corrected value",
             int(mism.sum()), "rows (corrected)", len(d))
    key_dups = d[d["name"].map(R.name_key).duplicated(keep=False) & (d["name"].map(R.name_key) != "")]
    for _, rec in key_dups.iterrows():
        log.issue(rec, "name", "same name as another record with a different NIT", "kept, flagged (possible duplicate)",
                  rec["name"])
    log.step("Find possible duplicates by name", "Same name (ignoring accents, punctuation and legal form) but "
             "different NIT", len(key_dups), "rows (flagged)", len(d))

    # 7. Phones (fax used as a backup phone when the main phone is missing)
    ph = d["telefono"].map(R.parse_phone).apply(pd.Series)
    fx = d["fax"].map(R.parse_phone).apply(pd.Series)
    use_fax = (ph["phone_e164"] == "") & (fx["phone_e164"] != "")
    ph.loc[use_fax] = fx.loc[use_fax].values
    d = pd.concat([d, ph], axis=1)
    log.step("Standardise phone numbers", "To +57 format; old 7-digit landlines get the 608 area prefix (2021 "
             f"numbering plan); fax used when the phone was missing ({int(use_fax.sum())})",
             int(d["phone_e164"].ne("").sum()), "rows", len(d))
    for _, rec in d[d["phone_status"].str.startswith("invalid")].iterrows():
        log.issue(rec, "phone", rec["phone_status"], "blanked")

    # 8. E-mails (+ privacy mask)
    em = d["correo"].map(R.parse_email).apply(pd.Series)
    d = pd.concat([d, em], axis=1)
    typos = int((d["email_status"] == "ok (domain typo fixed)").sum())
    lower = int(((d["email"] != "") & (d["email"] != d["correo"].str.strip())).sum())
    log.step("Standardise e-mails", f"Lower case, spaces removed; {typos} domain typos fixed (gmail.con -> gmail.com)",
             lower, "rows", len(d))
    for _, rec in d[d["email_status"] == "invalid format"].iterrows():
        log.issue(rec, "email", "invalid format", "blanked")
    d["email_is_org"] = [R.is_organisational_email(e, n) if e else False for e, n in zip(d["email"], d["name"])]
    d["email_public"] = [e if (not e or org) else R.mask_email(e) for e, org in zip(d["email"], d["email_is_org"])]
    masked = int(((d["email"] != "") & ~d["email_is_org"]).sum())
    log.step("Privacy: mask personal-looking e-mails", "Mailbox is not a role (info@, ventas@...) and does not contain "
             "the organisation's name, so it may belong to a person", masked, "rows", len(d))

    # 9. Phones: privacy mask for mobiles
    d["phone_public"] = [R.mask_mobile(p) if t == "mobile" else R.format_phone(p)
                         for p, t in zip(d["phone_e164"], d["phone_type"])]
    n_mob = int((d["phone_type"] == "mobile").sum())
    log.step("Privacy: partly hide mobile numbers", "Mobiles may be personal: only the operator prefix and the last "
             "2 digits are published (landlines are shown in full)", n_mob, "rows", len(d))

    # 10. Websites
    wb = d["sitio_web"].map(R.parse_website).apply(pd.Series)
    d = pd.concat([d, wb], axis=1)
    log.step("Standardise websites", "Lower case, https:// added, trailing slash removed; e-mails typed as websites "
             "and invalid domains blanked", int((d["website"] != "").sum()), "rows", len(d))
    for _, rec in d[d["website_status"].str.startswith("invalid")].iterrows():
        log.issue(rec, "website", rec["website_status"], "blanked", rec["sitio_web"])

    # 11. Addresses
    d["address"] = d["direccion"].map(R.standard_address)
    d["address_status"] = d["address"].map(R.address_status)
    log.step("Standardise addresses", "Colombian abbreviations (CALLE/CLL -> CL, CARRERA/CRA -> KR, No./N° -> #)",
             int((d["address"] != d["direccion"].str.upper()).sum()), "rows", len(d))
    for _, rec in d[d["address_status"].str.startswith("incomplete")].iterrows():
        log.issue(rec, "address", "no street type or number", "kept, flagged", rec["address"])

    # 12. Municipality -> official DANE code
    aliases = {"GUICAN": "GUICAN DE LA SIERRA"}
    keys = d["municipio"].map(lambda m: R.strip_accents(m).upper()).replace(aliases)
    d["dane_code"] = keys.map(lambda k: mun_map.get(k, ("", ""))[0])
    d["municipality"] = keys.map(lambda k: mun_map.get(k, ("", ""))[1].title()).str.replace(" De ", " de ")
    bad_mun = d["dane_code"] == ""
    for _, rec in d[bad_mun].iterrows():
        log.issue(rec, "municipality", "municipality missing" if not rec["municipio"] else "municipality not in the "
                  "official DANE list for Boyacá", "kept, flagged", rec["municipio"])
    log.step("Add DANE municipality code", "Matched to DIVIPOLA (DANE), ignoring accents and case; "
             "'Güicán' -> official name 'Güicán de la Sierra'",
             int((~bad_mun).sum()), "rows", len(d))

    # 13. Dates from two sources in different formats
    d["secop_registration_date"] = d["fecha_creacion"].map(R.parse_date)
    d["registration_date"] = d["rues_fecha_matricula"].map(R.parse_date)
    d["last_renewal_date"] = d["rues_fecha_renovacion"].map(R.parse_date)
    d["registry_updated"] = d["rues_fecha_actualizacion"].map(R.parse_date)
    for col in ("secop_registration_date", "registration_date", "last_renewal_date"):
        st = d[col].map(lambda x: R.date_status(x, as_of))
        for _, rec in d[(st != "ok") & (st != "missing or unreadable")].iterrows():
            log.issue(rec, col, st[_] if _ in st.index else "invalid date", "kept, flagged", str(rec[col]))
    log.step("Parse dates from both sources", "SECOP: 2024-03-25T22:44:28.000 · RUES: 19971015 and "
             "2026/06/18 11:31:29.553 -> ISO dates (YYYY-MM-DD)",
             int(d["secop_registration_date"].notna().sum() + d["registration_date"].notna().sum()), "cells", len(d))

    # 14. Registry status and renewal
    d["registry_status"] = d["rues_estado_matricula"].map(lambda s: ACTIVE_STATUS.get(s) or OTHER_STATUS.get(s) or
                                                          ("Not found in RUES" if not s else s.title()))
    d["last_renewal_year"] = pd.to_numeric(d["rues_ultimo_ano_renovado"], errors="coerce").astype("Int64")
    active = d["registry_status"].str.startswith("Active")
    late = active & (d["last_renewal_year"] < as_of.year)
    for _, rec in d[late].iterrows():
        log.issue(rec, "registry", f"registration not renewed for {as_of.year} (last renewal "
                  f"{rec['last_renewal_year']})", "flagged")
    for _, rec in d[d["registry_status"].isin(["Cancelled", "Moved to another chamber"])].iterrows():
        log.issue(rec, "registry", f"registry status: {rec['registry_status']}", "flagged")
    found = d["registry_status"] != "Not found in RUES"
    log.step("Cross-check with the business registry (RUES)", f"{int(found.sum()):,} found; status, registration "
             f"date and last renewal added; {int(late.sum())} active records not renewed for {as_of.year}",
             int(found.sum()), "rows", len(d))
    d["name_matches_registry"] = ["" if not rn else ("yes" if R.names_match(a, rn) else "no")
                                  for a, rn in zip(d["name"], d["rues_razon_social"])]
    for _, rec in d[d["name_matches_registry"] == "no"].iterrows():
        log.issue(rec, "name", "trade name differs from the legal name in RUES", "kept; legal name added",
                  rec["rues_razon_social"])
    liquid = d["rues_razon_social"].str.contains("EN LIQUIDACI", case=False)
    for _, rec in d[liquid].iterrows():
        log.issue(rec, "registry", "company is in liquidation (RUES name)", "flagged", rec["rues_razon_social"])
    log.step("Compare names with RUES", "Ignoring spaces, punctuation, legal form and small typos; legal name kept "
             f"in name_in_registry; {int(liquid.sum())} companies are 'en liquidación'",
             int((d["name_matches_registry"] == "no").sum()), "rows (flagged)", len(d))

    # Output table
    d["nit_formatted"] = [f"{n[:3]}.{n[3:6]}.{n[6:]}-{R.nit_check_digit(n)}" if len(n) == 9 else ""
                          for n in d["nit"]]
    issues = pd.DataFrame(log.issues)
    counts = issues.groupby("supplier_code").size() if len(issues) else pd.Series(dtype=int)
    lists = issues.groupby("supplier_code")["issue"].apply(lambda s: "; ".join(sorted(set(s)))) if len(issues) else {}
    d["issues_count"] = d["supplier_code"].map(counts).fillna(0).astype(int)
    d["issues"] = d["supplier_code"].map(lists).fillna("")
    clean = pd.DataFrame({
        "supplier_code": d["supplier_code"], "name": d["name"], "name_in_registry": d["rues_razon_social"],
        "nit": d["nit"], "nit_formatted": d["nit_formatted"], "nit_status": d["nit_status"],
        "company_type": d["tipo_empresa"], "legal_form": d["legal_form"],
        "sme": d["espyme"].map({"SI": "Yes", "NO": "No"}),
        "size": d["tama_o_entidad"].replace({"Pequeña": "Small", "Mediana": "Medium", "Micro": "Micro",
                                             "Grande": "Large", "No definido": ""}),
        "municipality": d["municipality"], "dane_code": d["dane_code"], "address": d["address"],
        "phone": d["phone_public"], "phone_type": d["phone_type"], "email": d["email_public"],
        "email_type": d["email_domain_type"], "website": d["website"], "website_note": d["website_status"],
        "secop_registration_date": d["secop_registration_date"], "registry_status": d["registry_status"],
        "registry_chamber": d["rues_camara_comercio"].str.title(), "registration_date": d["registration_date"],
        "last_renewal_year": d["last_renewal_year"], "ciiu_code": d["rues_cod_ciiu_act_econ_pri"],
        "issues_count": d["issues_count"], "issues": d["issues"],
    }).reset_index(drop=True)
    for c in ("phone", "email", "website", "address", "name_in_registry", "registry_chamber", "ciiu_code"):
        clean[c] = clean[c].fillna("")
    first = ["supplier_code", "name", "nit_formatted", "legal_form", "municipality", "dane_code", "address", "phone",
             "email", "website", "registry_status", "last_renewal_year", "issues_count", "issues"]
    clean = clean[first + [c for c in clean.columns if c not in first]]

    after = {
        "NIT (valid, unique)": clean["nit_status"].str.startswith("ok").mean(),
        "Name (standard spelling)": 1.0,
        "Phone (10-digit, dialable)": (d["phone_e164"] != "").mean(),
        "E-mail (valid, lower case)": (d["email"] != "").mean(),
        "Website (valid URL)": (d["website_status"] == "ok").mean(),
        "Address (standard format)": d["address_status"].str.startswith("ok").mean(),
        "Municipality (official DANE code)": (d["dane_code"] != "").mean(),
        "Registry status (RUES)": found.mean(),
    }
    quality = pd.DataFrame({"field": list(before), "usable_before_pct": list(before.values()),
                            "usable_after_pct": [round(100 * after[k], 1) for k in before]})
    steps = pd.DataFrame(log.steps)

    CLEAN.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CLEAN / "suppliers_clean.csv", index=False)
    steps.to_csv(CLEAN / "cleaning_log.csv", index=False)
    issues.to_csv(CLEAN / "issues.csv", index=False)
    quality.to_csv(CLEAN / "quality_before_after.csv", index=False)
    status_counts = clean["registry_status"].value_counts().rename_axis("registry_status").reset_index(name="suppliers")
    return {"raw": raw, "clean": clean, "steps": steps, "issues": issues, "quality": quality,
            "status": status_counts, "as_of": as_of, "removed_duplicates": removed}


if __name__ == "__main__":
    out = run()
    print(out["steps"][["step", "rule", "affected", "unit", "rows_after"]].to_string(index=False))
    print(out["quality"].to_string(index=False))
    print(out["status"].to_string(index=False))
    print(out["issues"]["issue"].value_counts().head(20).to_string())
