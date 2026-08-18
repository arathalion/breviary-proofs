# Proofing the breviary

**Open [arathalion.github.io/breviary-proofs](https://arathalion.github.io/breviary-proofs/).
That is the whole thing.** You need nothing from this page, and nothing from
GitHub. This page is here for anyone who lands on the code instead.

Thank you for helping. This is the 1967 Dominican Breviary in English. A
machine read all 2,386 pages of it. The machine is good but it is not right,
and this is where a person corrects it.

## What to do

1. Open the link above and pick a part. Tell Max which one you take, so that
   two people do not take the same one.
2. Put your name in the box at the top left.
3. Correct the words. There is more about this below.
4. Press **send corrections** before you stop. Your work goes on the
   clipboard. Paste it into a message to Max.

The browser remembers your work, so you can close a part and come back to it.
Press **send corrections** at the end of each sitting anyway. It costs
nothing, and then nothing can be lost.

If the clipboard does not work, press **download corrections** instead. That
writes a small JSON file, and you send the file.

## Correcting the words

Each page shows two columns of the scan, and beside each one what the machine
read. The machine marks the words it was unsure of. A pink word is doubtful. A
darker red word is usually wrong.

- **Click a word to correct it.** Type over it, then press `Enter`.
- **`Tab`** takes you to the next marked word. This is the fastest way to work.
- **`Esc`** means the machine was right. It goes on to the next marked word.
- **Empty a word** to delete it. Some words are not there at all.
- **Type two words** in place of one to add a word. The machine drops words.
- **Click the scan** to see it at full size. Click it again to make it small.

Red type in the book is red on the sheet. The machine reads red badly, so look
at the red closely.

## The stray ink

Some marks on the sheet are struck through. The book prints no such mark, so
each one is stray ink or bleed through from the back of the leaf. The machine
read it as `|`, `}`, `~` or `_`.

There are about 15 of these on every page, and they were 47 per cent of all
the work on the four pages Max checked word by word.

**Press `delete the stray ink` on each page.** One press takes all of them
off. Click any one of them to keep it, if you think the book really prints it.

A stray mark is not a word. It stays out of the word count and out of the
error rate, and the bar counts it on its own.

## The two marks

The book opens a great many lines with ℟ and ℣. No machine reads these, and no
keyboard carries them.

Type **`R/`** for ℟ and **`V/`** for ℣. The sheet turns them into the true
mark. The two buttons in the bar do the same thing.

## The bar at the top

| it says | it means |
|---|---|
| checked | words you looked at |
| wrong | words you corrected |
| stray marks gone | stray ink you took off |
| of the marked words | how many of the machine's own doubts were real |
| pages read in full | pages you ticked, see below |
| true error rate | errors over every word of those pages |

## Reading a page in full

Each page has a box: **I read this page in full**. Tick it only if you read
every word of the page against the scan, and not only the words the machine
marked.

This matters more than the corrections do. The machine's opinion of itself is
not a measurement. A few pages read word by word tell us the true error rate,
and that decides whether the whole book can be trusted.

Two or three pages in full is plenty. Do the rest the fast way, with `Tab`.

## The note box

Each page has a note box. Use it for anything a word cannot hold:

- A title or a rubric that runs across both columns. The reader cuts every
  line of it in half. This is a known fault and it needs a person to see it.
- A missing line, or a line in the wrong place.
- Anything that looks wrong and is not one word.

## Start here if you only do one thing: `proof-00-Repairs`

18 pages, and they are the worst 18 in the book. They were not chosen by hand.
`tools/unread.py` measures, on every one of the 2,386 pages, how much ink no
word box covers — that is, ink the machine never read at all. These 18 carry
two to twenty three times as much of it as the rest of their part.

They mark 20.3% of their words for checking, against about 9% for the book.

Two faults live here and both need a person:

- **A title that runs across both columns.** The reader cuts the page down the
  middle, so a heading spanning the measure is split and each half lands in a
  different column. `OFFICE OF THE SEASON` came out as `SON`. Five attempts to
  detect this automatically have failed, the last one on 2026-08-17, because
  the test that finds a real title also fires on ordinary two column text and
  interleaving two columns is a worse and quieter fault. So it is yours.
  **Write what the heading should say in the note box for that page.**
- **Bleed through from the back of the leaf.** Press **delete the stray ink**.

## Which part to take

Tell Max which part you are taking, so that two people do not proof the same
one. Put your name in the table below as well, if you use GitHub.

| part | pages | words | marked | stray marks | who is on it |
|---|---|---|---|---|---|
| `06-Psalter-Monday` | 26 | 9,033 | 6.6% | | |
| `07-Psalter-Tuesday` | 26 | 8,895 | 6.1% | | |
| `09-Psalter-Thursday` | 26 | 9,012 | 6.8% | | |
| `19-Psalms-for-1st-Class-Feasts-of-Our-Lord` | 4 | 1,274 | 4.7% | 25 | |
| `35-Appendix-II-Excerpts-from-the-Roman-Ritual` | 10 | 2,888 | 6.8% | 125 | |
| `32-Seven-Penitential-Psalms-and-Litany-of-the-Saints` | 10 | 3,397 | 7.8% | 90 | |
| `30-Little-Office-of-the-BVM-and-Pilgrimage-Psalms` | 10 | 3,358 | 10.1% | 154 | |
| `29-Saturday-Office-of-the-BVM` | 12 | 4,088 | 9.6% | 192 | |
| `27-Common-of-a-Non-Virgin-outside-PT` | 14 | 4,843 | 9.8% | 168 | |
| `26-Common-of-a-Virgin-outside-PT` | 22 | 7,650 | 9.7% | 235 | Max |

Start with **19**. It is four pages and it exists so that you can go through
the whole loop once — correct a few words, press send, paste it into a message
— and find out whether anything about the sheet is confusing before you spend
a real afternoon on it.

Then take a **Psalter** day: Monday, Tuesday or Thursday, 26 pages each. That
is the best work on this book. The text is the cleanest in it, 6.1% to 6.8%
marked against 9 to 10% for the Commons, and it is the text you pray every
week, so you will notice a wrong word that a stranger would read past.

**Do not start with `proof-00-Repairs`.** It is the worst 18 pages in the book
and it is chosen to be. On 10 of those 18 there is no word to correct at all,
because the fault is the page, not the reading. It is worth doing, and it is
not worth doing first.

Part 19 marks 4.7% of its words now, because Max proofed it on 2026-08-17 and
the corrections went back into the drafts.

Then take whichever you like. They are all independent.

There are 38 parts in the book. These are the small ones. The four big Propers
run to 576 pages each and nobody should meet one first.

## For Max

    tools/proof.py drafts/26-*.json --images drafts/crops -o proofs/proof-26-.../
    tools/proofindex.py proofs/            write the landing page again
    tools/applyfix.py corrections-*.json   put the corrections back

Save what a proofreader pastes back into `corrections/`, then run
`applyfix.py`. Build the sheets first and the landing page second: it reads
the numbers out of the sheets.
