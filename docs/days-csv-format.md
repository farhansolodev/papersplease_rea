# Days.csv: what happens on each day

Studied on 2026-10-12. Source: `extracted/art/assets/data/Days.csv` and the
decompiled `data.CsvTable`, `data.DayLib` and `play.day.Day` constructor
(`0x180540bc0`), which was read in full. Where the decompiler dropped a row
name from a lookup, the row was identified from the order of string constants
in the machine code (`ListStringUses.java`).

Everything here is confirmed in the code unless marked **inferred**.

## Where it sits in the data model

Class `Db` loads every data file into one "library" object each:
`dayLib`, `endlessDayLib`, `emblemLib`, `endlessLib`, `endLib`, `faceLib`,
`factLib`, `fontLib`, `errorLib`, `newsArticleLib`, `nightLib`,
`paperDefLib`, `bodyLib`, `pathLib`, `speechLib`, `travelerLib`, `atlasLib`,
`testScenarioLib`, plus `lang` and `uppercaser`.

`Days.csv` feeds `dayLib`. `endlessDayLib` uses the same class; that it is
loaded from `Endless.csv` is inferred.

## Table format

The table is sideways: **each row is a property and each column is a day.**

- 20 rows, 34 columns. Column 0 is the row name. Row 0 (`DAY`) holds the
  column names: `1` to `31`, one empty column, then `100` (a test day).
- Ordinary CSV rules, from `CsvTable.popRow`: cells are separated by `,`; a
  cell may be wrapped in `"`, inside which `""` means a literal quote and line
  breaks are allowed; a line break outside quotes ends the row. Every cell is
  trimmed. An empty last cell is dropped.
- A cell with several values lists them one per line.
- Two row names in the file have a stray trailing line break (`BULLETIN0`,
  `BULLETIN1`); trimming removes it.

## Carry-over rows

`CsvTable.getAccumulatedRow(throughDay, row)` walks the columns from day 1 up
to the requested day and builds a list:

- `+Name` adds `Name` and it stays for all later days.
- `-Name` removes `Name` from then on.
- A plain `Name` counts only on the day it is written.

Used for `FEATURES` and `RULES`.

## Rows

### DAY, DESC

`DAY` is the column name. `DESC` is a designer's note; its text is never used,
but `DayLib.hasDay` and `getNumDays` look at this row to tell which days
exist.

### TRAVELERS, FILL

- `TRAVELERS`: scripted traveler ids, one per line, in order.
- `minTravelers` = the number of `TRAVELERS` entries, or 100 if there are
  none.
- `FILL`: if not blank, appended to the end of the traveler list (after
  `minTravelers` is counted). Its use as the template for the remaining
  random travelers is inferred.
- If the saved story has a fact named `Game/Visitor<number>`, its value is
  inserted at the front of the list. The number is probably the day; not
  confirmed.
- `hasBoss` is true when the first traveler id starts with `BOSS`.

### DURATION, DURATION_SLOW, LINE

- `DURATION`: day length in minutes (decimal). Values 3 to 8.
- `DURATION_SLOW`: replaces `DURATION` only when the platform is `PHONE` and
  the mode is story, not endless.
- `LINE`: waiting line length, a whole number, 0 if blank. Values 100 down
  to 40.

### FEATURES

Carry-over list. Each name is a value of the `Feature` enum, and
`featureFlags` has bit `1 << position` set for each:

| Bit | Name | Bit | Name |
|---|---|---|---|
| 0 | `INSPECT` | 7 | `FORGERY` |
| 1 | `GATE_DENIAL` | 8 | `CRIMINALS` |
| 2 | `DETAIN` | 9 | `DENIAL_REASON` |
| 3 | `FINGERPRINT` | 10 | `BORDER_TARGET` |
| 4 | `SEARCH` | 11 | `KEEP_ESCAPE_PASSPORTS` |
| 5 | `FILER` | 12 | `SUICIDE_BOMBER` |
| 6 | `SNIPING` | 13 | `HARDER` |

Side effects in the constructor:

- `SNIPING`: `isFirstSnipingDay` is true when the previous day's carried-over
  list did not contain `SNIPING`.
- `SUICIDE_BOMBER`: `minTravelers` is set to 10000.
- `CRIMINALS`: the bulletin page id `criminals` is added (see `BPAGES`).

### RULES

Carry-over list of rule names. Stored in a map under the keys `Rule0`,
`Rule1`, ... in list order. A day with no rules is an error ("No rules for
day").

### ATTACK

One `Attack` enum name: `NONE` (default when blank), `RUNNER`, `RUNNERSHOT`,
`BIKE`, `BIKESHOT`, `BIKERUNNER`, `TRUCK`.

### GUARDS

A string of single characters, each tested independently:

| Character | Effect |
|---|---|
| `0` `1` `2` `3` `4` | Set `guardFlags` bits 1, 2, 4, 8, 16. Presumably one guard position each; which position is which is not studied |
| `J` | `hasLeftJailors` = true |
| `F` | Friendly guard is present (`GUARDING`) |

`friendlyGuard` is decided in this order: `DEAD` if the story fact
`Game/FriendlyGuardDead` is `YES`; otherwise `CHAT` if the first traveler id
starts with `FRIENDLY_GUARD`; otherwise `GUARDING` if the cell contains `F`;
otherwise `NONE`.

Values in the file: `3` (days 1-2), `12340` (days 3-15), then `12340J` and
`12340JF`.

### CONFISCATE

Stored in `confiscationId`, with `&amp;` turned into `&`. It must be filled
exactly when the `FILER` feature is on, otherwise the game raises an error.
Values in the file: `DistrictAltan`, `Native`.

### BULLETIN0, BULLETIN1, BPAGES

- Text = `BULLETIN0`, plus `{SPLITHERE}` and `BULLETIN1` when `BULLETIN1` is
  not blank. If the text is blank there is no bulletin.
- Story mode: the text is placed into a text template named
  `bulletin_default`, with `content` = the text and `date` = the formatted
  date. If the text starts with `[NOTICE]`, that marker is removed and the
  template `bulletin_notice` is used instead. The result is split at
  `{SPLITHERE}` into pages.
- Endless mode: template `bulletin_endless` with `style`, `course` and
  `date`; one page.
- `BPAGES`: extra bulletin page ids separated by spaces. On `TABLET`,
  `touchtut` is inserted after `correlatetut`. With the `CRIMINALS` feature,
  `criminals` is appended.

Where the templates live (probably `Text.xml`) is inferred.

### NEWS, NIGHTEVENTS

- `NEWS` is not read by the `Day` constructor. `DayLib.getNewsIds` reads it,
  and a `DayNews` object is built with the day's news random generator.
  `DayNews` itself is not studied.
- `NIGHTEVENTS`: night event ids, one per line.

### CRIMFACE

`NAME:face spec`, matched with the pattern `\s*(.*):(.*)\s*`. If it matches,
one criminal is created from `FaceSpec.fromString`. The list is then filled
up to three criminals with faces from the run's face cycler, drawing from the
traveler random generator each time.

### PAPERS

Extra paper ids, one per line. The story fact `Night/Papers<number>` (a list)
is appended to it. Only day 16 uses the row (`KeyTranq`).

### RPAGE

**Not used.** No string `RPAGE` exists anywhere in the game's code, and the
constructor sets `openRulebookPage` to nothing. The row is left over in the
data.

## Values computed in code, not in the file

- **Date.** Story day `n` is 23 November 1982 plus `n - 1` days. Endless mode
  starts from 1 January 1983.
- **Random seed.** Story: `seed = day * 50 + storySeed`. Endless: the
  endless run's own seed. Four independent random generators are created from
  it: news (`seed + 0x1000`), border (`+ 0x2000`), night (`+ 0x3000`) and
  travelers (`+ 0x4000`).
- **Day facts.** Three facts are recorded for the day: `Day/Rules` (rule
  names joined with `;`), `Day/Id` and `Day/Features` (feature names joined
  with `;`).

## Not studied

- `app.Rand`, the random number generator. The port must reproduce it
  exactly for days to play out the same.
- `DayNews`, `FaceSpec`, `FaceCycler` and the text template system.
- What each feature, rule and guard flag does in play.
- No reader has been written for the port, so none of this is tested end to
  end.
