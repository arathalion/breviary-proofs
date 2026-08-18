#!/usr/bin/env python3
"""Find ink on the page that no word box covers.

Usage:
    unread.py                     every page
    unread.py 13-Proper           one part, or a prefix
    unread.py --show 30           list more pages

The proof sheet marks the words the engine was unsure of. It cannot mark what
the engine never read, because a confidence score is an opinion about a
reading and there is no reading to have an opinion about. A page whose rubrics
failed reports high confidence on the few words it did find, and reads as one
of the healthiest pages in the book.

So do not ask the engine. Measure the page.

Every word the engine read carries a box. Paint all the boxes, lay them over
the ink, and whatever ink is left is ink the engine did not account for. That
is a geometric test, it is independent of the reading, and it can see the one
thing the reading is blind to.

**Count only ink shaped like type.** The first version counted every loose
pixel and flagged 67 pages, and the two worst were a leaf edge and the rules of
the Table of Movable Feasts. Neither is a missed word. So label the loose ink
and keep only the lumps that could be a letter: about the height of the type
around them, and not long and thin. That throws out the fore edge, the rules a
table draws, the running head and the specks, and leaves the one thing worth
reporting.

Some ink is uncovered on every healthy page, so the number on its own means
nothing:

  - a drop capital, which the engine never reads and `find_dropcaps` finds by
    shape instead
  - the versicle and response marks, which no engine knows
  - the printed rules
  - specks, bleed through from the other side of the leaf

The rules are taken out here. The rest is why each page is measured against
the median page of its own part rather than against a fixed number. A page
that carries three times the uncovered ink of its neighbours is the one worth
looking at, whatever the absolute figure is.
"""
import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pagelib
import structure

ROOT = Path(__file__).resolve().parent.parent
PAD = 3          # px: a box is the type, and ink spreads a little past it


def measure(args):
    """Uncovered ink over total ink, inside the span the reading used."""
    page, draft = args
    try:
        data = json.loads(Path(draft).read_text(encoding="utf-8"))
    except Exception:
        return None
    words = [w for b in data["blocks"] for w in b["words"]]
    if not words:
        return None

    img = Image.open(page).convert("RGB")
    red, black = pagelib.classify(img)
    ink = red | black
    _, glyphs, _ = pagelib.split_rules(ink)      # a rule is not a missed word
    # The fore edge of the book block shows as pale striations down the page
    # and is chunky enough to pass a test on shape alone. It runs unbroken,
    # and type never does.
    glyphs = glyphs & ~pagelib.furniture_columns(glyphs)
    H, W = glyphs.shape

    # Only where the reading claims to have looked. Outside it lies the
    # running head, the folio and the edge of the leaf, and none of those is
    # a missed word.
    x0 = max(0, min(w["x"] for w in words) - 12)
    x1 = min(W, max(w["x"] + w["w"] for w in words) + 12)
    y0 = max(0, min(w["y"] for w in words) - 12)
    y1 = min(H, max(w["y"] + w["h"] for w in words) + 12)
    band = glyphs[y0:y1, x0:x1]
    total = int(band.sum())
    if total < 500:
        return None

    covered = np.zeros_like(band)
    for w in words:
        a = max(0, w["y"] - PAD - y0)
        b = min(band.shape[0], w["y"] + w["h"] + PAD - y0)
        c = max(0, w["x"] - PAD - x0)
        d = min(band.shape[1], w["x"] + w["w"] + PAD - x0)
        if b > a and d > c:
            covered[a:b, c:d] = True

    from scipy import ndimage

    loose = band & ~covered
    # The height of the type on this page, from the boxes the engine did read.
    hs = sorted(w["h"] for w in words)
    med_h = hs[len(hs) // 2] or 1

    # A drop capital is ink no word box covers, on every page that has one,
    # and it is not missed: `structure.find_dropcaps` reads it off the page by
    # shape, exactly because the engine cannot. Take those out too, or the
    # detector reports the one thing the pipeline already handles.
    # find_dropcaps returns the box as a tuple under "box", not as x/y/w/h.
    # This was wrapped in a bare except at first, which swallowed the KeyError
    # and quietly removed nothing at all. A detector that fails silently is
    # the fault it exists to catch, so it raises now.
    for cap in structure.find_dropcaps(img, x0, x1, med_h):
        cx, cy, cw, ch = cap["box"]
        a = max(0, cy - y0 - PAD)
        b = min(loose.shape[0], cy + ch - y0 + PAD)
        c = max(0, cx - x0 - PAD)
        d = min(loose.shape[1], cx + cw - x0 + PAD)
        if b > a and d > c:
            loose[a:b, c:d] = False

    # A missed word is a lump of ink about as tall as the type beside it. The
    # fore edge of the book block is tall and thin, a table rule is long and
    # thin, and a speck is neither. Shape separates all three from a letter.
    labels, n = ndimage.label(loose)
    keep = 0
    if n:
        for sl in ndimage.find_objects(labels):
            ys, xs = sl
            h, w = ys.stop - ys.start, xs.stop - xs.start
            if h < med_h * 0.35 or h > med_h * 2.6:
                continue                      # a speck, or the edge of a leaf
            if w > med_h * 12 and h < med_h * 0.6:
                continue                      # a rule
            keep += int(loose[sl].sum())

    return {"page": Path(page).stem, "frac": keep / total,
            "ink": total, "words": len(words)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", nargs="?", default="")
    ap.add_argument("--show", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--names", action="store_true",
                    help="print only the page names, one a line, for a proof sheet")
    ap.add_argument("--pages", default=str(ROOT / "pages"))
    ap.add_argument("--drafts", default=str(ROOT / "drafts"))
    args = ap.parse_args()

    pages, drafts = Path(args.pages), Path(args.drafts)
    jobs = []
    for p in sorted(pages.glob(f"{args.part}*.png")):
        d = drafts / f"{p.stem}.json"
        if d.exists():
            jobs.append((str(p), str(d)))
    if not jobs:
        print(f"no pages match '{args.part}'")
        return 2

    if not args.names:
        print(f"measuring {len(jobs)} pages\n")
    with ProcessPoolExecutor(args.jobs) as pool:
        rows = [r for r in pool.map(measure, jobs, chunksize=8) if r]

    byp = defaultdict(list)
    for r in rows:
        byp[r["page"].split("-")[0]].append(r)

    if not args.names:
        print(f"{'part':<6}{'pages':>7}{'median':>9}{'worst':>9}")
        print("-" * 34)
    flagged = []
    for part in sorted(byp):
        rs = byp[part]
        med = st.median([r["frac"] for r in rs])
        worst = max(r["frac"] for r in rs)
        if not args.names:
            print(f"{part:<6}{len(rs):>7}{med:>8.1%}{worst:>9.1%}")
        # Against its own part. The Psalter came from a second machine and
        # every part differs, so one number for the book would be meaningless.
        for r in rs:
            if med > 0 and r["frac"] > max(med * 2.5, med + 0.05):
                flagged.append((r["frac"] / med, r))

    flagged.sort(key=lambda t: -t[0])
    if args.names:
        for _, r in flagged:
            print(r["page"])
        return 0
    print(f"\n{len(flagged)} pages carry far more unaccounted ink than their part")
    for ratio, r in flagged[:args.show]:
        print(f"   {r['page']}: {r['frac']:.1%} loose, {ratio:.1f}x its part, "
              f"{r['words']} words read")
    if len(flagged) > args.show:
        print(f"   ... and {len(flagged) - args.show} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
