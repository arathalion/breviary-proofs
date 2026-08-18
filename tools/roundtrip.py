#!/usr/bin/env python3
"""Read the built PDF back and check that every word of the source reached it.

Usage:
    roundtrip.py                          every part in tex/parts
    roundtrip.py 26-Common-of-a-Virgin    one part
    roundtrip.py --show 20                list the worst mismatches

Nothing else in this chain reads the PDF. `compile-all.log` records that
LuaLaTeX exited 0, which proves the run finished and nothing more. A dropped
rubric, a swallowed paragraph or a macro that eats its argument all compile
perfectly and set a book that is missing text. That fault is silent, and every
silent fault on this project has cost a night.

Two checks, because one is not enough.

**Content**, as a word multiset. Order changes legitimately: the class sets two
columns and moves the running head. Which words are there, and how many times,
must not change.

**Order**, over the headings. A multiset cannot see a transposition. If two
antiphons exchanged places the multiset is identical and the check passes, and
nothing downstream notices either, because both are well formed. In a
liturgical book that is the worse fault: a missing word is visible to anyone
reading, and a prayer under the wrong day is visible only to someone who knows
which prayer belongs there.

This diffs the markup against the PDF, not the `.tex` against the PDF. The
`.tex` carries `\\documentclass`, `\\begin{multicols}` and `\\input`, whose
arguments read as words and have to be stripped before any generic macro pass.
Going from the markup skips that class of false failure entirely.
"""
import argparse
import re
import subprocess
import sys
import difflib
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Macros that print a word the markup never held. See breviary.cls:
#   \psalmhead{44} -> "Psalm 44"   \lesson{ix} -> "Lesson ix"
#   \ant{...}      -> "Ant. ..."
# The word is added to the source side, not forgiven on the PDF side, so that
# a real loss of one of these words still shows.
ADDS_A_WORD = {"psalm": "psalm", "lesson": "lesson", "ant": "ant"}

# Written in the markup, set as a glyph. `<V>` would otherwise count as the
# word "v" on the source side and as nothing on the page.
RE_MARKUP_MARK = re.compile(r"<[VR*?]>")

# Tags whose line is a heading. Their order is what the order check follows.
HEADINGS = ("heading", "bheading", "hour", "day", "psalm", "lesson")

RE_TAG = re.compile(r"^\s*\.([a-z]+)\b ?(.*)$")
RE_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)


def norm(text):
    """Fold everything that typesetting is allowed to change.

    NFKD does the heavy lifting. `pdftotext` returns presentation ligatures as
    their own codepoints — U+FB01 for fi, U+FB00 for ff — so a source word and
    a correct page disagree without it. In a liturgical book that is a large
    share of the words. Decomposing also strips accents, which is wanted here
    for the same reason.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("—", "-"), ("–", "-"), ("æ", "ae"), ("œ", "oe")):
        text = text.replace(a, b)
    # Marks are glyphs, not words: versicle, response, and the psalm asterisk.
    for c in "℣℟∗*·":
        text = text.replace(c, " ")
    return text.lower()


def dehyphenate(text):
    """Join a word that a line break split.

    Both sides get this. LaTeX hyphenates to fill a 46 mm column, and the book
    itself hyphenates to fill its own, so the reading carries the book's breaks
    too. A source that a person typed would need this on the output side only.

    The newline is required. A pattern that joins any hyphen merges a genuine
    compound, and that fault is quieter than the one it fixes.
    """
    return re.sub(r"(?<=[^\W\d_])-\s*\n\s*(?=[^\W\d_])", "", text)


def words(text):
    return RE_WORD.findall(norm(dehyphenate(text)))


def read_markup(part, struct):
    """Every word the markup holds, and the headings in the order they stand.

    A tag names what a line is. The tag itself is not on the page; its
    argument is text of the book and counts.

    A drop capital is split here the way `totex.dropcap` splits it, because
    `lettrine` sets the initial as its own text object and `pdftotext` returns
    it as a separate word. The engine often joins the initial to the word
    beside it, so the markup holds "Iwill" where the page holds "I" and
    "will". Splitting the source the same way makes both sides agree by
    construction rather than by forgiveness.
    """
    seq, heads, npages = [], [], 0
    for page in sorted(struct.glob(f"{part}-*.md")):
        npages += 1
        opening, body_lines = False, []
        for line in page.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):          # `#src <page>`, a comment
                continue
            m = RE_TAG.match(line)
            if m:
                tag, val = m.group(1), m.group(2)
                if tag == "rule":
                    continue
                if tag in ADDS_A_WORD:
                    seq.append(ADDS_A_WORD[tag])
                if tag in HEADINGS and val.strip():
                    # A heading of one short token is usually the engine
                    # misreading a mark or a folio number. Ordering on those
                    # reports a move on every page and hides a real one.
                    w = words(val)
                    if len(w) > 1 or (w and len(w[0]) > 3):
                        heads.append(w)
                opening = tag == "open"
                # `.open` takes a colour, not text. Its argument is not on the
                # page and must not be counted as a word of the book.
                line = "" if tag == "open" else val
            elif opening:
                # Nothing to do. `lettrine` sets the initial as its own text
                # object, but -raw returns it joined to the word beside it,
                # which is how the markup already holds it. Splitting the
                # source here was right for positional extraction and is wrong
                # for this one.
                opening = False
            body_lines.append(RE_MARKUP_MARK.sub(
                " ", line.replace("{", " ").replace("}", " ")))
        # Count the page as one text, not line by line. The book breaks a word
        # across its own lines and the reading carries the break, so "com-" and
        # "panions" stand on separate lines of the markup and are one word on
        # the page. `dehyphenate` needs the newline between them to see it, and
        # a line handed over on its own has no newline at all.
        seq.extend(words("\n".join(body_lines)))
    return seq, heads, npages


def read_pdf(pdf):
    """Every word the built PDF puts on paper, in order, minus the furniture.

    The running head cannot be balanced by counting: `\\markboth` states the
    text twice, the markup states it once, and the head prints once a page.
    Under -raw it does not have to be. The folio number leads each page and is
    digits, which are not words here, and the office name in the head does not
    reach the text layer at all. Both fall out for nothing.

    Do not go back to dropping the first line of each page. Under positional
    extraction that line is the head; under -raw it is the folio, and the line
    after it is text of the book.
    """
    # -raw, and neither of the other two. This book sets two columns.
    # -layout tries to hold them side by side and welds the last word of one
    # line to the first of the other: "motherand", "blamethe". Plain output
    # rebuilds reading order from position on the page, and interleaves the
    # columns line by line, which breaks every word LaTeX hyphenated: "com-"
    # ends up on one line and "pared" three lines later. -raw keeps the order
    # the text was written in, so each column stays whole and a hyphenated
    # word stays next to its other half.
    out = subprocess.run(["pdftotext", "-raw", str(pdf), "-"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"pdftotext failed on {pdf}")
    return words(out.stdout.replace("\f", "\n"))


def out_of_order(heads, stream):
    """Headings that do not stand in the source's order on the page.

    A forward pointer does not work here. One heading the engine misread will
    not be found, or will be found somewhere spurious, and every heading after
    it then reports as moved: 473 of 482 in one part against 7 of 878 in its
    twin. That is a desynchronised pointer, not a book with 473 faults, and a
    check that cries wolf on a whole part is worse than no check.

    So align instead. Take every place each heading occurs, sort them by
    position on the page, and find the longest run that keeps the source's
    order. That run is the book set correctly. Whatever is left over is what
    moved, and one bad heading costs one report.
    """
    index = {}
    for i, head in enumerate(heads):
        if not head:
            continue
        n = len(head)
        for j in range(len(stream) - n + 1):
            if stream[j:j + n] == head:
                index.setdefault(i, []).append(j)

    # (position, heading) for every occurrence, in page order. A heading that
    # occurs several times offers several chances to stay in order; taking the
    # later ones first inside one position keeps the run strictly increasing.
    pairs = sorted((pos, i) for i, ps in index.items() for pos in ps)
    order = [i for _, i in pairs]

    # Longest increasing run of heading numbers: the most headings that can
    # stand in the source's order at once.
    import bisect
    tails, back, at = [], [], []
    for k, val in enumerate(order):
        j = bisect.bisect_left(tails, val)
        if j == len(tails):
            tails.append(val); at.append(k)
        else:
            tails[j] = val; at[j] = k
        back.append(at[j - 1] if j else -1)
    keep, k = set(), (at[-1] if at else -1)
    while k >= 0:
        keep.add(order[k]); k = back[k]

    return [" ".join(heads[i]) for i in range(len(heads))
            if heads[i] and i not in keep]


def longest_absent(src_seq, pdf_counts):
    """The longest run of source words that are nowhere on the page.

    A word is absent when the PDF holds none of it at all. That is the only
    unambiguous statement: a word that stands somewhere else on the page was
    not lost, it moved, and this measure must not report a move as a loss.

    `longest_gap` below cannot separate the two. It compares sequences, so it
    reports a run wherever the two orders part company, and multi-column
    extraction parts company all the time. Read this number for loss and that
    one for divergence, and never the second on its own.
    """
    run = best = 0
    where = start = 0
    for i, w in enumerate(src_seq):
        if pdf_counts[w] == 0:
            run += 1
            if run > best:
                best, where = run, start if run > 1 else i
        else:
            run, start = 0, i + 1
    return best, " ".join(src_seq[where:where + min(best, 12)])


def longest_gap(src_seq, pdf_seq):
    """The longest run where the two sequences diverge, for any reason.

    The count of lost words is not the number to act on. Extraction leaves
    noise: -raw drops the space between two words here and there, and every
    welded pair reads as two losses and one gain. That noise is scattered.

    A fault is not scattered. A macro that eats its argument, a swallowed
    paragraph, an environment that ran away — each takes a contiguous run of
    the book with it. So measure the longest run, and let the isolated ones
    alone.
    """
    sm = difflib.SequenceMatcher(None, src_seq, pdf_seq, autojunk=False)
    worst, where = 0, ""
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag in ("delete", "replace") and i2 - i1 > worst:
            worst, where = i2 - i1, " ".join(src_seq[i1:i2][:12])
    return worst, where


def check(part, struct, parts_dir):
    pdf = parts_dir / f"{part}.pdf"
    if not pdf.exists():
        return None
    seq, heads, npages = read_markup(part, struct)
    stream = read_pdf(pdf)
    src, got = Counter(seq), Counter(stream)
    lost, gained = src - got, got - src
    run, where = longest_absent(seq, got)
    drift, _ = longest_gap(seq, stream)
    return {"part": part, "pages": npages, "words": len(seq),
            "lost": lost, "gained": gained, "run": run, "where": where,
            "drift": drift,
            "nlost": sum(lost.values()), "ngained": sum(gained.values()),
            "moved": out_of_order(heads, stream), "heads": len(heads)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", nargs="?", default="")
    ap.add_argument("--show", type=int, default=8)
    ap.add_argument("--structured", default=str(ROOT / "structured"))
    ap.add_argument("--parts", default=str(ROOT / "tex" / "parts"))
    args = ap.parse_args()

    struct, parts_dir = Path(args.structured), Path(args.parts)
    names = sorted(p.stem for p in parts_dir.glob(f"{args.part}*.pdf"))
    if not names:
        print(f"no built part matches '{args.part}' in {parts_dir}")
        return 2

    rows, tw, tl, tg, tm = [], 0, 0, 0, 0
    print(f"{'part':<38}{'words':>9}{'lost':>7}{'gained':>7}"
          f"{'absent':>7}{'drift':>6}{'moved':>6}")
    print("-" * 78)
    for name in names:
        r = check(name, struct, parts_dir)
        if r is None:
            continue
        tw += r["words"]; tl += r["nlost"]; tg += r["ngained"]
        tm += len(r["moved"])
        bad = r["run"] > 5 or r["moved"]
        print(f"{name[:36]:<38}{r['words']:>9,}{r['nlost']:>7,}"
              f"{r['ngained']:>7,}{r['run']:>7}{r['drift']:>6}"
              f"{len(r['moved']):>6}{'  <--' if bad else ''}")
        rows.append(r)

    print("-" * 78)
    pc = 100 * tl / tw if tw else 0
    worst = max((r["run"] for r in rows), default=0)
    drift = max((r["drift"] for r in rows), default=0)
    print(f"{'total':<38}{tw:>9,}{tl:>7,}{tg:>7,}{worst:>7}{drift:>6}{tm:>6}")
    print(f"\nlongest run of source words nowhere on the page: {worst}")
    print(f"longest run where the two orders diverge:        {drift}"
          f"   (order, not loss; multi-column extraction does this)")

    if args.show:
        for r in sorted(rows, key=lambda r: -r["nlost"])[:3]:
            if not (r["nlost"] or r["ngained"] or r["moved"]):
                continue
            print(f"\n{r['part']}")
            for w, n in r["lost"].most_common(args.show):
                print(f"    lost   {n:>4}  {w}")
            for w, n in r["gained"].most_common(args.show):
                print(f"    gained {n:>4}  {w}")
            for h in r["moved"][:args.show]:
                print(f"    moved        {h}")
            if r["run"]:
                print(f"    absent run   {r['run']} words: {r['where']}")
    return 1 if (tl or tm) else 0


if __name__ == "__main__":
    sys.exit(main())
