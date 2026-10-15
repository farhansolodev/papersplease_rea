# Endless mode: Endlesses.xml, Endless.csv and scoring

Studied on 2026-10-13. Endless mode is the score-attack mode unlocked with a
code. `Endlesses.xml` defines its three scoring **styles** and four
**courses**; `Endless.csv` gives each course its rules, in the same table
format as `Days.csv`.

Functions read in full: the `data.EndlessLib` constructor; the
`EndlessCourse`, `EndlessStyle`, `Action` and `ScoreScale` constructors;
`Action.parseSigned`, `EndlessStyle.getAction` and `get_hasTimeLimit`,
`ScoreScale.getScale` and `transform`; `play.day.Endless` (constructor,
`start`, `update`, `handleAction`, `queEnd`, `end`). One dropped sign was read
from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## Endlesses.xml

```xml
<style id="timed" name="Timed" time="600" ... >
	<process score="+1"/>
	<mistake time="-30"/>
	<detain time="+5" score="+1"/>
</style>
<course id="course1" name="Course 1" day="1" button="EndlessCourse1.png" leaderboard="Course 1"/>
```

`<style>` attributes: `id`, `name`, `desc` (description), `bulletin` (a text;
that it goes in the booth's bulletin is inferred from the name), `icon`, `button` (picture names), `leaderboard`
(out of scope), `time` (a time limit in seconds; 0 or absent means none) and
`reportscoremax` (exactly `true`: the result is the highest score reached,
not the final one).

Under a style, each tag other than `<score>` is an **action**, named by its
tag. Its attributes are signed whole numbers (`+1`, `-30`):

| Attribute | Meaning |
|---|---|
| `score` | Points for the action |
| `delta` | Extra points per earlier occurrence of the same action |
| `time` | Seconds given back (positive) or lost (negative) |
| `end` | Exactly `true`: the run ends |

`<score scale0 scale1 time0 time1>` makes points depend on elapsed time: the
multiplier goes in a straight line from `scale0` at `time0` seconds to
`scale1` at `time1`, held at the ends, then cut to a whole number. Absent, the
multiplier is 1.

`<course>` attributes: `id`, `name`, `day` (the column of `Endless.csv`),
`button`, `leaderboard`.

## Scoring (`Endless.handleAction`)

The run keeps a score, the highest score so far, a clock, and a count per
action. When an action happens (ignored once the run is ending, or if the
style has no such action):

1. `before` = how many times this action happened already; the count goes up.
2. If the action has a `score`: points = multiplier now x `score` +
   `before` x `delta`. The score changes by that; the highest score is
   updated; **a score below 0 ends the run**.
3. If it has a `time`: the clock is set to its time **minus** that value
   (so `-30` moves the clock 30 seconds forward, `+5` moves it back 5).
4. If it has `end`: the run ends.

The clock runs up from 0. With a time limit, the run ends when the clock
passes it. "Ends" means an 8 second countdown starts and the foghorn sound
plays; when it finishes, the result (score or highest score, and the time) is
recorded and the result screen is shown.

Which game events raise `process`, `mistake` and `detain` is in the booth
code, not read for this step.

With the data:

| Style | Limit | Traveler processed | Citation | Detention |
|---|---|---|---|---|
| timed | 600 s | +1 | lose 30 s | +1 and 5 s back |
| perfection | none | +10 in the first minute, one less each minute, +1 from the tenth on | the run ends | same points as a traveler |
| endurance | none | +1 | -5, then -10, -15, ... | +2 |

Endurance ends when the score goes below 0 and reports the highest score
reached.

## Endless.csv

Same sideways table as `Days.csv` (`days-csv-format.md`), loaded by the same
`DayLib`, with columns `1` to `4` for the four courses. It has every row of
`Days.csv` except `BULLETIN1`, `DURATION_SLOW` and `RPAGE`, plus nothing new.
Each course: no scripted travelers, the filler `GENERIC`, a line of 100, a
duration of 0, and rules that build up from course to course:

- Course 1: passport, current documents, no contraband, id card, entry
  permit, work permit.
- Course 2: adds id supplement and diplomatic authorisation.
- Course 3: adds asylum grant and vaccine certificate, and the
  reason-for-denial stamp.
- Course 4: drops entry permit and id supplement, adds access permit.

All four have inspect, detain, fingerprint, search, forgery and criminals
switched on.

## Check against the data files

`scripts/checks/endless_check.py` (run 2026-10-13):

- Every attribute in `Endlesses.xml` is one the code reads. 3 styles, each
  with `process`, `mistake` and `detain`; one `<score>` scale (perfection).
- The scoring model gives the table above: timed 20 travelers then a
  citation moves the clock from 400 to 430 s, a detention back to 425 s;
  perfection gives 10, 9, ... 1, 1, 1 points in minutes 1 to 12; endurance
  citations cost 5, 10, 15, 20 and the run reports the highest score.
- Every rule in `Endless.csv` exists in `Facts.xml`; the filler traveler
  entry exists; each course's `day` is a column.
- **Three pictures named in the file are not in the extracted assets**:
  `EndlessStyleTimed.png`, `EndlessStylePerfection.png`,
  `EndlessStyleEndurance.png` (the `button` of each style). An
  `EndlessStyleButton.png` exists instead. Whether the game ever asks for the
  three named files: **the endless screen does not** (read on 2026-10-16,
  `screens.md`, part 7). It builds each style button from
  `EndlessStyleButton.png` plus the style's `icon`; no read of the style's
  `button` field by name was found elsewhere in the decompile.

## Notes for the port

- Leaderboards are online and out of scope (the user's decision,
  2026-10-16: no leaderboards in the port). **But the `leaderboard` names
  are also used offline**: `<style leaderboard> <course leaderboard>`
  (for example `Perfection Course 2`) is the key of the player's local
  best score, kept in the all-time statistics as
  `_Leaderboard:<key>` = `score,time` and shown on the endless screen
  (`screens.md`, part 7, "The score under each course"). This corrects
  the note that stood here until 2026-10-16, that the names were needed
  only for leaderboards.
- The multiplier is cut to a whole number before multiplying.

## Not studied

- (The scoreboard display is now studied: `border-view.md`, including the
  three messages `Endless` sends it.)
- (The endless screen and the result box after a run are studied since
  2026-10-16: `screens.md`, part 7. So is `Endless.end`, what a run hands
  over when it ends: the score, or the highest score for `reportscoremax`,
  and the clock in whole seconds.)
- How an endless day differs from a story day in the booth (which events
  raise the three actions, how the random seed of a run is chosen).
- (How the unlock code is entered and checked: `screens.md`, part 7,
  "The code box". The code is 62131.)
- The scoring has hardly been compared with the running game. One run
  was watched on 2026-10-16 (`screens.md`, part 7, "Compared with the
  running game"): Perfection, Course 2, one traveler processed with one
  citation, the run over at 33 seconds with 0 points. That fits
  `<mistake end="true"/>`; that the citation ended the run before the
  traveler's points were added is inferred. Nothing else here was
  compared.
