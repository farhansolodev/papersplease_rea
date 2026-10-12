# Faces: `Faces.xml`, the sheet images and how a face is built

Studied on 2026-10-13. This covers how `Faces.xml` is loaded, how a face
picture is assembled from four pieces, and how the face's pixel height (which
sets the traveler's height, `traveler-build.md`) is worked out. What a face
*specification* is and where it comes from is in `traveler-build.md`.

Functions read in full: `data.FaceLib` (constructor, `copyDecoration`,
`makeId`, `makeFace`, `replaceColors`); `data.Face` (constructor, static
values, `get_heightInMeters`); `data.FacePiece` (constructor, static values,
`addMark`, `makeHead`, `makeEyes`, `makeNoseMouth`, `makeShoulders`,
`flipOnX`, `flipPointOnX`); `data.FaceSpec.getSheetId` and static values;
`app.vis.Image.draw`, `fromPng`, `fill`, `copy`; the affine `invert` and
point `transform` helpers. One ambiguous branch (`makeShoulders`) and one
dropped value (the loader's key index) were settled from the raw
instructions; four constants were read from the DLL.

Everything here is confirmed in the code unless marked otherwise. The
procedure is implemented in `scripts/reference/faces.py`, which builds faces
from the local sheet images.

## `Faces.xml`

`<faces>` holds `<sheet id>` elements, each with `<face>` elements. The
loader stores one record per face under the key `<sheet id>:<position>`,
where the position counts from 0 within the sheet (`M0:2`, `F4:3`).

| Attribute | Read as | Use |
|---|---|---|
| `age`, `bmi`, `hairheight` | whole numbers, 0 if not a number | Age, body-mass index, hair height in pixels |
| `canbeconfusing` | contains `head`, `eyes`, `mouth` | Which pieces can pass for the other gender |
| `head`, `shoulders`, `mouth`, `eyes` | text | "Has" description words, by piece |
| `nhead`, `nshoulders`, `nmouth`, `neyes` | text | "Has not" description words, by piece |
| `id` (on `<face>`) | **not read** | |

How these are combined for a face made of four pieces is in
`traveler-build.md` ("Face metadata").

## The image files

In `assets/faces/`, for each sheet `M0`..`M6`, `F0`..`F4`:

| File | What |
|---|---|
| `Sheet<id>.png` | The coloured faces |
| `Sheet<id>d.png` | The same faces for document photos |
| `Sheet<id>p.png` | The **key image**: flat colours marking which pixels belong to which piece, plus white marker dots |

Each sheet is 300 × 240: four faces of 150 × 120, at positions 0 (top
left), 1 (top right), 2 (bottom left), 3 (bottom right). Piece number `p`
is position `p mod 4` on sheet `p div 4`.

Key colours (opaque): dark green and green = eyes; dark blue and blue = nose
and mouth; cyan = both; red = where head and shoulders overlap; black =
shoulders only; white = marker dot.

The seven **marker dots** of a face are found by reading the key image row
by row: the first two are the eyes, then nose, mouth, chin, and the last two
the shoulders.

`assets/FacePalette.png` is 50 × 90: nine rows of five 10 × 10 swatches. Row
0 holds the five base colours (two clothes colours, three face colours); row
`n` holds palette `n`'s replacements.

## Cutting out a piece (`FacePiece`)

A piece starts as one 150 × 120 face cut from the colour sheet (the `d`
sheet for a document photo) and the matching cell of the key image. Each
"make" step walks the key image and edits the colour image:

| Key pixel | Head | Eyes | Nose and mouth | Shoulders |
|---|---|---|---|---|
| dark green | dark face colour | keep unless mid face colour | clear | clear |
| green | mid face colour | keep unless mid face colour | clear | clear |
| dark blue | dark face colour | clear | keep unless mid face colour | fill |
| blue | mid face colour | clear | keep unless mid face colour | fill |
| cyan | mid face colour | keep unless mid | keep unless mid | fill |
| red | keep | clear | clear | fill |
| black | clear | clear | clear | keep |
| white (marker) | eye, nose, mouth dot: mid face colour; shoulder dot: clear; chin dot: keep | eye dot: keep unless mid; others clear | nose, mouth dot: keep unless mid; others clear | clear |
| anything else | keep | clear | clear | clear |

"Keep unless mid face colour" means a pixel that is exactly the mid face
colour becomes transparent, so the head's own skin shows through. "Fill" is
the dark clothes colour (for a document photo, the light photo tone).

So the head piece is the face with its own eyes, nose and mouth painted
over in skin colours, ready to receive other faces' features.

Colours: face `3D5043` (dark), `848A6B` (mid), `DED6AC` (light); clothes
`551B18`, `892C27`. For a document photo everything is one of two tones,
`574848` (dark) and `A29490` (light), and the background is the light tone
instead of transparent.

**Quirk**: in the shoulders piece, the code writes the fill colour on marker
dots and then immediately clears them, so they end up transparent.

## Mirroring (`flipOnX`)

When the specification's flip flag is set, each piece is mirrored about a
whole-pixel column: the shoulders and the head about their own chin dot's
column, the eyes and the nose-and-mouth pieces about the column half way
between their own two eye dots (rounded down). Pixels whose mirror image
would fall outside the piece are cleared. All seven dots are mirrored too,
and the two eye dots swap places.

## Putting the face together (`Face` constructor)

All four pieces are made for the specification's gender (shoulders, head,
eyes, nose-and-mouth piece numbers), mirrored if asked, then:

1. **Eyes onto the head.** The eyes piece is stretched sideways by
   (head's eye spacing ÷ eyes piece's eye spacing) and placed so its first
   eye dot lands on the head's first eye dot.
2. **Nose and mouth onto the head.** Stretched up and down by the average of
   1 and (head's nose-to-mouth distance ÷ the piece's), and placed so the
   mid-points between nose and mouth dots coincide.
3. A new 150 × 120 picture, transparent (or the light photo tone).
4. **Shoulders.** Stretched sideways about the mid-point of the shoulder
   dots by the average of 1 and (head's shoulder width ÷ shoulders' shoulder
   width).
5. **Head.** Stretched sideways by the average of 1 and (shoulders' width ÷
   head's width), **at most 1.05**, and placed so its chin dot lands where
   the shoulders' chin dot ended up. Nothing moves or stretches vertically
   here, so the head's rows shift by (shoulders' chin row − head's chin
   row).
6. A second picture with the head alone, and where its chin is, are kept
   (for later use; not studied).

For a document photo the work stops here. Otherwise:

7. The face's combined metadata is fetched (`traveler-build.md`).
8. **Pixel height.** The picture is scanned from the top row down for the
   first row containing a pixel of the dark face colour (alpha ignored).
   `heightInPixels = 120 − hair height − that row`. (If that came to
   exactly 0 the scan would go on to the next row.)
9. **Palette.** If the palette number is not 0, every pixel equal to one of
   the five base colours is replaced by that palette's colour. This happens
   after the height scan.

Height in metres = `1.0 + heightInPixels / 110` (the constant is the double
nearest 1/110).

### How pixels are drawn (`Image.draw`)

There is no smoothing or blending. For each whole pixel of the target inside
the stretched picture's bounding box (computed with truncation, the far edge
plus 1), the pixel's own coordinates are mapped back through the inverted
transform, both results are **truncated toward zero**, and if they fall
inside the source and the source pixel's alpha is above 127 it is copied
over. The inverse uses `1 / determinant` multiplied through; the port needs
the same arithmetic in double precision to land on the same pixels
(`faces.py` copies the formulas).

PNGs are decoded to one 32-bit number per pixel, alpha in the top byte, then
red, green, blue.

## Cross-check with the data

`scripts/checks/faces_check.py` (run 2026-10-13):

- 12 sheets of 4 faces in `Faces.xml` (7 male, 5 female). The only
  attribute the loader does not read is `id`. Hair heights run from −7 to
  23.
- All 36 sheet images exist and are 300 × 240; every pixel is fully opaque
  or fully transparent. The key images use only the eight colours above.
- 45 of the 48 faces have exactly seven marker dots, in the expected
  layout. **Sheet `M6` has artwork only at position 0** (piece 24); its
  other three entries in `Faces.xml` have no picture and no dots. A
  specification naming piece 25, 26 or 27 would fail. `Travelers.txt` uses
  nothing above 24.
- One face (`F1`, position 0) has its right shoulder dot one row above the
  left, so the "first" shoulder dot is the right-hand one. Only the distance
  and mid-point of the two are used, so nothing changes; a port must not
  assume the first is the left.
- `FacePalette.png` is 50 × 90 with flat swatches; row 0 is the five base
  colours in the order clothes dark, clothes light, face dark, face mid,
  face light. Rows 7 and 8 exist beyond the six random palettes and palette
  6: the code names them "photo front" and "photo back".

### Heights that can occur

`faces.py survey` builds every head with every set of shoulders (eyes and
nose-and-mouth taken from the head's own face; they cannot change the top
row) and reports `heightInPixels`:

| Faces | Pairings | Pixel height | Face height |
|---|---|---|---|
| Male, random (pieces 0 to 19) | 400 | 71 to 106 | 1.645 m to 1.964 m |
| Male, all pieces with artwork (0 to 24) | 625 | 46 to 106 | 1.418 m to 1.964 m |
| Female (pieces 0 to 19) | 400 | 68 to 100 | 1.618 m to 1.909 m |

No pairing gives 0, so the "scan on to the next row" case never happens with
this artwork. For one head, the height varies with the shoulders by about
19 pixels for men and 12 for women, because the shoulders' chin dot decides
how high the head sits. The traveler's height is this minus up to 10 cm
(`traveler-build.md`). These numbers come from the reference script, not
from the running game.

## Checked by eye

Five faces built by `faces.py` (two random-style, two scripted including
piece 24 with palette 6, one document photo) were written to
`extracted/checks/` and looked at: each is a correctly assembled face, the
palettes recolour skin and clothes, the mirrored one is mirrored. This shows
the procedure is right in the large. It does **not** show pixel-for-pixel
equality with the game; nothing has been compared with the running game.

## Notes for the port

- The traveler's height depends on this picture, so the port must build the
  face the same way before it can fill in a height, even for a traveler
  never shown.
- Use the same truncating, non-blending draw and the same inverse formula.
- Scan for the dark face colour **before** applying the palette.
- Keep the marker order rule (reading order), not left/right assumptions.

## Not studied

- `Face.getDocImage` and `getPhotoHeadImage` (how the document photo and
  the search photos are cut and coloured), and where the head-only picture
  is used.
- `Image.copy` with a rectangle goes through `Image.paste`, which was not
  read; `faces.py` assumes a plain copy (the sheets have no partly
  transparent pixels, so a blend would give the same result).
- The PNG decoder (`format.png`); `faces.py` uses Pillow instead. The sheets
  are palette PNGs.
- `Bodies.xml` and the body images in the same folder.
