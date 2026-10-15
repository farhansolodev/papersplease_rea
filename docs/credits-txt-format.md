# Credits.txt: the scrolling credits

Studied on 2026-10-14. `Credits.txt` is the text of the credits list. It is
an indented tree (`tab-tree-format.md`); the list is built by walking the
tree top down and stacking each line under the previous one.

Check: `scripts/checks/credits_check.py`.

Functions read in full: `play.screen.CreditList` (constructor, `addNode`,
`addText`, `addImage`, `draw`, its static values). The screen that
creates the list and scrolls it is the credits screen `CreditScreen`,
written up in `screens.md` part 6 (2026-10-15): where the list sits, the
4-second hold at the first view, the speed (0.5 pixel a frame, 4 times
that while the mouse button is held), the loop. (This sentence first
guessed "the title or ending screen"; part 5 found that the ending
screen does not make it, and part 6 that the title does not either: both
only fade to the credits screen.)

## A line

Each line is split into words at spaces. The **first word** decides what the
line is:

| First word | Result |
|---|---|
| `?` | a condition; the next word is the condition. `have-lang-<code>`: the line **and everything indented under it** is skipped unless language `<code>` is among the available languages. The two words are removed and the rest is handled as below. Any other condition word is simply removed |
| `+` | text in the style **role** (a heading such as "Special Thanks") |
| `/` | text in the style **team** |
| `-` | text in the style **small** |
| `$` | text in the style **finale** |
| `[OFFSCREEN]` | the next line starts 18 pixels above a height given by the screen. The credits screen gives the height that puts this point 18 pixels above the bottom of the visible band while the list is held at its first view; with the role heading that follows in the file (+20 before it), the next line starts 2 pixels below the band, out of sight (`screens.md` part 6). So the first view shows only what comes before `[OFFSCREEN]`. This was first an inference; it is now worked out from the code's numbers, not seen |
| `[SPACE]` | a gap of 20 pixels |
| `[IMAGE] <file>` | the picture `assets/<file>` |
| anything else | text in the style **name**, the whole line |

For the four marked styles the marker word is dropped and the remaining
words are joined with single spaces. (That the marker is dropped is certain
from the result; the exact test in the code was scrambled by the
decompiler.)

Indentation does not change how a line looks; it only matters for what a
`?` condition hides. Children are added right after their parent.

## How the lines are laid out

The list is `min(260, screen width in game pixels - 20)` wide. A running
"top" position starts at 0.

Text is centred, wrapped to the list's width, and placed at the current
top; then the top moves down by the text's height plus the style's extra.

| Style | Font (`fonts.md`) | Colour | Before | Extra after | Other |
|---|---|---|---|---|---|
| name | `title_tall` | white | | -2 | |
| role | `large` | `#546754` (grey green) | +20, except for the very first thing in the list | 0 | |
| team | `large` | white | +2 | +2 | underlined: a white line 1 pixel high, as wide as the text, 4 pixels below the font's capital height |
| small | `large` | white | | 0 | |
| finale | `large` | `#cc2e2e` (red) | | 0 | |

A picture is centred, placed 4 pixels below the current top, and the top
moves to 4 pixels below the picture.

Drawing clips the list to a band of the screen given by the creator
(a top and a bottom position).

## Cross-check with the file

`credits_check.py` (run 2026-10-14):

- With every language available: 19 role lines, 45 names, 8 teams, 28 small
  lines, 1 finale line, 3 pictures, 8 gaps, one `[OFFSCREEN]`: 113 lines.
- Two conditions, both of the known kind: `have-lang-id` (Indonesian) and
  `have-lang-eu` (Basque). With only English available, 109 lines.
- Both language codes are in `Languages.txt`.
- The three pictures (`CreditsHaxe.png`, `CreditsFreesound.png`,
  `CreditsCopyright.png`) exist in the extracted assets.
- No line starts with a marker the code does not know.
- The tree is at most three levels deep.

## Not known / not tested

- (Answered on 2026-10-15, `screens.md` part 6: the credits screen shows
  the list and sets the scroll speed. "Available languages" is the list
  of `.zip` files in the game's `StreamingAssets/loc` folder; this install
  has 16, including `id` and `eu`, so all 113 lines are shown. The
  language chooser's test for user-added languages is read since,
  `languages-list.md`; the chooser itself is left out of the port by the
  user's decision of 2026-10-16, English only. Which `have-lang-` lines
  an English-only port shows is for the design.)
- Nothing here was compared with the running game.
