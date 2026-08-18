#!/usr/bin/env python3
"""Read an image with Tesseract and keep the geometry.

Ask the engine for TSV, never for plain text. TSV carries twelve fields for
every word: which block, paragraph and line it belongs to, a bounding box, and
a confidence. Plain text throws all of that away, and none of it can be
recovered afterwards.

Two things depend on it.

**Confidence marks the words a person must check.** A dictionary test cannot
do this. It passes any real word, so it is blind to a word the engine read
wrongly into another real word. On this book that is most of what is left.

**Boxes join the reading to anything else measured off the page.** Whatever
the page carries that the engine cannot report — colour, italic, a rule, a
drop capital — is found by measuring the image, and the result must then be
attached to the right line of type. A box does that. A line number does not.

This file has no book in it. Any project that reads a scanned page can take it
as it stands.
"""
import subprocess
from pathlib import Path

# level page block par line word left top width height conf text
NFIELDS = 12
BLOCK, PAR, LINE = 2, 3, 4
LEFT, TOP, WIDTH, HEIGHT, CONF, TEXT = 6, 7, 8, 9, 10, 11


def read_words(path, lang="eng", psm="6", scale=1, pad=0, extra=()):
    """Read one image and return its lines of type.

    Each line is `{text, words, y, top, bot}`. Each word is
    `{t, conf, x, y, w, h}`, in the coordinates of the original image:
    `scale` and `pad` undo any enlargement or border added before the read, so
    that a box still indexes the picture it came from.

    Returns an empty list when the image holds no type. A caller that treats
    that as success will hide unread pages inside a run that reports none, so
    test the result.
    """
    out = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", str(psm), "-l", lang,
         *extra, "tsv"],
        capture_output=True, text=True,
    )
    lines, current = [], None
    for row in out.stdout.splitlines()[1:]:
        f = row.split("\t")
        if len(f) < NFIELDS or f[TEXT].strip() == "":
            continue
        try:
            conf = float(f[CONF])
        except ValueError:
            continue
        word = {
            "t": f[TEXT], "conf": conf,
            "x": int(f[LEFT]) // scale - pad, "y": int(f[TOP]) // scale - pad,
            "w": int(f[WIDTH]) // scale, "h": int(f[HEIGHT]) // scale,
        }
        key = (f[BLOCK], f[PAR], f[LINE])
        if key != current:
            lines.append({"words": []})
            current = key
        lines[-1]["words"].append(word)

    for line in lines:
        line["text"] = " ".join(w["t"] for w in line["words"])
        # The vertical extent of the line. `y` is the top edge, kept under its
        # old name because the reading order is built on it.
        line["y"] = line["top"] = min(w["y"] for w in line["words"])
        line["bot"] = max(w["y"] + w["h"] for w in line["words"])
    return lines


def read_image(img, tmp, tag, **kw):
    """The same, for an image held in memory. Writes it out first."""
    path = Path(tmp) / f"{tag}.png"
    img.save(path)
    return read_words(path, **kw)


def band_of(line, bands):
    """Index of the band of ink that holds this line, or None.

    `bands` is a list of `(top, bottom)` pairs measured off the image, in the
    same coordinates as the line. Use this to attach anything measured per
    band — an italic angle, an ink colour, a stave — to the words the engine
    read.

    Match on the centre of the line, not on the area the two share. A word box
    is as tall as its ascenders and descenders, so it always stands taller
    than the band of ink inside it, and an area test punishes a correct match
    for that. Measured over 962 lines of a Sarum Missal: centre joins 99.5% of
    lines, area over half joins 91%.

    Never match by counting instead. The engine and the image never agree on
    how many lines a region holds: the engine drops what it cannot read and
    merges what sits close, and the image counts every band of ink. Pairing
    them in order joined 68% of regions in the same test, and every line after
    the first disagreement was wrong. That fault is silent, because a shifted
    line is still a real line.
    """
    mid = (line["top"] + line["bot"]) / 2
    for i, (a, b) in enumerate(bands):
        if a <= mid <= b:
            return i
    return None
