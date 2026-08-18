#!/usr/bin/env python3
"""Shared page handling for the breviary scans.

The scans are photographs of an open book on a dark cloth. One image holds a
two page spread, and each book page holds two columns. Before OCR we must trim
the background, cut the spread at the fold, and straighten each page.

The ink colour carries meaning in a breviary. Black is what you say. Red is the
rubric that tells you how to say it. The classify function keeps the two apart.
"""
import subprocess
import tempfile
from pathlib import Path

import functools

import numpy as np
from PIL import Image
from scipy import ndimage

# Red ink in these scans is a bright vermilion. Its red channel stays near the
# brightness of the paper while green and blue fall away. Measured over a page
# of rubrics, the red channel sits at 237 and stands 111 above the larger of
# green and blue.
#
# Black ink is dark and neutral, but a stroke does not stop at its edge. The
# edge pixels are part ink and part cream paper, so they come out warm and
# red-dominant. That is the trap. Those pixels are red-dominant but they are
# neither bright nor strongly coloured: on the same page they sit at 112 with a
# margin of 28. Two absolute tests hold them out, where a ratio test did not.
RED_MIN = 150         # the red channel of true rubric ink
RED_MARGIN = 55       # how far red must stand above green and blue
HALO = 2              # px: red is not read where it touches a black stroke
VAL_BLACK = 145
SAT_BLACK = 0.42

# The book divides its columns and underlines its running heads with thin red
# rules. A rule is ink, so it fills the gutter and hides the division between
# the columns. It is also not a word. Both layers are measured for rules, and
# the rules are set aside before anything is read.
RULE_LONG = 0.15      # of the page dimension it runs along
RULE_THIN = 0.004     # ink over length: a rule is 3 px of ink, type is 12
RULE_GAP = 9          # px: breaks in a rule closed before it is measured
RULE_DRIFT = 0.05     # how far across the page a rule may wander end to end


def render_page(pdf, page, dpi=300):
    """Render one PDF page to a PIL image."""
    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(tmp) / "p"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
             str(pdf), str(stem)],
            check=True, capture_output=True,
        )
        out = sorted(Path(tmp).glob("p*.png"))
        if not out:
            raise RuntimeError(f"page {page} of {pdf} did not render")
        return Image.open(out[0]).convert("RGB")


def longest_run(flags):
    """Longest contiguous True span, as (start, end).

    The page is one solid block of paper. First-to-last index would stretch the
    box around any bright speck out in the background.
    """
    best = cur = None
    for i, f in enumerate(flags):
        if f:
            cur = (i, i) if cur is None else (cur[0], i)
            if best is None or cur[1] - cur[0] > best[1] - best[0]:
                best = cur
        else:
            cur = None
    return best


def close_gaps(flags, max_gap):
    """Bridge short False gaps in a boolean run.

    The shadow in the fold of the book is dark enough to break the paper into
    two runs. Without this the crop keeps one page and throws the other away.
    """
    out = np.array(flags, dtype=bool)
    n = len(out)
    i = 0
    while i < n:
        if out[i]:
            i += 1
            continue
        j = i
        while j < n and not out[j]:
            j += 1
        if 0 < i and j < n and (j - i) <= max_gap:
            out[i:j] = True
        i = j
    return out


def crop_to_paper(img, bright=150, frac=0.25, pad=8, keep=()):
    """Trim the dark surround from a book photographed against a black cloth.

    keep names the sides to leave alone: "left", "right", "top", "bottom".
    The fold of the book is dark like the surround, but it is not surround.
    Trimming it takes the last letter of every line of the column beside it,
    because the inner margin of this book is narrow.
    """
    v = np.asarray(img).max(axis=2)
    lit = v > bright
    rows = longest_run(close_gaps(lit.mean(axis=1) > frac, int(img.height * 0.06)))
    cols = longest_run(close_gaps(lit.mean(axis=0) > frac, int(img.width * 0.10)))
    if rows is None or cols is None:
        return img
    t, b = max(0, rows[0] - pad), min(img.height, rows[1] + pad)
    l, r = max(0, cols[0] - pad), min(img.width, cols[1] + pad)
    if "top" in keep:
        t = 0
    if "bottom" in keep:
        b = img.height
    if "left" in keep:
        l = 0
    if "right" in keep:
        r = img.width
    return img.crop((l, t, r, b))


def grow(mask, px):
    """Widen a mask by px in every direction."""
    if px <= 0:
        return mask
    size = px * 2 + 1
    return ndimage.binary_dilation(mask, np.ones((size, size), bool))


def classify(img):
    """Return (red_mask, black_mask) boolean arrays for an RGB image."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    v = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(v > 0, (v - mn) / np.maximum(v, 1), 0.0)
    gb = np.maximum(g, b)
    black = (v < VAL_BLACK) & (sat < SAT_BLACK)
    red = (r > RED_MIN) & ((r - gb) > RED_MARGIN)
    # The warm rim of a black stroke can still pass both tests where the ink is
    # thin. It always touches the stroke it came from, and a rubric never does.
    red &= ~grow(black, HALO)
    return red, black


def longest_down(mask):
    """The longest unbroken run of True down each column of a mask."""
    run = np.zeros(mask.shape[1], dtype=np.int32)
    best = np.zeros(mask.shape[1], dtype=np.int32)
    for row in mask:
        run = np.where(row, run + 1, 0)
        np.maximum(best, run, out=best)
    return best


def furniture_columns(ink, min_frac=0.15):
    """True for each x that is furniture rather than type.

    Three things stand at the edges of these pages and none of them is type:
    the shadow in the fold of the book, the dark edge of the leaf, and the
    fore edge of the whole book block, which shows as pale vertical striations
    where the leaves beneath it stack up.

    All three run unbroken down the page. Type cannot: a letter is about a
    fiftieth of the height of the type block, and there is paper between every
    line. So the length of the longest unbroken run of ink tells them apart,
    and it does so whether the furniture is dark or pale.
    """
    return longest_down(ink) > ink.shape[0] * min_frac


def split_rules(mask, shape=None):
    """Separate the printed rules in a mask from the glyphs.

    Returns (rules, glyphs, boxes). A rule is one lump of ink that runs long
    and thin. Connected component labelling reads that straight off the page,
    where a profile cannot: a rule that stands in the gutter reads as the
    densest column on the page, not the emptiest.

    The rules of this book are one pixel of ink wide in places, so the scan
    breaks them into pieces. Each direction is therefore labelled on a copy
    that has its short gaps closed along that direction. The closing is
    smaller than the space between two lines of type, so it joins a broken
    rule without joining one line of type to the next.
    """
    H, W = shape or mask.shape
    rules = np.zeros_like(mask)
    boxes = []
    for direction, gap in (("tall", np.ones((RULE_GAP, 1), bool)),
                           ("flat", np.ones((1, RULE_GAP), bool))):
        lab, n = ndimage.label(ndimage.binary_closing(mask, gap))
        if n == 0:
            continue
        # Thickness is ink divided by length, not the width of the bounding
        # box. A page sits a fraction of a degree off square, so a rule 700 px
        # long drifts across 30 px of the page while staying 3 px thick.
        area = np.bincount(lab.ravel(), minlength=n + 1)
        for i, box in enumerate(ndimage.find_objects(lab), 1):
            if box is None:
                continue
            ys, xs = box
            h, w = ys.stop - ys.start, xs.stop - xs.start
            # Thin by ink, and also straight. Closing short gaps can chain a
            # trail of specks across half a page: sparse enough to pass a test
            # on thickness alone, and it would then be read as the gutter.
            if direction == "flat":
                if not (w > W * RULE_LONG and area[i] / w < H * RULE_THIN
                        and h < H * RULE_DRIFT):
                    continue
            elif not (h > H * RULE_LONG and area[i] / h < W * RULE_THIN
                      and w < W * RULE_DRIFT):
                continue
            # Only this lump of ink, not everything sharing its bounding box.
            rules[ys, xs] |= (lab[ys, xs] == i) & mask[ys, xs]
            boxes.append({"x": xs.start, "y": ys.start, "w": w, "h": h,
                          "dir": direction})
    return rules, mask & ~rules, boxes


def ink_mask(img):
    """A single boolean array of all ink, red and black together."""
    red, black = classify(img)
    return red | black


def is_spread(img):
    """True if the image holds two facing pages.

    A single breviary page is taller than it is wide. A spread is wider.
    """
    return img.width > img.height


def find_fold(img, band=0.12):
    """The x range of the whole shadow in the fold, as (start, end).

    The darkest column is a point inside the fold, not an edge of it. The
    shadow is tens of pixels wide and the inner margin of this book is narrow,
    so a cut at the darkest column takes the last letter off every line of the
    inner column. Measure the width of the shadow instead, and give all of it
    to both pages. It is dark, unbroken and easy to throw away later, and a
    letter thrown away here cannot be recovered at all.

    **Look only near the middle.** `band` was 0.30, which searches the middle
    30% of the spread, and that is wider than the fold can ever be. Where the
    fold shadow is faint — the Psalter came from a second machine and lies
    flat, with almost no shadow at all — the darkest column in so wide a window
    is a column of type, not the fold. The cut then lands 12 to 15 per cent off
    centre, one page loses its inner edge and the other keeps a stripe of its
    neighbour. That cost 26 spreads, 52 pages, and nothing downstream could see
    it: a page that lost its edge still reads as a healthy page.

    A spread of this book is two pages of equal width, so the fold is at the
    middle. Measured over 38 spreads, one from each part, narrowing the window
    to 0.12 moved the fold on two and moved it more than 5% on one, which was
    one of the broken ones. It repairs the failures and leaves the rest alone.
    """
    v = np.asarray(img).max(axis=2).astype(np.float32)
    col = v.mean(axis=0)
    mid = len(col) // 2
    half = int(len(col) * band / 2)
    lo, hi = max(1, mid - half), min(len(col) - 1, mid + half)
    x = lo + int(np.argmin(col[lo:hi]))
    # Halfway between the darkest point and the ordinary brightness of the
    # spread: dark enough to be shadow, bright enough not to be paper.
    edge = (col[x] + float(np.median(col))) / 2
    a = b = x
    while a > 0 and col[a - 1] < edge:
        a -= 1
    while b < len(col) - 1 and col[b + 1] < edge:
        b += 1
    return a, b


def find_gutter(img, band=0.30):
    """Column index of the middle of the fold between the two pages."""
    a, b = find_fold(img, band)
    return (a + b) // 2


def split_spread(img, pad_frac=0.012):
    """Cut a spread into a list of single pages, left first.

    The two pages overlap a little at the fold. The darkest column is a good
    guess at the fold, but it is only a guess, and a guess that lands a few
    pixels to one side would cut into type. An overlap costs a sliver of the
    facing page, which is nothing; a cut costs letters.
    """
    if not is_spread(img):
        return [img]
    a, b = find_fold(img)
    pad = int(img.width * pad_frac)
    left = img.crop((0, 0, min(img.width, b + pad), img.height))
    right = img.crop((max(0, a - pad), 0, img.width, img.height))
    return [left, right]


def deskew(img, limit=3.0, step=0.25):
    """Rotate the page so the lines of type run level.

    Straight lines of text make the row ink totals rise and fall sharply. We
    try small angles and keep the one with the sharpest profile.
    """
    small = img.copy()
    small.thumbnail((700, 700))
    mask = ink_mask(small).astype(np.float32)
    if mask.sum() < 50:
        return img

    best_angle, best_score = 0.0, -1.0
    angle = -limit
    while angle <= limit:
        rot = mask if angle == 0 else np.asarray(
            Image.fromarray((mask * 255).astype(np.uint8)).rotate(
                angle, resample=Image.BILINEAR, fillcolor=0)
        ).astype(np.float32) / 255.0
        profile = rot.sum(axis=1)
        score = float(np.diff(profile).__pow__(2).sum())
        if score > best_score:
            best_score, best_angle = score, angle
        angle += step

    if abs(best_angle) < step / 2:
        return img
    return img.rotate(best_angle, resample=Image.BICUBIC, fillcolor=(255, 255, 255))


# A few pages this book's own deskew leaves crooked. It is a list and not a
# rule: turning every page by what a finer search asks for makes the book
# worse. `turn.txt` beside the drafts says why, and holds the measurements.
TURNS = Path(__file__).resolve().parent.parent / "turn.txt"


@functools.lru_cache(maxsize=1)
def extra_turns():
    """How much further each named page must turn, in degrees."""
    out = {}
    if TURNS.exists():
        for line in TURNS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                bits = line.split()
                if len(bits) == 2:
                    try:
                        out[bits[0]] = float(bits[1])
                    except ValueError:
                        pass
    return out


def turn_further(img, stem):
    """Turn one page by the angle `turn.txt` names for it, if any."""
    deg = extra_turns().get(stem)
    if not deg:
        return img
    return img.rotate(deg, resample=Image.BICUBIC, fillcolor=(255, 255, 255))


def prepare_page(img):
    """Full clean up for one rendered scan: crop, split, straighten."""
    pages = split_spread(crop_to_paper(img))
    if len(pages) == 1:
        return [deskew(crop_to_paper(pages[0]))]
    # The fold side of each page keeps its shadow. See crop_to_paper.
    left, right = pages
    return [deskew(crop_to_paper(left, keep=("right",))),
            deskew(crop_to_paper(right, keep=("left",)))]
