#!/bin/bash
# Read one page. Used by ocr_all.sh, which runs several of these at a time.
# It is a file rather than a line inside xargs because the command xargs would
# have had to assemble was longer than xargs on this system will accept.
set -u
ROOT="/Users/maxdoty/Documents/Dominican Breviary"
png="$1"
stem=$(basename "$png" .png)
"$ROOT/.venv/bin/python" "$ROOT/tools/ocr.py" "$png" \
    --out "$DRAFTS/$stem.md" --keep-images "$DRAFTS/crops" >/dev/null 2>&1
case $? in
    0) ;;
    # 2 means the page holds no type of its own: a blank leaf. That is a fact
    # about the book, not a fault, so it is listed apart.
    2) echo "  nothing to read: $stem" ;;
    *) echo "  failed to read: $stem" ;;
esac
