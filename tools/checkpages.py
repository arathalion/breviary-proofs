#!/usr/bin/env python3
"""Check prepared page images before anything is read from them.

Usage:
    checkpages.py <pages dir> [--every N] [--part PREFIX] [--jobs N]

Three things can go wrong in preparing a page, and none of them shows up in
the reading. A page can lose type off its edge, because the fold of the book
is dark and a trim by brightness eats into the column beside it. A page can
come out with one column where it has two, which reads both columns as one
line. And a page can come out empty.

Each is a measurement on the image, so each is asked of the image.
"""
import argparse
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr
import pagelib

# Type that stands closer than this to the edge of the page has probably been
# cut. The book leaves an outer margin of about a tenth of the page width and
# an inner one of about a twentieth.
TIGHT = 0.012


def check(path):
    img = Image.open(path).convert("RGB")
    red, black = pagelib.classify(img)
    _, red_glyphs, red_rules = pagelib.split_rules(red)
    _, black_glyphs, black_rules = pagelib.split_rules(black)
    ink = red_glyphs | black_glyphs
    rules = red_rules + black_rules
    H, W = ink.shape

    body = ink[int(H * 0.15):int(H * 0.85), :]
    # The shadow of the fold is ink by colour but it is not type.
    body = body & ~pagelib.furniture_columns(body)
    prof = body.sum(axis=0).astype(float)
    # A tenth of the busiest column, so that dust and the speckle of bleed
    # through at the edge of the leaf do not count as type. A margin measured
    # against any ink at all reads as nothing on every page.
    xs = np.nonzero(prof > prof.max() * 0.10)[0] if prof.max() else []

    out = {"page": Path(path).stem, "w": W, "h": H, "rules": len(rules),
           "cols": len(ocr.find_columns(img, ink=ink, rules=rules)),
           "left": 1.0, "right": 1.0, "empty": len(xs) == 0}
    if len(xs):
        out["left"] = float(xs[0]) / W
        out["right"] = float(W - 1 - xs[-1]) / W
    out["shape"] = W / H
    return out


def lopsided(rows, tol=0.15):
    """Pages whose spread was cut in the wrong place.

    Every page of this book is the same shape, so the width over the height of
    one page is near constant within a part. A spread cut off centre breaks
    that in a pair: one page comes out narrow because it lost its inner edge,
    and its partner comes out wide because it kept a stripe of the facing
    page. The narrow one has lost text, and nothing downstream can see the
    loss.

    Measure each page against the median shape of its own part, not against a
    fixed number. The scans came from two machines and the parts differ.
    """
    import statistics as st
    from collections import defaultdict
    bypart = defaultdict(list)
    for r in rows:
        bypart[r["page"].split("-")[0]].append(r)
    out = []
    for part, rs in bypart.items():
        med = st.median([r["shape"] for r in rs])
        for r in rs:
            off = abs(r["shape"] - med) / med
            if off > tol:
                out.append((off, r, med))
    return sorted(out, key=lambda t: -t[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages")
    ap.add_argument("--every", type=int, default=1, help="check every Nth page")
    ap.add_argument("--part", default="", help="only pages whose name starts with this")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()

    files = sorted(Path(args.pages).glob(f"{args.part}*.png"))[::args.every]
    if not files:
        print(f"no pages match '{args.part}' in {args.pages}")
        return 1
    print(f"checking {len(files)} pages in {args.pages}\n")

    with ProcessPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(check, files, chunksize=8))

    parts = defaultdict(list)
    for r in rows:
        parts[r["page"].split("-")[0]].append(r)

    print(f"{'part':5s} {'pages':>6s} {'1 col':>6s} {'3+ col':>6s} {'tight':>6s} "
          f"{'empty':>6s} {'median margin l/r':>20s}")
    bad = []
    for part in sorted(parts):
        rs = parts[part]
        one = sum(1 for r in rs if r["cols"] == 1)
        many = sum(1 for r in rs if r["cols"] > 2)
        tight = sum(1 for r in rs if min(r["left"], r["right"]) < TIGHT)
        empty = sum(1 for r in rs if r["empty"])
        ml = np.median([r["left"] for r in rs]) * 100
        mr = np.median([r["right"] for r in rs]) * 100
        print(f"{part:5s} {len(rs):6d} {one:6d} {many:6d} {tight:6d} {empty:6d} "
              f"{ml:9.1f}% {mr:8.1f}%")
        bad += [r for r in rs
                if r["empty"] or min(r["left"], r["right"]) < TIGHT]

    totals = Counter()
    for r in rows:
        totals["cols%d" % min(r["cols"], 3)] += 1
    print(f"\n{len(rows)} pages: "
          + ", ".join(f"{n} with {k[4:]} column(s)" for k, n in sorted(totals.items())))
    cut = lopsided(rows)
    if cut:
        print(f"\n{len(cut)} pages were cut in the wrong place. The narrow one of "
              f"each pair has lost text off its inner edge.")
        for off, r, med in cut[:24]:
            wide = "wide, holds a stripe of its neighbour" if r["shape"] > med \
                else "NARROW, has lost its inner edge"
            print(f"   {r['page']}: shape {r['shape']:.2f} against {med:.2f}"
                  f" for the part, {off:.0%} off - {wide}")
        if len(cut) > 24:
            print(f"   ... and {len(cut) - 24} more")

    print(f"\n{len(bad)} pages want a look")
    for r in bad[:40]:
        why = "empty" if r["empty"] else f"margin l{r['left']*100:.1f}% r{r['right']*100:.1f}%"
        print(f"   {r['page']}: {why}")
    if len(bad) > 40:
        print(f"   ... and {len(bad) - 40} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
