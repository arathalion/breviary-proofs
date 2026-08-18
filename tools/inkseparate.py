#!/usr/bin/env python3
"""Separate the red rubrics from the black text of a scanned breviary page.

In a breviary the ink colour carries meaning: black is what you say, red is the
rubric telling you how and when to say it. Ordinary OCR throws that away, so we
split the scan into two layers up front and OCR each one separately. Each layer
comes back as clean black-on-white, which is also what Tesseract likes best.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pagelib import classify        # noqa: F401  one definition, in pagelib


def crop_to_paper(img, bright=150, frac=0.25, pad=8):
    """Trim the dark surround from a book photographed against a black cloth.

    Without this the background reads as one enormous blob of black ink.
    A row or column belongs to the page when a quarter of it is bright paper.
    """
    v = np.asarray(img.convert("RGB")).max(axis=2)
    lit = v > bright
    rows = longest_run(lit.mean(axis=1) > frac)
    cols = longest_run(lit.mean(axis=0) > frac)
    if rows is None or cols is None:
        return img
    t, b = max(0, rows[0] - pad), min(img.height, rows[1] + pad)
    l, r = max(0, cols[0] - pad), min(img.width, cols[1] + pad)
    return img.crop((l, t, r, b))


def longest_run(flags):
    """Longest contiguous True span, as (start, end).

    The page is one solid block of paper. Taking first-to-last index instead
    would stretch the box around any bright speck out in the background.
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


def render(mask, shape):
    """Paint a mask as black ink on a white page."""
    out = np.full(shape, 255, dtype=np.uint8)
    out[mask] = 0
    return Image.fromarray(out)


def main(src, stem):
    img = crop_to_paper(Image.open(src))
    red, black = classify(img)
    shape = red.shape
    total = red.size

    render(black, shape).save(f"{stem}-black.png")
    render(red, shape).save(f"{stem}-red.png")
    # Both layers together, to eyeball that nothing was dropped on the floor.
    render(red | black, shape).save(f"{stem}-ink.png")

    print(f"{src}  {shape[1]}x{shape[0]}")
    print(f"  black ink : {black.sum()/total:6.2%} of page")
    print(f"  red ink   : {red.sum()/total:6.2%} of page")
    print(f"  paper     : {1-(red|black).sum()/total:6.2%}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
