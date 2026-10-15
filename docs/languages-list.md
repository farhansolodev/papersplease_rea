# Languages.txt and Languages.png: the language list

Studied on 2026-10-14. Two small files drive the language chooser screen:
`Languages.txt` lists the language codes, and `Languages.png` holds each
language's name as a picture (so that every name can be shown in its own
script whatever font is loaded).

Check: `scripts/checks/languages_check.py`.

Functions read in full: `LangChooser.hasUserAddedLanguages` and the static
values. Read in part: the `play.screen.LangChooser` constructor and
`setPage` (only where they use the two files). **Not studied:** the rest of
the chooser (its buttons, pages and what happens when a language is
applied), and how a language pack is loaded.

## Languages.txt

Plain text, **one code per line, split at line-feed characters and not
trimmed**. So the file must not have blank lines, a line break at the end,
or Windows line endings: each would become part of a code or an extra,
empty code. The shipped file obeys this (51 bytes, no final line break).

The codes, in order: `cs de en es eu fr id it ja ko pl pt-BR ru tr ukr zh`.

## Languages.png

One picture, one row per code, in the same order:

- the row width is the picture's width (110);
- the row height is the picture's height divided by the number of codes
  (320 / 16 = 20), as a whole number;
- row `i` (from 0) is the name of code `i`.

The chooser builds its buttons from these rows (three button pictures 40
pixels wider than a row: normal, selected, pressed) and shows as many per
page as fit the screen.

## User-added languages

`hasUserAddedLanguages(available codes)` answers yes when the list of
available languages differs from `Languages.txt`: a different number, or a
different code at any position. The available codes are the names of the
`.zip` files in the game's `StreamingAssets/loc` folder, sorted
(`HostUnity.UnityPlatformDisk.getAvailableLanguageCodes`, read on
2026-10-15 for `screens.md` part 6; this sentence first said where the
game looks was not studied). So a language is "user-added" when someone
puts another `.zip` in that folder. This install has 16 files whose
names are exactly the 16 codes above, in the same order, so the answer
here is no (the sort is .NET's default string sort; for these 16 names
it gives the order of the file, inferred, not run). The credits use the
same list of available codes for their `have-lang-` lines
(`credits-txt-format.md`).

## Cross-check with the files

`languages_check.py` (run 2026-10-14, needs Pillow):

- 16 codes, none empty, padded or repeated.
- The picture is 110 x 320: exactly 16 rows of 20 pixels, and no row is
  blank.
- `StreamingAssets/loc/` has 16 language packs, `<code>.zip`, one for every
  code and no others; the codes are in the same (alphabetical) order as the
  pack names.

## Not known / not tested

- The chooser screen itself and language loading (see above).
- Whether the port offers other languages at all is a design decision not
  yet made. Of the language packs only the list of files inside has been
  looked at (`art-dat-format.md`, "Not done"); their contents have not been
  studied.
- Nothing here was compared with the running game.
