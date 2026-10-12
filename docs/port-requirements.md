# Exactness rules for the port

A running list of behaviours the Rust port must copy exactly for a given
seed to produce the same game as the original. Each item points to the doc
with the evidence. Collected 2026-10-13; add to it as more is studied.

## Randomness

- Use the game's generator: sfc32 with the game's seeding (`rand.md`).
- `random()` returns 0.0 to 1.0 **inclusive**. `floor(length * r)` can
  equal `length`; the original then yields nothing (pick one) or raises an
  error (error selection). Decide and document what the port does.
- Keep the generators separate: per day there are news, border, night and
  traveler generators (`days-csv-format.md`) and the booth's own
  (`traveler-creation.md`). The booth and its error maker share one.
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
    twice (`fact-values.md`).
- Pick, weighted pick and shuffle procedures: `facts-xml-format.md`.

## Order

- Haxe `List.push` adds to the **front**; `List.add` to the back. The
  original uses `push` for: papers in `PaperDefLib` (so lookups see the file
  in reverse), a traveler's starting papers, the recent error groups, and
  the compiled error patterns.
- A `StringMap` is iterated in hash order, not insertion order. Where the
  original iterates one (expanding `*` patterns in fact groups, carrying
  facts between travelers), do not assume file order. Whether any outcome
  depends on that order has not been checked.
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

## Dates

- Day `n` of the story is 23 November 1982 plus `n - 1` days. Month numbers
  in the date helpers start at 0.
