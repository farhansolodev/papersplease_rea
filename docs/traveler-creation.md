# How a traveler is created

Studied on 2026-10-12. This follows one traveler from "next in line" to the
point where their documents and errors are in place. It is the top-level
sequence; several large steps it calls are listed at the end as not yet
studied.

Functions read in full: `play.day.BoothEnv.makeNewTraveler` (`0x18047e070`),
the `BoothEnv` constructor (`0x18046ca80`), `BoothEnv.applyError`,
`play.day.Day.makeTravelerSpec`, `getNextTravelerId`, `makeErrorContext` and
`makeTravelerTest`, and `data.ErrorContext` (constructor, `addToFilter`,
`expandExpressionLhs`). Two arguments the decompiler dropped were recovered
from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## Which traveler is next

`Day.makeTravelerSpec`:

```
index = min(travelerIds.length - 1, numMadeTravelers)
id    = travelerIds[index]
spec  = TravelerContext(db, storyState, id, day facts).makeTravelerSpec(travelerRand)
numMadeTravelers += 1
```

So travelers come in the order listed in `Days.csv`, and once the list runs
out **the last entry repeats for the rest of the day**. The `FILL` value is
appended last (see `days-csv-format.md`), so it is the template for every
traveler after the scripted ones. Every day in the table has one.

Building the specification from the script is in
`travelers-txt-format.md`. It uses the day's traveler random generator.

## Random generators involved

| Generator | Seed | Used for |
|---|---|---|
| `Day.travelerRand` | day seed + `0x4000` | Building the specification from the script |
| `BoothEnv.rand` | day seed - `0x7FFFF000` (32-bit wrap) | Everything below: the traveler's details, errors, the additional-error roll |

`BoothEnv`'s error maker is given the same generator object as `BoothEnv`
itself, so their draws interleave.

## When the booth is set up

`BoothEnv` is created by the `BoothEngine` constructor, which is given a
day. That this happens once per day is inferred from that; where engines are
created has not been checked.

The `BoothEnv` constructor, in order:

1. Creates its random generator and error maker.
2. Adds the paper `Rules`.
3. Sets the fact `Rules/PageMask` to the list of visible rulebook pages for
   the day's rules and confiscation id (`facts-xml-format.md`).
4. If the day has a confiscation id, sets `Rules/Confiscation` to its rule
   text.
5. If the day has a rulebook page to open, sets `Rules/OpenToPage`. (The
   `Day` constructor always leaves this empty.)
6. Sets `Rules/Upgrade0` to `Rules/Upgrade3` to image names according to the
   platform's upgrade set and which upgrades the player owns:
   - desktop: `INSPECT_HOTKEY` gives `Upgrade0 = RulesUpgrade0.png`;
     `STAMPBAR_HOTKEY` gives `Upgrade1 = RulesUpgrade1.png`; `RULEBOOK_TABS`
     gives `Upgrade2 = RulesUpgrade2.png`; `INSPECT_DOUBLECLICK` gives
     `Upgrade3 = RulesUpgrade3.png`.
   - tablet: `BOOTH_MULTITOUCH` gives `Upgrade0 = RulesUpgrade4.png`;
     `RULEBOOK_TABS` gives `Upgrade1 = RulesUpgrade2.png`.
   - phone: `RULEBOOK_TABS` gives `Upgrade0 = RulesUpgrade2.png`.
7. Adds the paper `Transcript`.
8. Adds the day's bulletin (`addBulletinForDay`, see `papers-on-desk.md`).
9. Adds each of the day's extra papers.
10. Adds each paper listed in the saved story fact `Game/StayingPapers`
    (separated by `;`).

## For each traveler

`BoothEnv.makeNewTraveler`, in order:

1. **Get the specification** (above).
2. **Carry over what persists.** Facts are kept only if they belong to a
   paper whose `stay` in `Facts.xml` is `day` or `game`, and the paper is not
   `Transcript`. Papers on the desk that do not persist are forgotten. The
   ids of the papers that remain are recorded as "had".
3. **Reset per-traveler state**: the fact groups for the traveler's nation,
   the lists of invalid and confusing facts, the transcript, and the list of
   applied errors.
4. **Build the error context**: a small table of the day's features and
   rules, the traveler's nation, purpose and district, the day's
   confiscation id and an empty filter, plus the traveler's starting papers.
5. **Make the scripted error**, if the specification has an `error`
   variable: `errorMaker.makeError(error, context)`.
6. **Create the traveler** from the specification, the error, the face and
   name sources and the day's list of criminals (`Traveler` constructor,
   see `traveler-build.md`). This can replace or drop the error.
7. If the traveler is one of the day's criminals, mark that criminal as
   used.
8. Add the traveler's custom fact groups, expanded for their nationality.
9. **Add papers**, in this order: `Traveler`, `Speech`, `Booth`, then each
   of the traveler's starting papers.
10. **Apply the traveler's error**, if any: record it and run each of its
    operations.
11. **Roll for an additional error.** Only when all of these hold: the
    traveler has an error; the specification has no custom error; the
    `error` variable was chosen from more than one option
    (`error_setRandomly` is `YES`); and `preventAdditionalError` is not set.
    Then the context's filter gets `;ADDITIONAL` appended, the first
    error's group is added to the groups to ignore, and:
    - if the first error hides a paper: one draw `r`; if
      `r < hiddenAdditionalErrorPerc` (from `Facts.xml` `<misc>`), a
      `<generic>` error is made for a context containing only the hidden
      paper;
    - otherwise, if the first error is a speech error: one draw `r`; if
      `r < speechAdditionalErrorPerc`, a `<generic>` error is made for the
      same context;
    - otherwise no draw is made.
    A made error is applied like the first.
12. **Apply the "always" errors** for the context
    (`errorLib.getAlwaysErrorsForContext`).

Note for the port: in step 11 the random draw happens only inside the two
branches, so whether a draw is consumed depends on the kind of the first
error.

## The error context

`ErrorContext` holds the traveler's paper ids, a list of error groups to
ignore, and a table with the keys `FEATURES`, `RULES`, `NATION`, `PURPOSE`,
`DISTRICT`, `CONFISCATION` and `FILTER`. When a condition names one of those
keys on its left side, the table value is used; any other left side is taken
literally.

## Reference implementation

`scripts/reference/booth.py` (written 2026-10-13 after re-reading
`makeFactValue`, `addPaper`, `setFactInvalid`, `setFactValid`,
`findInvalidFactPath`, `applyOp`, `getRandomAccessNations`,
`Criminal.selectRandom` and the criminal branch of the `Traveler`
constructor) is the whole sequence above in Python. It chains the earlier
layers: `travspec.py` (the script), `errormaker.py` (the error),
`person.py` (the person), `values.py` (wrong values), `factlib.py` (the
documents' facts) and `faces.py` (the face picture, for the height).

    python -I scripts/reference/booth.py <master seed> <day> <count> extracted\art\assets --facts

prints the first travelers of a day with their details, errors and every
generated document value (`*` marks a value that is wrong).

Details settled while writing it:

- **Criminals.** The rules in `traveler-build.md` ("Criminals") were
  re-read and are implemented here: `booth.py` hands the pick to
  `person.py`. With no candidate the traveler gets no error at all. A
  custom error in the script replaces the chosen error before the pick.
- **Wrong names move the name cycler.** A wrong name takes one or two names
  from the same name cycler that names travelers, so it changes the names of
  everyone after.

`scripts/checks/booth_check.py` (run 2026-10-13) first asks for wrong values
directly (results in `fact-values.md`), then builds 1,892 travelers over
all 31 days and four master seeds. Result: no failure; every fact not marked
wrong shows the traveler's real detail and every fact marked wrong shows
something else (name, id number, gender, height, weight, duration, purpose,
city, district, birth date, fingerprints, emblem, face); wrong expiration
dates are in the past and valid ones in the future; access-nation lists have
2 to 4 names with Arstotzka exactly when valid; vaccine lists have no repeat
and polio exactly when valid. 28 confusing-gender facts keep the real
letter, as designed. 8 to 55 booth draws per traveler, 25 on average. The
errors applied carry only requirement, invalidate and set-fact lines at
their top level (no add-paper or remove-paper line). Two runs with the same
seed print the same text.

Not modelled in `booth.py`: the bulletin's text and page mask and the
rulebook's page mask and upgrade marks (they make no draws); speech; custom
fact groups (they add no values); tokens and achievements; saving the
staying papers; anything the player does after the traveler arrives.
Travelers are made one after another with no player action in between, and
with an empty saved story unless one is passed in.

## Not studied

These are the large pieces this sequence calls:

- The saved story, and where the face and name cyclers are created.

Studied since, in their own docs: the error system (`errors-txt-format.md`),
`applyOp` (`operations-and-fact-validity.md`), `makeFactValue`
(`fact-values.md`), `addPaper` with `addBulletinForDay`
(`papers-on-desk.md`), and the `Traveler` constructor with the face and
name cyclers (`traveler-build.md`).

Nothing here has been checked against the running game.
