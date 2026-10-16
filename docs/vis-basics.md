# Drawing, part 6: the rest of `app.vis`

Studied on 2026-10-16. `app.vis` is the game's own drawing library.
Earlier parts read the pieces the screens use most: `Text` and `Font`
(`text-drawing.md`, `fonts.md`), the picture operations of `Image`
(`fact-pictures.md`, and `Image.render` in `desk-pictures.md`), `Sprite`,
`Visual.hitRect` and `renderToImage` (`desk-pictures.md`), `Quad.make`
(`text-drawing.md`) and the atlas's sequences (`borderanim-xml-format.md`).
This part covers what was left: how a picture is held in memory and how
colours are written, the plain fill, the nine-slice frame, the atlas of
chips, the text forms of points and rectangles in the data files, the
small geometry helpers, and which parts of the library the game never
calls.

Everything here is from the code; **nothing was compared with the running
game**.

Reference script: `scripts/reference/vis.py`. Check:
`scripts/checks/vis_check.py`.

Words used here:

- **tile**: one piece of a picture drawn at one place (`app.vis.Tile`:
  the picture, the source rectangle in it, the target rectangle, a
  colour, a mirror flag); every visual turns itself into tiles
  (`buildTiles`) and the tiles become quads for the screen
  (`text-drawing.md`);
- **nine-slice**: a picture cut into a 3 x 3 grid so that it can be
  stretched to any size: the corners keep their size, the edges stretch
  one way, the middle both ways.

## What was read

In `decompiled/all/app_vis.clean.c`, in full: `Image`'s constructor and
static constructor, `get`, `getClamped`, `part`, `dirty`, `fromPng`;
`ColorData`'s constructor, `Color.fromUInt`, `toUInt`; `Tile`'s
constructor; `Fill` (all); `Frame` (constructor, `applyBorder`, the
border getters, `makeBasic`, `setInnerRect`, `setOuterRect`, `width`,
`height`, `willDraw`; `buildTiles` for its source rectangles and its
column and row edges, its nine target assignments in outline); `Atlas.
buildTiles` and its sort; `Chip`'s constructor; `Rect.parse`,
`Point.parse`, `Point.transform`, `Point.distToSeg`, `Quad.
applyPostScale`. `app.StringUtil.splitAndTrim` (in `app_misc`). The
class layouts from `dump.cs`. A search of the whole decompile for the
callers of every remaining `app.vis` function (by name; below). Two
constants read as 32-bit floats (255 and 1).

## Pictures in memory (`Image`)

- An `Image` is width x height pixels, each a 32-bit number
  **0xAARRGGBB** (alpha, red, green, blue), stored in memory as the bytes
  B, G, R, A (the numbers are little-endian). This is why the odd-shape
  click test of part 4 reads the alpha at byte 3. All colours in the docs
  (`0xFF676C54` and the like) are in this form.
- A new picture's memory is zero (all transparent black), or, with
  `Alloc.EXISTING`, an existing block of bytes is used as it is.
  `Image.fromPng` decodes a PNG with the Haxe `format.png` reader
  (`Tools.extract32`, which gives the bytes in that B, G, R, A order) and
  wraps them so.
- Each picture has a number (`guid`) and a change counter
  (`generation`); `dirty()` and every drawing operation raise the
  counter. Who reads it (inferred: the Unity side, to know when to send
  the picture to the graphics card again) was not read.
- Fixed values: `white1x1`, a 1 x 1 white picture; the `OVERLAY` paste
  threshold 128 (`fact-pictures.md`); a fixed-point shift of 8 for
  `render`.
- `get(x, y)` reads a pixel as it is (a position outside the picture's
  memory raises an error); `getClamped(x, y)` first holds x and y inside
  the picture.
- `part(x, y, w, h)` is a piece of a picture (picture plus rectangle) for
  a sprite; a part without a rectangle is the whole picture.

## Colours

A `ColorData` is four floats r, g, b, a, each normally 0 to 1; a missing
value is 1. `Color.fromUInt` divides each byte by 255; `toUInt` holds
each channel to 0..1, multiplies by 255 and cuts toward zero. The check
shows that every 0xAARRGGBB value comes back unchanged through both. A
visual's colour multiplies its tiles (`text-drawing.md`).

## A plain rectangle (`Fill`)

One tile: the `white1x1` picture stretched to the fill's size, with its
colour. It draws only when visible, wider and taller than 0, and with
alpha above 0. `setRect` puts its position at the rectangle's corner and
its size to the rectangle's. (The debug outlines of part 4 are fills.)

## The nine-slice frame (`Frame`)

A `Frame` has a picture and `scale9Rect`, the middle part of the picture
that stretches. Its borders: left = the middle's x, top = its y, right =
picture width − (x + w), bottom = picture height − (y + h).

- `setOuterRect(r)`: position and outer size are the rectangle.
- `setInnerRect(r)`: the frame is placed so that `r` is its stretched
  middle: position = (r.x − left, r.y − top), size = left + r.w + right
  by top + r.h + bottom. (The inspect mode frames marked things this
  way, `inspect-mode.md`.)
- `applyBorder(r)` grows a rectangle by the borders the same way.
- `buildTiles`: nine tiles; the source columns are 0..left, left..left+
  middle, the rest, the same for rows; the target columns are 0..left,
  left..outer width − right, the rest. So the corners keep their size and
  the middle stretches (read in full for the edges; the nine target
  assignments in outline). The colour defaults to (1, 1, 1, 1).
- It draws only when visible and larger than 0 both ways.
- `Frame.makeBasic(colour)`: a 3 x 3 picture filled with the colour whose
  middle pixel is made transparent, with the middle 1 x 1 as the stretched
  part: a one-pixel outline of any size.

## The atlas of chips (`Atlas`, `Chip`)

The border scene's figures are chips of one atlas
(`borderanim-xml-format.md`, `border-figures.md`). A `Chip` has a
position, a visible and a mirror switch, a colour, and a source picture
of the atlas with its origin. `Atlas.buildTiles`:

1. sorts the chips by y, lowest first (`Array.quicksort`; the order of
   chips at the same y was not checked), so figures lower on the screen
   are drawn later, on top;
2. makes one tile per chip that is visible and has a source: the atlas
   picture, the chip's colour, the source rectangle, mirrored if the chip
   is, at ((x − origin x) x scale, (y − origin y) x scale), the source's
   size times the scale.

On desktop the border's scale is 1 (`booth-layout.md`).

## Points and rectangles as text

The data files write points as "x y" and rectangles as "x y w h". The
game reads them with:

- **`Point.parse`**: splits on single spaces; **exactly two** parts, each
  trimmed and read as a number; otherwise the default given, or (0, 0).
  So "10  20" with two spaces is not a point.
- **`Rect.parse`**: `StringUtil.splitAndTrim` (split on spaces, each piece
  trimmed, empty pieces dropped); exactly four parts; otherwise the
  default, or (0, 0, 100, 100).

The check runs every such attribute of the data files (`pos`, `pos2`,
`visacenter`, `datepos`, `stamplinksize`, `emblemrect` in `Papers.xml`;
`size` in `Emblems.xml`; `rect` in `Bodies.xml`; `xy`, `offset`,
`randomize` in `Paths.xml`; 625 values) and finds none the rules would
refuse; the six `range` values of `Facts.xml` (which Python's XML reader
cannot open, `facts-xml-format.md`) were checked by a text search and
are two numbers too.

## Geometry helpers used by the game

Outside `app.vis` the game's own code calls only these (most other
point and rectangle helpers are written inline by the compiler, so they
do not show as calls): the `Rect` constructor, `Point.setXY`,
`Point.parse`, `Rect.parse`, `Point.transform` and `Point.distToSeg`.

- `Point.transform(p, m)`: (m00 x + m01 y + m02, m10 x + m11 y + m12).
- `Point.distToSeg(a, b, p)`: the distance from p to the segment a..b
  (the nearest point held to the segment's ends). Its one caller is the
  pointer's update, for phone swipes only (`input-handling.md`).

## What the game never calls

A search of the whole decompile by name found **no caller** in the game's
own code for: `ImageTools.pasteScale2x` and `pasteScaleMMPX` with the
`MMPX` class (a pixel-art 2x enlarger), `Color.getRainbowColor`,
`Color.lerp`, `Point.random`, `Clipper.clip2`, `Quad.applyPostScale`
(reached only by name, through `__hx_getField`), `Affine.makeTRS`; and
for the picture methods `flipH`, `flipV`, `bordered`, `getClamped`
(only by name) and `save`. `rotatedLeft90` and `rotatedRight90` are used
only by the phone's picture changer (`data.MogrifierPhone`). The static
ones cannot be reached any other way; the picture methods could in
principle be called through an unnamed method slot, which this search
cannot see. The port can leave them out.

## Random draws

None in what is called. (`Point.random` would draw, but nothing calls
it.)

## Notes for the port

- Hold pictures as 0xAARRGGBB numbers (or keep the B, G, R, A byte order
  in mind when reading pixels), and convert colours with the 255 rule
  above, cutting toward zero.
- Read points with the exact-two-parts rule and rectangles with the
  four-non-empty-parts rule; the data has no case where it matters, but
  the defaults ((0, 0) and (0, 0, 100, 100)) are what the game would use.
- Draw atlas chips sorted by y.

## Not studied

- The Unity side: how tiles, quads and the change counter reach the
  screen (`text-drawing.md`, `desk-pictures.md`).
- `Frame.buildTiles`'s nine target rectangles in full, and the inspect
  frames' own `scale9Rect` values.
- `app.vis.Affine` and `Image.transformed` were read for pictures
  (`fact-pictures.md`); the rest of `Affine` is unused or inline.

## Things to watch in the game

None was done.

1. Border figures lower on the screen are drawn over those higher up.
2. The inspect mode's frames have a fixed-size corner at any size.
