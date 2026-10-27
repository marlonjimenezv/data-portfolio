"""Clean the SECOP II contracts and build a star schema (CSV) for Power BI and the HTML dashboard.

Output (powerbi/data/):
  fact_contracts.csv     one row per contract
  dim_entity.csv         contracting public entities
  dim_date.csv           calendar 2025 (relates to fact_contracts[date_signed])
  dim_modality.csv       procurement method, with an English group and flags
  dim_contract_type.csv  contract type (Spanish source value + English label)
  dim_status.csv         contract status
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))
import download  # noqa: E402

PBI = PROJECT / "powerbi" / "data"

MODALITY_GROUP = {
    "Contratación directa": "Direct contracting",
    "Contratación Directa (con ofertas)": "Direct contracting",
    "Contratación régimen especial": "Special regime",
    "Contratación régimen especial (con ofertas)": "Special regime",
    "Mínima cuantía": "Minimum-value selection",
    "Selección Abreviada de Menor Cuantía": "Abbreviated selection",
    "Selección abreviada subasta inversa": "Abbreviated selection",
    "Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes": "Abbreviated selection",
    "Licitación pública": "Public tender",
    "Licitación pública Obra Publica": "Public tender",
    "Concurso de méritos abierto": "Merit-based selection",
    "Enajenación de bienes con sobre cerrado": "Sale of public assets",
    "Enajenación de bienes con subasta": "Sale of public assets",
}
COMPETITIVE = {"Minimum-value selection", "Abbreviated selection", "Public tender", "Merit-based selection"}

CONTRACT_TYPE_EN = {
    "Prestación de servicios": "Professional services", "Compraventa": "Purchase of goods",
    "Suministros": "Supplies", "Obra": "Public works", "Otro": "Other",
    "Decreto 092 de 2017": "Agreements with non-profits (Decree 092/2017)",
    "Arrendamiento de inmuebles": "Real-estate lease", "Arrendamiento de muebles": "Equipment lease",
    "Seguros": "Insurance", "Consultoría": "Consulting", "Interventoría": "Works supervision",
    "Comodato": "Free loan of assets", "Servicios financieros": "Financial services",
    "Venta muebles": "Sale of goods", "Negocio fiduciario": "Trust agreement",
    "Concesión": "Concession", "Comisión": "Commission agreement", "No Definido": "Not defined",
}
STATUS_EN = {"En ejecución": "In progress", "Cerrado": "Closed", "Modificado": "Modified",
             "Terminado": "Finished", "Aprobado": "Approved", "Cedido": "Assigned", "Suspendido": "Suspended"}
LEVEL_EN = {"Nacional": "National", "Territorial": "Territorial", "Corporación Autónoma": "Autonomous corporation"}
UNIT_DAYS = {"Dia(s)": 1, "Semana(s)": 7, "Mes(es)": 30, "Año(s)": 365, "Hora(s)": 1 / 24}


def duration_days(text: str) -> float:
    m = re.match(r"\s*(\d+)\s*(\S+)", str(text))
    if not m or m.group(2) not in UNIT_DAYS:
        return np.nan
    return round(int(m.group(1)) * UNIT_DAYS[m.group(2)], 1)


def build() -> dict[str, pd.DataFrame]:
    raw = download.main()
    d = raw.copy()
    log = [("Contracts downloaded (Education sector, signed in 2025)", len(d))]

    d = d.drop_duplicates("id_contrato")
    log.append(("After removing duplicate contract IDs", len(d)))
    for c in ("valor_del_contrato", "valor_pagado", "valor_facturado", "dias_adicionados"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    for c in ("fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato"):
        d[c] = pd.to_datetime(d[c], errors="coerce")
    d["estado_contrato"] = d["estado_contrato"].str.strip().str.capitalize().replace({"En ejecución": "En ejecución"})
    d["departamento"] = d["departamento"].replace({"No Definido": "Not defined"}).str.strip()
    d["ciudad"] = d["ciudad"].replace({"No Definido": "Not defined"}).str.strip()
    d["nombre_entidad"] = d["nombre_entidad"].str.strip().str.replace(r"\s+", " ", regex=True)
    d["supplier_type"] = np.where(d["tipodocproveedor"].eq("NIT"), "Company / organisation",
                                  np.where(d["tipodocproveedor"].isin(["Otro", "No Definido"]), "Other / not defined",
                                           "Natural person"))
    d["duration_days"] = d["duraci_n_del_contrato"].map(duration_days)
    unknown_mod = set(d["modalidad_de_contratacion"]) - set(MODALITY_GROUP)
    unknown_type = set(d["tipo_de_contrato"]) - set(CONTRACT_TYPE_EN)
    if unknown_mod or unknown_type:
        raise SystemExit(f"Unmapped categories: {unknown_mod} {unknown_type}")

    # Dimensions
    ent = (d.groupby("codigo_entidad")
           .agg(entity_name=("nombre_entidad", "first"), entity_nit=("nit_entidad", "first"),
                department=("departamento", "first"), city=("ciudad", "first"), level_es=("orden", "first"),
                branch=("rama", "first"), centralized=("entidad_centralizada", "first"))
           .reset_index().rename(columns={"codigo_entidad": "entity_code"}))
    ent["level"] = ent["level_es"].map(LEVEL_EN)
    ent = ent.sort_values("entity_name").reset_index(drop=True)
    ent.insert(0, "entity_key", np.arange(1, len(ent) + 1))

    mod = pd.DataFrame({"modality_es": sorted(MODALITY_GROUP)})
    mod["modality_group"] = mod["modality_es"].map(MODALITY_GROUP)
    mod["is_direct"] = mod["modality_group"].eq("Direct contracting").astype(int)
    mod["is_competitive"] = mod["modality_group"].isin(COMPETITIVE).astype(int)
    mod.insert(0, "modality_key", np.arange(1, len(mod) + 1))

    ctype = pd.DataFrame({"contract_type_es": sorted(CONTRACT_TYPE_EN)})
    ctype["contract_type"] = ctype["contract_type_es"].map(CONTRACT_TYPE_EN)
    ctype.insert(0, "contract_type_key", np.arange(1, len(ctype) + 1))

    status = pd.DataFrame({"status_es": sorted(STATUS_EN)})
    status["status"] = status["status_es"].map(STATUS_EN)
    status.insert(0, "status_key", np.arange(1, len(status) + 1))

    days = pd.date_range("2025-01-01", "2025-12-31", freq="D")  # all contracts were signed in 2025
    dates = pd.DataFrame({"date": days})
    dates["year"] = dates["date"].dt.year
    dates["quarter"] = "Q" + dates["date"].dt.quarter.astype(str)
    dates["month_num"] = dates["date"].dt.month
    dates["month_name"] = dates["date"].dt.strftime("%b")
    dates["year_month"] = dates["date"].dt.strftime("%Y-%m")
    dates["weekday_num"] = dates["date"].dt.day_of_week + 1
    dates["weekday"] = dates["date"].dt.strftime("%a")

    f = d.merge(ent[["entity_key", "entity_code"]], left_on="codigo_entidad", right_on="entity_code")
    f = f.merge(mod[["modality_key", "modality_es"]], left_on="modalidad_de_contratacion", right_on="modality_es")
    f = f.merge(ctype[["contract_type_key", "contract_type_es"]], left_on="tipo_de_contrato",
                right_on="contract_type_es")
    f = f.merge(status[["status_key", "status_es"]], left_on="estado_contrato", right_on="status_es", how="left")
    if f["status_key"].isna().any():
        raise SystemExit(f"Unmapped status: {set(f.loc[f['status_key'].isna(), 'estado_contrato'])}")
    fact = pd.DataFrame({
        "contract_id": f["id_contrato"],
        "process_id": f["proceso_de_compra"],
        "entity_key": f["entity_key"],
        "date_signed": f["fecha_de_firma"].dt.date,
        "date_start": f["fecha_de_inicio_del_contrato"].dt.date,
        "date_end": f["fecha_de_fin_del_contrato"].dt.date,
        "modality_key": f["modality_key"],
        "contract_type_key": f["contract_type_key"],
        "status_key": f["status_key"].astype(int),
        "supplier_type": f["supplier_type"],
        "is_sme": f["es_pyme"].eq("Si").astype(int),
        "is_consortium": f["es_grupo"].eq("Si").astype(int),
        "resource_origin": f["origen_de_los_recursos"].map({"Recursos Propios": "Own resources",
                                                            "Distribuido": "Distributed"}).fillna("Not defined"),
        "spend_type": f["destino_gasto"].map({"Funcionamiento": "Operating", "Inversión": "Investment"})
                                          .fillna("Not defined"),
        "contract_value": f["valor_del_contrato"].round(0).astype("int64"),
        "paid_value": f["valor_pagado"].round(0).astype("int64"),
        "invoiced_value": f["valor_facturado"].round(0).astype("int64"),
        "duration_days": f["duration_days"].round(0).astype("Int64"),
        "zero_value_flag": f["valor_del_contrato"].eq(0).astype(int),
    }).sort_values(["date_signed", "contract_id"]).reset_index(drop=True)
    log.append(("Contracts in the fact table", len(fact)))
    log.append(("Contracts with value 0 (kept, flagged)", int(fact["zero_value_flag"].sum())))

    PBI.mkdir(parents=True, exist_ok=True)
    out = {"fact_contracts": fact, "dim_entity": ent.drop(columns=["level_es"]), "dim_date": dates,
           "dim_modality": mod, "dim_contract_type": ctype, "dim_status": status}
    for name, t in out.items():
        t.to_csv(PBI / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    extracted = pd.Timestamp(download.RAW.stat().st_mtime, unit="s").strftime("%Y-%m-%d")
    meta = {"source": "SECOP II - Contratos Electronicos (datos.gov.co, dataset jbjy-vk9h)",
            "licence": "CC BY-SA 4.0", "filter": download.WHERE, "extracted_on": extracted,
            "contracts": int(len(fact)), "entities": int(len(ent))}
    (PROJECT / "data" / "clean" / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    out["log"] = pd.DataFrame(log, columns=["step", "rows"])
    out["log"].to_csv(PROJECT / "data" / "clean" / "processing_log.csv", index=False)
    return out


if __name__ == "__main__":
    t = build()
    print(t["log"].to_string(index=False))
    for k, v in t.items():
        print(k, v.shape)
