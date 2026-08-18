#!/usr/bin/env python3
"""Convert breviary markup into LaTeX for the breviary class.

Usage:
    totex.py <in.md> [more.md ...] [-o out.tex] [--fragment]

The markup format is described in schema/markup.md. The markup holds the
meaning of the page. This tool decides how that meaning looks on paper, so the
transcription never has to change when the design does.
"""
import argparse
import re
import sys
from pathlib import Path

# Characters that TeX would otherwise read as instructions.
SPECIAL = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    # Braces are markup in this format, so the splitter has already taken the
    # matched pairs out. Any brace still here is stray, usually misread by the
    # OCR engine, and would unbalance the LaTeX if it went through raw.
    "{": r"\{", "}": r"\}",
}
MARKS = {
    "<V>": r"\vers{}", "<R>": r"\resp{}",
    "<*>": r"\med{}", "<?>": r"\unclear{}",
}


def escape(text):
    out = text.replace("\\", r"\textbackslash{}")
    for char, tex in SPECIAL.items():
        out = out.replace(char, tex)
    # A line of this book can open with a square bracket, because the folio
    # number is set that way and the engine reads it as text. A bracket that
    # follows an environment is read by LaTeX as an optional argument to it:
    # multicols took "[ tolled her in the number of" for its preface, ran on
    # to the end of the paragraph, and stopped the run. An empty group in
    # front costs nothing and settles it.
    if out.lstrip().startswith("["):
        out = "{}" + out
    return out


# The mediant divides a psalm verse at the pause, and the book sets it as a
# raised and enlarged asterisk, not the one on a keyboard. `structure.py`
# carries it through as a plain `*` standing on its own: 7,918 of them over
# the book, every one of which was being printed as a keyboard asterisk.
RE_MED = re.compile(r"(?<![^\s])\*(?![^\s])")


def marks(text):
    for mark, tex in MARKS.items():
        text = text.replace(mark, tex)
    # A star standing as a word of its own is the mediant. One inside a word
    # is not, and neither is `**`, which is stray ink.
    return RE_MED.sub(r"\\med{}", text)


def inline(text, base="black"):
    """Convert one line, handling the colour switches in braces.

    A brace pair means "the other colour". Inside a black block it turns the
    text red, and inside a red block it turns the text black.
    """
    parts = re.split(r"\{([^{}]*)\}", text)
    out = []
    for i, part in enumerate(parts):
        body = marks(escape(part))
        if i % 2:
            switch = r"\rubric" if base == "black" else r"\textcolor{black}"
            out.append(f"{switch}{{{body}}}")
        else:
            out.append(body)
    return "".join(out)


def dropcap(line, colour="black"):
    """Split the first word so that lettrine can set a two line initial."""
    body = line.lstrip()
    if not body:
        return ""
    first, rest = body[0], body[1:]
    word, _, tail = rest.partition(" ")
    return (f"\\opening[{colour}]{{{escape(first)}}}"
            f"{{{escape(word)}}} {inline(tail)}")


def convert(text):
    """Turn one markup file into LaTeX lines.

    The body runs in two columns, but a display title and the rubric that
    introduces a part span the full measure. LaTeX cannot span a column from
    inside multicols, so those blocks close the two column body and reopen it
    afterwards. The converter tracks that state here.
    """
    out = []
    block = "text"          # current block tag
    base = "black"          # current base colour
    pending_open = None     # colour of a drop cap waiting for its paragraph
    incols = False
    title = []              # a display title is buffered, to join its lines
    para = []               # body lines waiting to be joined into a paragraph
    rows = []               # the rows of a table, waiting for its end
    widths = []             # the width of each of its columns, as a fraction

    def columns(on):
        nonlocal incols
        if on and not incols:
            out.append(r"\begin{brevbody}")
            incols = True
        elif not on and incols:
            out.append(r"\end{brevbody}")
            incols = False

    def flush():
        """Set the buffered lines as one paragraph.

        The markup holds one line for each line of the scan, because that is
        how the page was read. Those are not the paragraphs of the book, they
        are the line breaks of a book set to a different measure in 1967.
        Emitting one paragraph for each of them stops the text from flowing:
        every line then sits where the scan put it, ragged and unjustified,
        and the book runs about a third longer than the original.

        So join them, and let the typesetter break the text to this measure.
        A paragraph ends where the markup says it ends, at a tag.
        """
        nonlocal pending_open
        if not para:
            return
        joined = ""
        for line in para:
            line = line.strip()
            if not joined:
                joined = line
            elif joined.endswith("-") and line[:1].islower():
                # A word the 1967 compositor broke across his measure. Put it
                # back together, or it reappears in the middle of a line here.
                joined = joined[:-1] + line
            else:
                joined += " " + line
        para.clear()
        if pending_open:
            out.append(dropcap(joined, pending_open))
            pending_open = None
        else:
            out.append(inline(joined, base))
        out.append("")

    def close():
        flush()
        if block == "rubric":
            out.append(r"\end{rubricpar}")
        elif block == "title" and title:
            out.append(f"\\displaytitle{{{r' \\ '.join(title)}}}")
            title.clear()
        elif block == "table" and rows:
            # Each column is set to the width it had on the page, less the
            # padding the table puts on either side of it, or the row runs
            # wider than the measure and LaTeX complains on every page.
            spec = "".join(
                f"p{{\\dimexpr {w:.4f}\\linewidth-2\\tabcolsep\\relax}}"
                for w in widths)
            out.append(f"\\begin{{brevtable}}{{{spec}}}")
            for r in rows:
                cells = [inline(c.strip()) for c in r.split("|")]
                cells += [""] * (len(widths) - len(cells))
                out.append(" & ".join(cells[:len(widths)]) + r" \\")
            out.append(r"\end{brevtable}")
            rows.clear()

    for raw in text.splitlines():
        line = raw.rstrip()

        if line.startswith("#"):
            tag, _, val = line[1:].partition(" ")
            if tag == "office":
                out.append(f"\\office{{{escape(val.strip())}}}")
            elif tag in ("page", "src", "hour", "day"):
                # The liturgical address does not print. It is carried through
                # as a comment so a later web office can read it back.
                out.append(f"% {tag}: {val.strip()}")
            continue

        if not line.strip():
            continue

        # A block tag is a dot followed by a word. The OCR engine sometimes
        # returns a bare dot as a line of its own, and that is stray ink, not
        # a tag.
        if re.match(r"^\.[A-Za-z]", line):
            close()
            tag, _, val = line[1:].partition(" ")
            val = val.strip()
            block, base, pending_open = "text", "black", None

            # The argument of a tag holds the same markup as any other
            # line: a brace pair means the other colour, and `<R>`, `<V>` and
            # the mediant stand in it too. `escape` put the brace on the page
            # instead: 366 of the 577 antiphon labels in this book carry one.
            if tag == "text":
                columns(True)
            elif tag == "rubric":
                columns(True)
                block, base = "rubric", "red"
                out.append(r"\begin{rubricpar}")
            elif tag == "title":
                columns(False)
                block = "title"
            elif tag == "wide":
                columns(False)
            elif tag == "widerubric":
                columns(False)
                block, base = "rubric", "red"
                out.append(r"\begin{rubricpar}")
            elif tag == "rule":
                columns(True)
                out.append(r"\blackrule" if val == "black" else r"\brevrule")
            elif tag == "hour":
                columns(True)
                out.append(f"\\hour{{{inline(val)}}}")
            elif tag == "heading":
                columns(True)
                out.append(f"\\heading{{{inline(val, 'red')}}}")
            elif tag == "bheading":
                columns(True)
                out.append(f"\\bheading{{{inline(val)}}}")
            elif tag == "psalm":
                columns(True)
                out.append(f"\\psalmhead{{{inline(val, 'red')}}}")
            elif tag == "lesson":
                columns(True)
                out.append(f"\\lesson{{{inline(val, 'red')}}}")
            elif tag == "ant":
                columns(True)
                out.append(f"\\ant{{{inline(val, 'red')}}}%")
            elif tag == "open":
                columns(True)
                pending_open = "rubric" if val == "red" else "black"
            elif tag == "table":
                # A grid spans the measure, so it stands outside the two
                # column body. The widths come off the page it was read from.
                columns(False)
                block = "table"
                widths[:] = [float(v) for v in val.split()] or [1.0]
            else:
                print(f"warning: unknown tag .{tag}", file=sys.stderr)
            continue

        if block == "title":
            title.append(inline(line))
        elif block == "table":
            rows.append(line)
        else:
            para.append(line)

    close()
    columns(False)
    return out


PREAMBLE = r"""\documentclass{breviary}
\begin{document}
"""
CLOSING = r"""\end{document}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out")
    ap.add_argument("--fragment", action="store_true",
                    help="omit the preamble, for including in a larger book")
    args = ap.parse_args()

    body = []
    for path in args.files:
        body += convert(Path(path).read_text(encoding="utf-8"))

    text = "\n".join(body)
    if not args.fragment:
        text = PREAMBLE + text + "\n" + CLOSING

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(text)} chars)")
    else:
        print(text)


if __name__ == "__main__":
    main()
