# Valores esperados en Power BI

Extracción de datos: 2026-10-26 (60,902 contratos, 495 entidades).
Si vuelves a descargar los datos, estos números pueden cambiar porque SECOP II se actualiza todos los días;
este archivo se regenera con `python run.py`.

## Sin filtros

| Medida | Valor esperado |
|---|---|
| Total Contracts | 60,902 |
| Total Value | 6,974,167,324,748 |
| Average Contract Value | 114,514,586 |
| Median Contract Value | 21,363,739 |
| Direct Contracting % (contracts) | 86.6% |
| Direct Contracting % (value) | 56.7% |
| Individuals % (contracts) | 89.6% |
| SME Suppliers % | 11.5% |
| Paid % of Value | 45.5% |
| Value YTD (tarjeta sin filtro de fecha = todo 2025) | 6,974,167,324,748 |

## Con el filtro `dim_entity[department]` = Antioquia

| Medida | Valor esperado |
|---|---|
| Total Contracts | 28,552 |
| Total Value | 1,187,809,928,857 |
| Direct Contracting % (contracts) | 97.9% |

Formato: separador de miles con coma (como en Power BI en inglés). En Power BI en español verás puntos.
