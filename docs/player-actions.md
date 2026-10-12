# The player's actions at the booth and how mistakes are judged (part 2)

Studied on 2026-10-13. Part 1 (`responses-and-events.md`) covers the visit's
events, responses and the citation flow. This covers what the engine does
when the player acts, and how a wrong decision is detected and punished.

Functions read in full: `BoothEngine.stampPaper`, `canGivePaperToTraveler`,
`givePaperToTraveler` (and its delayed closure), `confiscatePaper`,
`putPaperInFiler`, `removePaperFromFiler`, `interrogateFactPaths`,
`clickAction`, `printSearchPhoto`, `handleTimeBombUnscrew`,
`handleTimeBombCutWire`, `handlePaperCustomLinkClicked`, `addNewEnvPapers`,
`setEnabled`, `getEnabled`, `getPaperPoisoned`, `setPaperPoisoned`,
`shouldAutoConfiscatePaper`, `incrementTravelerIdleTime`,
`get/setPaperApproval`, `findEnginePaper`, `removePaper`,
`get/set_givenApproval`, `set_wantResist`, `closeShutter`, `debugAddPaper`,
`applyUpdatedSettings`; `EnginePaper` (constructor, `getApproval`,
`setApproval`); all of `StampApproval`; `BoothEnv.hasErrors`, `getCiteText`,
`wantConfiscatePassport`, `getOpForInvalidFactPaths`, `getFactRelationship`,
`getPaperNameInFiler`, `getNextMultiPaperIndex`, `getPaperIdWithIndexes`,
`canPutInFiler`; `Traveler.canGivePaper`; `Day.addCitation`,
`addConfiscatedPaper`, `findConfiscatedIdForPaperIdWithIndex`, `hasFeature`;
`FactLib.getPaperSayTrade`, `getCiteText`, `getShouldNoticeError`,
`getConfiscationWhen`, `getFactGroups`, `getExpandedFactGroup`;
`FactGroup.hasPath`, `getProxiedPath`, `autoGetCorrelationPairs`;
`OpHelper.getRunOps`, `getEnableButtonIds`; `Citation` constructor;
`FactSet.incInt`; `StoryState.incStat`. Dropped arguments and constants were
read from the raw instructions and the DLL's data (listed where used).

Everything here is confirmed in the code unless marked otherwise. Nothing has
been compared with the running game.

## Stamp results (`StampApproval`)

A set of flags. **Settles the part-1 open question**: approved = 2,
denied = 4, reasoned = 8 (bit `1 << kind index`; `NONE` is index 0 and is
never set).

- Set approved: only if not already denied.
- Set denied: clears approved.
- Set reasoned: adds 8.
- Combine two: reasoned if either is; then denied if either is, otherwise
  approved if either is. **Denied wins.**
- As text: the names joined with no separator (`APPROVED`, `DENIED`,
  `DENIEDREASONED`, ...); read back by "contains" tests.

Where kept: each stampable paper's result is the fact `<paper>/Approval`;
the result handed to the traveler is `Traveler/Approval`. A paper that is not
`stampable` always reads as empty and ignores writes.

## Stamping (`stampPaper(paper, kind)`)

1. **Mistake check**: if `(kind is DENIED)` differs from "the traveler has
   errors" (`hasErrors`, below), `mistakeCaught` is set. So any non-denial
   stamp on a traveler with errors, or a denial of one without, counts.
   This is the only place `mistakeCaught` is set (it is cleared at
   `EMPTY_START`).
2. Add `kind` to the paper's result.
3. `haveStampedSomething` = true; statistic `NumStamps` + 1
   (`Game/Stat/NumStamps`).

Who calls this with `REASONED` (the denial-reason stamp) is screen code, not
studied. If it is called that way, it counts as "not a denial" in step 1.

At the end of the visit (part 1) the citation for a wrong decision needs
**both** `mistakeCaught` and that the final handed-back result is still wrong
(`approved == hasErrors`), and the traveler not detained.

## Has the traveler errors? (`hasErrors`)

True if any fact in the invalid list (`operations-and-fact-validity.md`) has
`noticeErrors` in `Facts.xml` (a fact with no definition counts as not
noticed). A debug argument makes every invalid fact count; the game passes
none.

## Citation text (`getCiteText`)

For each invalid fact, in list order, whose paper (the part before the
first `/`) was on the desk at some point this visit (`hadPaperIds`) and whose
error is noticed: the fact's cite line (`FactLib.getCiteText(path, current
value text)`, the `<cite>` rules in `facts-xml-format.md`; an undefined fact
gives `UNKNOWN`). Lines are joined with line breaks. If there are none, the
text entry `env_clearforentry`.

## Penalties (`Day.addCitation`)

Citations are counted per day. The kind depends on how many the day already
has: 0 → warning (text `citation_warning`), 1 → last warning
(`citation_lastwarning`), 2 or more → penalty. Penalty cost =
`int(max(1, count_before - 2) × 5)` (constants 1.0 and 5.0 read from the
DLL), so the 3rd and 4th citation cost 5, the 5th 10, the 6th 15, and so on.
The penalty text is the `citation_penalty` template filled with the cost.
`Game/NumCitations` + 1. The citation paper gets `Citation[_n]/Message` and
`Citation[_n]/Penalty` (part 1).

## Handing papers back

### Can it be given? (`canGivePaperToTraveler`)

In order:

1. If the operation queue holds anything other than Say lines: no.
2. Not on the desk: no.
3. The paper has a `trade` (`Papers.xml`; only `FingerprintsBlank`): yes.
4. It is an envelope holding a confiscated paper the traveler wants: yes.
5. The traveler wants this paper id (below): yes.
6. Nothing stamped yet this visit: no.
7. The paper did not come from the traveler: no.
8. From the traveler and not stampable: yes.
9. From the traveler and stampable: only if stamped approved or denied.

**What the traveler wants** (`Traveler.canGivePaper`): with no `@ Want`
patterns, nothing. Otherwise no if any `@ Reject` pattern matches, else yes
if any `@ Want` pattern matches. Patterns are regular expressions matched
anywhere in the id.

### Giving (`givePaperToTraveler`)

1. If stampable: `Traveler/Approval` = combine(paper's result, current).
   Giving `Passport` sets "gave stamped passport". A `forceDeny` traveler
   has denied added.
2. If the paper is poisoned (`<paper>/Poisoned` = `YES`): the traveler is
   poisoned; response `Poisoned`.
3. A trade paper: operations [Say the received paper's `saytrade`
   (`Facts.xml`; `Fingerprints` → `trade-fingerprints`), add the received
   paper]. Applied at once, or, when the engine has a slow-mode timer,
   2 seconds later (constant from the DLL) as if from the queue.
4. The paper is removed.
5. Response `Give-<id>`, where `<id>` is the confiscated id if the paper is
   an envelope (below), otherwise the paper id. **Settles** the open
   question about the 23 `Give-...` names: the code builds them. The data
   confirms the envelope form: `Give-PASSPORT-KORDON-KALLO.*`.

## Confiscating and the filer

- **Confiscate into an envelope** (`confiscatePaper`): a new
  `FilerEnvelope` stack index; the confiscated id is
  `PAPERID-FIRST-LAST-NATION` in upper case; the title is the paper's
  localized name, " - ", the formatted name, and for passports a line break
  and the localized nation. The day records it (also in `Day/Confiscated`,
  `;`-separated); the paper is removed; operations set
  `<envelope>/Title` and add `FilerEnvelope`. Returns the envelope id.
- **Put in the filer** (`putPaperInFiler(paper, firstTime)`): the first time
  a passport goes in, a `SeizureSlip` is added. The paper is recorded as
  confiscated; for `Passport` "confiscated at some point" is set. First
  time: response `Confiscated-<paper>`.
- **Take out** (`removePaperFromFiler`): first time: response
  `Unconfiscated-<paper>`; un-recorded.
- **May it go in the filer?** (`canPutInFiler`): unless it is the
  traveler's `@ NoFiler` paper.
- **Should the passport be confiscated?** (`wantConfiscatePassport`): the
  day has a confiscation id, its `when` expression (`Facts.xml`
  `<confiscation>`) is true with the booth's condition tester
  (`responses-and-events.md`), and the passport may go in the filer.
- **Auto-confiscate** (`shouldAutoConfiscatePaper`, asked by the screen):
  after a decision (approved or denied), with the `FILER` feature, for a
  paper with filer type `CANFILER` and `stay` none.

No `Confiscated-` or `Unconfiscated-` response exists in `Travelers.txt`.

## Interrogating (`interrogateFactPaths`)

The player marks **exactly two** facts (inspect mode).

1. Find the operation: over the booth's fact groups in order (the
   nation's `Facts.xml` groups, then the traveler's custom groups, both set
   up in `makeNewTraveler`), each group that has both paths (as path or
   proxy): look up each path's proxy and whether it is invalid. Of all hits,
   the invalid fact **invalidated earliest** wins; its invalidating
   operation is used. No hit: nothing happens.
2. Its `Interrogate` response (`OpHelper.getRunOps`: searched recursively
   inside the operation; a name with `*` is a case-insensitive regular
   expression). None: nothing happens.
3. With `DENIAL_REASON`, the denial-reason button is switched on.
4. Responses run in this order: `Interrogate-Before`, then
   `Interrogate-<button>-Before` for each `@` command inside the response
   (in order, including inside condition groups); `Interrogate-Replace`, or
   if missing the first `Interrogate-<button>-Replace` that exists; if none
   replaced it, the `Interrogate` operations themselves; then
   `Interrogate-After` and each `Interrogate-<button>-After`. **Settles**
   `Interrogate-Detain-Replace` and `Interrogate-Search-Replace`.

`getFactRelationship(a, b)` (for showing a match or mismatch): the first
group with both paths decides: neither proxied path invalid → agree
(remembering whether either path had its confusion cleared), otherwise
disagree. No group with both: none. `FactGroup.autoGetCorrelationPairs`
builds pairs of a path with every other path of its group; it is used by the
test automation only (by name; callers not searched).

## Buttons (`clickAction`)

A disabled button does nothing. Buttons are bits in `enabledActions` (index
of `EngineAction`: fingerprint 0, search 1, detain 2, denial reason 3);
each change is reported to the screen.

- **Fingerprint**: switch off; add `IdentityRecord` and
  `FingerprintsBlank`.
- **Detain**: switch off; the traveler is detained. `Detain-Replace` if it
  exists and stop; else `Detain-Before`, Say `ask-detain` then `detain`,
  `Detain-After`.
- **Search**: switch off. `Search-Replace` if it exists and stop; else
  `Search-Before`, Say `ask-search` queued, `Search-After`. The photo is
  added later when the screen calls `printSearchPhoto` (adds `Photo`).
- **Denial reason**: nothing here (screen side).

## Poison, time bomb, links, idle time

- **Poison** (`setPaperPoisoned`): empties `Poison/Powder1` and `Powder2`;
  sets `<paper>/Poisoned` = `YES`; "just poisoned" = true.
- **Unscrew** screw `i`: `TimeBomb/Screw<i>` emptied; when all four
  (0 to 3) are empty, response `TimeBomb-Opened`.
- **Cut wire** `i`: `TimeBomb/Wire<i>` emptied. If any wire 0..i is still
  present: **explode**. If wire 3 is cut and all four are gone: response
  `TimeBomb-Disarmed`, disarmed. Otherwise nothing. So wires must be cut in
  order 0, 1, 2, 3.
- **Link clicked** on a paper: response `LinkClicked-<paper>-<link>`
  (settles `LinkClicked-EzicNote-open`).
- **Idle time**: added up per traveler; on passing 15 seconds (constant
  from the DLL), response `Impatient`.
- **Shutter closed** the first time per traveler: response `ShutterClose`.
- **Resisting**: `Traveler/Resisting` = `YES`/`NO`.

## Papers on the engine's desk (`addNewEnvPapers`)

Every paper in the booth whose `<paper>/Exists` fact is not invalid and that
is visible, sorted by id text, that the engine does not have yet, becomes an
engine paper and is reported to the screen.

## Cross-check with the data

`scripts/checks/actions_check.py` (run 2026-10-13):

- All 45 response names in `Travelers.txt` are accounted for: 19 fixed
  names, 23 `Give-...`, 2 `Interrogate-<button>-Replace`, 1
  `LinkClicked-...`. Seven names the code asks for are defined by no
  traveler: `Detain-Before`, `Enable-Fingerprint`, `Enable-Search`,
  `Interrogate-After`, `Interrogate-Before`, `Search-Before`,
  `Search-Replace`.
- The 23 `Give-` targets: 19 paper ids, 2 patterns matching paper ids, 2
  confiscated ids (`PASSPORT-FIRST-LAST...`). The 18 distinct `@ Want`
  targets are of the same three kinds. Five `Give-` papers have no `Want`
  anywhere (`BizCard`, `BrothelHelp`, `Locket`, `SpyDocs`, `SpyDocsFake`);
  they can only be handed back by rules 6 to 9.
- `@ Reject` is used twice (`BizCard`, `Money10`), `@ NoFiler` once
  (`Passport`). A reject pattern only has an effect on a traveler that also
  has a want pattern.
- `Errors.txt`, with templates expanded: all 141 invalidate lines carry an
  `Interrogate` response. The `@` commands inside them are `Detain` (46),
  `Fingerprint` (32) and `Search` (12), so those are the only
  `<button>` names that can occur.
- The one custom link in `Papers.xml` is `#custom-open` on `EzicNote`,
  matching `LinkClicked-EzicNote-open`. That the screen strips `#custom-`
  is inferred from this.
- Only `FingerprintsBlank` has a trade (for `Fingerprints`), and only
  `Fingerprints` has a `saytrade`. Only the seven `Passport` variants have
  `canconfiscate`, so auto-confiscation concerns passports only.
- Errors are "not noticed" for the `BrothelHelp` document and the four
  `Bulletin/News` facts; everything else is noticed.
- The time bomb's eight facts and the poison's two exist in `Facts.xml` with
  image names as values. `FilerEnvelope/Title`, `Citation/Message` and
  `Citation/Penalty` have no fact definition; the code sets them anyway.
- The text entries and speech ids named above all exist.
- `Facts.xml` has 59 fact groups with 162 paths, 13 of them with a proxy.

## Notes for the port

- `mistakeCaught` is decided at stamp time with the errors at that moment;
  later fixes by responses (validating a fact) only matter through the
  second check at the end.
- Denied beats approved when results are combined.
- Keep the response order of interrogation and the "earliest invalidated"
  rule.
- A set-fact on a path with no definition must still work (the envelope
  title and the citation texts rely on it).

## Not studied

- The screen side: who calls these functions and when, the denial-reason
  button, how wires and screws are numbered on screen, when the engine is
  given a slow-mode timer.
- Nothing here has been compared with the running game.

(Settled later: the `Want` and `Reject` patterns are both created as
case-insensitive regular expressions, `Traveler.addWantPaperId` and
`addRejectPaperId`.)
