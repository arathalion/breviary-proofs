#!/usr/bin/env python3
"""Put a person's structural corrections back, after `structure.py` has run.

Usage:
    applystructure.py structured/page.md            apply, in place
    applystructure.py structured/*.md -n            say what would change

`structure.py` infers the structure of a page from its geometry, and it is
wrong in ways no measurement has ever caught: a heading cut in half, a drop
capital missed, a red mark split off the line it belongs to. A person sees
those in the proof sheet and says so.

Their corrections must not be edits of `structured/*.md`, because that file is
built again from the draft every time a word changes, and the edits would go
with it. They are held in `structfix/<page>.json` instead and applied here,
after every run. Running the structure step twice gives the same answer.

Four things a person can say, and no more. The tag of a block comes from the
ink colour, which is measured and is right about 99 times in 100, so nothing
here changes a tag except to name a drop capital.

    join   this block belongs on the end of the one above it
    up     it sits one place too low
    down   it sits one place too high
    open   it opens with a drop capital

Every correction carries the text the sheet saw. A block that no longer says
that is refused and reported, never guessed at, exactly as `applyfix.py` does
with a word.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse(text):
    """The markup as blocks, and the `#` lines that head the page.

    A block is [tag, inline, lines]. A tag line can carry its text on the same
    line — `.heading | Lesson ix` — and that form is kept, so a page nobody
    corrects comes back byte for byte as `structure.py` wrote it.
    """
    head, blocks = [], []
    for line in text.splitlines():
        # `line[:1] in ".#"` is a trap: an empty string is a substring of
        # every string, so every blank line became a block with no tag.
        if line.startswith("#") and not blocks:
            head.append(line)
        elif line.startswith((".", "#")):
            tag, _, rest = line.partition(" ")
            blocks.append([tag, rest if rest.strip() else None, []])
        elif line.strip() and blocks:
            blocks[-1][2].append(line)
    return head, blocks


def body(block):
    """What the proof sheet showed for this block, exactly as it showed it."""
    _, inline, lines = block
    parts = ([inline] if inline is not None else []) + lines
    return "\n".join(parts).strip()


def find(blocks, want, hint):
    """The block that says `want`: at `hint` if it still does, else by text."""
    if 0 <= hint < len(blocks) and body(blocks[hint]) == want:
        return hint
    hits = [i for i, b in enumerate(blocks) if body(b) == want]
    return hits[0] if len(hits) == 1 else None


def retag(tag, name):
    """Keep the colour of a block while changing what it is called.

    `.rubric` is the red layer, so a drop capital in it is a red one. Only
    `.open` writes its colour out; the other tags carry it in the name.
    """
    red = tag == ".rubric" or tag.endswith(" red")
    return f".{name} red" if red else f".{name}"


def apply(md, ops, say):
    """Work the corrections into one page of markup."""
    head, blocks = parse(md)
    done = refused = 0
    # `open` changes nothing about the order, so it goes first and the moves
    # below still find their blocks where the sheet left them.
    order = sorted(ops.items(), key=lambda kv: (kv[1]["do"] != "open", int(kv[0])))
    # A sheet built before the blocks were renumbered can hold the same
    # correction under two numbers. `find` heals that by looking for the text,
    # and both would then land on one block: harmless for `open`, and a second
    # `join` would eat a block nobody asked about. Same action on the same
    # text is one correction.
    seen = set()
    for key, op in order:
        if (op["do"], op["was"]) in seen:
            continue
        seen.add((op["do"], op["was"]))
        i = find(blocks, op["was"], int(key))
        if i is None:
            say(f"  refused {op['do']}: no block says {op['was'][:40]!r}")
            refused += 1
            continue
        do = op["do"]
        if do == "open":
            blocks[i][0] = retag(blocks[i][0], "open")
        elif do == "join":
            if i == 0:
                say("  refused join: nothing above it")
                refused += 1
                continue
            above = blocks[i - 1]
            if above[1] is not None:
                above[2].insert(0, above[1])
                above[1] = None
            gone = blocks.pop(i)
            above[2].extend(([gone[1]] if gone[1] is not None else []) + gone[2])
        elif do == "up" and i > 0:
            blocks[i - 1], blocks[i] = blocks[i], blocks[i - 1]
        elif do == "down" and i + 1 < len(blocks):
            blocks[i], blocks[i + 1] = blocks[i + 1], blocks[i]
        else:
            say(f"  refused {do}: it is already at the end")
            refused += 1
            continue
        done += 1
    out = list(head) + [""]
    for tag, inline, lines in blocks:
        out.append(f"{tag} {inline}" if inline is not None else tag)
        out.extend(lines)
    return "\n".join(out) + "\n", done, refused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("-n", "--dry-run", action="store_true")
    ap.add_argument("--fixes", default=str(ROOT / "structfix"))
    args = ap.parse_args()

    fixes = Path(args.fixes)
    pages = done = refused = 0
    for p in args.pages:
        path = Path(p)
        rec = fixes / f"{path.stem}.json"
        if not rec.exists():
            continue
        ops = json.loads(rec.read_text(encoding="utf-8")).get("ops", {})
        if not ops:
            continue
        out, d, r = apply(path.read_text(encoding="utf-8"), ops, print)
        pages += 1
        done += d
        refused += r
        if not args.dry_run:
            path.write_text(out, encoding="utf-8")
    verb = "would mend" if args.dry_run else "mended"
    print(f"{verb} {done} blocks over {pages} pages, {refused} refused",
          file=sys.stderr)
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
