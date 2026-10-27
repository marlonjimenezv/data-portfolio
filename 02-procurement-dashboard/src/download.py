"""Download SECOP II electronic contracts (Colombia Compra Eficiente, datos.gov.co, CC BY-SA 4.0).

Scope: contracts of the Education sector ("Educación Nacional") signed in calendar year 2025.
Only organisation-level and contract-level columns are requested. Names and ID numbers of
people (contractors who are natural persons, legal representatives, supervisors, bank
accounts) are never downloaded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT.parent / "common"))
from fetch_utils import socrata_json  # noqa: E402

DATASET = "jbjy-vk9h"
RAW = PROJECT / "data" / "raw" / "secop2_education_2025.csv"
WHERE = ("sector = 'Educación Nacional' AND fecha_de_firma >= '2025-01-01T00:00:00' "
         "AND fecha_de_firma <= '2025-12-31T23:59:59'")
COLUMNS = [
    "id_contrato", "referencia_del_contrato", "proceso_de_compra",
    "nombre_entidad", "nit_entidad", "codigo_entidad", "departamento", "ciudad", "orden", "sector", "rama",
    "entidad_centralizada", "estado_contrato", "codigo_de_categoria_principal", "tipo_de_contrato",
    "modalidad_de_contratacion", "justificacion_modalidad_de", "fecha_de_firma", "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato", "tipodocproveedor", "es_grupo", "es_pyme", "origen_de_los_recursos",
    "destino_gasto", "valor_del_contrato", "valor_pagado", "valor_facturado", "dias_adicionados",
    "duraci_n_del_contrato", "urlproceso", "ultima_actualizacion",
]
PAGE = 50_000


def main() -> pd.DataFrame:
    if RAW.exists():
        return pd.read_csv(RAW, dtype=str)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    rows, offset = [], 0
    while True:
        page = socrata_json(DATASET, {"$select": ",".join(COLUMNS), "$where": WHERE,
                                      "$order": "id_contrato", "$limit": PAGE, "$offset": offset})
        rows += page
        print(f"  downloaded {len(rows):,} contracts")
        if len(page) < PAGE:
            break
        offset += PAGE
    df = pd.DataFrame(rows)
    df["urlproceso"] = df["urlproceso"].map(lambda u: u.get("url") if isinstance(u, dict) else u)
    df = df.reindex(columns=COLUMNS)
    df.to_csv(RAW, index=False)
    return df


if __name__ == "__main__":
    print(main().shape)
