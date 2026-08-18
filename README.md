# The 1967 Dominican Breviary, in English

A machine read all 2,386 pages of this book from scans, and this is the chain
that turns that reading into a book again. Max is setting it for himself and
for a few friends.

**Proofreading? Go to
[arathalion.github.io/dominican-breviary](https://arathalion.github.io/dominican-breviary/).**
That is the whole thing: open a part, work in the browser, paste your
corrections into a message. Nothing to install.

## Where the work stands

`STATE.md` holds the numbers and is kept current. In short: every page is
read, structured, set in type and checked against the type. 38 parts, 2,353
pages of PDF, 851,459 words. The machine part is finished. What is left needs
a person, or a decision about the binding.

The reading is **6.4% wrong on real words**, measured by a person reading 12
pages word by word, not by asking the engine what it thought of itself.

## The chain

    prepare_all.sh   render, split and straighten the scans   -> pages/
    checkpages.py    look at the images before reading them
    ocr_all.sh       read each page, both ink colours apart   -> drafts/
                     then infer its structure                 -> structured/
    proof.py         put the reading beside the scan          -> docs/
    applyfix.py      put a person's corrections back          -> drafts/
    totex.py         set the type                             -> tex/
    editions.py      bind the parts into 1, 2 or 4 volumes
    check.py         say what a change did to the book
    witness.py       words the book contradicts elsewhere in itself

`tools/README.md` is the long version: what every tool learned about this
book, and what is still wrong with it. It is worth reading before changing
anything, because it records seven detectors that failed and why.

## What is tracked here

548 KB, and none of it can be made again: the tools, the hand-set lists
`onecolumn.txt` and `turn.txt` and `structfix/`, `tex/breviary.cls`, and the
proof sheets in `docs/`.

The 23 GB that can be made again — the scans, the drafts, the markup, the
PDFs — is ignored. Everything in this repository is either a decision somebody
made or the code that acts on it.
