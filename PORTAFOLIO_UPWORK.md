# Portafolio Upwork: textos listos para copiar

Este archivo se genera con `python build_site.py` a partir de la carpeta `upwork/` de cada proyecto. Si cambias un texto, cámbialo en el `make_upwork.py` del proyecto y vuelve a correr ese proyecto.

**Cómo subir cada proyecto en Upwork:** Perfil → *Portfolio* → *Add a project*. Copia el título, la descripción y las 5 skills. En *Content*, sube primero `cover.png` (Upwork la usa como miniatura) y luego las capturas en el orden indicado; si Upwork te deja escribir un texto debajo de cada imagen, usa el caption. Agrega los links como bloque de link o al final de la descripción. Todos los archivos están en la carpeta `upwork/` del proyecto. En *Your role* puedes poner: *Data analyst (sample project)*.

Orden sugerido para publicar: 02, 01, 03, 08, 06, 05, 04, 07 (los más visuales primero).

## Proyecto 01 · Excel reporting

**Título** (40/50 caracteres)

```text
Excel KPI Dashboard for E-commerce Sales
```

**Descripción** (459/500 caracteres)

```text
An online retailer needs one Excel file to track sales and customer loyalty without manual work. I cleaned 1.07M raw invoice lines (duplicates, cancellations, fees) into a 46K-order Excel table and built a KPI sheet with live SUMIFS, COUNTIFS and INDEX/MATCH formulas, a period selector, native charts and conditional formatting, plus 13 SQL queries. Finding: net revenue grew 1.9% year over year while orders fell 4.0%. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Microsoft Excel
Excel Formula
Data Analysis
Data Visualization
SQL
```

**Imágenes, en este orden** (carpeta `01-excel-kpi-report/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: One-page KPI sheet. Pick the first and last month in the yellow cells and every KPI, ranking and chart updates. All values are live formulas (SUMIFS, COUNTIFS, INDEX/MATCH, LARGE) on Excel tables.
3. `shot-2.png`: Headline KPIs for Dec 2010 - Nov 2011 vs the previous 12 months: net revenue £9,330,919 (+1.9%), 18,957 orders (-4.0%), average order value £508.14 (+6.8%).
4. `shot-3.png`: Top 10 products and the monthly trend. Conditional formatting highlights the selected period, month-over-month changes and year-over-year changes.
5. `shot-4.png`: Notes sheet: definition of each KPI and how it is calculated. The same sheet lists the data source and licence (UCI, CC BY 4.0), the cleaning steps with the rows removed by each rule, and limitations.
6. `shot-5.png`: The same cleaned data loaded into SQLite with 13 business queries. Example: the top 10% of customers bring 60% of revenue, and one storage jar had 95% of its sales returned (one bulk order cancelled).

**Links**

```text
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/01-excel-kpi-report
Excel file: https://github.com/marlonjimenezv/data-portfolio/blob/main/01-excel-kpi-report/output/ecommerce_kpi_report.xlsx
SQL results: https://github.com/marlonjimenezv/data-portfolio/blob/main/01-excel-kpi-report/output/sql_results.md
```

## Proyecto 02 · Dashboards and Power BI

**Título** (44/50 caracteres)

```text
Interactive Procurement Dashboard + Power BI
```

**Descripción** (441/500 caracteres)

```text
Public-sector teams need to see where contracting money goes. I pulled 60,902 education-sector contracts signed in 2025 from Colombia's SECOP II open-data API, modelled them as a star schema and built a one-page interactive dashboard (Python, Plotly.js) with filters, KPI tiles and 6 charts that work on a phone, plus a Power BI kit with 12 DAX measures. Finding: 86.6% of contracts were direct awards. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Dashboard
Data Visualization
Microsoft Power BI
Python
Data Analysis
```

**Imágenes, en este orden** (carpeta `02-procurement-dashboard/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: One-page dashboard on 60,902 contracts worth COP 6.97 trillion. Seven filters (month, entity level, department, method, type, supplier) update every KPI, chart and table.
3. `shot-2.png`: The same page filtered to Antioquia (28,552 contracts, 97.9% direct awards). Numbers are recalculated in the browser, and an automated test checks them against pandas.
4. `shot-3.png`: Responsive layout: on a phone the filters, tiles and charts stack in one column, with no horizontal scrolling.
5. `shot-4.png`: Power BI kit: one fact table (one row per contract) and five dimensions as clean CSV files, with the relationships described step by step.
6. `shot-5.png`: Twelve DAX measures (CALCULATE, DIVIDE, TOTALYTD, DATEADD, RANKX) with explanations, a Spanish build guide and the expected values to check the model.

**Links**

```text
Live dashboard (GitHub Pages): https://marlonjimenezv.github.io/data-portfolio/procurement-dashboard/
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/02-procurement-dashboard
DAX measures: https://github.com/marlonjimenezv/data-portfolio/blob/main/02-procurement-dashboard/powerbi/dax_measures.md
```

## Proyecto 03 · Data cleaning

**Título** (41/50 caracteres)

```text
Data Cleaning, Deduplication & Validation
```

**Descripción** (462/500 caracteres)

```text
Supplier lists get messy: duplicates, placeholders, broken phones, IDs that fail validation. I cleaned 4,164 public supplier records from Colombia's SECOP II with Python: 20 logged rules, tax-ID check digits, phone, e-mail and address standards, DANE codes and a cross-check with the business registry. Result: 3,569 clean organisations, 103 duplicates removed and 469 suppliers whose registration was not renewed for 2026. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Data Cleaning
Data Entry
Python
Microsoft Excel
Data Analysis
```

**Imágenes, en este orden** (carpeta `03-data-cleaning/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: The clean Excel file: 3,569 organisations with a validated tax ID (NIT with check digit), standard name, +57 phone, e-mail, website, address, DANE municipality code and registry status.
3. `shot-2.png`: Issues sheet: one row per problem found (field, issue, action taken), ready to filter and assign. Values that could not be fixed with certainty are flagged, never guessed.
4. `shot-3.png`: Two-page quality report. Example: records with a standard address went from 5% to 92%, and a valid unique tax ID from 73% to 99%.
5. `shot-4.png`: Cross-check with the chamber-of-commerce registry: 469 active registrations not renewed for 2026, 55 companies in liquidation and 28 cancelled registrations.
6. `shot-5.png`: Every rule is logged with the rows or cells it changed, including the privacy rules: personal IDs excluded, personal-looking e-mails masked and mobile numbers partly hidden.

**Links**

```text
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/03-data-cleaning
Quality report (PDF): https://github.com/marlonjimenezv/data-portfolio/blob/main/03-data-cleaning/output/quality_report.pdf
Clean Excel file: https://github.com/marlonjimenezv/data-portfolio/blob/main/03-data-cleaning/output/suppliers_clean.xlsx
```

## Proyecto 04 · Data collection

**Título** (44/50 caracteres)

```text
Verified B2B Lead List from Official Sources
```

**Descripción** (455/500 caracteres)

```text
Sales teams need lead lists they can trust. I built a list of all 300 Colombian higher-education institutions from the Ministry of Education's open registry, enriched it with enrolment figures and Wikidata, normalised phones and checked every website with a respectful Python script (robots.txt, pauses, no crawling). Result: a Google Sheets-ready file with source, check date and status per row; 220 sites answered. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Lead Generation
Data Mining
Web Scraping
Python
Google Sheets
```

**Imágenes, en este orden** (carpeta `04-b2b-lead-list/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: One row per institution: city, phone in +57 format, verified website and status, check date, sector, type, accreditation, enrolment and the source of every value. CSV (UTF-8) for Google Sheets plus Excel.
3. `shot-2.png`: Summary of the website check: 207 online, 13 online but blocking bots, 62 not reachable from the checking server (to re-check locally), by sector, type and department.
4. `shot-3.png`: Method summary: official sources and licences, each step with its count, and how the check respects robots.txt, uses pauses and never crawls beyond the home page.
5. `shot-4.png`: The core of the verification script: a descriptive User-Agent, robots.txt checked before any page request, and a pause between requests to the same site.

**Links**

```text
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/04-b2b-lead-list
Lead list (CSV): https://github.com/marlonjimenezv/data-portfolio/blob/main/04-b2b-lead-list/output/colombia_higher_ed_leads.csv
Method: https://github.com/marlonjimenezv/data-portfolio/blob/main/04-b2b-lead-list/output/METHOD.md
```

## Proyecto 05 · Statistical analysis

**Título** (45/50 caracteres)

```text
Survey Data Analysis: Chi-square & Regression
```

**Descripción** (469/500 caracteres)

```text
Thesis students and researchers need survey results that are correct and easy to read. Using the public 2024 General Social Survey (3,986 US adults), I wrote a report on what goes with happiness: weighted estimates with design-based 95% CIs, cross-tabs with chi-square tests and a logistic regression with assumption checks (Python, statsmodels, Jupyter). Finding: people in fair health are 26 points less likely to be very happy. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Statistical Analysis
Survey Data Analysis
Regression Analysis
Python
Data Analysis
```

**Imágenes, en este orden** (carpeta `05-survey-analysis/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: Every number uses the official survey weight, and the confidence intervals account for the stratified, clustered sample design (68 strata, 137 sampling units), as in Stata svy or R survey.
3. `shot-2.png`: Cross-tabulations with row percentages, chi-square tests of independence and Cramér's V, with the expected-count assumption checked for each table.
4. `shot-3.png`: 23% of US adults say they are very happy (95% CI 20.8% to 25.3%), from 15% of people in poor health to 41% of those in excellent health.
5. `shot-4.png`: Weighted logistic regression with cluster-robust errors: odds ratios, 95% CIs and average marginal effects in percentage points, so the results are easy to explain.
6. `shot-5.png`: Assumptions checked and reported: events per predictor, multicollinearity (VIF), influential cases, calibration and goodness of fit, followed by the results in plain language and the limitations.

**Links**

```text
Report (web page): https://marlonjimenezv.github.io/data-portfolio/survey-report/
Report (PDF): https://github.com/marlonjimenezv/data-portfolio/blob/main/05-survey-analysis/output/report.pdf
Notebook with code: https://github.com/marlonjimenezv/data-portfolio/blob/main/05-survey-analysis/analysis/analysis.ipynb
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/05-survey-analysis
```

## Proyecto 06 · Predictive analytics

**Título** (40/50 caracteres)

```text
Customer Churn Prediction Model (Python)
```

**Descripción** (472/500 caracteres)

```text
Subscription businesses need to know who will leave before they do. On a public telecom dataset I built and compared logistic regression, random forest and gradient boosting with 5-fold cross-validation, removed duplicates before the split to avoid leakage and set the alert threshold on training data. Result on unseen customers: ROC-AUC 0.984; the alert list catches 79% of churners with 91% precision, plus a one-page action plan. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Machine Learning
Predictive Analytics
Python
scikit-learn
Data Science
```

**Imágenes, en este orden** (carpeta `06-churn-prediction/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: Cross-validated comparison on the training set: gradient boosting (PR-AUC 0.95) beats random forest (0.92) and logistic regression (0.75).
3. `shot-2.png`: Evaluated once on 713 unseen customers: ROC-AUC 0.984. At the chosen threshold, 88 of 112 churners are caught and only 9 loyal customers are flagged.
4. `shot-3.png`: Permutation importance shows usage (calls, seconds) and complaints drive the predictions; churn rates by group give the direction of each effect.
5. `shot-4.png`: A one-page summary for managers: model quality in plain words, the main drivers and five actions to test, each tied to a number from the data.
6. `shot-5.png`: Leakage control: 300 duplicate rows removed before the train/test split, scaling inside the pipeline, threshold chosen on out-of-fold training predictions.

**Archivo adicional:** `one-pager.pdf` (súbelo como PDF si Upwork lo permite).

**Links**

```text
Report (web page): https://marlonjimenezv.github.io/data-portfolio/churn-report/
Notebook with code: https://github.com/marlonjimenezv/data-portfolio/blob/main/06-churn-prediction/analysis/churn_model.ipynb
One-pager (PDF): https://github.com/marlonjimenezv/data-portfolio/blob/main/06-churn-prediction/output/churn_one_pager.pdf
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/06-churn-prediction
```

## Proyecto 07 · Economic research

**Título** (46/50 caracteres)

```text
Economic Research Brief: Colombia Minimum Wage
```

**Descripción** (431/500 caracteres)

```text
Policy teams need numbers they can cite. I wrote a 4-page brief on Colombia's minimum wage 2004-2025 from official data (DANE, ILO, World Bank, OECD), downloaded and processed with one Python script. Finding: increases never fell below the previous year's inflation, and since 2022 the real wage rose 14% while productivity was flat; it is 90% of the median wage, the highest of 32 countries. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Economic Research
Economics
Policy Analysis
Data Analysis
Python
```

**Imágenes, en este orden** (carpeta `07-economic-brief/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: Executive summary with four key figures: real minimum wage +46% and GDP per worker +38% since 2004, 90.5% of the median wage, $843 PPP a month.
3. `shot-2.png`: Every year the increase matched or beat the previous year's inflation; from 2022 the margin widened, with +16% in 2023 against 13.1% inflation.
4. `shot-3.png`: Until 2022 the real minimum wage grew more slowly than GDP per worker; since then it rose 13.6% while productivity changed -2.3%.
5. `shot-4.png`: Two comparisons, two pictures: the highest minimum-to-median ratio of 32 countries (OECD), but 8th of 15 in Latin America in purchasing-power dollars (ILO).
6. `shot-5.png`: Plain-language implications for employers, analysts and researchers, and honest limitations, including a series break detected in two countries' data. Sources are listed with access date and licence.

**Archivo adicional:** `research-brief.pdf` (súbelo como PDF si Upwork lo permite).

**Links**

```text
Brief (PDF): https://github.com/marlonjimenezv/data-portfolio/blob/main/07-economic-brief/output/colombia_minimum_wage_brief.pdf
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/07-economic-brief
```

## Proyecto 08 · AI automation

**Título** (40/50 caracteres)

```text
PDF Invoices to Excel with Python and AI
```

**Descripción** (386/500 caracteres)

```text
Teams lose hours typing invoice PDFs into Excel. I built a Python pipeline that reads each PDF (pdfplumber + rules, English and Spanish), checks the math, dates and duplicates, and writes an Excel file with an error log. An optional Claude AI step can read scanned PDFs. On 41 synthetic invoices: 36 clean, 5 flagged, every planted problem caught. Sample project built with public data.
```

**Skills** (copia una por una)

```text
Data Extraction
Python
Automation
Microsoft Excel
AI Development
```

**Imágenes, en este orden** (carpeta `08-ai-pdf-to-excel/upwork/`)

1. `cover.png`: portada (sin caption).
2. `shot-1.png`: A sample invoice (synthetic, watermarked) and the fields extracted from it: supplier, tax ID, number, dates, currency, subtotal, tax, total and line items.
3. `shot-2.png`: The Invoices sheet: one row per PDF with status OK, Check or Review. 36 of 41 sample invoices are ready to load; the rest go to a person.
4. `shot-3.png`: Summary: files processed, problems by type, and accuracy against the synthetic answer key (98% on totals; the one miss is the scanned image).
5. `shot-4.png`: The error log explains each problem in plain words and what to do: wrong total, wrong line amount, due date before issue date, duplicate invoice, scanned image.
6. `shot-5.png`: One command processes the whole folder and prints a status line per file. Four layouts, English and Spanish. The AI step runs only when an API key is set.

**Links**

```text
GitHub project folder: https://github.com/marlonjimenezv/data-portfolio/tree/main/08-ai-pdf-to-excel
Excel output: https://github.com/marlonjimenezv/data-portfolio/blob/main/08-ai-pdf-to-excel/output/invoices_extracted.xlsx
Run animation (GIF): https://github.com/marlonjimenezv/data-portfolio/blob/main/08-ai-pdf-to-excel/output/pipeline_run.gif
```
