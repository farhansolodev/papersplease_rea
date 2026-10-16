# The desktop layout: every value of `Layout`, from the emulator

Studied on 2026-10-16. `Layout` is the one object that holds every
position and size of the screen (`border-view.md`, "The layout values").
Its constructor is too big for the decompiler, and its booth rectangles
are computed from one another, so earlier steps read a few values by hand
from the instruction listing and left the booth's rectangles open
(`desk-pictures.md`). This step **ran the game's own constructor in
Ghidra's emulator** for the desktop platform and read the finished object.
All 98 fields now have their desktop value.

Words used here:

- **emulator**: Ghidra's built-in processor simulator; it executes the
  game's machine code instruction by instruction without running the
  game;
- **stub**: a stand-in for a function the emulator should not run (for
  example the engine's memory allocator); the script does that
  function's job itself and returns;
- **booth coordinates**: positions measured from the top left corner of
  the booth part of the screen (below the border scene), not from the
  top left of the window.

Reference values: `scripts/reference/layout.py` (`DESKTOP`, every field).
Emulator script: `scripts/ghidra/EmulateLayout.java`. Decoder:
`scripts/reference/layout_dump.py`. Check:
`scripts/checks/layout_check.py`.

## How the values were obtained

`EmulateLayout.java` (one read-only Ghidra run, about a minute; output
kept on this machine as `decompiled/layout_emulation_run1.txt`):

1. Every class slot the game's code reads (the symbols named
   `..._TypeInfo`, 2,805) is pointed at a fake class record. Its block of
   static values holds 64 fake enum values (an object whose number at
   `+0x10` is 0, 1, 2...), so a test such as "shape is `LANDSCAPE`"
   compares real objects. Its method table points at stub addresses, so a
   call through an object is caught and printed.
2. Every string slot (`StringLiteral_N`, 10,106) is pointed at a fake
   string, so map keys can be named afterwards.
3. `Layout`'s static constructor runs first, as the game's own code (it
   sets the fixed numbers such as 570 x 320).
4. The constructor runs with a fake platform whose kind is
   `PlatformKind.DESKTOP`. These are replaced by stubs: making an
   object, boxing a number, the `Rect`, `PointData` and `DockPoint`
   constructors (they only store their arguments), `StringMap.set` (the
   dock points), casts, write barriers, class set-up, `floor`, and the
   string building of the constructor's log line. `app.Num.lerpScale`
   runs as the game's own code.
5. It returned after 1,649 instructions. No call was left unhandled
   except the three `StringMap.set` calls, which are the dock points.

`layout_dump.py` then decodes the object with the field offsets and types
from `dump.cs`, so no offset is typed in by hand.

### How much to trust it

- **35 values read by hand from the instructions in earlier steps** (the
  border values in `border-view.md`, the title, menu and settings values
  in `screens.md` parts 2 and 4, the layer numbers in `desk-pictures.md`,
  `touchTargetExpand` in `page-layout.md`) are reproduced exactly by the
  run (`layout_check.py`, part 2). They come from three different parts
  of the constructor, the desktop block and the shared start, so the
  emulated branch is the desktop one and the stubs did not disturb the
  arithmetic.
- One booth rectangle was checked by hand in the listing:
  `boothOuter` is made at `0x18049c1c0` from 0, 0, the wall's width
  (`[wall + 0x20]`) and the booth's height (`[booth + 0x28]`), which gives
  (0, 0, 178, 217), as the run says.
- The booth's own position was checked in the `Booth` constructor's
  instructions (`decompiled/booth_ctor_asm.txt`, `0x1801b9e59`): its y is
  set to `Layout.booth.y` (103); its x is not written there and stays at
  the start value 0 (**inferred** from the missing write). So booth
  coordinates are screen coordinates moved up by 103.
- What the run cannot show: anything that changes these values after
  the constructor. A search of the whole decompile for writes to the
  booth fields of the first table (from `booth` to `filer`, and
  `dockPoints`) found none outside `Layout`'s generic by-name setters
  (`__hx_setField`, `__hx_setField_f`; the other hits are other classes'
  own fields of the same name, such as `InspectUi.booth`), and the names
  appear as text only in `Layout`'s own field list (`__hx_getFields`) and
  once in the test player (`"give"`, a command word). So nothing is seen
  changing them; not searched for the other fields.

## The booth on desktop

The screen is 570 x 320. The border scene is the top 103 rows; the booth
fills the rest, 570 x 217, from screen y 103. In booth coordinates:

```
x:  0            178                                   570
y 0 +-------------+--------------------------------------+
    | wall  (the  |                                      |
    | traveler's  |                                      |
    | window)     |                                      |
105 |.............|  desk (open pages)                   |
107 +-- counter --+                                      |
    | top edge    |                                      |
145 |  - - floor  |                                      |
    |  of closed  |                                      |
166 +- console ---+                                      |
217 +-------------+--------------------------------------+
```

| Field | Desktop value | What uses it (doc) |
|---|---|---|
| `booth` | x 0, y 103, w 570, h 217 (screen) | Where the booth is; items wholly outside it are not drawn (`desk-pictures.md`) |
| `wall` | x 0, y 0, w 178, h 107 | The traveler's window; clip of a hung paper; the wall picture |
| `counter` | x 0, y 105, w 178, h 73 | |
| `console` | x 0, y 166, w 178, h 51 | The clock, date and weight console |
| `desk` | x 178, y 0, w 392, h 217 | Where open pages lie; reveal positions (`desk-movement.md`) |
| `boothOuter` | x 0, y 0, w 178, h 217 | Clip of a closed paper (`desk-pictures.md`); where a paper going into the drawer ends up closed (`desk-movement.md`) |
| `boothOuterClamp` | x 0, y 0, w 178, h 145 | Where a closed paper may be dragged |
| `boothInner` | x 178, y −5000, w 5392, h 10217 | "Is the cursor over the desk": in effect everything right of x 178 |
| `boothInnerClip` | x 180, y 0, w 5390, h 217 | Clip of an open page and of the drawer: **2 pixels right of the desk's edge** |
| `boothInnerClamp` | x 178, y 0, w 392, h 217 | Where an open page may be dragged (with margins, `desk-movement.md`) |
| `wallMountArea` | x 0, y 0, w 178, h 107 | Where a hung paper may be placed |
| `give` | x 39, y 0, w 100, h 107 | The give area: the middle of the traveler's window |
| `slotCenter` | (89, 116) | The middle of the counter's slot |
| `counterTopEdgeY` | 107 | Where the counter meets the window; a given paper drops behind it |
| `outerFloorMidY` | 145 | A closed paper falls until its middle is here |
| `boothMountDragBottomY` | 100 | Above this, a hangable paper is hung on the wall while dragged |
| `boothPrintBottomY` | 217 | Where printed papers come out (the booth's bottom edge) |
| `filer` | (198, 217) | The drawer's x and the line it rises from |
| `filerEnvelopeSpacingY` | 10 | Gap between envelopes in the drawer |
| `filerUseBigHandle` | false | |
| `filerCountCenter` | none | The drawer shows no count on desktop |
| `boothLayout` | `OUTER_LEFT` | The closed papers are left of the desk |
| `touchTargetExpand` | 0 | |
| `grabDeskItemGraceRect` | none | |
| `boothHeaderHeight` | 0 | |
| `stampBar` | (570, 24) | |
| `stampBarEdgeGrace` | 10 | |
| `shutterSwitch` | (150, 4) | |
| `reasonSprite` | (182, 0) | |
| `fingerprintButton`, `searchButton`, `detainButton` | (277, 0), (191, 0), (105, 0) | |
| `interrogateButtonRect` | x 73, y 163, w 33, h 49 | The interrogate button (the inspect mode, drawing part 5) |
| `interrogateButtonTextCentered` | true | |
| `inspectableCounter`, `inspectableFace` | x 9, y 120, w 160, h 46; x 47, y 23, w 80, h 80 | Things in the booth that the inspect mode can mark (the inspect mode, drawing part 5) |
| `inspectableClock`, `inspectableWeight` | x 2, y 184, w 30, h 31; x 146, y 184, w 30, h 31 | Same |
| `consoleClock`, `consoleTranscriptBolt`, `consoleDate`, `consoleTravelerCount`, `consoleWeight` | (9, 21), (85, 31), (4, 48), (86, 42), (164, 34) | Inside the console |
| `consoleKind` | `UNDEROVER` | |
| `consoleClockHourWidth` | 1 | |
| `useInspectMagnifier` | false | No magnifier in inspect mode |
| `inspectInstructionsOnTop` | false | The inspect hint sits at the bottom |
| `inspectDiagramFavorUpRight` | false | |
| `inspectButtonOverrideHitRect` | none | The inspect button's own picture is its hit area |
| `touch` | false | |

The positions of buttons and console pieces are given here as the run
gave them; in whose coordinates each is meant (booth or one of its
parts) is a question for the code that uses it, not read here.

### The dock points

The three papers with `dock="true"` go back to a fixed place on the
counter. All three enter from the top (`TOP`), may be dragged anywhere in
x 0..570, y 0..178 while closed (`clamp`), and have no clip of their own:

| Key | Home (x, y, w, h) |
|---|---|
| `rules` | 113, 174, 26, 34 |
| `bulletin` | 42, 170, 21, 38 |
| `transcript` | 71, 171, 37, 46 |

The homes lie on the console (y 166 and below), at the bottom of the
counter column.

### Everything else

The remaining fields, for completeness (all in `layout.py`): `border` x 0,
y 0, w 570, h 103; `borderOuterBoothButton` (146, 65) and its react margin
**0** (now seen, no longer inferred: `buttons.md`); `borderScale` 1;
`borderShowSnipingSurround` false; `borderPersonHitSize` (8, 18);
`borderSnipingTimescale` 1; `borderCamRectL`, `borderCamRectR` none;
`portraitHeightStretchT` 0; `headerInEndless` false;
`endlessScoreboardPos` (180, 2); `endlessScoreboardScrollWithBorder`
true; `tranqRifleButtonY` 113; `menuItemPaddingY` 10; `settingsPadding` 4;
`settingsTipsOnTop` false; `settingsButtonX` 180; `settingsButtonSize`
(15, 15); `titleLogoScale` 1; `titleStackFooter` false;
`titleShowVersion` true; `titleLogoTop` 28; `titleMenuCenterY` 260;
`confirmBoxPadding` (15, 20); `standardFooterButtonY` 290; `notchHeight`
**0** (now seen, no longer inferred: `screens.md`); `introTextWidth` 380;
`nightMessageWidth` 520; `gameScreenHeaderY` 13; `aspect` `LANDSCAPE`;
`shape` `LANDSCAPE`; the layers (filer 1, shutter shadow −1, mounted
paper −2, wall −3, stamp desk 2, tutorial 3, unstash overlay 4); `rack`,
`carousel`, `stampDesk`, `boothCarouselFilerClip` none (phone parts);
`showPauseButton` false; `kPixelWidth` 570; `kPixelHeight` 320;
`subpixelCount` 1.

## Notes for the port

- Take the values from `layout.py`; do not re-derive them.
- Keep the desk's open-page clip starting at x 180, two pixels right of
  the desk's edge at 178 (by the code; not seen in the game).
- `boothInner` is a "right of x 178" test written as a huge rectangle;
  the port can write it as that.

## Not studied

- The tablet and phone values (not needed for a desktop port; the
  emulator script could give them by passing another platform kind).
- `Layout`'s static numbers (`kGiveZoneWidth` and the like) were used by
  the run but not printed one by one.
- In which coordinates the button and console positions are meant.

## Things to watch in the game

None was done.

1. The open-page area starts two pixels right of the counter's edge (a
   page dragged left is cut there).
2. The rulebook, bulletin and transcript go back to the three places in
   the table, at the bottom of the counter column.
