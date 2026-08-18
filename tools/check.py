#!/usr/bin/env python3
"""Say what a change to these tools did to the book.

Usage:
    check.py --save          record the book as it stands now
    check.py                 say what has moved since, and stop
    check.py --list          name every page that moved

There is no other automated check on this project. On 2026-08-17 and 18 four
faults went out and every one was caught by a person looking at a page: a crop
stretched to 114,716 px tall, a table collapsed into one row, every display
line reversed, and two printed lines interleaved. Three of them had a check
written for them that passed, because the check read the text of a block and
the sheet renders the words.

So this reads the words, and it reads them **in order**. A reordering anywhere
in the book moves the fingerprint of the page it is on, and this prints the
count. It does not know which answer is right. It knows that something changed
and how much, which is the thing nobody knew yesterday.

Run `--save` when the book is in a state you believe. Run it bare after any
change to `ocr.py`, `structure.py` or the drafts.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKISH = re.compile(r"^[^A-Za-z0-9]{0,3}$")


def sha(parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()[:16]


def fingerprint(drafts, structured):
    """One line for every page: what it says, in what order, in what shape."""
    out = {}
    for f in sorted(Path(drafts).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        words = [w["t"] for b in d["blocks"] for w in b["words"]]
        shape = [f'{b["column"]}{b["layer"][0]}{len(b["words"])}'
                 for b in d["blocks"]]
        md = Path(structured) / f"{f.stem}.md"
        out[f.stem] = {
            "words": sha(words),          # the reading, in order
            "shape": sha(shape),          # the blocks, in order
            "n": len(words),
            "markup": sha([md.read_text(encoding="utf-8")]) if md.exists() else "",
        }
    return out


def invariants(drafts, structured):
    """What must be true of the book whatever anybody changes."""
    bad = []
    for f in sorted(Path(drafts).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for i, b in enumerate(d["blocks"]):
            # The sheet renders the words and the markup carries the text. If
            # the two ever disagree, one of them is a lie about the page.
            got = [w["t"].strip() for w in b["words"] if w["t"].strip()]
            if got != b["text"].split():
                bad.append(f"{f.stem} block {i}: the words and the text differ")
                break
        if not (Path(structured) / f"{f.stem}.md").exists():
            bad.append(f"{f.stem}: no structured page")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", default=str(ROOT / "drafts"))
    ap.add_argument("--structured", default=str(ROOT / "structured"))
    ap.add_argument("--record", default=str(ROOT / "check.json"))
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    now = fingerprint(args.drafts, args.structured)
    bad = invariants(args.drafts, args.structured)
    for b in bad[:10]:
        print(f"broken  {b}", file=sys.stderr)
    if len(bad) > 10:
        print(f"        and {len(bad) - 10} more", file=sys.stderr)

    if args.save:
        Path(args.record).write_text(json.dumps(now), encoding="utf-8")
        print(f"recorded {len(now):,} pages, {sum(p['n'] for p in now.values()):,} words")
        return 1 if bad else 0

    rec = Path(args.record)
    if not rec.exists():
        print("nothing recorded yet: run check.py --save first", file=sys.stderr)
        return 2
    was = json.loads(rec.read_text(encoding="utf-8"))

    gone = sorted(set(was) - set(now))
    fresh = sorted(set(now) - set(was))
    moved = {k: [f for f in ("words", "shape", "markup")
                 if was[k].get(f) != now[k].get(f)]
             for k in sorted(set(was) & set(now))}
    moved = {k: v for k, v in moved.items() if v}

    for what in ("words", "shape", "markup"):
        n = sum(1 for v in moved.values() if what in v)
        say = {"words": "the reading changed, or its order",
               "shape": "the blocks changed, or their order",
               "markup": "the structure changed"}[what]
        print(f"{n:6,} pages  {say}")
    print(f"{len(gone):6,} pages gone, {len(fresh):,} new")
    old_n = sum(p["n"] for p in was.values())
    new_n = sum(p["n"] for p in now.values())
    print(f"words: {old_n:,} -> {new_n:,}"
          + ("  same" if old_n == new_n else f"  {new_n - old_n:+,}"))
    if args.list:
        for k, v in list(moved.items())[:40]:
            print(f"   {k[:52]:54} {' '.join(v)}")
        if len(moved) > 40:
            print(f"   and {len(moved) - 40} more")
    return 1 if (bad or moved) else 0


if __name__ == "__main__":
    sys.exit(main())
