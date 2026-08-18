#!/usr/bin/env python3
"""Write the page a proofreader lands on, and link every sheet from it.

Usage:
    proofindex.py proofs/            write proofs/index.html

A sheet used to reach a person as a folder: download the repository, unzip
it, find the part, open `index.html`. That is three steps and 17 MB before
any work starts. The sheets stand at a web address now, so a person follows
one link. This page is what that link opens.

The numbers come out of the sheets themselves, so this page cannot disagree
with them. Build the sheets first, then build this.
"""
import argparse
import html
import re
from pathlib import Path

# `proof.py` writes these five numbers into the head of every sheet, and this
# is where they are read back. Change one there and change it here.
STAT = re.compile(r"<span>(pages|words|to check|that is|stray marks) "
                  r"<b>([0-9.,%]+)</b></span>")

# The same palette the sheets use, and the same switch. See `proof.py`.
LIGHT = """--bg:#FCFBF9;--ink:#17140F;--mute:#6E675E;--rule:#E1DBD2;
      --warn:#B03127;--good:#2E6B4C;--bar:#F4F1EC"""
DARK = """--bg:#232019;--ink:#E6E0D4;--mute:#B0A79A;--rule:#3C372E;
      --warn:#F09080;--good:#8FD1A8;--bar:#2C2820"""

CSS = ("""
:root{""" + LIGHT + """}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){""" + DARK + """}}
:root[data-theme="dark"]{""" + DARK + """}
:root[data-theme="light"]{""" + LIGHT + """}
""" + """
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);margin:0 auto;padding:3rem 1.5rem 6rem;
     max-width:52rem;font:16px/1.6 ui-serif,Georgia,serif}
h1{font-size:1.7rem;font-weight:400;margin:0 0 .4rem}
h2{font-size:1.1rem;font-weight:400;margin:2.5rem 0 .6rem;
   padding-top:1rem;border-top:1px solid var(--rule)}
p{margin:0 0 1rem;color:var(--ink)}
p.sub{color:var(--mute);font-size:.95rem}
ol{padding-left:1.2rem;color:var(--ink)}
li{margin-bottom:.4rem}
a{color:inherit}
table{border-collapse:collapse;width:100%;margin:1rem 0;
      font:13px/1.5 ui-monospace,Menlo,monospace}
th{text-align:left;font-weight:400;color:var(--mute);border-bottom:1px solid var(--rule);
   padding:.5rem .6rem}
td{border-bottom:1px solid var(--rule);padding:.55rem .6rem;vertical-align:baseline}
td.n{text-align:right;color:var(--mute)}
td a{font-weight:600;text-decoration:none;border-bottom:1px solid var(--rule)}
td a:hover{border-bottom-color:var(--ink)}
.first{background:var(--bar)}
.tag{font:11px ui-monospace,Menlo,monospace;color:var(--warn);
     border:1px solid var(--warn);border-radius:3px;padding:.05rem .35rem}
.note{background:var(--bar);border-left:3px solid var(--rule);
      padding:.9rem 1.1rem;margin:1.5rem 0;font-size:.95rem}
kbd{font:12px ui-monospace,Menlo,monospace;border:1px solid var(--rule);
    border-bottom-width:2px;border-radius:3px;padding:0 .3rem}
#theme{position:fixed;top:1rem;right:1rem;font:11px ui-monospace,Menlo,monospace;
       color:var(--mute);background:var(--bar);border:1px solid var(--rule);
       border-radius:3px;padding:.35rem .6rem;cursor:pointer}
#theme:hover{color:var(--ink)}
""")

# The switch, and the same words the sheets use. It writes the same key, so a
# person chooses once and every sheet follows.
JS = """
const T = ["", "light", "dark"];
const W = {"": "theme: browser", "light": "theme: light", "dark": "theme: dark"};
const b = document.getElementById("theme");
function paint(t){
  if(t) document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
  b.textContent = W[t];
}
paint(localStorage.getItem("proof:theme") || "");
b.onclick = () => {
  const t = T[(T.indexOf(localStorage.getItem("proof:theme") || "") + 1) % T.length];
  localStorage.setItem("proof:theme", t);
  paint(t);
};
"""


def read(sheet):
    """Take the numbers a sheet already prints in its own head."""
    stats = dict(STAT.findall((sheet / "index.html").read_text(encoding="utf-8")))
    return {k: stats.get(k, "") for k in
            ("pages", "words", "to check", "that is", "stray marks")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="the folder holding the proof-* sheets")
    args = ap.parse_args()
    root = Path(args.root)

    rows, repairs = [], None
    for sheet in sorted(root.glob("proof-*")):
        if not (sheet / "index.html").exists():
            continue
        row = (sheet.name, read(sheet))
        # The repair sheet is not a part of the book. It is the worst 18 pages
        # of it, and it stands on its own above the parts.
        if sheet.name == "proof-00-Repairs":
            repairs = row
        else:
            rows.append(row)

    def cells(name, s, first=False):
        title = name.replace("proof-", "").replace("-", " ")
        return (f'<tr class="{"first" if first else ""}">'
                f'<td><a href="{html.escape(name)}/">{html.escape(title)}</a></td>'
                f'<td class="n">{s["pages"]}</td><td class="n">{s["words"]}</td>'
                f'<td class="n">{s["that is"]}</td>'
                f'<td class="n">{s["stray marks"]}</td></tr>')

    head = ('<tr><th>part</th><th class="n">pages</th><th class="n">words</th>'
            '<th class="n">marked</th><th class="n">stray marks</th></tr>')
    # The smallest part first: a person goes through the whole loop once, on
    # four pages, before they spend an afternoon on twenty two.
    rows.sort(key=lambda r: int(r[1]["pages"] or 0))
    body = "".join(cells(n, s, i == 0) for i, (n, s) in enumerate(rows))

    rep = ""
    if repairs:
        n, s = repairs
        rep = (f'<h2>Start here <span class="tag">the worst 18 pages</span></h2>'
               f'<p>These 18 pages are the worst in the book, and a machine chose '
               f'them. <code>unread.py</code> measures, on every one of the 2,386 '
               f'pages, how much ink no word box covers. These carry two to twenty '
               f'three times as much of it as the rest of their part.</p>'
               f'<p>Two faults live here, and both need a person. A title that runs '
               f'across both columns comes out cut in half: write what it should say '
               f'in the note box. Bleed through from the back of the leaf comes out '
               f'as stray marks: press <b>delete the stray ink</b>.</p>'
               f'<table>{head}{cells(n, s, True)}</table>')

    page = (
        '<!doctype html><meta charset=utf-8>'
        '<title>Proofing the Dominican Breviary</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<style>{CSS}</style>'
        '<script>try{var t=localStorage.getItem("proof:theme");'
        'if(t)document.documentElement.dataset.theme=t}catch(e){}</script>'
        '<button id="theme">theme</button>'
        '<h1>Proofing the 1967 Dominican Breviary</h1>'
        '<p class="sub">Thank you for helping. A machine read all 2,386 pages of '
        'this book. The machine is good but it is not right, and this is where a '
        'person corrects it.</p>'
        '<p class="sub">You need no software. Open a part below, and work in this '
        'browser. Nothing to download, and nothing to install.</p>'
        '<h2>What to do</h2>'
        '<ol>'
        '<li>Open a part. Tell Max which one you take, so that two people do not '
        'take the same one.</li>'
        '<li>Put your name in the box at the top left.</li>'
        '<li>Press <kbd>Tab</kbd>. It goes to the first word the machine doubted. '
        'Type the right word and press <kbd>Enter</kbd>. Press <kbd>Esc</kbd> if the '
        'machine was right. Press <kbd>Tab</kbd> again for the next one.</li>'
        '<li>Press <b>delete the stray ink</b> on each page. That takes off the '
        'marks the book never printed, which is bleed through from the back of the '
        'leaf. Click any one of them to keep it.</li>'
        '<li>Press <b>send corrections</b> before you stop. Your work goes on the '
        'clipboard. Paste it into a message to Max.</li>'
        '</ol>'
        '<div class="note">The browser remembers your work, so you can close a part '
        'and come back to it. Press <b>send corrections</b> at the end of each '
        'sitting anyway. It costs nothing, and then nothing can be lost.</div>'
        '<h2>Read a few pages in full</h2>'
        '<p>Each page has a box: <b>I read this page in full</b>. Tick it only if '
        'you read every word of the page against the scan, and not only the words '
        'the machine marked.</p>'
        '<p>This matters more than the corrections do. The machine’s opinion of '
        'itself is not a measurement. A few pages read word by word tell us the true '
        'error rate, and that decides whether the whole book can be trusted. Two or '
        'three pages in full is plenty. Do the rest the fast way, with '
        '<kbd>Tab</kbd>.</p>'
        f'{rep}'
        '<h2>The parts</h2>'
        '<p class="sub">These are the small parts of the book. They are all '
        'independent, so take whichever you like. The four big Propers run to 576 '
        'pages each, and nobody should meet one first.</p>'
        f'<table>{head}{body}</table>'
        '<p class="sub">The two marks: the book opens a great many lines with '
        '℟ and ℣. No keyboard carries them. Type <kbd>R/</kbd> and '
        '<kbd>V/</kbd>, and the sheet writes the true mark.</p>'
        f'<script>{JS}</script>')
    out = root / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(rows)} parts"
          f"{' and the repair sheet' if repairs else ''}")


if __name__ == "__main__":
    main()
