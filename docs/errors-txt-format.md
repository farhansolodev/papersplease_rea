# Errors.txt and how an error is chosen

Studied on 2026-10-12. `Errors.txt` defines everything that can be wrong
with a traveler. This document covers the file and the code that picks an
error. What an error then does to the documents (running its operations) is
not studied yet.

Functions read in full: `data.ErrorLib` (constructor, `findError`,
`getMatchingErrors`, `getErrorsForContext`), `data.ErrorMaker` (constructor,
`makeError`), `data.Error` (constructor, `getHiddenPaperId`,
`isSpeechError`, `getMatchesContext`, `collectPaperIds`).
`ErrorLib.getAlwaysErrorsForContext` was read for its logic; most of it is
debug logging identical in shape to `getErrorsForContext`, and those lines
were filtered out rather than read one by one. Two dropped details were
recovered from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## The file

It uses the indented-tree format (`tab-tree-format.md`) **with templates**:
`ErrorLib` builds the tree and calls `expandParams`. It reads the text
directly rather than through `Res.getTabParser`, so the language pack does
not alter it.

- 11 templates (top-level names starting with `*`), used 82 times.
- 110 errors: 3 whose name starts with `ALWAYS`, and 107 "random" errors.
- Three block comments and some commented-out entries.

### Templates

All eleven are named `*Interrogate` or `*Interrogate:Variant`. A line such as

```
> $Interrogate:Missing passport
```

becomes a response named `Interrogate` whose first lines are the template's
lines with `$1` replaced by `passport`. Arguments are numbered from 1.

### An error entry

```
Name<tags>    GroupId
    \ requirement
    ! Fact/Path
        > Interrogate
            " speech-id
            @ Button
            ^ Fact/Path
    = Fact/Path value
```

- **Name**: the error id. No two are the same.
- **Tags** are just part of the name: `<generic>` (69), `<deny>` (46),
  `<missing>` (20), `<obvious>` (14), `<contraband>` (5), `<speech>` (4).
  17 errors have no tag. Tags matter because errors are selected by
  matching patterns against the name.
- **GroupId**: optional second word. Without it the group is the name
  itself. 76 groups among the random errors; 45 have a single member.
- **`\` requirement** (184): decides whether the error is possible for this
  traveler. See below.
- **`!` fact** (141): a fact to make invalid, with the response to give when
  the inspector challenges it. 107 distinct paths. 22 start with `~`; with
  the `~` removed all 107 are real fact paths in `Facts.xml`. `~` marks the
  fact as "confusing" (`operations-and-fact-validity.md`).
- **`=` fact value** (7): on the seven `...-ConfusingName` errors, sets
  `IdentityRecord/Alias` to the name of another fact.
- Inside the 141 `> Interrogate` groups: 255 speech lines (74 distinct ids),
  90 buttons (`Detain` 46, `Fingerprint` 32, `Search` 12), 13 `^` validate
  lines and one `+` add-paper line.

Speech lines here are bare ids such as `ask-missing-passport`. In
`Travelers.txt` the same stock lines are written with a leading `$`. How the
two are told apart at run time is not studied.

## Loading

For each top-level entry, in file order: skip templates; build its
operations with `OpHelper.makeOp`; create an `Error(id, groupId, ops)`.
Errors whose id starts with `ALWAYS` go into one list, the rest into the
"random" list.

`Error.requiredPaperIds` is created but, as the code reads, never filled:
the function that would fill it is given the entry's outer group, which is
not a requirement, and does not look inside it.

## Is an error possible? (`Error.getMatchesContext`)

Every requirement directly under the error must hold. Requirements nested
deeper are ignored (the file has none).

- **One word**: the traveler's starting papers must include that paper.
  Used with eleven papers, most often `AccessPermit` (17) and `AsylumGrant`
  (16). All are documents in `Facts.xml`.
- **Three or more words**: a condition, evaluated exactly like the
  conditions in `travelers-txt-format.md` (left to right, case ignored).
  The left side is looked up in the error context: `FEATURES` (43 uses),
  `RULES` (17), `PURPOSE` (15), `NATION` (5), `FILTER` (2), `DISTRICT` (2),
  `CONFISCATION` (2). Operators used: `has`, `!=`, `!has`, `==`.
- Two words: ignored.

Two errors carry `\ FILTER !has ADDITIONAL`, which keeps them from being
picked as a second error (`traveler-creation.md`, step 11).

## Which errors are candidates (`getErrorsForContext`)

Given a pattern text and a context:

1. Split the text at spaces. Each piece is a **case-insensitive regular
   expression**.
2. Go through the random errors in file order. Keep an error when its group
   is not in the context's ignore list, **any** pattern matches its id, and
   its requirements hold.

So a traveler script's `= error <generic>` means "any error whose name
contains `<generic>` and is possible here", and `= error EntryPermit-Missing`
selects by name. The 28 distinct values used in `Travelers.txt` each match at
least one error, except `--`, which matches none and therefore yields no
error.

`getAlwaysErrorsForContext` returns every `ALWAYS` error whose requirements
hold: `ALWAYS:Rules-ArstotzkaOnly`, `ALWAYS:Rules-NoImpor`,
`ALWAYS:Rules-NoUnitedFed`.

## Picking one (`ErrorMaker.makeError`)

1. Get the candidates. **If there are none, return nothing, with no random
   draw.**
2. Sort the candidates into groups by group id, keeping groups in order of
   first appearance.
3. **Avoid recent groups.** For each recently used group id, newest first:
   stop if fewer than two groups remain; otherwise, if that group is among
   the candidates, drop it. At least one group always survives.
4. Draw `r1`: pick the group at `floor(groups * r1)`.
   Draw `r2`: pick the error at `floor(members * r2)` in that group.
5. If the error's id contains `<rare>`: draw `r3`; if `r3 < 0.5`, pick again
   with two more draws (step 4), with no further rare check. **No error in
   the current file has `<rare>`** (the one that did is commented out), so
   this never fires with this data.
6. Remember the chosen group as most recent. If that makes five remembered,
   forget one: the entry equal to the oldest. (The list removes the first
   entry with that value, which differs from "the oldest" only if the same
   group is in the list twice.)

Random draws per call: none when there are no candidates, otherwise two.

Edge case: a draw of exactly 1.0 (`rand.md`) would index past the end of the
list and raise an error in the original. This is roughly a one in two
billion event per draw.

The error maker is created once, by the booth environment, which is in turn
created by the booth engine for a given day. So "recent" spans every
traveler that engine handles. That there is one engine per day is inferred
from the engine taking a day as input; where engines are created has not
been checked.

## Small helpers

- `getHiddenPaperId`: if the id contains `-Hidden`, the paper is the part of
  the id before its **first** `-` (for example `Passport`). Ten errors:
  one per document type.
- `isSpeechError`: the id contains `<speech>`.

## Checks against the real file

Using the reference reader (`scripts/reference/tabtree.py`) with template
expansion:

- 768 nodes before expansion, 981 after; no template reference left over.
- No duplicate ids. Every requirement is directly under its error.
- Every condition has a well-formed shape, a known operator and a left side
  that is one of the seven context keys.
- Every invalidated fact path exists in `Facts.xml` (after removing `~`).
- Every paper requirement names a document in `Facts.xml`.
- One error has no `!` line (`Traveler-Criminal<generic>`); eight have no
  requirement, so they are always possible when selected by name.

## Not studied

- How the replacement value for an invalidated fact is generated
  (`makeFactValue`). What invalidating does is in
  `operations-and-fact-validity.md`.
- How the `Interrogate` response is run and how speech ids become text.
- `Error.validate` and `ErrorLib.validateAll` (checks run by the
  developers' tooling, by their names).
- Nothing here has been compared with the running game.
