# The newspaper picture

Studied on 2026-10-14. The newspaper shown at the start of a day is one
picture, composed once by `play.day.DayNewsImage.make` when the news screen
opens. This doc covers the layout pictures, where each article goes, what is
drawn, and the random draws made on the way.

Functions read in full: `play.day.DayNewsImage` (static setup, `make`,
`roundToNearestLine`); `play.day.LayoutImage` (static setup, constructor,
`getColorBoundsRect`); `play.screen.NewsScreen` (constructor, `draw`,
`update`, `goButton_onClick`); the `app.vis.Fill` constructor. Read in part:
`Face.getDocImage` (only for its random draw), `Image.transformed` (only for
how it uses the angle). Three places where the decompiler dropped arguments
were read from the raw instructions (marked "from the instructions").

Everything here was read in the code unless marked **inferred** or **not
studied**. **Nothing here has been compared with the running game.**

## Answers to the two open questions

- **The first article of the day's list is the main headline.** Article `i`
  of `DayNews.articles` goes into rectangle `i` of the layout, and rectangle
  0 (the red one) is the single largest rectangle in all six layouts (and in
  all six phone layouts), counted in columns times lines
  (`newsimage_check.py`). So on days 2, 3, 13 and 16, where the game's sort
  swaps two equal articles (`news-txt-format.md`), the article that comes
  second in `News.txt` is the big one. Day 2: "Analysts Upbeat" is the main
  headline and "Grestin Checkpoint a Success!" the second. "Main" here means
  "in the largest rectangle"; the code has no other notion of a main
  headline.
- **Which random generator.** `NewsScreen` passes `day.newsRand`: the same
  generator object the `Day` constructor made (day seed + `0x1000`) and gave
  to `DayNews`. So `make` continues where `DayNews` stopped (after its 5 to 7
  draws when fillers are needed, `news-txt-format.md`). `make` then draws
  roughly 190 times (below). **Nothing else uses it** (answered on
  2026-10-16 over the whole-game decompile; this line said before that
  only part of the game had been searched, so it was not established).
  Its only users are the `Day` constructor (makes it, passes it to the
  `DayNews` constructor) and the `NewsScreen` constructor (passes it to
  `DayNewsImage.make`, whose only caller this is). Neither keeps a copy:
  `DayNews` has a field `rand`, but its constructor does not write it
  (only the by-name field functions `__hx_getField`/`__hx_setField`
  touch it), and `make` stores the generator nowhere; inside `make` it
  also goes to `FaceSpec.fromString` for a news face (below). How it was
  searched: the field name (5 functions: the `Day` constructor, `Day`'s
  three by-name field functions, the `NewsScreen` constructor); the
  name's hash `0x7daf0358`, by which Haxe code asks for a field by name
  (only in `Day`'s own by-name get and set); the field's position
  (`0xD0` in the fields, `0xe0` from the object's start) in reads without
  a type, where the 3 pointer reads found are a desk item's reveal state;
  and the instruction listings of the `Booth` and `Layout` constructors
  (no match). Not traced: `State.getSnapshot` and `MapUtil` read fields
  by names known only at run time; which objects they get was not
  followed. The only call that lists an object's field names
  (`Reflect.fields`) is in the test code's `test.Equal.equals`.

## The layout pictures (`LayoutImage`)

`NewsLayout0.png` to `NewsLayout5.png` are tiny maps of the page, 40 x 26
pixels. One pixel across is a tenth of a column; one pixel down is one text
line. Each holds five solid rectangles on black, in pure red, green, blue,
yellow and magenta.

The constructor `LayoutImage(res, dayId)`:

1. Loads `assets/NewsLayout<dayId % 6>.png`. Day 1 uses layout 1, day 6
   layout 0, day 7 layout 1 again.
2. For each colour **in the order red `FF0000`, green `00FF00`, blue
   `0000FF`, yellow `FFFF00`, magenta `FF00FF`** it finds the box around all
   pixels of that colour (alpha ignored). The box is `x = smallest x`,
   `y = smallest y`, `w = largest x - smallest x`, `h = largest y - smallest
   y`. **`w` and `h` are one less than the number of pixels.** Then
   `x = floor(x / 10 + 0.5)` and `w = floor(w / 10 + 0.5)`, which turns them
   into whole columns (30 pixels wide gives `w = 29`, then 3 columns). `y`
   and `h` are left alone, so a rectangle 10 pixel rows tall has `h = 9`
   lines. The five rectangles are kept in that colour order.
3. `numCols = picture width / 10` (4) and `numLines = picture height` (26).
4. The back picture is `assets/News.png` (365 x 220). If `numCols` is 3 it is
   `assets/NewsTall.png` instead, with a piece of `News.png` (x 54, y 0,
   253 x 52) pasted at the top, centred. That is the phone layout:
   `assets/layout/phone/` holds six 30 x 40 layout pictures and
   `NewsTall.png` (280 x 304). On desktop the layout folders are never
   loaded, so the desktop always uses the six main layouts. (This
   sentence first said the rule was described in `art-dat-format.md`; it
   was not. Corrected on 2026-10-16, when the rule was read from the code
   and added there.)

The rectangles of the six desktop layouts (columns and lines), from
`newsimage_check.py`:

| Layout | red (article 0) | green (1) | blue (2) | yellow (3) | magenta (4) |
|---|---|---|---|---|---|
| 0 | col 0, line 0, 3 x 9 | col 2, line 14, 2 x 11 | col 3, line 0, 1 x 11 | col 0, line 20, 1 x 5 | col 1, line 12, 1 x 9 |
| 1 | col 0, line 0, 3 x 8 | col 0, line 18, 2 x 7 | col 3, line 16, 1 x 9 | col 3, line 0, 1 x 13 | col 2, line 11, 1 x 9 |
| 2 | col 1, line 0, 3 x 8 | col 0, line 11, 1 x 14 | col 3, line 14, 1 x 10 | col 0, line 0, 1 x 8 | col 2, line 17, 1 x 8 |
| 3 | col 0, line 0, 2 x 12 | col 3, line 0, 1 x 17 | col 2, line 16, 1 x 9 | col 0, line 20, 1 x 5 | col 3, line 20, 1 x 5 |
| 4 | col 1, line 0, 2 x 12 | col 0, line 0, 1 x 17 | col 3, line 4, 1 x 10 | col 0, line 21, 2 x 4 | col 3, line 19, 1 x 6 |
| 5 | col 0, line 0, 2 x 12 | col 2, line 3, 2 x 10 | col 3, line 16, 1 x 9 | col 0, line 20, 1 x 5 | col 2, line 19, 1 x 6 |

## The numbers `make` uses

Static values of `DayNewsImage` (names from the game):

| Name | Value | | Name | Value |
|---|---|---|---|---|
| `kArticleX` | 13 | | `kTextDrop` | 2 |
| `kArticleY` | 56 | | `kPaperColor` | `FFEFEDDC` |
| `kColWidth` | 80 | | `kImageColor` | `FFCBCABB` |
| `kColPaddingX` | 5 | | `kWordBreakColor` | `FFDCDACB` |
| `kLineHeight` | 5 | | `kTextColor` | `FF000000` |
| `kLinePaddingY` | 1 | | `kTimeTextColor` | `FF605F58` |
| `kArticlePaddingX` | 1 | | `kTimeTextBaselineY` | 50 |

The compiled code uses the sums directly: a column step of 85 pixels (80 + 5)
and a line step of 6 pixels (5 + 1). For a rectangle with columns `x`, `w`
and lines `y`, `h`:

- `left = x * 85 + 13`, `top = y * 6 + 56`
- `width = w * 85 - 5`
- `roundToNearestLine(p) = ceil(p / 6) * 6` (it always rounds **up**)

## What `make` does, in order

Everything is collected in a list of drawable things and pasted at the end.

1. **The back picture**, at 0, 0.
2. **The date**: font `regular`, colour `kTimeTextColor`, the text
   `lang.formatVerboseDate(dayNews.date)` (`text-xml-format.md`), centred:
   `x = floor(backWidth / 2 - textWidth / 2)`, `y = 50 - font.ascent`.
3. **Word marks.** A loop that scatters small marks, 1 pixel wide and 5 tall
   in `kWordBreakColor`, over the whole grid. Starting from `pos = 0`:
   - one draw `r`; `pos += trunc((r * 0.5 + 0.3) * 60)` (a step of 18 to 48);
   - `line = floor(pos / 60)`, `col = floor(line / numLines)`;
   - if `col >= numCols`, stop (this last draw is used up);
   - otherwise a mark at `x = col * 85 + 23 + pos % 60`,
     `y = (line % numLines) * 6 + 56`.

   The number of marks, and so of draws, depends on the random numbers: over
   200 master seeds and 31 days it was 179 to 204 marks (mean 191.5), plus
   the one closing draw. Why the walk is 60 wide inside an 80-pixel column
   was not looked into; **inferred**: `News.png` already shows grey bars as
   stand-in text and the marks cut them into "words" (the picture was not
   compared).
4. **The five rectangles in order**, rectangle `i` with article `i`. A
   rectangle past the end of the article list gets no article
   (**inferred**: that a Haxe array gives nothing past its end was not read
   here). For each:
   1. **No text** (no article, or neither title nor subtitle): a grey box in
      `kImageColor`, at `left + 5`, `top + 5`, size `width - 10` by
      `h * 6 - 11`. Text bottom = `top + h * 6 - 1`.
   2. **Subtitle only**: text in font `regular`, black, word-wrapped to
      `width - 2`, centred; `x = floor(left + width / 2 - textWidth / 2)`,
      `y = floor(top + 2) - font.ascent + font.capHeight`. Text bottom =
      `y + textHeight`. No check against the rectangle's height.
   3. **With a title**: the title in font `title_news`, black, wrapped to
      `width - 2`, centred, same `x` and `y` formulas.
      - If a word had to be split (`Text.hyphenated`) or the title is taller
        than the rectangle (`textHeight / 6 > h`): **the title is set again
        in font `regular`**. If it now fits (`textHeight / 6 <= h`) it is
        shown; if not, **nothing is shown** and text bottom = `top`. In both
        cases the subtitle is **not** shown.
      - Otherwise the title is shown, and a subtitle (if any) goes below it:
        font `regular`, black, wrapped to `width - 2`, no alignment set,
        `x = left`, `y = floor(titleY + titleHeight + 4) - font.ascent +
        font.capHeight`. It is shown only if
        `(y + subtitleHeight - top) / 6 <= h`.
      - **Stamp** (the `$` line). The picture `assets/<stamp>` is turned by
        an angle of `r1 * 60 - 30` (first draw; from the instructions) with
        `Image.transformed`, which **uses the number as radians as it is**
        (**inferred** from two maths calls on it that were not identified;
        if so, the stamp can end up at any angle). Then two more draws place
        it: `x = floor(left + (width - stampWidth) * r2)`,
        `y = floor(top + (textBottom - top - stampHeight) * r3)`. It is
        drawn at 80% opacity (colour 1, 1, 1, 0.8). **Three draws.** In the
        decompiled code the stamp step sits inside the "with a title"
        branch; all five stamped articles in `News.txt` have a title, so the
        data cannot tell whether a title is required.
   4. `contentHeight = roundToNearestLine(textBottom + 1 - top)`.
   5. **Picture** (the `@` line), if the article has one:
      - `Face:<spec>`: `FaceSpec.fromString(rand, spec)`, then
        `faceLib.makeFace(spec, forDoc = true)`, then
        `face.getDocImage(rand, scale 0.5, flipX false, replaceColors true,
        textColor kImageColor, backColor kPaperColor)` (arguments from the
        instructions). The result is copied one pixel to the left into a new
        picture of the same size, and its bottom 2 rows and right 2 columns
        are filled with `kPaperColor`. **Draws**: one for each part the spec
        leaves out (`traveler-build.md`), then one inside `getDocImage`
        (`desk-drawing-draws.md`). All five `Face:` lines in `News.txt` give
        5 of the 7 parts, so the palette and the mirror flag are drawn:
        **three draws** per face picture.
      - anything else: the picture `res.getImage(<name>)`, with no
        `assets/` in front. None in the file.

      Position: `x = floor(left)`,
      `y = floor(contentHeight + top + roundToNearestLine(pictureHeight) -
      pictureHeight - 1)`: directly below the text. Its height is not
      checked against the rectangle.
   6. **Paper patch**: a box in `kPaperColor` at `left`, `top`, size
      `width + 1` by `contentHeight`. It is put in the list **before** this
      rectangle's other things, so it covers the back picture and the word
      marks under the text, and the text and stamp are drawn on top of it.
      It does not cover the area under a picture.
5. **Pasting.** A new picture of the back picture's size is filled with
   opaque red (colour 1, 0, 0, 1) and every listed thing is drawn into it in
   list order with paste mode `BLEND`. The back picture covers the red.

Articles beyond the fifth are not shown. With the data the most articles on
one day is 4 (`news-txt-format.md`), so rectangle 4 (magenta) is always a
grey box, unless traveler news adds more.

### Draws, in order

1. Word marks: one per mark plus one (about 190).
2. For each rectangle 0 to 4: the stamp's three (if any), then the face
   picture's (three with the present data).

## The news screen (`NewsScreen`)

- Song `Theme`; pausing is switched off.
- A push button with the id `walk-to-work`; its label is a `Text.xml` entry
  whose name the decompiler dropped (**not recovered**). Clicking it fades
  to the screen `day`.
- The newspaper is made here with `make(db, day.newsRand, day.news)`, scaled
  by `layout.getFitScale(width, height, buttonY)` and centred:
  `x = floor((layout.kPixelWidth - width) / 2)`,
  `y = floor(buttonY / 2 - height / 2)`.
- If the scale is below 0.999 a `NewsScreenMagnifier` is added.
  `getFitScale` gives 1 when the newspaper fits and 2/3 otherwise; **on
  desktop it fits** (365 x 220 on a 570-wide screen, button at y 290),
  so the scale is 1, the newspaper sits at (102, 35) and there is no
  magnifier. (This said "not studied" until 2026-10-16; `screens.md`
  part 11 has both functions.)
- `update` only adds the frame time to the story's play time.

## Check against the data files

`scripts/checks/newsimage_check.py` (run 2026-10-14), using the reference
script `scripts/reference/newsimage.py`:

- All 12 layout pictures hold only black and the five colours; each colour
  is one solid rectangle on whole columns; no two rectangles overlap or
  leave the page.
- In all 12 the red rectangle is the single largest (columns times lines).
- The grid fits the back pictures: desktop reaches x 353, y 212 inside
  365 x 220; phone x 268, y 296 inside 280 x 304.
- Over 200 master seeds and 31 days without traveler news: 179 to 204 word
  marks; never more than 4 articles; rectangle 0 holds an article with a
  title in 5,800 of 6,200 newspapers and a subtitle-only filler in 400 (the
  days with no news id); 600 newspapers (3 days of 31) have a stamp or a
  face among the day's own news.
- All 5 pictures in `News.txt` are `Face:` with 5 parts; all 5 stamps are
  `NewsEzicStamp.png` (44 x 44); every article with either has a title.

The reference script models the layout, which article goes where, the word
marks and the **number** of draws. It does **not** lay out text, so it does
not know whether a title falls back to the regular font or a subtitle is
dropped, and it does not compute the stamp's position.

## Notes for the port

- The word marks and stamp positions come from `newsRand`, which feeds
  nothing else after the day's headlines are chosen (whole-game search,
  2026-10-16; "Which random generator" above). So an
  exact copy of these draws matters only for a pixel-identical newspaper.
- Rounding the content height **up** to whole lines and the "one less than
  the pixel count" width and height of the layout rectangles must be copied
  or text will sit one line off.
- The title's fallback to the regular font drops the subtitle.

## Not studied

- The fallback rules above, evaluated for real headlines. What they
  waited on, how `app.vis.Text` measures, wraps, centres and hyphenates,
  is read since 2026-10-16 (`text-drawing.md`, with `fonts.md`), so this
  can now be done with `text.py`; it was not done.
- `Face.getDocImage` and `makeFace` beyond their draws: what the face looks
  like at half scale with the two colours.
- `Image.transformed` in full, and so the stamp's real angle.
- (`Layout.getFitScale` and `NewsScreenMagnifier` were listed here;
  read on 2026-10-16, `screens.md` part 11.)
- (Answered 2026-10-14, `save-format.md` part 2, from the code: the news
  screen is built when the game goes on to the next day and when a save is
  loaded; a new game goes to the intro screen first. Whether `make` runs
  each time the screen is built was not re-checked.) Whether endless mode
  has a news screen: its day is queued as the screen `day` directly, so by
  the code no; not seen in the game.
- The phone layout: the rectangle (54, 0, 253 x 52) was read from the code,
  but the method that cuts it out of `News.png` was not identified
  (**inferred** to be a crop), and nothing else about the phone was looked
  at.
