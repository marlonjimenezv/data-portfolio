# Cómo publicar el portafolio (10 minutos)

El portafolio está hoy en la carpeta `data-portfolio/` de la rama `ccr-e258660f-8myl64` del repositorio
`marlonjimenezv/DATOMIA` (tu sitio web). Desde esta sesión no se pueden crear repositorios nuevos en tu cuenta, así
que el último paso lo haces tú. Todos los enlaces del portafolio ya apuntan al repositorio nuevo
`github.com/marlonjimenezv/data-portfolio` y a la página `marlonjimenezv.github.io/data-portfolio`.

**No fusiones esa rama en `main` de DATOMIA**: `main` es tu sitio web y no debe llevar el portafolio.

## 1. Crea el repositorio vacío en GitHub

1. Entra a <https://github.com/new>.
2. *Repository name*: `data-portfolio` (exactamente así; si usas otro nombre, cambia `REPO` en
   `common/config.py` y vuelve a correr los proyectos).
3. Marca **Public**. No agregues README, .gitignore ni licencia (el repositorio debe quedar vacío).
4. Clic en **Create repository**.

## 2. Copia el portafolio y súbelo (5 comandos)

Abre **Git Bash** (Windows) o la **Terminal** (Mac/Linux) en la carpeta donde quieras trabajar y pega, uno por uno:

```bash
git clone --depth 1 --branch ccr-e258660f-8myl64 https://github.com/marlonjimenezv/DATOMIA.git datomia-tmp
cp -r datomia-tmp/data-portfolio ./data-portfolio && rm -rf datomia-tmp
cd data-portfolio && git init -b main && git add . && git commit -m "Data portfolio: eight sample projects built with public data"
git remote add origin https://github.com/marlonjimenezv/data-portfolio.git
git push -u origin main
```

Así el repositorio nuevo empieza con un historial limpio y a tu nombre. Si Git te pide usuario y contraseña, usa
tu usuario de GitHub y un *personal access token* (GitHub → Settings → Developer settings → Personal access tokens)
en lugar de la contraseña, o inicia sesión con GitHub Desktop.

## 3. Activa GitHub Pages

1. En el repositorio nuevo: **Settings → Pages**.
2. *Source*: **Deploy from a branch**. *Branch*: **main**, carpeta **/docs**. Clic en **Save**.
3. Espera 1 o 2 minutos y abre <https://marlonjimenezv.github.io/data-portfolio/>.

## 4. Revisa que todo abra

- Página principal: <https://marlonjimenezv.github.io/data-portfolio/>
- Dashboard (proyecto 2): <https://marlonjimenezv.github.io/data-portfolio/procurement-dashboard/>
- Informe de encuesta (proyecto 5): <https://marlonjimenezv.github.io/data-portfolio/survey-report/>
- Informe de churn (proyecto 6): <https://marlonjimenezv.github.io/data-portfolio/churn-report/>
- README del repositorio: <https://github.com/marlonjimenezv/data-portfolio>

Si una página da error 404, espera unos minutos más (la primera publicación tarda) y revisa que en Pages diga
`main` y `/docs`.

## 5. Después de publicar

- Sube los proyectos a Upwork con `PORTAFOLIO_UPWORK.md`.
- Arma el Power BI con `02-procurement-dashboard/powerbi/POWERBI_PASO_A_PASO.md`.
- Para trabajar en el portafolio desde tu computador: `python3 -m venv .venv`,
  `.venv/bin/pip install -r requirements.txt` y luego `.venv/bin/python run_all.py` (o el `run.py` de un proyecto).
  Haz `git add . && git commit -m "..." && git push` cuando cambies algo.
- Cuando confirmes que todo quedó publicado, puedes borrar la rama `ccr-e258660f-8myl64` del repositorio DATOMIA
  (GitHub → DATOMIA → Branches → icono de basura). Es opcional.
