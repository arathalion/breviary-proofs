#!/usr/bin/env python3
"""Find pages where the reading went wrong, before they reach the book.

Usage:
    audit.py drafts/*.json

Confidence scores cannot see text that was never read at all. A page whose
rubrics silently failed reports high confidence on the few words it did find.
This tool watches the quantity instead of the quality.

Each page is compared against the middle of its own part, not against a fixed
expectation. Content differs sharply between parts: the Ordinary is nearly all
rubric, while a Proper is nearly all text to be said. Judging every page by one
global figure raises false alarms, which is exactly the mistake this tool
exists to avoid.

The versicle and response marks are excluded from the counts. No OCR engine
reads U+2123 or U+211F, they always score badly, and `structure.py` recovers
them by rule. Leaving them in would bury the real faults.
"""
import argparse
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

LOW = 80          # a word below this confidence wants a person
THIN = 0.45       # a page holding less than this share of the usual is suspect
NOISY = 2.0       # a page flagging this many times the usual is suspect
RE_MARKISH = re.compile(r"^[^A-Za-z0-9]{0,3}$")


def part_of(src):
    """The part a page belongs to, taken from its file name."""
    m = re.match(r"(\d+)-", src)
    return m.group(1) if m else "??"


def measure(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {"src": d["src"], "part": part_of(d["src"]), "black": 0, "red": 0,
           "low": 0, "counted": 0, "crossed": len(d.get("crossed", []))}
    for b in d["blocks"]:
        for w in b["words"]:
            if RE_MARKISH.match(w["t"]):
                continue          # a mark or stray ink, not a word
            out[b["layer"]] += 1
            out["counted"] += 1
            if w["conf"] < LOW:
                out["low"] += 1
    out["words"] = out["black"] + out["red"]
    out["rate"] = out["low"] / out["counted"] if out["counted"] else 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts", nargs="+")
    ap.add_argument("--quiet", action="store_true", help="print only the faults")
    ap.add_argument("--crossed", action="store_true",
                    help="list the pages whose gutter closes somewhere")
    args = ap.parse_args()

    pages = [measure(p) for p in args.drafts]
    byparts = defaultdict(list)
    for p in pages:
        byparts[p["part"]].append(p)

    faults = []
    for part, group in sorted(byparts.items()):
        words = st.median([p["words"] for p in group])
        rate = st.median([p["rate"] for p in group])
        reds = st.median([p["red"] for p in group])
        if not args.quiet:
            # The median page, not the pooled total. The proof sheet pools its
            # words and so reports a slightly different figure; both are right.
            print(f"part {part}: {len(group):4d} pages   "
                  f"median page {words:4.0f} words ({reds:3.0f} red)   "
                  f"{rate*100:4.1f}% to check")
        for p in group:
            why = []
            if words and p["words"] < words * THIN:
                why.append(f"only {p['words']} words against {words:.0f}")
            if reds >= 8 and p["red"] < reds * THIN:
                why.append(f"only {p['red']} red against {reds:.0f}")
            if rate and p["rate"] > max(rate * NOISY, 0.25):
                why.append(f"{p['rate']*100:.0f}% to check against {rate*100:.0f}%")
            if why:
                faults.append((p["src"], "; ".join(why)))

    print(f"\n{len(pages)} pages audited, {len(faults)} want a look")
    for src, why in faults:
        print(f"  {src}: {why}")

    # Counted, not listed, and not called a fault. It says the gutter closes
    # somewhere down the page, which is what a heading set across both columns
    # does. But the type is justified and the gutter of this book is as narrow
    # as four pixels, so ordinary lines reaching it set this off as well.
    # Checked by eye, most of these are ordinary two column pages. It is a
    # rough upper bound on the pages that want an eye, no more. Look at them
    # with tools/showcolumns.py; --crossed prints the list.
    crossed = [p for p in pages if p["crossed"]]
    print(f"\n{len(crossed)} pages where the gutter closes somewhere down the "
          f"page. Most are ordinary pages whose lines reach it.")
    if args.crossed:
        for p in crossed:
            print(f"  {p['src']}: {p['crossed']} band(s)")


if __name__ == "__main__":
    main()
