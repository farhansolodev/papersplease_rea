# Travelers.txt: scripted travelers and their behaviour

Studied on 2026-10-12. The file is an indented tree (see
`docs/tab-tree-format.md`). This document covers what the lines mean when a
traveler is **created**: how an entry becomes a "traveler specification" and
a set of responses. How those responses are **run** at the booth is not
studied yet.

Functions read in full: all of `play.day.TravelerContext` (`makeTravelerSpec`,
`applyToSpec`, `assignVar`, `getFactGroup`, `testConditional` and its helper
closure, `expandExpressionLhs`, `hasDayRule`, `getDayRules`),
`data.OpHelper.makeOp` and `getRunOps`, `app.ExpressionTester.test` and
`testWithGlue`, `app.StringUtil.joinQuoted`, and the `TravelerSpec` static
setup. Every line of the real file was then checked against what this code
accepts.

Everything here is confirmed in the code unless marked otherwise.

## The file

- 185 top-level entries, each named by one word. One 12-line block comment
  switches off an entry called `IDSUPPLEMENT_DAY`.
- 142 entries are named by `Days.csv`. 28 are pulled into other entries with
  `INCLUDE`. `GENERIC` is also a `fallback` target. `DEFAULT` is special
  (see the end).
- 20 entries are not referred to by `Days.csv`, by any `INCLUDE` or
  `fallback`, or by any exact string in the code: `TEST`, twelve
  `PRESSKIT_*`, `POSTER_DEFAULT`, `POSTER_WRONGFACE`, `FEATURE_FACE`,
  `DEVLOG_GRAB`, `BOSS_ANGRY`, `DIPLOMAT`, `DIPLOMAT_ERROR` and
  `SECRET_POLICE_CAUGHT`. (`TEST` is named in `TestScenarios.xml`, and
  `SECRET_POLICE_CAUGHT` in two files the game never loads by name.)

## Two levels of line

A traveler entry is read at two levels, and the same symbol can mean
different things at each.

- **Block level**: the entry's own lines, and lines under a block-level `?`.
  These run once, top to bottom, when the traveler is created.
- **Operation level**: everything under a `>` (a response) or a `*` (a custom
  error). These are stored and run later.

## Block level

Handled by `TravelerContext.applyToSpec`. Any other first word raises
"Unknown block node". The real file has none at this level.

| Line | Count | Effect |
|---|---|---|
| `= name ...` | 437 | Sets a variable (details below) |
| `> Event` | 344 | Stores a response; its children are operations |
| `INCLUDE Entry` | 103 | Runs another entry's block lines here. Unknown entry is an error |
| `? condition` | 84 | If true, runs its children as block lines |
| `+ Paper` | 24 | Adds a paper id to the traveler's starting papers, **at the front** of the list |
| `- Paper` | 0 | Removes a paper id from the starting papers |
| `MANUALPAPERS` | 22 | Sets variable `MANUALPAPERS` to `true` |
| `BREAK` | 19 | Stops processing **the whole traveler**, not just the current block. It also stops any entry that included this one |
| `( Name` | 5 | Adds a custom fact group called `Name`; each child line is one path, which may be a pattern such as `.*/Name` |
| `* ErrorId ...` | 3 | Sets the traveler's custom error; its children are operations |

### `=` at block level

`= name value1 value2 ...` picks one value at random and stores it.

- Each value may end in `:weight` (after the **last** colon), for example
  `visit:2`. No weight means 1.
- For values with spaces, the choices go on child lines instead:
  `x weight words...`. A child that is not `x` or has weight 0 is an error.
  12 lines use this.
- **One random draw is made even when there is only one value** (357 such
  lines). A port that skipped the draw would fall out of step with the
  original.
- With no value at all, the variable is removed (1 line).
- Special case: setting `error` with more than one choice also sets
  `error_setRandomly` to `YES`; removing `error` removes that too.

Variable names used in the file that `TravelerSpec` exposes as properties:
`nation`, `error`, `gender`, `purpose`, `face`, `name`, `idNumber`, `want`,
`fallback`, `slow`, `district`, `issuingCity`, `contrabandTypes`, `duration`,
`special`, `leaveDir`, `job`, `preventAdditionalError`, `forceDeny`.
Names used that are not properties: `test` (42), `TESTDAY` (11), `weight`
(1). What reads each variable is not studied, except as noted below.

### Conditions (`?`)

`? left op right` optionally followed by `||` or `&&` and another
comparison, and so on. Fewer than three words is an error.

- **Evaluation is strictly left to right, with no precedence.** After each
  comparison: `||` returns true if it held, otherwise continues; `&&`
  returns false if it failed, otherwise continues. So `A && B || C` is false
  whenever `A` is false; `C` is never looked at.
- **Both sides are lower-cased**, so comparisons ignore case.
- Operators: `==`, `!=` compare text. `<`, `<=`, `>`, `>=` compare whole
  numbers (text that is not a number counts as 0). `has` and `!has` test
  whether the left text contains the right text. **Any other operator makes
  the comparison false.**
- The left side is looked up; the right side is taken literally.
  At block level the left side can be:
  - `RANDOM100`: a random whole number 0 to 99, `floor(random() * 100)`.
    Each use is one random draw. (1 use in the file.)
  - a word with no `/`: one of this traveler's variables.
  - `Day/...`: a fact of the current day.
  - `Game/...` or `Night/...`: a fact of the saved story.
  - anything else with a `/` is an error ("Invalid TravelerContext lhs").
  - `PASSTHROUGH` is never looked up.
  A missing value counts as empty text.

## After the block lines: filling in the gaps

`makeTravelerSpec` runs the entry, then, in this order:

1. If `fallback` is set, **the whole result is thrown away** and the entry
   named by `fallback` is made instead (9 lines, all `GENERIC`).
2. `nation`: if unset, a random nationality for the purpose (or any nation
   if there is no purpose yet).
3. `purpose`: if unset **or equal to `random`**, a random purpose for the
   nation and the day's rules, taking the `error` variable into account.
4. `job`: if unset, a random job.
5. `district`: if unset, a random district.
6. `duration`: if unset, a random duration for the purpose.
7. `issuingCity`: if unset, a random city of the nation; if set, its `-`
   characters become spaces.
8. `gender`: if unset, one draw `r`; `M` if `r > 0.5`, otherwise `F`. If it
   was set, `genderForced` becomes `YES`.
9. Unless `MANUALPAPERS` is `true`: every automatic paper for the purpose and
   rules (`Facts.xml` `<autopaper>`) that is not already in the starting
   papers is added at the front.

Each step that fires makes random draws, in exactly this order. The draw
procedures are in `docs/facts-xml-format.md`.

## Operation level

Handled by `OpHelper.makeOp`, which turns each line and its children into an
operation.

| Line | Count | Operation |
|---|---|---|
| `" words...` | 1,169 | Say. The words are rejoined with single spaces. One word starting with `$` names a stock response in `Speeches.txt`; other text is said literally (`speech.md`) |
| `@ Button ...` | 175 | Enable a button. Seen: `Leave`, `Want`, `News`, `Detain`, `Resist`, `Night`, `End`, `Tomorrow`, `Search`, `Reject`, `Custom`, `Unresist`, `NoFiler` |
| `= Fact/Path value` | 120 | Set a fact. **Only the first word after the path is the value**; all 120 in the file have exactly one |
| `? condition` | 113 | A conditional group: stored with the whole line as its id; its children run if the condition holds |
| `+ Paper` | 99 | Add a paper |
| `- Paper` | 5 | Remove a paper |
| `INCLUDE Entry` | 10 | Insert another entry's operations, wrapped in a group named `? PASSTHROUGH == PASSTHROUGH`, a condition that is always true |
| `! Fact/Path` | 6 | Invalidate a fact; may have child operations |
| `^ Fact/Path` | 1 | Validate a fact |
| `\ words...` | 0 | A "requirement"; never used in this file |
| anything else | 6 | A named group of operations. In the file these are all a `> Interrogate` nested inside another response |

A response `> Event` is itself a named group, with the event as its name.

- 43 distinct events. The most common are `Intro-Replace` (87), `Denied`
  (60), `Approved` (52), `Interrogate-Replace` (19), `Detain-Replace` (17)
  and `Intro-After` (17).
- **A group name containing `*` is a pattern** (a case-insensitive regular
  expression). Four are used: `Give-Police.*`, `Give-Ezic.*`,
  `Give-PASSPORT-KORDON-KALLO.*` and `Give-PASSPORT-SIMON-WENS.*`.
- `getRunOps(op, name)` finds the operations for an event: the first group,
  searching depth-first, whose name equals `name` or whose pattern matches.

Two entries, `PRISON_GUARD_REPORTDETAINS` and `BOSS_REPORTCITATIONS`, are
written as operations at the top level. They are only ever pulled in from
inside responses (5 times each), where that is valid.

## Findings in the data

- **A misspelled operator.** In `EZIC_DIPLO`, one response condition reads
  `? Traveler/PassportConfiscated =! YES`. `=!` is not an operator.
  Response conditions do use the same comparison code
  (`responses-and-events.md`), so that comparison is always false and its
  line ("Barbarian.") never runs.
- `Traveler/...` on the left of a condition would be an error at block
  level. All block-level uses are inside `DEFAULT`, which is handled
  separately.

- **A condition that can never hold.** `HIRING_ENGINEERS` tests
  `? Game/Rules has RuleNoImpor` to leave Impor out of its nations.
  `Game/Rules` appears nowhere else in the data files and is not a string in
  the game's code (the day's rules are in `Day/Rules`), so the saved story
  never has it and the line under it never runs. Found 2026-10-13.

## Reference implementation

`scripts/reference/travspec.py` (written 2026-10-13 after re-reading
`applyToSpec`, `assignVar`, `makeTravelerSpec`, the condition tester, the
`WorldDef` pickers, `Probability.select`, `CsvTable.getAccumulatedRow` and
the end of the `Day` constructor) evaluates an entry into a specification:
block lines, weighted `=` picks, conditions, `INCLUDE`, `BREAK`, `fallback`,
then the gap filling in order. It also models the day: the traveler list
from `Days.csv`, the day facts and the three criminal faces made at the
start of every day (`days-csv-format.md`).

`scripts/checks/travspec_check.py` builds the first travelers of all 31
story days for 12 master seeds (4,932 specifications): nothing is rejected,
no detail is left empty, and an unset gender comes out male 2,120 times and
female 2,104 times. A specification takes 7 to 16 draws; only two entries
(`GENERIC_BOMBER`, with its `RANDOM100`, and `SEARCH_DAY`) take a varying
number. With an empty saved story, three entries fall back to `GENERIC`
(`EZIC_HANDLER_PRE1`, `WATCH_BUYER0`, `WATCH_BUYER1`).

Limits: the saved story's facts and the facts scripts set during the day
(`Day/Confiscated`, `Day/KidKiller` and others, 23 in all) are inputs,
empty by default; the error-pattern filter on random purposes is left out
because it excludes nothing with the game's data (`facts-xml-format.md`);
responses and custom errors are recorded by name only. A weighted pick
whose draw is exactly 1.0 returns nothing, as in the game. Nothing has been
compared with the running game.

## DEFAULT

`TravelerLib` keeps a pointer to the entry `DEFAULT`. The designer's note
there says it holds default responses, and that its conditions can see all
facts and are evaluated when a response is needed rather than when a traveler
is created. It is read by `BoothEnv.findDefaultRunOpNode`
(`responses-and-events.md`).

## Not studied

- How the player's actions trigger responses (part 2 of
  `responses-and-events.md`). Events, default responses, conditions and
  button commands are in part 1.
- How a specification becomes an actual traveler with documents:
  `BoothEnv.makeNewTraveler`.
- What names like `TWO_PASSPORTS/...` refer to on the left of a response
  condition. (Response conditions in general: `responses-and-events.md`.)
- The custom error and custom fact group classes beyond how they are built.
- What reads each variable (`want`, `special`, `slow`, `face` and so on).
- How the language packs alter the tree.
- (A reference reader now exists: `scripts/reference/travspec.py`, above.)
