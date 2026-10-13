# Emblems.xml and Bodies.xml

Studied on 2026-10-13. `Emblems.xml` describes the seals printed on permits
and diplomatic papers. `Bodies.xml` describes the hidden contraband shown in
the body-search photo.

Functions read in full: the `data.EmblemLib` constructor, `getEmblemImage`
and its two search helpers; the `data.BodyLib` constructor,
`getTypeMatches`, `getBodyId`, `getBodyImage`, `getContraband`,
`getRandomNonBombContrabandType`. Read in part: `EmblemLib.getValidImage`.

Everything here is confirmed in the code unless marked otherwise.

## Emblems.xml

```xml
<emblem id="MinistryOfAdmission" file="EmblemsMOA.png" count="9" valid="2" size="35 35" canrotate="false"/>
<emblem id="DiplomaticAuth" count="6" valid="2" size="42 42" canrotate="true">
	<nation id="Kolechia" file="EmblemsDipKolechia.png"/>
	...
</emblem>
```

Each emblem is a **sheet** picture cut into equal cells of `size`, read left
to right, top to bottom. The first `valid` cells are genuine emblems; the
cells after them, up to `count`, are wrong ones.

- An `<emblem>` with a `file` gives one set. One without gives one set per
  `<nation>` child, each with its own sheet and the emblem's `count`,
  `valid` and `size`.
- **`canrotate` is not read**: the loader does not ask for it and the word
  is not among the code's strings.

Picking a picture (`getEmblemImage(rand, id, nation, which)`): the set with
that id and nation is used (or, failing that, the first set with that id).
Then:

| Wanted | Cell number | Draws |
|---|---|---|
| any valid | `floor(valid * r)` | one |
| any invalid | `floor(valid + (count - valid) * r)` | one |
| a given cell | that number | none |

The cell is cut from the sheet at column `n mod columns`, row
`floor(n / columns)`, where `columns` is the sheet width divided by the cell
width.

`getValidImage(id, backColor)` builds one picture showing all the valid
emblems of a set in two columns on a coloured background (for the rulebook,
inferred from the name and layout; its exact spacing was not worked out).

Which random generator is passed in, and when the pick happens, is in the
document-drawing code, which is not studied. The fact value only says
`VALID`, `INVALID` or `NONE` (`fact-values.md`).

## Bodies.xml

```xml
<loc id="back" rect="31 39 40 45"/>
<contra type="gun" loc="back" file="Contra-Gun0.png">
	<offset body="F1" val="-2 -3"/>
</contra>
```

- `<loc>`: a named rectangle on the body picture (x, y, width, height).
- `<contra>`: one contraband picture, its type, and the place it is worn.
- `<offset>`: a small shift of that contraband for one body shape.

**Which body** (`getBodyId(male, bmi)`): `M` or `F`, then `0` if the body
mass index is below 21, `2` if above 24, otherwise `1`. The picture is
`assets/faces/Body<id>.png` unclothed or `Body<id>c.png` clothed.

**Which contraband** (`getContraband(rand, body, types, places)`):

1. Keep the `<contra>` entries whose type fits `types` and whose place is
   named in `places` (either test is skipped when its argument is absent).
2. Pick one at random (one draw). None gives nothing.
3. Take the place's rectangle and the entry's offset for this body, or
   `0 0` when there is none. The piece is **cut from the contraband picture
   at the rectangle moved back by the offset, and pasted on the body at the
   rectangle itself**.

**Type test** (`getTypeMatches`): if `types` starts with `$`, the rest must
appear in the entry's **file name** (so `$Gun0` means exactly
`Contra-Gun0.png`). Otherwise the entry's type must appear in `types`
(so `types` can list several). This settles the open question about the one
`contrabandTypes` value written `$Gun0` in `Travelers.txt`
(`traveler-build.md`).

**Random type for a traveler** (`getRandomNonBombContrabandType`): one draw
from the list of the types of all non-bomb entries, repeats included
(`traveler-build.md` uses this as the default contraband type).

## Check against the data files

`scripts/checks/emblems_bodies_check.py` (run 2026-10-13):

- Emblems: 8 sets (2 ministries, 6 nations). Every sheet exists and divides
  evenly: the ministry sheets are 140x140 with 35x35 cells (16 cells, 9
  used), the diplomatic ones 84x126 with 42x42 cells (6 cells, all used).
  Modelled picks stay in range: Ministry of Admission valid cells 0-1 and
  invalid 2-8; Ministry of Labor valid 0-3 and invalid 4-8; diplomatic
  valid 0-1 and invalid 2-5. The three emblem ids named in `Facts.xml`,
  `Papers.xml` and `Errors.txt` are defined, and every nation in
  `Facts.xml` has a diplomatic sheet.
- Bodies: 3 places, 12 contraband pictures (3 each of gun, knife, bomb,
  drugs; 9 worn on the back, 3 on a leg), 50 offsets. All six body pictures
  exist clothed and unclothed (200x200); the contraband pictures are
  100x200. Body `M1` has no offsets at all, so it always uses `0 0`. No
  cut-out reaches outside its contraband picture for any body.
- `contrabandTypes` values in `Travelers.txt`: `$Gun0` (one picture), `bomb`
  and `drugs` (three each). All match something.
- The random non-bomb type is drawn from 9 entries: gun, knife and drugs
  three times each, so each is equally likely.

## Notes for the port

- Emblem validity is a matter of cell number, not of anything in the
  picture.
- The contraband cut-and-paste uses the offset only for where to cut.

## Not studied

- The drawing side: how the search photo is composed (`SearchPhoto`, front
  and back views in the 200-wide body picture), how emblems are stamped on a
  document, and which random generator those picks use.
- `EmblemLib.getValidImage` in detail.
- Nothing here has been compared with the running game.
