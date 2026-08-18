#!/bin/bash
# Read every small part: all 27 parts except the four large Propers, which are
# parts 12, 13, 15 and 16.
#
#   tools/ocr_small.sh
#
# The small parts hold 528 of the 2,180 pages. They cover more kinds of page
# than the four Propers do between them: hymns, litanies, pointed psalms and
# missal extracts. Reading them first shows what the detectors still miss,
# before 1,652 pages are read on detectors that have seen one genre.
#
# The parts run smallest first, so a fault shows in the first minutes.
#
# No proof sheet is built here. A sheet embeds its colour crops and costs
# about 2.5 MB a page. Build one for a part when you sit down to proof it:
#
#   tools/ocr_all.sh 25-Common-of-a-Confessor
#
# Safe to stop and start again. A page that already has output is skipped.
set -u

ROOT="/Users/maxdoty/Documents/Dominican Breviary"
PAGES="$ROOT/pages"
DRAFTS="$ROOT/drafts"
PY="$ROOT/.venv/bin/python"
BIG='^(12|13|15|16)-'

parts=$(ls "$PAGES" | sed 's/-[0-9]*[ab]\.png$//' | sort | uniq -c | sort -n \
        | awk '{print $2}' | grep -Ev "$BIG")

count=$(echo "$parts" | wc -l | tr -d ' ')
echo "$count small parts to read"
echo

n=0
for p in $parts; do
    n=$((n+1))
    echo "########## [$n/$count] $p"
    PROOF=0 "$ROOT/tools/ocr_all.sh" "$p"
    echo
done

echo "########## audit across every small part"
for p in $parts; do
    "$PY" "$ROOT/tools/audit.py" "$DRAFTS/$p"*.json
    echo
done
