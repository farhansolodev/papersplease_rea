# Drawing, part 4: a paper's pictures on the desk (`DeskItem`)

Studied on 2026-10-16. Every paper the player can handle (documents, the
rulebook, the bulletin, money, keys...) is a `play.day.booth.DeskItem`
made by a `play.day.booth.Paper`. This part covers the item's pictures:
which ones it has, how each is made, how they are clipped (cut to an area
of the screen), drawn, and clicked, how the mark under the cursor is
picked, how stamp ink lands on a page, and `Image.render`, the last picture
operation not yet read. Dragging, the reveal and hide animations, the
drawer's own logic and the inspect mode are **not** in this part (see
"Not studied").

Everything here is from the code; **nothing was compared with the running
game**.

Reference script: `scripts/reference/deskpics.py` (makes the pictures;
holds the clipping, picking, stamping and `Image.render` rules). Check:
`scripts/checks/desk_pictures_check.py`.

Words used here:

- **sprite**: one picture drawn on screen at a position (`app.vis.Sprite`);
- **visual**: anything drawable (a sprite, a text, a box);
- **layer**: a numbered drawing list; the item puts each visual in the
  list its `layer` number names;
- **clip rectangle**: the part of the screen a visual may show in; what
  lies outside is not drawn and cannot be clicked.

## What was read

Read in full in `decompiled/all/play_day_booth.clean.c`: the `DeskItem`
constructor and static values, `addInnerVisual`, `addFilerVisual`,
`setInnerImage`, `setOuterImage`, `setFilerImage`, `setMountImage`,
`setRackImage`, `setInnerVisualsLayer`, `set_innerShadowOffset`,
`set_placement`, `clip`, `updateClipRects`, `draw`, `width`, `height`,
`innerWidth`, `innerHeight`, `filerHeight`, `worldRect`, `autoTestHit`,
`innerCheckHit`, `confirmHitTestPointVisible`, `getInnerVisualAt`,
`getInnerVisualsAt`, `getOuterVisualAt`, `applyStampInkToInner`,
`autoRenderInnerVisualsToImage`, `autoGetSizeForPlacement`,
`autoInnerSize`; the `Paper` constructor, `setPage`, `updatePage`,
`applyStampInk`, `restoreFromStash`. In `play_day.clean.c`:
`PaperInnerVisuals.compareProximity`. In `data.clean.c`:
`PaperDef.generateRotatedOuterImage`, `getOuterImage`, `getMountImage`,
`get_isMountable`. In `app_vis.clean.c`: `ImageTools.createShadow`,
`Image.clone`, `replaceNonTransparent`, `render`; `Sprite` (constructor,
`rebuild`, `width`, `height`, `willDraw`, the setters, `bakeAffine`);
`Visual.hitRect`, `renderToImage` and the constructor. In `app_ent.clean.c`:
`SoftwareRenderer.render` and `renderFromQuadIter`. Read in part: the
lines of `DeskItem.updateCustomDrag`, `endCustomDrag`, `update` and
`animateReveal` that show or hide the shadow and the give icon; the
`Booth` constructor's instructions (`decompiled/booth_ctor_asm.txt`) where
it makes the carousel.

One read-only Ghidra run (`decompiled/drawing4_run1.txt`):
`DumpAssembly.java` on `updateClipRects` (two clip rectangles the
decompiler dropped), `generateRotatedOuterImage` (the scale it passes) and
`compareProximity`; `ListStringUses.java` on the `Paper` constructor (the
envelope picture's name). Twenty constants with `read_doubles.py`: 10, 4,
20, 0.75, 60, 30, 180, 0.5, 1, 15, 2, 2, −1, −1, 0.001, 0.01, 0.24, −4,
0.25, 0.1 (the last four belong to the phone's carousel and are not used
below).

## A desktop booth has no carousel

The `Booth` constructor makes a `Carousel` (the phone's tray of papers)
only when the layout's shape is `PORTRAIT_THIN`: the instructions compare
`Layout.shape` (offset `0x260`) with `Shape.PORTRAIT_THIN` at `0x1801bb321`
and jump to the only call of the `Carousel` constructor, and the only
write of `Booth.carousel` is in that branch. Desktop's shape is
`LANDSCAPE` (`border-view.md`, "The layout values"). So **on desktop every
paper's `carousel` is empty**, and so is everything below that needs one
(the rack picture, the carousel's clip, the inner shadow's carousel
switch). This settles the open question of `buttons.md` and `screens.md`
part 11 about whether a desktop booth has a carousel: it does not, and
its stamp bar is the plain `StampBar`.

## The pictures of a paper

A `DeskItem` holds these sprites, in this order (the order they are drawn
within a layer):

| Sprite | Picture | Layer | Shown when |
|---|---|---|---|
| inner shadow | the page in black, drawn at half opacity, 4 right and 4 down | 0 | the page is being dragged on the desk and has moved |
| inner | the open page (`Paper.setPage`) | 0 | the paper is open on the desk (placement `INNER`) |
| outer | the closed paper | 0 | the paper is closed on the counter (placement `OUTER`) |
| filer | the paper in the drawer | `layerFiler` (1) | in the drawer (placement `FILER`) |
| give icon | `assets/GiveIcon.png` (57 x 13) | 0 | while dragging, over the give area (the rule is in the drag code, not read here) |
| mount (only papers with `mount`) | the paper on the wall | `layerMountedDeskItem` (−2) | on the wall (placement `MOUNT`) |

The item also keeps two lists: the **inner visuals** (the page's texts,
pictures and seals from `PaperInnerVisuals`, `page-layout.md`) and the
**filer visuals** (the drawer's extra pieces), and one more sprite, the
**stamp ink layer**, made when ink first lands (below).

The four placements are an enum: `OUTER`, `INNER`, `FILER`, `MOUNT`.
Setting the placement shows the matching sprite and hides the other
three, the inner shadow and the give icon. Without a drawer (`filer`
empty), `FILER` becomes `INNER`. The item's width and height are those of
the shown sprite.

The layer numbers are the same in all three layouts (`Layout`
constructor, before the blocks): wall −3, mounted paper −2, shutter
shadow −1, stamp desk 2, filer 1; a visual nobody sets is on layer 0.
How the drawer orders its layers was not read (**inferred**: lower
numbers first, which would put the wall behind the hung papers).

### The closed paper (outer)

Made in the `Paper` constructor (and again when a stash is restored),
with `PaperDef.generateRotatedOuterImage(res, angle)`:

1. **The tilt.** If the paper's `rotate` is true (all but `TimeBomb`), one
   draw of the booth's generator `r` (0 ≤ r < 1) gives the angle
   (r × 60 − 30) × π / 180: **from −30° up to (not including) +30°**,
   in radians. `rotate="false"` gives 0 and makes no draw. This is the
   "tilt" draw of `desk-drawing-draws.md`.
2. If the paper has `dock="true"` (`Rules`, `Bulletin`, `Transcript`) or a
   `mount` picture (5 papers), the closed picture is
   `assets/papers/<outer>` **as it is**: no turn, no halving, no shadow.
   The angle is still drawn.
3. Otherwise (60 papers):
   - the picture is turned by the angle and **scaled by 0.5**
     (`Image.transformed`, `fact-pictures.md`; the 0.5 was checked in the
     instructions);
   - its shadow is a copy with every pixel that is not fully transparent
     set to `0xFF676C54` (`ImageTools.createShadow`: `clone`, then
     `replaceNonTransparent`, which writes the colour over any pixel whose
     alpha is not 0, alpha included);
   - the result is a new transparent picture of width (w + 1) / 2 × 2 and
     height (h + 2) / 2 × 2 (whole-number division: the width rounded up
     to even, the height plus one rounded up to even);
   - the shadow is pasted at (−1, 2) and the turned picture at (0, 0),
     both with `OVERLAY` (pixels with alpha ≥ 128 copied as they are,
     `fact-pictures.md`).

   So the closed paper shows its outline one pixel left and two down in
   a grey-green, cut by one column on the left and, when the turned
   height is odd, by one row at the bottom.

Sizes for every paper are printed by the check: an entry permit
(100 x 50) is 50 x 26 untilted and up to 56 x 48; a passport (60 x 80)
30 x 42, up to 46 x 52.

The **give icon** is placed when the closed picture is set: x = floor
(closed width × 0.5 − icon width × 0.5) as a whole number, y = −icon
height. So it sits centred above the closed paper, touching its top
edge. On a passport (30 wide when untilted) that is x −14.

### The open page (inner)

`Paper.setPage(index)` (`page-layout.md` describes the page itself):

- the index is held between 0 and the last page, then moved forward to
  the first page the paper has (`PaperNav.hasPage`);
- the **page stack** (for the `#back` link) is reset to [0] on page 0;
  otherwise the page is pushed, or, if it is already in the stack,
  everything after it is dropped;
- a new `PaperInnerVisuals` lays the page out; the item gets its picture
  with `setInnerImage(picture, oddshape)` and then each visual in order
  with `addInnerVisual`.

`setInnerImage`:

- the inner size becomes the picture's size; for the drawer envelope
  (`ONLYFILER`) the drawer size too;
- the inner shadow becomes the picture in black (`createShadow`,
  `0xFF000000`); the shadow sprite's colour has alpha 0.5, so it is drawn
  at half opacity;
- **the list of inner visuals is emptied** (the old page's visuals go);
- the inner sprite gets the picture;
- without a carousel (desktop), the inner sprite gets a clip rectangle
  if it had none, and the clips are updated (below).

`addInnerVisual(visual)` **sets the visual's clip rectangle to the inner
sprite's** (the same object, so the visual is cut wherever the page is)
and adds it to the list. This replaces any clip the page gave it: the
only such clip in the game is the `Citation`'s message
(`clipheight="36"`, `page-layout.md`), so **on the desk that clip has no
effect** by the code. Whether a citation message is ever taller than 36
pixels was not checked. Not seen in the game.

The stamp ink layer is **not** touched by `setPage`, so ink would stay
when a page is turned. Every stampable paper has one page (the check), so
this does not arise.

### The drawer (filer)

Only papers with `canconfiscate="true"` (the seven passports) and the
drawer envelope itself have a drawer picture, and a passport only when
the booth has a drawer and `canPutInFiler` allows it
(`papers-on-desk.md`); otherwise its drawer type is `NONE`.

- **A confiscatable paper**: the drawer sprite is
  `assets/papers/FilerEnvelopeOpen.png` (175 x 80). Two filer visuals go
  on top of it:
  - a strip of the paper's closed picture (the original, unturned):
    the rectangle x = max(10, width − 30), y = 1, 30 wide, min(height,
    envelope height − 2) high, copied (`Image.copy`) and placed at
    (envelope width − 31, 1). For a passport: x 30, 30 x 78, at (144, 1);
  - the label: a text in the font `small_tight`, colour `0xFF303030`,
    line spacing 0, several lines allowed, saying the paper's drawer name
    (`papers-on-desk.md`, `getPaperNameInFiler`), at x 13, y = cap height
    − ascent + 2 of that font.
- **The drawer envelope** (`FilerEnvelope`, `ONLYFILER`): its page is laid
  out as for the desk, and its picture and visuals become the drawer
  picture and filer visuals.

Filer visuals are put on `layerFiler` and share the drawer sprite's clip
rectangle.

### The wall (mount)

Papers with `mount`: `PlaqueOne`, `PlaqueTwo`, `FamilyPhoto`,
`SonDrawing`, `Arskickers`. The mount sprite is
`assets/papers/<mount>` as it is, on `layerMountedDeskItem`.

### The rack (phone only)

With a carousel the constructor also makes a rack picture: the closed
picture (halved unless it docks or hangs), on a copy of itself in
translucent black (`0x80000000`) two pixels to the left. Desktop has no
carousel, so no rack picture.

## Clipping

`DeskItem.clip(visual, bounds)`: the visual's rectangle (its position
plus the item's position, its width and height), cut to `bounds`, then
moved back into the item's own coordinates. A clip rectangle is always in
the same coordinates as the visual's position (`Visual.hitRect` and
`Quad.make` cut the visual's own rectangle to it directly).

`updateClipRects`, without a carousel (desktop):

| Sprite | Cut to |
|---|---|
| inner, and the inner shadow when it has a picture | `Layout.boothInnerClip` |
| filer | `Layout.boothInnerClip` |
| mount | `Layout.wall` |
| outer | depends on the state, below |

For the outer sprite, its y is first set to 0, then by the item's state:

- **revealing or hiding** (coming out of or going back into the slot): the
  clip is (0, max(0, slot centre y − item y), closed width, closed
  height), so nothing above the slot's middle shows;
- **giving** (handed back to the traveler): (0, 0, closed width,
  max(0, min(closed height, counter top edge y − item y))), so nothing
  below the counter's top edge shows;
- otherwise: cut by `clip` to the dock point's clip rectangle if the item
  has a dock point with one, else to `Layout.boothOuter`.

The desktop values of `boothInnerClip`, `boothOuter`, `wall`,
`slotCenter` and `counterTopEdgeY` were **not read**: the `Layout`
constructor computes them from other values, and reading them from the
instructions is a job of its own.

Visuals added later share the clip rectangle object of their sprite, so
they follow it when it is updated.

## Drawing on screen

`DeskItem.draw(drawer)`:

1. Nothing if the item is hidden, or if its rectangle (below) lies wholly
   outside `Layout.booth`.
2. For each sprite in the order of the table above: if it will draw
   (visible, has a picture, colour alpha above 0: `Sprite.willDraw`) and
   is visible, its host position becomes the item's position in the
   world, it lays out its tiles, and it is added to its layer's list.
3. If the placement is `INNER`: the same for each inner visual in order,
   then the stamp ink layer.
4. Else if the placement is `FILER`: the same for each filer visual.
5. A debug outline of the item's rectangle when the debug switch
   `showDesktopItemHitRects` is on (not in normal play).

So on the desk the page picture is drawn first, then its texts, pictures
and seals in mark order, then the ink. How the layers' quads reach the
screen is the Unity side (not read; `text-drawing.md`).

**The item's rectangle** (`worldRect`): the shown sprite's hit rectangle
(clipped), moved by the item's world position; for `OUTER` with a dock
point that has a clip, the sprite's unclipped rectangle instead. Width
and height for layout use are the shown sprite's (`width`, `height`).

## Clicking

- **On the item** (`autoTestHit`, `innerCheckHit`): the point must be in
  the item's rectangle (left and top edges in, right and bottom out),
  and then pass the **odd-shape test** (`confirmHitTestPointVisible`):
  for a paper with `oddshape="true"` whose page is shown, the page
  picture's pixel under the point (positions cut toward zero) must have
  alpha **above 8**; outside the picture fails. Other papers pass.
  `innerCheckHit` also needs the placement to be `INNER`.
- The check counts, per page picture, the pixels the test refuses: for
  example 5,985 of the `Arskickers` poster's, 152 of each token's (taken
  from the files, before the marker pixels are painted over). The
  `Poison` paper's first two pages have none, so on them the test changes
  nothing.
- **On the closed paper** (`getOuterVisualAt`): the outer sprite's
  rectangle, widened by `touchTargetExpand` (0 on desktop).

## Picking the mark under the cursor

`DeskItem.getInnerVisualAt(point)` (used by the inspect mode and links,
not read here):

1. Nothing when the placement is `MOUNT` or the page is hidden.
2. The point is moved into the item's coordinates. It must be inside the
   page sprite's hit rectangle (clipped), widened by `touchTargetExpand`.
3. Each visible inner visual whose hit rectangle (clipped) holds the
   point is a candidate, in order. The first becomes the pick. A later
   one replaces the pick unless `compareProximity(point, new, pick)` is
   positive; so on a tie (0) the later one wins.
4. No candidate: the page itself.

`getInnerVisualsAt(point)` lists every visible inner visual whose hit
rectangle holds the point, **last added first**, then the page sprite.
Without a point: all visible inner visuals in order, then the page.

### `compareProximity(p, a, b)`

Negative: `a` is the better pick; positive: `b`; 0: no preference.

1. The same rectangle: 0.
2. One inside the other (edges may touch): the inner one wins.
3. **The same height** (difference below 1) **and a shared left or right
   edge** (difference below 1): take the vertical distance from p to
   each one's middle line, floor(y + h × 0.5) as a whole number. If `a`
   is at least 15 wide and `b` narrower, `b` wins when its distance × 0.75
   is less than `a`'s. If `a` is narrower than 15 and `b` at least 15,
   `a` wins when its distance × 0.75 is less than `b`'s. Otherwise go on.
4. Shrink both by one pixel on each side (x + 1, y + 1, w − 2, h − 2) up
   to five times. After each shrink: if only one still holds p, it wins;
   if neither does, stop; if both do, shrink again.
5. The rectangle nearer to p wins (squared distance, 0 inside; the
   original rectangles).
6. The one whose middle (floor(x + w × 0.5), floor(y + h × 0.5)) is
   nearer wins, the distance being floor(|dx|) + floor(|dy|).
7. Otherwise 0.

The x and y shrink amounts are −1 and the w and h ones 2 (constants
`0x180a80b20` to `0x180a80b38`); the decompiler shows `b`'s height shrink
taken from the width constant, which is also 2, so the result is the
same. The check found the function symmetric (swapping `a` and `b` swaps
the answer) on 20,000 random pairs.

## Stamp ink

`Paper.applyStampInk(ink picture, position)` passes on only for papers
with `fromtraveler` and `stampable` (the passports, `VisaSlip`,
`SeizureSlip`, `Pezpert`, `SecondPassport`). `DeskItem.applyStampInkToInner`:

1. Nothing unless the page is shown and the ink's rectangle overlaps the
   page's (touching edges do not count).
2. The first time: an **ink layer**, a transparent picture the size of
   the page, as a sprite with colour (1, 1, 1, 1), the page's clip
   rectangle and the page's layer.
3. The ink is pasted into the ink layer at its position in the item's
   coordinates (cut toward zero), mode `OVERLAY`: ink pixels with alpha
   ≥ 128 are copied as they are, the others leave the layer as it was.

The ink is drawn after the page's visuals (above). The ink layer keeps
the size of the page that was shown when the first ink landed.

## `Image.render`: a stretched tile into a picture

Called through slot 31 by `Visual.renderToImage` (for a tile whose size
differs from its piece's by 0.01 or more, `text-drawing.md`) and by
`SoftwareRenderer` (made only by the test player's code in `test.*`, so
**inferred** not used in normal play).

`render(quad, paste mode, clip width, clip height)`:

- the defaults: mode `BLEND`, clip width and height the picture's size;
- the target rectangle is the quad's corners floored; nothing if it lies
  outside (0, 0, clip width, clip height);
- the source rectangle is the quad's picture coordinates (0 to 1) times
  the source's size, plus 0.001, floored;
- a target edge past 0 or the clip size is moved in, and the source edge
  moved in proportion (whole-number division, cut toward zero);
- each target pixel takes the source pixel ((x − x0) × source width /
  target width + source x0, cut toward zero; the same for y): nearest
  pixel, no smoothing;
- the pixel is tinted by the quad's colour (each channel times the
  colour's / 255, whole numbers) and written as `Image.paste` writes in
  that mode: `REPLACE` as it is, `OVERLAY` if its alpha ≥ 128, `BLEND`
  mixed with alpha = max(target, source) (`fact-pictures.md`).

`deskpics.render_quad` follows this. `autoRenderInnerVisualsToImage`
(the page and its visuals drawn into one picture with `renderToImage`)
is used only by the test player (`test.auto.AutoEnv`).

## Random draws

Only the tilt, one draw per paper with `rotate` true, made in the `Paper`
constructor before the first page is drawn (`desk-drawing-draws.md`). A
restored stash reuses the saved angle. Nothing else in this part draws.

## Preview and checks

`desk_pictures_check.py scripts/reference extracted/art` (run 2026-10-16)
prints `problems: none`. It lists, for every paper, how the closed
picture is made (59 tilted and halved, 1 halved only, 3 as they are for
the dock, 5 as they are for the wall), its size untilted and the largest
over the tilt range, and the wall pictures; the envelope (175 x 80) and
give icon (57 x 13), and each passport's drawer strip; the pixels the
odd-shape test refuses on every page of the odd-shaped papers; the
stampable papers (all one page); the one `clipheight`; and
`compareProximity`'s symmetry and three hand-made cases.

Previews (`deskpics.py extracted/art extracted/previews/deskpics`),
looked at: the entry permit closed at −30°, 0° and +30°, passports, an
id card, the time bomb (halved, not turned), the rulebook (as it is), a
wall plaque, a passport in the drawer envelope, an entry permit's drag
shadow.

## Notes for the port

- Make the closed pictures as above (turn, halve, nearest pixel, the
  grey-green shadow at (−1, 2), the even sizes) and keep the tilt draw in
  the booth's sequence even for docked and hung papers.
- Keep the odd-shape test's alpha-above-8 rule, the clip sharing (a page's
  visuals are cut where the page is), and `compareProximity` as written:
  it decides which fact the inspect mode picks.
- Whether to keep the `Citation`'s lost 36-pixel clip is a design
  question (the code loses it; not seen).

## Not studied

- The desktop values of the layout rectangles used here (`booth`,
  `boothInnerClip`, `boothOuter`, `wall`, `slotCenter`,
  `counterTopEdgeY`): computed in the `Layout` constructor, not read.
- How the drawer orders its layers, and how the quads reach the screen
  (the Unity side).
- Where the item is and how it moves: dragging (`startCustomDrag`,
  `updateCustomDrag`, `endCustomDrag`, `clampPlacementPos`), the reveal
  and hide animations and their timings (`startRevealAnim`,
  `animateReveal`, `animateHide`; the static times 1, 3, 3, 0.5 s), the
  drawer (`Filer`), the dock points, the give area and the give icon's
  rule, depth order (`moveDepthToTop`).
- The inspect mode (`Paper.getInspectables`, `getInspectable`, the booth's
  inspect code), which uses the picking above.
- The reveal chosen in the `Paper` constructor (`ONWALL` for a hung paper
  with a saved wall place, `ONDESK` for some others).

## Things to watch in the game

None was done.

1. A closed document on the counter: about half the size of its open
   page's outer art, tilted up to 30° either way, with a grey-green
   outline one pixel left and two down.
2. The rulebook, bulletin and transcript closed: not tilted, full size.
3. A confiscated passport in the drawer: the envelope with the right
   30 pixels of the passport's cover at its right edge, and the label.
4. Dragging an open page: a black shadow at half opacity, 4 pixels right
   and down, only while it moves.
5. A click on a transparent part of a token or the Arskickers poster
   goes to what lies under it.
6. A long citation message, if one exists: not cut at 36 pixels.
