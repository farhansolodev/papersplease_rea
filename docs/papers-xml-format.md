# Papers.xml: every document, page and mark

Studied on 2026-10-12. Source: `extracted/art/assets/data/Papers.xml` and the
decompiled loaders, each read in full: `data.PaperDefLib` constructor
(`0x18060ded0`), `data.PaperDef` constructor (`0x180610110`) and `getReveal`,
`data.Page` constructor (`0x18060a1e0`), `data.Mark` constructor
(`0x1808a4d40`), `isValid`, `getFactId`, `getProxiedFactId`,
`data.SoundsDef` and `data.CarouselGroupDef` constructors,
`PaperDefLib.find`, `getCarouselForceSortOrder`, `app.vis.Point.parse`,
`app.vis.Rect.parse` and `FactLib.getPaperStay`.

Everything here is confirmed in the code unless marked **inferred**. Every
attribute name and value in the file was then checked against what the code
accepts (results at the end).

## Shape of the file

```
<papers>
  <sounds .../>          5   named sets of sound effects
  <paper ...>           68   one document type
    <page ...>         120   one side or spread of it
      <mark .../>      509   one thing drawn on the page
  <ink .../>             2   stamp ink definitions
  <carousel>             1
    <group .../>         7   papers shown together in a picker
    <forceorder .../>    4   sort order overrides
```

The file is well-formed XML. Its 43 comments are section labels, two notes
("wrap to enable multiline"), and three switched-off items: a mark on the
transcript, the paper `EzicColor`, and a bulletin page `diplotut`.

Load order in the game: all `<sounds>`, then all
`<paper>`, then `<ink>`, then the carousel.

On desktop the file is used as-is. On phone a "mogrifier" object rewrites
parts of it before loading (`MogrifierPhone.mogrifyXml`); not studied.

## Value formats

- **Booleans**: only the exact text `true` counts as true.
- **Point**: two numbers separated by one space, `x y`. Anything else gives
  `0 0`.
- **Rectangle**: four numbers separated by spaces, `x y w h`. Anything else
  gives `0 0 100 100`.
- **Colour**: `0xRRGGBB`. The game forces it fully opaque (`| 0xFF000000`).

## `<paper>`

| Attribute | Field | Default | Notes |
|---|---|---|---|
| `id` | `id` | required | 62 distinct ids; `Passport` appears 7 times, once per nation |
| `nation` | `nation` | empty | |
| `outer` | `outerImageName` | required | Image of the closed/outside document |
| `mount` | `mountImageName` | none | 5 papers |
| `trade` | `tradeForPaperId` | none | 1 paper (`Fingerprints`) |
| `fromtraveler` | `fromTraveler` | false | |
| `stampable` | `stampable` | false | |
| `inspectable` | `inspectable` | **true** | |
| `rotate` | `rotateOuter` | **true** | |
| `oddshape` | `oddShape` | false | |
| `dock` | `hasDockPoint` | false | |
| `canpinch` | `canPinch` | false | |
| `visacenter` | `visaCenter` | none | Point |
| `sounds` | `sounds` | `paper` | Id of a `<sounds>` set |
| `reveal` | `reveal` | see below | |
| `canconfiscate` | `filerType` | see below | |
| `font`, `textcolor`, `backcolor` and other mark attributes | | | Not paper fields: they are defaults for every mark in the paper (see inheritance) |
| `fontlinespacing` | | | **Not used.** The name does not exist in the game's code. On `EzicNote` only |

Derived fields:

- **`reveal`** (how the paper appears). With the attribute: `printbottom`,
  `spitfromright`, `infiler`, `printtop` map to the enum values of the same
  name; text starting with `ondesk` becomes `ONDESK(x, y)` from the pattern
  `ondesk:(\d+),(\d+)` (or `0, 0` if it does not match); anything else,
  including the `fromslot` used in the file, becomes `FROMSLOT`. Without the
  attribute: `DOCKED` if `dock` is true, otherwise `FROMSLOT`.
- **`filerType`**: `ONLYFILER` if the id is exactly `FilerEnvelope`;
  otherwise `CANFILER` if `canconfiscate` is true; otherwise `NONE`.
- **`stay`** (how long the paper is kept) does not come from this file. It is
  the `stay` value of the document definition with the same id in
  `Facts.xml`: `day`, or any paper with `dock`, gives `DAY`; `game` gives
  `GAME`; otherwise `NONE`.

Only child elements named `page` are read.

## `<page>`

| Attribute | Field | Default |
|---|---|---|
| `id` | `id` | `none` |
| `image` | `defaultInnerImageName` | required |
| `image_portrait_wide` | `portraitWideInnerImageName` | same as `image` |
| `image_portrait_thin` | `portraitThinInnerImageName` | same as `image` |
| mark attributes (`backcolor`, `wrap`, `align`) | | defaults for the marks on this page |

Only child elements named `mark` are read. A mark with none of `text`,
`image` or `emblem` is dropped.

Page ids are what `Days.csv` refers to in its `BPAGES` row (for example
`guntut`, `filertut`, `criminals` are pages of the bulletin).

## `<mark>`

The kind is decided by the first of these attributes present:

| Attribute | Kind | Stored in | Count |
|---|---|---|---|
| `text` | `TEXT` | `text` | 197 |
| `image` | `IMAGE` | `imageName` | 307 |
| `emblem` | `EMBLEM` | `emblemId` | 5 |

**Fixed text versus generated values.** `Mark.getFactId`: a text or image
value starting with `$` is not literal. The rest of it is the id of a *fact*
whose value is filled in for each traveler (166 of 197 text marks, 75 of 307
image marks). An emblem mark's fact id is `Emblem/` plus its emblem id. If
`proxy` is set, that fact id is used instead (`getProxiedFactId`, for
inspection; drawing a page uses the mark's own fact id and ignores
`proxy`: `page-layout.md`, 2026-10-16. The nine `proxy` marks are
transparent `BLANK:` pictures on the rulebook's document pages).

| Attribute | Field | Inherited | Default with nothing to inherit |
|---|---|---|---|
| `align` | `textAlignment` | yes | `LEFT`. Accepts `left`, `center`, `right` |
| `flow` | `flow` | yes | `NONE`. Accepts `down`, `right` |
| `font` | `fontName` | yes | `regular` |
| `textcolor` | `textColor` | yes | 0 |
| `backcolor` | `backColor` | yes | 0. The value `0` means none |
| `wrap` | `wrapWidth` | yes | 0 |
| `flowpad` | `flowPad` | yes | 0 |
| `side` | `markSide` | yes | 0 |
| `scale` | `imageScale` | yes | 1.0 |
| `emblemrect` | `emblemRect` | yes | `0 0 100 100` |
| `inspectable` | `inspectable` | yes | see below |
| `link` | `link` | no | none |
| `pos` | `forcePos` | no | none (Point) |
| `pos2` | `forcePos2` | no | none (Point) |
| `proxy` | `proxyFactId` | no | none |
| `clipheight` | `clipHeight` | no | 0 |
| `stamplinksize` | `stampLinkSize` | no | none (Point) |
| `format` | | | **Not read by the paper loaders.** The word is only used when loading `Facts.xml`. 8 marks, all `120 720` |
| `section` | | | **Not read.** No code looks it up. 5 marks |

**Inheritance.** The paper element is itself read as a mark, giving
paper-wide defaults. Each page element is read as a mark on top of those,
giving page defaults. Each real mark then inherits from its page.

**`inspectable`**: the attribute if present; otherwise the inherited value;
otherwise true. In all cases a mark with a `link` is not inspectable.

## `<sounds>`

`id`, and five optional sound names: `dragstart`, `dragstop`, `drop`,
`totop`, `turnpage`. Ids in the file: `banner`, `metal`, `paper`, `plaque`,
`timebomb`.

## `<ink>`

`id`, `datefont`, `datepos` (Point), `datecolor` (colour). Stored as a loose
object keyed by id.

## `<carousel>`

- `<group id papers tight>`: `papers` is a comma-separated list of paper
  ids; `tight` is a boolean. Each listed paper id maps to its group.
- `<forceorder id val>`: a whole number sort order per paper id. A paper
  with no entry uses the entry whose id is `DEFAULT`.

What the carousel is in play is not studied.

## Looking a paper up

`PaperDefLib.find(id, nation)` returns the first paper whose id matches and
where the requested nation is empty, or the paper's nation is empty, or the
two are equal. Papers are stored in **reverse file order** (each is added to
the front of the list), so asking for `Passport` with no nation returns the
last one in the file. Ids `Booth`, `Traveler` and `Speech` are expected not
to be found and are not reported as errors.

## Cross-check of the file against the code

- No `<paper>` has children other than `<page>`; no `<page>` has children
  other than `<mark>`.
- Every boolean attribute in the file is written `true` or `false`.
- Every `reveal`, `align` and `flow` value is one the code handles
  (`fromslot` by falling through to the default).
- All 282 point values are `number number`; all rectangles have 4 numbers;
  all 81 colours are `0xRRGGBB` or `0`.
- Every `sounds` reference names an existing set, and `paper` exists.
- Every paper id in a carousel group is a defined paper. `DEFAULT` exists.
- No mark has both `text` and `image`. No mark is of kind none.
- Three attributes in the file are never read: `fontlinespacing`, and on
  marks `format` and `section`.

## Not studied

- `MogrifierPhone` and `MogrifierTablet` (platform-specific rewrites).
- (How marks are laid out and drawn, including what `flow`, `side`,
  `link` and `pos2` do, was listed here; read on 2026-10-16,
  `page-layout.md`. In short: a mark without `pos` takes its place from
  a marker pixel in the page picture, black for side 0, red for side 1.)
- (Studied since: the fact system that supplies `$` values, and
  `Facts.xml`, in `facts-xml-format.md` and `fact-values.md`.) Note:
  `Facts.xml` is **not well-formed XML**; a strict parser stops at line 96,
  so the port will need a lenient reader or a clean-up step.
- (How the language packs override text was listed here; read on
  2026-10-16, `language-pack.md`: the pack can replace `text` attributes
  of `page/mark` without `$`, context `paper:<id>`. In English it changes
  nothing in this file. The bulletin page `diplotut`'s picture,
  `BulletinInnerDiploTut.png`, exists only in the language packs.)
- No reader has been written for the port, so none of this is tested end to
  end.
