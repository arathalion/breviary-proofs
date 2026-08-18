#!/usr/bin/env python3
"""Draw what the column finder saw, on top of the page it saw it in.

Usage:
    showcolumns.py <page.png> [more.png ...] -o sheet.html

Every fix so far has come from looking at the page, and every wrong turn from
reasoning about numbers taken off it. This puts the two side by side: the
column bounds in blue, the rules the page carries in green, and the columns
thrown out as furniture in grey.
"""
import argparse
import base64
import html
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr
import pagelib

SCALE = 3        # the page is shown at a third of its size


def draw(path):
    img = Image.open(path).convert("RGB")
    red, black = pagelib.classify(img)
    _, red_glyphs, red_rules = pagelib.split_rules(red)
    _, black_glyphs, black_rules = pagelib.split_rules(black)
    ink = red_glyphs | black_glyphs
    rules = red_rules + black_rules
    regions, crossed = ocr.find_regions(img, ink=ink, rules=rules)

    H, W = ink.shape
    body = ink[int(H * 0.09):int(H * 0.95), :]
    furniture = pagelib.furniture_columns(body)

    out = img.copy()
    d = ImageDraw.Draw(out, "RGBA")
    for x in np.nonzero(furniture)[0]:
        d.line([(x, 0), (x, H)], fill=(120, 120, 120, 90))
    for r in rules:
        d.rectangle([r["x"] - 2, r["y"] - 2, r["x"] + r["w"] + 2, r["y"] + r["h"] + 2],
                    outline=(0, 160, 0, 255), width=3)
    for y0, y1, cols in regions:
        for a, b in cols:
            d.rectangle([a, y0, b, y1], outline=(0, 90, 255, 255), width=5)
    for y0, y1 in crossed:
        d.rectangle([0, y0, W - 1, y1], outline=(255, 140, 0, 255), width=5)

    out.thumbnail((W // SCALE, H // SCALE))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=55)
    return (regions, crossed), rules, base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    cards = []
    for p in args.pages:
        (regions, crossed), rules, b64 = draw(p)
        shape = "; ".join(" ".join(str(b - a) for a, b in cols)
                          for _, _, cols in regions)
        tall = sum(1 for r in rules if r["dir"] == "tall")
        cards.append(
            f'<figure><img src="data:image/jpeg;base64,{b64}" alt="">'
            f'<figcaption>{html.escape(Path(p).stem)}<br>'
            f'column widths {shape}, {tall} tall rule(s), '
            f'{len(crossed)} band(s) crossing the gutter</figcaption></figure>')

    Path(args.out).write_text(
        "<!doctype html><meta charset=utf-8><title>Column check</title>"
        "<style>body{background:#15130F;color:#E9E3D8;font:14px ui-monospace,Menlo,monospace;"
        "margin:0;padding:1.5rem}main{display:flex;flex-wrap:wrap;gap:1.5rem}"
        "figure{margin:0}img{display:block;max-width:100%}"
        "figcaption{padding-top:.5rem;color:#9A9086;line-height:1.5}</style>"
        f"<main>{''.join(cards)}</main>", encoding="utf-8")
    print(f"wrote {args.out}: {len(cards)} pages")


if __name__ == "__main__":
    main()
