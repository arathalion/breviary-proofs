# Breviary markup

This is the format between the OCR step and the LaTeX step.

The OCR step writes one markup file for each book page. The converter
`tools/totex.py` turns the markup into LaTeX. Keep the markup simple. A human
must be able to read it and correct it against the scan.

## Why a middle format

Do not send OCR output straight to LaTeX. The markup holds the meaning of the
page, not its appearance. You can change the page size, the font, or the trim
later, and you do not touch the transcription.

## Page header

Start every file with a header. It ties the text back to the scan, so a
proof-reader can find the source.

    #page 6
    #src 04-Ordinary-of-the-Divine-Office-0004a
    #office Ordinary of the Divine Office at Matins
    #hour Matins

`#office` sets the running head. Repeat it only when the running head changes.

`#hour` and `#day` are the *liturgical address*. They do not print. They record
which hour and which day the matter on this page serves. Write them whenever
the page tells you, because the running head almost always does.

The address costs nothing now. It is what a later web office, such as a
Divinum Officium fork, needs in order to place the text, because that program
is addressed by day and hour while a printed book is addressed by page.
Recovering it later would mean opening every page a second time.

Use `#hour` for one of: Matins, Lauds, Prime, Terce, Sext, None, Vespers,
Compline. Use `#day` for the liturgical day, such as `Trinity Sunday` or
`Feria II`. Leave either one out when the page does not say.

## Blocks

A block starts with a tag on its own line. The block runs until the next tag or
a blank line pair. Each block has a base colour.

| Tag | Base colour | Use |
|---|---|---|
| `.text` | black | The words that you say. This is the default. |
| `.rubric` | red | An instruction. |
| `.hour NAME` | black | A large centred hour name, such as Lauds. |
| `.heading TEXT` | red | A small centred red heading. |
| `.psalm N` | red | The centred `Psalm N` line. |
| `.lesson N` | red | The centred `Lesson N` line. |
| `.ant N` | mixed | An antiphon. The label is red. The text is black. |
| `.rule` | red | The thin rule that divides two blocks. Takes no text. |
| `.rule black` | black | The heavier black rule under a display title. |
| `.open` | black | A paragraph that starts with a two line drop cap. |
| `.open red` | black | The same, but the initial letter is red. |

These three blocks span the full page. They interrupt the two columns, so use
them only for matter that the original also runs across the whole measure.

| Tag | Base colour | Use |
|---|---|---|
| `.title` | mixed | The display title of a part. Each line becomes one line of the title. |
| `.wide` | black | Text across the full measure. |
| `.widerubric` | red | A rubric across the full measure, such as the one that opens a part. |

## Inline marks

| Mark | Meaning |
|---|---|
| `{...}` | Change to the other colour. In a `.rubric` block the text turns black. In a `.text` block it turns red. |
| `<V>` | The versicle mark ℣. |
| `<R>` | The response mark ℟. |
| `<*>` | The mediant star. It marks the pause in the middle of a psalm verse. |

Nest nothing inside `{...}`. If a rubric holds two black parts, use two pairs
of braces.

## Rules for the transcription

- Write one paragraph on one line. Do not break a paragraph to match the
  column of the scan. LaTeX sets the columns again.
- Do not carry over a hyphen that only exists because the line broke.
- Keep the spelling of the original, including British forms such as
  `saviour`.
- Mark every colour change. The colour is the meaning of the book.
- If you cannot read a word, write `<?>`. Do not guess.

## Example

    #page 6
    #src 04-Ordinary-of-the-Divine-Office-0004a
    #office Ordinary of the Divine Office at Matins

    .text
    Day by day <*> we bless you.

    .rule

    .rubric
    After the {Te Deum} or the last responsory, when Matins is separated
    from Lauds, the following is said:

    .text
    <V> The Lord be with you.
    <R> And also with you.

    .rubric
    This versicle {The Lord be with you} is not said by one who prays alone.
