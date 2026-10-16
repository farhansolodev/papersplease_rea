# Drawing, part 7: the rest of `play.ui`

Studied on 2026-10-16. `play.ui` holds the game's interface pieces.
Read earlier: `Button`, its looks (`Mode`), `ButtonHelper` and
`HoverButton` (`buttons.md`), `RevealTextEnt` (the typing text,
`screens.md`), `FramerateCounter` (`screens.md`). This part covers the
rest: the dotted diagram line, the straight dotted line, the speech
bubble, the drag-and-coast helper, and the achievement popup in outline.
The drawn cursor (`CursorEnt`) is in `input-handling.md`, with the
pointer.

Everything here is from the code; **nothing was compared with the running
game**.

Reference script: `scripts/reference/ui.py`. Check:
`scripts/checks/ui_check.py`.

## What was read

In `decompiled/all/play_ui.clean.c`, in full: `DiagramLine` (constructor,
`addPoint`, `addDottedTo`, `addDotted`, `buildDots`, `buildTiles`,
`clearPoints`, `getPointAt`, `get_numPoints`; `makeTestLines` only to
see it is a test), `DottedLine` (all), `SpeechBubble` (all),
`KineticScroll` (all), the rest of `RevealTextEnt` (`draw`, `set_text`,
the getters and setters); `AchievementPopup`'s constructor, states and
`show` in outline. `play.AlltimeStats.update` far enough to see who shows
the popup. Haxe's `Math` static fields from `dump.cs` (`PI` at `+0x8`);
four constants with `read_doubles.py`.

## The dotted diagram line (`DiagramLine`)

Used by the inspect mode (`inspect-mode.md`) and the screens' rules
(`screens.md`). It is **dotted**: single pixels, each more than one
pixel (in x or y, after rounding) from the one before, so two apart on a
straight run. This answers the open question of `screens.md` ("dotted
or solid").

- Points are added floored to whole pixels; the line's length is kept.
- The dots (`buildDots`), from the first point: for each inner corner, a
  straight run to where the corner's curve starts, then a quarter circle
  of radius r = min(corner radius, the two segments' lengths) (default
  corner radius 10), in 2r steps of the angle (sine and cosine of
  π/2 x k / 2r), then on to the last point. A straight run walks
  ceil(length) steps from the last dot and adds a rounded dot whenever it
  is far enough, then the end point if far enough.
- Each dot is one tile of the 1 x 1 white picture in the line's colour.
- **How much shows**: `visibleT` from 0 to 1; the first floor(dots x
  visibleT) dots get the colour's alpha, the others alpha 0. So a line
  "draws itself" from its start.

The check runs four polylines (26, 38, 71 and 3 dots; none too close).

## The straight dotted line (`DottedLine`)

Used under the centred speech bubble. Made of two strips, 32 x 1 and
1 x 32, with every other pixel (even ones) in the given colour.
`set(p0, p1)`: horizontal when the two y differ by less than 1, else
vertical; the line from the lower to the higher whole coordinate is cut
into pieces of at most 30 pixels, each taken from the strip starting at
the piece's own parity, so the lit pixels are always at even positions.

## The speech bubble (`SpeechBubble`)

Made by the booth's chat list (`SpeechChat`, five places in its
constructor) and by the border scene (two). What it says is in `speech.md`.

- **Look**: `assets/SpeechBubble.png` (20 x 20) as a nine-slice frame
  with middle (2, 2, 14, 14) (`vis-basics.md`); text in `small_tight`,
  colour `0xFF34353F`, several lines allowed; padding 4. Aligned left,
  centred or right of its position; a centred bubble also has a dotted
  line in `0xFFEDE0D8` from the box's bottom edge 14 pixels down, which
  grows from its lower end as the bubble opens.
- **`showText(text, delay)`**: after the delay (if any, through the
  bubble's tweener), the bubble closes at once, then: the text wraps at
  120 pixels only if it is wider than 160 in one line; the box is the
  text plus 8 both ways; its left edge is 0 (left), −(width + 8) / 2 cut
  toward zero (centre) or −(width + 8) (right); the text sits 4 pixels in
  and at y = cap height − ascent + 5. The bubble opens and **stays 0.1
  second per character** (unless made to stay open), then closes. It
  returns the delay plus that time. Of the 296 lines of `Speeches.txt`
  as written (placeholders not filled in), 12 are wider than 160 pixels
  and wrap; most stay 1 to 3 seconds.
- **Opening and closing**: states `on` (blend 0.75 s, visible at once,
  reveal to 1) and `off` (blend 0.5 s, reveal to 0, hidden at the end).
  The reveal is split into the dotted line (first quarter), the box's
  width growing from the aligned edge, and a bounce of up to 5 pixels
  wider (sin(π x b)): opening, width over 0.25..0.375 and the bounce
  over 0.375..0.5 of the reveal; closing, width over 0.25..0.75 and the
  bounce over 0.75..1. A bubble without the dotted line starts its
  reveal a quarter in. (The reveal is taken as linear in time: the
  state's default curve was not read.)
- The box is never narrower than its borders; the text is cut to the
  box less 4 pixels on each side while it opens.
- `originOffsetY` = −(line height + 22); `totalHeight` = text height + 8.

## Dragging with momentum (`KineticScroll`)

Used by the load screen's grid (`screens.md` part 3) and the border
scene's panning (`border-view.md`; never moves on desktop). One axis.
Positions are a scroll amount that moves **against** the drag.

- While held, each frame: the move since the last frame is held to ±100
  pixels; the velocity is that move x 60 a second; the scroll moves by
  it, but past either end only a tenth as fast (a rubber band), except
  that on the first frame of a press, or when within 1 pixel of the end,
  it is held at the end.
- After release, each frame: the scroll moves by velocity x dt; past an
  end by 1 pixel or more it is pulled back a fifth of the way (never
  more than 100 past) and the velocity shrinks to decay² of itself; within
  1 pixel it snaps to the end and stops; otherwise the velocity shrinks to
  decay^(60 x dt). The decay is 0.75 unless given (the border uses 0.95).

(Read with some damage in the decompiled output around the axis
choice; the rules above match both axes' code paths.)

## The typing text (`RevealTextEnt`), the rest

`set_text` resets the reveal to the start with a first wait of 0.05 s
(the rest of the typing is in `screens.md`); the other functions pass
straight to its `Text`, and `draw` draws that text when visible.

## The achievement popup (`AchievementPopup`), in outline

`play.AlltimeStats.update` shows it when the platform's social service
reports an achievement as newly awarded. It shows
`assets/achievements/<id>.png` (13 pictures in the archive) in the top
right corner, slot by slot (x = screen width − (width + 5) x slot −
width − 20, starting above the screen), with the sound `ui-achievement`;
it drops in over 0.75 s (`BOUNCEBACK(0.5, 1)`), stays 5 s, and leaves
over 0.5 s (`POW(2)`). The social service is out of scope
(`save-format.md`), so whether the port has achievements at all is the
user's decision; not studied further.

## Random draws

None.

## Notes for the port

- Draw diagram lines and the bubble's line as single pixels two apart,
  not as solid lines.
- Speech lines: wrap at 120 pixels only when wider than 160; 0.1 s per
  character on screen.

## Not studied

- `app.Interp`'s default curve (the bubble's reveal is taken as linear).
- The booth's chat list (`SpeechChat`) and how it stacks bubbles.
- Achievements (above).

## Things to watch in the game

None was done.

1. The inspect mode's lines and the screens' rules are dotted.
2. A speech bubble opens from its edge with a small overshoot and stays
   about 0.1 s per letter.
3. A long speech line wraps into a narrower bubble.
4. The load screen's grid can be pulled past its end and springs back.
