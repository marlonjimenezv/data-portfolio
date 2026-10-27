# Publicación del portafolio

**Estado: publicado.**

- Repositorio: <https://github.com/marlonjimenezv/data-portfolio>
- Página web: <https://marlonjimenezv.github.io/data-portfolio/>
  (dashboard: `/procurement-dashboard/`, informes: `/survey-report/` y `/churn-report/`)

La página se publica desde la rama **`gh-pages`**, que tiene una copia de la carpeta `docs/`.

## Si cambias algo de la página

Opción sencilla (una sola vez): en GitHub → **Settings → Pages** cambia *Branch* a **`main`** y la carpeta a
**`/docs`**, y guarda. Desde ese momento la página se actualiza sola cada vez que haces `git push` a `main`, y la
rama `gh-pages` ya no hace falta.

Si prefieres dejarla como está, después de cambiar `docs/` copia su contenido a la rama `gh-pages` y haz push de esa
rama.

## Para trabajar en el portafolio desde tu computador

```bash
git clone https://github.com/marlonjimenezv/data-portfolio.git
cd data-portfolio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_all.py        # o el run.py de un solo proyecto
git add . && git commit -m "Describe el cambio" && git push
```
