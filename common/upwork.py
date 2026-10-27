"""Builds and checks the Upwork package of each project (upwork/ folder).

- make_cover(): 1600x1200 cover, same layout for every project.
- make_shot(): puts a screenshot on a 1600x1200 (4:3) canvas with a short header.
- write_texts(): writes title/description/skills/captions/links .txt files.
- check_package(): verifies character limits, image sizes and placeholder text.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from brand import (AXIS, BRAND, BRAND_2, FONTS, INK, INK_2, MUTED, PAGE, PORTFOLIO_TAG,
                   SURFACE)
import config

W, H = 1600, 1200
TITLE_MAX = 50
DESC_MAX = 500
CAPTION_MAX = 300
DESC_ENDING = "Sample project built with public data."
PLACEHOLDERS = re.compile(r"\b(TODO|TBD|FIXME|lorem ipsum|xxx)\b", re.I)


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS[weight]), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_into(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    img = img.convert("RGB")
    scale = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def _card(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 18) -> None:
    """White card with a soft shadow and hairline border."""
    x0, y0, x1, y1 = box
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x0, y0 + 8, x1, y1 + 8), radius=radius, fill=(13, 54, 107, 38))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(box, radius=radius, fill=SURFACE, outline=AXIS, width=2)


def make_cover(out: Path, number: int, service: str, title: str, subtitle: str,
               chart_png: Path, tools: str) -> Path:
    canvas = Image.new("RGBA", (W, H), PAGE)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, W, 18), fill=BRAND)

    d.text((90, 66), f"PROJECT {number:02d}  ·  {service.upper()}", font=_font("semibold", 30), fill=BRAND_2)

    title_font = _font("extrabold", 92)
    lines = _wrap(d, title, title_font, W - 180)
    if len(lines) > 2:
        title_font = _font("extrabold", 78)
        lines = _wrap(d, title, title_font, W - 180)
    y = 118
    for line in lines[:2]:
        d.text((86, y), line, font=title_font, fill=INK)
        y += int(title_font.size * 1.12)
    y += 6
    sub_font = _font("medium", 38)
    for line in _wrap(d, subtitle, sub_font, W - 180)[:2]:
        d.text((90, y), line, font=sub_font, fill=INK_2)
        y += 50

    top = y + 34
    box = (90, top, W - 90, 1085)
    _card(canvas, box)
    chart = _fit_into(Image.open(chart_png), box[2] - box[0] - 60, box[3] - box[1] - 50)
    cx = box[0] + (box[2] - box[0] - chart.width) // 2
    cy = box[1] + (box[3] - box[1] - chart.height) // 2
    canvas.paste(chart, (cx, cy))

    d = ImageDraw.Draw(canvas)
    foot = _font("medium", 28)
    d.text((90, 1118), f"{PORTFOLIO_TAG}  ·  {config.AUTHOR}", font=foot, fill=MUTED)
    tw = d.textlength(tools, font=_font("semibold", 28))
    d.text((W - 90 - tw, 1118), tools, font=_font("semibold", 28), fill=INK_2)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, optimize=True)
    return out


def make_shot(out: Path, screenshot: Path, label: str, crop: tuple[int, int, int, int] | None = None) -> Path:
    """Place a real screenshot of the deliverable on a 4:3 canvas with a short label."""
    canvas = Image.new("RGBA", (W, H), PAGE)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, W, 12), fill=BRAND)
    d.text((70, 44), label, font=_font("semibold", 40), fill=INK)
    box = (70, 130, W - 70, H - 60)
    _card(canvas, box, radius=14)
    img = Image.open(screenshot)
    if crop:
        img = img.crop(crop)
    img = _fit_into(img, box[2] - box[0] - 36, box[3] - box[1] - 36)
    canvas.paste(img, (box[0] + (box[2] - box[0] - img.width) // 2, box[1] + (box[3] - box[1] - img.height) // 2))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, optimize=True)
    return out


def write_texts(upwork_dir: Path, title: str, description: str, skills: list[str],
                captions: list[str], links: list[str]) -> None:
    upwork_dir.mkdir(parents=True, exist_ok=True)
    (upwork_dir / "title.txt").write_text(title.strip() + "\n", encoding="utf-8")
    (upwork_dir / "description.txt").write_text(description.strip() + "\n", encoding="utf-8")
    (upwork_dir / "skills.txt").write_text("\n".join(skills) + "\n", encoding="utf-8")
    cap_lines = [f"shot-{i}.png: {c.strip()}" for i, c in enumerate(captions, start=1)]
    (upwork_dir / "captions.txt").write_text("\n".join(cap_lines) + "\n", encoding="utf-8")
    (upwork_dir / "links.txt").write_text("\n".join(links) + "\n", encoding="utf-8")


def check_package(upwork_dir: Path) -> list[str]:
    """Return a list of problems (empty list = package is ready to upload)."""
    problems: list[str] = []
    title = (upwork_dir / "title.txt").read_text(encoding="utf-8").strip()
    desc = (upwork_dir / "description.txt").read_text(encoding="utf-8").strip()
    skills = [s for s in (upwork_dir / "skills.txt").read_text(encoding="utf-8").splitlines() if s.strip()]
    caps = [c for c in (upwork_dir / "captions.txt").read_text(encoding="utf-8").splitlines() if c.strip()]
    links = [l for l in (upwork_dir / "links.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

    if len(title) > TITLE_MAX:
        problems.append(f"title has {len(title)} chars (max {TITLE_MAX})")
    if len(desc) > DESC_MAX:
        problems.append(f"description has {len(desc)} chars (max {DESC_MAX})")
    if not desc.endswith(DESC_ENDING):
        problems.append("description must end with the 'Sample project...' sentence")
    if len(skills) != 5:
        problems.append(f"skills.txt has {len(skills)} skills (need 5)")
    for line in caps:
        text = line.split(":", 1)[1].strip()
        if len(text) > CAPTION_MAX:
            problems.append(f"caption too long ({len(text)}): {line[:40]}...")
    if not links:
        problems.append("links.txt is empty")
    for name, text in (("title", title), ("description", desc), ("captions", "\n".join(caps))):
        if PLACEHOLDERS.search(text):
            problems.append(f"placeholder text found in {name}")

    cover = upwork_dir / "cover.png"
    if not cover.exists():
        problems.append("cover.png missing")
    else:
        im = Image.open(cover)
        if im.size != (1600, 1200):
            problems.append(f"cover.png is {im.size}, expected (1600, 1200)")
        if cover.stat().st_size >= 5 * 1024 * 1024:
            problems.append("cover.png is 5 MB or larger")

    shots = sorted(upwork_dir.glob("shot-*.png"))
    if not 3 <= len(shots) <= 5:
        problems.append(f"{len(shots)} screenshots (need 3-5)")
    if len(caps) != len(shots):
        problems.append(f"{len(caps)} captions for {len(shots)} screenshots")
    for s in shots:
        im = Image.open(s)
        if abs(im.width / im.height - 4 / 3) > 0.01 or im.width < 1000 or im.height < 750:
            problems.append(f"{s.name} is {im.size}: must be 4:3 and at least 1000x750")
        if s.stat().st_size >= 5 * 1024 * 1024:
            problems.append(f"{s.name} is 5 MB or larger")
    pdf = upwork_dir / "one-pager.pdf"
    if pdf.exists() and pdf.stat().st_size >= 25 * 1024 * 1024:
        problems.append("one-pager.pdf is 25 MB or larger")
    return problems


def report(upwork_dir: Path) -> None:
    problems = check_package(upwork_dir)
    title = (upwork_dir / "title.txt").read_text(encoding="utf-8").strip()
    desc = (upwork_dir / "description.txt").read_text(encoding="utf-8").strip()
    print(f"  Upwork title: {len(title)}/{TITLE_MAX} chars | description: {len(desc)}/{DESC_MAX} chars")
    if problems:
        raise SystemExit("Upwork package problems:\n  - " + "\n  - ".join(problems))
    print("  Upwork package: OK")
