# Input handling: the mouse, the keys and the drawn cursor

Studied on 2026-10-16. This is how the desktop game turns the mouse and
the keyboard into what its parts see each frame: the pointer, its
"pressed this frame" flags, the double click, a part "taking" the
pointer, blocked areas of the screen, keys held back until released, and
the cursor the game draws itself.

Everything here is from the code; **nothing was compared with the running
game**. The keys themselves (which keyboard key is which game key) are in
`screens.md`, part 4, "Every key the game reads"; the order in which the
parts of a screen get input is in `screens.md`, part 4, "Who gets the key
first".

Words used here:

- **pointer**: the game's record of one mouse or finger: where it is and
  whether its button is down. The game keeps three; on desktop only the
  first one (pointer 0, the mouse) is ever used.
- **frame**: one pass of the game loop, about 1/60 s.
- **entity**: one part of a screen (a button, a paper, a panel).
- **take** (the code says *capture*): a part claims the pointer so other
  parts ignore it.
- **blocked area** (the code says *masked area*): a rectangle a part marks
  so that parts asked after it, in the same frame, do not see a pointer
  there.

## What was read

- `HostUnity.Update` (the pointer and cursor part; the key part was read
  in `screens.md`, part 4), `InputWrapper.GetPointerState`,
  `InputWrapper.Update`, `InputWrapper.PointerState.Invalid`,
  `InputWrapper.IsTouchDown`.
- `app.ent.Input`: all of it (the constructor and class setup, `update`,
  the key functions, `getPointerOver`, `getPointerOverEvenIfCaptured`,
  `getPointerJustDown`, `checkPointerJustDown`, `getMainPointer`,
  `getPointer`, `getAnyPointerJustDown`/`JustUp`,
  `getFirstCapturingPointer`, `isCapturing`, `isInMaskedArea`,
  `getIntersectsMaskedArea`, `maskAreaUntilFrameEnd`,
  `maskKeyUntilRelease`, `maskPointerDownUntilRelease`,
  `maskAllPointersDownUntilRelease`, `hidePointersForOneFrame`,
  `get_wantVisibleCursor`, `hasChangedSinceLastFrame`; `getSwipe` in
  outline).
- `app.ent.Pointer`: `update`, `willDoubleClick`,
  `captureUntilNextFrameEnd`, the cursor setters; the swipe part in
  outline (phones only).
- `app.ent.Cursor` (its three kinds) and `play.ui.CursorEnt` (the drawn
  cursor).
- The callers of the masking functions, found by name across
  `decompiled/all/`; `play.day.border.Border.react` and the
  `RifleButton` constructor for the rifle's scope cursor.
- Constants with `read_doubles.py`: 0.2 (double-click time), 2.0
  (double-click distance), 0.5, and the cursor offsets -1, -6, -2.

## One frame

In order (`HostUnity.Update`, then `Game.update` and `Game.draw`, which
were read in `screens.md`, part 4):

1. The host hides the system's own mouse cursor (every frame), reads the
   11 game keys, then the three pointers.
2. `Input.update`: the game clock of the input ticks; the keys are
   updated; each pointer is updated; the list of blocked areas is
   emptied; the "hide the pointers" countdown goes down by one.
3. `Game.update`: Escape may pause; the clock; the screen's own states;
   the entity tree's `update` (first child to last); music; all-time
   statistics; the tree's `react` (last child to first, so the newest and
   topmost parts get input first); sounds; settings; the screenshot key.
4. `Game.draw`: the tree is drawn (first child to last).

So input is handled in `react`, after every `update` of the frame. A part
that records the pointer in `react` acts on it in the next frame's
`update`: a dragged paper follows the mouse one frame late
(`desk-movement.md`).

## From the mouse to a game pixel

`InputWrapper` has a mode. It starts at 0 (no input yet) and becomes 1,
the mouse, in `InputWrapper.Update` as soon as the mouse moves or its left
button is held. In mode 1 pointer 0 is the mouse: valid, "from the mouse",
down while the **left** button is held. (The state has a right-button
field, but the mouse mode leaves it false and nothing reads it: searched
by its name, `buttonDownR`, across `decompiled/all/`.) Every other
pointer, and pointer 0 before the mouse first moves, is "invalid": not
valid, not from the mouse, at (0, 0). Mode 2 is the touch screen; where
it is set was not found in this pass (it does not apply to desktop).

For a valid pointer the host turns the screen position into a game pixel:
Unity's camera gives a point in the world, the game's screen quad (the
picture the whole game is drawn onto) turns it into its own coordinates,
from -0.5 to 0.5 each way, and then

- x = floor((qx + 0.5) x 570)
- y = floor(320 - (qy + 0.5) x 320)

(570 x 320 is the desktop game size; y is turned over because the game
counts down from the top). So the game sees whole pixels only, wherever
the window is and however large it is. An invalid pointer keeps its old
position and is not down. The pointer counts as a **touch** pointer when
it is not from the mouse, so on desktop pointers 1 and 2 are touch
pointers that are never down, and the parts of the game pass over them
(below).

For pointer 0 the host also passes on "the system wants a visible
cursor" = "pointer 0 is from the mouse", and places a Unity object called
`phantomCursor` at the mouse (shown while pointer 0 is from the mouse,
hidden otherwise). What that object looks like on screen was not
settled: the game has a picture `CursorPhantom.png` (19 x 26) and a
function `Game.phantomCursorImage` that returns it, but the call from the
host goes through the game's interface and was not followed. (Inferred:
it is that picture.)

## A pointer's frame (`Pointer.update`)

Each frame, for each pointer:

1. **Down.** The host's "down". If the pointer is masked until release
   (below), down counts as false, and the mask ends once the host button
   is up.
2. **Just down** = down now and not before; **just up** = down before and
   not now.
3. **Position.** The old position is kept (`preWorldPos`). The new one is
   held inside the game's screen, 0..570 and 0..320 (both ends included)
   (`worldPos`); the position as given is kept too (`unclampedWorldPos`).
   The drawn cursor uses the second, so it can be partly off screen.
4. The pointer's **cursor** is cleared (no part has asked for one yet).
5. **Taken.** A countdown: when a part takes the pointer it is set to 2;
   here it goes down by one, and at 0 the pointer is free again. So a
   take lasts for the rest of that frame and all of the next one, and a
   part that keeps the pointer (a held button, a dragged paper) takes it
   again every frame.
6. **Double click.** On a press: it is a double click if the last press
   was less than 0.2 s ago and less than 2 pixels away (straight-line
   distance). Then the time and place of this press are kept. A third
   quick press is a double click again (it is compared with the second).
   Without a press, "double clicked" is false.
7. A swipe and a history of positions are kept on phones only.

## How a part asks for the pointer

Most parts use one of two questions.

**Is a pointer over this rectangle?** (`getPointerOver(ent, rect,
onlyId)`):

1. First, a pointer that **this part has taken**, wherever it is now,
   unless it is in a blocked area.
2. Otherwise the first pointer that **no part has taken**, inside the
   rectangle (left and top edges in, right and bottom out), not in a
   blocked area; one that is held is preferred, else the first one
   found.

A touch pointer that is neither down nor just released is skipped in
both, which is why pointers 1 and 2 never matter on desktop. `onlyId`
limits it to one pointer.

**Was this rectangle just pressed?** (`getPointerJustDown(ent, pos,
rect, cursor)`; `checkPointerJustDown` is the same, answering yes or no;
the rectangle is the part's own, moved to its place on screen):

1. Ask the first question for the rectangle. No pointer: no.
2. If the pointer is inside the rectangle (a taken pointer may be
   elsewhere): the rectangle is **blocked** for the rest of the frame;
   the pointer's **cursor** is set to the one asked for (the hand, if
   none is given), unless a part set it earlier this frame; and if the
   button went down this frame, the part **takes** the pointer and the
   answer is yes.
3. Otherwise no.

Because input goes to the topmost parts first and each one blocks its
rectangle, a click goes to the topmost part under the mouse, and only
that part's cursor shows. The blocked areas are emptied at the start of
each frame. Example: a budget line on the night screen
(`BudgetLineEnt.react`) asks this for its whole rectangle with no cursor
given, so the cursor is the hand anywhere on the row, which matches what
the user saw on 2026-10-14 (`screens.md`, part 1).

Other questions: `getPointerOverEvenIfCaptured` (the first pointer
inside the rectangle and not in a blocked area, taken or not),
`getMainPointer` (pointer 0), `getAnyPointerJustDown`/`JustUp`,
`isCapturing(ent)`, `getFirstCapturingPointer(class)`,
`getIntersectsMaskedArea(rect)` (does the rectangle touch a blocked
area; here all edges count), `hasChangedSinceLastFrame` (a pointer
changed or a key changed).

Which parts block areas themselves (`maskAreaUntilFrameEnd`), found by
name: the inspect mode (`InspectUi`), the stamp desk, the key desk, the
rack, the drop remote, the tutorial cover, and the two "passthrough"
parts (`screens.md`). The buttons block through `getPointerJustDown`
and their own code (`buttons.md`).

## Keys

Each frame, for each of the 11 game keys: the old state is kept; if the
key is held, it counts as down unless it is **masked until release**; if
it is up, it counts as up and its mask ends. "Just down" = down now and
not before, "just up" = the reverse.

`maskKeyUntilRelease(key)` makes the key count as up at once and until
it is let go. `Game.update` uses it for Escape when it pauses, so the
same press does not also press a button on the pause screen
(`screens.md`, part 4).

## Holding the pointer back

- `maskAllPointersDownUntilRelease`: every pointer counts as up until its
  button is let go, so a held button does nothing until it is pressed
  again. Used by the title screen's `react`.
- `maskPointerDownUntilRelease(id)`: the same for one pointer.
- `hidePointersForOneFrame`: the drawn cursor is hidden for the rest of
  this frame (the countdown is 1, and the next frame's `Input.update`
  takes it to 0). Used by the language chooser.

## The cursor

There are three kinds (`app.ent.Cursor`): `ARROW`, `HAND` and
`CUSTOM(picture)`. Each frame every pointer's cursor starts empty; the
first part to set it wins (`setCursorArrow`, `setCursorHand`, or the
cursor given to `getPointerJustDown`).

The game draws the cursor itself (`play.ui.CursorEnt`): the system's
cursor is hidden every frame. `CursorEnt` is made early by
`Game.createDefaultEnts` as a child of the tree's trunk, so it reacts
after everything else and sees the cursor the parts chose. Its picture
is on layer 100 (above everything); it sits at pointer 0's position as
given (not held inside the screen), moved by:

| Cursor | Picture | Size | Picture's top left from the pointer |
|---|---|---|---|
| arrow, or none set | `assets/CursorArrow.png` | 19 x 26 | (-1, -1) |
| hand | `assets/CursorHand.png` | 19 x 26 | (-6, -2) |
| custom | the picture given | w x h | (floor(-w/2), floor(-h/2)), centred |

It is shown only when the system wants a visible cursor (pointer 0 is the
mouse) and the pointers are not hidden for this frame
(`Input.wantVisibleCursor`). Inferred from the mode rule above, not
tested: before the mouse first moves, no cursor is drawn.

The only custom cursors are the border rifles' scopes: each
`RifleButton` loads `assets/CursorScope` + its kind + `.png`
(`CursorScopeKill.png`, `CursorScopeTranq.png`, 47 x 47) as a custom
cursor, and the border view passes the selected rifle's scope to
`getPointerJustDown` for its background picture (`Border.react`; the
field is read by its place in the class, `scopeCursor` at `+0x90`,
checked in `dump.cs`). So with sniping on and a rifle selected, the
cursor over the border picture is the scope, centred on the mouse
(top left at -24, -24), and a press there is the shot's point
(`border-shooting.md`). No other caller of `Cursor.CUSTOM` was found.

`CursorEnt` also has a touch-recording look (`CursorTouch.png`, 72 x 32,
three frames, with a drag trail on layer 99 at half alpha), read in
outline only. It is chosen by a flag, `recordingTouch`, that is false
when the cursor is made; the only code that writes it found here is
`CursorEnt`'s own set-by-name function, and the name `recordingTouch`
appears nowhere else in `decompiled/all/`. So on the desktop build the
arrow, hand and custom looks are the ones used (from the code; not
tested).

## For the port

- Read the mouse once per frame, before everything else; turn it into
  whole game pixels; keep both the held and the given position.
- Hide the browser's cursor over the game and draw the game's own, after
  every part has had its say.
- Handle input topmost part first; each part that answers blocks its
  rectangle for the rest of the frame, and the first cursor set wins.
- A take lasts until the end of the next frame and is renewed while
  held; a double click is under 0.2 s and under 2 pixels.
- Only the left mouse button counts.
- The reference model is `scripts/reference/inputs.py`; its check is
  `scripts/checks/input_check.py`.

## Not studied

- What the `phantomCursor` object shows, and whether it is visible at
  all next to the drawn cursor (above).
- Where the input mode becomes touch (mode 2), and the phone swipes.

## Things to watch in the game

None was done.

1. The cursor is the game's own, pixel-sized picture, and turns into a
   hand over things that can be clicked.
2. Before moving the mouse after the game starts, no cursor shows.
3. Two clicks on a paper under 0.2 s apart count as a double click
   (with the upgrade that uses it, `inspect-mode.md`).
4. With a rifle selected at the border, the cursor over the border is a
   47 x 47 scope centred on the mouse.
5. The right mouse button does nothing.
