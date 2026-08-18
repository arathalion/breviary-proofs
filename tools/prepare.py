#!/usr/bin/env python3
"""Turn a scanned breviary PDF into clean single page images for OCR.

Usage:
    prepare.py <file.pdf> <outdir> [--dpi 300] [--first N] [--last N]

Each scan holds a two page spread. This tool trims the dark background, cuts
the spread at the fold, and straightens each page. It writes one PNG for each
book page, named for the scan page and the side.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import pagelib


def page_count(pdf):
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="redo pages already written")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    last = args.last or page_count(pdf)
    written = skipped = 0
    for scan in range(args.first, last + 1):
        # The run takes about an hour, so let it resume where it stopped.
        if not args.force and (out / f"{pdf.stem}-{scan:04d}a.png").exists():
            skipped += 1
            continue
        try:
            img = pagelib.render_page(pdf, scan, args.dpi)
            pages = pagelib.prepare_page(img)
        except Exception as exc:
            print(f"scan {scan}: FAILED {exc}", file=sys.stderr)
            continue
        for side, page in zip("ab", pages):
            name = out / f"{pdf.stem}-{scan:04d}{side}.png"
            page.save(name)
            written += 1
        print(f"scan {scan:4d} -> {len(pages)} page(s)  {pages[0].size}")

    print(f"\n{written} page images written, {skipped} scans already done, in {out}")


if __name__ == "__main__":
    main()
