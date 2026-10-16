# Random draws made when a paper is drawn on the desk

Found on 2026-10-14 while solving the open problem "the booth's random
numbers fall out of step with the game" (the record is under "Dead ends" in
`comparing-with-the-game.md`). **Drawing a paper's picture uses the booth's
own random generator**: the same one that picks
errors, builds the person and generates document values. So the pictures are
part of the game's logic as far as random numbers go: leave them out and
every later pick is different.

Reference script: `scripts/reference/desk.py`. It counts the draws; it does
not make pictures.

Functions read in full: `BoothEngine.addNewEnvPapers`,
`Booth.engine_onPapersAdded`, `Paper.setPage`, `Paper.updatePage`,
`Paper.set_page`, `BoothEnv.getEmblemStatus`, `Mark.getRandomForcePos`.
Read in part (the parts that touch the generator, and what leads to them):
the `play.day.booth.Paper` constructor, the `play.day.PaperInnerVisuals`
constructor, `BoothEnv.getImage`, `Page.getInnerImageAndMarkPositions`,
`Face.getDocImage`. (The `PaperInnerVisuals` constructor and
`getInnerImageAndMarkPositions` were read in full on 2026-10-16,
`page-layout.md`; `BoothEnv.getImage`, `Face.getDocImage` and the
fingerprint and contraband pictures the same day, `fact-pictures.md`. The
draws listed below hold, and the fingerprint draws were added.) How they were found: all 1,433 functions of the booth
classes were decompiled and searched for uses of a generator; every function
in the game that takes a generator as a parameter was listed from the
recovered names.

## When a paper gets a picture

After every batch of operations and every event, the engine
(`addNewEnvPapers`) asks the booth which papers are shown (existing, visible,
**sorted by id**, `papers-on-desk.md`) and, for each one it has no desk paper
for yet, creates one. Papers without a definition in `Papers.xml` (the
fact-only `Traveler`, `Speech`, `Booth`) are skipped.

So:

- at the start of a day: the day's own papers (`Rules`, `Transcript`,
  `Bulletin`, and any others on the desk then);
- after a traveler is created: their papers, in sorted order (for example
  `EntryPermit` before `Passport`);
- later: a paper added by an operation, or a hidden paper once it is shown.

A missing paper never gets a picture. A hidden one gets it when revealed.

## The draws for one paper, in order

1. **Tilt**: one draw, unless the paper has `rotate="false"` (only
   `TimeBomb`). It turns the closed paper's picture slightly.
2. **The first page is drawn** (`setPage`, then `PaperInnerVisuals`):
   1. **Mark positions**: for each mark in file order that has both `pos`
      and `pos2`, two draws (x, then y, between the two points).
   2. Then mark by mark, in file order:
      - a picture mark showing the fact `Face`: **one draw**
        (`Face.getDocImage` shifts the photo down by 3 to 6 pixels). A
        value that is neither `VALID` nor a full face specification first
        draws once for each missing or `*` part (`fact-pictures.md`; not
        modelled in `desk.py`);
      - a picture mark showing `Criminal0`...: one draw if that slot has a
        criminal (same function), none if it is blank;
      - a picture mark showing `Fingerprints` or `Thumbprint`: a random
        fingerprint code that the value then overwrites (five draws plus
        redraws, `traveler-build.md`), then one draw per finger shown (5,
        or 1 for the thumbprint). Added 2026-10-16 (`fact-pictures.md`);
      - (a search photo's contraband: one draw, the first time for a
        traveler, if the fact is invalid. It is on the photo's second page,
        so it is not a first-page draw.)
      - a seal mark (`emblem="..."`): nothing if the seal's fact
        `<paper>/Emblem/<id>` is neither `VALID` nor `INVALID`; otherwise
        **three draws**: which seal picture (any valid one, or any invalid
        one, `emblems-and-bodies.md`), then its x, then its y inside the
        mark's rectangle.

For the documents of the first days that gives:

| Paper | Draws |
|---|---|
| `Rules`, `Transcript`, `Bulletin` (first page), `BrothelFlyer` | 1 |
| `Passport`, `IdCard` | 2 (tilt, photo) |
| `EntryTicket` | 3 (tilt, the date's position) |
| `EntryPermit`, `WorkPermit`, `AccessPermit`, `DiplomaticAuth` | 4 (tilt, seal choice, seal position) |

## Checked against the running game

`scripts/checks/compare_with_log.py` replays, for each traveler in the
game's log, these draws and the spoken lines (`speech.md`), and compares the
error the reference picks with the game's.

| Run (seed 12345) | With both | Without the desk draws | Without speech |
|---|---|---|---|
| route 20, days 1 to 4, 36 travelers | **36 of 36** | 30 of 36 | 32 of 36 |
| route 1, day 1, 8 travelers | 8 of 8 | | |

The 36 include two picks among 14 candidates and one among 4 on day 4, the
ones that failed before. In an earlier experiment the number of draws at the
start of the day was varied from 0 to 5: only 3 (rulebook, transcript,
bulletin, as the code says) gives 36 of 36.

What this confirms: the tilt, the photo draw, the entry ticket's two
position draws, the entry permit's three seal draws, the three draws at the
start of the day, the sorted order, and that both the desk draws and the
spoken lines are needed.

## Not known / not tested

- **Pages drawn again.** `setPage` runs again when a page is turned, a link
  is followed or a stash is restored, and each time the page's draws are
  made again. (A stash is not restored in normal desktop play:
  `save-format.md`, part 2.) For the first four days this did not matter (the pages the
  test player turned have no random marks). The bulletin's criminals page
  (three photos) would draw on every visit. Not modelled, not tested.
- The fingerprint, thumbprint and contraband pictures receive the generator
  too (`FingerprintCode.fromString`, `Traveler.getContrabandImage`). Their
  draws were read on 2026-10-16 (`fact-pictures.md`; listed above), and
  `desk.py` counts the fingerprint and thumbprint ones. **Not tested**:
  route 20 draws four fingerprint pictures (identity record and
  fingerprint paper, twice each), but they all come after the last pick
  the log can show. With three deliberate extra draws in them, the
  comparison still matched 36 of 36.
- `PaperInnerVisuals.autoGetPageIndexForFactId` also calls `getImage`,
  and so makes these draws. Its callers appear to serve the test player
  only (inferred, `fact-pictures.md`).
- The criminal photo draw and the invalid seal are from the code only.
- A hidden paper shown later: modelled, but the one case in the log came
  after the last informative pick. Not tested.
- Consequence for the port, to be decided in `DESIGN.md` when the booth is
  built: to reproduce the original's travelers exactly for a seed, the port
  must make these draws at the same moments, even where its own drawing
  works differently. And because turning to some pages draws again, what
  the player looks at can change later travelers in the original.
