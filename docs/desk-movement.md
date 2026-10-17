# Drawing, part 5a: how a paper moves on the desk (`DeskItem`)

Studied on 2026-10-16. Part 4 (`desk-pictures.md`) covered a paper's
pictures; this part covers where the paper is and how it moves: how it
appears (the reveal animations), how it leaves (the hide animations),
dragging and dropping between the counter, the desk, the drawer and the
wall, the give area, what a paper does when let go, the dock points of
the rulebook, bulletin and transcript, and the drawer's movement. The
inspect mode is part 5b (`inspect-mode.md`).

Everything here is from the code; **nothing was compared with the running
game**. Positions are in booth coordinates (`booth-layout.md`: the booth
is the 570 x 217 area below the border scene; the desk is x 178..570,
the counter column x 0..178). Desktop has no carousel and no multitouch
(`desk-pictures.md`; the `BOOTH_MULTITOUCH` upgrade is tablet only,
`night-pictures.md`), so those branches are left out.

Reference script: `scripts/reference/deskmove.py` (every rule below,
frame by frame). Check: `scripts/checks/desk_movement_check.py`.

Words used here:

- **placement**: where the paper is, one of `OUTER` (closed, on the
  counter side), `INNER` (open, on the desk), `FILER` (in the drawer),
  `MOUNT` (hung on the wall); part 4 lists which picture each shows;
- **state**: what the paper is doing: `NONE`, `REVEALING`, `NORMAL`,
  `RETURNINGTODOCK`, `HIDING`, `HIDDEN`, `GIVING`, `GIVEN`;
- **frame**: one update of the game, normally 1/60 s (`border-view.md`);
  `dt` is its length in seconds;
- **clamp**: holding a position inside a range.

## What was read

Read in full in `decompiled/all/play_day_booth.clean.c` (`DeskItem`):
`startRevealAnim`, `animateReveal`, `startHideAnim`, `animateHide`,
`startCustomDrag`, `updateCustomDrag`, `endCustomDrag`, `react`, `update`,
`clampPlacementPos`, `set_placement`, `commitToFiler`, `initInFiler`,
`isOverFiler`, `returnToDock`, `moveDepthToTop` and its sort function,
`wantMoveDepthToTopWhileDragging`, `getDragIsCommitted`, the `get_is...`,
`get_canGive`, `get_giveable`, `get_isBlockingOtherGiving` getters, the
static values, the dock-point part of the constructor;
`coordinateReavelFloating`, `unfloatIfPossible` and the `carousel...`
functions only far enough to see they need a carousel. `TouchDrag` (all).
`Filer`: `getLocalSlotPos`, `getCount`, `react`, `set_open`, `set_openT`,
`height`, `width`, `update`, `openIfClosed`, `closeIfOpen`,
`bumpIfClosed`, the four state functions, and the constructor's sizes and
states. `Paper`: the constructor's choice of reveal and hide, `onClick`,
`followLink`, `flipPageIfPossible`, `testHasLink`, `get_mountPos`,
`set_mountPos`, `getMountPosFactPath`. `Booth`: `engine_onPapersAdded`
(the callbacks), `deskItem_onGiven`, `onHidden`, `onMounted`,
`onPutInFiler`, `onRemoveFromFiler`, `testGiveable`, `onDoubleClicked`,
`hideTransientPapers`, `updateHidingPapers`, `onCallingNextTraveler`,
`applyMountedPaperIdsOrder`, the three state functions that hide papers.
In `data.clean.c`: `DockPoint` (constructor, `clampDrag`, `returnHome`,
`get_toasterPos`). In `app_misc.clean.c`: `app.Num.lerpScale`.

Three read-only Ghidra runs for what the decompiler dropped
(`decompiled/drawing5_run1.txt` to `drawing5_run3.txt`): the
instructions of the `Filer` constructor (its state timings),
`Paper.set_mountPos`, `get_mountPos`, `DeskItem.animateReveal`,
`startCustomDrag` (the `toTop` sound) and the helper
`FUN_180131040` (the remainder `fmod`, from its instructions: two
numbers, exponent handling); 33 constants with `read_doubles.py`.

## How a paper appears

The `Paper` constructor ends with `startRevealAnim(wall position)`. The
reveal is the paper's `reveal` from `Papers.xml` (`papers-xml-format.md`),
**replaced** in these cases, checked in this order:

1. A paper that can hang on the wall and has a saved wall place
   (`Game/MountPos/<paper>`, below): `ONWALL`.
2. A paper that stays on the desk from an earlier day and is added in the
   first second of the booth's clock (`Booth.engine_onPapersAdded` counts
   them): `ONDESK(4, 4 + 10 x its number)`, so they lie in a small
   staircase at the desk's top left.
3. A paper with a non-empty `<paper>/OpenToPage` fact: `ONDESK(6, 47)`.
   In the game this is the rulebook on a day with a page to open
   (`Rules/OpenToPage`, set when the traveler is made,
   `traveler-creation.md`).

The hide is always `OFFBOTTOM` at first; the booth may ask for
`TOFILER` when it hides papers (below).

`startRevealAnim` sets the state `REVEALING`, the fall speed to 0, makes
the paper visible and places it:

| Reveal | Start | Placement |
|---|---|---|
| `DOCKED` | its dock home's top left | `OUTER` |
| `FROMSLOT` | x = floor(slot centre x − closed width / 2), y = slot centre y − closed height: just above the slot, hidden by the slot clip | `OUTER`; sound `dragStart` of its sound set |
| `PRINTBOTTOM` | x = floor(floor(desk middle x) − page width / 2), y = `boothPrintBottomY` (217); countdown 6 s | `INNER` |
| `SPITFROMRIGHT` | x = desk's right edge (570), y = desk top + 80; countdown 0.5 s | `INNER` |
| `ONDESK(x, y)` | desk top left + (x, y), then clamped | `INNER` |
| `INFILER` | its slot in the drawer | `FILER` |
| `PRINTTOP` | x as for `PRINTBOTTOM`, y = desk top − page height (above, out of sight); countdown 3 s; sound `photo-print` | `INNER` |
| `ONWALL` | the saved wall place, then clamped | `MOUNT` |

Then every frame (`animateReveal`), and after it the position is rounded
to whole pixels (Haxe `Math.round`):

- **`FROMSLOT`**: y moves down at 350 pixels a second until the closed
  paper's middle reaches `outerFloorMidY` (145); then `NORMAL` and the
  sound `drop`. A passport (closed 30 x 42) falls from y 74 to y 124 in
  9 frames (the check lists every paper).
- **`PRINTBOTTOM`** (the identity record, the citation, the missing-paper
  hint): p = max(0, 1 − countdown / 3), so **nothing moves for the first
  3 seconds**, then p goes from 0 to 1 over 3 seconds.
  - While p < 0.8 it prints line by line: with `L` = whole part of
    (page height − 1) / 20 lines and `f` = p / 0.8 x `L`, line n = whole
    part of `f`, its part done `r` = `f` mod 1; y = 217 − (20 n +
    min(20, 40 r)). So each line feeds 20 pixels in the first half of its
    time, then pauses. When the line number changes between this frame
    and the next (or printing starts), the sound `printer-feed` plays,
    `printer-tear` for the last line; when `r` crosses 0.5 within a line,
    `printer-line`.
  - From p = 0.8: q = (p − 0.8) / 0.2, y goes from 217 − (height − 20)
    to 217 − height − 20 along 1 − (1 − q)^5 (fast, then slowing), so the
    page ends with its bottom 20 pixels above the booth's bottom. The
    drag shadow shows while q < 0.5, and `dragStop` plays when q crosses
    0.5.
  - At countdown 0: `NORMAL`, shadow hidden. 361 frames in all.
- **`SPITFROMRIGHT`** (the visa slip, the seizure slip, the blank
  fingerprint form): t = clamp(1 − 2 x countdown, 0, 1); x goes from 570
  to 570 − page width − 20 along 1 − (1 − t)^4, over 0.5 s. The sound
  `paper-spit` on the first frame (when the countdown passes 0.5). The
  shadow shows until the end; then `NORMAL`. 31 frames.
- **`PRINTTOP`** (the search photo): p as above but over 3 s from the
  start; while p < 0.8, y moves linearly from desk top − height to desk
  top − 40; then along 1 − (1 − q)^5 to desk top + 20. Shadow while
  q < 0.5, `dragStop` at 0.5. 181 frames.
- **All others**: `NORMAL` on the first frame.

## How a paper leaves

`startHideAnim(kind)`: state `HIDING`, fall speed 0, the sound
`dragStart`, and the hide kind if one is given. Every frame
(`animateHide`):

- **`OFFBOTTOM`**: the speed grows by 12,000 pixels a second, each
  second. A closed paper (`OUTER`) moves **left** by speed x dt and is
  gone when x ≤ −closed width; any other moves **down** and is gone when
  its y reaches the desk's bottom (217).
- **`TOFILER`** (into the drawer): the target is the paper's slot in the
  drawer. x moves a fifth of the way to it each frame until within half
  a pixel, then x snaps and y does the same; when both are within half a
  pixel the paper is placed there. On every frame the placement becomes
  `OUTER` if the position is inside `boothOuter` (the counter column),
  else `FILER`.
- When gone: `HIDDEN` and the booth's `deskItem_onHidden`. While not yet
  gone it is moved to the top of the drawing order and its clips are
  updated each frame.

**Who hides papers.** `Booth.hideTransientPapers`, called by three of the
booth's state functions (the ones at lines 531, 608 and 624 of the
`Booth` constructor; one of them also closes the shutter and starts the
detain sequence), hides every paper that is not hidden and whose `stay`
is none (`papers-xml-format.md`): with `OFFBOTTOM` unless the engine says
it is auto-confiscated (`player-actions.md`), in which case the drawer is
opened if the paper is not already in it and the hide is `TOFILER`. A
paper already given is left alone. `updateHidingPapers` reports whether
any paper is still hiding; the booth waits for it.

`deskItem_onHidden`: if the paper was given, nothing. If it is in the
drawer or auto-confiscated, the engine confiscates it
(`confiscatePaper`, `player-actions.md`) and the drawer envelope that the
engine names is placed in the drawer at the hidden paper's position
(`initInFiler`).

## Dragging

### Starting

`react` (every frame, desktop): the pointer must be over the paper's
rectangle (`worldRect`) and, if the paper is not being dragged, pass the
odd-shape test (`desk-pictures.md`). The cursor is the **hand** over a
mark with a link (unless the drag has moved 4 pixels or more) and over a
closed paper, otherwise the arrow; either only if nothing has set the
pointer's cursor yet this frame. Then:

- on the press (`justDown`): `startCustomDrag`;
- while held (`down`): the drag's cursor position is updated and the
  pointer is captured for the paper until the end of the frame (how a
  take works, and that it lasts to the end of the next frame:
  `input-handling.md`, read on 2026-10-16; this said input handling was a
  later step);
- when the paper is being dragged and the pointer is not held (or no
  pointer was given for it this frame): `endCustomDrag`;
- on a double click: `whenDoubleClicked` (the inspect mode's quick
  inspect, `inspect-mode.md`).

`startCustomDrag` works only in the state `NORMAL`. It remembers the
placement at the start, sets "dragging", "not yet moved" and "was
dragged", and remembers the time. A closed paper with a dock point is
first put at its dock home, lifted 6 pixels (entry `TOP`). It remembers
the offset from the paper's corner to the cursor, the start position,
starts the drag velocity (`TouchDrag`) and moves the paper to the top of
the drawing order. The sound `toTop` of its sound set plays only when
the paper **was already** the last of its parent's children (on top):
the other way round from what the name suggests. Checked in the
instructions (`decompiled/drawing5_run3.txt`: the index is compared
with the children count − 1 at `0x18045cf56`, and the sound field read
is `SoundsDef.toTop`, `+0x30`). Not seen in the game.

### Every frame of a drag (`updateCustomDrag`)

The cursor (in booth coordinates) decides the placement, in this order:

1. **Over the drawer** (a paper that can go in the drawer, and the
   cursor right of the desk's left edge (178), below the drawer's top
   and left of the drawer's right edge): `FILER`. The paper keeps its
   offset to the cursor if the drag started in the drawer (or, for the
   drawer envelope, started open), otherwise it is centred on the
   cursor. The drawer opens.
2. **Over the desk** (`boothInner`: right of x 178): `INNER`, keeping the
   offset if the drag started open (or, for the envelope, in the
   drawer), otherwise centred; then clamped; no give icon.
3. **Otherwise** (the counter column):
   - a paper that can hang on the wall, when it may not be given now and
     the cursor is at y 100 (`boothMountDragBottomY`) or above: `MOUNT`,
     keeping the offset if the drag started on the wall, otherwise
     centred; clamped;
   - else `OUTER`, keeping the offset if the drag started closed,
     otherwise centred; a docked paper is held by its dock point's drag
     clamp (below), the others clamped. **The give icon shows** when the
     paper may be given now (`YES_NOW`, below), the cursor's x is inside
     the give area (x 39..139) and the closed paper's bottom edge is
     inside its height (y 0..107).

Then: the position is rounded to whole pixels; the first time the cursor
is more than 1 pixel (in x or y, whole pixels) from where the drag
started, the sound `dragStart` and "moved"; the drag shadow shows when
the paper is open and has moved; the paper is moved to the top of the
drawing order; the clips are updated.

### The clamps (`clampPlacementPos`)

| Placement | x range | y range |
|---|---|---|
| `INNER` | from 178 − page width + m to 570 − m, m = min(70, page width) | from 0 − page height + n to 217 − n, n = min(30, page height) |
| `OUTER` | 0 to 178 − closed width / 2 (`OUTER_LEFT`: half the paper may cross onto the desk) | 0 to 145 − closed height / 2 |
| `MOUNT` | −wall width / 2 to 178 − wall width / 2 | −wall height / 2 to 107 − 10 |

So an open page always keeps at least 70 x 30 pixels (or all of itself
if smaller) on the desk, and a closed paper stays above the counter's
floor line.

### Dropping (`endCustomDrag`)

1. Not dragging; the sound `dragStop` if it moved; the drag velocity is
   kept (for the slide below); the shadow hidden.
2. In the drawer: `commitToFiler`: the paper's middle stays where it is
   while its placement becomes `FILER` (its corner moves by the size
   change); its position in the drawer is remembered; the booth's
   `deskItem_onPutInFiler(first time?)` (the engine's `putPaperInFiler`,
   `player-actions.md`).
3. On the wall: it sinks 2 pixels (`kMountDropSink`).
4. Moved to the top of the drawing order; clips updated.
5. If it started in the drawer and left it: `deskItem_onRemoveFromFiler
   (first time?)`.
6. If it can hang: `deskItem_onMounted(on the wall?)`: the booth saves
   the wall place (`Game/MountPos/<paper>` = "x y" relative to the wall's
   corner, each cut toward zero; read back by adding the wall's corner)
   or clears it, and saves `Game/MountedPapers`, the ids of all hung
   papers in drawing order, separated by `;`.
7. If the give icon was showing and the paper may still be given now:
   **state `GIVING`**.
8. The give icon is hidden, the fall speed set to 0.
9. **A click**: if the cursor moved less than 4 pixels from where the
   drag started (`kDragClickDist`, whole pixels in x or y), the mark
   under the cursor (`getInnerVisualAt`, `desk-pictures.md`) is passed to
   `Paper.onClick`: if that mark has a link, it is followed
   (`#next`, `#prev`, `#home`, `#back` or another page's id, with the
   sound `turnPage` of its sound set; any other link starting with `#`
   goes to the booth's `paper_onUnhandledLinkClicked` without a sound;
   `page-layout.md`).

## The give area

`Booth.deskItem_testGiveable` answers:

- **`NO`** unless the booth is in the state `working` or `resisting`,
  the shutter is open, the curtain is open, and the engine says this
  paper can go to the traveler (`canGivePaperToTraveler`,
  `player-actions.md`);
- **`YES_WAITING`** if another paper is being given right now;
- **`YES_NOW`** otherwise.

Only `YES_NOW` shows the icon and gives. A paper being given
(`GIVING`) falls each frame: the speed is 1 pixel a second on the first
frame, then grows by 3,000 a second, each second; when its top passes
`counterTopEdgeY` (107) it becomes invisible, `GIVEN`, the sound
`givetake-close` plays and the booth's `deskItem_onGiven` hands it to the
engine (`givePaperToTraveler`). Its clip shows only the part above the
counter's edge (`desk-pictures.md`), so it seems to drop behind the
counter.

## When the paper is let go (state `NORMAL`)

Every frame, when not dragged:

- **Closed, with a dock point** (rulebook, bulletin, transcript): the
  dock's return path (below).
- **Closed, without**: while above the floor line (its middle above y
  145): it slides with the drag velocity (below), is clamped, and falls:
  the speed grows by 3,000 a second each second and y grows by at least
  1 pixel a frame. On reaching the floor line it stops there, with the
  sounds `drop` and `dragStop`, and the velocity is cleared. A closed
  passport let go at y 10 lands in 17 frames.
- **Open**: while the drag velocity is at least 1 pixel a second, it
  slides and is clamped (a throw). A page let go moving at 600 pixels a
  second slides 29 pixels in 23 frames.
- **In the drawer**: its position in the drawer moves half way to its
  slot each frame (snapping within 1 pixel), so the papers in the drawer
  close up when one is taken out.

### The drag velocity (`TouchDrag`)

While dragging, each frame: velocity = half the old velocity + half
(the cursor's move this frame x 60), in pixels a second. After the drag,
each frame: if the speed is below 1 pixel a second it is set to 0;
otherwise it is multiplied by 0.75^(60 x dt) (0.75 per 1/60 s) and the
position moves by velocity x dt, rounded. Its clock is its own
`app.Clock`.

### Going back to the dock

On the first traveler of the day (`Booth.onCallingNextTraveler`), the
bulletin goes back to its dock if it was never dragged
(`returnToDock`, state `RETURNINGTODOCK`). It slides left at 750 pixels
a second while open; once its x is left of 178 − page width / 2 it
becomes closed at x = floor(178 − closed width / 2), y + floor(page
height / 2); on the next frame `NORMAL`, and then the return path.

**The dock points** (`booth-layout.md`; all three have entry `TOP`):

- *While dragged closed* (`clampDrag`, on the paper's middle): if the
  paper's bottom would be below the clamp's bottom (y 178): over the
  dock's own column, the middle snaps to the dock's middle x and is held
  no lower than the dock's middle y less half the paper's height x t,
  t = how far off the column's middle, from 0 (in its middle half) to 1;
  elsewhere it is held with its bottom at 178. Then the middle is clamped
  so the whole paper is inside x 0..570, y 0..178.
- *When let go* (`returnHome`, each frame): if below the home's top, it
  rises 500 pixels a second to one pixel above it; else, if not at the
  home's x, it moves sideways 500 pixels a second to it; else, if above
  the home, it falls (speed + 3,000 a second each second, at least 1
  pixel a frame) and lands on it, with `drop` and `dragStop`. The check
  runs it from three places; each lands at its home within 33 frames.

The dock homes have exactly the sizes of the three closed pictures
(rulebook 26 x 34, bulletin 21 x 38, transcript 37 x 46).

## Drawing order (`moveDepthToTop`)

- A paper in the drawer: all papers in the drawer are re-sorted by y
  (lower ones drawn later, so on top).
- Any other: put last among the booth's papers (on top), except that a
  paper being printed (`PRINTTOP` or `PRINTBOTTOM`, while revealing)
  stays above it: the paper goes just before the first such paper.
- On a day's start, once the papers are added, the rulebook and then the
  bulletin are moved to the top. When a saved game is loaded,
  `applyMountedPaperIdsOrder` moves each hung paper to the top in the
  order of `Game/MountedPapers`, which puts back their drawing order.
  (This settles an item of `save-format.md`.)

## The drawer (`Filer`)

`assets/Filer.png` (190 x 210) at x 198 (`Layout.filer`); it rises from
y 217. Its open height is the picture's height (210) and its closed
height 8 (plus 5 for each with the big handle, which desktop has not), so
closed it shows 8 pixels, open its top is at y 7. Its y = (217 − 8) + t x
((217 − 210) − (217 − 8)) for t from 0 (closed) to 1 (open).

Three states (`app.Stater`, `border-scene.md`):

- `closed`: t goes to 0 over 0.5 s along `BOUNCEBACK(0.1, 1)`; on entering,
  the sound `filer-close` unless a bump played it in the last 0.6 s;
- `open`: t goes to 1 over 0.5 s along `INVPOW(3)`; on entering, the
  sound `filer-open` and `whenOpened`;
- `bumping` (asked by the phone's carousel only): lasts 0.5 s, then
  `closed`; on entering, `filer-close`; while in it, t = sin(2π x time) x
  0.1 (the helper `FUN_180130a00` is the sine, `fact-pictures.md`, and the
  constant is Haxe's `Math.PI`, its static at `+0x8` in `dump.cs`; this was
  first marked inferred, checked 2026-10-16 in `ui-parts.md`'s step).

A click on the drawer (a press inside its rectangle, whose height is
taken as 1,000 so it reaches below the screen) opens or closes it. Its
papers get the input first (last drawn first). A paper's slot in the
drawer is (3, 20 + 10 x the number of papers before it in the drawer),
in the drawer's coordinates. On desktop the drawer shows no count
(`filerCountCenter` none).

## Random draws

None. (The tilt of a closed paper is made in the `Paper` constructor,
part 4.)

## Preview and checks

`desk_movement_check.py scripts/reference extracted/art` (run 2026-10-16)
prints `problems: none`. It lists every paper's reveal with its start,
end and number of frames (55 from the slot, 3 printed from the bottom,
3 spat from the right, 1 printed from the top, 3 laid on the desk, 2
docked, 1 in the drawer); the dock homes against the closed pictures
(same sizes) and the return path from three places; the clamp ranges
on random positions; a fall and a throw; and the placement and give
icon for seven cursor points, ending with a give.

`deskmove.py` alone prints a passport's fall from the slot and a
citation being printed.

## Notes for the port

- Run these per frame with the game's `dt`; the speeds are in pixels a
  second, and the drag velocity's decay depends on `dt`.
- Keep the rounding: whole pixels after each reveal frame and each drag
  frame (`Math.round`), floor in the return to the dock.
- The 3-second wait before a printed paper moves is part of the game
  (`kPrintDelay`), not a stall.

## Not studied

- (The drawing order inside one layer was listed here: read on
  2026-10-17, `screen-output.md`. Inside a layer the visuals are drawn
  in the order they were added, so papers on one layer come out in the
  order they draw, the drawing order above; the host keeps it.)
- The engine side of giving, confiscating and the drawer
  (`player-actions.md` has the rules; the booth's state machine that
  calls `hideTransientPapers` was not named state by state).
- The curves `BOUNCEBACK` and `INVPOW` (`app.Interp`), also open in
  `buttons.md`.
- The carousel's floating papers (`coordinateReavelFloating`; phone
  only).

## Things to watch in the game

None was done.

1. A document from the slot drops onto the counter in about a sixth of a
   second.
2. A citation or identity record: nothing for 3 seconds, then it prints
   line by line with feed, line and tear sounds, then slides up.
3. A visa slip slides in from the desk's right edge in half a second.
4. An open page cannot be dragged so far that less than 70 x 30 pixels
   stay on the desk.
5. A document dropped over the traveler's window, while the traveler may
   take it, sinks behind the counter edge.
6. The rulebook dropped anywhere on the counter rises, slides and drops
   back into its place.
7. A page thrown on the desk slides a little and stops.
