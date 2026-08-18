# Taking these tools to another book

Four of these tools hold nothing about the breviary. They work on any scanned
book that can produce the draft schema below. Copy them and they run.

| copy | lines | change needed |
|---|---|---|
| `tsv.py` | 110 | none |
| `proof.py` | 506 | none |
| `applyfix.py` | 166 | none. It takes `--drafts` and `--structured` |
| `checkpages.py` | 113 | none, but it needs **scipy** as well as numpy |
| `showcolumns.py` | 90 | it calls `ocr.find_columns`, so it comes with that |

Third party across the whole set: **numpy**, **scipy**, **Pillow**. Only
`tsv.py`, `applyfix.py` and `audit.py` need none of them.

Do **not** copy `pagelib.py`, `ocr.py`, `structure.py` or `totex.py`. Every
number in them was paid for by a failure on these scans, and another book
fails differently. Read them for the method and write your own.

## The schema is the whole interface

One JSON file for each page, in `drafts/`.

```json
{"src": "<page name, no extension>",
 "blocks": [
   {"column": 1, "region": 1, "layer": "black",
    "text": "the line, space joined",
    "words": [{"t": "word", "conf": 93.4, "x": 45, "y": 410, "w": 38, "h": 33}]}
 ]}
```

- `column` orders the blocks across the page. `region` orders them down it.
- `layer` is `black` or `red`. It means "what the reader says" against "what
  tells the reader how to say it". If your book marks that difference by
  italic rather than by colour, still call it `red`. The proof sheet then
  shows it in red, which is what the printed book will do.
- `conf` is the engine's confidence, 0 to 100. The proof sheet marks anything
  under 80, and marks under 60 more strongly.
- `x, y, w, h` are in the coordinates of the picture named by `src`. The proof
  sheet does not use them, but `structure.py` and every geometric join do, and
  they cannot be recovered later.

Write that, and the proof sheet, the correction round trip and the audit all
work. Nothing else is required.

## Getting the words

`tsv.py` is the piece to take first.

```python
import tsv
lines = tsv.read_words(path, lang="lat", psm="6")
for line in lines:
    for w in line["words"]:
        ...              # t, conf, x, y, w, h
```

Ask the engine for TSV, never for plain text. Plain text drops the confidence
and the boxes, and neither can be recovered by reading the text again.

## Do not split the page by a signal you cannot measure per pixel

This book separates its two inks *before* the read, and gives the engine one
clean layer at a time. That works because **colour is a property of one
pixel**. A red pixel is red on its own, so the split is exact.

Do not copy that when your signal is italic. **Slant can only be measured
across a run of letters**, and any window wide enough to measure it is wider
than many words, so it straddles a transition and averages the two classes
away. The Sarum project built the mask version and dropped it. Dickinson sets
quoted incipits in roman inside italic rubrics, so mid-line transitions are
common, and both layers handed the engine a torn fragment.

For any signal that is not per pixel, classify **per word box, after the
read**. Their control test, 115 words in one column:

| class | n | median slant | range |
|---|---|---|---|
| roman | 61 | -1.3° | -4.2 to +2.4 |
| italic | 54 | +11.0° | +7.6 to +14.8 |

Zero overlap, and a five degree empty gap between the classes. The threshold
is not delicate. The boxes come from `tsv.read_words`.

## Joining a measurement to the words

Anything the engine cannot report — ink colour, italic, a rule, a stave — is
found by measuring the image. `tsv.band_of` attaches such a measurement to the
right line:

```python
i = tsv.band_of(line, bands)      # bands: [(top, bottom), ...]
italic = i is not None and slants[i] >= ITALIC_AT
```

Match on the centre of the line box. Do not match by counting lines. The
engine and the image never agree on how many lines a region holds, and
pairing them in order goes wrong from the first disagreement onward without
saying so. Measured over 962 lines of a Sarum Missal: by centre 99.5%, by
shared area 91%, by position 68% of regions.

## The proof sheet

```
proof.py <draft.json> ... -o proof-<name>/ --images <crops dir>
```

`--images` wants one picture for each column, named `<src>-c<n>.png`, where
`n` is the `column` field. Leave it out and the sheet shows the reading alone,
which is much less use.

Then `applyfix.py corrections-*.json --drafts <dir> --structured <dir>` writes
the corrections back and deletes the structured page, so your next run rebuilds
it. See the README for what a person does in between.

## Four things that cost this project a night each

They are not about this book.

- **Ask the engine for words. Measure the page for shapes.** Stroke weight,
  drop capitals, rules and folds are all shapes. The engine guesses at them
  and the guess is confident.
- **Do not judge a reading by a dictionary.** It passes any real word, so it
  is blind to reading order and to a word misread into another real word.
  Use confidence, and watch quantity too: a page whose rubrics failed reports
  high confidence on the few words it did find. Compare each page against the
  median page of its own section.
- **A tool that reads nothing must exit non-zero.** Printing a message and
  exiting 0 once hid 29 unread pages inside a run that reported no failures.
- **Build the whole output, not a sample.** Setting all 31 parts took four
  minutes and found three faults that every audit of the reading had passed
  over. Two of them corrupted the markup silently.
