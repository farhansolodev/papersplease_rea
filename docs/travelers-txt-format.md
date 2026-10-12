# Travelers.txt: scripted travelers and their behaviour

Started on 2026-10-12. **Only the structure is studied so far.** The file is
read as an indented tree (see `docs/tab-tree-format.md`, confirmed). What
each kind of line *means* is decided by code that has not been read yet, so
the "meaning" column below is unconfirmed throughout.

## Structure (confirmed)

- 3,346 lines. One block comment (lines 2891 to 2903) switches off a
  traveler called `IDSUPPLEMENT_DAY`.
- 185 top-level entries, each a single word: a traveler id. All distinct.
- `data.TravelerLib` keeps the tree and a pointer to the entry `DEFAULT`.
  `findTravelerNode(id)` returns the top-level entry with that id.
- 142 of the ids are named by `Days.csv`. The other 43 include `DEFAULT`
  and entries that are only pulled in by other entries (`INCLUDE`), such as
  `BOSS_APPEARANCE`.

The designer's comment on `DEFAULT` (lines 5 to 8) says it holds the default
responses, and that its conditions are evaluated when a response is needed
and can see all facts, whereas other entries' conditions are evaluated when
the traveler is created.

## Kinds of line (counts confirmed, meanings not)

Counts are after comments are removed.

| First token | Lines | Looks like | Meaning (unconfirmed) |
|---|---|---|---|
| `"` | 1,175 | `" some words` or `" $ask-purpose` | Something said. `$name` appears to refer to a stock line; `${Fact/Path}` to a fact value |
| `=` | 557 | `= nation Kolechia`, `= Game/Jorji 2` | Set a traveler property or a fact |
| `>` | 350 | `> Intro-Replace`, `> Denied`, `> Approved` | Start of a response to an event. 45 distinct event names |
| `?` | 197 | `? Traveler/Nationality != Arstotzka` | Condition; children apply when it holds. Joined with `\|\|` |
| `@` | 175 | `@ Leave`, `@ Want`, `@ News`, `@ Detain` | An action. 14 distinct |
| `+` | 123 | `+ Passport`, `+ Money10` | Give a paper |
| `INCLUDE` | 113 | `INCLUDE GENERIC` | Pull in another entry |
| `x` | 25 | | Unknown |
| `MANUALPAPERS` | 22 | | Unknown |
| `BREAK` | 19 | | Unknown |
| `!` | 6 | `! Passport/Exists` | Unknown; appears with fact paths |
| `(` | 5 | `( KillerName0` followed by `.*/Name` | Unknown; children look like fact path patterns |
| `-` | 5 | `- Passport` | Remove a paper (a file comment says "remove Passport") |
| `*` | 3 | `* Misc-DiploFollower` | Unknown |
| `^` | 1 | `^ Passport/Exists` | A file comment says "validate Exists" |

`=` lines mostly have a name and one value (477 of 557). `?` lines have one
comparison (171), two (24) or more (2).

The class `data.TravelerSpec` has properties named `nation`, `purpose`,
`job`, `district`, `duration`, `issuingCity`, `contrabandTypes`, `special`,
`forceDeny`, `slow`, `canDetain`, `leaveDir`, `want`, `face`, `gender`,
`name`, `idNumber`, `genderForced`, `fallback`, `MANUALPAPERS`, `error` and
`preventAdditionalError`. Many `=` lines use these same names. That the two
are connected is a name match only, not confirmed. `=` names seen in the
file that are not in that list include `test`, `TESTDAY` and `weight`.

## Not studied

- The code that turns a traveler's tree into a `TravelerSpec` and runs its
  responses. This is where every line kind above gets its real meaning.
- How conditions (`?`) are evaluated.
- `TravelerLib.getAllConditionalSolutions` and `data.SolutionsBuilder`.
- How the language packs alter the tree.
