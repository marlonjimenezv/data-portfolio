"""Turn a percent-format Python script into an executed Jupyter notebook and export it.

'# %%' starts a code cell and '# %% [markdown]' a markdown cell (the jupytext 'percent' convention), so the
analysis can be reviewed and diffed as plain Python while still producing a real notebook.
"""
from __future__ import annotations

import re
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

import brand


def py_to_notebook(src: Path) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for block in re.split(r"^# %%", src.read_text(encoding="utf-8"), flags=re.M)[1:]:
        header, _, body = block.partition("\n")
        if header.strip() == "[markdown]":
            text = "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#")
                             for line in body.strip().splitlines())
            nb.cells.append(nbformat.v4.new_markdown_cell(text))
        else:
            nb.cells.append(nbformat.v4.new_code_cell(body.strip()))
    return nb


def execute(nb: nbformat.NotebookNode, workdir: Path, timeout: int = 900) -> nbformat.NotebookNode:
    NotebookClient(nb, timeout=timeout, kernel_name="python3",
                   resources={"metadata": {"path": str(workdir)}}).execute()
    errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
    if errors:
        raise SystemExit(f"Notebook error: {errors[0]['ename']}: {errors[0]['evalue']}")
    return nb


def report_css(font_rel_path: str) -> str:
    return f"""<style>
    @font-face {{ font-family: Inter; src: url('{font_rel_path}'); }}
    body, .jp-Notebook, .jp-RenderedHTMLCommon {{ font-family: Inter, system-ui, sans-serif !important;
      color: {brand.INK}; }}
    .jp-Notebook {{ max-width: 980px; margin: 0 auto; padding: 24px 16px 60px; }}
    .jp-RenderedHTMLCommon h1 {{ color: {brand.BRAND}; font-size: 30px; line-height: 1.2; }}
    .jp-RenderedHTMLCommon h2 {{ color: {brand.BRAND}; border-bottom: 1px solid {brand.GRID}; padding-bottom: 4px;
      margin-top: 34px; }}
    .jp-RenderedHTMLCommon h3 {{ color: {brand.BRAND_2}; }}
    .jp-RenderedHTMLCommon table {{ font-size: 13px; border-collapse: collapse; margin: 8px 0 4px; }}
    .jp-RenderedHTMLCommon th {{ background: {brand.BRAND}; color: #fff; padding: 5px 9px; }}
    .jp-RenderedHTMLCommon td {{ padding: 4px 9px; border-bottom: 1px solid {brand.GRID}; white-space: nowrap; }}
    .jp-RenderedImage img {{ max-width: 100%; height: auto; }}
    .jp-OutputPrompt, .jp-InputPrompt {{ display: none; }}
    @media (max-width: 700px) {{ .jp-RenderedHTMLCommon table {{ display: block; overflow-x: auto; }} }}
    </style>"""


def export_html(nb: nbformat.NotebookNode, out: Path, title: str, with_code: bool, font_rel_path: str) -> Path:
    exp = HTMLExporter(template_name="lab", exclude_input=not with_code, exclude_input_prompt=True,
                       exclude_output_prompt=True)
    body, _ = exp.from_notebook_node(nb)
    body = body.replace("</head>", report_css(font_rel_path) + "\n<meta name='viewport' content='width=device-width, "
                        "initial-scale=1'>\n</head>").replace("<title>Notebook</title>", f"<title>{title}</title>")
    out.write_text(body, encoding="utf-8")
    return out
