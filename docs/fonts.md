# Fonts.xml and the font files

Studied on 2026-10-14. `Fonts.xml` names the game's fonts; each points to a
bitmap font: a `.fnt` description and a picture sheet in `assets/fonts/`.
Reference script: `scripts/reference/fonts.py`. Check:
`scripts/checks/fonts_check.py`.

Functions read in full: `data.FontLib` (constructor, `get`, `getAll`), the
`data.FontDef` constructor, and `app.vis.Font` (constructor, `getTextWidth`,
`get_descent`, `escape`, the static values). `Font.split` (line breaking)
was read in full, but the decompiler scrambled its order of steps; see the
note there. Drawing text (`app.vis.Text`) is not studied.

## Fonts.xml

`<fonts>` holds `<font>` elements, read in file order into a table by id.

| Attribute | Meaning |
|---|---|
| `id` | the name other files use (`font="regular"` in `Papers.xml`, ...) |
| `file` | the font file, without folder or ending: `assets/fonts/<file>.fnt` |
| `lineheight` | optional; replaces the line height worked out from the letters. Missing counts as 0, which means "do not replace" |

Asking for an unknown id is an error (`Font not found: <id>`). Several ids
may share one file with different line heights (`regular`, `regular_short2`
and `regular_tall`). The commented-out `tiny` line is ignored.

## The .fnt file

An XML file in the style of the common "BMFont" tools. What the game reads:

- `<pages>`/`<page file="...">`: the picture sheets, loaded from
  `assets/fonts/<file>`. Every font here has exactly one.
- `<chars>`/`<char>`: one per letter, with:

| Attribute | Use |
|---|---|
| `letter` | **the character itself**, and what the letter is filed under: the code of its first character. Seven names are translated: `space`, `&#13;`, `&#10;`, `&gt;`, `&lt;`, `&quot;`, `&amp;` |
| `page` | which sheet |
| `x`, `y`, `width`, `height` | the letter's rectangle on the sheet |
| `xoffset`, `yoffset` | where to draw it relative to the pen position |
| `xadvance` | how far the pen moves after it |

**Not read:** `id` (the numeric code; the game uses `letter` instead),
`chnl`, the `<info>` and `<common>` elements (so the file's own
`lineHeight` is ignored), the `count` attributes, and `<kernings>` (there is
no kerning: no adjustments between pairs of letters).

## Measurements worked out when a font is loaded

| Value | How |
|---|---|
| line height | the tallest letter rectangle, unless `Fonts.xml` gives `lineheight` |
| widest advance | the largest `xadvance` |
| space width | the `xadvance` of the space letter (0 if there is none) |
| top | the smallest `yoffset` of any letter. **It is subtracted from every letter's `yoffset`**, so the highest letter sits at 0 |
| ascent | taken from the letter `A`, or `0` in a font with no `A`: its (shifted) `yoffset` plus its height |
| capital height | that same letter's height |
| descent | line height minus ascent (can be 0 or negative) |
| hyphen | the text `wrap_hyphen` of the current language (`-` in English); the word `NONE` means no hyphen. Its width is stored. (The key name is inferred: the decompiler dropped the argument, and `wrap_hyphen` is the only hyphen entry in `Text.xml`) |

A font with neither `A` nor `0` would keep ascent 0.

## Measuring and breaking text

**Width of a text** (`getTextWidth`): the sum of the letters' advances.
Characters the font does not have count as nothing.

**Breaking into lines** (`split(text, maxWidth, multiLine)`):

- `maxWidth` 0: split at line breaks only; each line is trimmed.
- Otherwise the limit is `maxWidth`, but never less than the widest advance.
  Each paragraph (split at line breaks) is split into words at spaces, and
  words are added to the current line while `word width + line width so far
  < limit` (the line width counts a space after every word).
  - A word that does not fit but is narrower than the limit starts a new
    line.
  - A word as wide as the limit or wider is **cut**: as many of its
    characters as fit together with a hyphen stay on the current line,
    followed by the hyphen (unless the piece already ends with one); the
    rest is treated as the next word.
  - Each finished line has its trailing spaces removed.
- Without `multiLine`, only the first line is kept.
- The result: the lines with their widths, whether anything was hyphenated,
  the widest line, and the number of non-space characters.

**Note on certainty:** the decompiler output for `split` jumps in and out of
its loops, so the order "add word / cut word / finish line" above is my
reconstruction. The pieces and their conditions are from the code; the
exact behaviour at the edges (an empty word from two spaces in a row, a
paragraph ending exactly at the limit) is **not tested against the game**.

## Cross-check with the files

`fonts_check.py` (run 2026-10-14):

- `Fonts.xml`: 16 fonts, only the attributes `id`, `file`, `lineheight`; no
  repeated id. They use 12 font files; all 12 exist and none is unused.
- Every `.fnt` has one sheet, and the sheet exists.
- In every file each `letter` is one character after translating the seven
  names, its code equals the `id` attribute, and no letter repeats. So
  filing by `letter` or by `id` gives the same table with this data.
- 11 files have `A`. `Digits` has only `.` and `0` to `9` (its `count`
  attribute says 95, which shows `count` is not reliable) and takes its
  measurements from `0`.
- Letters per file: 1,329 to 1,359 for the text fonts, 163 for
  `proggytinytt_regular_16`, 11 for `Digits`.
- Font ids used by the XML data files: `regular` (44 times), `title_thick`,
  `small_tight`, `regular_short`, `large`, `regular_tall`, `regular_short2`,
  `small_harsh`, `tiny`. The other ids are asked for from code (not listed).

Measurements, from the reference script (**not from the running game**):

| Id | File | Line | Ascent | Cap | Descent | Space |
|---|---|---|---|---|---|---|
| `tiny` | `minikylie_u_regular_8` | 8 | 7 | 5 | 1 | 1 |
| `small_harsh` | `5mikropix_regular_8` | 9 | 9 | 5 | 0 | 2 |
| `small_tight` | `atarismall_u_regular_8` | 8 | 7 | 6 | 1 | 4 |
| `digits` | `Digits` | 5 | 5 | 5 | 0 | 0 |
| `regular` | `bmmini_u_regular_8` | 9 | 7 | 6 | 2 | 2 |
| `regular_short2` | `bmmini_u_regular_8` | 8 | 7 | 6 | 1 | 2 |
| `regular_tall` | `bmmini_u_regular_8` | 12 | 7 | 6 | 5 | 2 |
| `regular_short` | `04b03_u_regular_8` | 9 | 7 | 5 | 2 | 2 |
| `regular_transcript` | `04b03_u_regular_8` | 8 | 7 | 5 | 1 | 2 |
| `ui_regular` | `notnokia_u_regular_8` | 10 | 8 | 7 | 2 | 2 |
| `ui_large`, `title_tall` | `pixelplay_regular_16` | 20 | 16 | 12 | 4 | 5 |
| `large` | `resource_u_regular_8` | 10 | 10 | 7 | 0 | 2 |
| `fixed` | `proggytinytt_regular_16` | 16 | 8 | 7 | 8 | 6 |
| `title_thick` | `chixa_demibold_14` | 11 | 12 | 9 | -1 | 4 |
| `title_news` | `motorolascreentype_u_regular_16` | 20 | 18 | 15 | 2 | 3 |

## Not known

- How `app.vis.Text` places lines and letters (alignment, padding, the
  background box), and which code asks for which font id.
- Other languages: the language packs in `StreamingAssets/loc/` may bring
  their own fonts; not looked at.
