# Drawing, part 5b: the inspect mode (`InspectUi`)

Studied on 2026-10-16. The inspect mode is the booth's "highlight
discrepancies" tool: the player opens it, marks two facts (on papers or
in the booth), and the game says whether they match; when they disagree
in a way the traveler can be asked about, an **interrogate** button
appears. What asking does is in `player-actions.md`
("Interrogating"). This part covers the screen side: opening and
closing, what can be marked and how the thing under the cursor is
chosen, the two selection slots, the overlay, the label and its lines
(the "diagram"), and the interrogate button.

Everything here is from the code; **nothing was compared with the running
game**. Positions are in booth coordinates (`booth-layout.md`). On
desktop the layout has no magnifier (`useInspectMagnifier` false), no
carousel lens (phone only) and puts the hint at the bottom
(`inspectInstructionsOnTop` false).

Reference script: `scripts/reference/inspectmode.py`. Check:
`scripts/checks/inspect_check.py`.

Words used here:

- **inspectable**: something that can be marked: a fact path (such as
  `Passport/Name`), its rectangle in the booth, whether it may be
  selected, and which desk item holds it;
- **fact path**: the name of one fact, `<paper>/<fact>`
  (`facts-xml-format.md`), or a paper alone, or `Booth/...`;
- **overlay**: a dark see-through picture over the whole booth while
  the mode is open, with the marked things cut out of it.

## What was read

Read in full in `decompiled/all/play_day_booth.clean.c`: `InspectUi`
(`react`, `update`, `draw`, `set_open`, `get_open`, `disable`,
`quickInspect`, `selectInspectableAt`, `selectInspectable`,
`revalidateSelectedInspectables`, `updateOverlay`, `set_revealT`,
`set_surroundT`, `generateInitialScan`, `testHitOpenCloseButton`, the
hit-rectangle helpers, `getSelectedInspectableFactPaths`,
`getSelectedInspectableFactRelationship`, `interrogateButton_onClick`,
`onDrawRack`, `autoGetOpenButtonCenter`, the static colours, the six
state functions; the constructor for its parts and states, its exact
positions of the surround lines only in outline); `Inspectable` (all);
`Paper.getInspectables`, `getInspectable` and its sort function;
`Booth.getInspectable`, `getAllVisibleInspectables`, `getSortedPapers`
and its sort function, `deskItem_onDoubleClicked`,
`inspectUi_onOpen`, `inspectUi_onInterrogateClick`,
`inspectUi_onDenialEnabledClick`, the four booth inspectables in the
constructor's instructions, and the state function that disables the
mode; `InterrogateButton` (`react`; the constructor in outline);
`InspectUiDiagram` (`set_visibleT`, `draw`, the side choice of `set`; the
line building in outline). In `play_day.clean.c`:
`BoothEnv.getFactPathForInnerVisual`, `getTranscriptFactPath`. In
`app_misc.clean.c`: `app.Num.lerpScale`.

The constructor's instructions and the strings of `updateOverlay`, the
constructor and `InspectUiDiagram.set` are in
`decompiled/drawing5_run1.txt` (the Ghidra run of part 5a); four
constants with `read_doubles.py`.

## Opening and closing

The mode is a state machine (`app.Stater`, `border-scene.md`) with two
states, `closed` and `open`:

| State | Blend | Targets | On entering | Later |
|---|---|---|---|---|
| `closed` | 0.1 s | visible off at the end; overlay alpha to 0 over the second half; surround and reveal to 0 | diagram `off`; sound `inspect-close`; scan hidden | at the end of the blend: both selections cleared, the overlay picture cleared, the surround lines hidden |
| `open` | 0.25 s | visible on at once; overlay alpha to 1 over the first half; reveal to 1 | sound `inspect-open`; the initial scan made; the surround lines shown; the booth's `inspectUi_onOpen`, which closes the stamp bar (`IStampBar.set_open(false)`) | every frame: the surround lines and the scan (below) |

`set_open(true)` does nothing when the mode has been **disabled**. The
booth disables it when it becomes busy with the border scene (the state
function made right after the name `busy-with-border` in the `Booth`
constructor, which also closes the shutter and switches the stamp bar
off, `set_enabled(false)`); nothing
ever turns it back on, so after that the mode stays closed for the rest
of the day (the booth is made anew each day).

Ways to open or close it:

- **The button** in the booth's bottom right corner
  (`assets/InspectButtonOpen.png` when closed,
  `InspectButtonClose.png` when open, each placed with its bottom right
  at the booth's bottom right). A press on it toggles the mode.
- **Space**, with the upgrade `INSPECT_HOTKEY` (`screens.md`, part 4).
- **A double click** on a paper, with the upgrade `INSPECT_DOUBLECLICK`,
  unless the booth is in the state `intro` or `busy-with-border`
  (`Booth.deskItem_onDoubleClicked`, then `quickInspect`): if the mode is
  closed and the thing under the cursor can be selected, it opens and
  selects it; if the mode is open and the thing cannot be selected, it
  closes; otherwise nothing. Inside the open mode a double click on
  something that cannot be selected does the same `quickInspect`.
- **Interrogating** closes it (below).

### The reveal

`revealT` goes from 0 to 1 on opening (0.25 s) and back on closing
(0.1 s). With b = booth width (570), h = booth height (217) and
e = 1 − (1 − t)^2:

- the hint `HIGHLIGHT DISCREPANCIES` (`booth_highlight`, font
  `ui_regular`, colour `0xFFE0E9C7`, on `0xFF191212` with padding 5 by 1)
  is shown while t > 0, at y = h − its height and x = floor(start + t² x
  (end − start)), from start = b − the open button's width to end =
  b − its width − the open button's width: it slides in from the right
  edge, next to the buttons;
- the open button is shown while t < 1 and moves from its place to the
  booth's bottom right corner (out of sight) along e;
- the close button is shown while t > 0 and moves in from beyond the
  corner to its place along e.

### What the open mode shows

- **The overlay**: a picture the size of the booth filled with
  `kFillColor` `0x80191212` (dark, half see-through), drawn with the
  state's alpha, with the marked things' frames drawn into it (below).
- **The surround lines**: four lines (`play.ui.DiagramLine`) inset 6
  pixels around the booth's edges, in `kLineColor` `0xFFE0E9C7`; they
  grow with `surroundT`, two in the first half and two in the second.
  `surroundT` follows the time in the `open` state over 0.5 s. (Their
  exact end points were read in outline only.)
- **The initial scan**: on opening, one frame (`InspectSelectionInner`
  picture as a nine-slice frame) around every selectable thing that is
  on the booth (`getAllVisibleInspectables`); over the first 0.5 s of
  the `open` state a clip window sweeps across the booth from right to
  left (x from the booth's width to −100), showing the frames inside
  it; then they are hidden.

## What can be marked

`Booth.getInspectable(point)`, in this order; the first hit wins:

1. **Papers**, the topmost first (the booth's papers sorted by their
   place in the drawing order, last drawn first). For each paper that
   is shown and whose rectangle holds the point, `Paper.getInspectable`:
   - none if the paper has `inspectable="false"` (16 papers: money, the
     EZIC grid, holes and port papers, flyers, the poison, the love
     song, the watch, the time bomb, the spy papers, the victim photo;
     the check lists them) or hangs on the wall;
   - an **open page**: every mark under the point (`getInnerVisualsAt`,
     `desk-pictures.md`) gives a fact path
     (`BoothEnv.getFactPathForInnerVisual`): the mark's fact after its
     proxy (`papers-xml-format.md`), renamed by the day's rule table or
     the day's news remap if they have it, as `<paper>/<fact>`; the
     transcript's marks give the stored path of the spoken line they
     show (`Transcript/Speech<n>` gives the n-th path of the
     transcript's list). A mark with no fact, not inspectable or with a
     link gives the paper itself. The paper itself comes last;
   - a **closed paper**: the paper itself, with the closed picture's
     rectangle;
   - the paper itself may be selected only if it does not dock and
     `Facts.xml` has a document of that id (so the rulebook, the
     bulletin and the transcript, and papers with no fact list, cannot
     be marked as a whole);
   - of these, the one nearest the point by `compareProximity`
     (`desk-pictures.md`) is taken (a sort, so ties keep no promised
     order).
2. **The criminal poster's** things, when it is shown (phone only by the
   earlier reading, `buttons.md`).
3. **The booth's own things**: `Booth/Counter` x 9, y 120, 160 x 46;
   `Booth/Face` x 47, y 23, 80 x 80; `Booth/Clock` x 2, y 184, 30 x 31;
   `Booth/Weight` x 146, y 184, 30 x 31 (the layout's inspect
   rectangles).

`Papers.xml` has 220 marks that give a selectable fact (the check lists
them per paper).

## Selecting

While open, a press inside the booth: if the thing under it can be
selected, `selectInspectable`; else, on a double click, `quickInspect`
(above). The input under the mode is then masked for the frame, so
papers do not also react.

There are **two slots**. `selectInspectable(thing)`:

1. A thing that cannot be selected: nothing.
2. Already in a slot (same fact path): that slot is emptied; sound
   `inspect-unhighlight`.
3. Otherwise, a slot holding a parent or child of it (`Passport` and
   `Passport/Name`) is emptied first. Then it goes into the first empty
   slot; if both are full it **replaces the older of the two**. Sound
   `inspect-highlight`.

(On desktop nothing re-checks the selection when papers move:
`revalidateSelectedInspectables` is called only by the phone's lens. A
marked fact keeps its rectangle from when it was marked.)

After each change, `updateOverlay`:

- if a slot changed, the overlay is filled again and each marked thing
  gets two frames drawn into it: `InspectSelectionInner.png` (black
  replaced by transparent) pasted as it is, and
  `InspectSelectionOuter.png` blended, both as nine-slice frames around
  its rectangle;
- with **both** slots full and a pair not yet shown, the pair's text is
  chosen from the relationship (`player-actions.md`,
  `getFactRelationship`): no group with both facts: `NO CORRELATION`;
  agree: `MATCHING DATA`, or `DISCREPANCY CLEARED` when a confusion was
  cleared; disagree: `DISCREPANCY DETECTED`. The diagram is set with the
  text and the two rectangles, reset to `off` at once and started `on`;
- with fewer than two, the diagram goes `off`.

## The diagram: lines and label

States: `off` (0.25 s, visible amount to 0) and `on` (2 s, to 1). On
entering `on`: the interrogate button is enabled only if the pair
**disagrees** and the invalidating operation of the pair
(`getOpForInvalidFactPaths`) has responses for the button's id
`Interrogate` (`OpHelper.getRunOps`, `player-actions.md`); sound
`inspect-diagramon`. At 60 % of the blend (1.2 s), if enabled, the sound
`inspect-interrogateon`.

Over the 2 seconds (the visible amount taken as linear in time;
`app.Interp`'s default curve was not read):

| Time | What shows |
|---|---|
| 0 to 0.4 s | the two lines from the marked things grow to the join point |
| 0.4 to 0.8 s | the third line, from the join to the label |
| 0.8 to 1.2 s | the label blinks: shown in the second half of each third, three times, and stays on the third |
| 1.2 to 2 s | the interrogate button slides in (only if enabled) |

**Where the label goes** (`InspectUiDiagram.set`, the side choice; the
label is the text plus 4 pixels): with the gaps between the two
rectangles across and down:

1. `H` (between them, across) if the gap across is wider than the label;
2. `V` (between them, up and down) if the gap down is taller than the
   label plus 4 and their middles are further apart across than the
   label is wide;
3. otherwise a side, avoiding sides that are too close to the booth's
   edge (left or right: within the label's width + 24 of the edge; top
   or bottom: within 50): when the gap down is smaller than the gap
   across, top, then bottom, then left, then right; otherwise left, then
   right, then top, then bottom (desktop never uses the inner join).

The join point for a side is 20 pixels beyond the outer edges of the two
rectangles on that side. A side once chosen is kept unless another is
asked for more than 9 times in a row; on desktop the diagram is set once
per pair and the memory is cleared when it goes off, so in effect the
side is chosen afresh for each pair (inferred from the order of the
calls; what `Stater.go`'s "instant" option does was not read,
`screens.md`). How the curved lines are built (`buildCurvedLine`) and
where the label sits next to the join were read in outline only.

## The interrogate button

`play.day.booth.InterrogateButton` at the layout's
`interrogateButtonRect` (x 73, y 163, 33 x 49, on the console; text
centred): a frame of lines in `0xFFE0E9C7` and the text `INTERROGATE`
(`booth_interrogate`, `ui_regular`). While shown, the cursor is the hand
over it; a press calls the inspect mode's `interrogateButton_onClick`,
**at most once every 2 seconds**. The booth's
`inspectUi_onInterrogateClick` then closes the mode and asks the engine
to interrogate with the two marked fact paths (`interrogateFactPaths`,
`player-actions.md`).

While the button is shown, the booth does not finish the traveler's
visit (the booth's state function at line 501 of its constructor waits
for it to go).

`inspectUi_onDenialEnabledClick` (it would open the stamp bar,
`set_open(true)`) is wired up, but `InspectUi` itself never calls it (no
caller found by name); not studied further.

## Random draws

None.

## Preview and checks

`inspect_check.py scripts/reference extracted/art` (run 2026-10-16)
prints `problems: none`: the selectable marks per paper (220 in all) and
the 16 papers that cannot be inspected, the four booth things, the six
texts, the selection rules on hand-made cases (selecting, unselecting,
parent and child, replacing the older), the double click's four cases,
the diagram's timeline (the label appears three times and stays), and
the label side for five pairs.

## Notes for the port

- Keep the two-slot rule with "replace the older" and the parent/child
  rule; they decide which pair is judged.
- Keep the 2-second lock on the interrogate button and the "disagree and
  has `Interrogate` responses" rule for showing it.
- The mode disables itself for the rest of the day once the booth is
  busy with the border scene.

## Not studied

- The surround lines' exact end points, the curved lines' shape and the
  label's exact place next to the join; `play.ui.DiagramLine` itself.
- `app.Interp`'s default curve (taken as linear above).
- The criminal poster's inspectables (phone by the earlier reading).

## Things to watch in the game

None was done.

1. Space (with the upgrade) and the corner button open the mode with a
   dark overlay, a hint sliding in from the right and a sweep of frames
   over everything that can be marked.
2. Marking a third fact replaces the older of the two marked ones.
3. A pair that disagrees: two lines, then a third, the label blinks
   three times, then the interrogate button slides in on the console.
4. The interrogate button cannot be pressed twice within 2 seconds.
5. After an attack has started at the border, the mode cannot be opened
   again that day.
