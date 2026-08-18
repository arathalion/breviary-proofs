#!/usr/bin/env python3
"""Put the corrections from a proof sheet back into the drafts.

Usage:
    applyfix.py corrections-26-Common-of-a-Virgin.json [more.json ...]
    applyfix.py corrections-*.json -n          say what would change, change nothing

The proof sheet writes one JSON file. It names each corrected word by its
address in the draft: the index of its block, then the index of the word in
that block. This tool reads that file and rewrites `drafts/`.

A word that a person touched gets confidence 100, so the audit and the next
proof sheet stop asking about it. The tool then deletes the structured page,
because it is now out of date. Run `tools/ocr_all.sh <part>` afterwards. It
skips every page that is already read and rebuilds only what is missing.

The tool refuses a correction whose word no longer says what the proof sheet
saw. That means the draft changed under the correction, and guessing which
one is right would be worse than stopping.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def split_box(word, parts):
    """Share one word box between the words a person typed in its place.

    `structure.py` groups words into lines by their vertical position, and
    orders them by x. So the height and the top edge must stay, and the new
    boxes must run left to right inside the old one.
    """
    span = len(" ".join(parts))
    gap = max(1, round(word["w"] / span))
    out, x = [], word["x"]
    for p in parts:
        w = max(1, round(word["w"] * len(p) / span))
        out.append({"t": p, "conf": 100.0, "x": x, "y": word["y"],
                    "w": w, "h": word["h"]})
        x += w + gap
    return out


def apply_page(src, rec, drafts, struct, dry):
    path = drafts / f"{src}.json"
    if not path.exists():
        return None, [f"{src}: no draft"]

    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = data["blocks"]
    changed, cut, added, again, problems = 0, 0, 0, 0, []

    # Verify every correction against the page as the proof sheet saw it,
    # before anything is changed. Two words deleted next to each other used to
    # refuse the second of them: the first deletion moved the word that
    # followed, and the guard below then found the wrong neighbour. Eighteen
    # of Max's first 168 corrections were refused for that reason alone.
    seen = {}
    for addr, f in rec.get("fix", {}).items():
        bi, wi = (int(n) for n in addr.split("."))
        if bi < len(blocks) and wi < len(blocks[bi]["words"]):
            here = blocks[bi]["words"]
            seen[addr] = (here[wi]["t"],
                          here[wi + 1]["t"] if wi + 1 < len(here) else None)

    # Work from the end of each block, so deleting a word cannot move the
    # address of a word that is still to come.
    for addr in sorted(rec.get("fix", {}),
                       key=lambda a: tuple(int(n) for n in a.split(".")),
                       reverse=True):
        was = rec["fix"][addr]["was"]
        now = rec["fix"][addr]["now"]
        bi, wi = (int(n) for n in addr.split("."))
        if bi >= len(blocks) or wi >= len(blocks[bi]["words"]):
            problems.append(f"{src} {addr}: no such word")
            continue
        # The same file can be applied twice: the sheet stays open, and a
        # person downloads it again after more work. A correction that is
        # already in the draft must do nothing. Without this test the words a
        # person added go in a second time, and nothing says so.
        here = blocks[bi]["words"]
        parts = now.split()
        if parts and [w["t"] for w in here[wi:wi + len(parts)]] == parts:
            again += 1
            continue
        word = here[wi]
        was_then, after_then = seen.get(addr, (None, None))
        if word["t"] != was:
            problems.append(f"{src} {addr}: the draft says {word['t']!r}, "
                            f"the sheet saw {was!r}")
            continue
        if now == "":
            # A deletion leaves no sign of itself, so the sheet names the word
            # that came after it. Both words must agree before anything goes.
            # Against the page as it was, not as this run has left it.
            after = rec["fix"][addr].get("after")
            if after is not None and after != after_then:
                problems.append(f"{src} {addr}: {was!r} is there, but {after!r} "
                                f"does not follow it")
                continue
            here.pop(wi)
            cut += 1
        else:
            if len(parts) == 1:
                word["t"] = parts[0]
                word["conf"] = 100.0
            else:
                here[wi:wi + 1] = split_box(word, parts)
                added += len(parts) - 1
            changed += 1

    # A word the person confirmed is not doubtful any more. The sheet holds
    # those separately, and only counts them, so raise the whole page when the
    # person read the whole page.
    if rec.get("full"):
        data["proofed"] = True
    if rec.get("note"):
        data["note"] = rec["note"]

    # An empty block stays. Dropping it would move every block after it, and
    # the addresses in a proof sheet that is still open would then point at
    # the wrong words.
    for b in blocks:
        b["text"] = " ".join(w["t"] for w in b["words"])

    if not dry:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        md = struct / f"{src}.md"
        if md.exists():
            md.unlink()
    return (changed, cut, added, again), problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-n", "--dry-run", action="store_true")
    ap.add_argument("--drafts", default=str(ROOT / "drafts"))
    ap.add_argument("--structured", default=str(ROOT / "structured"))
    ap.add_argument("--structfix", default=str(ROOT / "structfix"))
    args = ap.parse_args()

    drafts, struct = Path(args.drafts), Path(args.structured)
    sfix = Path(args.structfix)
    pages = notes = changed = cut = added = again = blocks = tables = 0
    problems = []

    for f in args.files:
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        print(f"== {Path(f).name}, from {doc.get('who') or 'nobody named'}")
        for src, rec in doc["pages"].items():
            # What a person said about the structure is not written into the
            # markup here. `structure.py` builds that file again from the
            # draft every time a word changes, so an edit of it would be
            # thrown away. It is held beside the drafts and applied after
            # every run, by `applystructure.py`.
            if rec.get("str") or rec.get("cols"):
                blocks += len(rec.get("str") or {})
                if not args.dry_run:
                    sfix.mkdir(parents=True, exist_ok=True)
                    out = sfix / f"{src}.json"
                    kept = json.loads(out.read_text(encoding="utf-8")) \
                        if out.exists() else {}
                    ops = kept.get("ops", {})
                    ops.update(rec.get("str") or {})
                    kept["ops"] = ops
                    # The column guides are the shape of a table, and the
                    # newest word on it wins: a person who moves a guide means
                    # the new place, not both.
                    if rec.get("cols"):
                        kept["cols"] = rec["cols"]
                        # One page has one shear, and the guides lean with it.
                        kept["lean"] = rec.get("lean", 0) or 0
                        tables += 1
                    out.write_text(json.dumps(kept, ensure_ascii=False,
                                              indent=1), encoding="utf-8")
            if (not rec.get("fix") and not rec.get("note")
                    and not rec.get("full") and not rec.get("str")
                    and not rec.get("cols")):
                continue
            counts, bad = apply_page(src, rec, drafts, struct, args.dry_run)
            problems += bad
            if counts:
                pages += 1
                changed += counts[0]
                cut += counts[1]
                added += counts[2]
                again += counts[3]
            if rec.get("note"):
                notes += 1
                print(f"note  {src}: {rec['note']}")

    for p in problems:
        print(f"stop  {p}", file=sys.stderr)

    what = "would change" if args.dry_run else "changed"
    print(f"{what} {pages} pages: {changed} words corrected, {cut} deleted, "
          f"{added} added, {again} already in, {notes} notes, "
          f"{blocks} blocks mended, {tables} tables set out, "
          f"{len(problems)} refused")
    if not args.dry_run and pages:
        print("now run  tools/ocr_all.sh <part>   to structure the pages again")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
