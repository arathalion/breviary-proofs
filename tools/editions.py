#!/usr/bin/env python3
"""Bind the parts into editions: one volume, two volumes, or four.

Usage:
    editions.py                 build every edition
    editions.py two             build one edition
    editions.py --list          say what each edition holds, build nothing

A part is a unit of transcription. A volume is a unit of binding, and the two
have nothing to do with each other. This tool gathers the markup of several
parts into one LaTeX document and sets it, so the same transcription can be
bound three ways without being touched.

**What repeats, and why.** A breviary volume has to stand on its own: whoever
holds it needs the Ordinary, the Psalter, the Commons and the Office of the
Dead on any day of the year. So those blocks go into every volume of a
multi-volume edition. That is what the 1967 edition did, and the folio numbers
prove it: the Psalter runs 18 to 215 in both volumes, and the Commons carry a
second, bracketed series [2] to [245] precisely so the same sheets could be
bound into both.

The cost is large and it is the whole difficulty of the four volume edition.
Front matter and Psalter come to 417 pages, and the Commons, accessory offices
and appendices to 431. That is 848 pages carried by every volume before a
single Proper is set.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCT = ROOT / "structured"
OUT = ROOT / "tex" / "editions"

# Named groups of parts, by the number each part's name begins with.
BLOCKS = {
    "front":      ["00", "01", "02", "03", "04"],
    "psalter":    ["05", "06", "07", "08", "09", "10", "11"],
    "season1":    ["12"],
    "season2":    ["13", "14"],
    "saints1":    ["15", "19"],
    "saints2":    ["16", "17", "18"],
    "commons":    ["20", "21", "22", "23", "24", "25", "26", "27", "28",
                   "29", "30", "31", "32", "33"],
    "appendices": ["34", "35", "36", "37"],
}

# Everything a volume needs before its own Propers, and everything after them.
CARRIED_BEFORE = ["front", "psalter"]
CARRIED_AFTER = ["commons", "appendices"]


def carried(*own):
    return CARRIED_BEFORE + list(own) + CARRIED_AFTER


EDITIONS = {
    # One book. Nothing repeats, so this is the true length of the work and
    # the only edition where the page count means anything on its own.
    "one": [
        ("Dominican-Breviary",
         ["front", "psalter", "season1", "season2", "saints1", "saints2",
          "commons", "appendices"]),
    ],

    # What the 1967 edition did. For bible paper and a binder who sews.
    "two": [
        ("Volume-I-Advent-to-Trinity", carried("season1", "saints1")),
        ("Volume-II-Trinity-to-Advent", carried("season2", "saints2")),
    ],

    # For ordinary digital stock, which is thicker, so the block must be
    # thinner. The year divides at the same places the parts already divide.
    "four": [
        ("Volume-I-Advent-to-Trinity", carried("season1")),
        ("Volume-II-Trinity-to-Advent", carried("season2")),
        ("Volume-III-Saints-January-to-June", carried("saints1")),
        ("Volume-IV-Saints-July-to-December", carried("saints2")),
    ],
}


def markup_for(block):
    """Every page of markup in a block, in the order the book has it."""
    files = []
    for prefix in BLOCKS[block]:
        files += sorted(STRUCT.glob(f"{prefix}-*.md"))
    return files


def build(edition, volume, blocks, dry=False):
    files = []
    for b in blocks:
        got = markup_for(b)
        if not got:
            print(f"  {volume}: block '{b}' has no markup", file=sys.stderr)
        files += got
    if dry:
        return len(files), None

    into = OUT / edition
    into.mkdir(parents=True, exist_ok=True)
    tex = into / f"{volume}.tex"
    r = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "tools/totex.py"),
                        *[str(f) for f in files], "-o", str(tex)],
                       capture_output=True, text=True)
    if r.returncode:
        print(f"  {volume}: totex failed\n{r.stderr}", file=sys.stderr)
        return len(files), None

    # Twice, so the running heads settle.
    for _ in range(2):
        r = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={into}", str(tex)],
            cwd=ROOT / "tex", capture_output=True, text=True)
        if r.returncode:
            log = into / f"{volume}.log"
            print(f"  {volume}: lualatex failed, see {log}", file=sys.stderr)
            return len(files), None

    pdf = into / f"{volume}.pdf"
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = int([l for l in info.splitlines() if l.startswith("Pages")][0].split()[1])
    return len(files), pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", nargs="?", default="")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    names = [args.edition] if args.edition else list(EDITIONS)
    for name in names:
        if name not in EDITIONS:
            print(f"no edition called '{name}'. Try: {', '.join(EDITIONS)}")
            return 2
        print(f"\n== {name}: {len(EDITIONS[name])} volume(s)")
        total = 0
        for volume, blocks in EDITIONS[name]:
            pages_of_markup, pages = build(name, volume, blocks, dry=args.list)
            if args.list:
                print(f"   {volume:<38} {pages_of_markup:>5} pages of markup"
                      f"   {' '.join(blocks)}")
            elif pages:
                total += pages
                print(f"   {volume:<38} {pages:>5} pages")
            else:
                print(f"   {volume:<38}   FAILED")
        if total and not args.list:
            print(f"   {'paper in the edition':<38} {total:>5} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
