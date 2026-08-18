# The tools

Taking these to another book? Read `PORTING.md`. Four of them hold nothing
about the breviary and run as they stand.

The chain runs in one direction. Each step writes files that the next step
reads, and every step can be stopped and started again.

    scans (PDF)  ->  pages/  ->  drafts/  ->  structured/  ->  tex/

| step | tool | writes |
|---|---|---|
| render, split and straighten the scans | `prepare_all.sh` | `pages/` |
| check the pages before reading them | `checkpages.py` | a report |
| set every part in type | `compile_all.sh` | `tex/parts/` |
| bind the parts into volumes | `editions.py` | `tex/editions/` |
| read a page into draft markup | `ocr_all.sh` | `drafts/` |
| ask the engine for words and boxes | `tsv.py` | (used by `ocr.py`) |
| infer the structure of a page | (inside `ocr_all.sh`) | `structured/` |
| find pages where the reading went wrong | `audit.py` | a report |
| find ink no word box covers | `unread.py` | a report |
| put the reading beside the scan | `proof.py` | `proofs/proof-*/` |
| write the page a proofreader lands on | `proofindex.py` | `proofs/index.html` |
| put the corrections back | `applyfix.py` | `drafts/` |
| show what the column finder saw | `showcolumns.py` | an HTML sheet |
| set the type | `totex.py` | `tex/` |
| read the PDF back and check it | `roundtrip.py` | a report |
| typeset one part, end to end | `tex/parts/` | one PDF a part |

## Running it

    tools/prepare_all.sh pages          every scan, six parts at a time
    tools/checkpages.py pages --every 8 a sample, before reading anything
    tools/ocr_all.sh ''                 every page that is ready
    tools/ocr_all.sh 04-Ordinary        one part, with a proof sheet
    PROOF=0 tools/ocr_all.sh ''         a bulk run, without proof sheets
    tools/ocr_small.sh                  every part except the four big Propers

`ocr_all.sh` takes `PAGES`, `DRAFTS`, `STRUCT` and `JOBS` from the environment,
so a second set of pages can be read without disturbing the first.

## Proofing a part

The proof sheet is where a person works. It holds the corrections, and
`applyfix.py` puts them back into the drafts.

    tools/ocr_all.sh 26-Common-of-a-Virgin      build the sheet
    tools/proofindex.py proofs/                 write the landing page again
    git -C proofs commit -am sheets && git -C proofs push
    tools/applyfix.py corrections-26-*.json -n  say what would change
    tools/applyfix.py corrections-26-*.json     change it
    tools/ocr_all.sh 26-Common-of-a-Virgin      structure the pages again

A sheet is a folder: `index.html`, and the colour crops beside it in `img/` as
WebP. Part 26 is 5.4 MB. Give `-o` a name that ends in `.html` for one file
with the images inside it, and expect 87 MB for the same part.

The sheets stand at
[arathalion.github.io/breviary-proofs](https://arathalion.github.io/breviary-proofs/),
which GitHub Pages serves out of the `proofs` repository. A proofreader
follows one link and works in the browser. Nothing is downloaded, and nothing
is installed. Push the repository and the site follows about a minute later.

Build the sheets first and `proofindex.py` second. It reads the numbers back
out of the sheets, so it cannot disagree with them.

Corrections come back on the clipboard, as text in a message, because a file
was the hardest step of the whole task for the people doing it. **download
corrections** still writes the file, for a browser that will not copy.

In the sheet, click a word to correct it. Press <kbd>Tab</kbd> to go to the
next marked word, <kbd>Enter</kbd> to keep what you typed, and <kbd>Esc</kbd>
to say the engine was right. Empty a word to delete it. Type two words in
place of one to add a word. Click the scan to see it at full size. The bar at
the top counts the work.

Press **delete the stray ink** on a page to take off every mark the book
cannot have printed. See "Two kinds of mark" below.

The button at the right of the bar says **theme**, and it turns between the
browser's own setting, light and dark. A scan of white paper stands beside
every column, so light suits this work and a person should be able to say so
whatever their machine is set to. The dark ground was near black and it was
hard to look at for an hour; it is lifted well off black now, and the type is
softened to 12.4 to 1 against it. `LIGHT` and `DARK` at the head of `proof.py`
hold the two palettes, and `proofindex.py` repeats them. The choice goes in
`localStorage` under one key, so it holds over every sheet.

Type `R/` or `V/` for ℟ and ℣, or use the two buttons in the bar. No keyboard
carries these, and no engine reads them, but the book opens a great many lines
with them. `structure.py` takes the true glyph anywhere in a line and turns it
into `<R>` or `<V>`. Its own rules only ever look at the first word of a line,
because they must guess from junk and a wrong guess corrupts what a reader
says aloud. A person's glyph is not a guess.

Put your name in the box at the left of the bar. It goes into the file name
and into the file, so two people can proof the same part and both files come
back. `applyfix.py` takes any number of them at once.

Tick **I read this page in full** on a page you read word by word, including
the words the engine was sure of. Only those pages give a true error rate. The
bar shows two figures: how many of the marked words were wrong, and the error
rate over the pages you read in full. The first measures the engine's opinion
of itself. The second measures the reading.

The note box on each page takes anything the words cannot: a heading cut in
half, a missing line, the wrong order.

The browser holds the corrections, so the sheet can be closed and opened
again. Press **send corrections** before you move to another part.
`applyfix.py` can run over the same file twice without doubling anything, and
it refuses any correction whose word no longer says what the sheet saw.

## Two kinds of mark, and only one of them is a person's work

A token of one to three characters, holding no letter and no digit, is 8.8 per
cent of everything the engine returns: 82,424 tokens over the book. The sheet
used to grey all of them and call them "a mark, recovered by rule". That was
right for a few of them and wrong for most.

Two different things hide in there.

**A versicle or a response mark.** No engine reads U+2123 or U+211F, so it
returns junk such as `©` or `R7`, and `as_mark` in `structure.py` puts the
true glyph back by rule. About 1,650 tokens. A person must not touch these.

**Stray ink, and bleed through from the back of the leaf.** The engine takes
it for faint type and returns `|`, `}`, `~`, `_`, `=`, `{`, `\`, `<` or `>`.
The book prints none of those characters on any page, so a token made only of
them is always wrong. 34,713 tokens, about 15 a page.

That second kind was the largest single cost in proofing this book. On the
four pages Max read word by word on 2026-08-17, 79 of the 168 errors were
these: 47 per cent of the work, and the sheet gave a person no cheap way to
remove them. `RE_MARKISH` could not tell the two apart, so it treated the
34,713 like the 1,650.

`RE_STRAY` in `proof.py` names the characters the book cannot print. The sheet
strikes those tokens through and puts one button on every page: **delete the
stray ink**. One press removes every one of them, and a click on any one puts
it back. Each removal is an ordinary deletion in the corrections file, with
the word that follows it named, so `applyfix.py` needs no change and still
never cuts twice.

A stray mark stays out of the word count, out of the Tab pass, and out of the
error rate, and the bar counts it on its own. This matters: the word count
never held these tokens, so counting a removal as an error would put it over a
total that does not contain it. The rate the sheet reports now measures real
words, and it agrees with `audit.py`.

The nine characters are chosen to be safe, not complete. `*`, `;`, `:`, `.`,
`,` and `-` are also stray far more often than not, but the book really prints
all of them — `*` opens the second half of every psalm verse — so they stay
grey and a person deletes them one at a time. That leaves 2,084 stray tokens
this cannot reach, against 34,713 it can.

## Read a page again and the sheet must be told, twice

`onecolumn.txt` changed the shape of 28 crops, and two caches held the old
shape until each was made to notice.

- **`proof.py` wrote a WebP only when none stood there already.** A page that
  goes from half the measure to all of it keeps a half width scan beside the
  text of the whole page. The calendar showed 361 pixels of a 1,256 pixel
  page. The crop wins now whenever it is the newer file.
- **A page that loses a column leaves its old crop behind.** Nothing names it
  and it stays in the folder. The folder is the sheet, so `proof.py` deletes
  any image the page it just wrote does not name.

Check it with the sizes, not by eye: every `img/*.webp` in a sheet must match
`drafts/crops/*.png` of the same name. 195 images over 8 sheets, none
mismatched, none orphaned, on 2026-08-17.

**A proofreader saw this before any check did.** Max opened the page and said
the text was full width and the picture was not.

## The sheet shows the structure now, and the structure is full of stray ink

`proof.py` reads `structured/*.md` and shows it under the columns, behind a
button in the bar. It is **read only**. Nothing here mends the structure yet.
It was built first because every one of Max's 18 notes on the repair pages was
structural, and none of us knew where those faults really sat.

The first page it was pointed at answered that. A lone `|` in the red layer
becomes a `.rubric` block of its own, and `| Lesson ix` comes out as a
heading carrying a stray bar. Measured over all 2,386 pages:

| tag | blocks | nothing but stray marks | opens with a stray mark |
|---|---|---|---|
| `.text` | 22,970 | 324, 1.4% | 1,899, 8.3% |
| `.rubric` | 16,019 | **1,660, 10.4%** | 2,902, 18.1% |
| `.heading` | 1,084 | 7, 0.6% | 84, 7.7% |
| `.bheading` | 1,290 | 12, 0.9% | 40, 3.1% |
| `.open` | 3,245 | 0 | 3, 0.1% |

**One rubric in ten is not a rubric.** It is bleed through from the back of
the leaf, given a block of its own and a tag, and `totex.py` will set it in
red in the book.

So stray ink is not only 47% of the word errors. It manufactures structure as
well, and the two faults have one cure: **delete the stray ink**, then
`applyfix.py`, then structure the page again. The phantom rubrics go with it.

`applyfix.py` deletes the structured page when it changes a draft, so the
stale markup cannot be used by mistake. Run the structure step afterwards or
the sheet has nothing to show: 13 pages sat that way after Max's corrections
on 2026-08-17.

## Mending the structure: four gestures, and none of them sets a tag

Press **show the structure** in the bar, and every block gains four buttons.

| | |
|---|---|
| ↴ | join this block to the one above it |
| ↑ ↓ | move it one place |
| ¶ | it opens with a drop capital |

**There is no way to change a tag to anything but `.open`, and that is on
purpose.** `structure.py` decides `.rubric` from the ink colour, which is
measured rather than inferred: `want = "rubric" if layer == "red" else "text"`.
Of 2,255 blocks opening with a word this book sets in red, 21 came out as
plain text. It is right about 99 times in 100. What goes wrong is which block
a line sits in, and the four gestures say exactly that.

`.open` is the one exception, because a drop capital is typography that a word
correction cannot record. Correcting `ehold,` to `Behold,` gives the right
letters and leaves `totex.py` setting ordinary type where the book sets a
drop capital.

### Where the corrections live, and why not in the markup

`structure.py` builds `structured/*.md` again from the draft every time a word
changes, and `applyfix.py` deletes that file when it changes a draft. An edit
of the markup would be thrown away on the next run.

So `applyfix.py` writes the structural corrections to `structfix/<page>.json`,
and `_structure_page.sh` runs `applystructure.py` after `structure.py` every
time. The markup is built, then mended, in that order, always.

    structure.py    draft   ->  structured/page.md
    applystructure  + structfix/page.json  ->  structured/page.md

**Run it twice and the answer is the same.** Checked on 2026-08-17: with no
corrections at all, 2,386 of 2,386 pages come back byte for byte identical,
and a page with corrections gives the same file on the second run as the first.

Every correction carries the text the sheet saw. `applystructure.py` looks for
the block at that number, and if it no longer says that, it looks for the text
anywhere on the page. If it still cannot find it, the correction is refused and
reported, never guessed at, exactly as `applyfix.py` does with a word.

### A trap worth naming

`line[:1] in ".#"` looks like a test for a tag line and is not. An empty
string is a substring of every string, so that form made a block out of every
blank line: 2,386 phantom blocks, one a page, in both `proof.py` and
`applystructure.py`. Use `line.startswith((".", "#"))`. The round trip test
above is what caught it.

## The calendar: a person places the columns, because nothing else can

Press **set the columns** on a page the book does not set in two columns. The
scan tints, and a click on it drops a guide; a click on a guide takes it away.
The words then leave the flat run and stand in cells.

A guide is held as a fraction of the width of the scan, so it survives the
image being shown at any size, and it travels back in the corrections as
`cols`. Every word in a cell is the same `<w>` the sheet always had, moved
rather than copied, so it keeps its address and its confidence colour and a
person corrects it exactly as before. No new kind of correction was needed.

**One row is not one line.** On a calendar the day number stands once and the
feast beside it runs on for three lines. The widest column is the one that
runs on, so a line putting ink anywhere to its left opens a row, and a line
that does not is the rest of the row above. On the first calendar page that
turned 54 lines into 32 rows, and `6 THE EPIPHANY OF THE LORD I cl.` came out
as one row.

### Two things measured first, and both said no

**A detector cannot find the guides.** Empty bands 18 px or wider give 4
columns on a page that has 5, and the letter column is too narrow to separate
at all. Dropping to 6 px and ignoring the two title lines, which span the
measure and hide every gap, gives usable boundaries — but they still needed a
person's eye to choose among them. Six earlier attempts to find the shape of a
page by measurement failed on this book; this is the seventh.

**Reading a column on its own is worse than reading them together.** The idea
was good: the two ink layers are already read apart, so why not the columns.
Measured on the first calendar page, mean confidence:

| | mean | marked |
|---|---|---|
| the three numeral columns together, psm 6 | 61.8 | 66.7% |
| psm 4 | 65.3 | 61.2% |
| psm 11 | 56.7 | 73.1% |
| Epact alone | 52.0 | 68.0% |
| letters alone | 47.1 | 79.2% |
| day numbers alone | 70.8 | 56.5% |

The whole page through the ordinary pipeline scores 74.5. Cropping loses the
engine the context it uses, and every crop scored worse than the page. So the
guides format the words; they do not read them again.

### The calendar is the worst read part of this book

| | words | mean confidence | marked |
|---|---|---|---|
| the calendar, 24 pages | 5,637 | 78.9 | **32.4%** |
| the rest of the book | 845,806 | 89.2 | 11.8% |

The small roman numerals are the worst of it: `XXVil` at 0, `EXVI` at 37,
`XXiX` at 48, `Fo yiti` at 47 and 56. A grid does not mend that, and nothing
tried on 2026-08-17 mends it. **It makes the calendar correctable, which it
was not before**, and a person should expect to type most of those two columns
rather than correct them. 24 pages.

`totex.py` still has no table, so nothing sets this in type yet.

## The calendar is set in type now, and the chain that gets it there

The guides a person places do not stop at the sheet. They travel the whole way:

    proof sheet   a person clicks the scan          -> cols in the corrections
    applyfix.py   holds them beside the drafts      -> structfix/<page>.json
    structure.py  lays the words into cells         -> .table in the markup
    totex.py      sets each column to its width     -> \begin{brevtable}
    breviary.cls  stands the grid outside multicols -> the printed page

`.table` carries the width of every column as a fraction of the measure, taken
from the page it was read off, so the printed table keeps the shape the 1967
compositor gave it. `totex.py` turns each into
`p{\dimexpr 0.53\linewidth-2\tabcolsep\relax}`; subtracting the padding
matters, or every row runs wider than the measure and LaTeX complains on every
page. A grid spans the measure, so `brevtable` stands outside `brevbody`, the
way a display title already does.

**The row rule lives in two places and they must agree.** `buildGrid` in
`proof.py` and `as_table` in `structure.py` both say: the widest column is the
one that runs on, so a line putting ink to its left opens a row. If they ever
disagree, the proof sheet and the printed book disagree about the book.

**A guide is a fraction of the width of the scan, not of the type.** Measuring
it against the rightmost word instead moves every column on a page whose type
does not reach the edge. On the first calendar page the two differ by 28 px.

The whole 24 page calendar is set from one set of guides, `0.109 0.279 0.424`,
four columns, 854 rows. Occupancy runs 13% / 74% / 74% / 82%: the Epact column
is thin because the book does not print an epact on every line. A fifth guide
at 0.953 was tried and dropped — the column it made was empty on most pages.

**These guides were measured, not placed by eye, so treat them as a first
try.** Open a calendar page in the sheet, press **set the columns**, and the
guides in use are already drawn on the scan; move them and they replace these.

## Turning the page: already done, and the two faults I found were not there

Max asked on 2026-08-17 whether the tilt of a scan costs the reading. It does,
and `pagelib.deskew` already turns every page before it is read: it tries
angles from -3 to +3 degrees in quarter degree steps and keeps the one that
makes the row profile sharpest. Two attempts to find what it leaves behind
both turned out to be measuring something else.

**The residual skew is not skew.** A finer search, 0.05 degree steps on the
already prepared pages, said the calendar wants 0.00 degrees on every page and
some prose pages want up to 0.60. Turning those pages by what it asked for
made the reading **worse**:

| | mean confidence | marked |
|---|---|---|
| `26-...-0002a` as it stands | 76.7 | 30.0% |
| turned a further -0.60 deg | 74.8 | 34.4% |
| `26-...-0004a` as it stands | 88.3 | 12.1% |
| turned a further -0.35 deg | 86.1 | 15.7% |

So `deskew` had already found the right angle, and the finer search was
finding noise.

**The columns are upright, and the shear was an artefact.** Fitting x against
y over the day numbers of a calendar page said the printed columns lean by
2.55 degrees, which would carry a column 51 px sideways down the leaf and drop
words into the cell next door. Drawing that line on the page settled it in one
look: the leaning guide crosses the printed rules and the upright one lies
along them. The drift is in the numbers, not the page — `1` and `25` do not
start at the same x in a column set to the right, and they alternate down the
page.

It also barely mattered: applied to all 24 calendar pages, the lean moved 30
words of 6,507 into another cell, 0.5%.

**The lean control was built anyway and it sits at zero.** Drag a guide in
**set the columns** and every guide on the page leans with it, because one page
has one shear; the corner shows the angle and clicking it stands them up
again. `structfix` carries `lean` and `as_table` applies it. **No page has
needed it.** Keep it at zero unless a scan plainly disagrees with its guides.

**Look at the page.** Both of these were caught that way and neither by a
number.

### Then the same question, over all 2,388 pages

| what the fine search asks for | pages | |
|---|---|---|
| no turn at all | 2,328 | 97.5% |
| 0.30 to 0.60 deg | 43 | 1.8% |
| 0.60 to 1.00 deg | 16 | 0.7% |
| over 1.00 deg | 1 | 0.0% |

So `deskew` gets 97.5% of the book exactly right, and the finer search finds
nothing at all on those pages — not a small angle, zero.

The 60 that ask for 0.3 degrees or more were then read **both ways** and the
better reading kept. It is not a rule and it must not become one:

| | pages |
|---|---|
| clearly better turned | 16 |
| clearly worse turned | 18 |
| much the same either way | 26 |

Turning all of them by what the search asks for costs 0.48 of a point of
confidence. Turning the 16 gains a great deal:

| | mean confidence | marked |
|---|---|---|
| those 16 pages before | 80.3 | 20 to 36% |
| after | **89.8** | 7 to 16% |

The gain is larger than the test predicted, because the test read the whole
type block as one layer while the pipeline reads red and black apart, in each
column. Level type helps that more.

`turn.txt` names the 16 and the angle each wants, and `pagelib.turn_further`
applies it, so a page rendered again keeps its turn. The book now stands at
851,459 words, mean confidence 89.14, 11.96% marked.

**Read it both ways and keep the better.** That is the rule this found, and it
is worth using anywhere the engine's own confidence can choose between two
readings of the same thing.

## The column at the edge is the next page, not a column

Max saw it in the calendar grid on 2026-08-17: the rightmost column is not a
column of the table, it is the facing leaf showing past the fold. The scan of
an `a` page keeps the fold shadow on purpose — `crop_to_paper(left,
keep=("right",))`, because trimming it takes the last letter off the inner
column — and the next leaf comes with it.

On the first calendar page that band holds 20 tokens. Every one is a single
character, twelve of them a bar, and they average 53.2 against 74.5 for the
page. The real letter column beside it holds single characters too — `A`, `b`,
`c` — but not one stray mark.

**So a column more than half stray ink is not a column.** It goes, and its
width goes to the column beside it. That drops the fold on the right and the
edge of the leaf on the left, and the printed calendar came down from five
columns to three.

### Two fixes tried first, and both were worse

`type_block` masks the fold as furniture and then closes gaps up to 8% of the
width, which bridges straight over it to the ink beyond. Making furniture end
a block instead of being bridged looked right and was not: it splits an
ordinary page at the printed rule down its gutter, and part 26 went from
`(15, 1182)` to `(257, 721)`, half a page. Restricting the wall to the outer
15% still cut real type — `16-...` lost 402 px off the right.

Counting words in the outer 7% of the measure does not find this either: 90.9%
of pages have some, on both sides of the fold, and most are the real ends of
real lines.

**The column counts vary across the calendar, 2 to 4.** That is the test
reading different pages differently, and it will settle once a person places
the guides and deletes the stray ink first. Do that before trusting the shape.

## Never stretch a crop, and say so when there is nothing to show

`.col img` carried `width:100%`, so every crop was pulled out to the full
17rem whatever its own size. A crop 4 px wide then rendered 272 px wide and
**114,716 px tall**, and Max asked why the scan of
`00-Preliminary-Pages-0004a` was so big to correct against. `width:auto` lets
a crop keep its own size and `max-width` still holds the big ones in.

A crop that narrow is not a scan of anything. It happens where the spread
split leaves a strip of the facing leaf and the column finder takes the strip
for the page. **The book chooses the threshold itself**: of 4,772 crops, 8 are
92 px or narrower and the next is 281. Nothing lies between, so 150 px catches
every one and cannot reach a real column.

Those 8 now show a line saying how wide the crop is and that the page was split
in the wrong place, instead of a strip of paper a hundred thousand pixels
long. They sit on 5 pages: `00-Preliminary-Pages-0001b`, `-0002a`, `-0004a`,
`03-Liturgical-Calendar-0012b`, `04-Ordinary-of-the-Divine-Office-0001a`. Two
of those have **both** columns under the threshold, so the page has no usable
scan at all.

The fault behind it is in the spread split, not the column finder, and it is
item 6 in `STATE.md`.

## Putting back a character the engine dropped

**A character that belongs to the line goes in with the word beside it.** Click
the word and type the two together: `* Praise` where the reading has `Praise`.
`applyfix.py` splits two words out of one at that address, so the star arrives
as a word of its own. The `*` button in the bar does it without typing —
℟ and ℣ stand **instead** of the word, because there the word is the mark
misread, but the mediant stands **beside** one, so that button goes in front
and leaves the word alone.

**A drop capital is not a character and cannot go in this way.** It is a
property of the block: press **show the structure**, find the line the
paragraph opens with, and press <kbd>¶</kbd>. Correcting `ehold,` to `Behold,`
gets the letters right and still leaves `totex.py` setting ordinary type where
the book sets a two line initial.

### The mediant was printing as a keyboard asterisk

`breviary.cls` has `\med` — a raised, enlarged, centred asterisk with thin
spaces — and `totex.py` mapped `<*>` to it. But `structure.py` never writes
`<*>`. It carries the mediant through as a plain `*`, and there are **7,918 of
them** in the markup, every one of which was being set as the asterisk off a
keyboard.

`marks()` now turns a star standing as a word of its own into `\med{}`. A star
inside a word is left alone, and so is `**`, which is stray ink. Four pages of
part 26 hold 62 of them.

## Two ink layers, one printed line, and the order they come back in

Max asked why some lines come out in a different order. The reading is good
because the engine never sees two things at once: the black layer and the red
layer are read apart. Putting them back was one line, and it was wrong.

    lines.sort(key=lambda l: l["y"])

A printed line can hold both colours. The book sets a red versicle mark, a red
`Ant.` or a red chapter reference inside a black line and carries straight on.
Those come back as two pieces, and the engine measures each layer's line box
off its own glyphs: black carries ascenders and descenders, a red mark is
short. So which piece came first was decided by **the height of the letters**,
not by where they stand across the measure.

| | |
|---|---|
| places where one block hands to the next | 63,677 |
| where the later block began to the LEFT of the earlier, on one printed line | **13,325, 20.9%** |
| pages touched | 2,274 of 2,386 |

`merge_layers` gathers the pieces of one printed line from both layers first,
then orders them across the measure. **20.9% down to 4.0%**, and the 934,071
words are the same 934,071 words: only the order of the blocks changed.

### Never rebuild a line from where the words sit

The first attempt at putting the existing drafts right did exactly that, and
it handed back `ACCORDING TO THE RITE` as `RITE THE TO ACCORDING`. Two reasons,
and both are about a page this book really contains:

- **Sorting on y decides nothing about a line.** On a centred display line the
  word boxes drift a few pixels the other way, so sorting by y and keeping
  that order reverses the line.
- **One median height cannot group two sizes of type.** The median glyph on a
  title page is 26 px because the body type sets it; the display capitals are
  47 to 55. Two printed lines then fall into one group, and a stray mark at
  the fold, 118 px tall, splits a third.

**The engine already knew its lines, and the draft still holds them.** The
text of a block carries a newline for each, and every one of the **68,463
blocks in this book accounts for exactly its words** that way. Take the lines
from there and nothing inside a line ever moves: checked page by page, all
2,386 have the same printed lines word for word as before, and 0 differ.

The drafts were put right without reading a page again. Every page was
structured afterwards, because the block numbers move and every word address
moves with them. **A proof sheet open in a browser across this change points
at the wrong words**: press **start again** on it.

## `check.py`: the only automated check this project has

    tools/check.py --save     record the book as it stands now
    tools/check.py            say what has moved since
    tools/check.py --list     name every page that moved

**1.7 seconds over 2,386 pages.** Run `--save` when the book is in a state you
believe, and run it bare after any change to `ocr.py`, `structure.py` or the
drafts.

It does not know which answer is right. It knows that something moved and how
much, which is the thing nobody knew on 2026-08-17.

### Why it reads the words, and why in order

Four faults went out over two days and **a person caught every one by looking
at a page**: a crop stretched to 114,716 px tall, a table collapsed into one
row, every display line reversed, two printed lines interleaved. Three of them
had a check written for them, and all three checks passed.

They passed because they counted words, or compared the **text** of a block.
The proof sheet renders the **words**, and the text of a line is carried over
whole, so the text agreed while the words were scrambled. The word total was
934,071 before and after every one of those bugs.

So `check.py` fingerprints three things a page, in order:

| | catches |
|---|---|
| the sequence of word tokens | a reading reordered anywhere |
| the sequence of blocks, by column, colour and length | a regrouping |
| the structured markup | anything `structure.py` did differently |

and it holds one invariant that needs no record: **the words of a block and
its text must say the same thing.**

It was tested by damaging the book the way yesterday's bugs damaged it. Both
were caught: the reversal broke the invariant outright, and the block swap
moved two fingerprints. The word count stayed at 934,071 through both, which
is exactly why counting was not enough.

## The project root is under git now

23 GB sit in that folder and almost all of it is derived. **548 KB cannot be
made again**: the tools, `onecolumn.txt`, `turn.txt`, `structfix/`,
`breviary.cls`, `STATE.md`. Those are tracked and everything else is ignored.
`structfix/` alone holds seven failed detectors' worth of knowledge about
which pages this book does not set in two columns, set by hand, page by page.

## A lone lowercase `i` is a roman numeral here, not dirt

This was nearly a change to `RE_STRAY`, and the page stopped it. A lone
lowercase `i` stands 5,425 times in the book and it looked like the same bleed
through as `|`. It is not. The book sets `Lesson i`, `Ant. i` and `℟. i`, and
`Lesson` stands before it 261 times and `Chapter` after it 230 times.

Striking them all through would have struck out every one of those numerals.
The rest of them, about 4,900, are stray, and telling the two apart wants the
word beside it rather than the character itself. Nothing does that yet, and a
context rule that is wrong damages the text where a character rule cannot.

**Look at the page.** Every wrong turn on this project has come from reasoning
about a number taken off a page instead of the page.

## A dictionary does not work on this book, and here is the measurement

The idea is the obvious one: the engine returns junk, a dictionary knows
words, so flag every word the dictionary does not hold. It was tested against
183 real-word errors on 22 pages that a person read word by word, and it fails.

The reason is not the dictionary. It is the shape of the errors.

| what the error is | share of 183 |
|---|---|
| a word that is not there at all, invented from stray ink | 38.8% |
| a misread word | 35.5% |
| a dropped word, or one word split into two | 18.6% |
| punctuation glued on to a word | 3.8% |
| a case error, `lord` for `Lord` | 3.3% |

Only the second kind is a spelling. A dictionary cannot see the first, the
third or the fifth at all, because every one of those is a correctly spelt
word. `i`, `I`, `O` and `it` appear out of nothing; `lord` and `With` are real
words in the wrong case; a dropped word leaves nothing to flag.

Frequency says the same thing. A rule that flags any word appearing rarely in
the whole 836,757 word corpus buys this:

| flag a word seen | catches | recall | flags a page |
|---|---|---|---|
| once | 25 | 13.7% | 6.4 |
| at most twice | 36 | 19.7% | 9.4 |
| at most 3 times | 43 | 23.5% | 11.7 |
| at most 10 times | 54 | 29.5% | 22.4 |

Seven errors in ten are on words the book uses more than ten times. The
vocabulary works against it as well: Habacuc, Zorobabel, Aggeus, vouchsafe,
didst, and the roman numerals `ix` and `lxx` are all real and all rare.

**What the measurement does support** is the opposite move: not a list of good
words, but a list of characters the book cannot print. That is `RE_STRAY`, it
needs no dictionary, and one button clears about 12 marks a page. The next
character to add is a lone lowercase `i`: it stands 5,426 times in the book,
2.3 a page, third after `|` at 30,215 and `*` at 10,600, and a lone lowercase
`i` is never right in English. It is `I`, or it is dirt.

## The markup holds line breaks. The book must not.

The markup carries one line for each line of the scan, because that is how the
page was read. Those are not the paragraphs of the book. They are the line
breaks of a book set to a different measure in 1967.

`totex.py` emitted a blank line after each of them, and a blank line is a new
paragraph in LaTeX. So every line of the scan became its own paragraph. The
text never flowed: each line sat where the scan put it, ragged and
unjustified, no word ever hyphenated, and the whole book ran a third longer
than the original on the same trim.

Nothing measured this. The reading was right, the markup was right, the audit
was clean and the round trip was clean, because every word was on the page.
Only putting a set page beside its scan showed it.

`totex.flush` now joins the lines of a block into one paragraph and lets the
typesetter break them. A paragraph ends where the markup says it ends, at a
tag. A line ending in a hyphen is joined to the next when the next begins
lowercase, because that hyphen belongs to the 1967 compositor's measure and
not to the word.

Two more faults were behind the rest of the excess, and both were found by
comparing each part against the number of pages the 1967 edition gave it. The
scan page count is that number: one scanned page is one page of the book.

**A rule outside the type is furniture.** `find_rules` collapsed the two or
three rows of one rule into one entry only when the colour matched, so the warm
rim of a black rule was found again in the red layer and the page carried
`.rule black` followed by `.rule`. Nothing filtered by position either, so the
rule under the running head and the edge of the leaf came through as body.
Parts 13, 16 and 17 carried four to five rules to a page where the book draws
one. 5,704 rules fell to 1,836, which is 0.77 a page.

**A block is a paragraph only until two blocks share a printed line.** The book
sets a red versicle mark, a red `Ant.` or a red chapter reference inside a
black line and goes straight on. The colour split happens per pixel and knows
nothing about lines, so each of those became its own block, and `totex` set
each block as its own paragraph. Every inline mark broke the paragraph. The
parts thick with short rubrics carried 35 blocks to a page against 20
elsewhere, and ran 18 to 25 per cent long on that alone. `structure.py` now
joins items that share a printed line and switches colour inside the line with
a brace pair, which `totex.inline` already understood.

The Sarum session named this one before it was found here, from the other
side: with slant instead of colour a fifth of their blocks are one word long,
and they warned that a renderer treating a block as a paragraph would break a
line wherever two blocks met. They thought this book would not notice. It
noticed, in exactly the parts where the book puts rubrics inside its lines.

| | before | reflow | rules | inline colour |
|---|---|---|---|---|
| every part set | 3,291 | 2,597 | 2,536 | **2,340** |
| longest run absent from the page | 5 words | 5 | 5 | **5** |

Against the 1967 edition, part by part, every part now falls between -12% and
+13%, where three of them stood at +22 to +29%.

The round trip is what says the reflow lost nothing. Its `lost` count roughly
doubled, from 3.9% to 7.1%, and that is extraction noise, not loss: the text
now hyphenates like the original, so more words break across lines and more of
them survive `pdftotext` as two pieces. Read `absent`, which did not move.

## The error the proof sheet cannot mark

A confidence score is the engine's opinion of its own reading. Three kinds of
error sit outside it, and the proof sheet is blind to all three.

- **Read confidently and wrongly.** `c` for `e`, where the result is still a
  real word. The engine is sure and a dictionary is happy.
- **Never read at all.** There is no reading to score. A page whose rubrics
  failed reports high confidence on the few words it did find.
- **Right words, wrong place.** Reading order, or a rubric set as text.

`unread.py` answers the second. Every word the engine read carries a box.
Paint the boxes, lay them over the ink, and whatever ink is left is ink the
engine never accounted for. It asks the page, not the engine, so it can see
the one thing the engine cannot report.

Three passes were needed to make it say anything useful, and each is a lesson:

- Counting every loose pixel flagged 67 pages, and the two worst were the edge
  of a leaf and the rules of the Table of Movable Feasts. **Count only ink
  shaped like type**: about the height of the type beside it, and not long and
  thin.
- A drop capital is ink no box covers, on every page that has one, and it is
  not missed — `find_dropcaps` reads it by shape precisely because the engine
  cannot. Subtract those, and the fore edge with `furniture_columns`.
- The first attempt to subtract drop capitals sat inside a bare `except` and
  removed nothing, because `find_dropcaps` returns its box under `box` and not
  as `x/y/w/h`. It failed silently, which is the fault this tool exists to
  catch. It raises now.

That brought 67 pages down to 17, and among them a real one: the display title
on `11-Psalter-Saturday-0015b` reads as `SON`, because the engine never saw
`OFFICE OF THE SEA`. That is the full-width matter fault, on a page nothing
else had flagged.

What is left in the list is mostly fore edge that survived, and the ℣ and ℟
marks, which no engine reads. 17 pages is short enough to look at.

**Measured, on part 19.** Four pages read word by word: 1,309 words, 168
corrections. 79 of them were on tokens the sheet greys out as punctuation, and
89 on real words, so the real-word error rate is 6.8%. Of those 89, 55 carried
a mark and 34 did not, and 60 of the 115 marks were on words that were right.
Checking only the marked words finds about three fifths of the errors.

The 79 greyed tokens are the surprise. They are stray ink and bleed through
from the back of the leaf, read as `|`, `}`, `~`, `*`, `=`. Their darkest
strokes sit at brightness 123 against 69 for real type, which is a signal
nothing uses yet.

**It does not answer the other two kinds.** Only reading a page word by word
does, which is what **I read this page in full** in the proof sheet is for.
Three pages read that way give the fraction of real errors that carried a
mark, and nobody has that number yet.

## Checking that the type holds the book

    tools/roundtrip.py                       every built part
    tools/roundtrip.py 26-Common-of-a-Virgin one part

`compile-all.log` proves LuaLaTeX exited 0. It does not prove the words
reached the page. A macro that eats its argument, a swallowed paragraph and a
runaway environment all compile perfectly. `roundtrip.py` reads the PDF back
with `pdftotext` and checks it against the markup two ways.

**Content**, as a word multiset. Do not read the lost count as faults. It
stands at 4.0% and nearly all of it is extraction noise: `-raw` drops the space
between two words here and there, and each welded pair reads as two losses and
a gain.

**Read the `absent` column.** It is the longest unbroken run of source words
that appear nowhere on the page at all. Over 757,417 words the worst is 5, so
nothing the size of a sentence is missing anywhere in the book.

**Do not read `drift` as loss.** It is the longest run where the two orders
part company, and `difflib` reports that whether words are missing or merely
moved. Multi-column extraction parts company constantly, so drift stands at 15
where absence stands at 5. The Sarum session found the same thing the other way
round: two of their proofs showed runs of 17 and 18 words with an identical
multiset, so nothing was missing at all. One number for loss, one for
divergence, and never the second on its own.

**Order**, over the headings. A multiset cannot see a transposition, and an
antiphon under the wrong day is a worse fault than a missing word: one is
visible to any reader and the other only to someone who knows which prayer
belongs there. 32 headings over the whole book do not stand in the source's
order. Each needs an eye.

Three things this cost, all worth keeping:

- **`-raw` here, but test before trusting it anywhere else.** Plain output
  rebuilds reading order from position, interleaves the two columns, and
  separates `com-` from `pared`. `-layout` welds the last word of one column
  to the first of the other. `-raw` keeps the order the text was written in.
  **The condition is the PDF, not the book, and no one has explained it.**
  `-raw` works only where the file holds real space characters. Some PDFs
  position each word instead, and `-raw` then returns the page with the spaces
  gone. Nobody has reproduced a cause: the Sarum session proposed one, tried
  six minimal documents to confirm it — font, microtype, font expansion, a
  narrow justified measure, multicol, a mid-paragraph colour change — and
  retracted it, because none of them welds anything. We are both on LuaLaTeX,
  so it is not the engine. Test the actual file: extract one page both ways
  and compare the token count against the source. If `-raw` collapses, it is
  unusable. That test is the whole of what is known.
- **The running head is a separate question from the flag.** Here it never
  reaches the text layer, so it costs nothing and is not stripped. Where
  `fancyhdr` draws it as real text it leads every page under both modes, and
  then the answer is to split on the form feed and drop the first line. Ask
  whether the head is in the text layer, not which flag is in use.
- **`-raw` returns a drop capital joined, not split.** `lettrine` sets the
  initial as its own text object, so positional extraction returns "I" and
  "will" and the source must be split to match. Under `-raw` it comes back as
  "Iwill", which is how the markup already holds it. The right answer inverts
  with the extraction mode.
- **Do not align headings with a moving pointer.** One heading the engine
  misread desynchronises it and everything after reports as moved: 473 of 482
  in one part against 7 of 878 in its twin. Sort every occurrence by position
  and take the longest run that keeps the source's order instead. The same
  part then reported 2.

## What the page tools know about this book

These came out of reading 499 pages and finding four faults that no confidence
score could see. Each is written up in the tool that carries it.

- **Red ink is bright.** The rim of a black stroke is warm, because it is part
  ink and part cream paper, and a ratio test calls it red. Then the red layer
  is a broken copy of the black text and the engine reads `ee` and `oe` off it.
  Test the red channel and its margin over green and blue in absolute terms,
  and drop any red that touches black. `pagelib.classify`
- **The printer drew the gutter.** A rule stands in it on many pages, and a
  rule is a lump of ink 700 px long and 3 px thick, which connected component
  labelling reads straight off. `pagelib.split_rules`
- **Never trim the fold side of a page.** The inner margin is narrow and the
  shadow of the fold reaches into the type, so a trim by brightness takes the
  last letter off every line. Give the whole fold to both pages instead.
  `pagelib.find_fold`
- **Look for the fold only near the middle.** The search window was the middle
  30% of the spread, which is wider than the fold can ever be. Where the fold
  shadow is faint — the Psalter came from a second machine and lies flat — the
  darkest column in so wide a window is a column of type, not the fold. The cut
  then landed 12 to 15 per cent off centre: one page lost its inner edge and
  its partner kept a stripe of the facing page. 26 spreads, 52 pages, and no
  check downstream could see it, because a page that lost its edge still reads
  as a healthy page. Narrowed to 12%. Measured over one spread from each of
  the 38 parts, that moved the fold on two and moved it more than 5% on one,
  which was one of the broken ones. `pagelib.find_fold`
- **Furniture runs unbroken down the page; type never does.** That one test
  finds the fold, the edge of the leaf and the fore edge of the book block,
  whether they are dark or pale. `pagelib.furniture_columns`
- **A page that reads as nothing must exit non-zero.** Printing a message and
  exiting 0 once hid 29 unread pages inside a run that reported no failures.
  Exit code 2 means the page holds no type of its own, which some do: a blank
  leaf backs a title page and carries only what shows through from behind it.

## Three more faults, found by typesetting all of it

Setting every part is the only test that reads the whole output. It found
three things that no audit of the reading could see.

- **A line of the book can begin with a full stop**, where the engine misreads
  the remains of a drop capital. A line that begins with a full stop is a tag
  in this markup, so twelve lines became tags called `.troyed` and `.omeness`.
  `structure.py` now puts one space in front of any line that would read as a
  tag it does not know.
- **A drop capital is a shape, so measure it.** `classify_line` also called a
  line a drop capital when its first token was tall and one or two characters
  long. A word box is as tall as its ascenders, and a versicle mark is one or
  two characters of junk, so the rule fired six times on the median page and
  thirty seven times on the worst, where the book sets one or two. It also ate
  the marks it misread. Removed: `find_dropcaps` reads them off the page.
  Drop capitals fell from 15,751 to 2,912, and rubric blocks rose by 5,750.
- **A bracket after an environment is an optional argument.** A folio number
  reads as `[110`, and where such a line opened a page, `multicols` took it
  for its preface and ran to the end of the paragraph. Two parts would not
  set at all. `totex.py` now puts an empty group in front of a leading
  bracket.

## What is still wrong

Some pages set matter across the full width in the middle of two column
matter: the title of a part, and a few rubrics. The column split cuts every
line of it in half. `04-Ordinary-of-the-Divine-Office-0001b` is the clearest
example; its title reads as `ORDINAR` and the rubric under it breaks at
`At all the Hours throu`.

Reading such a band full width was tried twice and dropped both times. The
type is justified and the gutter is as narrow as four pixels, so the ends of
ordinary lines sit inside any window drawn at the gutter, and ordinary pages
were read full width by mistake. That interleaves the two columns, which is a
worse fault than cutting a heading, and a quieter one.

So `audit.py` counts the pages whose gutter closes somewhere and says so
without listing them. It is an upper bound: most of those pages are ordinary.
Look at them with `showcolumns.py` before believing any of it.

**A fourth attempt, 2026-08-17, and what it found.** The Sarum Missal project
solves this on its book by comparing ink *density per pixel* in the gutter
channel against density in the columns, and calling a band full width when the
gutter runs above 0.35 of the columns. A ratio, never an absolute count.

Run on this book as it stands, it fired on 43 of 490 bands of ordinary text.
The cause is worth writing down: **this book draws a rule down the gutter and
Dickinson does not.** The test assumes the channel is empty on a columnar
line. Here it never is. `split_rules` lifts whole rules out, but the scan
breaks them, and a surviving piece of rule inside a five pixel channel is very
high density per pixel.

Clear each rule inside its own bounding box first, and the picture changes:

| | |
|---|---|
| `04-Ordinary-...-0001b`, the documented case | all 4 full-width lines caught, ratios 1.61 to 12.23 |
| 569 bands over 17 ordinary body pages | 0 tagged full |
| `26-Common-of-a-Virgin-...-0001a` | 2 titles caught, 3 false positives left |

Clear the rule by column instead of by box and detection goes to zero: the
rule stops below the title, so blanking the whole column blanks the title too.

**A fifth attempt, 2026-08-17, and it is not shipped either.** Max hit this
twice in four proofed pages, so it was worth another try. Four things were
learned and all of them are worth keeping.

- **Persistence beats length for finding the rule columns**, as the Sarum
  session said. A rule stands in the same columns down the whole page; a
  heading crosses the channel in one band or two. Excluding columns that carry
  ink in more than 30% of bands removes the rule without any threshold on how
  long a piece of it is.
- **Density is the wrong test at this gutter.** This book justifies to a four
  to eighteen pixel channel, so the ends of ordinary lines carry as much ink
  into it as a heading crossing it. Continuity is better: a full width line
  puts ink in every column of the channel. But a letter spaced title has word
  spaces wider than the channel, so continuity alone misses the very titles it
  is for.
- **The measurement was wrong before the logic was.** On the title pages, and
  only on those, what shows through from the back of the leaf reaches both
  margins and welds the lines into one 500 pixel band. Every margin and every
  band came out wrong. A stricter ink mask for measuring shapes — brightness
  under 110 rather than under 145 — fixed it outright: the right margin of one
  page went from 12 px to 124. Keep 145 for reading, because faint type is
  still type, and measure shapes on the strict mask. That idea is reusable.
- **Centring is the only signal a title has that two justified lines never do**
  — and requiring it of the opening band lost three of the five known cases
  while keeping the false ones. So it is not sufficient either.

Where it ended: on 110 sampled pages it reported a head zone on 10%, and of
the ones looked at, roughly half were real titles and half were ordinary psalm
text. That is not good enough to treat. **`unread.py` finds these pages
reliably by a different route** — it caught `11-Psalter-Saturday-0015b`, whose
title reads as `SON`, from ink no word box covered. So the fault is findable
per page, and the repair belongs in the proof sheet, where the note box exists
for it.

**Still not shipped.** The three remaining false positives are pieces of rule
shorter than the clearing threshold. A false positive interleaves two columns
and does it silently, which is worse than cutting a heading. Close the rule
fragments first, then measure over a few hundred pages, then ship.

**The way to close them, untested.** Do not raise or lower the length
threshold. Any length threshold fails, because a broken scan makes pieces of
any length. Use persistence instead: **a rule stands in the same columns all
the way down the page, and a full-width heading does not.** For each column in
the gutter channel, count the fraction of line bands in which that column
carries ink. Drop the columns that score high, then take the density ratio
over what is left. This needs no bounding box, no length, and no assumption
that the scan kept the rule whole, because a rule broken into ten pieces still
occupies the same columns. It should also pass the title for free: the rule
stops below the title, so those bands hold fewer rule columns. The idea came
from the Sarum session, which cannot test it — their gutter is empty.
