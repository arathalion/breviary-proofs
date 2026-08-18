#!/usr/bin/env python3
"""Find a word this book contradicts somewhere else in itself.

Usage:
    witness.py                       write witness.json beside the drafts
    witness.py --report              print what it found, and stop

A breviary repeats. The psalter comes round every week, the Ordinary stands in
both volumes, and an antiphon can be printed twenty times. So the book is its
own second witness: where the same six words surround one word in many places,
and that word is one thing everywhere but here, here is probably wrong.

This is the only check on this project that can see a **correctly spelt word in
the wrong place**. The engine's confidence cannot: it is sure of what it read.
A dictionary cannot: the word is real. Measured over 22 pages read word by
word, 70% of the errors were on words the book uses more than ten times, and
nothing else reaches them.

It proposes and never decides. The proof sheet shows what the book says
elsewhere, and a person chooses.
"""
import argparse
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The same rule the proof sheet uses, so the two agree about what a word is.
RE_MARKISH = re.compile(r"^[^A-Za-z0-9]{0,3}$")
SIDE = 3            # words of context on each side
SEEN = 2            # a context must stand this many times to be a witness


def norm(t):
    return re.sub(r"^[^\w']+|[^\w']+$", "", t).lower()


def read_pages(drafts):
    """Every page as a flat list of (address, token), in reading order."""
    for f in sorted(Path(drafts).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        words = []
        for bi, b in enumerate(d["blocks"]):
            for wi, w in enumerate(b["words"]):
                if RE_MARKISH.match(w["t"]):
                    continue
                words.append((f"{bi}.{wi}", w["t"], w["conf"]))
        yield d["src"], words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", default=str(ROOT / "drafts"))
    ap.add_argument("--out", default=str(ROOT / "witness.json"))
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    pages = list(read_pages(args.drafts))

    # Pass one: what does the book put between these six words, and how often?
    context = collections.defaultdict(collections.Counter)
    for src, words in pages:
        keys = [norm(t) for _, t, _ in words]
        for i in range(SIDE, len(keys) - SIDE):
            if not keys[i]:
                continue
            key = (tuple(keys[i - SIDE:i]), tuple(keys[i + 1:i + 1 + SIDE]))
            context[key][keys[i]] += 1

    # Pass two: a word standing once where the book says something else twice.
    found = collections.defaultdict(dict)
    total = 0
    for src, words in pages:
        keys = [norm(t) for _, t, _ in words]
        for i in range(SIDE, len(keys) - SIDE):
            if not keys[i]:
                continue
            key = (tuple(keys[i - SIDE:i]), tuple(keys[i + 1:i + 1 + SIDE]))
            says = context[key]
            if says[keys[i]] != 1:
                continue
            other = [(w, n) for w, n in says.items()
                     if w != keys[i] and n >= SEEN]
            if not other:
                continue
            other.sort(key=lambda p: -p[1])
            addr, token, conf = words[i]
            found[src][addr] = {"is": token, "book": other[0][0],
                                "seen": other[0][1], "conf": round(conf)}
            total += 1

    if args.report:
        pages_hit = len(found)
        quiet = sum(1 for p in found.values() for v in p.values() if v["conf"] >= 80)
        print(f"{total:,} words the book contradicts, on {pages_hit:,} pages")
        print(f"{quiet:,} of them score 80 or better, so the sheet marks none of them")
        shown = 0
        for src in sorted(found):
            for addr, v in sorted(found[src].items()):
                if v["conf"] < 80 or shown >= 12:
                    continue
                print(f"   {v['is']!r:16} the book says {v['book']!r:16} "
                      f"{v['seen']:3}x   conf {v['conf']:3}   {src[:34]}")
                shown += 1
        return

    Path(args.out).write_text(json.dumps(found, ensure_ascii=False),
                              encoding="utf-8")
    print(f"wrote {args.out}: {total:,} words on {len(found):,} pages")


if __name__ == "__main__":
    main()
