# Proofing the breviary

Thank you for helping. This is the 1967 Dominican Breviary in English. A
machine read all 2,180 pages of it. The machine is good but not right, and
this is where a person corrects it.

Nothing here needs any software. You work in a browser, and you send one small
file back.

## What to do

1. Press the green **Code** button at the top of this page, then **Download
   ZIP**. Unzip it.
2. Open the folder of the part you are proofing, such as
   `proof-26-Common-of-a-Virgin`. Double click `index.html`. It opens in your
   browser.
3. Put your name in the box at the top left. This names the file you send back.
4. Correct the words. There is more about this below.
5. Press **download corrections** before you stop. It writes one small JSON
   file.
6. Send that file back, or put it in the `corrections/` folder of this repo.

The browser remembers your work, so you can close the sheet and come back to
it. Press **download corrections** at the end of each sitting anyway. It costs
nothing, and then nothing can be lost.

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
- **Bleed through from the back of the leaf**, which the reader takes for
  faint type and returns as stray `|`, `}`, `~`, `*`. Delete them.

## Which part to take

Say which part you are taking, so that two people do not proof the same one.
Put your name in the table below and commit it — that is the whole system.

| part | pages | words | marked | who is on it |
|---|---|---|---|---|
| `19-Psalms-for-1st-Class-Feasts-of-Our-Lord` | 4 | 1,309 | 8.8% | |
| `35-Appendix-II-Excerpts-from-the-Roman-Ritual` | 10 | 2,888 | 6.8% | |
| `32-Seven-Penitential-Psalms-and-Litany-of-the-Saints` | 10 | 3,397 | 7.8% | |
| `30-Little-Office-of-the-BVM-and-Pilgrimage-Psalms` | 10 | 3,358 | 10.1% | |
| `29-Saturday-Office-of-the-BVM` | 12 | 4,088 | 9.6% | |
| `27-Common-of-a-Non-Virgin-outside-PT` | 14 | 4,843 | 9.8% | |
| `26-Common-of-a-Virgin-outside-PT` | 22 | 7,650 | 9.7% | Max |

Start with **19**. It is four pages and it exists so that you can go through
the whole loop once — correct a few words, press download, send the file — and
find out whether anything about the sheet is confusing before you spend a real
afternoon on it.

Then take whichever you like. They are all independent.

There are 31 parts in the book. These are the small ones. The four big Propers
run to 576 pages each and nobody should meet one first.
