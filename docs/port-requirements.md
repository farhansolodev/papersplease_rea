# Exactness rules for the port

A running list of behaviours the Rust port must copy exactly for a given
seed to produce the same game as the original. Each item points to the doc
with the evidence. Collected 2026-10-13; add to it as more is studied.

## Randomness

- Use the game's generator: sfc32 with the game's seeding (`rand.md`).
- Derive every generator from one master seed exactly as the original does:
  story seeds from `Rand(master + 73)`, one at start-up and one more per
  loaded save; endless seeds from `Rand(master + 26)`; face and name cyclers
  from the master seed (`run-and-seeds.md`, `scripts/reference/seeds.py`).
  The story seed is not saved. Make the master seed settable for tests.
- `random()` returns 0.0 to 1.0 **inclusive**. `floor(length * r)` can
  equal `length`; the original then yields nothing (pick one) or raises an
  error (error selection). Decide and document what the port does.
- Keep the generators separate: per day there are news, border, night and
  traveler generators (`days-csv-format.md`) and the booth's own
  (`traveler-creation.md`). The booth and its error maker share one.
- Faces and names come from long-lived cyclers with their own generators,
  not from the day. The face cycler's sequences have overlapping seeds; the
  name cycler's position is saved with the game and advances even for
  scripted names (`traveler-build.md`).
- Draw **exactly** when the original does:
  - a `=` line in a traveler script draws even with a single value
    (`travelers-txt-format.md`);
  - `RANDOM100` draws each time it is evaluated;
  - unset details are filled in a fixed order: nation, purpose, job,
    district, duration, issuing city, gender;
  - error selection draws nothing when there are no candidates, otherwise
    two (`errors-txt-format.md`);
  - the additional-error roll draws only for hidden-paper and speech errors
    (`traveler-creation.md`);
  - each fact value has its own draw pattern, and `~` facts are generated
    twice (`fact-values.md`);
  - building the person draws in a fixed order with several conditional
    steps (`traveler-build.md`, "Order of draws");
  - speech draws once per stock response with a fitting line, once more per
    `$` reference inside it, and once per `;` alternative (`speech.md`);
  - adding a paper draws once for its expiration date only if the document
    has an `ExpirationDate` fact, then generates every empty fact **even if
    the value will be discarded** because the path already exists
    (`papers-on-desk.md`).
- Pick, weighted pick and shuffle procedures: `facts-xml-format.md`.

## Order

- Responses and operations: conditional groups are flattened before
  anything runs; operations run now or are queued by the queue rules;
  `Break`, `End` and an early leave cut the rest of the list; a default
  response search continues after a true condition block that did not
  contain the name (`responses-and-events.md`).
- Haxe `List.push` adds to the **front**; `List.add` to the back. The
  original uses `push` for: papers in `PaperDefLib` (so lookups see the file
  in reverse), a traveler's starting papers, the recent error groups, and
  the compiled error patterns.
- A `StringMap` is iterated in hash order, not insertion order. Where the
  original iterates one (expanding `*` patterns in fact groups, carrying
  facts between travelers, saving staying papers), do not assume file
  order.
- **At least one outcome does depend on that order**: when a paper is put on
  the desk, its empty facts are generated in the hash order of a fresh
  `StringMap` (`papers-on-desk.md`). `VaccineCert` has two facts that draw
  random numbers, so their order decides who gets which draws. Aliases also
  depend on hash order: the swap-set list comes from a `StringMap` and the
  letter positions from an `IntMap` (`value-helpers.md`). Both tables are
  worked out in `haxe-maps.md` and modelled in
  `scripts/reference/haxemap.py` (text hash checked in the emulator).
- `Days.csv` carry-over lists are built left to right through the day
  columns.

## Text and parsing

- `Facts.xml` is not valid XML (a raw `&&`); read it leniently. Attribute
  names are case-sensitive.
- Ignore the attributes the game never reads: listed in
  `papers-xml-format.md` and `facts-xml-format.md`. In particular the
  misspelled `whennot` must stay unread.
- The indented-tree reader: tabs only, `#` cuts a line anywhere, block
  comments first, speech-line rule, quoted tokens keep backslashes
  (`tab-tree-format.md`). Templates apply to `Errors.txt` only, arguments
  numbered from 1.
- Conditions: left to right with no precedence; both sides lower-cased;
  unknown operators are false; numeric comparisons treat non-numbers as 0
  (`travelers-txt-format.md`).
- Rule tests are substring tests on the joined rules text
  (`facts-xml-format.md`).
- Error ids are matched as case-insensitive regular expressions; a fact
  group path or response name containing `*` is also a regular expression.
- Out-of-range reads of a Haxe array give nothing rather than failing, and
  `Std.parseInt` of non-numeric text gives nothing (usually treated as 0).

## Data quirks to preserve, not fix

- `BREAK` stops the whole traveler; `fallback` discards and rebuilds.
- The `=!` operator typo in `EZIC_DIPLO` (pending confirmation of its
  effect).
- An invalid weight is always lower; a valid vaccine list always has polio;
  a valid access list always has Arstotzka (`fact-values.md`).
- The "rare error" re-roll exists but no error uses it.
- Removing a paper keeps its facts; a re-added paper keeps the old values.
  A stackable paper's index is one more than the highest present. With no
  notice pages the bulletin emblem goes to `Bulletin/Emblem-1`
  (`papers-on-desk.md`).

## Dates

- Day `n` of the story is 23 November 1982 plus `n - 1` days. Month numbers
  in the date helpers start at 0.
- Dates are Julian Day numbers in a float; use the same conversion
  (`scripts/reference/gdate.py`), `afterYears` as `years × 365.242199` days,
  and the three player date formats (`value-helpers.md`).
