#!/usr/bin/env python3
"""Read a prepared breviary page into draft markup.

Usage:
    ocr.py <page.png> [--out draft.md] [--keep-images DIR]

The page is cut into its two columns, and each column is split into a red
layer and a black layer. Every layer is read on its own. That is the whole
trick: the OCR engine never sees two columns at once, and never sees two
colours at once, so it cannot merge them.

The output is a draft. It still needs a person to check it against the scan.
"""
import argparse
import json
import statistics as st
import sys
import tempfile
from pathlib import Path

import fnmatch
import functools

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pagelib
import tsv

UPSCALE = 2          # small type reads better when enlarged before OCR
PAD = 12             # white border added so the engine sees clean edges
PSM = "6"            # treat each column as one uniform block of text
# How much of a band's height may hold ink inside the gutter before the band
# is called full width. Bleed through from the far side of the leaf speckles a
# real gutter; a heading standing across the page fills half of it.
CROSS_HEADING = 0.30
# Rows of ink standing in the gutter before a band is read full width. One
# line of this type is about thirty rows tall; a comma is three.
CROSS_ROWS = 18


# The few pages this book does not set in two columns, named by hand in
# `onecolumn.txt` beside the drafts. There is no detector, and the file says
# why. This tool holds no page names itself, so it still ports to another book:
# without the file every page is measured as before.
ONECOLUMN = Path(__file__).resolve().parent.parent / "onecolumn.txt"


@functools.lru_cache(maxsize=1)
def one_column_patterns():
    """The glob patterns naming pages to read as one column."""
    if not ONECOLUMN.exists():
        return ()
    out = []
    for line in ONECOLUMN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.split()[0])
    return tuple(out)


def is_one_column(stem):
    """True if this page must not be split down the middle."""
    return any(fnmatch.fnmatch(stem, p) for p in one_column_patterns())


def longest_false(flags, lo, hi):
    """The longest run of False within flags[lo:hi], as (start, end)."""
    best = (0, 0)
    start = None
    for i in range(lo, hi):
        if not flags[i]:
            if start is None:
                start = i
            if i + 1 - start > best[1] - best[0]:
                best = (start, i + 1)
        else:
            start = None
    return best


def find_columns(img, ink=None, rules=(), one=False):
    """Just the columns, for the page checkers."""
    regions, _ = find_regions(img, ink, rules, one=one)
    return regions[0][2] if regions else []


def type_block(ink):
    """The x range that the type occupies, and the ink profile inside it."""
    H, W = ink.shape
    body = ink[int(H * 0.09):int(H * 0.95), :]
    # The fold of the book, the edge of the leaf and the fore edge of the book
    # block are all ink by colour, and all of them stand unbroken down the
    # page, which no column of type does. See pagelib.
    body = body & ~pagelib.furniture_columns(body)
    prof = body.sum(axis=0).astype(float)
    if prof.max() == 0:
        return None, None
    # A low floor, so that a page of a few centred lines still shows its full
    # width, and the gaps closed, so that a title page is one block and not six.
    edge = prof > max(2.0, prof.max() * 0.02)
    xs = np.nonzero(pagelib.close_gaps(edge, int(W * 0.08)))[0]
    if len(xs) == 0 or xs[-1] - xs[0] < W * 0.2:
        return None, None
    return (int(xs[0]), int(xs[-1]) + 1), body


def cluster(values, tol):
    """Group values that lie within tol of each other, and return the middles.

    Not the median of everything. A band whose last line is short leaves a
    space wider than the gutter, so a page collects its guesses in two or
    three places, and the median of those sits between them: inside a column,
    where a split cuts every line of that column in half.
    """
    out, cur = [], []
    for v in sorted(values):
        if cur and v - cur[0] > tol:
            out.append(int(np.median(cur)))
            cur = []
        cur.append(v)
    if cur:
        out.append(int(np.median(cur)))
    return out


def widen(j, body, floor=0.05):
    """Grow a point in the gutter out to the whole empty gap around it.

    The guess lands somewhere in the gutter, and often near one edge of it,
    because the emptiest window is not the middle one. Splitting there takes
    the last letters off the lines of the column beside it, and it leaves the
    test for a crossing looking at the ends of those lines rather than at the
    gap. Both are cured by finding the two edges of the gap and using them.
    """
    prof = body.sum(axis=0).astype(float)
    if prof.max() == 0:
        return j, j
    quiet = prof <= prof.max() * floor
    a = b = j
    while a > 0 and quiet[a - 1]:
        a -= 1
    while b < len(prof) - 1 and quiet[b + 1]:
        b += 1
    return (a, b) if b > a else (j, j)


def crossing_run(rows, c, half=3):
    """The tallest unbroken run of rows that carry ink through the gutter.

    This is what tells a heading set across the page from an ordinary line
    that merely reaches the gutter. The type is justified and the gutter of
    this book is as narrow as four pixels, so a comma at the end of a line
    lands in it and closes it for two or three rows. A line of type standing
    across the gutter closes it for its whole height, about thirty rows.
    """
    lo, hi = max(0, c - half), min(rows.shape[1], c + half + 1)
    if hi <= lo:
        return 0
    best = cur = 0
    for v in rows[:, lo:hi].any(axis=1):
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def band_gap(rows, c):
    """How wide the clear gap is at column c in one band of rows.

    Zero if the type stands on c itself. This is measured band by band and
    then compared with the same measure over the whole page, because what
    marks a heading is not that the gutter is narrow but that it closes.
    """
    prof = rows.sum(axis=0)
    if c >= len(prof):
        return 0
    # A stray pixel or two is not type. A comma at the end of a justified line
    # can sit on the gutter, and a speck of bleed through certainly can.
    clear = prof <= max(1, rows.shape[0] * 0.03)
    if not clear[c]:
        return 0
    a = b = c
    while a > 0 and clear[a - 1]:
        a -= 1
    while b < len(prof) - 1 and clear[b + 1]:
        b += 1
    return b - a + 1


def crosses(rows, gutter, W, limit=0.15):
    """True if the type crosses the gutter, so this band is not two columns.

    The window sits in the middle of the gutter and is kept narrow. A window
    that reached to the edge of the gutter would find the ends of the lines
    beside it, and then every band of an ordinary page would look crossed.
    """
    a, b = (gutter, gutter) if np.isscalar(gutter) else gutter
    c = (a + b) // 2
    half = max(4, (b - a) // 6)
    a, b = max(0, c - half), min(rows.shape[1], c + half + 1)
    if b <= a:
        return True
    return bool(rows[:, a:b].any(axis=1).mean() > limit)


def band_gutter(rows, lo, hi, W, crossing=0.15):
    """Where the gutter falls in one horizontal band, or None.

    The emptiest window, not the longest empty run: one descender, or one
    speck of bleed through from the far side of the leaf, lands in the gutter
    and cuts that run in half, but hardly moves a window.

    Then the window has to earn the name. What makes a gutter is that the
    lines stop at it, so almost no row of the band has ink inside it. A
    heading standing across the middle of the page leaves gaps between its
    words that are just as empty on average, but the letters of the heading
    cross the window and give it away.
    """
    prof = rows.sum(axis=0).astype(float)
    if prof.max() == 0 or hi - lo < 4:
        return None
    win = max(9, int(W * 0.012))
    smooth = np.convolve(prof, np.ones(win) / win, mode="same")
    j = lo + int(np.argmin(smooth[lo:hi]))
    return None if crosses(rows, j, W, crossing) else j


def find_regions(img, ink=None, rules=(), band=90, one=False):
    """The columns of a page, and the bands where that answer is wrong.

    Returns ([(y0, y1, [(x0, x1), ...])], crossed), where crossed lists the
    y ranges in which the type runs across the gutter.

    The book sets some headings across the full width of the page, in the
    middle of two column matter. The column split cuts those in half, and
    nothing downstream can see that it happened, because the pieces are still
    words. Reading each band with its own measure was tried and was worse: on
    a page where the gutter is hard to place, the measure then changes from
    band to band and the page comes apart into a ladder of little regions.

    So the page keeps one measure, and the bands that disagree with it are
    reported instead of guessed at. A known list of pages to look at beats a
    silent mistake on an unknown list.
    """
    if ink is None:
        red, black = pagelib.classify(img)
        _, red_glyphs, red_rules = pagelib.split_rules(red)
        _, black_glyphs, black_rules = pagelib.split_rules(black)
        ink = red_glyphs | black_glyphs
        rules = red_rules + black_rules

    H, W = ink.shape
    block, body = type_block(ink)
    if block is None:
        return [], []
    left, right = block
    # A page named in `onecolumn.txt` keeps its measure whole. Nothing is
    # crossed, because there is no gutter for the type to cross.
    if one:
        return [(int(H * 0.09), int(H * 0.95), [(left, right)])], []
    width = right - left
    lo, hi = left + int(width * 0.30), left + int(width * 0.70)
    top = int(H * 0.09)

    # Where the printer drew a rule down the gutter, that rule is the answer,
    # and it is the answer for every band it passes through. The gutter of this
    # book is about eight pixels of clear paper at 300 ppi, too little to
    # measure safely, but the rule standing in it is plain.
    drawn = [r for r in rules
             if r["dir"] == "tall" and r["h"] > H * 0.20
             and lo <= r["x"] + r["w"] // 2 < hi]

    # A rule that the scan broke into pieces leaves the short pieces behind,
    # and they stand in the gutter and read as ink on every row of it. Ink
    # anywhere a rule was found is furniture, whole or in pieces.
    ruled = np.zeros(W, dtype=bool)
    for r in rules:
        if r["dir"] == "tall":
            ruled[max(0, r["x"] - 1):r["x"] + r["w"] + 1] = True
    body = body & ~ruled

    bands = [body[y:y + band] for y in range(0, body.shape[0], band)]

    # The gutter of a page does not move down the page, so it is measured once,
    # from every band that shows one clearly. A single band holds three or four
    # lines and its own guess wobbles by tens of pixels; the middle of all the
    # guesses does not. Where the printer drew a rule, that is the answer
    # already and nothing needs to be guessed.
    if drawn:
        gutter = (min(r["x"] for r in drawn),
                  max(r["x"] + r["w"] for r in drawn))
    else:
        seen = [j for j in (band_gutter(rw, lo, hi, W) for rw in bands)
                if j is not None]
        # Of the places the bands point at, keep the one that works for the
        # most of them. Counting the bands a candidate would divide cleanly
        # measures the thing we actually want, where counting the guesses only
        # measures where the argument was loudest.
        best, votes = None, 0
        for c in cluster(seen, W * 0.04):
            n = sum(1 for rw in bands if not crosses(rw, c, W, CROSS_HEADING))
            if n > votes:
                best, votes = c, n
        gutter = None if best is None else widen(best, body)

    # Each band is then measured against the page it is on, and a band whose
    # gutter closes is reported. It is not treated. Reading such a band full
    # width was tried, twice, and both times it fired on ordinary pages: the
    # type is justified and the gutter of this book is as narrow as four
    # pixels, so the ends of ordinary lines sit inside any window drawn at it.
    # Reading two columns as one interleaves them, which is a worse fault than
    # cutting a heading, so the page keeps one measure and the disagreement is
    # reported. See the note in audit.py.
    crossed = []
    if gutter is not None:
        c = (gutter[0] + gutter[1]) // 2
        gaps = [band_gap(rows, c) for rows in bands]
        real = [g for g, rows in zip(gaps, bands) if rows.sum() >= band * 0.5]
        typical = st.median(real) if real else 0
        for i, (g, rows) in enumerate(zip(gaps, bands)):
            if rows.sum() < band * 0.5 or g >= max(2, typical * 0.35):
                continue
            y0 = top + i * band
            if crossed and crossed[-1][1] == y0:
                crossed[-1] = (crossed[-1][0], min(y0 + band, int(H * 0.95)))
            else:
                crossed.append((y0, min(y0 + band, int(H * 0.95))))

    cols = ([(left, gutter[0]), (gutter[1], right)] if gutter
            else [(left, right)])
    return [(top, int(H * 0.95), cols)], crossed


def merge_layers(lines, column, region, gap=0.6):
    """Put the lines of the two ink layers back into reading order.

    A printed line can hold both colours: the book sets a red versicle mark,
    a red "Ant." or a red chapter reference inside a black line and carries
    straight on. The two layers are read apart, so that line comes back as two
    pieces. Gather the pieces of one printed line, then order them across the
    measure, which is how a person reads it.
    """
    if not lines:
        return []
    hs = sorted(w["h"] for l in lines for w in l["words"])
    med = hs[len(hs) // 2] if hs else 1
    pieces = sorted(lines, key=lambda l: (l["y"], min((w["x"] for w in l["words"]),
                                                      default=0)))
    rows, cur = [], []
    for l in pieces:
        if cur and abs(l["y"] - cur[0]["y"]) > med * gap:
            rows.append(cur)
            cur = []
        cur.append(l)
    if cur:
        rows.append(cur)

    out = []
    for row in rows:
        row.sort(key=lambda l: min((w["x"] for w in l["words"]), default=0))
        for l in row:
            # Nothing inside a line is ever reordered. It was tried, sorting
            # the words across the measure, and it broke a page this book
            # really contains: the engine returned BREVIARY OF THE ORDER OF
            # PREACHERS as one line over two printed lines, and sorting its
            # words by x handed back ORDER BREVIARY OF PREACHERS OF THE.
            #
            # The engine knows the reading order of its own line, including
            # where it has run two printed lines together. Only the lines are
            # put in order here, never the words in them.
            if not out or out[-1]["layer"] != l["layer"]:
                out.append({"column": column, "region": region,
                            "layer": l["layer"], "text": "", "words": []})
            out[-1]["words"] += l["words"]
            out[-1]["text"] += ("\n" if out[-1]["text"] else "") + l["text"]
    return out


def layer_image(mask, pad=PAD):
    """Paint one ink layer as black on white, ready for the OCR engine."""
    h, w = mask.shape
    canvas = np.full((h + pad * 2, w + pad * 2), 255, dtype=np.uint8)
    canvas[pad:pad + h, pad:pad + w][mask] = 0
    img = Image.fromarray(canvas)
    return img.resize((img.width * UPSCALE, img.height * UPSCALE), Image.LANCZOS)


def read(img, tmp, tag):
    """Run the OCR engine over one layer.

    The reading itself is in `tsv.py`, which holds nothing about this book.
    The scale and the pad undo the enlargement and the white border added by
    `layer_image`, so every box comes back in the coordinates of the column
    crop and can index the image.

    The vertical position of each line is what puts the two ink layers back
    into one reading order further down.
    """
    return tsv.read_image(img, tmp, tag, lang="eng", psm=PSM,
                          scale=UPSCALE, pad=PAD)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--out")
    ap.add_argument("--keep-images")
    args = ap.parse_args()

    img = Image.open(args.page).convert("RGB")
    red, black = pagelib.classify(img)
    # The rules are furniture, not words. They are set aside before the columns
    # are measured and before either layer is read, and their positions travel
    # with the draft, because a rule under a running head marks the head.
    red_rules, red, red_boxes = pagelib.split_rules(red)
    black_rules, black, black_boxes = pagelib.split_rules(black)
    rules = red_boxes + black_boxes

    regions, crossed = find_regions(img, ink=red | black, rules=rules,
                                    one=is_one_column(Path(args.page).stem))
    if not regions:
        # A blank leaf backing a title page carries no type of its own, only
        # what shows through from the other side. Nothing to read is a fact
        # about the page, not a failure of the tool, so it has its own exit
        # code and the runner lists it apart from the faults.
        print(f"nothing to read on {args.page}", file=sys.stderr)
        return 2

    stem = Path(args.page).stem
    blocks = []
    n = 0
    with tempfile.TemporaryDirectory() as tmp:
        # Regions run down the page and columns run across each region, so
        # this order is reading order. Columns are numbered straight through
        # the page, which keeps everything downstream working on a flat list.
        for k, (y0, y1, cols) in enumerate(regions, 1):
            for a, b in cols:
                n += 1
                if args.keep_images:
                    d = Path(args.keep_images)
                    d.mkdir(parents=True, exist_ok=True)
                    # The proof sheet compares against the colour original,
                    # which is what a person can check the reading against.
                    img.crop((a, y0, b, y1)).save(d / f"{stem}-c{n}.png")
                # Read the two ink layers apart, then put them back together in
                # the order they sit on the page. A rubric interrupts the text
                # and hands it back, so layer order is not reading order.
                lines = []
                for name, mask in (("black", black), ("red", red)):
                    layer = layer_image(mask[y0:y1, a:b])
                    for line in read(layer, tmp, f"c{n}-{name}"):
                        line["layer"] = name
                        # The engine measures from the corner of the piece it
                        # was given. Shift back to the coordinates of the whole
                        # page, so a box can be used to index the page image.
                        for word in line["words"]:
                            word["x"] += a
                            word["y"] += y0
                        line["y"] += y0
                        lines.append(line)
                # Sorting the two layers by y alone was wrong. Where a red
                # mark and black text share one printed line, the engine
                # measures each layer's line box off its own glyphs: black
                # carries ascenders and descenders, a red mark is short. So
                # which came first was decided by the height of the letters
                # rather than by where they stand across the measure, and
                # 20.9% of the handovers in this book came out backwards.
                #
                # Group the lines of both layers together first, then read
                # each printed line across. That takes it to 4.7%.
                blocks += merge_layers(lines, n, k)

    lines = [f"#src {stem}", ""]
    for b in blocks:
        lines.append(f".{'rubric' if b['layer'] == 'red' else 'text'}")
        lines.append(f"% region {b['region']}, column {b['column']}, "
                     f"{b['layer']} layer")
        lines += [t for t in b["text"].splitlines() if t.strip()]
        lines.append("")

    if not any(b["words"] for b in blocks):
        # A page that reads as nothing must say so. Reporting success here once
        # hid 29 pages inside a batch that claimed it had read everything.
        print(f"nothing to read on {args.page}", file=sys.stderr)
        return 2

    body = "\n".join(lines)
    if args.out:
        out = Path(args.out)
        out.write_text(body, encoding="utf-8")
        draft = {"src": stem, "regions": regions, "rules": rules,
                 "crossed": crossed, "blocks": blocks}

        # What a person put here does not come from the engine and cannot be
        # made again. `applyfix.py` writes it into the draft, and this file
        # used to overwrite the draft whole: reading a page again threw away
        # the note somebody wrote on it and the record that they had read it
        # in full. Three of the jobs left on this book end in "read that page
        # again", and every one of them would have done it in silence.
        keep = out.with_suffix(".json")
        if keep.exists():
            try:
                was = json.loads(keep.read_text(encoding="utf-8"))
            except ValueError:
                was = {}
            for field in ("proofed", "note"):
                if was.get(field):
                    draft[field] = was[field]
                    print(f"  kept {field} from the draft that was here",
                          file=sys.stderr)

        # The confidences travel beside the draft, for the proof sheet.
        keep.write_text(json.dumps(draft, indent=1), encoding="utf-8")
        print(f"wrote {out} and {keep}")
    else:
        print(body)

    for b in blocks:
        w = b["words"]
        low = sum(1 for x in w if x["conf"] < 80)
        avg = sum(x["conf"] for x in w) / len(w) if w else 0
        print(f"  column {b['column']} {b['layer']:5s}: {len(w):4d} words, "
              f"mean confidence {avg:5.1f}, {low:3d} to check", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
