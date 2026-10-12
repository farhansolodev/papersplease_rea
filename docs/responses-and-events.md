# The booth's events, responses and operations (part 1)

Studied on 2026-10-13. This covers how the booth engine reacts to the steps
of a traveler's visit: which scripted **responses** it runs, how their
conditions are tested, how their **operations** are applied and spaced out in
time, what the `@` button commands do, and how the game decides at the end of
a visit whether you earn a **citation**. The player's own actions (stamping,
handing papers back, confiscating, interrogating, detaining, fingerprinting,
searching) are part 2: `player-actions.md`. Wherever this file says
"part 2", that is the place.

Functions read in full: `play.day.BoothEngine.handleEvent` (`0x180468a30`),
`applyTravelerResponseOps`, `applyDefaultResponseOps`,
`expandConditionalOps`, `applyOps`, `applyNextQuedOp`,
`hasEnableButtonOpInQue`, `speak`, the `BoothEngine` constructor;
`BoothEnv.getDefaultRunOps`, `findDefaultRunOpNode`, `testExpression`,
`expandExpressionLhs`; `data.OpQue` (constructor, `push`, `pop`, `delay`,
`hasOnlySayOps`, `hasEnableButtonOp`, `lastTimeToPop`); the `EngineEvent`
static setup. Text keys and timing constants the decompiler dropped were
read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## The visit, event by event (`handleEvent`)

The screen code reports each step of a visit to the engine as an event. In
order of a normal visit:

| Event | What the engine does |
|---|---|
| `ENTERING_START(before6PM)` | **Create the next traveler** (`BoothEnv.makeNewTraveler`, `traveler-creation.md`); remember whether they entered before 6 PM; tell the screen the transcript changed |
| `ENTERING_FINISH` | Clear "just made a mistake" and "just poisoned"; ask the screen to open the shutter |
| `WELCOMING_START` | Unless the traveler is special, the inspector says the text entry `papers_please`. Count one more traveler |
| `WORKING_START` | Put the traveler's papers on the desk (`addNewEnvPapers`, part 2); clear the operation queue |
| `WORKING_INTRO` | Run responses `Intro-Before`; then `Intro-Replace`, and only if the traveler has none, the default `Intro`; then `Intro-After` |
| `WORKING_FINISH` | Switch off the Fingerprint, Detain, Search and denial-reason buttons |
| `WAITINGTOLEAVE_START` | See "Leaving" below |
| `PROCESSING_FINISH` | Decide on a citation and update statistics; see "Citations" below |
| `EMPTY_START` | Remove the papers that do not stay (`stay` none); forget the traveler; reset the stamp result, "has stamped", "mistake caught", "wants to leave early", "resisting", the confiscated list and "approved/denied responses run" |

### Leaving (`WAITINGTOLEAVE_START`)

1. If the passport was confiscated at some point and a stamped passport was
   never handed back, set `Traveler/PassportConfiscated` to `YES`.
2. If the traveler is resisting, stop here.
3. Once per traveler: if the stamp result includes **approved**, run the
   traveler's `Approved` and `ApprovedDenied` responses; if neither exists
   and the traveler is not special, run the default `Approved`. Otherwise
   run `Denied` and `ApprovedDenied`; if there is no traveler `Denied`, run
   the default `Denied`.
4. Unless now resisting, run the traveler's `Leave` responses.

## Running responses

A response is a named group of operations (`> Name` in `Travelers.txt`,
`travelers-txt-format.md`).

- **Traveler responses** (`applyTravelerResponseOps`): looked up in the
  current traveler's own script by name (patterns allowed). Returns whether
  one was found.
- **Default responses** (`applyDefaultResponseOps`): looked up in the
  `DEFAULT` entry of `Travelers.txt`. The engine only asks for defaults by
  name in the cases listed above (`Intro`, `Approved`, `Denied`).

### Finding a default response (`findDefaultRunOpNode`)

The `DEFAULT` entry is walked in file order:

- `> Name` with the wanted name: found; stop.
- `? condition`: if the condition holds, search inside it. If found there,
  stop; otherwise **continue with the next line** after the block.
- `BREAK`: stop with nothing found.
- Anything else is skipped.

In the data (`scripts/checks/responses_check.py`), `DEFAULT` has three
`Intro`s for non-Arstotzkan travelers when an entry or access permit is
required (one for immigrants and diplomats, one for asylum seekers, one for
everyone else), two `Approved` (passport confiscated or not) and one
`Denied` (only when the passport was confiscated).

## Conditions at the booth

Conditions in responses (`? ...` groups) and in `Speeches.txt` lines use the
same comparison code as traveler scripts (`ExpressionTester`,
`travelers-txt-format.md`): left to right, no precedence, case ignored,
unknown operators false. At the booth the **left side is any fact path**,
looked up in the day's facts (`Day/...`), the saved story (`Game/...`,
`Night/...`) or the booth's facts (everything else, for example
`Traveler/Nationality`); a missing fact is empty text. `PASSTHROUGH` is not
looked up, so `INCLUDE` groups always run. There is no `RANDOM100` here.

A `?` line in `Speeches.txt` may be written without spaces
(`Passport/Gender==F`); it is then split into left, operator and right with a
pattern.

**Settles an open question**: the misspelled
`? Traveler/PassportConfiscated =! YES` in `EZIC_DIPLO` goes through this
code, `=!` is not an operator, so that group never runs: the traveler never
says the "Barbarian." line under it.

## Applying operations (`applyOps`)

1. **Conditional groups are flattened first** (`expandConditionalOps`): a
   group whose name starts with `?` is replaced by its operations if the
   condition holds (recursively), or dropped. Other named groups (for example
   a nested `> Interrogate`) are **dropped** here; they only run when asked
   for by name.
2. Any `@ Leave` or `@ Leave Left` in the list switches off the Fingerprint,
   Detain and Search buttons at once.
3. Each operation in order:
   - If it does not come from the queue: when the queue already has items,
     it is **queued** behind them; when the queue is empty, a Say is queued
     and anything else is applied now.
   - Button commands (`@`) are handled by the engine (below).
   - Everything else is applied to the booth (`BoothEnv.applyOp`,
     `operations-and-fact-validity.md`). Papers it added, removed or changed
     are collected; a speech is passed to the screen, and a line ending in
     `~` adds a pause.
4. Afterwards, changed papers are redrawn, new papers are put on the desk
   and removed papers are taken off.

### The queue and its timing (`OpQue`)

- An operation is popped when the clock reaches its time.
- Adding to an empty queue: due now. Adding behind a Say: the last item's
  time plus the delay. Adding behind anything else: the last item's time
  plus 0.001 seconds.
- The delay is 1.5 seconds (0 in "fast" mode); for travelers marked `slow`
  it is 3.
- A line ending in `~` pushes everything still queued back by 1.5 seconds
  (3 for `slow` travelers).
- Each popped operation is applied as above, marked as coming from the
  queue.

### Button commands (`@`)

| Command | Effect |
|---|---|
| `Fingerprint` | Only with the `FINGERPRINT` feature, and if neither `Fingerprints` nor `FingerprintsBlank` is on the desk: enable the Fingerprint button and run responses `Enable-Fingerprint` |
| `Detain` | Only with the `DETAIN` feature, once per traveler, and if the traveler can be detained: enable Detain and run `Enable-Detain` |
| `Search` | Only with the `SEARCH` feature and if no `Photo` is on the desk: enable Search and run `Enable-Search` |
| `Custom name` | Ask the screen for a custom action `name` |
| `Leave`, `Leave Left`, `Leave Right` | The traveler leaves early. `Leave Right` sets the stamp result to **approved**; `Leave Left` adds **denied** and **reasoned**. If resisting, run `Leave` responses first. If the screen takes the early leave, **the remaining operations are not applied** |
| `Resist` / `Unresist` | Start or stop resisting |
| `News id` | Add a news item for the traveler (`Day.addTravelerNews`) |
| `Want pattern`, `Reject pattern` | Add a wanted or rejected paper pattern (`traveler-build.md`) |
| `NoFiler paper` | That paper may not go in the filer |
| `Night id` | Add a night event |
| `Tomorrow id` | Add a visitor for tomorrow |
| `End id` | Ask the screen to end the game with that ending; the remaining operations are not applied |
| `Break` | The remaining operations are not applied |

Every `@` line in `Travelers.txt` is one of these (checked: 175 lines).

## Citations (`PROCESSING_FINISH`)

At the end of each visit the engine builds a list of reasons:

1. Unless the traveler has `forceDeny`:
   - With the `FILER` feature: if the passport should have been confiscated
     (`BoothEnv.wantConfiscatePassport`, part 2) and the traveler gave one
     that was not confiscated, the reason is the day's confiscation error
     text (`Facts.xml` `<confiscation error>`). If it should not have been and
     it was, the text entry `unauth_confiscation`.
   - If a mistake was caught (part 2) and the traveler was not detained, and
     **"approved" equals "the traveler has errors"** (approving someone with
     a problem, or denying someone without one): the lines of the booth's
     citation text (`BoothEnv.getCiteText`, part 2) are added, and the
     denial-reason check below is skipped.
   - With the `DENIAL_REASON` feature: denied without a reason adds the text
     entry `missing_reason`.
2. **No reasons**: on the landscape (desktop) layout a traveler who entered
   after 6 PM counts as unpaid; otherwise paid.
3. **Reasons**: a citation is made. If it fits (the reasons would take fewer
   than four lines on the `Citation` paper's message area, measured with its
   font), the text entry `protocol_violated` goes first. The day records the
   citation (`Day.addCitation`, part 2), and the operations "set
   `Citation[_n]/Message`", "set `Citation[_n]/Penalty`" and "add paper
   `Citation`" are applied.
4. Statistics: `NumProcessed` + 1; with a citation `NumCitations` + 1;
   `NumDetained` + 1 if detained, otherwise `NumApproved` or `NumDenied` + 1
   unless the traveler is special. In endless mode the course is told
   `mistake`, `detain` or `process`.

The stamp result has four flags: approved, denied, reasoned (a denial
reason was given), and none. They are named in `StampApprovalKind`;
`APPROVED`, `DENIED` and `REASONED` are the bits 2, 4 and 8 tested here
(confirmed in `player-actions.md`).

## Response names

Of the 45 response names in `Travelers.txt`, 19 appear as text in the code,
so the engine calls them by name: `Approved`, `ApprovedDenied`, `Denied`,
`Detain-After`, `Detain-Replace`, `Enable-Detain`, `Impatient`,
`Interrogate`, `Interrogate-Replace`, `Intro`, `Intro-After`,
`Intro-Before`, `Intro-Replace`, `Leave`, `Poisoned`, `Search-After`,
`ShutterClose`, `TimeBomb-Disarmed`, `TimeBomb-Opened`. The others are
`Give-...` (23), `Interrogate-Detain-Replace`, `Interrogate-Search-Replace`
and `LinkClicked-EzicNote-open`; the code builds these from parts
(confirmed in `player-actions.md`, which also lists the names the code asks
for that no traveler defines, such as `Enable-Fingerprint` and
`Enable-Search`).

## Notes for the port

- Keep the order of operations and the queue rules exactly: whether an
  operation runs now or later changes what the player sees, and `Break`,
  `End` and early leaving cut the list short.
- The citation reasons come in a fixed order: confiscation, cited facts,
  missing reason.
- Timing values are in seconds of game time.

## Not studied

- (The player's actions, how `mistakeCaught` is set, `hasErrors`,
  `getCiteText`, `wantConfiscatePassport`, penalties, `addNewEnvPapers` and
  `StampApproval` are now in `player-actions.md`.)
- The screen code that sends the events.
- Nothing here has been compared with the running game.
