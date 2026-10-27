"""Download the raw supplier records and the business-registry records used for the cleaning project.

1. SECOP II - Proveedores Registrados (Colombia Compra Eficiente, datos.gov.co qmzu-gj57, CC BY-SA 4.0):
   suppliers located in Boyacá whose company type is an organisation (companies, non-profits,
   cooperatives, consortia...). Natural persons and sole proprietors are excluded at the source,
   and the columns about legal representatives (names, IDs, phones, emails) are never requested.
2. RUES - Personas Naturales, Jurídicas y ESAL (Confecámaras, datos.gov.co c82u-588k, CC BY-SA 4.0):
   the chamber-of-commerce record of the same tax IDs (NIT), used to cross-check status and dates.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
from fetch_utils import socrata_json  # noqa: E402

RAW = PROJECT / "data" / "raw"
SUPPLIERS = RAW / "secop2_suppliers_boyaca.csv"
REGISTRY = RAW / "rues_registry_matches.csv"

ORG_TYPES = [
    "Sociedad por acciones simplificada", "Entidades sin ánimo de lucro", "Asociaciones", "Fundaciones",
    "Sociedad Anónima Abierta colombiana", "Sociedad de Responsabilidad Limitada colombiana", "Patrimonios Autónomos",
    "Junta de Acción Comunal.", "Corporaciones", "Consorcio", "Cooperativas", "Sociedad Anónima Cerrada Colombiana",
    "Unión Temporal", "Otras Entidades públicas", "Sociedad en Comandita Simple colombiana", "Entidades Religiosas",
    "Sociedad en Comandita por Acciones colombiana", "Institución de Educación Superior", "Federaciones",
    "Entidad Estatal de acuerdo con la definición del Decreto 1082 de 2015", "Sucursal de Sociedad Extranjera",
    "Persona Jurídica Extranjera sin domicilio en Colombia", "Organismos Multilaterales de Crédito",
    "Estructura Plural",
]
SUPPLIER_COLS = ["codigo", "nombre", "nit", "tipo_empresa", "es_entidad", "es_grupo", "espyme", "tama_o_entidad",
                 "esta_activa", "fecha_creacion", "telefono", "fax", "correo", "sitio_web", "direccion", "municipio",
                 "departamento", "pais", "codigo_categoria_principal", "descripcion_categoria_principal"]
REGISTRY_COLS = ["camara_comercio", "matricula", "razon_social", "sigla", "nit", "digito_verificacion",
                 "fecha_matricula", "fecha_renovacion", "ultimo_ano_renovado", "fecha_cancelacion",
                 "organizacion_juridica", "categoria_matricula", "estado_matricula", "cod_ciiu_act_econ_pri",
                 "fecha_actualizacion"]


def suppliers() -> pd.DataFrame:
    if SUPPLIERS.exists():
        return pd.read_csv(SUPPLIERS, dtype=str, keep_default_na=False)
    types = ", ".join("'" + t.replace("'", "''") + "'" for t in ORG_TYPES)
    rows = socrata_json("qmzu-gj57", {
        "$select": ",".join(SUPPLIER_COLS),
        "$where": f"departamento = 'Boyacá' AND tipo_empresa in ({types})",
        "$order": "codigo", "$limit": 50000})
    df = pd.DataFrame(rows).reindex(columns=SUPPLIER_COLS).fillna("")
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(SUPPLIERS, index=False)
    return df


def registry(nits: list[str]) -> pd.DataFrame:
    """Look up the chamber-of-commerce records of the given NITs, 150 per request."""
    if REGISTRY.exists():
        return pd.read_csv(REGISTRY, dtype=str, keep_default_na=False)
    out = []
    nits = sorted(set(n for n in nits if n.isdigit()))
    for i in range(0, len(nits), 150):
        chunk = ",".join(f"'{n}'" for n in nits[i:i + 150])
        out += socrata_json("c82u-588k", {"$select": ",".join(REGISTRY_COLS), "$where": f"nit in ({chunk})",
                                          "$limit": 50000})
    df = pd.DataFrame(out).reindex(columns=REGISTRY_COLS).fillna("")
    df.to_csv(REGISTRY, index=False)
    return df


if __name__ == "__main__":
    s = suppliers()
    print(s.shape)
