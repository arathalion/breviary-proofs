#!/usr/bin/env python3
"""Infer the block structure of a page from a draft reading.

Usage:
    structure.py <draft.json> <page.png> [-o out.md]

The colour split is automatic, but a breviary page carries more structure than
colour alone: centred headings, psalm and lesson titles, antiphon labels, drop
capitals and dividing rules. This tool guesses those from two signals that do
not depend on each other.

  Geometry  A heading sits centred in its column. A drop capital is about
            twice the height of the type around it. A rule is one long run of
            ink on a row that holds nothing else.
  Wording   A psalm title reads "Psalm 94". An antiphon label reads "Ant. 7".

Where the two agree the guess is safe. Everything it cannot place stays plain
text or plain rubric, which is the harmless answer.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pagelib

HOURS = {"MATINS", "LAUDS", "PRIME", "TERCE", "SEXT", "NONE",
         "VESPERS", "COMPLINE"}
RE_ANT = re.compile(r"^Ant\.?\s*(\d+)?\b", re.I)
RE_TAGLIKE = re.compile(r"^\.[A-Za-z]")
# Every tag this tool writes. Anything else that looks like one is a line of
# the book that happens to start with a full stop.
TAGS = {"text", "rubric", "open", "rule", "bheading", "heading", "hour",
        "lesson", "psalm", "ant", "mark", "day", "widerubric", "vers", "resp"}


def is_tag(line):
    return line[1:].split(" ", 1)[0] in TAGS

# Letters and digits the engine trades for one another in this type.
CONFUSED = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B",
                          "l": "I", "|": "I"})
# The same confusions read the other way, for recovering a psalm number.
TO_DIGIT = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1",
                          "S": "5", "B": "8"})


def edits(a, b, cap=2):
    """Edit distance between two short words, given up as soon as it exceeds cap.

    A strict pattern loses a whole title to one misread character, and that is
    how "Psalm 94" was found once in seventeen pages. Matching the keyword
    loosely, while still demanding a number beside it, recovers those without
    letting ordinary prose through.
    """
    a, b = a.lower(), b.lower()
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def keyed(text, word, cap=2):
    """Split "Psalm 94" into its keyword and the rest, allowing misreadings."""
    parts = text.strip().rstrip(".:").split()
    if len(parts) < 2:
        return None
    if edits(parts[0].strip(".").translate(CONFUSED), word, cap) > cap:
        return None
    return " ".join(parts[1:])


def as_hour(text):
    """Match an hour name even when a letter came back wrong."""
    t = text.strip().rstrip(".:").translate(CONFUSED)
    if not t or len(t.split()) > 1 or not t.isupper():
        return None
    for h in HOURS:
        if edits(t, h, 1) <= 1:
            return h
    return None

CENTRE_TOL = 0.28   # how evenly a line must sit to count as centred


def as_mark(token, conf=None):
    """Recover a versicle or response mark from what the engine read.

    No OCR engine knows the glyphs at U+2123 and U+211F, so it returns junk
    such as "©" or "R7". These marks open a great many lines, so it is worth
    recovering them. A real word is never treated as a mark: the token must be
    a single character, or must mix letters with something that is not a
    letter, and the common one letter words are excluded outright.
    """
    t = token.strip().strip(".")
    if not t or len(t) > 3:
        return None
    # A person can put a mark in by hand, in the proof sheet, and the sheet
    # writes the true glyph. Take that as certain: the tests below look for
    # the junk an engine returns, and the true glyph is not junk.
    if "℟" in t:
        return "<R>"
    if "℣" in t:
        return "<V>"
    if t.upper() in {"A", "I", "O"}:
        return None
    if len(t) > 1 and t.isalpha():
        # Two letters and nothing else is usually a word, and "by" and "my"
        # would otherwise become marks, because one holds a B and the other a
        # Y. But the engine also returns "RR", "KX" and "yy" for these glyphs,
        # and Max had to put four of those right by hand in four pages.
        #
        # Confidence tells them apart, and nothing else does. A real two letter
        # word is read easily and scores high. A glyph no engine knows scores
        # 8, 18, 50. So let this shape through only where the engine itself
        # says it could not read it.
        if conf is None or conf >= 60:
            return None
    if re.search(r"[RKB]", t, re.I):
        return "<R>"
    if re.search(r"[VY©¥]", t, re.I):
        return "<V>"
    return None


def group_lines(words, gap=0.6):
    """Cluster words into lines of type by their vertical position."""
    if not words:
        return []
    heights = sorted(w["h"] for w in words)
    med = heights[len(heights) // 2] or 1
    lines, current = [], []
    for w in sorted(words, key=lambda w: (w["y"], w["x"])):
        if current and abs(w["y"] - current[0]["y"]) > med * gap:
            lines.append(current)
            current = []
        current.append(w)
    if current:
        lines.append(current)
    for ln in lines:
        ln.sort(key=lambda w: w["x"])
    return lines


def find_rules(img, x0, x1):
    """Rows that hold a dividing rule, as (y, colour).

    A rule is one unbroken run of ink. A line of type is many short runs, so
    the ratio of the longest run to the total ink on the row separates them.
    """
    red, black = pagelib.classify(img)
    out = []
    for colour, mask in (("red", red), ("black", black)):
        band = mask[:, x0:x1]
        w = band.shape[1]
        for y in range(band.shape[0]):
            row = band[y]
            total = int(row.sum())
            if total < w * 0.15:
                continue
            best = run = 0
            for v in row:
                run = run + 1 if v else 0
                best = max(best, run)
            if best > w * 0.15 and best > total * 0.85:
                out.append((y, colour))
    # Collapse the two or three rows of one rule into a single entry.
    #
    # Across colours as well, which it did not do. The rims of a black rule
    # are warm, so the same printed rule is found once in the black layer and
    # again in the red, four rows apart, and the page then carries ".rule
    # black" followed by ".rule". Both consume space and both break the
    # paragraph. One printed rule is one rule, whatever colour it was found in.
    merged = []
    for y, c in sorted(out):
        if merged and y - merged[-1][0] <= 6:
            continue
        merged.append((y, c))
    return merged


def find_dropcaps(img, x0, x1, med_h):
    """Locate the drop capitals in a column by their shape on the page.

    Asking the OCR engine does not work. It merges a large initial into the
    word beside it, or misreads it, so only one was ever found. A drop capital
    is easy to see instead: one lump of ink about two lines tall, sitting hard
    against the left edge of the column, and wide enough not to be a stem or a
    rule. That is a measurement of tens of pixels, which these scans support.
    """
    from scipy import ndimage

    red, black = pagelib.classify(img)
    width = x1 - x0
    found = []
    for colour, mask in (("red", red), ("black", black)):
        band = mask[:, x0:x1]
        labels, count = ndimage.label(band)
        if not count:
            continue
        for sl in ndimage.find_objects(labels):
            ys, xs = sl
            h, w = ys.stop - ys.start, xs.stop - xs.start
            if not (med_h * 2.0 <= h <= med_h * 5.0):
                continue
            if w < med_h * 0.7 or w > width * 0.35:
                continue
            if xs.start > width * 0.18:      # must open the column, not sit in it
                continue
            found.append({"y": int(ys.start), "colour": colour,
                          "box": (x0 + int(xs.start), int(ys.start), w, h)})
    found.sort(key=lambda d: d["y"])
    # two colours can both claim one blob; keep the first of any close pair
    merged = []
    for d in found:
        if merged and d["y"] - merged[-1]["y"] < med_h:
            continue
        merged.append(d)
    return merged


def read_letter(img, box):
    """Read the single letter of a drop capital, which the page text lacks."""
    import subprocess
    import tempfile

    x, y, w, h = box
    crop = img.crop((max(0, x - 3), max(0, y - 3), x + w + 3, y + h + 3))
    crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "cap.png"
        crop.save(p)
        out = subprocess.run(
            ["tesseract", str(p), "stdout", "--psm", "10", "-l", "eng"],
            capture_output=True, text=True).stdout.strip()
    letters = [c for c in out if c.isalpha()]
    return letters[0].upper() if letters else ""


def classify_line(line, text, layer, left, right, med_h, clearing=1.0):
    """Return a block tag for one line, or None to leave it as running text.

    `clearing` is how much vertical space surrounds the line, against the
    normal leading of the column. A heading sits in a clearing; body text sits
    on an even grid. That measurement spans tens of pixels, so unlike the
    weight of the strokes it is reliable at the resolution of these scans.
    """
    x0 = min(w["x"] for w in line)
    x1 = max(w["x"] + w["w"] for w in line)
    width = right - left
    lead, trail = x0 - left, right - x1
    short = (x1 - x0) < width * 0.85
    offcentre = abs(lead - trail) / width if width else 1.0
    centred = short and offcentre < CENTRE_TOL and lead > width * 0.04

    rest = keyed(text, "psalm")
    if rest:
        num = re.sub(r"\D", "", rest.translate(TO_DIGIT))
        if num:
            return ("psalm", num)

    rest = keyed(text, "lesson")
    if rest and re.fullmatch(r"[ivxlcIVXLC1|]{1,6}\.?", rest):
        return ("lesson", rest.rstrip(".").translate(CONFUSED).lower())

    parts = text.strip().rstrip(".:").split()
    if len(parts) == 2 and edits(parts[1], "nocturn", 2) <= 2:
        return ("bheading", text.strip())

    if layer == "red":
        m = RE_ANT.match(text)
        if m and m.group(1):
            return ("ant", m.group(1))

    hour = as_hour(text)
    if hour:
        return ("hour", hour)

    # There was a rule here that called a line a drop capital when its first
    # token was tall and one or two characters long. It was wrong: the height
    # of a word box depends on whether the word has an ascender or a descender,
    # and a versicle mark is one or two characters of junk with an odd height.
    # It fired six times on the median page and thirty seven times on the worst,
    # where the book sets one or two, and it ate the marks it misread.
    #
    # Drop capitals are found by shape instead, in find_dropcaps, which reads
    # them off the page as lumps of ink two lines tall against the left edge of
    # a column. Asking the engine about a shape is the mistake this whole tool
    # exists to avoid.

    # A heading is short, sits square in the column, and stands in a clearing.
    # A versicle is short and indented too, so centring alone is not enough:
    # that test alone produced five false headings on one page. Requiring the
    # clearing as well separates them. Thresholds are deliberately tight,
    # because a missed heading is harmless plain text while a false one
    # corrupts what a reader would say aloud.
    if (short and clearing >= 1.45 and offcentre <= 0.20
            and len(text.split()) <= 8
            and not text.rstrip().endswith((".", ":", ";", ","))):
        return ("heading" if layer == "red" else "bheading", text)
    return None


def table_cuts(src, fixes):
    """Where a person put the column guides on this page, in pixels later.

    Held as a fraction of the width of the scan, because the proof sheet shows
    the scan at whatever size the window allows. Nothing here guesses: six
    attempts to find the columns of a page by measurement have failed on this
    book, and reading a column on its own scores worse than reading the page.
    """
    rec = Path(fixes) / f"{src}.json"
    if not rec.exists():
        return [], 0.0
    try:
        held = json.loads(rec.read_text(encoding="utf-8"))
        return sorted(held.get("cols", [])), float(held.get("lean") or 0)
    except (ValueError, TypeError, OSError):
        return [], 0.0


# The book prints none of these, so a cell holding only them holds nothing.
# The fold of the leaf reads as a run of them, and that is exactly the column
# this has to see through. Kept in step with `RE_STRAY` in `proof.py`.
RE_NOT_STRAY = re.compile(r"[^|\\{}~_=<>\s]")


def as_table(words, cuts, med_h, width, lean=0.0):
    """Lay the words of a page into rows and cells, as the sheet lays them.

    One row is not one line. On a calendar the day number stands once and the
    feast beside it runs on for three lines, so the widest column is the one
    that runs on: a line putting ink anywhere to its left opens a row, and a
    line that does not is the rest of the row above. This must agree with
    `buildGrid` in `proof.py`, or the printed table and the proof sheet
    disagree about the book.
    """
    # A guide is a fraction of the width of the scan, because that is what a
    # person sees in the proof sheet and clicks on. Measuring it against the
    # rightmost word instead would move every column on a page whose type does
    # not reach the edge, and the sheet and the printed table would disagree.
    edges = [0] + [c * width for c in cuts] + [width]
    widths = [(edges[i + 1] - edges[i]) / width for i in range(len(edges) - 1)]
    key = max(range(len(widths)), key=lambda i: widths[i])

    # The columns of this book lean on the scan even where the rows are level,
    # by as much as 2.55 degrees on a calendar page, which is 51 px of drift
    # from the top of the leaf to the bottom. A person leans the guides in the
    # proof sheet and the lean arrives here. `buildGrid` in `proof.py` must do
    # the same arithmetic, or the sheet and the printed table disagree.
    t = math.tan(math.radians(lean))
    mid_y = (min(w["y"] for w in words) + max(w["y"] for w in words)) / 2

    def cell_of(w):
        mid = w["x"] + w["w"] / 2 - t * (mid_y - w["y"])
        return sum(1 for e in edges[1:-1] if mid >= e)

    lines = []
    for w in sorted(words, key=lambda w: (w["y"], w["x"])):
        if lines and abs(w["y"] - lines[-1][0]["y"]) <= med_h * 0.6:
            lines[-1].append(w)
        else:
            lines.append([w])

    rows = []
    for line in lines:
        cells = [[] for _ in widths]
        for w in sorted(line, key=lambda w: w["x"]):
            cells[cell_of(w)].append(w["t"])
        # A line opens a row unless everything it holds is in the column that
        # runs on. Looking only to the LEFT of that column was wrong: where
        # the widest column comes early, everything left of it is the margin
        # of the leaf, no line ever opens, and the whole page collapses into
        # one row. Max hit that on the table of the movable feasts.
        if any(c for i, c in enumerate(cells) if i != key) or not rows:
            rows.append(cells)
        else:
            for i, c in enumerate(cells):
                rows[-1][i].extend(c)
    # The fold of the book and the edge of the leaf beside it stand inside the
    # scan, so the last column of a table can be the next page showing at the
    # edge rather than a column at all. Max saw this on the calendar on
    # 2026-08-17. A column that is empty on every row of the page is not a
    # column: it goes, and its width goes to the one beside it.
    # A column that is mostly stray ink is not a column of the table. At the
    # fold it is the next leaf showing at the edge of the scan: on the first
    # calendar page that band held 20 tokens, every one a single character and
    # 12 of them a bar, against none in the real letter column beside it.
    keep = []
    for i in range(len(widths)):
        ts = [t for r in rows for t in r[i] if t.strip()]
        if not ts:
            continue
        stray = sum(1 for t in ts if not RE_NOT_STRAY.search(t))
        if stray * 2 <= len(ts):
            keep.append(i)
    if keep and len(keep) < len(widths):
        spare = sum(widths) - sum(widths[i] for i in keep)
        rows = [[r[i] for i in keep] for r in rows]
        widths = [widths[i] for i in keep]
        widths[-1] += spare

    # A cell is separated by a bar, and the book prints no bar on any page, so
    # any that survives here is stray ink and comes out.
    return ([" | ".join(" ".join(c).replace("|", "").strip() for c in r).rstrip(" |")
             for r in rows], widths)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("page")
    ap.add_argument("-o", "--out")
    ap.add_argument("--fixes", default=str(Path(__file__).resolve().parent.parent
                                           / "structfix"))
    args = ap.parse_args()

    data = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    img = Image.open(args.page).convert("RGB")

    bycol = {}
    for b in data["blocks"]:
        bycol.setdefault(b["column"], []).append(b)

    all_words = [w for b in data["blocks"] for w in b["words"]]
    if not all_words:
        print("empty draft", file=sys.stderr)
        return
    hs = sorted(w["h"] for w in all_words)
    med_h = hs[len(hs) // 2] or 1

    out = [f"#src {data['src']}", ""]
    counts = {}

    # A page the book sets as a grid is not lines of prose, and none of the
    # rules below apply to it. Where a person has placed the columns in the
    # proof sheet, the words go into cells instead. See `as_table`.
    cuts, lean = table_cuts(data["src"], args.fixes)
    if cuts:
        rows, widths = as_table(all_words, cuts, med_h, img.width, lean)
        out.append(".table " + " ".join(f"{w:.4f}" for w in widths))
        out.extend(rows)
        counts["table"] = len(rows)
        body = "\n".join(out) + "\n"
        if args.out:
            Path(args.out).write_text(body, encoding="utf-8")
        else:
            print(body)
        print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())),
              file=sys.stderr)
        return
    for n in sorted(bycol):
        words = [w for b in bycol[n] for w in b["words"]]
        left = min(w["x"] for w in words)
        right = max(w["x"] + w["w"] for w in words)
        # A rule outside the type is furniture, not content. The printer drew
        # one under the running head and the scan carries the edge of the leaf,
        # and both stand clear above the first line. Reproducing them costs a
        # rule's worth of space and a paragraph break on every page: parts 13,
        # 16 and 17 carried four to five rules to a page where the book draws
        # one, and ran 22 to 29 per cent long because of it. The class sets its
        # own running head, so the printed one must not come through as body.
        ytop = min(w["y"] for w in words)
        ybot = max(w["y"] + w["h"] for w in words)
        margin = med_h * 1.5
        rules = {y: c for y, c in find_rules(img, left, right)
                 if ytop - margin <= y <= ybot + margin}
        rule_ys = sorted(rules)
        caps, cap_i = find_dropcaps(img, left, right, med_h), 0

        # Flatten the blocks into one ordered run of lines. The versicle mark
        # is red and the words after it are black, so the two sit in separate
        # blocks. Only a flat run lets a mark reach the line it belongs to.
        items = []
        for b in bycol[n]:
            for line in group_lines(b["words"]):
                items.append({"layer": b["layer"], "line": line,
                              "text": " ".join(w["t"] for w in line),
                              "y": min(w["y"] for w in line)})

        # How far apart the lines normally sit in this column. A heading is
        # measured against this, not against a fixed number of pixels.
        gaps = [items[i + 1]["y"] - items[i]["y"] for i in range(len(items) - 1)]
        leading = sorted(gaps)[len(gaps) // 2] if gaps else 1
        leading = max(leading, 1)

        current, pending = None, ""
        body = False        # did the last thing emitted end a line of the book
        for i, item in enumerate(items):
            line, text, layer = item["line"], item["text"], item["layer"]
            up = item["y"] - items[i - 1]["y"] if i > 0 else leading
            down = items[i + 1]["y"] - item["y"] if i < len(items) - 1 else leading
            clearing = (up + down) / (2 * leading)

            # emit any rule that falls above this line
            while rule_ys and rule_ys[0] < item["y"]:
                body = False
                ry = rule_ys.pop(0)
                out.append(".rule black" if rules[ry] == "black" else ".rule")
                counts["rule"] = counts.get("rule", 0) + 1
                current = None

            # A red line holding nothing but a mark belongs to the line below.
            if layer == "red" and len(line) == 1 and i + 1 < len(items):
                mark = as_mark(line[0]["t"], line[0].get("conf"))
                if mark and items[i + 1]["layer"] == "black":
                    pending = mark + " "
                    counts["mark"] = counts.get("mark", 0) + 1
                    continue

            # A drop capital found on the page belongs to the line beside it.
            # The engine did not read the letter, so supply it here.
            while cap_i < len(caps) and caps[cap_i]["y"] < item["y"] - med_h * 1.5:
                cap_i += 1
            if (cap_i < len(caps)
                    and abs(caps[cap_i]["y"] - item["y"]) <= med_h * 1.5
                    and len(line) > 1):
                cap = caps[cap_i]
                cap_i += 1
                letter = read_letter(img, cap["box"])
                counts["open"] = counts.get("open", 0) + 1
                out.append(".open red" if cap["colour"] == "red" else ".open")
                if letter and not text.upper().startswith(letter):
                    text = letter + text
                out.append(pending + text)
                current, pending = None, ""
                continue

            tag = classify_line(line, text, layer, left, right, med_h, clearing)
            if tag:
                kind, val = tag
                counts[kind] = counts.get(kind, 0) + 1
                if kind == "open":
                    out.append(f".open {val}".rstrip())
                    current, pending = "open", ""
                    continue
                if kind == "ant":
                    out.append(f".ant {val}")
                    rest = text[RE_ANT.match(text).end():].strip()
                    if rest:
                        out.append(rest)
                    current, pending = None, ""
                    continue
                out.append(f".{kind} {val}".rstrip())
                current, pending, body = None, "", False
                continue

            inline_mark = as_mark(line[0]["t"], line[0].get("conf")) if len(line) > 1 else None
            if inline_mark:
                text = inline_mark + " " + " ".join(w["t"] for w in line[1:])
                counts["mark"] = counts.get("mark", 0) + 1

            # One printed line, two ink colours. The book sets a red versicle
            # mark, a red "Ant." or a red chapter reference inside a black line
            # and goes straight on. The reading splits those into two blocks,
            # because the colour split happens per pixel and knows nothing
            # about lines.
            #
            # Emitting a block as a paragraph is right while a block is a
            # paragraph. It is wrong the moment two blocks share a printed
            # line, and then every inline mark breaks the paragraph. The parts
            # thick with short rubrics carried 35 blocks to a page against 20
            # elsewhere, and ran 18 to 25 per cent long entirely on that.
            #
            # So join them, and switch colour inside the line instead. A brace
            # pair means "the other colour" in this markup, which totex.inline
            # already sets.
            want = "rubric" if layer == "red" else "text"
            same = (body and i > 0
                    and abs(item["y"] - items[i - 1]["y"]) <= med_h * 0.5)
            if same:
                seg = text if want == current else "{" + text + "}"
                out[-1] = out[-1] + " " + pending + seg
            else:
                if current != want:
                    out.append(f".{want}")
                    current = want
                out.append(pending + text)
            pending = ""
            body = True

    # A line of the book can begin with a full stop, because the engine reads
    # the remains of a drop capital or a broken word that way, and a line that
    # begins with a full stop is a tag in this markup. Twelve lines of the book
    # turned into tags called .troyed and .omeness before this. One space in
    # front settles it: the markup ignores leading space, and a tag must stand
    # at the start of its line.
    out = [f" {line}" if RE_TAGLIKE.match(line) and not is_tag(line) else line
           for line in out]
    body = "\n".join(out) + "\n"
    # `as_mark` looks at the first token of a line only, because that is where
    # the book puts these marks and because it must not mistake a word for
    # one. A mark that a person typed stands wherever they put it, and the
    # glyph is certain, so take it anywhere.
    body = body.replace("℟", "<R>").replace("℣", "<V>")
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
    else:
        print(body)
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())),
          file=sys.stderr)


if __name__ == "__main__":
    main()
