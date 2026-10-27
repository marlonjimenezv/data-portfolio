"""Animated GIF of a real run: the console output of run.py, line by line, then the resulting Excel sheet."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
GIF = PROJECT / "output" / "pipeline_run.gif"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf"
W, H, PAD, LINE_H, VISIBLE = 1200, 720, 22, 22, 27
BG, FG, DIM = (15, 27, 45), (226, 232, 240), (140, 154, 175)
STATUS = {"OK": (74, 222, 128), "Review": (248, 113, 113), "Check": (251, 191, 36)}


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(MONO, size)
    except OSError:
        return ImageFont.load_default()


def _frame(lines: list[str], title: str) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 34), fill=(30, 41, 59))
    for i, c in enumerate([(239, 68, 68), (234, 179, 8), (34, 197, 94)]):
        d.ellipse((16 + i * 22, 11, 28 + i * 22, 23), fill=c)
    d.text((W // 2, 17), title, font=_font(14), fill=DIM, anchor="mm")
    f = _font(15)
    for i, ln in enumerate(lines[-VISIBLE:]):
        y = 48 + i * LINE_H
        if ln.startswith("  SAMPLE") and len(ln) > 41:
            name, rest = ln[:41], ln[41:]
            d.text((PAD, y), name, font=f, fill=FG)
            status = rest.split()[0] if rest.split() else ""
            d.text((PAD + d.textlength(name, font=f), y), rest[:77], font=f, fill=STATUS.get(status, DIM))
        else:
            d.text((PAD, y), ln[:118], font=f, fill=(147, 197, 253) if ln.startswith("[") else FG)
    return im


def main(log: list[str], excel_png: Path | None = None) -> Path:
    title = "python run.py  ·  SAMPLE / SYNTHETIC invoices"
    frames, durations = [], []
    shown: list[str] = []
    for i, ln in enumerate(log):
        shown.append(ln)
        fast = ln.startswith("  SAMPLE")
        if fast and i + 1 < len(log) and log[i + 1].startswith("  SAMPLE") and i % 2 == 0:
            continue                                     # two file lines per frame keeps the GIF short
        frames.append(_frame(shown, title))
        durations.append(110 if fast else 700)
    durations[-1] = 2500
    if excel_png and excel_png.exists():
        ex = Image.open(excel_png).convert("RGB")
        ex.thumbnail((W - 40, H - 80))
        im = Image.new("RGB", (W, H), (249, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((24, 22), "Result: output/invoices_extracted.xlsx (Invoices sheet)", font=_font(18), fill=(13, 54, 107))
        im.paste(ex, ((W - ex.width) // 2, 64))
        frames.append(im)
        durations.append(4000)
    pal = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=64) for f in frames]
    GIF.parent.mkdir(exist_ok=True)
    pal[0].save(GIF, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
    frames[-2 if excel_png else -1].save(PROJECT / "output" / "run_console.png")
    return GIF
