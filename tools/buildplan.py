#!/usr/bin/env python3
"""Inline EB Garamond into plan.html and write plan.built.html.

The artifact host blocks every request to an outside server, so a linked font
would fail without warning. We embed the face as a data URI instead. EB
Garamond is the face that the book itself uses.
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path("/usr/local/texlive/2026/texmf-dist/fonts/opentype/public/ebgaramond")

src = (ROOT / "plan.html").read_text(encoding="utf-8")
for token, name in (("__FONT_REGULAR__", "EBGaramond-Regular.otf"),
                    ("__FONT_ITALIC__", "EBGaramond-Italic.otf")):
    data = base64.b64encode((FONTS / name).read_bytes()).decode("ascii")
    src = src.replace(token, data)

out = ROOT / "plan.built.html"
out.write_text(src, encoding="utf-8")
print(f"wrote {out}  {len(src)/1024:.0f} KB")
