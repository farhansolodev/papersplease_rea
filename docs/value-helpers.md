# Helpers behind document values: wrong names, aliases, typos, faces, fingerprints and dates

Studied on 2026-10-13. These are the small functions `makeFactValue`
(`fact-values.md`) calls to make a value deliberately wrong, plus the date
type every date fact uses.

Functions read in full: `TravelerName` (`getFormatted`, `isEqual`,
`getRandomInvalidated`, `getRandomInvalidatedImp`, `getRandomAlias`);
`Lang` (static setup, constructor, `buildAliasSwapSets`, `makeAlias`,
`makeTypo`, `getReplaced`); `Uppercaser` (constructor, `toUpperCaseU`);
`FaceSpec.getInvalid` and `clone`; `FingerprintCode.makeInvalid` and
`fromString`; `Settings` (static setup, constructor, `formatDate`);
`GregorianDate` (static setup, `fromYMD`, `split`, `get_year`, `get_month`,
`get_day`, `int`, `afterDays`, `afterYears`, `format`). Numbers the
decompiler dropped (the thresholds, the date constants, the alias text key,
the format arithmetic) were read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise. All
random draws are from the generator passed in, which for document values is
the booth's (`traveler-creation.md`).

## Names

### Layouts (`getFormatted`)

| Format (`Facts.xml` `format`) | Result |
|---|---|
| `Last, First` | `Last, First` as written |
| `FIRST LAST` | `FIRST LAST`, upper case |
| `LAST,/FIRST` | `LAST,` line break `FIRST`, upper case |
| `FIRST/LAST` | `FIRST` line break `LAST`, upper case |
| anything else, or none | `First Last` as written |

Upper case here is .NET's invariant upper-casing, not the `Uppercaser`
table below.

Two names are **equal** when first and last names are the same text;
gender is not compared.

### A wrong name (`getRandomInvalidated`)

Repeat until the result is not equal to the real name. Each try makes one
draw `r`:

| `r` | Result |
|---|---|
| below 0.5 | new first name **and** new last name, taken from **two** separate names from the name cycler |
| 0.5 to below 0.75 | new first name, same last name |
| 0.75 or more | same first name, new last name |

New names come from the name cycler for the traveler's gender. **Every
name taken advances the cycler and saves its position**
(`traveler-build.md`), so wrong names change which names later travelers
get.

### An alias (`getRandomAlias`)

One draw `r`, then:

- **Men**: below 0.5, an alias of the first name; otherwise an alias of the
  last name.
- **Women**: below 0.333, an alias of the first name; 0.666 or more, the
  last name is replaced by the last name of the next **female** name from
  the cycler; otherwise an alias of the last name.

The result is not checked against the real name.

## Alias of a word (`Lang.makeAlias`)

An alias changes exactly one letter into a similar one.

**Swap sets** are built once when the language is loaded: the text entry
`env_typochars` from `Text.xml`, a comma, and the built-in
`aeiou,iuy,pgq,lj,ck,bh`; split at commas and trimmed; each set also in
upper case (using `Uppercaser`); the letters of each set sorted; duplicate
sets removed. The resulting list is in **hash order** (it comes out of a
`StringMap`). In English `env_typochars` is the same as the built-in text,
so there are 12 distinct sets, in this order (`haxe-maps.md`): `CK, IUY,
JL, aeiou, jl, bh, GPQ, BH, gpq, AEIOU, iuy, ck`.

Making an alias of a word:

1. For each character position, list the swap sets that contain that
   character (in swap-set order).
2. If no position has any, make a typo instead (below).
3. One draw: pick a position, from the positions in the order an `IntMap`
   gives them, which is often not left to right (`haxe-maps.md`).
4. One draw: pick one of that position's swap sets.
5. Draw a letter from that set, one draw each time, until it differs from
   the original letter.
6. Replace that one character.

## Typo (`Lang.makeTypo`)

A typo **removes one character**. Up to 10,000 tries: one draw `r`,
position `i = int(r × (length − 2.0001) + 1)`, which is never the first
character and practically never the last. Accept `i` if neither that
character nor the one before it is `-`, `.` or a space. After 10,000 failed
tries the last position drawn is used anyway.

## Wrong face (`FaceSpec.getInvalid`)

A copy with four draws, in this order: nose/mouth, eyes, shoulders, head.
Each piece becomes `(piece + floor(18 × r + 1)) mod 20`, a shift of 1 to 18,
so **every piece is different**. Palette and mirror flag stay the same.

## Wrong fingerprints

`makeFactValue` makes a new fingerprint code (five draws plus redraws,
`traveler-build.md`), then `makeInvalid` goes through the five fingers in
order and redraws each one (`floor(10 × r)`) while it equals the traveler's.
So **all five fingers differ**. The constructor's rule that neighbouring
fingers differ is not applied again.

`FingerprintCode.fromString(rand, text)` makes a random code (using up its
draws) and then overwrites finger `i` from character `i`: `-` gives −1, a
digit gives that digit, anything else 0. Its only caller is
`BoothEnv.getImage`, for the fingerprint and thumbprint pictures (searched
2026-10-16, `fact-pictures.md`).

## Dates (`app.GregorianDate`)

A date is a **Julian Day number** held in a floating-point number. Months
count from 0.

- **From year, month, day**: with `m = month + 1`, and for January and
  February `m + 12` of the year before: `floor(y / 4) + table[m] + day +
  365 y − floor(y / 100) + floor(y / 400) + 1721118.5`, where the table
  gives the days before each month counting from 1 March (March 0, April
  31, ..., February 337).
- **Back to year, month, day**: the standard method that counts from
  1 March of year 0 (constants 1721118.5, 36524.25, 365.25, 153 and 5). Any
  fraction of a day is dropped.
- **Checked**: `scripts/reference/gdate.py` implements both directions as
  read. For every day from 1800 to 2200 (146,462 days) it agrees exactly
  with Python's own calendar. 23 November 1982 is Julian Day 2445296.5.
- `afterDays(n)` adds `n`. `afterYears(n)` adds `n × 365.242199` days, so a
  birth date from a fractional age (`traveler-build.md`) lands on some day
  with a fraction, which is dropped when shown.
- **Text** (`format`): `%y` is the year mod 100 with no leading zero, `%Y`
  the full year, `%m` and `%d` are two digits.

### The player's date format (`Settings.formatDate`)

| Index | Short | Long | Example shown in the options |
|---|---|---|---|
| 0 | `%y.%m.%d` | `%Y.%m.%d` | `1982-1-23` |
| 1 | `%d.%m.%y` | `%d.%m.%Y` | `23-1-1982` |
| 2 | `%m.%d.%y` | `%m.%d.%Y` | `1-23-1982` |

The index is the player's setting `dateFormatIndex`; an index out of range
uses 0. A new `Settings` starts at 0; its constructor then reads the saved
value from the `settings` entry of the save folder, if there is one
(`save-format.md`; a real settings file held `dateFormatIndex` 0). Day 1 in
format 0 is `82.11.23` (short) and `1982.11.23` (long).

## Upper case (`Uppercaser`)

Reads `UpperCase.txt`: one mapping per line, `0x` code point, a space, the
upper-case text. Lines without exactly two parts are skipped. The file has
1,115 mappings; 102 map to more than one letter (for example `ß` to `SS`),
and its ASCII part matches ordinary upper-casing. Characters not in the
table are kept. Used for the alias swap sets and for upper-case document
values (`fact-values.md`).

## Text with placeholders (`Lang.getReplaced`)

Given up to three values, replaces `$0`, `$1`, `$2`. Given a string-keyed
map instead, replaces `$key` with each value, in the map's hash order. Given
another list, replaces numbered placeholders in turn (the numbering was
dropped by the decompiler and not checked).

## Reference implementation

`scripts/reference/values.py` (written 2026-10-13 after re-reading
`TravelerName`, `buildAliasSwapSets`, `makeAlias`, `makeTypo`,
`FaceSpec.getInvalid`, `FingerprintCode.makeInvalid` and
`invalidateIdNumber`; the constants 0.75, 0.333, 0.666 and 0.0001 were read
from the DLL) implements everything in this document except the date type,
which is in `gdate.py`. It builds the swap sets from `Text.xml` and
`UpperCase.txt` through the lookup-table model (`haxemap.py`) and gets the
same order as listed above.

Its self-checks, over 1,500 name parts and 300 seeds: an alias changes
exactly one letter and uses at least three draws (3 for about 70% of names,
up to 11 seen); every name part has at least one swappable letter, so the
typo fallback never fired; a typo removes one character and never the first;
a wrong face has four different pieces within 0 to 19 and uses four draws;
wrong fingerprints differ on all five fingers; an altered id number differs
in exactly one place; a wrong name is never the real one.

Two details the code makes explicit: a typo only checks the removed
character and the one **before** it against `-`, `.` and space (the one
after may be a space); and reading a position outside a word gives nothing
rather than an error, which matters for one- and two-letter words.

## Notes for the port

- Count the draws exactly: wrong names loop; an alias makes at least three
  draws; a typo at least one; a wrong face four; wrong fingerprints five
  plus redraws.
- Wrong names and female aliases take names from the shared name cycler.
- The alias swap-set order (a `StringMap`) and position order (an `IntMap`)
  are hash orders; both are worked out in `haxe-maps.md`.

## Not studied

- (`SpeechLib.applyGenderSwitches` is in `speech.md`.)
- (Answered 2026-10-14: the saved date-format setting is loaded by the
  `Settings` constructor, `save-format.md`. Which screen changes it is not
  studied.)
- Nothing here has been compared with the running game.
