# How the game's drawing reaches the screen (the Unity side)

Studied on 2026-10-17. This is the last part of the drawing step: what
happens after the game's parts have handed their pictures to the drawer.
It covers the order in which everything is drawn, how the Unity host
turns the game's rectangles into graphics-card work, the one picture
the whole game is drawn onto, how that picture is fitted to the window,
how pictures are sent to the graphics card and re-sent when they change,
and the host's second cursor (`phantomCursor`).

Everything here is from the code; **nothing was compared with the running
game**. Several things that matter are not in the code at all but in the
Unity scene and shader files (`level0`, `sharedassets0.assets`); they
are listed under "Not in the code" with what the port should assume.

Words used here:

- **quad**: one rectangle to draw, with a picture, the piece of that
  picture to show (its texture coordinates, 0 to 1), and a colour.
  Every text letter, sprite and box ends up as quads (`text-drawing.md`).
- **layer**: a number each visual carries; lower layers are drawn first,
  so higher ones cover them.
- **texture**: a copy of a picture in the graphics card's memory.
- **render target**: a picture in the graphics card's memory that is
  drawn into instead of the window.
- **mesh, submesh**: Unity's names for a batch of rectangles sent to the
  graphics card together, and a slice of that batch drawn with one
  texture.

## What was read

- In `decompiled/all/top.clean.c`: `HostUnity` (all 12 of its own
  functions: `Start`, `CreateGame`, `Update`, the constructor,
  `applyDesktopScreenResolution`, `applyFrameSync`,
  `convertImageToTexture`, `detectPlatformKind`, `findResolution`,
  `getDeviceIsIpad`, `getTexture`, `setStretchFill`), `HostUnity.Monitor`
  (the constructor), `HostUnity.TextureStats.Clear`; `QuadBatcher` (4),
  `QuadBatcher.QuadMesh` (5) and `QuadMesh.Submesh` (2), all of them; the
  `IGame` functions of `Game`: `draw`, `width`, `height`,
  `subpixelCount`, `phantomCursorImage`, `deviceTestMaskImage`,
  `wantSoak`, `wantPlatformKind`.
- In `decompiled/all/app_ent.clean.c`: `Drawer` (constructor, `add`,
  `addMultiple`, `getLayer`, `reset`), `Layer` (constructor, `reset`),
  `VisualIter` (`begin` with its sort function, `hasNext`, `next`),
  `QuadIter` (constructor, `begin`, `hasNext`, `next`), and
  `GroupEnt.draw` (the other caller of `getLayer`).
- In `decompiled/all/app_misc.clean.c`: `PagedArray<Visual>` (`get`,
  `push`, `reset`) and `Iter<Visual>` (`init`, `hasNext`, `next`).
- In `decompiled/all/app_vis.clean.c`: `Quad.make` again
  (`text-drawing.md` read it first), for the texture coordinates.
- `dump.cs`: the fields of `HostUnity`, `HostUnity.Monitor`, `Quad`,
  `Layout`'s static fields, and the `IGame` interface's slot order
  (0 `update`, 1 `draw`, 2 `width`, 3 `height`, 4 `subpixelCount`,
  5 `phantomCursorImage`, 6 `deviceTestMaskImage`, 7 `wantSoak`,
  8 `wantPlatformKind`), which is how the host's calls through the
  interface were named.
- Constants with `read_doubles.py`: 0.5 (single precision), 1.0, 0.5,
  and the projection's near and far planes, −1 and 1.
- A search for names in the Unity files (`strings` on `level0`,
  `sharedassets0.assets`, `globalgamemanagers`,
  `globalgamemanagers.assets`; see "Not in the code").
- The pictures `CursorPhantom.png` and `CursorArrow.png`, compared pixel
  by pixel (`host_check.py`).

## One frame, the drawing half

`HostUnity.Update` runs once per frame. Its first half (the frame rate,
the keys and pointers, the game's `update`) is in `border-view.md`
("The frame rate") and `input-handling.md` ("One frame"). After the
game's `update` it does this, in order:

1. **Textures not used for a while are thrown away** (below, "Pictures
   on the graphics card").
2. It points a command list at the render target (the game's screen
   picture), clears it to **opaque black**, sets the view to "none" and
   the projection to an orthographic one from (0, 0) at the top left to
   (570, 320) at the bottom right, in game pixels, near −1, far 1
   (`Matrix4x4.Ortho(0, w, h, 0, -1, 1)`, passed through
   `GL.GetGPUProjectionMatrix(…, true)`, Unity's correction for drawing
   into a texture rather than the window). So the quads' corners, which
   are in game pixels, are used as they are.
3. It calls the game's `draw`, which returns the quad walker, and goes
   through every quad in order. A quad marked not valid is skipped
   (`Quad.make` marks a quad not valid when its colour's alpha is below
   0.001 or the clip rectangle leaves nothing of it; `QuadIter` gives a
   not-valid quad for a visual with no tiles). For each valid quad it
   gets the texture of the quad's picture (asking only when the picture
   differs from the previous quad's) and adds the quad to the batcher.
4. The batcher sends everything to the graphics card in the same order
   (below), the command list is run and emptied.
5. Then the end-of-frame checks: quit if the game asked to; if the game
   wants a "soak" run, the game is replaced by a test player with the
   default plan (`test.auto.AutoGame`; test tooling,
   `test-tooling-files.md`); if the game wants another platform kind,
   the game is made again for it (phones and tablets only by the
   reading of `screens.md`, part 11).

## The drawing order

The game's `draw` (`Game.draw`) empties the drawer, lets the screen's
tree of parts draw itself into it (the trunk's `draw`), then the screen
flash and fade cover (`ScreenFlash.draw`, `screens.md`, part 11), and
hands the drawer to the quad walker. So the whole order is:

1. **Layers, lowest number first.** `VisualIter.begin` collects the
   layers in use and sorts them by number, ascending (its sort function
   returns a − b; an empty slot counts as 1,000,000,000 and so sorts
   last). Layer numbers are unique within a frame (the drawer keeps one
   layer per number), so the sort has no ties. This confirms what
   `desk-pictures.md` and `PROGRESS.md` had inferred ("lower numbers
   first").
2. **Inside a layer, in the order the visuals were added.** A layer
   holds its visuals in a paged list that keeps them in the order they
   were pushed, and the walker reads it from the start. A visual is
   added when its owner draws (`Drawer.add`, `addMultiple`,
   `GroupEnt.draw`), so inside one layer the order is the order in which
   the parts of the screen drew, which is the tree's order (a parent,
   then its children; `screens.md`, part 1). The screen flash is added
   last of all, but it is drawn by its layer like everything else.
3. **Inside a visual, tile by tile**, as `text-drawing.md` describes
   (a text's background first, then its letters).
4. **The host keeps that order exactly.** The batcher never reorders:
   quads go into meshes and submeshes in the order they come, and the
   meshes and submeshes are drawn in that order (below). Pictures are
   not grouped by texture across the list, so a quad drawn later always
   covers one drawn earlier.

A visual that is not visible is not added (`Drawer.add` checks
`visible`, unless the caller forces it). Every layer in use has at least
one visual: the only callers of `getLayer` push a visual straight after.
(This matters because `VisualIter.hasNext`, at the end of a layer, only
looks at whether the next layer has a visual; it would stop early at an
empty layer, but there are none.)

## The screen picture and the window

- **The game is drawn onto one picture**, a render target of
  `width × subpixelCount` by `height × subpixelCount` pixels. On desktop
  that is **570 × 320** (`Layout.kPixelWidth`, `kPixelHeight`, and
  `subpixelCount` 1, `booth-layout.md`). It is made in `CreateGame`:
  no depth buffer, colour format `BGRA32`, `sRGB` read/write, **nearest
  pixel** filtering (`FilterMode.Point`).
- That picture is shown on the **screen quad** (`screenQuad`), a Unity
  object in the scene, sized 570 / PPU by 320 / PPU in Unity units (PPU,
  "pixels per unit", is a setting of the scene's camera, not in the
  code).
- The scene's camera has Unity's **Pixel Perfect Camera** component
  (`PixelPerfectCamera`, from Unity's 2D Pixel Perfect package). The
  host sets its reference resolution to 570 × 320. Its other three
  switches decide how the picture is fitted to the window:
  - **Windowed desktop** (`applyDesktopScreenResolution`, called at the
    start and whenever full screen is switched on or off): the window is
    made `570 × 320` doubled as often as the doubled size stays under
    two thirds of the monitor in both directions (the test is
    `monitor × 2 / 3 ≤ size × 2`, whole-number division, which stops the
    doubling). On a 1920 × 1080 monitor that is **1140 × 640**; on
    2560 × 1440, 1140 × 640 too; on 3840 × 2160, 2280 × 1280; on a
    monitor at most 1711 pixels wide or at most 961 high (1366 × 768,
    1600 × 900, 1680 × 1050), 570 × 320 itself (that first size is
    never checked against the monitor). Then **crop X, crop Y and
    stretch fill are all on**.
  - **Full screen**: the screen is set to the monitor's own resolution
    (the last entry of Unity's list of resolutions, `Monitor`) at a
    preferred 60 Hz, or to 1920 × 1080 with the command-line word
    `1080p`, or 1280 × 720 with `720p` (each picked at about
    60 Hz when the list has it, otherwise at any rate; when the list has
    no such size at all, the monitor's own resolution is kept). Crop X,
    crop Y and stretch fill take the value of the command-line word
    `stretch`: **off by default**. (`run-and-seeds.md` lists the
    command-line words.)
  - On phones and tablets all three are on.
  What these switches do is the package's own behaviour, not the
  game's. By the package's documentation (not this game's code, not
  tested): with crop on, the picture is drawn at a whole-number zoom and
  the rest of the window is black bars; stretch fill then scales that to
  fill the window as far as the shape allows, so the zoom need not be a
  whole number; with crop off, the camera keeps a whole-number zoom and
  shows more of the scene around the screen quad. In a windowed game
  the window is an exact multiple of 570 × 320, so every choice gives
  the same whole-number zoom there.
- On desktop the host also sets `maxQueuedFrames` to 1 (the graphics
  driver may work at most one frame ahead).
- The mouse is mapped back through the screen quad, which is why the
  game sees whole game pixels wherever the window is
  (`input-handling.md`, "The mouse").

## How the quads are batched (`QuadBatcher`)

- A **mesh** holds up to **1024 quads** (4096 corners, 6144 corner
  numbers). Each quad is two triangles: corners (0, 1, 3) and (1, 2, 3),
  where corner 0 is the top left (`px`, `py`), 1 the top right (`pr`,
  `py`), 2 the bottom right (`pr`, `pb`) and 3 the bottom left (`px`,
  `pb`). Each corner carries its position (z 0), the quad's colour as
  four floats (r, g, b, a exactly as the game gave them), and its
  texture coordinates.
- A mesh has **32 submesh slots**. A submesh is a run of quads that
  share a texture. When a quad's texture differs from the current
  submesh's, the next slot is opened; when the 32 slots or the 1024
  quads are used up, the next mesh is started (meshes are made on
  demand and kept).
- Quirk: after a mesh is emptied, its first slot has no texture, and the
  first quad's texture always differs from "none", so **slot 0 always
  stays empty** and a mesh holds at most 31 texture changes. Slot 0 is
  still drawn, with no quads. No visible effect.
- At the end of the frame each mesh in use, in order, gets its corners
  and its submesh list uploaded and each submesh is drawn in order with
  the host's quad material (made from the scene's `quadShader`) and the
  submesh's texture (`_MainTex`). Then every slot is emptied.
- Inferred, not checked: a frame with no valid quad at all would make
  the batcher look at slot −1 and fail. Every screen draws something
  (at least its background), so it is not expected to happen.

## Texture coordinates and the picture's rows

`Quad.make` divides the piece's pixel rectangle by the picture's size,
with y counting **down** from the picture's top row
(`text-drawing.md`). The host copies the picture's bytes into the
texture as they are (`Texture2D.SetPixelData`), first row first; Unity
counts texture rows from the bottom, so the picture's top row is the
texture's row at v = 0, which is exactly where the quad's v = 0 reads.
So nothing is turned over, and the y-down projection above puts the
game's top row at the top of the screen picture.

## Pictures on the graphics card (`getTexture`)

- Each game picture becomes one texture, kept in a table under the
  picture's number (`guid`, `vis-basics.md`). A texture is made with the
  picture's size, format `BGRA32` (the same byte order the game keeps
  its pixels in: B, G, R, A), no mipmaps, sRGB, **nearest pixel**
  filtering and **clamped** edges (`TextureWrapMode.Clamp`: reading past
  an edge repeats the edge pixel).
- **The change counter is read here.** The table remembers the
  picture's change counter (`generation`) when it last sent it. When a
  quad uses the picture and the counter differs, **the whole picture is
  sent again** (`SetPixelData` and `Apply`). So a picture the game
  draws into (a stamped page, the newspaper, a family picture) shows
  its new content from the next time it is drawn. This answers
  `vis-basics.md`'s "who reads it": the host, as inferred there.
- The table also remembers the last frame each texture was used. Each
  frame, before drawing, a texture **not used for more than 10 frames**
  is destroyed and its entry removed; it is made again on its next use.
  No visible effect, only work.
- When the game is made again (`CreateGame`), all textures are
  destroyed.
- `TextureStats` counts textures added, updated and removed each frame;
  nothing in the game reads the counts.

## Where a fractional position lands

The game's quads are not rounded to whole pixels (`text-drawing.md`,
`buttons.md`), and the host does not round them either: they go to the
graphics card as single-precision floats in game pixels, drawn into the
570 × 320 screen picture with nearest-pixel texture reads. **The game
code ends there**; which pixels a quad covers is decided by the
graphics card. By the usual rule of Direct3D 11 and OpenGL (general
graphics-card behaviour, not read in this game, not tested): a pixel is
drawn when its centre (x + 0.5, y + 0.5) is inside the quad, with ties
on the left and top edges counted in and ties on the right and bottom
edges counted out; its colour is read from the texture at the point the
pixel's centre maps to, rounded down to a texel. For a quad that is not
scaled, that makes the picture land at its position rounded to the
nearest whole pixel, a half rounding **down** (a quad starting at 10.3
or 10.5 starts at pixel 10, one at 10.7 at pixel 11). The reference script
`host.py` has this rule as `covered_pixels` and `texel_at`, marked as
an assumption.

How the colour is applied there, and how a see-through pixel mixes with
what is under it, is in the quad shader, not the code (below).

## The host's second cursor (`phantomCursor`)

This answers the open item of `input-handling.md`.

- **What it shows**: `CreateGame` calls the game's
  `phantomCursorImage` (interface slot 5), which returns
  `assets/CursorPhantom.png`, turns it into a texture (as above) and
  puts it on the `phantomCursor` object's material. The object's size
  is set so one picture pixel is one game pixel (19 × 26).
- **The picture**: `CursorPhantom.png` is exactly the **white edge of
  the arrow cursor**: its 39 opaque pixels, all grey-green
  (85, 104, 85), are at the same places as the 39 white pixels of
  `CursorArrow.png`; everything else is transparent (`host_check.py`).
- **Where it sits**: each frame, while pointer 0 is from the mouse, the
  host places it so that its top left corner is at game pixel
  (x − 1, y − 1), where (x, y) is the mouse in whole game pixels, and
  sets its z to 1. (The host places the object's centre at
  (x − 1 + 19 / 2, y − 1 + 26 / 2), going through the screen quad's
  coordinates; "top left at (x − 1, y − 1)" assumes the object's mesh is
  centred on it, as Unity's stock quad is: inferred.) That is the same
  place as the drawn arrow
  (`input-handling.md`: the arrow's top left is at (−1, −1) from the
  pointer). So, if it is visible, it lies exactly on the white edge of
  the game's own arrow. It follows the mouse position of the current
  frame, the same one the game uses. When the pointer is not from the
  mouse its renderer is switched off.
- **Whether it is visible** is not in the code: it depends on the
  scene (its depth against the screen quad, the camera) and on its
  shader (`Unlit/PhantomCursorShader`, material `PhantomCursorMat`;
  both names are in `sharedassets0.assets`, the object's name
  "Phantom Cursor" is in `level0`). Not settled. If it is visible, over
  the hand or the rifle's scope cursor it would show as an arrow
  outline next to them; a look at the game with the hand cursor would
  settle it.
- The host also sets the system cursor to a fully transparent 32 × 32
  picture (`blankCursorTexture`) and hides it every frame.

## Other host details

- `deviceTestMaskImage` (`assets/DeviceTestMask.png`) is part of the
  game's interface, but the host never calls it (searched in
  `decompiled/all/`; only the test player and the by-name helpers name
  it). Not used on desktop.
- `screenShader` and `screenPausedShader` are fields the scene fills,
  but no game code reads them. (The shader names `Unlit/ScreenShader`
  and `Unlit/ScreenPausedShader` are in the asset files.) So the screen
  quad's look is whatever its material in the scene is; nothing in the
  code switches it when the game is paused.
- `applyFrameSync`, `setStretchFill`, `findResolution`, `getDeviceIsIpad`
  and the static `detectPlatformKind` have no caller in the game code;
  `Update` and `applyDesktopScreenResolution` have their own copies of
  the same steps inline.
- `HostUnity.Monitor` takes the **last** entry of Unity's list of
  screen resolutions as the monitor (inferred from Unity's
  documentation: the list is sorted from smallest to largest, so that is
  the largest mode).

## Not in the code

These decide how the screen looks but are stored in the Unity scene and
shader files, which this project has not opened (they need a Unity asset
reader; ask before downloading one):

- **The quad shader** (`Unlit/QuadShader`): how the texture and the
  quad's colour are combined (inferred: multiplied, which is what the
  game's software drawing does, `fact-pictures.md`), and how a drawn
  pixel mixes with what is under it (inferred: ordinary alpha blending,
  "source × alpha + under × (1 − alpha)"). The names `_SrcBlend` and
  `_DstBlend` appear in `sharedassets0.assets`, so some shader or
  material there sets its blending by property.
- **The colour space**: the textures and the screen picture are made as
  sRGB. If the project is set to Unity's linear colour space, blending
  happens on linear values, and half-transparent pixels (the paper
  shadows, the half-opacity seal marks, `page-layout.md`) come out a
  little different from blending the stored values directly. The
  setting is in `globalgamemanagers` (not read).
- **The screen quad's material and shader** (`Unlit/ScreenShader`
  inferred), the camera's background colour (the bars around the
  picture), the Pixel Perfect Camera's pixels-per-unit and its
  "upscale render texture" switch, and whether the window can be
  resized by the player.
- **The phantom cursor's depth and shader** (above).

For the port, meanwhile: draw every quad in the order above into a
570 × 320 picture cleared to black, with nearest-pixel reads, clamped
edges, the colour multiplied in and ordinary alpha blending on the
stored values; then scale that picture to the window by a whole number
with black bars. Leave the phantom cursor out until it is seen in the
game.

## For the port

- One render target of 570 × 320, cleared to opaque black each frame.
- Sort layers by number, lowest first; inside a layer keep the order
  the visuals were added; inside a visual, tile order. Never batch by
  texture across that order.
- Skip quads whose alpha is below 0.001 or that the clip leaves empty
  (already in `Quad.make`).
- Re-send a picture to the graphics card when its change counter
  differs from the last one sent; drop textures unused for more than 10
  frames if memory matters (optional, no visible effect).
- Windowed size: 570 × 320 doubled while the double stays under two
  thirds of the screen; in a browser, the canvas size takes this place
  (a choice for `docs/DESIGN.md`).
- The reference model is `scripts/reference/host.py`; its check is
  `scripts/checks/host_check.py`.

## Not studied

- Everything under "Not in the code" (the scene and shader files).
- How Unity itself turns the command list into graphics-card calls
  (Unity's own code, not a target).

## Things to watch in the game

None was done.

1. In a window on a 1920 × 1080 monitor, the window is 1140 × 640 and
   every game pixel is a 2 × 2 block.
2. In full screen (no command-line words) on a 16:9 monitor: whether
   the picture fills the screen or sits at a whole-number zoom with
   black bars (the Pixel Perfect Camera's behaviour with crop off).
3. Whether a grey-green arrow outline shows over the hand cursor (the
   phantom cursor).
4. A half-transparent shadow under a paper: its darkness against a
   picture of the same spot, if the colour space is to be settled by
   eye (weak; reading the setting is better).
