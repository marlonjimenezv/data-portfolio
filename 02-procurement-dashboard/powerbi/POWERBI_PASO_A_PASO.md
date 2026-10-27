# Power BI paso a paso (guía para Marlon)

Objetivo: armar en Power BI Desktop el mismo tablero del dashboard HTML, con el modelo en estrella ya preparado,
y sacar las capturas para Upwork. Tiempo estimado: **30 a 60 minutos**.

Todo lo que necesitas está en esta carpeta (`02-procurement-dashboard/powerbi/`):

| Archivo | Para qué sirve |
|---|---|
| `data/fact_contracts.csv` | Tabla de hechos: un contrato por fila (60.902 filas). |
| `data/dim_entity.csv` | Entidades contratantes (nombre, NIT, departamento, nivel). |
| `data/dim_date.csv` | Calendario 2025 (365 días). |
| `data/dim_modality.csv` | Modalidad de contratación, su grupo en inglés y las banderas `is_direct` / `is_competitive`. |
| `data/dim_contract_type.csv` | Tipo de contrato (español e inglés). |
| `data/dim_status.csv` | Estado del contrato. |
| `dax_measures.md` | Las 12 medidas DAX, listas para copiar y pegar. |
| `portfolio_theme.json` | Tema de colores del portafolio (mismos colores del dashboard HTML). |
| `VALORES_ESPERADOS.md` | Los números que deben salir, para comprobar que todo quedó bien. |

> Los nombres de menús están en la versión en español de Power BI Desktop. Si tu Power BI está en inglés, el
> nombre en inglés va entre paréntesis.

---

## Parte 1. Preparar el archivo (5 min)

1. Instala Power BI Desktop si no lo tienes (gratis, en Microsoft Store o en powerbi.microsoft.com). Funciona solo en Windows.
2. Descarga la carpeta `powerbi/` del repositorio (o copia la carpeta si ya tienes el repo clonado).
3. Abre Power BI Desktop → **Archivo → Nuevo** (File → New).
4. Guarda de una vez: **Archivo → Guardar como** → nombre `education_procurement_2025.pbix` dentro de la carpeta `powerbi/`.
5. Aplica el tema: **Vista → Temas → Examinar temas** (View → Themes → Browse for themes) → elige `portfolio_theme.json`.

## Parte 2. Cargar las seis tablas (10 min)

6. **Inicio → Obtener datos → Texto/CSV** (Home → Get data → Text/CSV) → elige `data/fact_contracts.csv`.
7. En la ventana de vista previa revisa dos cosas:
   - **Origen de archivo:** `65001: Unicode (UTF-8)` (si no, las tildes se ven mal: "EducaciÃ³n").
   - **Delimitador:** `Coma`.
8. Haz clic en **Transformar datos** (Transform data) para revisar los tipos en Power Query:
   - `date_signed`, `date_start`, `date_end` → tipo **Fecha** (icono de calendario).
   - `contract_value`, `paid_value`, `invoiced_value`, `duration_days` y todas las columnas `_key` → **Número entero**.
   - `is_sme`, `is_consortium`, `zero_value_flag` → **Número entero** (0 o 1).
   - Si una fecha aparece como texto: clic derecho en la columna → **Cambiar tipo → Usar configuración regional** →
     Tipo de datos: Fecha, Configuración regional: **Inglés (Estados Unidos)**. Los CSV usan fechas `AAAA-MM-DD`.
9. **Inicio → Cerrar y aplicar** (Close & Apply).
10. Repite los pasos 6 a 9 con las otras cinco tablas: `dim_entity`, `dim_date`, `dim_modality`, `dim_contract_type`,
    `dim_status`. En `dim_date`, la columna `date` debe quedar como **Fecha**.
11. Revisa el panel **Datos** (Data) a la derecha: deben aparecer las 6 tablas.

## Parte 3. Modelo en estrella (8 min)

12. Ve a la **Vista de modelo** (Model view, el tercer icono de la barra izquierda).
13. Power BI suele crear relaciones solas. Abre **Inicio → Administrar relaciones** (Manage relationships) y deja
    exactamente estas cinco (si falta alguna, **Nueva**; si sobra alguna, **Eliminar**):

    | Desde (muchos) | Hacia (uno) | Cardinalidad | Dirección del filtro |
    |---|---|---|---|
    | `fact_contracts[entity_key]` | `dim_entity[entity_key]` | Varios a uno (*:1) | Única |
    | `fact_contracts[modality_key]` | `dim_modality[modality_key]` | Varios a uno | Única |
    | `fact_contracts[contract_type_key]` | `dim_contract_type[contract_type_key]` | Varios a uno | Única |
    | `fact_contracts[status_key]` | `dim_status[status_key]` | Varios a uno | Única |
    | `fact_contracts[date_signed]` | `dim_date[date]` | Varios a uno | Única |

    Si Power BI creó una relación entre `date_start` o `date_end` y `dim_date`, elimínala: solo la fecha de firma se relaciona.
14. Ordena la vista: arrastra `fact_contracts` al centro y las cinco dimensiones alrededor. Así se ve la "estrella"
    (esta imagen sirve como captura para Upwork).
15. Marca el calendario: selecciona la tabla `dim_date` → **Herramientas de tablas → Marcar como tabla de fechas**
    (Table tools → Mark as date table) → columna `date` → Aceptar.
16. Ordena los meses: en la vista de datos (Data view) selecciona la columna `dim_date[month_name]` →
    **Herramientas de columnas → Ordenar por columna → month_num** (Column tools → Sort by column).
    Sin esto, los meses salen en orden alfabético (Apr, Aug, Dec…).
17. Oculta las columnas técnicas para que el panel quede limpio: en la vista de modelo, clic derecho → **Ocultar en la
    vista de informe** sobre todas las columnas `_key` de `fact_contracts` y de las dimensiones.

## Parte 4. Medidas DAX (10 min)

18. Crea una tabla para las medidas: **Inicio → Especificar datos** (Enter data) → nombre `_Measures` → **Cargar**.
19. Selecciona `_Measures` en el panel Datos → **Herramientas de tablas → Nueva medida** (New measure).
20. Copia la primera medida de `dax_measures.md` (por ejemplo `Total Contracts = COUNTROWS ( fact_contracts )`),
    pégala en la barra de fórmulas y presiona **Enter**.
21. Repite con las 12 medidas, en el mismo orden del archivo.
22. Da formato a cada medida (selecciónala → **Herramientas de medición**):
    - Porcentajes (`... %`): **Porcentaje**, 1 decimal.
    - `Total Value`, `Average Contract Value`, `Median Contract Value`, `Value YTD`: **Número entero** con separador de miles.
23. Borra la columna `Column1` que Power BI creó en `_Measures` (clic derecho → Eliminar). La tabla queda con un icono de calculadora.
24. **Comprueba los números:** pon una **Tarjeta** (Card) con `Total Contracts` en un lienzo vacío. Debe decir
    exactamente lo que dice `VALORES_ESPERADOS.md` (60.902 contratos para la extracción incluida). Haz lo mismo con
    `Total Value` y `Direct Contracting % (contracts)`. Si no coincide, revisa los tipos de la Parte 2 y las relaciones de la Parte 3.

## Parte 5. La página del tablero (15 min)

25. Cambia el nombre de la página a `Overview` (doble clic en la pestaña de abajo).
26. Título: **Insertar → Cuadro de texto** → "Colombia public procurement: education sector, 2025". Debajo, en letra pequeña:
    "Source: SECOP II (Colombia Compra Eficiente), datos.gov.co, CC BY-SA 4.0 · Sample project built with public data".
27. Fila de **segmentaciones** (Slicer) arriba, todas del mismo tamaño:
    - `dim_date[month_name]` (estilo **Lista desplegable**, selección múltiple),
    - `dim_entity[level]`,
    - `dim_entity[department]` (activa **Buscar** en el formato),
    - `dim_modality[modality_group]`,
    - `dim_contract_type[contract_type]`.
28. Fila de **tarjetas** (Card) debajo de las segmentaciones: `Total Contracts`, `Total Value`, `Median Contract Value`,
    `Direct Contracting % (contracts)`, `Individuals % (contracts)`.
29. **Gráfico de columnas agrupadas** (Clustered column chart): Eje X = `dim_date[month_name]`, Eje Y = `Total Value`.
    Título: "Contract value by month signed".
30. **Gráfico de barras agrupadas** (Clustered bar chart): Eje Y = `dim_modality[modality_group]`, Eje X = `Total Value`.
    Ordénalo de mayor a menor (… → Ordenar eje → Total Value). En **Formato → Barras → Colores**, activa
    "Mostrar todo" y pon `Direct contracting` en naranja (#EB6834); las demás quedan azules.
31. **Gráfico de barras agrupadas** para el top 10 de entidades: Eje Y = `dim_entity[entity_name]`, Eje X = `Total Value`.
    En el panel **Filtros → Filtros de este objeto visual** arrastra `Entity Rank by Value` y pon "es menor o igual que 10".
32. **Tabla** (Table) abajo: `dim_entity[entity_name]`, `dim_entity[level]`, `dim_entity[department]`, `Total Contracts`,
    `Total Value`, `Direct Contracting % (contracts)`. Ordénala por `Total Value` descendente.
33. Alinea todo: selecciona varios objetos → **Formato → Alinear**. Deja márgenes iguales. Guarda (Ctrl + S).
34. Prueba los filtros: en `department` elige **Antioquia**. La tarjeta `Total Contracts` debe mostrar el número que
    aparece en `VALORES_ESPERADOS.md` para Antioquia. Quita el filtro al terminar.

## Parte 6. Capturas para Upwork (5–10 min)

35. Pantalla completa del lienzo: **Vista → Ajustar a la página** y oculta los paneles (flechas `>` a la derecha).
36. Toma estas capturas con **Windows + Shift + S** (recorte rectangular) y guárdalas en `02-procurement-dashboard/upwork/`:
    - `pbi-1.png`: la página `Overview` completa sin filtros.
    - `pbi-2.png`: la misma página filtrada (por ejemplo Antioquia + Direct contracting).
    - `pbi-3.png`: la **vista de modelo** con la estrella ordenada (paso 14).
    - `pbi-4.png`: la vista de datos o el editor de una medida DAX (por ejemplo `Entity Rank by Value`).
37. Pon cada captura en formato 4:3 con el mismo estilo del portafolio. Desde la carpeta `data-portfolio/` ejecuta:
    ```bash
    .venv/bin/python common/frame_shot.py 02-procurement-dashboard/upwork/pbi-1.png 02-procurement-dashboard/upwork/shot-6.png "Power BI version of the dashboard"
    ```
    (En Windows: `.venv\Scripts\python common\frame_shot.py ...`). Repite con las otras capturas si quieres usarlas.
38. El paquete de Upwork ya tiene 5 capturas (el máximo que usamos en este portafolio). Si agregas las de Power BI,
    reemplaza `shot-4.png` o `shot-5.png` y actualiza `upwork/captions.txt` (máximo 300 caracteres por pie de foto).
39. Guarda el `.pbix` (pesa unos pocos MB). Puedes subirlo al repo en `powerbi/` para que el cliente lo descargue.

## Problemas comunes

| Problema | Solución |
|---|---|
| Las tildes se ven como `Ã³` | Repite la carga con Origen de archivo `65001: Unicode (UTF-8)`. |
| Los meses salen en orden alfabético | Paso 16: ordenar `month_name` por `month_num`. |
| `Value YTD` o `Value MoM %` salen en blanco | Falta marcar `dim_date` como tabla de fechas (paso 15) o la relación con `date_signed`. |
| Los totales no cambian al filtrar por departamento | La relación `fact_contracts[entity_key]` → `dim_entity[entity_key]` no existe o está inactiva (línea punteada). |
| `Total Value` sale con decimales raros o enorme | `contract_value` quedó como texto o decimal: cámbialo a Número entero en Power Query. |
