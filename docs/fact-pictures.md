# Drawing, part 3: the fact pictures of a page (`BoothEnv.getImage`)

Studied on 2026-10-16. A picture mark whose name starts with `$`
(`image="$Face"`, `page-layout.md`) shows a fact.
`play.day.BoothEnv.getImage(paper id with index, fact id, scale, text
colour, back colour)` turns the fact into a picture. This covers what it
makes for each fact, the picture operations it uses, and every random
draw it makes. Everything here is from the code; **nothing was compared
with the running game**. The pictures look right in the previews, but a
look is not a comparison.

Reference script: `scripts/reference/factpics.py`. It makes the pictures,
and `pages.py` now uses it to draw a page's fact pictures. Check:
`scripts/checks/fact_pictures_check.py`.

## What was read

Read in full in `decompiled/all/`: `BoothEnv.getImage`; `Face.getDocImage`,
`getPhotoHeadImage` and the `Face` static values; `FaceSpec.fromString`;
`FingerprintCode.fromString`, `getImage`, its constructor and static
values; `Traveler.getBodyImage` and `getContrabandImage`;
`BodyLib.getBodyImage`, plus the cut in `BodyLib.getContraband`;
`Criminal.getFace`; `EmblemLib.getValidImage`, plus how its constructor
makes the faded copy of a seal sheet; `app.vis.Image.paste`, `copy`,
`fill`, `replace`, `tint`, `draw`, `transformed`; `Clipper.clip`;
`Affine.invert`; `Point.transform`; `FactLib.getFactFormat`. Read in part:
`EmblemLib.getEmblemImage` (only which picture it cuts from; the rest is in
`emblems-and-bodies.md`) and where the `BoothEnv` constructor sets the
rulebook's upgrade pictures.

One read-only Ghidra run (`decompiled/drawing3_run1.txt`,
`DumpAssembly.java`) settled what the decompiler left unclear:

- `System.Math.Cos` and `Sin` jump to `FUN_18012fb50` and `FUN_180130a00`,
  so `transformed` turns by the usual rotation.
- Haxe `Math.round`.
- `getValidImage`'s row formula.
- `FingerprintCode.getImage`'s finger count and alpha arithmetic.
- `getImage`'s arguments to the passport photo, criminal photo and
  fingerprint calls, and its scale test.

Ten constants were read with `read_doubles.py`: 1.0, 0.5, 0.0, 0.0001, 3.0,
10.0, −0.5, 25, 42 and 12.

## Who calls it

- The `PaperInnerVisuals` constructor, for every picture mark with a fact
  that its link does not leave out (`page-layout.md`).
- `PaperInnerVisuals.autoGetPageIndexForFactId`, to test whether a mark
  would draw something. So **this also makes the draws below**. Its
  callers are three `BoothEnv` functions named `auto…`. No caller of those
  was found by name or by slot. They are reachable only through the
  by-name dispatch (`__hx_invokeField`). **Inferred** from the `auto`
  prefix (as in `Border.autoGetLivingTargetPerson`,
  `border-shooting.md`): they serve the game's test player and do not run
  in normal play. Not traced.

## The order of the tests

The fact is looked up as `<paper>/<fact>` in the booth's facts. Then:

| Test, in this order | Picture | Scaled at the end? |
|---|---|---|
| a traveler is present and the fact is `Face` | the document photo | no (its own size uses the scale) |
| a traveler is present and the paper is `Photo` | `HeadFront`, `HeadBack`, `BodyFront`, `BodyBack`, `ContrabandBack`, `ContrabandBackLegL`, `ContrabandBackLegR` as below; **any other fact: nothing** | no |
| the fact does not exist | nothing | |
| `Fingerprints` | all five fingers | yes |
| `Thumbprint` | the first finger only | yes |
| starts with `Criminal` | a bulletin criminal photo, or the blank picture | yes |
| `SealsMoa`, `SealsMol` | the rulebook's sheet of valid seals (Ministry of Admission, of Labor) | yes |
| the value is `BulletinEmblem` | the bulletin's faded seal | yes |
| the value is empty | nothing | |
| anything else | the picture file `assets/papers/<value>` | yes |

"Nothing" leaves the mark out (`page-layout.md`). "Scaled" means: if
|scale − 1| > 0.0001, the picture is replaced by `Image.transformed(0,
scale)` (below).

The check sorts all 57 picture facts of `Papers.xml` (75 marks):

| Branch | Facts | Marks |
|---|---|---|
| document photo | 6 | 12 |
| search photo: head, body, contraband | 7 | 7 |
| fingerprints, thumbprint | 4 | 4 |
| criminal photos | 3 | 3 |
| valid seal sheets | 2 | 4 |
| by value | 35 | 45 |

No `Photo` fact falls through to "nothing".

## The document photo (`Face`)

**Which face.** No fact at all: a box filled with opaque red (`FF0000`),
`floor(80 x scale)` by `floor(96 x scale)`, and no draw. Otherwise the
fact's value decides:

- `VALID`: the traveler's document face (`docFace`, built in the colours of
  a document photo, `faces.md`).
- Anything else: `FaceSpec.fromString(rand, value)` (one draw for each part
  that is missing or `*`, `traveler-build.md`), then a new face made with
  `FaceLib.makeFace(spec, for a document)`. A wrong face's value is a full
  specification (`value-helpers.md`), so it makes no draw here. An empty
  value would make six draws, since parts 1 to 6 are missing (not seen in
  the data; edge only).

**The picture** (`Face.getDocImage(rand, scale, flipX, replaceColors, text
colour, back colour)`):

1. A picture `round(80 x scale)` by `round(96 x scale)` (`Math.round`,
   below), filled opaque black.
2. The face picture (150 x 120) is placed by this matrix, in this order:
   move it so its bottom middle is at the origin (−75, −120); scale by
   (−scale if `flipX` else scale, scale); move by (picture width x 0.5,
   picture height + d). Here **d = round(3r + 3)**, with **one draw** r,
   so 3, 4, 5 or 6 (6 only when r ≥ 5/6). So the face's bottom edge sits
   3 to 6 pixels below the photo's bottom edge, centred across.
3. It is drawn with `Image.draw` (below): no smoothing, only pixels with
   alpha 128 or more are copied.
4. If `replaceColors`: every pixel of the dark photo tone `574848` becomes
   the text colour, then every pixel of the light tone `A29490` becomes the
   back colour (both with alpha `FF`). It is done in that order, so a text
   colour equal to `A29490` would end up as the back colour.

The black never shows. The check drew 12 faces at every scale used (0.4,
0.5, 0.75, and 1.0 for criminals), with every shift 3 to 6, mirrored and
not. That is 384 pictures, and none has a black pixel. A document face is
opaque everywhere (`faces.md`), and it is larger than the photo.

**The two flags.** `getImage` passes `flipX = replaceColors = (paper id ≠
"Passport")`, which was checked in the instructions (`SETZ`). So:

- The seven passports (all share the id `Passport`) show the face as built,
  in the two photo tones.
- The five other papers with a photo show it **mirrored** and in their own
  colours: `AsylumGrant`, `IdCard`, `Pezpert`, `PressPass`,
  `SecondPassport`.
- `SecondPassport`'s colours are the two photo tones themselves (text
  colour `574848`, back `A29490`). So it differs from a passport photo only
  by the mirror and the draw. (It is the second passport a traveler may
  hold; `Facts.xml` cites it as conflicting passports.)

The sizes come out as 32 x 38 at 0.4 (`IdCard`), 40 x 48 at 0.5, and
60 x 72 at 0.75 (`AsylumGrant`).

## The search photo (paper `Photo` only)

The `Photo` paper has two pages, front and back (`Papers.xml`). The facts
in its `Facts.xml` section hold no value that is used here.

- **`HeadFront`, `HeadBack`** (`Face.getPhotoHeadImage(faceLib, front)`):
  - It uses the traveler's own face (`face`, in colour), not the document
    face, and only its head-alone picture with that picture's chin point
    (`faces.md`, step 6 of building a face).
  - It makes a 50 x 50 picture: the head is scaled by 0.5, and mirrored
    for the back (scale x −0.5). It is placed so its chin lands at
    (25, 42). The draw is the same `Image.draw`.
  - Then `FaceLib.replaceColors(picture, 7)` for the front, 8 for the
    back. These are rows 70 and 80 of `FacePalette.png`, which is 90 rows
    high. The head-alone picture keeps the five base face colours (the
    traveler's own palette is applied only to the full picture,
    `faces.md`), so these rows recolour it.
  - No draw.
- **`BodyFront`, `BodyBack`** (`Traveler.getBodyImage(nude, front)`):
  - Which body: `BodyLib.getBodyId(male, bmi)` (`emblems-and-bodies.md`).
  - Which picture: `assets/faces/Body<id>.png` when `nude`, otherwise
    `Body<id>c.png`. **`nude` is the player's Nudity setting.**
  - The cut is the left half (front) or right half (back), 100 x 160 from
    the top. It is kept per traveler for each of the four kinds.
  - All twelve body pictures are 200 x 200 (checked). No draw.
- **`ContrabandBack`, `…LegL`, `…LegR`**: only if the fact is invalid
  (`findInvalidFactPath`, `operations-and-fact-validity.md`). Then
  `Traveler.getContrabandImage(rand, "back" | "legl" | "legr")`:
  - The first time for a traveler, it picks one contraband with
    `BodyLib.getContraband(rand, body, the traveler's contraband types,
    any place)`. That is **one draw**, made even when nothing fits
    (`ArrayUtil.getRandomItem` draws before it looks at the list;
    `emblems-and-bodies.md`).
  - It keeps the pick under its place.
  - If the asked place holds it, the result is its cut piece. Otherwise
    nothing.
  - So a traveler shows at most one contraband piece, and the draw happens
    once.
  - The piece is the place's rectangle in size (`back` 40 x 45, `legl`
    25 x 35, `legr` 26 x 37). It is cut from the contraband picture at the
    rectangle moved back by the body's offset.
  - The check confirms that each contraband mark's `pos` on the back page
    is the body mark's `pos` (19, 24) plus its place's rectangle corner.
    So the piece lands on the body where the rectangle says.
  - `Contraband.pastePos` always equals that rectangle corner, and
    `getImage` does not use it.

## Fingerprints and the thumbprint

**The code.** The value (the traveler's fingerprint text,
`fact-values.md`) goes through `FingerprintCode.fromString(rand, text)`:

1. Its constructor first makes a random code: **five draws plus the
   redraws** of `traveler-build.md`.
2. Then finger i is set from character i: `-` gives −1, a digit gives
   itself, anything else 0.

So **every fingerprint picture costs those draws**, whatever the value.

**The picture** (`FingerprintCode.getImage(res, text colour, allFingers,
cell width)`):

- `allFingers` is true for `Fingerprints` and false for `Thumbprint`, so
  5 fingers or 1.
- The cell width comes from the fact's `format` attribute
  (`FactLib.getFactFormat`, default `"32"`). No fingerprint fact has a
  `format` in `Facts.xml`, so the width is always 32. (A width of 0 would
  also become 32.)
- The picture is (fingers x 32) x 32, transparent to start.

For each finger i, in order:

1. **One draw** r, made before the finger is looked at.
2. The sheet `assets/FingerSworls.png` is 96 x 320: 3 columns by 10 rows
   of 32 x 32 prints.
   - The column is `(i + 1) / 2` (whole numbers): the thumb uses column 0,
     fingers 1 and 2 use column 1, fingers 3 and 4 use column 2.
   - The print is the row given by the finger's number (0 to 9).
   - The mask is row `floor(10 r)` of the same column. A draw of exactly
     1.0 would give row 10, past the sheet: the game would fail on the
     array bounds. The chance is about 1 in 2³¹.
3. A finger of −1 instead gets `FingerSworlBlank.png` (32 x 32) pasted at
   (32 i, 0), plain copy (`REPLACE`).
4. Otherwise each pixel of the 32 x 32 cell gets the text colour (RGB)
   with alpha = (mask pixel's alpha − print pixel's blue) **modulo 256**.
   This was checked in the instructions (two `SHL 0x18`, `SUB`).

The sheet has only three colours: transparent white (alpha 0, blue 255),
opaque black and opaque white. So the alpha comes out as:

| mask pixel | print pixel | alpha |
|---|---|---|
| opaque | black | **255**: ink |
| opaque | white or transparent | 0 |
| transparent | black | 0 |
| transparent | white or transparent | **1** (0 − 255 wraps) |

So a finger shows the black of its print, cut to the shape of a randomly
chosen print of the same column. Most of the rest of the picture is
alpha 1 rather than 0. Over 200 random codes: 55% of pixels at alpha 1,
14% at 0, 31% at 255. Alpha 1 is invisible in practice. Whether anything
reads it (a hit test, for example) was not checked.

## The bulletin's criminal photos (`Criminal0` to `Criminal2`)

- **Empty value:** `assets/papers/BulletinCriminalBlank.png` (80 x 96),
  scaled. No draw.
- **Otherwise:** the value is a number into the day's criminals.
  `Criminal.getFace(faceLib)` makes, once, the document face of that
  criminal's specification. Then `getDocImage(rand, scale 1.0, flipX
  false, replaceColors true, text, back)`: **one draw**, 80 x 96. Then the
  picture is scaled by the mark's 0.4, so the sizes come out as 32 x 39.
- The same face at scale 0.4 directly would be 32 x 38. The difference is
  that `transformed` rounds sizes up, while `getDocImage` rounds to the
  nearest. The blank picture also comes out at 32 x 39.

## The seal sheets

**`SealsMoa`, `SealsMol`** (`EmblemLib.getValidImage(id, back colour)`).
`Facts.xml` gives both an empty value under the comment "Moved to code".
The value is not read here.

1. The first emblem set with that id is used, and its **faded sheet**.
   `EmblemLib`'s constructor makes that sheet when it loads the sets: a
   copy of the sheet tinted `80000000`, so every pixel is black with its
   alpha halved.
2. The picture is (2 x cell width + 12) by ((rows − 1) + rows x cell
   height), where rows = (valid + 1) / 2. It is filled with the back
   colour (alpha `FF`).
3. Valid seal i (0 to valid − 1) is cut from the sheet's cell i. It is
   pasted with `BLEND` at:
   - x = (i mod 2) x (cell width + 12)
   - y = floor(i / 2) x cell height + floor(i / rows)

   The y formula was checked in the instructions: `DIVSD` by the rows
   count. For the Ministry of Labor (4 valid, 2 rows) this gives tops 0,
   0, 36 and 36: a one-pixel gap between the rows. For the Ministry of
   Admission (2 valid, 1 row) the second seal's top is **1**, not 0. So it
   sits one pixel lower and its bottom row falls outside the 35-pixel
   picture. That row of the seal is fully transparent (checked), so the
   only visible effect is the one-pixel offset.
4. Sizes: Admission 82 x 35, Labor 82 x 71.

The result is dark shapes at half strength on the page colour. The
rulebook's "valid seals" pages in the preview look like that.

**`BulletinEmblem`** (the value `BoothEnv.addBulletinForDay` writes to
`Bulletin/Emblem<n>`, `papers-on-desk.md`):

- It is `EmblemLib.getEmblemImage(rand, "MinistryOfAdmission", "", cell
  0)`: a given cell, so **no draw**.
- The cell is cut from the normal sheet, copied, then tinted `80FFFFFF`
  (alpha halved).
- It is 35 x 35 at half opacity.

## Pictures named by the value

The value is a file name in `assets/papers/`. Where the values come from
(found by searching the decompile for the fact paths; all 35 facts have
one and every file exists, checked):

| Fact | Value | From |
|---|---|---|
| `Rules/<nation>-Passport0` (7) | `PassportOuter<nation>.png`, scale 0.5 (60 x 80 becomes 30 x 40) | `Facts.xml` (`[NATIONS]`) |
| `Rules/IssuingCity`, `DiploAccess`, `SealRequired` | `RuleIssuingCity.png`, `RuleDiploAccess.png`, `RuleSealRequired.png` | `Facts.xml` |
| `Rules/DiploSeals<nation>` (6) | `DiploSeals<nation>.png` | `Facts.xml` |
| `Rules/Upgrade0` to `3` | see below | the `BoothEnv` constructor |
| `Bulletin/PagesNote` | `BulletinPagesNote.png`, when a notice has `[PAGESNOTE]` | `BoothEnv.addBulletinForDay` (`papers-on-desk.md`) |
| `Transcript/NextPage0`, `1` | `TranscriptNext.png` | `BoothEnv.applyOp` |
| `TimeBomb/Wire0` to `3`, `Screw0` to `3` | `TimeBombWire<n>.png`, `TimeBombScrew.png` | `Facts.xml` |
| `Poison/Powder1`, `2` | `PoisonPowder1.png`, `PoisonPowder2.png` | `Facts.xml` |

**The rulebook's upgrade pictures** (the `BoothEnv` constructor, by the
story's upgrade set). On desktop, each is set only if the story has the
upgrade:

| Fact | Upgrade | Picture |
|---|---|---|
| `Upgrade0` | `INSPECT_HOTKEY` | `RulesUpgrade0.png` |
| `Upgrade1` | `STAMPBAR_HOTKEY` | `RulesUpgrade1.png` |
| `Upgrade2` | `RULEBOOK_TABS` | `RulesUpgrade2.png` |
| `Upgrade3` | `INSPECT_DOUBLECLICK` | `RulesUpgrade3.png` |

The tablet set uses `BOOTH_MULTITOUCH` (`RulesUpgrade4.png`) and
`RULEBOOK_TABS`, and the phone set starts with `RULEBOOK_TABS`. Those were
not read further. A fact never set does not exist, so its mark is left
out.

## Picture operations (`app.vis.Image`)

A pixel is 4 bytes B, G, R, A, read as one number `AARRGGBB`.

- **`draw(image, matrix)`**: already read for `faces.md`, and the same
  here.
  - The target area is the bounding box of the four transformed corners:
    from max(0, whole part of the minimum) to min(size, whole part of
    (maximum + 1)).
  - For each pixel (x, y) of it, the inverse matrix maps (x, y), the
    pixel's corner and not its centre, back to the source. Both
    coordinates are cut toward zero, so −0.5 gives 0.
  - A source pixel with alpha ≥ 128 is copied as it is. Others are
    skipped. There is no blending.
- **`transformed(rotation in radians, scale)`**:
  - A matrix moves the picture's centre to the origin, turns it by
    (cos, −sin; sin, cos), then scales it.
  - The new picture is the bounding box of the four corners, each size
    **rounded up**, transparent.
  - The matrix is moved so the box starts at 0, and the picture is drawn
    with `draw`.
  - With no turn and scale k, a size n becomes ceil(n k), and target pixel
    x shows source pixel x / k cut down. A 60 x 80 passport cover becomes
    30 x 40 from its even pixels.
  - The rotation is used as given (the newspaper's stamp,
    `newspaper-picture.md`).
- **`paste(source, x, y, rect, paste mode, colour mode)`**:
  - x and y are cut toward zero.
  - `Clipper.clip` cuts the rectangle (default: the whole source) to both
    pictures. A negative target position moves the source start. A
    negative source start is raised to 0 without moving the target.
  - The default modes are `REPLACE` and `DEFAULT` (no tint). Per pixel:

  | Mode | DEFAULT colour mode | TINT (colour t) |
  |---|---|---|
  | `REPLACE` | copy the pixel as it is (row by row, alpha too) | each channel x t's channel / 255, alpha x t's alpha / 255; write |
  | `OVERLAY` | copy if alpha ≥ 128 | the tinted pixel, written if its alpha ≥ 128 |
  | `BLEND` | each colour channel = (target x (255 − a) + source x a) / 255; alpha = max(target alpha, a) | the same with the tinted pixel and its alpha |

  All divisions are whole numbers, cut down.
- **`copy(rect)`**: no rectangle gives a byte copy. Otherwise a new picture
  of the rectangle's whole size, with that part pasted in (`REPLACE`).
- **`fill(colour, rect)`**: writes the colour as it is over the clipped
  rectangle (alpha too). No rectangle fills the whole picture.
- **`replace(find, put)`**: every pixel exactly equal to `find` becomes
  `put`.
- **`tint(colour)`**: each channel, alpha included, times the colour's
  channel / 255, cut down.
- **Haxe `Math.round`** (checked in the instructions): take i = the whole
  part toward zero and d = x − i. Then i + 1 if d ≥ 0.5, i − 1 if
  d < −0.5, otherwise i. So halves go up for positive numbers (2.5 gives
  3), and −2.5 gives −2.

## Random draws, all from the booth's generator

| Picture | Draws |
|---|---|
| document photo, `VALID` or a full face specification | 1 (the shift) |
| document photo, a value with missing or `*` parts | 1 per such part, then 1 |
| document photo, no fact | 0 |
| criminal photo | 1, or 0 when the slot is blank |
| fingerprints | the random code (5 plus redraws), then 5 |
| thumbprint | the random code (5 plus redraws), then 1 |
| contraband | 1 the first time for a traveler, if the fact is invalid (even when nothing fits); then 0 |
| search photo head, body | 0 |
| seal sheets, bulletin seal, files | 0 |

The seal marks (`emblem="..."`, three draws) are separate from this
function (`page-layout.md`, `desk-drawing-draws.md`).

`desk.py` now counts the fingerprint and thumbprint draws for a paper's
first page. Re-run on 2026-10-16, `compare_with_log.py` still matches
36 of 36 (route 20) and 8 of 8 (route 1).

**This does not test the new draws.** Route 20 draws four fingerprint
pictures (the identity record and the fingerprint paper, twice each), but
three deliberate extra draws there still give 36 of 36. So they come
after the last pick the log can show (as `desk-drawing-draws.md` already
noted for the identity record). The contraband draw is on the search
photo's second page, which `desk.py` does not model (pages drawn again are
not modelled).

## The Nudity setting

Its readers: `getImage` (the body picture, above), and `Booth.update`.
When the setting differs from the booth's copy, `Booth.update` updates
the copy and calls `BoothEngine.applyUpdatedSettings`, which was not read.
Everything else that names it is the settings code: `Settings`,
`SettingsMenu`, the save and load (`screens.md`, part 4;
`save-format.md`).

## Preview and checks

`fact_pictures_check.py` (run 2026-10-16) prints `problems: none`. It
checks:

- the branches above;
- every value's file exists, and each code value is among the code's
  strings;
- the sizes;
- the fingerprint sheet (96 x 320, three colours);
- the seal sheets and the lost row;
- the twelve body pictures;
- the palette rows;
- the black that never shows;
- the contraband positions.

Previews looked at:

- `factpics.py <assets> extracted/previews/factpics`: a passport photo and
  the same face mirrored and recoloured for an id card, a missing photo,
  fingerprints with and without a missing finger, a thumbprint, a criminal
  photo, the head front and back, the body front and back, a contraband
  piece, both seal sheets, the bulletin seal, and a rulebook passport
  cover at half size.
- `pages.py` with `--face` and `--prints`: an Arstotzka passport, an
  Arstotzka id card, the fingerprint paper, the bulletin's criminals page,
  and three rulebook pages (Antegria with its diplomatic seals and passport
  cover, the entry permit and work pass pages with their seal sheets).

## Notes for the port

- Make the photos with the same matrix, the same nearest-pixel draw (pixel
  corner, cut toward zero, alpha ≥ 128) and the same draw order: the
  random shift belongs to the booth's sequence.
- Mirror and recolour the photo on every paper except `Passport`.
- Keep `round` for the document photo's size and "round up" for
  `transformed`. The criminal photos are 32 x 39, the id card's photo
  32 x 38.
- Count the fingerprint code's draws even though the value overwrites
  them, and one draw per finger.
- Whether to keep the fingerprint picture's alpha-1 background, and the
  Ministry of Admission seal's one-pixel drop, is a design question: both
  are what the code does, and neither is visible in a normal look.

## Not studied

- `Image.render` (how a quad is drawn into a picture), and how the page's
  visuals reach the screen (the Unity side).
- `BoothEngine.applyUpdatedSettings` (what a change of the Nudity setting
  redraws, and whether that makes draws again).
- The tablet and phone upgrade pictures in full.
- Whether the alpha-1 pixels of a fingerprint picture count for anything.

## Things to watch in the game

None was done.

1. An id card next to its passport: the id card's photo should be the
   passport photo mirrored, in the id card's colours.
2. A second passport (`SecondPassport`): its photo mirrored compared with
   the first passport.
3. The fingerprint paper: each finger cut to the outline of a different
   print, and a missing finger's blank.
4. The bulletin's criminal photos: 32 x 39 in the game's pixels, not
   32 x 38.
5. The rulebook's Ministry of Admission seal sheet: the right seal one
   pixel lower than the left.
6. With Nudity off, the search photo's body clothed (`Body<id>c.png`).
