# The night screen's family pictures (the screens, part 10)

Everything the night screen shows around the budget: each family
member's status badges and name, the apartment class, the column of
tokens, the passports and the upgrades. The rest of the night screen is
in `screens.md`, part 1; the rules that decide the family's state are in
`night.md`.

Studied on 2026-10-16 by code reading, plus a check of the six picture
files. **Not run in the game.** The only comparison with the real screen
is the description of one screenshot written in `screens.md`, part 1
(the picture itself is not kept); it agrees, see "Compared with the
screenshot" below.

## What was read

From `decompiled/all/play_night.clean.c`, read in full:

| Class | Functions |
|---|---|
| `play.night.FamilyVisuals` | the constructor `__hx_ctor_play_night_FamilyVisuals` `0x18074cdc0` (about 1,550 lines; all three layout branches, the desktop one line by line), the static constructor `0x180750750`, `hideTopDivider` `0x180750c60` |
| `play.night.FamilyVisualsDim` | its constructor `0x18021e180` (the sizes) |
| `play.night.Family` | `makeVisuals` `0x180758cd0`; the fact names and defaults in its constructor (already in `night.md`) |
| `play.night.FamilyMember` | `get_emotionFlags` `0x18074ca00` (read again; agrees with `night.md`) |
| `play.StoryState` | `getValidUpgrades` `0x1807f0990`, the lists in its static constructor `0x1807efc00`, and where the constructor picks the upgrade set by platform |

Checked in the machine instructions (`decompiled/part10_run1.txt`,
`DumpAssembly.java 0x18074cdc0`), because the decompiler dropped or
mistyped them: the text under each badge row is the member's
`statusName` (field `0x18`); it is centred (`Align` value 1); its fixed
width is the whole part of the step's x; the passport cover is made with
`Image.transformed(0, 0.5)`, so turned by 0 and halved; the gap before the
passport count is 1.0; and the empty-token test asks the map for place
number 0 to 6 in turn. Number constants were read with `read_doubles.py`.

Not read: `app.vis.Text` (so where a text's position puts its letters),
`app.vis.Sprite` and `app.vis.Fill` beyond their constructors' arguments,
`Image.transformed`'s scaling method.

## In short

- `BudgetEnt` calls `Family.makeVisuals(layout)` while it builds the night
  screen (`screens.md`, part 1, step 4). That builds one `FamilyVisuals`,
  which is only a list of pictures and texts (`visuals`) in a fixed order.
  Nothing in it moves, takes clicks or changes after it is built. **No
  random draws.**
- The constructor has three branches by layout shape. **Desktop is
  `LANDSCAPE`**, the first branch, which only sets fixed positions. The two
  portrait branches compute positions from the screen size, put the family
  in a row at the bottom, scale the badges on phones, and add one or two
  thin divider lines (`topDividerFill`). **On desktop there is no divider**,
  so `hideTopDivider` does nothing there.
- Sizes (`FamilyVisualsDim`, scale 1 on every layout that passes none,
  which includes desktop): token 29, apartment 40 x 30, upgrade 45 x 15,
  passport 30 x 40, status badge 30, badge overlap 2 (`kMoodIconPaddingX` =
  -2). `kSleepButtonHeight` (32) is not used by this constructor.

## What is placed, in order (desktop)

The screen is 570 x 320. All positions below are what the code writes
into each picture's position. How a sprite is drawn from its position was
not read; the preview in `nightpics.py` takes it as the top-left corner,
which gives the arrangement the screenshot showed.

### 1. The apartment class

`ApartmentClass.png` (160 x 30) is four pieces of 40 x 30, side by side:
"8 CLASS", "7 CLASS", "6 CLASS", "5 CLASS". `Night/Apartment` `C5` gives
the fourth, `C6` the third, `C7` the second, anything else (normally `C8`)
the first. Placed at **(500, 9)**: 520 minus half its width.

### 2. Each family member

For every member of `Family.members`, **dead ones too** (wife, son,
mother-in-law, uncle, then the niece if adopted; `night.md`), member
number i (from 0):

- The row's centre is x = **520**, y = c0 + 43 i, where
  c0 = floor(160 - ((n - 1) x 43 + 30) / 2) and n is the number of
  members. Four members: c0 = 80, so centres at 80, 123, 166, 209. Five:
  c0 = 59.
- **Badges.** `get_emotionFlags` gives a set of flags (`night.md`, "The
  family"): dead alone; otherwise hungry, cold, very sick or sick, the
  mood, and "ok" when none apply. One badge per flag, from
  `Emotions.png` (30 x 240: eight 30 x 30 badges top to bottom, HAPPY,
  OK, SAD, COLD, SICK, VERYSICK, DEAD, HUNGRY), **in that order**, so
  COLD comes before SICK and HUNGRY is always last. With k badges the row
  is 28 k + 2 wide; badge j sits at x = centre - floor((28 k + 2) / 2) +
  28 j (rounded down), y = centre y - 15. So neighbouring badges overlap
  by 2 pixels.
- **The name.** A text in the font `regular`, colour `0x556855`, centred,
  with word wrap and several lines allowed, fixed width 0 (the step's x
  on desktop is 0), saying the member's `statusName`: the texts
  `family_<member>_status` ("Wife", "Son", "Mother-in-law", "Uncle",
  "Niece"). x = floor(centre - text width / 2); y = floor(centre y + 15)
  - the font's ascent + its capital height. What y means to
  `app.vis.Text`, and whether a fixed width of 0 means "no wrapping" as it
  does in the line breaker (`fonts.md`), was not read.

### 3. The tokens

Seven places in a column: place p at **(25, 60 + 31 p)**, so y 60 to 246.

- The tokens shown are `Night/TokenIds` followed by the day's own token
  ids (`Summary.tokenIds`), joined as they are (not de-duplicated).
- A token's **place** is its position in `Facts.xml`'s
  `<misc tokenOrder="Impor Antegria Obristan Arstotzka Republia Kolechia
  UnitedFed">`. Its **picture** is its position in the static list
  `imageTokenIds` = `Empty Obristan UnitedFed Republia Antegria Impor
  Kolechia Arstotzka`, a piece of `Tokens.png` (29 x 232: eight 29 x 29
  pieces top to bottom; the first is the dotted empty circle).
- A token that is in neither list is skipped. One in `imageTokenIds` but
  not in `tokenOrder` gets a picture that is never added (none exists in
  the data: `night_pictures_check.py`).
- First every place with no token gets the empty circle (places 0 to 6 in
  order), then the tokens' pictures are added, in the order of the list.
- The order the tokens are collected in the story (`save-format.md`, the
  debug jump's facts: Impor day 5, Antegria 6, Obristan 7, Arstotzka 17,
  Republia 24, Kolechia 26, UnitedFed 31) is the same as `tokenOrder`, so
  the column fills from the top down.

### 4. The passports

Placed at **(76, 158)**, 30 x 40.

- If `Night/HaveFamilyPassports` is 1 (the default; `TakeFamilyPassports`
  in `Nights.txt` sets it to 0): the count is the number of living members
  + 1, and the picture is `papers/PassportOuterArstotzka.png`.
- Otherwise the count is `Night/NumEscapePassports` and the picture is
  `papers/PassportOuterObristan.png`.
- Both covers are 60 x 80 and are **halved** to 30 x 40 when the sprite is
  made (`Image.transformed(0, 0.5)`).
- If the count is 0: the dotted outline `NightPassportFrame.png` (30 x 40)
  instead, and no text.
- Otherwise a text `x<count>` in `regular`, colour `0x556855` with the
  Arstotzkan passports and **red `0x8a0c0c`** with the Obristan ones
  (`kObristantFamilyStatusColor`). x = 76 + the cover's width + 1;
  y = 158 + the cover's height - the text's height (the text's bottom on
  the cover's bottom; `Text.height` not read).

### 5. The upgrades

One place per upgrade the platform offers (`StoryState.getValidUpgrades`).
**Desktop offers four**, in this order: `INSPECT_HOTKEY`,
`STAMPBAR_HOTKEY`, `RULEBOOK_TABS`, `INSPECT_DOUBLECLICK`. (Tablet:
`BOOTH_MULTITOUCH`, `RULEBOOK_TABS`; phone: `RULEBOOK_TABS`. The platform
picks the set when the story state is made: desktop, tablet, phone.)

Place i at **(69, 205 + 18 i)**, so y 205 to 259. `Upgrades.png` (45 x 90)
is six 45 x 15 pieces top to bottom: an empty dotted box, then
`INSPECT_HOTKEY` (SPACE), `STAMPBAR_HOTKEY` (TAB), `RULEBOOK_TABS` (book
and bookmark), `INSPECT_DOUBLECLICK` (mouse), `BOOTH_MULTITOUCH`. A place
shows the upgrade's own piece if the story has it (`hasUpgrade`), the
empty box if not. On desktop the order of the places is the order of the
pieces.

## Desktop positions at a glance

| Item | Position | Size |
|---|---|---|
| Apartment class | (500, 9) | 40 x 30 |
| Member i's badges | centred on x 520, top at c0 + 43 i - 15 | 30 x 30 each, 28 apart |
| Member i's name | centred on x 520, under the badges | font `regular` |
| Token place p (0 to 6) | (25, 60 + 31 p) | 29 x 29 |
| Passports | (76, 158), count text at x 107 | 30 x 40 |
| Upgrade place i (0 to 3) | (69, 205 + 18 i) | 45 x 15 |

The budget rectangle is x 185 to 385 (`screens.md`, part 1), so the left
column and the right column both stay clear of it.

**Predicted, not seen:** a member with four badges (in the data only the
son gets a mood, through `MakeSonHappy` / `MakeSonSad`, the only two
places in `Family.applyOp` that set one; with hungry, cold and sick that
is four) gives a row 114 wide from x 463, whose last badge ends at 577, past
the screen's right edge (570). Three badges end at 563.

## Compared with the screenshot

`screens.md`, part 1 noted what one screenshot of night 3 of the user's
replay showed of these pictures, before they were read: "on the right,
one row per living member with round badges (COLD, SICK, HUNGRY) and the
name under them; top right, the apartment class ("8 CLASS"); on the left,
a column of seven dotted circles, a booklet picture marked "x5", and four
dotted rectangles."

Each part matches the reading: rows down the right at x 520, badges in
the flag order with the name under them, `C8` at the top right, seven
empty token places on day 3 (the first token comes on day 5), the
Arstotzkan passports with 4 living + 1 = 5, and desktop's four upgrade
places, all shown as empty boxes (so none was bought by then; not checked
against that save). **How strong:** a description, not measurements; no
position was measured, and the picture is not kept. A night with a dead
member, a token, an upgrade, five members or the Obristan passports has
not been seen.

## For the port

- Build the list once when the night screen opens; nothing changes after.
- Use the desktop positions above. The portrait branches and the divider
  are not needed.
- The reference `scripts/reference/nightpics.py` lists every item with
  its picture piece and position, and can render the pictures (not the
  texts) for a given night:

      python -I scripts\reference\nightpics.py extracted\art\assets list demo
      python -I scripts\reference\nightpics.py extracted\art\assets render demo out.png

  `demo` is a made-up night (four members, some badges); a JSON file with
  the same fields can be given instead (see the script's header).
- `scripts/checks/night_pictures_check.py` checks that the six pictures
  divide into the pieces the code cuts and that every `tokenOrder` name
  has a piece (result on 2026-10-16: `0 problems`).

## Not studied

- `app.vis.Text`: where the names and the passport count really sit, and
  whether a fixed width of 0 turns wrapping off.
- How a sprite is drawn from its position (taken as its top-left corner in
  the preview), and how `Image.transformed` halves the passport covers
  (which pixels it keeps).
- The portrait branches were read for their structure only, not their
  numbers (not needed for a desktop port).

## Things to watch in the game

None of these is needed before the port is built; they guard against a
misreading, and are cheapest with the port's night screen next to the
game's.

1. The badge order on a member with several flags (COLD before SICK,
   HUNGRY last) and the 2-pixel overlap.
2. A night after day 5: the Impor token in the top place, the other six
   empty.
3. A night with an upgrade bought: its piece in its place, the others
   empty.
4. A dead member: still a row, with the DEAD badge only; the passport
   count one lower.
5. After `TakeFamilyPassports`: the Obristan cover with a red count, or the
   dotted frame when the count is 0.
6. Five members (after the niece): the rows start higher (c0 = 59).
7. The son with a mood and three other flags: does the fourth badge run
   off the right edge?
