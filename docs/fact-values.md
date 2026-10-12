# How each value on a document is generated

Studied on 2026-10-13. `BoothEnv.makeFactValue(path, valid, confusing)`
(`0x18047add0`, about 13 KB of code) produces the value of one fact: the
correct one when `valid` is true, a deliberately wrong one when it is false.

The function was read in full (1,516 lines after cleaning), together with
`app.Num.lerpScale`. Its sixteen numeric constants were read from the DLL.
Methods it reaches by slot number were named from the recovered metadata,
and three calls whose arguments the decompiler dropped were checked against
the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## Shape

The path is split at its first `/` into a paper id and a fact id. The fact
id decides what happens; the first matching row below wins. All randomness
comes from `BoothEnv.rand` (`traveler-creation.md`). A "draw" is one call to
`random()`, a fraction from 0 to 1 (`rand.md`).

A value has a text, and optionally a date, a traveler name, and a separate
"localized text" for display. Where the table says "display", that is the
localized text.

## By fact id

| Fact id | Valid value | Invalid value |
|---|---|---|
| `BirthDate` | The traveler's birth date for today's date | Two draws. Shift by `10 + 1815 * r1` days (10 days to about 5 years); earlier if `r2 < 0.5`, otherwise later |
| `Exists`, `Visible` | `YES` | `NO` |
| `ExpirationDate` | The paper's stored expiration date | One draw. Today minus `1 + 29 * r` days (expired 1 to 30 days ago) |
| `WorkEndDate` | First day of the month `ceil(duration) + 1` months after this month | One draw. First day of the month `floor(duration)` months ahead, moved back `floor(1 + 11 * r)` months (1 to 11) |
| `UseDate` | Today | One draw. Today plus `1 + 29 * r` days |
| `Name` | The traveler's name, laid out by the fact's `format` (`Facts.xml`) | One draw. `r >= 0.5`: a randomly altered name (`getRandomInvalidated`). Otherwise: an alias (`getRandomAlias`). Then laid out the same way |
| `IssuingCity` | The traveler's issuing city; display is its localized form | See below |
| `Nation` | The traveler's nationality in upper case | A random nationality, redrawn until it differs from the traveler's |
| `AccessNations` | One draw: a list of `floor(2 + 3 * r)` nations (2 to 4) **including Arstotzka**, joined with `, `, upper case | Same, **without Arstotzka** |
| `IdNumber` | The traveler's id number | See below |
| `Gender` | `M` or `F`; display from the text entries `env_lettermale` / `env_letterfemale` | The opposite letter. **If `confusing` is set, the correct letter is kept** |
| `Face` | `VALID` | A wrong face specification (`FaceSpec.getInvalid`), as text |
| `Description` | One draw: a random entry of the face's "has this feature" list, with gender wording applied, upper case | The same from the face's "does not have" list |
| `Fingerprints`, `Thumbprint` | The traveler's fingerprint code | A fresh random code made to differ from the traveler's (`makeInvalid`) |
| `Alias` | The text entry `env_noalias` | The same |
| `Height` | Height in cm followed by `cm` | Two draws. Off by `floor(10 + 10 * r1)` cm (10 to 19); taller if `r2 > 0.5`, otherwise shorter |
| `Weight` | Weight followed by `kg` | One draw. **Lower** by `floor(3 + 2 * r)` kg (3 or 4). Never higher |
| `Duration` | The traveler's duration; display from `getDurationText` | A random duration from the whole list (no purpose filter), redrawn until different |
| `Purpose` | The traveler's purpose; display localized, upper case | A random purpose valid for the nation and the day's rules, chosen "for invalid" (`facts-xml-format.md`), redrawn until different |
| `Job` | The traveler's job; display localized | The same |
| `District` | The traveler's district; display is the localized `district` template filled with it, upper case | See below |
| `Nationality` | The traveler's nationality; display localized | The same |
| `Contraband` | The traveler's contraband types | The same |
| `NowDate` | Today | The same |
| `VaccineDates` | See below | See below |
| `VaccineDrugs` | See below | See below |
| starts with `Emblem` | `VALID` | One draw. `INVALID` if `r < 0.75`, otherwise `NONE` |
| starts with `Criminal` | The number after `Criminal` as text, if the day has that many criminals; otherwise empty | The same |
| anything else | For papers `Bulletin` and `Rules`: the value already stored for that path, if any. Otherwise empty text | The same |

"The same" means the function ignores `valid` for that fact.

### `IssuingCity`, invalid

One draw `r`:

- `r < 0.25`: an alias of the city (`Lang.makeAlias`), made separately for
  the text and the display text.
- otherwise, if the day has the `HARDER` feature: a second draw; if it is
  below 0.25, a typo of the city (`Lang.makeTypo`).
- otherwise: a random nationality, redrawn until it is not the traveler's,
  then a random city of that nation.

### `IdNumber`, invalid

- With the `HARDER` feature: one draw; if below 0.5, a second draw: below
  0.25 gives a typo of the number (`Lang.makeTypo`), otherwise a deliberate
  alteration (`Traveler.invalidateIdNumber`).
- In all other cases: a completely new random number
  (`Traveler.makeRandomIdNumber`).

### `District`, invalid

- With the `HARDER` feature: one draw; below 0.5 gives a typo.
- Otherwise: an alias (`Lang.makeAlias`).

### `VaccineDates`

One draw for the first date: valid is today minus `730.484 - 700.484 * r`
days (30 days to 2 years ago); invalid is today minus
`3652.42 - 2191.452 * r` days (4 to 10 years ago). Then, once per vaccine the
traveler has: add the current date to the list, and draw again to move
`1 + r` days later. The dates are joined with line breaks.

### `VaccineDrugs`

The list starts as `[POLIO]` when valid and empty when invalid. Random
vaccines are drawn and added, skipping repeats and (when invalid) skipping
`POLIO`, until there are as many as the traveler has vaccines. The list is
then shuffled (`facts-xml-format.md`) and joined with line breaks. So a
valid certificate always includes polio and an invalid one never does. This
is the "added automatically" note on `POLIO` in `Facts.xml`.

## What "confusing" means

The `confusing` flag changes only one thing in this function: for `Gender`
the correct letter is kept instead of flipped.

For every other fact, a `~` path in `Errors.txt` (see
`operations-and-fact-validity.md`) generates a wrong value, then generates a
wrong value **again** and stores that, and records the path as confusing.
The second generation uses more random draws, which the port must also do.

## Notes for the port

- The number of draws depends on the fact, on `valid`, on the `HARDER`
  feature and on earlier draws. Each row above states its draws; helper
  calls (`makeAlias`, `makeTypo`, name and face helpers, random picks) make
  their own.
- Several "redrawn until different" loops have no limit. With the game's
  data there is always a different option.
- Months are numbered from 0 in the date helpers (`days-csv-format.md` has
  November as month 10).
- A draw of exactly 1.0 gives one more than the ranges shown (for example
  5 access nations).

## Not studied

These are called from here and decide the fine detail of several values:

- `TravelerName`: `getFormatted`, `getRandomInvalidated`, `getRandomAlias`.
- `Lang.makeAlias`, `Lang.makeTypo`, `Lang.getReplaced`,
  `Uppercaser.toUpperCaseU`, `SpeechLib.applyGenderSwitches`.
- `FaceSpec.getInvalid`, the face's feature lists, `FingerprintCode`.
- `Traveler.getBirthDate`, `invalidateIdNumber`, `makeRandomIdNumber`, and
  the `Traveler` constructor that sets height, weight and the rest.
- `Settings.formatDate` and `GregorianDate`.
- When this function is called with `valid = true` for a freshly added paper
  (`addPaper`).

Nothing here has been compared with the running game. No reference
implementation exists yet for this function; it depends on the pieces above.
