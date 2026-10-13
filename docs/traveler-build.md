# How the traveler (the person) is built

Studied on 2026-10-13. This is step 6 of `traveler-creation.md`: turning a
traveler specification into a person with a face, name, height, weight, id
number and fingerprints. It runs once per traveler, before any document is
put on the desk.

Functions read in full: the `play.day.Traveler` constructor (`0x180969140`)
and its small methods (`makeRandomIdNumber`, `invalidateIdNumber`,
`getBirthDate`, `get_heightInCm`, `get_hasBomb`, `get_isSpecial`,
`get_specialEnterRight`, `addWantPaperId`, `addRejectPaperId`,
`setNoFilerPaperId`, `canGivePaper`, `getResponseRunOps`);
`FaceSpec.fromString`, `toString` and its static values; `FaceCycler`
(constructor, `makePieces`, `getNextFaceSpec`); `FaceLib.makeFace` and
`getMetadata`; `FaceMetadata.isOkForConfusingGender`;
`Face.get_heightInMeters` and its static values; `TravelerName`
(constructor, `randomize`); `NameCycler` (constructor, `get`, `load`,
`save`); `FingerprintCode` (constructor, `randomize`, `makeRandomSingle`);
`app.ShuffledSequence` (constructor, `makeBasic`, `makeReshufflingOnLoop`,
`getNext`, static value); `ArrayUtil.getShuffledWithMaxSeparation` and
`getRandomItem`; `Criminal.selectRandom`, its filter and `getFace`;
`BodyLib.getRandomNonBombContrabandType`; `ErrorLib.findError`;
`app.Num.lerpScale`. Dropped arguments were recovered from the raw
instructions: the six variable names the decompiler left out, the numeric
constants, the lookup keys in `getMetadata`, and one substring length in
`invalidateIdNumber`.

Everything here is confirmed in the code unless marked otherwise.

## Three sources of randomness

| Source | Used for | Notes |
|---|---|---|
| The booth's generator (`BoothEnv.rand`, `traveler-creation.md`) | Everything in "Order of draws" below | Shared with the error maker |
| The **face cycler** | Which face pieces and colours a random face gets | Its own generators. Lives on the run, so it continues from traveler to traveler and day to day |
| The **name cycler** | Which name a traveler gets | Its own generators. Its position is **saved** in the encrypted store under `names` and continues across play sessions |

So a traveler's face and name do not depend on the day's seed but on how
many faces and names were handed out before. Both cyclers are created at
start-up from the launch's master seed (`run-and-seeds.md`).

## What is copied from the specification

From the specification's variables (set by `Travelers.txt`, see
`travelers-txt-format.md`):

| Variable | Becomes | Rule |
|---|---|---|
| `nation`, `purpose`, `job`, `district`, `duration`, `issuingCity`, `contrabandTypes`, `special` | the same-named property (`nation` becomes `nationality`) | copied as text, missing stays missing |
| `forceDeny`, `slow` | true/false | true only if the value is exactly `true` |
| `canDetain` | true/false | **true when missing**, otherwise true only if `true` |
| `leaveDir` | `customLeaveDir` | copied |
| `want` | a "wanted paper" pattern | a case-insensitive regular expression |
| `gender` | `male` | true only if exactly `M` |
| `face`, `name`, `idNumber`, `genderForced` | see below | |

Also copied: the specification's id, starting papers and custom fact
groups; its response lines are wrapped into one "run steps" operation.

## Order of draws from the booth's generator

1. **Number of vaccines**: one draw `r`; 3 if `r <= 0.5`, otherwise 2.
2. **Error override**: if the specification has a custom error, it replaces
   the error passed in. No draw.
3. **Contraband type**, only if `contrabandTypes` is missing: one draw, a
   pick from the `type` of every `<contra>` in `Bodies.xml` that is not
   `bomb`, duplicates kept (9 entries today: gun, knife, drugs three times
   each).
4. **Wanted paper**: no draw.
5. **Scripted face**, only if `face` is set: `FaceSpec.fromString` (below)
   draws once for each part that is missing or `*`.
6. **Gender**: from `gender`. No draw.
7. **Special errors**, looked for in the error's id:
   - contains `Traveler-ConfusingGender`: one draw `r`; the **name** will be
     of the opposite gender if `r > 0.5`.
   - otherwise, contains `Traveler-Criminal`: pick a criminal
     (`Criminal.selectRandom`, below): no draw if a criminal is reserved for
     this traveler, otherwise one draw if there is any candidate. If none is
     found, **the traveler gets no error**. (`makeNewTraveler` applies the
     error as the traveler holds it after this step.)
8. **Face and name**: from the cyclers, no booth draws (below).
9. **Id number**, only if `idNumber` is missing: ten draws
   (`makeRandomIdNumber`).
10. **Fingerprints**: five draws, plus redraws (below).
11. **Height**: one draw.

Then weight is computed; no draw.

## The face

- **Scripted** (`face` set): used as given (parts filled in randomly where
  missing, step 5).
- **Criminal** (step 7 found one): the criminal's face. The traveler's
  gender becomes that face's gender.
- **Confusing gender**: faces are taken from the face cycler **for the
  opposite gender**, repeatedly, until one whose head, eyes and nose/mouth
  pieces are all marked as able to pass for the other gender
  (`isOkForConfusingGender`). Each try advances the face cycler.
- **Otherwise**: the next face from the face cycler for the traveler's
  gender.

Two faces are built from that face specification: the live face and the
document face (`forDoc`). How a face is built from its four pieces is in
`faces.md`.

### Face specification and `FaceSpec.fromString`

A face specification is gender, four piece numbers (shoulders, head, eyes,
nose/mouth), a palette (colour set) and a mirror flag. As text:
`M-shoulders-head-eyes-noseMouth-palette-flip`, for example `M-23-23-23-23-1-0`.

`fromString` splits at `-`. For each part that is missing or `*`, one draw
`r` in this order:

| Part | Random value |
|---|---|
| gender | male if `r > 0.5` |
| each of the four pieces | `floor(20 * r)` (5 sheets of 4 faces, for either gender) |
| palette | `floor(6 * r)` |
| flip | `r > 0.5` |

Given parts are read as whole numbers (0 if not a number); flip uses the
lowest bit. In `Travelers.txt` 21 face values have all 7 parts, 3 have 6
and 8 have 5, so up to two draws happen there. None uses `*`.

Random faces only use sheets 0 to 4 (pieces 0 to 19). `Faces.xml` has seven
male sheets; the scripted faces use pieces up to 24 and palette 6, which
random faces never get.

### The face cycler

Created with a seed `s` (the launch's master seed, `run-and-seeds.md`):

- its own generator `Rand(s)`, used only for the mirror flag
  (`r > 0.5`);
- for male faces, four piece sequences (shoulders, head, eyes, nose/mouth)
  with seeds `s+1`, `s+2`, `s+3`, `s+4`; for female faces, seeds `s+2`,
  `s+3`, `s+4`, `s+5`;
- a palette sequence of 6 with seed `s+3`.

**The seeds overlap** (for example male heads and female shoulders both use
`s+2`), so those sequences come out in the same order. The port must copy
this.

`getNextFaceSpec(male)` takes the next number from each of the four piece
sequences of that gender, the next palette, and one draw from the cycler's
generator for the flip.

### Shuffled sequences (`app.ShuffledSequence`)

A shuffled sequence hands out `0 .. count-1` in a shuffled order, then
starts again.

- Made with `Rand(seed)` and the shuffle in `facts-xml-format.md`.
- Face pieces and palettes use the **reshuffling** kind. Each time it runs
  out it reshuffles "with maximum separation" using `Rand(seed + k)`, where
  `k` counts 1, 2, 3. After that it starts over from a plain shuffle with
  `Rand(seed)` and `k` returns to 0 (the limit is the static value 4), so
  the pattern repeats every four passes.
- **Shuffle with maximum separation**: with `n` items and
  `sep = floor(n * 0.5 - 1)`, for `i` from 0 to `n-1`: take the items in
  the first `min(n, n - sep + i)` positions of the old order that are not
  yet chosen, and pick one with one draw. This keeps an item from coming
  back soon after it was last used.
- Names use the **basic** kind, which repeats the same order when it runs
  out.

### Reference implementation

`scripts/reference/cyclers.py` implements the shuffle, the
maximum-separation reshuffle, the shuffled sequence and both cyclers, written
from the decompiled code (re-read on 2026-10-13). Given a master seed and the
two name files it prints the first faces and names a launch hands out, and
checks itself: every pass is a permutation, a reshuffling sequence repeats
every four passes, male heads and female shoulders come out in the same
order (the overlapping seeds), and no name repeats within a pass. With 20
items the reshuffle keeps an item from returning for at least 10 steps.

`scripts/reference/person.py` builds the person on top of that and of
`faces.py`: the constructor's draws in the order above, the scripted-face
parser, the combined face metadata, id number, fingerprints, height, weight
and birth date. The arithmetic was re-read from the decompiled constructor
and its constants from the DLL (0.1, 10, 60/100 and 1.3/1.0 for men, 40/100
and 1.0/0.8 for women, 0.5/0.3/0.2 for age, 0.8/0.2 for body-mass index).
It does not evaluate traveler scripts, choose errors or pick criminals; the
caller passes those in. `scripts/checks/person_check.py` (run 2026-10-13)
confirms the number of draws in each case (18 with nothing scripted; one
fewer with a contraband type given, ten fewer with an id number, one more
per missing face part, one more for a confusing-gender error), that the name
cycler advances even for a scripted name, and that all 35 scripted face
values found in the raw text of `Travelers.txt` can be built (face heights
1.455 m to 1.882 m). About one person in five needs a fingerprint redraw.
A man given a woman's face always gets the first one tried; a woman given a
man's face needed up to five tries over 40 master seeds.

It models a fresh name cycler; a saved position (the `names` entry of the
encrypted store) is not modelled. Two cases where a draw of exactly 1.0
reads past the end of an array follow Haxe's documented behaviour and are
marked in the script; they were not checked in this build. The output
(names, faces, numbers) has not been compared with the running game, whose
log does not print it; the number of random draws has, indirectly (see
"Not studied").

### Face metadata (`FaceLib.getMetadata`)

Each of the four pieces belongs to a face on a sheet in `Faces.xml`: piece
number `p` is the face at position `p mod 4` on sheet `p div 4`, looked up
as `M<sheet>:<position>` or `F<sheet>:<position>`. The combined metadata is:

- age = 0.5 × eyes face's age + 0.3 × head face's age + 0.2 × nose/mouth
  face's age;
- body-mass index = whole part of (0.8 × head face's + 0.2 × shoulders
  face's);
- hair height from the head face;
- "can pass for the other gender": head from the head face, eyes from the
  eyes face, mouth from the nose/mouth face; all three must be true for
  `isOkForConfusingGender`;
- description words ("has" and "has not") taken from the matching piece
  (shoulders, head, eyes, mouth).

How `FaceLib` reads `Faces.xml` into those keys is in `faces.md`.

## The name

A name is always taken from the name cycler, for the traveler's gender
(flipped for a confusing-gender error, step 7). Then, if `name` is set, it
is split at `-`: a non-empty first part replaces the first name and a
non-empty second part replaces the last name. **The cycler advances even
when the script gives the whole name.**

The name cycler reads `NamesM.txt` and `NamesF.txt`, split at line breaks.
Each list is a basic shuffled sequence (seed `s` for male, `s+1` for
female), unless a saved position exists under `names` in the encrypted
store. Taking a name: up to 1000 times, take the next line and split it at
spaces; accept it if it has exactly two words. Then **save the position**.
After 1000 failures the name is `First Last`.

Both files end with a line break, so each list has one empty entry
(1341 male and 1300 female entries in total). When the empty entry comes up
it is skipped, and that uses up a step of the sequence.

## Id number

`makeRandomIdNumber`: ten draws, each picking `floor(32 * r)` from
`0123456789ABCDEFGHJKLMNPQRSTUVWX` (no I, O, Y or Z), written as five
characters, `-`, five characters. A draw of exactly 1.0 asks for position
32, which does not exist; Haxe's `charAt` then gives an empty text, so the
number is one character short (Haxe's documented behaviour; not checked in
this build).

`invalidateIdNumber` (used for wrong values, `fact-values.md`): make a
complete new random number (ten draws); then draw a position in the old
number, and repeat until the new number differs from the old one at that
position; replace just that one character. (When both have the random
format, position 5 is `-` in both, so landing there always means another
draw.)

Scripted `idNumber` values do not all follow the random format: 2 of the 14
in `Travelers.txt` use letters outside the alphabet or have four characters
before the `-`.

## Fingerprints

Five numbers, one per finger, each `floor(10 * r)` (0 to 9), drawn in
order. Then: while finger 2 equals finger 3 (counting from 1), redraw finger
3; then, while finger 4 equals finger 5, redraw finger 5.

## Height and weight

- The face has a height from its image: `1.0 + pixels / 110` metres. The
  pixel count is `120 − hair height − the first row of the assembled face
  picture that contains the dark face colour` (`faces.md`).
- **Height** = face height − `r × 0.1` metres (one draw, up to 10 cm
  shorter). In centimetres it is rounded.
- **Weight**: start with `w = floor(bmi × height²)`. Then multiply by a
  factor and take the whole part:
  - men: from 1.3 at `w <= 60` down to 1.0 at `w >= 100`, in a straight
    line between;
  - women: from 1.0 at `w <= 40` down to 0.8 at `w >= 100`.
- **Birth date** (`getBirthDate`): today minus the face's age in years. How
  a fractional year is handled (`GregorianDate.afterYears`) is not studied.

## Criminals

`Criminal.selectRandom`:

1. If one of the day's criminals is reserved for this traveler id, take it.
   No draw.
2. Otherwise keep the criminals that are not used and not reserved, and,
   when gender is forced, have a face of the traveler's gender. If any
   remain, pick one (one draw), otherwise none.

`genderForced` is never set in `Travelers.txt`, so in practice gender is
not forced.

When a criminal is found, the traveler's error is replaced by
`Bulletin-Criminal<n>` (`n` is the criminal's index; the three exist in
`Errors.txt`), and two fact groups are added: `Criminal-Bulletin`
(`Bulletin/Criminal<n>` with every `.../Face`) and `Criminal-Booth`
(`Booth/Criminal<n>` with every `.../Face`). These are added to the
specification's own list. After the traveler is made, `makeNewTraveler`
marks the criminal as used (`traveler-creation.md`, step 7).

## Small questions the rest of the game asks

| Question | Answer |
|---|---|
| Special? | `special` is set |
| Enters from the right? | `special` is set and does not contain `left` |
| Has a bomb? | the contraband types contain `bomb` |
| Can give paper `X`? | Only if there is at least one wanted pattern: false if any reject pattern matches `X`, true if any wanted pattern matches, otherwise false. With no wanted patterns the answer is always false |
| Responses for an event | taken from the wrapped response lines (`OpHelper.getRunOps`, described in `travelers-txt-format.md`) |

## Check against the data files

Script: `scripts/checks/traveler_build_check.py`.

- All 18 variables the constructor reads were listed with their values.
  `canDetain` and `genderForced` are never set in `Travelers.txt`.
  `contrabandTypes` has one value written `$Gun0`: a `$` makes it name a
  contraband picture file instead of a type (`emblems-and-bodies.md`).
- All 31 `name` values have exactly two parts.
- `Errors.txt` has `Traveler-ConfusingGender<generic>`,
  `Traveler-Criminal<generic>` and `Bulletin-Criminal0` to `2`, matching
  the names the code looks for.
- `Bodies.xml`: 12 `<contra>`, three each of gun, knife, bomb and drugs.
- `Faces.xml`: 7 male and 5 female sheets of 4 faces. Every female face can
  pass for male in all three parts; 9 of the 28 male faces can pass for
  female.

## Notes for the port

- Count the booth draws exactly as in "Order of draws"; several are
  conditional on the specification and the error.
- The face and name cyclers must be separate generators with the overlapping
  seeds, and the name position must be saved with the game.
- Advance the name cycler even for fully scripted names.

## Not studied

- (How a face image is built, `heightInPixels` and the `Faces.xml` format
  are now in `faces.md`.) The `Bodies.xml` format in general.
- `GregorianDate.afterYears`, `TravelerName.getFormatted` and the other
  name methods, `FaceSpec.getInvalid`, `FingerprintCode.makeInvalid`.
- What `canDetain`, `forceDeny`, `slow` and `special` do in play.
  (`leaveDir` is known since: it is the direction text the border scene gets
  when the traveler leaves, and it picks the exit path; see "When the
  traveler leaves the booth" in `border-scene.md`. The four values in
  `Travelers.txt` are `left-killer`, `left-timebomber`, `right-elisa` and
  `right-police`.)
- Compared with the running game since, indirectly
  (`comparing-with-the-game.md`): for seed 12345, days 1 to 4, the
  reference picks the same errors as the game for all 36 travelers, which
  it could not do if the number of random draws made while building a
  person were off. The results themselves (name, face, id number, height,
  weight, fingerprints) are not in the game's log and were not compared.
