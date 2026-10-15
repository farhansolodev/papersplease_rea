# Drawing, part 1: how a text is laid out and drawn (`app.vis.Text`)

Studied on 2026-10-16, as part 1 of the drawing step (step 5 of
`PROGRESS.md`). Code reading, three read-only Ghidra runs for the
instructions, and previews made with the reference script. **Nothing here
has been compared with the running game.**

Reference script: `scripts/reference/text.py` (lays a text out tile by
tile and draws a preview). Check: `scripts/checks/text_drawing_check.py`.
Fonts, their measurements and the line breaker are in `fonts.md`.

## What was read

In `decompiled/all/app_vis.clean.c`: all of `app.vis.Text` (the
constructor, `buildTiles`, `getBuiltLetters`, `width`, `height`, the
`baselineY`, `capY` and `bottomY` pairs, `hasText`, `hyphenated`, every
setter, `willDraw`); from `app.vis.Visual`, `allocateTiles`,
`renderToImage`, `hitRect` and the `x` / `y` pairs; `app.vis.Quad.make`
and `app.ent.QuadIter.next` (how tiles become quads on screen); the
`SplitResult` constructor and the end of `Font.split`; the start of
`Image.paste` (how it turns a position into pixels). Field offsets are
from `dump.cs`.

Checked in the instructions (`decompiled/step5_run1.txt` to
`step5_run3.txt`, `DumpAssembly.java 0x18066ef30 0x1807d4480`,
`0x1809f5f80`, `0x18087f080`): the missing-letter box, the centring
division, the height formula, the three background tiles, that
`buildTiles` never reads `wordWrap` (field `0x7C`), how `Image.paste`
converts its position, and which width `Font.split` returns. Constants
read with `read_doubles.py`: `0x180a6e160` is the float 255,
`0x180a36c10` the float 1, `0x180a6dfc0` the double 0.01, `0x180a84128`
the float 0.001.

Whole-decompile searches: every caller of the padding, line spacing,
background and `wordWrap` setters and of `getBuiltLetters` (below, "Who
uses the settings").

## What a text holds

| Setting | Field | Start value | What it does |
|---|---|---|---|
| `text` | `0x60` | none | the string. Empty or missing: nothing is laid out, size 0 x 0 |
| `font` | `0x68` | given to the constructor | |
| `fixedWidth` | `0x80` | 0 | the line breaker's limit (`Font.split`'s `maxWidth`): **0 means break only at line breaks**, anything else wraps (`fonts.md`) |
| `multiLine` | `0x84` | false | false keeps only the first line |
| `wordWrap` | `0x7C` | false | **stored, but nothing reads it**: the layout ignores it (checked in the instructions). Wrapping depends on `fixedWidth` alone |
| `align` | `0x98` | LEFT | LEFT, CENTER or RIGHT, for each line inside the text's box |
| `paddingX`, `paddingY` | `0x70`, `0x74` | 0 | space around the lines, on both sides |
| `lineSpacing` | `0x78` | 0 | extra pixels between lines (not after the last) |
| `color` | `0x88` | 0 | the letters' colour, `0xAARRGGBB` |
| `backgroundColor` | `0x8C` | 0 | a filled box behind the text when its alpha is not 0 |
| `backgroundRounded` | `0x90` | false | the box with its four corner pixels cut |

The constructor sets only the font, so a new text has colour 0, which is
fully transparent: **a text whose colour is never set shows no letters**
(see "Drawing"). Every setter counts a change only when the value
differs (the text is compared as a string); a change makes the next
question about the text's size, or the next drawing, lay it out again.

## Laying out (`buildTiles`)

The text is broken into lines by `Font.split(text, fixedWidth,
multiLine)`. That gives the lines with their widths, the widest width W,
whether a word was cut with a hyphen, and the count of characters that
are not spaces (each gets a tile). Then:

1. Let r be 1 if the background is rounded, else 0.
2. The pen starts at y = `paddingY`. For each line:
   - x = `paddingX`, plus `(W - line width) / 2` cut toward zero for
     CENTER, or `W - line width` for RIGHT; then + r.
   - For each character (pairs of UTF-16 halves are joined into one
     character):
     - **A letter the font has, other than the space:** one tile, a piece
       of the font sheet (the letter's rectangle) placed at
       (x + the letter's x offset, y + its y offset), unstretched, in the
       text colour. The pen moves right by the letter's advance.
     - **The space** (code 32) gets no tile; the pen moves by its advance.
     - **A character the font lacks:** a filled box in the text colour,
       `spaceWidth` wide and `capHeight` high, at
       (x + `spaceWidth` - 1, y). The pen moves by `spaceWidth`. (If the
       missing character is the space itself, only the move.) The box
       starts one pixel before the next pen position, so it overlaps the
       next letter by `spaceWidth` - 1 pixels: that is what the
       instructions say (`DEC EDX` before `ADD EDX,EDI`), not a misreading.
   - y moves down by the font's line height + `lineSpacing`.
3. **Size.** With n lines:
   - width = W + 2 `paddingX` + r;
   - height = n x line height + `lineSpacing` x (n - 1) + 2 `paddingY`

4. **Background**, if its alpha is not 0, drawn before the letters:
   - not rounded: one box (0, 0) to (width, height);
   - rounded: a box from x 1 to x W + 2 `paddingX` over the whole height,
     and a column 1 pixel wide on each side (x 0 and x W + 2 `paddingX`)
     from y 1 to y height - 1. So the four corner pixels are left out.
     The letters are shifted right by 1 with it, so the left margin is
     one pixel wider than the right.

**W is the widest line before a one-line text drops its other lines**
(checked in the instructions: the maximum is kept in a register that is
not touched after the `multiLine` test). So a one-line text given
`"one\ntwo longer"` draws only "one" but is as wide as "two longer", and
CENTER and RIGHT place "one" inside that width. Corrected on 2026-10-16:
`fonts.py` took the widest of the kept lines only; fixed.

Positions in the tiles are relative to the text's position (below), all
whole numbers.

## Where a text sits

A text's position (`x`, `y`) is the **top left corner of its box**: the
padding starts there, then the first line. In the first line, a letter's
top is at its font y offset, so:

| Helper | Meaning | Value |
|---|---|---|
| `baselineY` | the first line's base line | y + ascent |
| `capY` | the top of a capital letter in the first line | y + ascent - cap height |
| `bottomY` | the bottom of the box | y + height |

Each has a setter that moves y so that the given line lands where asked
(for example `set_capY(c)` sets y = c - ascent + cap height). They ignore
`paddingY`. `hitRect` is (x, y, width, height), cut to the clip rectangle
if there is one.

## Drawing

A text is drawn in one of two ways. Both go through its tiles in order,
background first.

**On screen.** An object's `draw` (read in `play.ui.Button.draw`) sets
the text's `hostPos` to the object's position in the world, lays the text
out, and hands it to the drawer's layer. The layer's quad walker
(`app.ent.QuadIter.next`) turns each tile into a **quad** with
`app.vis.Quad.make`:

- a tile whose colour alpha is below 0.001 (`kAlphaThresh`, constant
  `0x180a84128`) is skipped: so the letters of a text whose colour is
  never set (0) are not drawn, while its background follows its own
  colour;
- the corners are text position + tile place, cut to the clip rectangle
  if there is one (the picture coordinates are cut in proportion), plus
  `hostPos`, in single-precision floats, **not rounded** to whole pixels;
- the picture coordinates are divided by the picture's size (0 to 1), and
  the colour is copied as four floats.

What the Unity side then does with the quads (and so how a fractional
position lands on a pixel) was not read.

**Into a picture** (`Visual.renderToImage`; called three times, all in
`play.day.booth`). A tile whose size equals its piece's size (within
0.01) is **pasted** at (text x + tile x + host x, text y + tile y +
host y), with the paste mode BLEND unless the caller gives another, and
a colour mode: none if the colour is `0xFFFFFFFF`, otherwise a tint by the
colour. `Image.paste` turns each coordinate into a whole pixel by
**cutting toward zero** (`CVTTSD2SI`, checked in the instructions), so
10.7 becomes 10 and -0.5 becomes 0. A stretched tile (the background, the
missing-letter box) goes through `Quad.make` as above and then
`Image.draw`, which was not read.

`willDraw` (visible, not empty, colour alpha not 0) has no caller in the
decompiled game code other than the generic by-name helpers, so it is not
what keeps a transparent text off the screen; the 0.001 test above is.

The colour travels as four floats (each byte / 255) and back (float x 255,
cut to a whole number); a test of all 256 byte values in single precision
gives every value back unchanged, so no colour is off by one.

All twelve font sheets are white with alpha 0 or 255 only
(`text_drawing_check.py`), so a letter shows as solid text colour where
the sheet is opaque **if the tint multiplies**. The decompiled paste
suggests a multiplication by colour / 255 per channel, but its tint and
blend code was not read in full.

## Letters shown one by one (`getBuiltLetters`)

The first call to `getBuiltLetters` turns on a list of built letters and
lays the text out again; from then on each layout also lists every
character with its tile (none for the space). `play.ui.RevealTextEnt`
(the typing captions and the night screen's messages) uses it: the whole
text is laid out at once, and letters are shown by setting their tile's
alpha to 1 (`revealAll` sets every letter's). So **a typing text has the
size and position of its full text from the start**; nothing moves as it
types.

## Who uses the settings

Whole-decompile search (every call to the setter, direct or through the
method table; no other code writes the fields):

| Setting | Set by |
|---|---|
| padding | `PaperInnerVisuals` (the document pages: x 1 for a text with `backcolor`, x and y 1 for a link button; `page-layout.md`), `InspectUi` (booth), `GameScreen.addHeader` (x only, 8), `FramerateCounter` |
| line spacing | `Paper` and `Filer` (booth) |
| background | `PaperInnerVisuals` (`backcolor`; rounded, in `textcolor`, for a link button), `InspectUi`, `GameScreen.addHeader` (black), `FramerateCounter` |
| `wordWrap` (no effect) | `DayNewsImage.make`, `PaperInnerVisuals`, `Filer`, `FamilyVisuals`, `BudgetEnt.createMessageTexts`, `CreditList.addText`, `EndScreen`, `RevealTextEnt` |

So every other text in the game (the menus, buttons, credits, the
endless screen, the night screen, the border scoreboard, the intro
caption) has no padding, no line spacing and no background: **its height
is its number of lines x its font's line height, and its width is its
widest line**.

## What this answers in the earlier docs

- **Button texts** (`buttons.md`): a button text is one line with no
  padding, so its height is the font's line height, and the text's top
  `floor(picture height / 2 - text height / 2)` can now be computed.
- **The night screen** (`night-pictures.md`): a member's name has fixed
  width 0, so it is never wrapped; the code places it with `capY`, so the
  top of its capitals is at floor(centre y + 15). The passport count's
  height is the line height, as `nightpics.py` assumed.
- **The header title** (`screens.md`, the header): one line of
  `title_tall` with 8 pixels of padding left and right and none above or
  below: height 20 (the line height from `fonts.md`), width the text's
  width + 16. So the credits screen's B = 77, `kStopY` = 159 and the
  offscreen value 161 hold as computed there.
- **The intro caption** (`screens.md`, part 5): with fixed width 380 its
  `width` is the widest of its wrapped lines, not 380, so its left edge
  floor(285 - width / 2) depends on the text. No code found sets its
  alignment (searched by name), so its lines start at the left edge of
  that box.
- **The credits list** (`screens.md`, part 6): its texts set no padding
  or spacing, so the estimate's assumption (lines x line height) is the
  game's rule.
- **`Image.paste`** (`buttons.md`, `faces.md`): positions are cut toward
  zero, not rounded. This is the drawing-into-a-picture path; a button on
  screen is drawn as quads, whose positions are not rounded in the game
  code (the Unity side not read).

## Cross-check

`text_drawing_check.py` (run 2026-10-16):

- Every character of `Text.xml`'s texts (74 different ones) is in every
  font but `digits` (which has only `.` and `0` to `9`). Of all the data
  files, only `UpperCase.txt` (a table, not shown) has characters the text
  fonts lack, plus one character of `Credits.txt` that `fixed` lacks. So
  in English the missing-letter box should appear only where a player
  types or a name brings a character the font lacks.
- The twelve font sheets have exactly two colours: white at alpha 0 and
  white at alpha 255. `problems: none`.

Previews looked at (`text.py --png`): the header title "SETTINGS" (64 x
20, white on black), a centred text wrapped at 80 with a missing-letter
box, a rounded background, and `nightpics.py render demo`, which now
draws the family names and the passport count with `text.py`.

## Notes for the port

- Lay a text out exactly as above; tile places are integers, and only
  the text's own position and its host position can be fractional (cut
  toward zero when pasted into a picture; on screen, not known).
- Ignore `wordWrap`; wrap whenever the fixed width is not 0.
- Skip any tile whose alpha is below 0.001.
- Keep the one-line width rule (widest line before the cut) and the
  rounded background's extra pixel on the left.

## Not studied

- `Image.paste`'s blend and tint arithmetic, and `Image.draw` (how a
  stretched tile, a background or a box, is filled; whether its edges are
  cut the same way).
- How the Unity side draws the quads on screen, so where a fractional
  position lands and how the colour is applied there.
- How `Font.split` behaves at its edges (`fonts.md`, "Note on
  certainty"); this part only confirmed which width it returns.
- Which texts use which font and settings, beyond the setter search above
  and the screens already written up.
- The rest of the drawing step: the search photo, the rest of `app.vis`
  and `play.ui`, input handling. (`PaperInnerVisuals`, the document
  pages, was listed here; read on 2026-10-16, `page-layout.md`.)

## Things to watch in the game

Each takes a few seconds; none was done.

1. The settings screen's header: "SETTINGS" on a black box 64 x 20, the
   box centred on the bottom edge of the header picture.
2. The intro caption: a line shorter than the widest sits at the same
   left edge as the widest (left aligned), and the block as a whole is
   centred.
3. A typing caption does not shift while it types.
