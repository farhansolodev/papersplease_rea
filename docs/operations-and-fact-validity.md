# Running an operation, and what makes a fact invalid

Studied on 2026-10-12. This covers what happens when one operation from an
error or a response is run at the booth, and how the game tracks which facts
are wrong.

Functions read in full: `play.day.BoothEnv.applyOp` (`0x180472770`),
`setFactInvalid`, `setFactValid`, `setFactValue`, `findInvalidFactPath`,
`isValid`, `getFactValue`, `getFactValueText`.

Everything here is confirmed in the code unless marked otherwise.

## Three stores of facts

A fact path's prefix decides where it is kept:

| Prefix | Store | Lifetime (by name; not checked) |
|---|---|---|
| `Day/` | the day's facts | one day |
| `Game/` or `Night/` | the saved story's facts | the whole game |
| anything else | the booth's facts | carried between travelers only for papers that persist (`traveler-creation.md`) |

## What each operation does (`applyOp`)

Operations are built from script lines (`travelers-txt-format.md`). Each
returns a result that tells the booth what changed.

| Operation | Effect | Result |
|---|---|---|
| Say | Looks up the speech (`getSpeech`, see `speech.md`). If it has text: stores it as fact `Transcript/Speech<n>`, where `n` is the number of transcript lines so far, with `@` in front when the inspector is speaking; remembers the speech's fact path. Past 10 lines it sets `Transcript/NextPage0` to `TranscriptNext.png`, past 20 lines `Transcript/NextPage1` | Speak (text, who, pause after) |
| Add paper | `addPaper` (`papers-on-desk.md`), then saves the list of staying papers | Added paper |
| Remove paper | If the paper is on the desk: removes it, saves the staying papers, and subtracts the paper's `money` value (`Facts.xml`) from the day's bribe money. The paper's facts are kept (`papers-on-desk.md`) | Removed paper, or nothing if it was not there |
| Invalidate fact | See below | Updated facts (the paper) |
| Validate fact | See below | Updated facts, or Added paper when the fact is `Visible` |
| Set fact | See below | Updated facts (the paper) |
| Requirement, named group, enable button | **Nothing here.** These are handled by the caller | None |

So `applyOp` does not look inside a named group. When an error is applied
(`applyError`), only the error's own top-level operations run: its
invalidate and set-fact lines. The `Interrogate` response nested under an
invalidate line is stored with the fact (below) for later.

### Set fact

`= Path value`, where the value is one word:

- `++N` / `--N`: the fact's current value (0 if unset) plus or minus `N`.
  (The decompiler dropped the addition; it was confirmed from the raw
  instructions.)
- A word containing `/`: **copy from another fact.** The text is the target
  fact's `prefix` (`Facts.xml`) followed by the source's text. If the source
  holds a traveler name, the name is re-formatted with the target fact's
  `format`. If the source fact does not exist, the word itself is stored.
- Anything else: stored as written.

The seven `...-ConfusingName` errors use the copy form to make
`IdentityRecord/Alias` equal a name from another document.

## Tracking invalid facts

`BoothEnv` keeps `invalidFactPaths` (an ordered list) and, for each path,
the operation that invalidated it and the order in which it happened.

### Is a fact invalid? (`findInvalidFactPath`, `isValid`)

A fact is invalid when either:

- it is in `invalidFactPaths`, or
- some fact in `invalidFactPaths`, **with its current value**, invalidates
  it according to the `<invalidate>` entries in `Facts.xml`
  (`getFactInvalidatesPath`, see `facts-xml-format.md`).

The list is searched in order and the first match is returned. With no
traveler present, nothing is invalid.

This is how a rule conflict works without anything on a document being
wrong. Example from the data: `ALWAYS:Rules-ArstotzkaOnly` invalidates
`Traveler/Nationality`; `Facts.xml` says nationality invalidates
`Rules/RuleArstotzkaOnly`; so that rule now counts as invalid too, and
comparing the two is a discrepancy.

### Invalidate (`setFactInvalid`)

1. If the fact is already invalid by the test above, do nothing.
2. Otherwise **generate a new, wrong value for it**
   (`makeFactValue(path, valid = false)`), add it to the list, and record
   the operation and order.

### The `~` prefix: confusing

`! ~Path` (22 uses in `Errors.txt`) does the same, then generates the value
again in "confusing" mode (`makeFactValue(path, valid = false, confusing =
true)`), stores that, and records the path as confusing. Inside
`makeFactValue` the flag changes only `Gender`, which keeps its correct
value; every other fact simply gets a second wrong value (`fact-values.md`).

### Validate (`setFactValid`)

1. If the fact is not invalid, do nothing.
2. If the fact is `editable` in `Facts.xml`, generate a fresh **valid**
   value for it. Non-editable facts keep the value they have.
3. Record the path as "cleared", and remove it from the invalid list.

## The misspelled `whennot` in Facts.xml has no effect

`facts-xml-format.md` notes that `Traveler/Nationality` has an entry meant
to read "invalidates `Rules/RuleArstotzkaOnly` when not Arstotzka", whose
condition is never read. With the above, its effect can be judged: that
entry only matters when `Traveler/Nationality` is itself in the invalid
list. In the data, the only thing that puts it there is
`ALWAYS:Rules-ArstotzkaOnly`, which already requires the traveler not to be
Arstotzkan. So the lost condition is always true anyway. (Checked: no other
error and no traveler script invalidates `Traveler/Nationality`.)

## Not studied

- (`getSpeech` is covered in `speech.md`, `makeFactValue` in
  `fact-values.md`, `addPaper` and `saveStayingPaperIds` in
  `papers-on-desk.md`.)
- (How the stored `Interrogate` response is used is in
  `player-actions.md`; who runs named groups and button operations is in
  `responses-and-events.md`.)
- Nothing here has been compared with the running game.
