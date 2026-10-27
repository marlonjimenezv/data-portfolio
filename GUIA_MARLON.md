# Guía del portafolio (para Marlon)

Esta guía es para ti, no para los clientes. Explica cada proyecto en español sencillo: qué problema resuelve, qué
cliente lo pediría, qué datos usa y por qué, cada etapa del trabajo, los resultados con números, y cinco preguntas
que te pueden hacer en una entrevista con una buena respuesta. Todos los números salen de los datos y del código
del proyecto; si vuelves a correr un proyecto con datos más recientes (SECOP, RUES, sitios web), algunos cambian.

**Antes de una entrevista:** abre el README del proyecto y el entregable principal (Excel, PDF o dashboard) y
recorre los pasos. Si te preguntan por algo que no hiciste, dilo con calma y explica cómo lo harías.

**Qué decir siempre:** "Es un proyecto de muestra con datos públicos; los resultados son hallazgos reales de esos
datos, no de un cliente". En el proyecto 8 las facturas son sintéticas y lo dicen en cada archivo.

---

## Cómo está organizado el repositorio

- Cada carpeta `01-…` a `08-…` tiene: `README.md` (en inglés, para clientes), `run.py` (reconstruye todo con un
  comando), `src/` (código), `data/` (datos limpios; los crudos grandes se descargan), `output/` (entregables) y
  `upwork/` (portada, capturas y textos).
- `common/` tiene el estilo compartido: colores, fuente Inter, generador de portadas y capturas, y las herramientas
  de LibreOffice (recalcular Excel) y del navegador (capturas y pruebas).
- `build_site.py` construye la página web (`docs/`) y el archivo `PORTAFOLIO_UPWORK.md`.
- `run_all.py` corre los ocho proyectos y luego construye la página.

Para correr un proyecto: `python3 -m venv .venv`, `.venv/bin/pip install -r requirements.txt` y luego
`.venv/bin/python 0X-…/run.py`. Necesitas LibreOffice, Node.js con Playwright, poppler y pandoc instalados.

---

## 01 · Excel KPI Report (ventas de e-commerce)

**Problema y cliente.** Una tienda en línea o un distribuidor tiene sus ventas en un archivo enorme y quiere un
reporte en Excel que se actualice solo: ventas, pedidos, ticket promedio, clientes que repiten, productos y países
top, y la tendencia mensual. Es de los trabajos más pedidos en Upwork ("Excel dashboard", "KPI report").

**Datos y por qué.** Online Retail II (UCI, CC BY 4.0): todas las transacciones de una tienda británica de
regalos, dic-2009 a dic-2011, 1.067.371 líneas. Es real, grande, tiene devoluciones, clientes sin ID y códigos raros:
todo lo que trae un archivo de cliente de verdad.

**Etapas.**
1. Descarga desde UCI (`run.py`).
2. Limpieza con pandas y registro de cada regla: duplicados exactos (−34.335), 24 meses completos (−25.247),
   códigos que no son productos como envío o ajustes (−5.724), precios ≤ 0 (−5.911), códigos en mayúscula (173
   códigos como `85123a`, porque las búsquedas de Excel no distinguen mayúsculas). Quedan 996.154 líneas.
3. Tablas para Excel: 45.968 facturas, productos, clientes.
4. Libro de Excel con XlsxWriter: hoja KPIs con selector de periodo (celdas amarillas `StartMonth` y `EndMonth`),
   fórmulas `SUMIFS`, `COUNTIFS`, `INDEX/MATCH`, `LARGE`, `MINIFS`, `EDATE`; gráficos nativos; formato condicional;
   hoja Notes con definiciones, fuente, licencia y limitaciones.
5. Verificación: LibreOffice recalcula el archivo (44.001 fórmulas, 0 errores) y pandas recalcula los KPIs, que
   deben coincidir. El archivo guarda los valores calculados para que se vean incluso en Vista protegida.
6. Bonus SQL: la misma data en SQLite y 13 consultas (LAG, NTILE, SUM OVER, self-join).

**Resultados (dic-2010 a nov-2011 vs los 12 meses anteriores).** Ventas netas £9.330.919 (+1,9 %), pedidos 18.957
(−4,0 %), ticket promedio £508,14 (+6,8 %), clientes activos 4.293 (+1,3 %), tasa de recompra 63,9 % (−2,5 pp),
devoluciones 3,1 % de las ventas. Hallazgos: menos pedidos pero más grandes; el 10 % de los clientes trae el 60 % de
las ventas; el producto 23166 tuvo 95 % devuelto porque un pedido de 74.215 unidades se canceló 16 minutos después.

**Preguntas de entrevista.**
1. *¿Por qué fórmulas y no una tabla dinámica?* Porque el cliente cambia el periodo en dos celdas y todo se
   recalcula, incluida la comparación con el periodo anterior y los rankings; una tabla dinámica no compara periodos
   móviles tan fácil y se rompe cuando alguien la mueve. Igual, para explorar, una dinámica sobre la hoja Data sirve.
2. *¿Cómo sabes que no hay errores en las fórmulas?* El script abre el archivo en LibreOffice, recalcula y cuenta
   celdas con error (#REF!, #DIV/0!, #NAME?, #VALUE!): deben ser cero. Además calculo los KPIs con pandas y comparo.
3. *¿Qué hiciste con las devoluciones?* Son líneas con cantidad negativa. Restan en "ventas netas" y aparecen como
   % de devoluciones; se cuentan en el mes en que se procesaron (está en las limitaciones).
4. *¿Por qué pasaste los códigos a mayúscula?* `SUMIFS` no distingue mayúsculas, así que `85123A` y `85123a` se
   sumaban juntos pero aparecían como dos productos. Unificarlos evita duplicar el producto en el top 10.
5. *¿Y si fueran 10 millones de filas?* Excel tiene límite de ~1 millón de filas por hoja. Haría la agregación en
   SQL o Power Query y dejaría en Excel solo la tabla resumida, o usaría el modelo de datos/Power BI.

---

## 02 · Dashboard interactivo + kit de Power BI (contratación pública en educación)

**Problema y cliente.** Una entidad, un periodista de datos, una ONG de transparencia o un consultor quiere ver de
un vistazo cómo se contrata: cuánto, con quién, por qué modalidad, en qué meses. Piden "interactive dashboard" o
"Power BI dashboard".

**Datos y por qué.** SECOP II – Contratos Electrónicos (Colombia Compra Eficiente, datos.gov.co, CC BY-SA 4.0),
filtrado a sector Educación Nacional y contratos firmados en 2025: 60.902 contratos. Es un tema que conoces, es
público y tiene volumen suficiente. Solo se piden columnas de entidades y contratos, nunca nombres ni cédulas.

**Etapas.**
1. Descarga con la API SoQL (`src/download.py`), con filtro en el servidor.
2. Limpieza y modelo estrella (`src/clean.py`): `fact_contracts` + `dim_entity` (495), `dim_date`, `dim_modality`
   (13 modalidades agrupadas en 7, con banderas directa/competitiva), `dim_contract_type`, `dim_status`.
3. Dashboard de un solo archivo HTML con Plotly: 7 filtros, 6 indicadores, 6 gráficos, tabla, modo oscuro,
   funciona en celular.
4. Prueba automática en Chromium (`tests/test_dashboard.js`): aplica combinaciones de filtros en escritorio y
   celular y verifica que los indicadores coincidan con pandas, sin errores ni scroll lateral.
5. Kit de Power BI: CSV del modelo, 12 medidas DAX explicadas, tema de colores y guía paso a paso en español.

**Resultados.** COP 6,97 billones en total; contrato mediano COP 21,4 millones (el promedio es 114,5 millones porque
pocos contratos muy grandes lo jalan). Contratación directa: 86,6 % de los contratos y 56,7 % del valor. Contratos
con personas naturales: 89,6 %. Proveedores pyme: 11,5 %. Enero concentra 14.103 contratos (23 % del año).

**Pendiente tuyo:** armar el `.pbix` en Power BI Desktop siguiendo `02-procurement-dashboard/powerbi/POWERBI_PASO_A_PASO.md`
y comparar con `VALORES_ESPERADOS.md`. Luego tomar 2 o 3 capturas y agregarlas al proyecto en Upwork.

**Preguntas de entrevista.**
1. *¿Por qué muestras la mediana?* Porque el valor de los contratos es muy sesgado: la mediana (21,4 millones)
   describe el contrato típico; el promedio (114,5 millones) está inflado por unos pocos contratos grandes.
2. *¿Qué es un modelo estrella y por qué lo usaste?* Una tabla de hechos (un contrato por fila) rodeada de tablas
   de dimensiones (entidad, fecha, modalidad…). Power BI filtra más rápido y las medidas DAX son más simples.
3. *¿Cómo calculas el % de contratación directa en DAX?* `DIVIDE(CALCULATE([Total Contracts], dim_modality[is_direct] = 1), [Total Contracts])`.
   `CALCULATE` agrega el filtro encima de lo que el usuario eligió en los segmentadores, y `DIVIDE` evita errores
   cuando el filtro deja cero contratos.
4. *¿Cómo garantizas que el dashboard muestra datos correctos?* Una prueba en el navegador aplica filtros y compara
   los indicadores con los que calcula pandas sobre los mismos datos; si no coinciden, el build falla.
5. *¿Qué limitaciones tienen los datos?* Son valores al firmar, no pagos; la clasificación de sector y departamento
   viene de SECOP y puede tener errores; SECOP cambia todos los días, así que la fecha de extracción importa.

---

## 03 · Limpieza, deduplicación y validación (proveedores de Boyacá)

**Problema y cliente.** Una empresa o entidad tiene una base de proveedores o clientes sucia: NIT mal escritos,
duplicados, teléfonos en mil formatos, direcciones sin estándar. Necesita una base confiable y saber qué se cambió.
Piden "data cleaning", "deduplication", "CRM cleanup".

**Datos y por qué.** SECOP II – Proveedores Registrados (organizaciones con dirección en Boyacá) cruzado con el
RUES (Confecámaras) y DIVIPOLA (DANE), todos CC BY-SA 4.0. Es un archivo real y sucio: no se agregó ningún error.

**Etapas.**
1. Descarga por API (`src/download.py`); el RUES se consulta por NIT en lotes de 150.
2. Reglas en `src/rules.py` con pruebas unitarias (`tests/test_rules.py`): espacios y valores de relleno, NIT con
   dígito de verificación DIAN (módulo 11), nombres y forma jurídica, teléfonos al plan de numeración 2021
   (60 + indicativo + 7 dígitos), correos (minúsculas, errores como `gmail.con`), sitios web, direcciones con
   abreviaturas estándar (`KR 7 # 18-56`), códigos DANE de municipio, fechas en tres formatos.
3. Privacidad: se excluyen registros con cédula como NIT (428) o con nombre de persona (64); se enmascaran 821
   correos personales y los celulares solo muestran prefijo y dos últimos dígitos. Un chequeo automático falla si
   algo se escapa.
4. Deduplicación por NIT (103 NIT repetidos): se queda el registro más completo y más reciente.
5. Cruce con RUES: estado, renovación, liquidación.
6. Entregables: Excel (resumen, datos limpios, problemas, registro de limpieza, calidad antes/después, diccionario)
   y un PDF de 2 páginas.

**Resultados.** 4.164 registros → 3.569 organizaciones limpias. NIT válido y único: 73,3 % → 99,2 %. Dirección
estándar: 4,6 % → 91,9 %. Municipio con código DANE: 0 % → 99,2 %. 157 formas jurídicas corregidas con el RUES.
469 matrículas activas no renovadas para 2026; 55 en liquidación; 28 canceladas.

**Preguntas de entrevista.**
1. *¿Cómo validas un NIT?* Con el dígito de verificación de la DIAN: cada dígito se multiplica por un peso fijo
   (3, 7, 13, 17, 19, 23…), se suma, se toma el residuo módulo 11 y si es 0 o 1 ese es el dígito; si no, 11 menos
   el residuo. Si no coincide, el NIT se marca para revisión.
2. *¿Cómo decides cuál duplicado conservar?* Mismo NIT = misma organización. Conservo el registro con más campos
   de contacto llenos y, si empatan, el más reciente. Todo queda en el registro de limpieza.
3. *¿Qué hiciste con los datos personales?* Solo publico organizaciones. Si el "NIT" es una cédula o el nombre es
   de una persona, el registro sale; los correos personales se enmascaran. Hay una verificación automática.
4. *¿Cómo convertiste los teléfonos fijos?* Desde 2021 un fijo se marca 60 + indicativo + número. Un `7444664` en
   Boyacá queda `+57 608 744 4664`. Celulares de 10 dígitos se validan por prefijo.
5. *¿Cómo mides que la base quedó mejor?* Con una tabla de calidad antes/después por campo (% de valores
   utilizables) y el registro de cada regla con cuántas filas o celdas tocó.

---

## 04 · Lista B2B verificada (instituciones de educación superior)

**Problema y cliente.** Un equipo de ventas (software educativo, servicios, eventos) necesita una lista de
organizaciones con datos de contacto y sitio web verificado, con la fuente de cada dato. Piden "lead generation",
"B2B list", "data collection".

**Datos y por qué.** Registro oficial de Instituciones de Educación Superior del Ministerio de Educación
(datos.gov.co, CC BY-SA 4.0), matrícula por institución (MEN) y Wikidata (CC0) para sitios faltantes. Partir de un
registro oficial es más confiable y legal que hacer scraping.

**Etapas.**
1. Descarga del registro (361 sedes, 300 instituciones principales), matrícula agregada con SoQL (semestre 2021-1,
   el último publicado) y una consulta SPARQL a Wikidata.
2. Normalización: teléfonos a +57 con el plan 2021 según departamento; sitios web con errores corregidos
   (`wwww.`, correo escrito como sitio: si el dominio no es institucional se descarta).
3. Verificación respetuosa de cada sitio (`src/verify.py`): User-Agent que se identifica, robots.txt primero,
   pausa de 1,5 s, solo la página de inicio, 6 sitios distintos en paralelo, resultados guardados en caché.
4. Salidas: CSV UTF-8 para Google Sheets, Excel con resumen y método, `METHOD.md`.
5. Chequeos: 150–300 filas, columnas requeridas, sin NIT duplicados, sin correos, coherencia sitio/estado.

**Resultados.** 300 instituciones en 27 departamentos (122 en Bogotá); 292 con teléfono +57; 278 con matrícula
(1,86 millones de estudiantes). 220 sitios respondieron (193 en línea, 14 movidos a otro dominio, 13 en línea pero
bloquean scripts). 61 no se pudieron verificar desde el servidor (conexión rechazada, tiempo agotado, certificado).
Las 80 instituciones con acreditación de alta calidad tienen mediana de 10.407 estudiantes vs 1.296 las demás.

**Ojo:** la verificación corrió desde un servidor fuera de Colombia y muchos sitios colombianos bloquean ese tráfico.
Si quieres mejorar la cifra, corre `python 04-b2b-lead-list/run.py --refresh` desde tu computador en Colombia
(tarda unos minutos por las pausas) y haz commit de los resultados.

**Preguntas de entrevista.**
1. *¿Por qué no hiciste scraping de directorios?* Porque existe un registro oficial con licencia abierta: es más
   completo, legal y fácil de mantener. Solo visité la página de inicio de cada sitio para verificar que responde.
2. *¿Cómo respetas los sitios?* Leo robots.txt antes, me identifico en el User-Agent, pauso entre solicitudes, no
   sigo enlaces ni lleno formularios y guardo en caché para no repetir visitas.
3. *¿Qué significa "Not verified"?* Que desde mi servidor no hubo respuesta; no prueba que el sitio esté caído.
   Por eso lo separo de "Site error" y recomiendo verificarlo desde una conexión local.
4. *¿Cómo usaste Wikidata?* Solo cuando el registro no tenía sitio, y solo si el nombre coincidía con similitud
   ≥ 0,90. Así se agregaron 2 sitios; la columna `website_source` dice de dónde salió cada uno.
5. *¿Cómo lo entregas para Google Sheets?* CSV en UTF-8 (con BOM para que las tildes se vean bien), una fila por
   institución, columnas de fuente, fecha de verificación y estado; se importa con Archivo → Importar.

---

## 05 · Análisis estadístico de encuesta (GSS 2024)

**Problema y cliente.** Un estudiante de maestría, un investigador o una ONG tiene una encuesta y necesita un
análisis serio: descripción de la muestra, tablas cruzadas con chi-cuadrado, intervalos de confianza y una
regresión bien interpretada. Piden "statistical analysis", "SPSS/R help", "thesis data analysis".

**Datos y por qué.** General Social Survey 2024 (NORC, Universidad de Chicago): microdatos oficiales con
codebook, pesos y diseño muestral. Uso libre citando; no se suben al repo, el script los descarga. Pregunta: ¿qué
se asocia con decir "muy feliz"?

**Etapas.**
1. Descarga y lectura (pyreadstat), diccionario de variables con la pregunta textual del codebook.
2. Estimaciones con diseño: peso `WTSSNRPS_AS`, estratos `VSTRAT`, conglomerados `VPSU`, errores por
   linealización de Taylor (como `svy` de Stata o `survey` de R), intervalos en escala logit.
3. Tablas cruzadas y chi-cuadrado con V de Cramér.
4. Regresión logística ponderada con errores agrupados por conglomerado; odds ratios y efectos marginales
   promedio en puntos porcentuales.
5. Supuestos: eventos por predictor, VIF, Cook, calibración, Hosmer-Lemeshow.
6. Informe HTML y PDF sin código, y versión con código.

**Resultados.** 23,0 % "muy feliz" (IC 95 %: 20,8 %–25,3 %). Casados 32 % vs nunca casados 13 %; salud excelente
41 % vs mala 15 %; satisfechos con sus finanzas 39 % vs nada satisfechos 14 %. Chi-cuadrado: estado civil 211,5
(V = 0,16), salud 338,9 (V = 0,21), finanzas 396,2 (V = 0,22), todos p < 0,001. Regresión (n = 3.760, AUC 0,73):
nunca casado −16 pp; salud regular −26 pp (OR 0,20); finanzas no satisfechas −16 pp; asistir a servicios
religiosos +5 pp (p = 0,011); título universitario −5 pp (p = 0,015) controlando salud y finanzas. VIF máximo 2,02.
Hosmer-Lemeshow p = 0,03: se reporta y se discute.

**Preguntas de entrevista.**
1. *¿Por qué usar pesos y diseño muestral?* Porque la GSS no es una muestra aleatoria simple: hay estratos,
   conglomerados y ajustes por no respuesta. Sin pesos los porcentajes están sesgados; sin diseño, los intervalos
   salen demasiado estrechos.
2. *¿Odds ratio o efecto marginal?* El odds ratio (0,20 para salud regular) es difícil de explicar a un cliente.
   El efecto marginal dice "26 puntos porcentuales menos de probabilidad de ser muy feliz", que se entiende.
3. *¿Qué supuestos revisaste?* Suficientes eventos por predictor (54), multicolinealidad (VIF ≤ 2,02), casos
   influyentes (Cook), calibración por deciles y Hosmer-Lemeshow.
4. *Hosmer-Lemeshow dio p = 0,03, ¿el modelo sirve?* Indica algo de falta de ajuste en algunos deciles; con muestras
   grandes la prueba es sensible. La calibración es razonable y el AUC 0,73; lo reporto en vez de esconderlo.
5. *¿Casarse hace feliz a la gente?* No se puede concluir: son datos transversales y autorreportados. Son
   asociaciones; puede haber causalidad inversa o variables omitidas.

---

## 06 · Modelo de predicción de churn (telecomunicaciones)

**Problema y cliente.** Una empresa de suscripción quiere saber qué clientes se van a ir para llamarlos antes.
Piden "churn prediction", "machine learning model", "predictive analytics".

**Datos y por qué.** Iranian Churn Dataset (UCI, CC BY 4.0): 3.150 clientes anónimos de una operadora, con 9 meses
de uso y si se fueron en el mes 12. Es pequeño, limpio de licencia y realista (tiene duplicados).

**Etapas.**
1. Exploración: tasas de churn por grupo.
2. Preparación sin fuga: se eliminan 300 duplicados antes de dividir; test de 25 % estratificado que se usa una
   sola vez; escalado dentro del `Pipeline`; se quita `age` porque repite `age_group`.
3. Modelos: regresión logística, random forest y gradient boosting con validación cruzada de 5 pliegues.
4. Umbral: elegido con predicciones fuera de pliegue del entrenamiento: atrapar al menos 80 % de los que se van con
   la mayor precisión posible → 0,85.
5. Evaluación final en test, matriz de confusión, curva ROC, importancia por permutación.
6. One-pager para gerentes con 5 recomendaciones.

**Resultados.** Gradient boosting fue el mejor (CV ROC-AUC 0,986, PR-AUC 0,947; random forest 0,983/0,916;
logística 0,934/0,749). En test: ROC-AUC 0,984, PR-AUC 0,940. Con umbral 0,85: atrapa 88 de 112 que se van
(recall 79 %), y 88 de 97 marcados realmente se van (precisión 91 %); se marca el 14 % de los clientes.
Se fue el 83 % de quienes se quejaron (vs 10 %), el 48 % de los no activos (vs 6 %), el 35 % del cuartil de menor uso.

**Preguntas de entrevista.**
1. *¿Cómo evitaste la fuga de datos?* Duplicados fuera antes del split, test apartado desde el inicio y usado una
   vez, escalado dentro del pipeline en cada pliegue y umbral elegido sin mirar el test.
2. *¿Por qué reportas PR-AUC además de ROC-AUC?* Porque solo el 15,6 % se va: con clases desbalanceadas el ROC-AUC
   puede verse muy bien aunque el modelo marque muchos falsos positivos; PR-AUC mira justamente a los que se van.
3. *¿Cómo elegiste 0,85 y no 0,50?* Es una decisión de negocio: quise atrapar al menos 80 % de los que se van
   gastando lo menos posible en llamadas inútiles. Sin datos de costos uso esa meta; con costos, optimizaría
   ganancia esperada.
4. *¿Por qué gradient boosting y no solo regresión logística?* Ganó en validación cruzada por bastante en PR-AUC.
   La logística queda como línea base y para explicar direcciones.
5. *¿Qué es la importancia por permutación?* Cuánto cae el ROC-AUC si desordeno una variable. Dice qué usa el
   modelo, no causas; por eso acompaño con tasas de churn por grupo.

---

## 07 · Informe de investigación económica (salario mínimo en Colombia)

**Problema y cliente.** Un centro de pensamiento, un gremio, un medio o una consultora necesita un informe corto,
con datos oficiales y fuentes citadas, sobre un tema de política. Piden "economic research", "policy brief".

**Datos y por qué.** DANE (IPC 2003–2026), OIT-ILOSTAT (salario mínimo en pesos y en dólares PPA), Banco Mundial
(PIB por persona ocupada, productividad), OCDE (salario mínimo como % de la mediana) y los decretos para 2025 y
2026. Todo oficial y descargado por API o archivo, con fecha de acceso.

**Etapas.**
1. `download.py`: descarga y guarda la URL y la fecha de acceso de cada fuente (el enlace del DANE cambia cada mes,
   por eso se lee de su página).
2. `process.py`: verifica que todos los años estén completos; calcula inflación diciembre-diciembre, aumento de cada
   año vs inflación del año anterior, salario real a precios de 2025 (IPC promedio anual) e índices 2004 = 100.
   Detecta quiebres de serie: Ecuador y Uruguay 2024 caen más de 80 % con cambio de fuente y se excluyen.
3. `charts.py`: 4 gráficos. `brief.py`: PDF de 4 páginas con resumen ejecutivo, contexto, hallazgos, implicaciones,
   limitaciones, método y fuentes con fecha de acceso.

**Resultados.** Salario mínimo de COP 358.000 (2004) a COP 1.423.500 (2025): +298 % nominal, precios +172 %, poder
de compra +46 %. Productividad +38 %. El aumento nunca fue menor que la inflación anterior (20 de 21 años por
encima; 2009 igual). Ganancia real promedio 1,5 puntos por año hasta 2021 y 3,6 puntos en 2022–2025. De 2022 a 2025
el salario real subió 13,6 % y la productividad −2,3 %. En 2025 fue el 90,5 % del salario mediano, el más alto de 32
países con datos de la OCDE (mediana 52 %). En dólares PPA (2024) es USD 843 al mes: puesto 8 de 15 en América
Latina, justo la mediana regional. Para 2026 se decretó COP 1.750.905 (+23,0 %), mencionado solo como contexto.

**Preguntas de entrevista.**
1. *¿Por qué deflactas con el IPC promedio anual?* Porque el salario rige todo el año; el promedio del año refleja
   lo que compra durante ese año. Con el IPC de diciembre los resultados cambian uno o dos puntos, no el patrón.
2. *¿Qué es PPA?* Paridad de poder adquisitivo: convierte monedas según lo que compran, no según la tasa de cambio,
   para comparar países.
3. *¿Por qué excluiste Ecuador y Uruguay?* Su valor 2024 en ILOSTAT cae más de 90 % frente a 2023 y cambia de
   fuente: es un quiebre de serie, no un cambio real. El script lo detecta solo y el informe lo explica.
4. *¿Cómo puede ser "alto" y "promedio" a la vez?* Frente a la mediana local es alto (90 %) porque los salarios
   típicos en Colombia son bajos; en poder de compra internacional está en la mitad de la región.
5. *¿Qué no se puede concluir?* El informe es descriptivo: no estima efectos sobre empleo ni informalidad, y la
   productividad del Banco Mundial incluye el sector informal.

---

## 08 · Automatización con IA: facturas PDF a Excel

**Problema y cliente.** Un área contable recibe cientos de facturas en PDF y las digita a mano en Excel. Quiere
automatizarlo con control de errores. Piden "PDF data extraction", "invoice automation", "AI automation".

**Datos y por qué.** Facturas **de ejemplo / sintéticas** generadas por `make_samples.py` (la única excepción
permitida a la regla de datos reales): 4 proveedores inventados con NIT que empiezan en ceros, 4 formatos (inglés
con tabla, factura de venta en español, formato USD, texto plano sin tabla), marca de agua "SAMPLE / SYNTHETIC" en
cada página. Se plantaron 5 problemas: total mal sumado, línea con cantidad × precio errado, vencimiento antes de la
emisión, factura escaneada sin texto y una factura enviada dos veces. Hay una clave de respuestas para medir
precisión.

**Etapas.**
1. Lectura con pdfplumber, quitando los caracteres de la marca de agua (grandes o rotados).
2. Reglas con expresiones regulares por etiqueta, en inglés y español; líneas de tabla o de texto; descripciones que
   ocupan dos renglones se unen.
3. Normalización de montos (`1.234.567` o `1,234.56`) y de 5 formatos de fecha.
4. Validación: campos obligatorios, cantidad × precio, suma de líneas, subtotal + impuesto = total, tasa de
   impuesto, fechas, duplicados.
5. Paso de IA opcional: solo si existe la variable `ANTHROPIC_API_KEY`. Las facturas que las reglas no pudieron
   leer se envían a Claude (el PDF escaneado como documento) y devuelve JSON con estructura fija; pasa por las
   mismas validaciones y queda marcado "AI (Claude)". Nunca "corrige" una factura que está mal en el papel.
6. Excel (Resumen, Facturas, Líneas, Registro de errores, Cómo funciona), CSV, GIF de una corrida real.

**Resultados.** 41 PDF: 36 OK, 5 marcados (uno por cada problema plantado), 0 falsas alarmas. Todos los campos
correctos en 40 de 41 archivos; el que falla es el escaneado, que no tiene texto. 124 líneas extraídas. El paso de
IA no corrió aquí porque no había API key; está probado contra una API falsa local.

**Para activar la IA:** crea una API key en la consola de Anthropic, en la terminal `export ANTHROPIC_API_KEY=...`
y corre `python 08-ai-pdf-to-excel/run.py`. Cuesta centavos por factura; no subas la key a GitHub.

**Preguntas de entrevista.**
1. *¿Por qué reglas y no solo IA?* Las reglas son gratis, rápidas, repetibles y fáciles de auditar para los
   formatos conocidos. La IA se usa solo donde las reglas fallan (escaneados, formatos nuevos), lo que baja costo y
   riesgo.
2. *¿Cómo sabes que lo que extrae la IA está bien?* Pasa por las mismas validaciones (sumas, fechas, duplicados) y
   queda marcado para revisión humana. Además pido salida JSON con esquema fijo, así no inventa campos.
3. *¿Qué pasa con un PDF escaneado?* No tiene capa de texto, así que las reglas no leen nada; se reporta como error
   ("escanee con OCR o use el paso de IA"). Con la IA activa, Claude lee la imagen del PDF.
4. *¿Cómo lo adaptas a un proveedor nuevo?* Normalmente basta agregar una etiqueta nueva en `extract.py`. Mientras
   tanto, sus facturas salen en el registro de errores como "campo no encontrado" o pasan a la IA.
5. *¿Y la privacidad?* Si se activa la IA, el contenido de la factura se envía a la API de Anthropic; solo debe
   hacerse si el cliente lo autoriza. Sin la key, todo corre localmente.

---

## Lo que te queda por hacer

1. **Publicar el repositorio** siguiendo `PUBLICAR.md` (5 comandos y activar GitHub Pages).
2. **Power BI:** armar el `.pbix` con `02-procurement-dashboard/powerbi/POWERBI_PASO_A_PASO.md`.
3. **Upwork:** subir los 8 proyectos con `PORTAFOLIO_UPWORK.md` (textos listos y orden de imágenes).
4. Opcional: repetir la verificación de sitios del proyecto 4 desde Colombia (`--refresh`).
5. Opcional: activar el paso de IA del proyecto 8 con tu API key y volver a correrlo.
