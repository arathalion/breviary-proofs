#!/bin/bash
# Prepare every scanned part into single page images for OCR.
#
#   tools/prepare_all.sh                 write into pages/
#   tools/prepare_all.sh pages.new       write somewhere else
#   JOBS=1 tools/prepare_all.sh          one part at a time
#
# The parts run several at a time. One part is one process, so the work
# divides without any locking. Safe to stop and start again: prepare.py skips
# any scan it already wrote.
set -u

ROOT="/Users/maxdoty/Documents/Dominican Breviary"
SRC="$ROOT/1967 Dominican Breviary (English)"
OUT="${1:-$ROOT/pages}"
JOBS="${JOBS:-6}"
PY="$ROOT/.venv/bin/python"

case "$OUT" in /*) ;; *) OUT="$ROOT/$OUT" ;; esac
mkdir -p "$OUT"

start=$(date +%s)
echo "preparing into $OUT, $JOBS parts at a time"

find "$SRC" -name '*.pdf' -print0 \
  | xargs -0 -n1 -P "$JOBS" -I{} \
    "$PY" "$ROOT/tools/prepare.py" {} "$OUT" --dpi 300

count=$(ls -1 "$OUT"/*.png 2>/dev/null | wc -l | tr -d ' ')
size=$(du -sh "$OUT" | cut -f1)
echo
echo "FINISHED in $(( ($(date +%s) - start) / 60 )) minutes"
echo "$count page images, $size, in $OUT"
