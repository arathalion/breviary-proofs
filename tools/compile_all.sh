#!/bin/bash
# Set every part in type, one PDF a part.
#
#   tools/compile_all.sh              every part that is not built
#   tools/compile_all.sh 05-Psalter   one part, or a prefix
#   FORCE=1 tools/compile_all.sh ''   build everything again
#   JOBS=1 tools/compile_all.sh ''    one part at a time
#
# Setting every part is the only test that reads the whole output. It found
# three faults that no audit of the reading could see: twelve lines of the book
# turned into markup tags, a tag firing six times on the median page, and two
# parts that would not compile at all because a folio number read as "[110" and
# multicols took the bracket for its own optional argument.
#
# So build all of it, not a sample, and run tools/roundtrip.py afterwards. A
# part that compiles is not a part that holds the book.
set -u

ROOT="/Users/maxdoty/Documents/Dominican Breviary"
PREFIX="${1:-}"
STRUCT="${STRUCT:-$ROOT/structured}"
OUT="${OUT:-$ROOT/tex/parts}"
JOBS="${JOBS:-4}"
PY="$ROOT/.venv/bin/python"
LOG="$ROOT/compile-all.log"

mkdir -p "$OUT"

# One part: markup to LaTeX, then LuaLaTeX twice so the running heads and any
# cross reference settle. Everything runs inside tex/ so the class is found.
build_one() {
    part="$1"
    set -- "$STRUCT/$part-"*.md
    [ -e "$1" ] || { echo "skip $part: no markup"; return 0; }

    "$PY" "$ROOT/tools/totex.py" "$@" -o "$OUT/$part.tex" || {
        echo "FAIL $part: totex"; return 1; }

    cd "$ROOT/tex" || return 1
    for pass in 1 2; do
        lualatex -interaction=nonstopmode -halt-on-error \
                 -output-directory="$OUT" "$OUT/$part.tex" \
                 > "$OUT/$part.compile.log" 2>&1 || {
            echo "FAIL $part: lualatex pass $pass, see $OUT/$part.compile.log"
            return 1; }
    done
    pages=$(pdfinfo "$OUT/$part.pdf" 2>/dev/null | awk '/^Pages/{print $2}')
    echo "ok $part ($pages pages)"
}
export -f build_one
export ROOT STRUCT OUT PY

# Which parts have markup at all.
#
# No xargs here. The path to this project holds a space, and xargs splits on
# whitespace, so "Dominican Breviary" arrives as two arguments and the word
# "Dominican" is then looked up as a part. Loop in the shell instead, which
# does not split what the glob returns.
parts=""
for f in "$STRUCT/$PREFIX"*.md; do
    [ -e "$f" ] || break
    b=$(basename "$f")
    parts="$parts${b%-[0-9][0-9][0-9][0-9][ab].md}"$'\n'
done
parts=$(printf '%s' "$parts" | sed '/^$/d' | sort -u)
[ -n "$parts" ] || { echo "no markup matches '$PREFIX' in $STRUCT"; exit 1; }

todo=""
for p in $parts; do
    if [ "${FORCE:-0}" = 1 ] || [ ! -s "$OUT/$p.pdf" ]; then
        todo="$todo$p"$'\n'
    fi
done
todo=$(printf '%s' "$todo" | sed '/^$/d')
[ -n "$todo" ] || { echo "every part matching '$PREFIX' is already built"; exit 0; }

echo "setting $(printf '%s\n' "$todo" | wc -l | tr -d ' ') parts, $JOBS at a time"
start=$(date +%s)
printf '%s\n' "$todo" | xargs -P "$JOBS" -I{} bash -c 'build_one "$@"' _ {} \
    | tee -a "$LOG"
echo
echo "FINISHED in $(( ($(date +%s) - start) / 60 )) minutes. Now run:"
echo "    tools/roundtrip.py"
