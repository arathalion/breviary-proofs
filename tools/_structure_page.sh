#!/bin/bash
# Infer the structure of one page. Used by ocr_all.sh. See _read_page.sh.
set -u
ROOT="/Users/maxdoty/Documents/Dominican Breviary"
stem="$1"
"$ROOT/.venv/bin/python" "$ROOT/tools/structure.py" \
    "$DRAFTS/$stem.json" "$PAGES/$stem.png" -o "$STRUCT/$stem.md" \
    >/dev/null 2>&1 || echo "  failed to structure: $stem"
# What a person said about the structure is applied after every run, never
# written into the markup, so running this twice gives the same answer.
"$ROOT/.venv/bin/python" "$ROOT/tools/applystructure.py" "$STRUCT/$stem.md" \
    >/dev/null 2>&1 || echo "  refused a structural correction: $stem"
