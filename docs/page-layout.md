# Drawing, part 2: how a document page is laid out (`PaperInnerVisuals`)

Studied on 2026-10-16, as part 2 of the drawing step (step 5 of
`PROGRESS.md`). Code reading, two read-only Ghidra runs for the
instructions, one constant read from the DLL, and a check of all 120 page
pictures against `Papers.xml`. **Nothing here has been compared with the
running game.**

Reference script: `scripts/reference/pages.py` (lays a page out and draws a
preview). Check: `scripts/checks/page_layout_check.py`. The file format
(`<paper>`, `<page>`, `<mark>`, inheritance) is in `papers-xml-format.md`;
how a text is laid out is in `text-drawing.md`; the random draws a page
makes are in `desk-drawing-draws.md`.

## What was read

In `decompiled/all/play_day.clean.c`: all of `play.day.PaperInnerVisuals`
(static setup, constructor, `toImage`, `getMarkFromName`,
`autoGetPageIndexForFactId`, `autoGetPageIndexWithLink`, and
`compareProximity` in outline); all of `play.day.PaperNav`
(`hasPage`, `hasPageFromId`, `getExistingPageId`, `getNextPageIndex`,
`getPrevPageIndex`, constructor); `BoothEnv.getLocalizedText`. In
`decompiled/all/data.clean.c`: `Page.getInnerImageAndMarkPositions`,
`Mark.getFactId`, `getImage`, `getRandomForcePos`. In
`decompiled/all/play_day_booth.clean.c`: `Paper.setPage` and the filer
branch of the `Paper` constructor (the two callers). `Res.getImage`.
`BoothEnv.getImage` was only listed (what it calls), not read.

The decompiler typed the mark as an `app.vis.Text`, so its field names in
the constructor are wrong; they were mapped by offset from `dump.cs`
(for example its `hostPos`, offset `0x58`, is the mark's `link`;
`field_0x24`, offset `0x34`, is `backColor`).

Checked in the instructions (`decompiled/drawing2_run1.txt`,
`DumpAssembly.java 0x180613260`; `decompiled/drawing2_run2.txt`,
`0x18060b940 0x1809f45e0`): the padding values, the wrap width, the
arguments of `getLocalizedText`, `getExistingPageId` and `hasUpgrade`, and
that `Image.copy` is called with no rectangle (a copy of the whole
picture). Constant read with `read_doubles.py`: `0x180a80b18` is 55.
The desktop value of `Layout.touchTargetExpand` was read from the existing
listing `decompiled/layout_ctor_asm.txt` (below).

## Who builds a page

`PaperInnerVisuals(boothEnv, paperDef, multiPaperIndex, pageIndex,
touchTargetExpand)` is made in two places:

- **`Paper.setPage`**, every time a paper on the desk shows a page (first
  drawn, page turned, link followed). It clamps the page index to the
  pages there are, skips forward to the first page the paper has
  (`PaperNav.hasPage`), then gives the desk item the page picture
  (`setInnerImage`, with the paper's `oddshape`) and each visual in order
  (`addInnerVisual`).
- the `Paper` constructor, for the filer envelope only (`FilerType`
  `ONLYFILER`): its page becomes the filer picture and visuals.

`touchTargetExpand` comes from the layout. **On desktop it is 0**: the
`Layout` constructor writes it only in its two portrait blocks (10 at
`0x1804993b8`, 6 at `0x18049b62a`, each followed by the portrait-only
`borderShowSnipingSurround` write), and nothing else writes the field
except `Layout`'s own by-name setters. ("Nothing else writes it" means no
store through the layout's register in the desktop block and no other
user of the field's name or hash; a store by another route would have
been missed.)

`toImage` (a copy of the page picture with every visual drawn into it at
0, 0) has no direct caller; it is reachable only by name
(`__hx_invokeField`). No by-name call to it was looked for.

## Step 1: the picture and the mark positions

`Page.getInnerImageAndMarkPositions(res, layoutShape, rand)`:

1. The picture is `assets/papers/<image>` for the shape `LANDSCAPE`,
   `image_portrait_wide` or `image_portrait_thin` for the two portrait
   shapes. Desktop is taken to be `LANDSCAPE` (**inferred** from the
   names; the shape value was not traced). `Res.getImage` returns the
   shared loaded picture, and the page works on **a copy of the whole
   picture** (`Image.copy(null)`, checked in the instructions), so the
   changes below never reach the shared one.
2. One position per mark, in file order:
   - a mark with `pos` and no `pos2`: `pos`;
   - with `pos` and `pos2`: a random point between them, two draws (x,
     then y), each cut down to a whole pixel (`desk-drawing-draws.md`);
   - **without `pos`: the next marker pixel of the mark's side** (below).
     Until one is found the position is (0, 0).
3. **Marker pixels.** The picture is scanned row by row, left to right.
   An opaque black pixel (`0xFF000000`) belongs to side 0, an opaque red
   one (`0xFFFF0000`) to side 1. The first black pixel goes to the first
   side-0 mark without `pos`, the second to the second, and so on; red
   pixels likewise for side 1. **Every** marker pixel is then painted
   over with the pixel read just before it (the one to its left; for the
   first pixel of a row, the last of the row above; for the very first
   pixel, transparent 0), whether a mark used it or not. Marker pixels
   beyond the number of marks are painted over and ignored.

`side` is only this: which marker colour a mark takes its place from. It
has no other use here.

**Checked against the pictures** (`page_layout_check.py`, run
2026-10-16): on 109 of the 120 pages the number of black pixels equals
the side-0 marks without `pos`, and on all 17 pages with side-1 marks the
number of red pixels equals them exactly (blue matches on none, which
settles that side 1 is red and that the game's pixel is `0xAARRGGBB`).
In all, 205 side-0 and 41 side-1 marks take their place from a pixel.
The 11 other pages:

- The five pages with a seal mark (`EntryPermit`, `WorkPermit`,
  `AccessPermit`, `DiplomaticAuth`, `AsylumGrant`) have one black pixel
  fewer than marks without `pos`. On all five the seal is the last such
  mark, and a seal places itself by its `emblemrect`, so it gets (0, 0)
  and nothing is shifted.
- The rulebook's documents page (`RulesInnerDocs.png`) has 13 black
  pixels for 8 marks, in a column at x 138 (y 38 to 86, every 4). Its
  marks after the first use `flow="down"`, so only the first pixel's y
  and every pixel's x matter.
- Pages with black pixels and no mark to use them: the seven tokens
  (`TokenInner*.png`, 22 to 32 pixels each), and one each in
  `EntryTicketInner.png`, `FingerprintsInner.png`,
  `EzicIntroInnerBack.png`. **These are painted over too**: in the
  tokens, black pixels of the drawing itself become the colour to their
  left, so by the code the game shows the tokens without their black
  details (preview made of `TokenArstotzka`; **not compared with the
  game**).

The Arstotzka passport, laid out with made-up values, puts the name above
the photo and the date of birth, sex, issuing city and expiry date beside
the printed labels "DOB.", "SEX", "ISS.", "EXP.", and the number at the
bottom (preview looked at).

## Step 2: one visual per mark

For each mark in file order (the constructor stops early if there are
fewer positions than marks, which cannot happen with step 1):

**Left out by its link:**

- `link="#next"`: left out if there is no next page
  (`PaperNav.getNextPageIndex` is -1);
- `link="#prev"`: left out if there is no earlier page;
- any other link: left out unless `PaperNav.getExistingPageId(link)`
  finds a page: the link may list several ids separated by commas, and the
  first one the paper has is used.

Which pages a paper has (`PaperNav`): the booth fact
`<paper>/PageMask` (its localized text). If it is empty, every page
exists. Otherwise a page exists if its id **occurs in the mask text** (a
substring test, so a mask with `region-ar` also contains `region`). The
`Transcript` has only as many pages as the booth's transcript page count.

**The mark's fact.** `Mark.getFactId`: the text or picture name without
its `$`, or `Emblem/<id>` for a seal; none for a literal. (`proxy` is not
used here; it is for inspection, `getProxiedFactId`.) If the day's rule
table has the fact id as a key (for example `Rule0` on the rule pages),
the value it maps to is used instead; otherwise the same for the day's
news renames (`News0` ..., `news-txt-format.md`). Not traced here: what
the rule table holds.

**A text mark:**

1. The string: the literal text, or for a fact
   `BoothEnv.getLocalizedText(<paper id with index>, <fact>)`: a fact id
   starting with `%` is a global fact (`Day/...` from the day's facts,
   `Game/...` and `Night/...` from the story's facts, others from the
   booth's), shown through the language table; any other is the booth
   fact `<paper>/<fact>`, as text (`fact-values.md`). **An empty string
   leaves the mark out.** A two-character `\n` becomes a line break.
2. A text in the mark's font (an unknown font stops the game with "Font
   not found"), colour `textcolor`, alignment `align`.
3. Its position:

   | `flow` | x | y |
   |---|---|---|
   | none | position x | position y + 1 - font ascent |
   | `down` | position x | `flowpad` + bottom of the last text or picture |
   | `right` | `flowpad` + right edge of the last text or picture | position y + 1 - font ascent |

   So the marker pixel (or `pos`) of a plain text is **one pixel above its
   first line's base line**. "The last text or picture" is the last one
   actually drawn; a mark left out does not move it. Before the first, both
   edges are 0.
4. Colours and box:
   - no link, `backcolor` set: a box in `backcolor` behind the text,
     `paddingX` 1 (no `paddingY`);
   - **with a link** (a button): the box in `textcolor`, **rounded**, the
     letters in `backcolor`, padding 1 on all sides. A link text without
     `backcolor` would get letters of colour 0, which are not drawn
     (`text-drawing.md`); every link text in `Papers.xml` has one, from
     its page or itself (checked with `pages.py`).
5. `wrap` not 0: several lines, wrapped at `wrap` pixels.
6. A string starting with `@`: the `@` is removed and the letter and box
   colours are swapped (no data string starts with `@` as far as
   `Papers.xml` goes; fact values were not searched).
7. **Touch padding** (phone and tablet only, since `touchTargetExpand` is
   0 on desktop): a fact text narrower than 55 pixels gets n spaces, the
   smallest n with 55 - width <= n x space width: after it for LEFT,
   before it for RIGHT, n / 2 (rounded down) on each side for CENTER.
8. Alignment moves x: CENTER `floor(x - width / 2)`, RIGHT
   `floor(x - width)`. Then the right edge and bottom for the next flow
   are x + width and y + height.

**A picture mark:**

1. A picture named `RulesTab...` is left out unless the story has the
   upgrade `RULEBOOK_TABS`.
2. The picture: for a literal, `Mark.getImage`: `BLANK:WxH` is a
   transparent picture of that size (`BLANK:` without a match, 10 x 10);
   anything else is `assets/papers/<name>`, scaled by `scale` when it
   differs from 1 (`Image.transformed`, not read). For a fact,
   `BoothEnv.getImage(<paper id with index>, <fact>, scale, textcolor,
   backcolor)` (photos, fingerprints, contraband, seals; not read). No
   picture leaves the mark out.
3. Position: the mark's position; `flow` down or right as for a text
   (y or x only; no ascent); then the same alignment rule with the
   picture's width; then the edges for the next flow.

**A seal mark** (`emblem`): drawn only if the seal's status
(`BoothEnv.getEmblemStatus`) is not `NONE`. The picture is
`EmblemLib.getEmblemImage(rand, emblem id, the traveler's nationality,
ANY_VALID if the status is VALID, else ANY_INVALID)`, placed at
`floor(rect x + (rect w - picture w) x r1)`,
`floor(rect y + (rect h - picture h) x r2)` inside `emblemrect`, with two
more draws r1 and r2, and drawn at **half opacity** (its tile's alpha
0.5). It does not move the flow edges. (The draws are those of
`desk-drawing-draws.md`.)

**Then, for any mark drawn:** `clipheight` not 0 cuts the visual to the
rectangle (0, 0, 100000, `clipheight`) relative to it; the visual is named
`MARK#<index of the mark in the page>` and added in mark order.

## Finding marks and pages

- `getMarkFromName(paper, page, name)`: a name `MARK#n` gives mark n of
  that page (any other name gives none). The static list `kMarkNames`
  holds 20 names `MARK#...` whose numbers the decompiler dropped;
  whatever they are, a name not in the list is parsed for its number, so
  the result is the same.
- `autoGetPageIndexForFactId(fact)`: the first page the paper has with a
  mark that is not left out by its link, whose fact (after the rule and
  news renames) is the given one, and that would draw something (a
  non-empty text, a picture, a seal whose status is not `NONE`).
  `autoGetPageIndexWithLink(link)`: the first page with a mark whose
  `link` is exactly the given one. Both are used by `BoothEnv` for
  inspection.
- `compareProximity(point, ra, rb)` (read in outline): decides which of
  two mark rectangles a point is nearer, for picking a mark under the
  cursor (`DeskItem.getInnerVisualAt`, `Paper.getInspectable`). Not
  needed for the layout; its constants were not read.

## Preview and checks

`page_layout_check.py` (run 2026-10-16): the marker counts above
(`problems: none`); every page laid out with fact names as values, every
page existing and the tabs upgrade on: 197 texts, 231 pictures, 5 seals.
One literal text reaches past its page in that setting: the rulebook's
documents list with all eight entries, whose last button ("Vaccine
Cert.") ends at y 162 on a 160-pixel page. In the game the list only
shows the documents of the day's page mask, so all eight are never
expected together (**inferred**; which masks occur was not checked).

Previews looked at (`pages.py --png`): the Arstotzka passport with made-up
values, the rulebook's contents page (five rounded buttons with dots,
"next" arrow, no tabs without the upgrade), the documents page with four
documents, the Arstotzka token before and after the painting over.

## Notes for the port

- Read the marker pixels from the page pictures exactly as above, on a
  copy, and paint them over; do not hand-place these marks.
- Keep the one-pixel base line offset (position y + 1 - ascent).
- The token pictures lose their black pixels by this rule; whether the
  port should copy that is a design question (it is what the code does;
  not seen in the game).
- `touchTargetExpand` is 0 on desktop: no padding of short values.

## Not studied

- `BoothEnv.getImage` (the fact pictures: photos, fingerprints,
  contraband, seals), `Image.transformed` (scaled pictures), and
  `EmblemLib.getEmblemImage`.
- What the day's rule table maps (`Rule0` ...) and where the page masks
  are set.
- The desk side: `DeskItem.setInnerImage` and `addInnerVisual` (how the
  page and its visuals are put on screen), and inspection.
- `compareProximity` in detail.

## Things to watch in the game

None was done.

1. A token on the desk: are its black details there? By the code they
   are not.
2. The rulebook's contents page: dark rounded buttons with light letters,
   one pixel of box around each word.
3. A passport: the date of birth's base line one pixel below the marker
   (compare a screenshot with the preview at the same scale).
