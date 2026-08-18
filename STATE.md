# Where the work stands

2026-08-17, evening.

## Done

Every page of the book is read, structured, set in type, and checked against
the type. The machine part is finished. What is left needs a person or a
decision.

| | |
|---|---|
| parts held | **38 of 38.** The Psalter arrived 2026-08-17 |
| scans | 1,194, each a two page spread |
| page images | 2,388 in `pages/` |
| pages read | 2,386 in `drafts/`; two are blank leaves and hold no type |
| words | **851,459** real words, 934,071 tokens |
| parts set in type | 38 of 38, **2,353 pages** of PDF in `tex/parts/`, no LaTeX errors. Built 2026-08-18 |
| the type checked against the source | longest run absent from the page **5 words** in 851,459; 32 headings out of order |
| spreads cut in the wrong place | **none.** 26 were repaired on 2026-08-17 |
| editions built | one volume 2,322 pages; two volumes 1,418 + 1,491; four volumes 893 to 1,139 |

## The tools

`tools/README.md` describes the chain, what these tools learned about this
book, and what is still wrong with them.

    tools/prepare_all.sh pages          render, split and straighten the scans
    tools/checkpages.py pages           check the images before reading them
    tools/ocr_all.sh ''                 read and structure every page
    tools/audit.py drafts/*.json        pages where the reading went wrong
    tools/unread.py                     ink no word box covers
    tools/proof.py ... -o docs/x/     build a sheet for a person
    tools/proofindex.py docs/         write the page a link opens
    tools/witness.py                    words the book contradicts
    tools/check.py                      what a change did to the book
    onecolumn.txt                       pages not set in two columns
    tools/applyfix.py corrections-*.json put the corrections back
    tools/compile_all.sh                set every part in type
    tools/editions.py                   bind the parts into 1, 2 or 4 volumes
    tools/roundtrip.py                  read the PDF back and check it
    tools/showcolumns.py <page.png>     draw what the column finder saw

`tools/PORTING.md` is for taking these to another book. Four of them hold
nothing about the breviary. The Sarum Missal project has them.

## What is measured, and what is still opinion

The true error rate is measured now, on part 19, four pages read word by word
by Max on 2026-08-17. This is the only measurement of the reading that is not
the engine's opinion of itself.

| | |
|---|---|
| words on those pages | 1,309 |
| the engine marked | 115, 8.8% |
| errors actually found | 168, 12.8% |
| of those, on tokens the sheet greys as punctuation | 79 |
| of those, on real words | 89, **6.8%** |
| real-word errors that carried a mark | 55 of 89, **62%** |
| marks that were false alarms | 60 of 115, 52% |

So checking only the marked words finds about three fifths of the real errors,
and half the marked words were right. The other 79 corrections were stray ink
and bleed through, read as `|`, `}`, `~`, `*`.

**That was the largest single cost in proofing this book, and the sheet
addresses it now.** The book prints none of `| \ { } ~ _ = < >` on any page,
so a token made only of those characters is always wrong: 34,713 of them,
about 15 a page. The sheet strikes them through, and every page carries one
button, **delete the stray ink**, which removes all of them at one press. A
click puts any one back. They stay out of the word count and out of the error
rate, so the rate the sheet reports measures real words and agrees with the
audit. `tools/README.md` holds the reasoning, under "Two kinds of mark".

**It is checked now, and it holds.** Max read the 18 repair pages in full on
2026-08-17 and sent 117 corrections. Eight of those pages carry text a person
could correct at all, and they give 94 real-word errors over 1,567 words:
**6.0%**, against 6.8% on part 19. Two samples, chosen by different means,
agree.

| | part 19 | the repair pages | together |
|---|---|---|---|
| pages read in full | 4 | 8 of 18 | 12 |
| words | 1,309 | 1,567 | 2,876 |
| real-word errors | 89 | 94 | 183 |
| the rate | 6.8% | 6.0% | **6.4%** |

Take 6.4% as the reading's true error rate on real words. It is measured, on
12 pages, by a person, twice.

## More than half of the worst pages fail before a word is read

The other 10 of the 18 carry 1,984 words and Max corrected none of them. Not
because they are clean: because the fault is not a word.

| what Max wrote | pages |
|---|---|
| "this is a calendar", "shouldn't be split" | 3 |
| "not split correctly", "split in the wrong spot" | 4 |
| "this is a table, should be rebuilt as a table" | 1 |
| "a full page, shouldn't be split into columns" | 1 |
| "zoomed in way too much, not able to make any corrections" | 1 |

So 56% of the words on the worst 18 pages sit on a page the column finder
mishandled. `unread.py` chose these 18 by measuring unread ink, and what it
really found was the column finder failing, not the engine failing.

**A calendar and a table are not two columns of prose.** The finder splits
every page down the middle, and on those pages every line is cut in half. The
Liturgical Calendar is 3 pages here and the whole part is more. Nothing
downstream can mend it, and no proofreader can either. See `showcolumns.py`
before believing any measurement of one of these pages.

## The turn of the page, checked over all of it

`pagelib.deskew` gets **2,328 of 2,388 pages exactly right**: the finer search
finds nothing at all on them. 60 pages ask for 0.3 degrees or more.

Those 60 were read both ways on 2026-08-17 and the better reading kept. **16
came out clearly better turned, 18 clearly worse, 26 much the same**, so this
is a list and not a rule — turning all of them costs 0.48 of a point. The 16
went from mean confidence 80.3 to **89.8**, and from 20-36% marked to 7-16%.

`turn.txt` names them and `pagelib.turn_further` applies it. The book now
stands at 851,459 words, mean confidence 89.14, 11.96% marked.

Two faults looked for and not found: no page is sheared, and no page wants a
turn that `deskew` did not already make. Both were caught by drawing the line
on the page, not by a number.

## The two ink layers were being put back in the wrong order

The black and the red are read apart, which is what makes the reading good,
and were merged by vertical position alone. Where both colours share one
printed line — a red `℣`, a red `Ant.`, a red chapter reference inside black
text — which came first was decided by the height of the glyphs rather than by
where they stand across the measure.

**13,325 of 63,677 handovers, 20.9%, over 2,274 of the 2,386 pages.** This is
Max's "V bar and R bar are very typically out of order".

`merge_layers` in `ocr.py` gathers one printed line from both layers, then
reads it across. **20.9% down to 4.0%.** All 934,071 words are unchanged, and every page
has the same printed lines word for word; only the order of the blocks moved. Applied on 2026-08-17 without reading a page again, and
every page structured afterwards.

## The book is its own second witness

`witness.py` takes every seven words of the book, blanks the middle one, and
groups by the six around it. Where the book puts one word in that place many
times over and something else once, the once is probably wrong.

**3,594 words on 1,438 pages, in two seconds. 1,714 of them score 80 or
better, so nothing else on the sheet marks them at all.** That is the class of
error no other check on this project can reach: a real word, spelt right, that
the engine was sure of.

    'inchiding'  the book says 'including'  4x   confidence 89
    'Pather'     the book says 'father'      7x   confidence 91
    'Soirit.'    the book says 'spirit'      4x   confidence 89
    'ts'         the book says 'is'          2x   confidence 95

It proposes and never decides. Some of what it finds is the book really
differing from itself, and a person must look. The proof sheet underlines
these in green, `Tab` reaches them, and the tooltip says what the book puts
there elsewhere. They are counted apart from the engine's own doubts, so every
measurement already taken stays comparable.

## What to do next

0. **The sheets stand at a link now.**
   [arathalion.github.io/dominican-breviary](https://arathalion.github.io/dominican-breviary/),
   served by GitHub Pages out of the `docs` folder of this repository, which is public now.
   A proofreader follows the link and works in the browser. Nothing is
   downloaded and nothing is installed, and the corrections go back on the
   clipboard, pasted into a message. Send the link to the friends who offered.

1. **`docs/proof-00-Repairs`, 18 pages.** The worst 18 in the book, chosen
   by measurement rather than by eye: `unread.py` finds, on every page, the
   ink that no word box covers, and these carry two to twenty three times as
   much of it as the rest of their part. They mark 20.3% of their words
   against about 9% for the book. Two faults live there and both need a
   person: a title cut in half by the column split, and bleed through read as
   punctuation. Write what a cut heading should say in the note box, and
   press **delete the stray ink** for the bleed through.

2. **Proof a part.** Six small parts are built and unclaimed, 4 to 14 pages
   each, and the landing page lists them smallest first. Tick **I read this
   page in full** on a few pages of whatever you take: that is what turns the
   engine's opinion into a measurement, and one part is not enough to trust.

   Part 19 marks 4.7% of its words now, not 8.8%. Max's corrections went back
   into the drafts, and every sheet is built again from them.

3. **Settle the binding, and the volume split follows it.** Find a binder, ask
   their greatest pages for one volume and whether they sew, then split to
   fit. The Guild of Book Workers directory at guildofbookworkers.org/find is
   the place to start; binders who rebind altar missals already solve this
   exact problem. Manufacturers will not take an order for five.

   On bible paper the two volume edition is 35 and 37 mm, which is the 1967
   edition's own size. On ordinary digital stock the four volume edition is 38
   to 48 mm. Max expects no bible paper at first, so four volumes is the
   working assumption.

4. **Half of that is mended, and the list says which half.** `onecolumn.txt`
   names the pages this book does not set in two columns, and `ocr.py` reads
   it. 28 pages, re-read on 2026-08-17: the whole Liturgical Calendar, the
   Bull of Clement XII, the table of movable feasts, and one full page of the
   preliminaries. The Bull went from `recourse, if : This prov the force ol`
   to `recourse, if such be deemed advisable, to the Secular Arm.` Confidence
   on it rose from 91.1 to 93.5.

   **There is no detector, and that was tried.** A sixth attempt on
   2026-08-17 measured ink at the middle of the measure: 6% to 20% on the
   pages Max named, 7% to 19% on ordinary two column pages. They do not
   separate. `crossed`, which the drafts already carry, fires on 247 pages
   and on only 9 of Max's 10. So the list is set by hand, and the file says
   why. Add a page when a proofreader reports one.

   **A calendar is still not a table.** It is no longer cut in half, but it
   is read as running text and it scores 53 to 92. The rows and the columns
   of it are lost. That wants `totex.py` to set a table, and nobody has
   started.

5. **The gutter in the wrong place. Not mended, and it is the harder half.**
   Max named 4 pages: `13-...-0001a`, `13-...-0001b`, `16-...-0040b`,
   `16-...-0048b`. These are two columns of prose, so the list above is the
   wrong tool; the finder puts the split at the wrong x. Nothing detects it
   and nothing reports it.

6. **Four pages carry a strip of the facing leaf, and it costs them a column.**
   This is Max's "zoomed in way too much" on `00-Preliminary-Pages-0004a`.
   The page is almost blank, and the only ink on it is a sliver of the page
   opposite, standing at the edge. `type_block` then reaches from x=5 to the
   far margin, so the split lands near the edge and column 1 comes out **4
   pixels wide**. The proof sheet showed Max those 4 pixels.

   It is small and it is exactly measurable: 6 crops under 60 px wide, over
   4 pages, out of 4,772 crops. `00-Preliminary-Pages-0002a`,
   `00-Preliminary-Pages-0004a`, `03-Liturgical-Calendar-0012b`,
   `04-Ordinary-of-the-Divine-Office-0001a`. Every one is a near blank leaf.

   The fault is in the spread split, not the column finder, so `onecolumn.txt`
   is the wrong tool for it. `split_spread` and `crop_to_paper` leave the
   strip behind. A crop under 60 px wide should be a fault the runner reports,
   the way "nothing to read" already is.

7. **The 32 headings the round trip reports out of order.** Nobody has looked.

8. **Mend the structure in the sheet. Steps 1 and 2 are done.** The sheet
   shows what `structure.py` made of each page, behind **show the structure**,
   and every block carries four buttons: join, up, down, and drop capital. No
   button changes a tag to anything else, because the ink colour decides the
   tag and is right 99 times in 100.

   The corrections go to `structfix/<page>.json` and `applystructure.py`
   applies them after `structure.py` runs, every time. Building twice gives
   the same file: 2,386 of 2,386 pages come back byte for byte with no
   corrections, and a corrected page is stable on the second run.

   **Step 3 is done in the sheet and not in the type.** Press **set the
   columns** on a page the book does not set in two columns, click the scan to
   drop a guide, and the words stand in cells. A guide is a fraction of the
   width, so it survives any size, and it travels back as `cols`. 54 lines of
   the first calendar page became 32 rows.

   Two ideas were measured and both failed. A detector cannot find the guides:
   empty bands give 4 columns on a page that has 5. And reading a column on
   its own is **worse** than reading the page: 52, 47 and 71 against 74.5 for
   the whole page, because cropping loses the engine its context.

   **The calendar is the worst read part of the book**: 32.4% of its words
   marked against 11.8% for the rest, and the small roman numerals are mostly
   wrong. The grid makes it correctable, which it was not before. Expect to
   type those two columns rather than correct them. It is 24 pages.

   **The calendar is set in type now.** `.table` carries the width of every
   column as a fraction of the measure, `totex.py` turns those into a
   `brevtable`, and `breviary.cls` stands the grid outside the two column
   body. The whole 24 page calendar sets from one set of guides,
   `0.109 0.279 0.424`, and 854 rows come out. An ordinary part still
   compiles unchanged.

   The guides were measured rather than placed by eye, so they are a first
   try. Open a calendar page in the sheet: the guides in use are drawn on the
   scan already, and moving one replaces them.

   What is still wrong is the reading, not the shape. The numerals in the two
   narrow columns are largely wrong and nothing mends that.

9. **A drop capital is missing wherever a page opens a text.** Max named it on
   6 of the 8 pages he could correct: "missing drop cap". The engine does not
   read the letter, and `structure.py` supplies it from the drop capital found
   on the page, so this fires only when the finder misses the capital.

## What the original was

Measured from the folio numbers printed in the scans, not guessed. The 1967
edition was **two volumes**.

| pages | Volume I | Volume II |
|---|---|---|
| 1&ndash;17 | Ordinary | the same |
| 18&ndash;215 | Psalter, seven days | the same |
| 216&ndash; | Season, Advent to Trinity | Season, Trinity to the 24th Sunday |
| | Saints Vol 1 | Prayers and Homilies, Saints Vol 2, Saints OP, Missions |
| [2]&ndash;[245] | Commons, Little Office, Office of the Dead | the same |

Both Propers of the Season begin at plain page 216, so each volume restarts.
The Commons carry a second, bracketed series **because** that block is printed
identically in both. The Psalter reads 22 to 216 in the scans, and the Proper
of the Season begins at 216 — the join is exact, and it was predicted before
the Psalter files existed here.

## Files

| kept | what it is |
|---|---|
| `pages/`, `drafts/`, `structured/` | the corrected output |
| `pages.old/`, `drafts.old/`, `structured.old/` | the previous output, 13 GB. Delete when satisfied |
| `tex/parts/` | one PDF a part |
| `tex/editions/one\|two\|four/` | the same book bound three ways |
| `docs/` | the proof sheets. GitHub Pages serves this folder, and it is what a proofreader opens |
| `.git` | the whole project, at github.com/arathalion/dominican-breviary. 548 KB tracked, the 23 GB of derived work ignored |
| `docs/corrections/` | what a proofreader sends back |
| `compile-all.log` | the typesetting result for each part |
| `plan.html` | the full plan, published at claude.ai/code/artifact/c1c8506d-0b51-47f1-8e9c-87b46660fe12 |

Use the `arathalion` GitHub account for this project, never `max-doty`.

## Open faults

- **A title that runs across both columns is cut in half.** Five attempts to
  detect this automatically have failed, the last on 2026-08-17. All five are
  written up in `tools/README.md` so a sixth does not start from nothing. It
  is findable per page with `unread.py` and repairable by hand in the sheet.
- **Bleed through is read as punctuation.** 79 stray tokens in 1,309 words on
  the pages measured. Lowering the ink threshold from 145 to 125 removes only
  a fifth of them and risks real type, so it was not done. A stricter mask is
  right for *measuring shapes* and is used that way; it is wrong for reading.
- **Drop capitals are found but the letter is not supplied**, and the psalm
  numbers in the margin are not captured at all. Both are Max's notes from
  part 19 and neither is addressed.
