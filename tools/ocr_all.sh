#!/bin/bash
# Read prepared pages, infer their structure, audit the result, and build a
# proof sheet.
#
#   tools/ocr_all.sh 04-Ordinary        one part
#   tools/ocr_all.sh ''                 every page that is ready
#   PROOF=0 tools/ocr_all.sh 04-Ord     the same, without the proof sheet
#   JOBS=1 tools/ocr_all.sh ''          one page at a time
#   PAGES=pages.new tools/ocr_all.sh '' read a different set of pages
#
# Pages are read several at a time. One page is one process, so the work
# divides without any locking.
#
# Safe to stop and start again. A page that already has output is skipped, so
# a run that is interrupted picks up where it left off.
set -u

ROOT="/Users/maxdoty/Documents/Dominican Breviary"
PREFIX="${1:-}"
PAGES="${PAGES:-$ROOT/pages}"
DRAFTS="${DRAFTS:-$ROOT/drafts}"
CROPS="$DRAFTS/crops"
STRUCT="${STRUCT:-$ROOT/structured}"
JOBS="${JOBS:-6}"
PY="$ROOT/.venv/bin/python"

case "$PAGES" in /*) ;; *) PAGES="$ROOT/$PAGES" ;; esac
case "$DRAFTS" in /*) ;; *) DRAFTS="$ROOT/$DRAFTS"; CROPS="$DRAFTS/crops" ;; esac
case "$STRUCT" in /*) ;; *) STRUCT="$ROOT/$STRUCT" ;; esac

mkdir -p "$DRAFTS" "$CROPS" "$STRUCT"
work=$(mktemp)
trap 'rm -f "$work"' EXIT

echo "== reading pages from $PAGES"
: > "$work"
for png in "$PAGES/$PREFIX"*.png; do
    [ -e "$png" ] || { echo "no pages match '$PREFIX' in $PAGES"; exit 1; }
    stem=$(basename "$png" .png)
    [ -s "$DRAFTS/$stem.json" ] || printf '%s\0' "$png" >> "$work"
done
echo "   $(tr -cd '\0' < "$work" | wc -c | tr -d ' ') pages to read, $JOBS at a time"
# A page that reads as nothing exits non-zero and says so here. Reporting
# success for such a page once hid 29 of them inside a run that claimed to
# have read everything.
# NUL separated, because the path to this project has a space in it and
# xargs splits on whitespace by default.
DRAFTS="$DRAFTS" xargs -0 -P "$JOBS" -n1 "$ROOT/tools/_read_page.sh" < "$work"

echo "== inferring structure"
: > "$work"
for json in "$DRAFTS/$PREFIX"*.json; do
    [ -e "$json" ] || break
    stem=$(basename "$json" .json)
    [ -s "$STRUCT/$stem.md" ] || printf '%s\0' "$stem" >> "$work"
done
echo "   $(tr -cd '\0' < "$work" | wc -c | tr -d ' ') pages to structure"
DRAFTS="$DRAFTS" PAGES="$PAGES" STRUCT="$STRUCT" \
    xargs -0 -P "$JOBS" -n1 "$ROOT/tools/_structure_page.sh" < "$work"

name="${PREFIX:-all}"

# Nothing to report on if nothing was read. Without this the glob below goes
# through unexpanded and the tools fail on a file name that does not exist.
set -- "$DRAFTS/$PREFIX"*.json
if [ ! -e "$1" ]; then
    echo "== no drafts to audit"
    exit 1
fi

# A proof sheet is a folder: the page, and the colour crops beside it as WebP.
# That is about 250 KB a page. The same sheet with the crops inside it as PNG
# is 4 MB a page, which is 87 MB for one small part and more than a gigabyte
# for a Proper. Set PROOF=0 for a bulk run, then build the sheet for one part
# when you proof it.
if [ "${PROOF:-1}" = 1 ]; then
    echo "== proof sheet"
    "$PY" "$ROOT/tools/proof.py" "$@" -o "$ROOT/proofs/proof-$name/" --images "$CROPS"
    # The landing page reads its numbers back out of the sheets, so it follows
    # them. A sheet that is built and not listed is a sheet nobody can reach.
    "$PY" "$ROOT/tools/proofindex.py" "$ROOT/proofs/"
fi

echo "== audit"
"$PY" "$ROOT/tools/audit.py" "$@"
