# MODLOG

A running log of what changed and what was tested. Newest entries go at the top,
below this header. "Tested" means it was actually run; otherwise write
"not tested". Log failures too. Keep each field to a line or two.

```markdown
## [Date] [short title]

**Changed:** what was changed, and in which files
**Why:** the problem or goal
**Tested how:** what was done to check it
**Result:** what happened, with numbers or log lines where possible
**Still broken / not tested:** be honest
**Next:** what to do next
```

## 2026-10-13 Sounds.xml (remaining data files, fifth)

**Changed:** added `docs/sounds-xml-format.md` and `scripts/checks/sounds_check.py`; updated `docs/data-files.md` and the checks README.
**Why:** next of the remaining data files; two earlier steps left open where sounds and songs are defined.
**Tested how:** read the file with its comments; decompiled and read `SoundDefLib`, `SoundDef`, `Speaker` (constructor, `play`, `music`) and `Music.play` / `playNow`; read three constants from the DLL (default volume 1, default fade 3, song volume 1); ran `sounds_check.py`, which models the choice of recording with the existing shuffled-sequence reference.
**Result:** `problems: none`. 94 sounds, all asked for by the code or a data file. Findings: songs have no table, a song id is played as `<id>.ogg`; a sound with more than two recordings cycles through a shuffled order of exactly three, so the fourth recording of `text-reveal` and `chain-jingle` is never played; sound choice uses its own generator (seed 23). Failure on the way: the check first called a method name the shuffled-sequence reference does not have (fixed).
**Still broken / not tested:** not compared with the running game. The audio files are not extracted, so their existence is not checked. The audio platform layer, fading, rooms, beat tracking and the full list of songs are not studied.
**Next:** the next data file (`Paths.xml`, `Fonts.xml`, `Emblems.xml`, `Bodies.xml`, `BorderAnim.xml`, the endless-mode files).

## 2026-10-13 Text.xml (remaining data files, fourth)

**Changed:** added `docs/text-xml-format.md` and `scripts/checks/text_check.py`; updated `docs/data-files.md` and the checks README.
**Why:** next of the remaining data files; most other parts read their text from it.
**Tested how:** inventoried the file; decompiled and read the `Lang` constructor and static setup, `loadFromXml`, `cleanHtml`, `formatVerboseDate`, `Repl` and `LangFixed`; read the dropped month adjustment (`+ 1`) from the raw instructions and resolved the function's strings; ran `text_check.py`.
**Result:** `problems: none`. 192 entries, no repeats. The first entry loaded for an id wins; the English file needs none of the six text replacements the loader makes; the long date uses month entries numbered from 1 (`November 23rd, 1982`). 172 ids are asked for by the code or data; 20 have no reference found (listed in the doc).
**Still broken / not tested:** not compared with the running game. Language packs and the other callers of `loadFromXml` not studied; the 20 unreferenced ids not pursued; `title_news` / `title_tall` assumed to be font names.
**Next:** the next data file (`Sounds.xml`, `Paths.xml`, `Fonts.xml`, `Emblems.xml`, ...).

## 2026-10-13 Ends.xml and Intro.xml (remaining data files, third)

**Changed:** added `docs/ends-xml-format.md`, `scripts/checks/ends_check.py` and `scripts/ghidra/read_doubles.py` (reads a numeric constant from the DLL; replaces a scratch copy that was lost); updated `docs/data-files.md` and the checks README.
**Why:** next of the remaining data files; the night's endings point into it.
**Tested how:** read both files with their comments; decompiled and read `EndLib`, the page-showing closures of `play.screen.Intro`, and the parts of the `EndScreen` constructor that read the ending's attributes; read the sound delay (2.0) from the DLL; ran `ends_check.py`.
**Result:** `problems: none`. 20 endings, 149 pages; every attribute in the files is read by the code; all pictures exist; the facts and the condition the escape ending uses are the ones the `Escape` command sets; every ending is asked for by something. Finding: `Ends.xml` is not strict XML (comments made of dashes), so the port needs a lenient reader.
**Still broken / not tested:** not compared with the running game. Not read: the slide player's timing and input, the rest of the ending screen, how the endings seen are recorded, where the six shooting endings are asked for, where songs are defined.
**Next:** the next data file (`Paths.xml`, `Sounds.xml`, `Text.xml`, ...).

## 2026-10-13 The night: family, budget and going to sleep

**Changed:** added `docs/night.md` and `scripts/checks/night_check.py`; extended `scripts/reference/nights.py` with the whole night (`Member`, `Summary`, `Family`, and `Budget` total / profit / balance / will-pay); updated `docs/nights-txt-format.md` and the checks README.
**Why:** finishes what the `Nights.txt` step started: which events run, the family's health, the standard budget lines, debt and death.
**Tested how:** decompiled and read the `Family` constructor and `applyBudget`, `FamilyMember`, `Stat` and the `Budget` functions; recovered the dropped attack-event and sickness-message choices from the raw instructions and the string list; ran `night_check.py` and re-ran `nights_check.py`.
**Result:** `problems: none` in both. Night 1 with 8 paid travelers leaves 20; a rent rise shows the same night; starving kills the son on night 3 and the rest on night 4 (`family-dead`); a negative total gives `in-debt`; all 31 days' night events run. Confirmed the three fact names that were inferred in the previous step. Failure on the way: two attempts to patch files through a shell here-document failed on quoting; used direct edits instead.
**Still broken / not tested:** not compared with the running game. Not read: the night screen (when balancing is called, how the ending is acted on), `buildMessage` (inferred from the text entries), `getNightMessages`, the order of pairs in a saved family member, where the day fills in its summary.
**Next:** the next data file (`Ends.xml` / `Intro.xml`), or the night screen.

## 2026-10-13 Nights.txt and how a night event is run (remaining data files, second)

**Changed:** added `docs/nights-txt-format.md`, `scripts/reference/nights.py` (the event table, the calendar, running an event's lines, budget lines and their ordering, the YES / NO step, the commands) and `scripts/checks/nights_check.py`; updated `docs/data-files.md`, `days-csv-format.md` and the checks README.
**Why:** next of the remaining data files.
**Tested how:** read `Nights.txt` with its comments; decompiled and read `NightLib`, `NightEvent`, `Calendar`, `CalendarEvent`, `Family.applyEvent`/`applyOp`/`applyRentAndHeatAffectingEvents`, `Budget.addLine` with its sorting function, `Line`; re-read `OpHelper.makeOp` and `getRunOps`; read two constants from the DLL and five dropped arguments from the raw instructions; ran `nights.py` and `nights_check.py`.
**Result:** `problems: none`. 40 events, all named by something (Days.csv, traveler scripts, scheduling, includes, or the code). Findings: `+` schedules an event here (it adds a paper in traveler scripts); a budget line with no third part is optional if it costs money and fixed if it pays; the budget is re-sorted after every added line with the quicksort that swaps equal lines; `End` keeps the first ending asked for but `Escape` overrides it; `GivePaper` stores the paper under the day that just ended.
**Still broken / not tested:** not compared with the running game. Not studied: the `Family` constructor (which events run and in what order, the family members, the standard budget lines), the rest of `applyBudget` (health, death, debt), `buildMessage`. In `nights.py` the fact names behind `AdoptNiece`, `RemoveSavings` and `TakeFamilyPassports` are names found in the code's strings; that those commands use them is inferred until the constructor is read.
**Next:** the `Family` constructor and `applyBudget` (the night itself), or the next data file (`Ends.xml` / `Intro.xml`).

## 2026-10-13 News.txt and the day's headlines (step 3, first data file)

**Changed:** added `docs/news-txt-format.md`, `scripts/reference/news.py` (articles, scores, the game's quicksort, the day's headline list, fillers, the `News<i>` names, traveler news) and `scripts/checks/news_check.py`; updated `docs/data-files.md`, `days-csv-format.md`, `papers-on-desk.md`, `port-requirements.md` (sorting is not stable) and the checks README.
**Why:** step 3 of `PROGRESS.md`: the remaining data files, starting with news.
**Tested how:** read `News.txt` with its comments; decompiled and read the `NewsArticleLib`, `NewsArticle` and `DayNews` functions, `addTravelerNews`, `getNewsIds`, `getValueStringArray`, `compareStrings`, `Array.sort`/`quicksort`, both `getRemappedFactId`; read four dropped numbers from the raw instructions; searched the other data files and the code's strings for news ids; ran `news.py 12345` and `news_check.py` (31 days, 200 master seeds).
**Result:** `problems: none`. 57 entries, 64 articles. Findings: a day's paper takes traveler-triggered news from the **previous** day's saved fact; the sort is a quicksort that swaps equal items, so on days 2, 3, 13 and 16 the two articles end up in the opposite order to the file; fillers are counted from the number of ids (so up to four items); each `RANDOM_` list has one live article, the rest are commented out; the entry `DIPLOMAT_FIRST` is named by nothing found.
**Still broken / not tested:** not compared with the running game. Drawing the newspaper (`DayNewsImage.make`, `LayoutImage`, the `NewsLayout` images) is not studied, so whether the first article is the main headline is not known. `whenAddNews` and endless-mode news not studied. Other callers of `Array.sort` not listed.
**Next:** either the newspaper picture (`DayNewsImage.make`), or the next data file (`Nights.txt`).

## 2026-10-13 Reference script for the booth: a whole traveler from a master seed (answer key, layer 5b part 2 and the chaining layer)

**Changed:** added `scripts/reference/booth.py` (fact stores, `addPaper`, every branch of `makeFactValue`, `setFactInvalid`/`setFactValid`, the lines of an error, criminal selection, and `makeNewTraveler` chaining all earlier layers) and `scripts/checks/booth_check.py`; `person.py` now takes the criminal pick as a function and records the criminal's number and the name's gender; `travspec.py` keeps a specification's custom error lines; updated `docs/traveler-creation.md` (reference section), `fact-values.md` (access nations, description words, date text, check results) and the checks README.
**Why:** last layer of the Python reference of traveler creation: the port's Rust code can now be compared with it traveler by traveler.
**Tested how:** re-read `makeFactValue` in full (1,516 lines), `addPaper`, the fact-validity functions, `applyOp`, `getRandomAccessNations`, `Criminal.selectRandom`; read twelve constants from the DLL; ran `booth.py` for days 1, 8, 12 and 20 (twice for day 12: identical output); re-ran `person_check.py`; ran `booth_check.py` (1,892 travelers, 31 days, four master seeds, plus fourteen wrong values asked for 300 times each on days 1 and 19).
**Result:** `problems: none` in both checks. Valid facts equal the traveler's details, wrong facts differ, dates fall on the right side of today, typos appear only with `HARDER` and at the expected rates. 8 to 55 booth draws per traveler (average 25). Applied errors carry only requirement, invalidate and set-fact lines at top level. Failures on the way: the first full check would have taken about 40 minutes (face drawing; now each sheet is read once and it takes about 4.5 minutes); a section I added then hung for 10 minutes with no output, because asking for a wrong purpose for an Arstotzkan native redraws for ever (confirmed separately: more than 20,000 draws). The check now uses a foreign traveler, has a draw limit that reports a stuck loop, and prints a progress line per day.
**Still broken / not tested:** not compared with the running game. Not modelled: bulletin and rulebook texts and page masks, speech, fact groups, tokens, the staying-papers save, and everything the player does between travelers (which also draws from the booth generator in the game). Story facts are empty unless passed in. A wrong name moves the name cycler; a saved name position is still not modelled.
**Next:** step 3 of `PROGRESS.md` (the remaining data files), or first decide how to compare this reference with the running game.

## 2026-10-13 Reference model of Facts.xml as the game holds it (answer key, layer 5b, part 1)

**Changed:** added `scripts/reference/factlib.py` (documents and facts after expansion, a document's fact copy in the game's table order, invalidate links, localization table, expiration-date rule); noted it in `docs/facts-xml-format.md`.
**Why:** the booth (next) needs the fact definitions, the order facts are generated in and the expiration rule.
**Tested how:** re-read the `DocDef`, `FactDef` and `InvalidateDef` constructors, `addFactDefs`, `generateExpirationDate`, `getLocalized`, `getFacts`, `getFactInvalidatesPath`, `FactDef.getInvalidatesPath`; read three constants from the DLL; ran `factlib.py` and compared with `map_order_check.py`.
**Result:** `problems: none`; 63 documents, 203 facts (146 empty), 56 invalidate links; the `VaccineCert` order equals the one found earlier. First run crashed on a fact with an empty id in my own printing code (fixed; the model was right).
**Still broken / not tested:** not compared with the running game. Fact groups and `<cite>` rules are not modelled here.
**Next:** layer 5b part 2: the booth (`addPaper`, `makeFactValue`, applying an error's lines), then chaining all layers.

## 2026-10-13 Reference script for the wrong-value helpers (answer key, layer 5a)

**Changed:** added `scripts/reference/values.py` (name layouts, wrong names, aliases, the alias swap sets, typos, the upper-case table, wrong faces, wrong fingerprints, altered id numbers); noted it in `docs/value-helpers.md`.
**Why:** first half of the fifth layer of the Python reference of traveler creation; the document values need these helpers.
**Tested how:** re-read `TravelerName` (`getFormatted`, `getRandomInvalidated`, `getRandomInvalidatedImp`, `getRandomAlias`), `Lang.buildAliasSwapSets` and its sort, `makeAlias`, `makeTypo`, `FaceSpec.getInvalid`, `FingerprintCode.makeInvalid`; read four constants from the DLL; ran `values.py`, which prints examples and checks itself over 1,500 name parts and 300 seeds.
**Result:** `problems: none`. The swap-set order built from `Text.xml` and `UpperCase.txt` through `haxemap.py` equals the order recorded earlier in `haxe-maps.md` (`CK, IUY, JL, aeiou, jl, bh, GPQ, BH, gpq, AEIOU, iuy, ck`). Aliases use 3 to 11 draws.
**Still broken / not tested:** not compared with the running game. The two "draw of exactly 1.0" cases in the pickers follow Haxe's documented behaviour. Only the English text was used for the swap sets.
**Next:** layer 5b: the booth itself (fact definitions, `addPaper` in hash order, `makeFactValue`, applying an error's lines), then the script that chains all layers.

## 2026-10-13 Reference script for choosing errors (answer key, layer 4)

**Changed:** added `scripts/reference/errormaker.py` (error library, requirements, error context, `makeError` with the recent-groups rule, the additional-error roll, the always errors) and `scripts/checks/errormaker_check.py`; updated `docs/errors-txt-format.md` (reference section; corrected the number of hidden-paper errors from ten to nine), `port-requirements.md` and the checks README.
**Why:** fourth layer of the Python reference of traveler creation from a master seed.
**Tested how:** re-read the `ErrorLib` constructor, `getErrorsForContext`, `getMatchingErrors`, `Error.getMatchesContext`, `getHiddenPaperId`, `isSpeechError`, `makeError`, `makeErrorContext`, `ErrorContext` and the error steps of `makeNewTraveler`; ran the demonstration for days 1 and 8 and `errormaker_check.py` over 31 days and 12 master seeds.
**Result:** 4,532 errors chosen with no rule broken: 0 or 2 draws per pick, every chosen group allowed by the recent-groups rule, second-error rate 31-32% against the data's 0.33. Day 1 foreigners get `ALWAYS:Rules-ArstotzkaOnly`; day 8's Jorji gets `EntryPermit-Missing`. New findings: one error pattern uses a negative look-ahead, which the port's matcher must support; the earlier doc's "ten hidden-paper errors" was wrong (nine).
**Still broken / not tested:** not compared with the running game. The demonstration's errors are not what the game would produce for that seed (the person's and documents' draws come between). The `Traveler-Criminal` replacement and custom errors are handled in the person layer and the chaining layer, not here.
**Next:** layer 5: document values and papers (`makeFactValue`, `addPaper`, applying an error's invalidate lines); then one script chaining all layers.

## 2026-10-13 Reference script for traveler scripts and the day's traveler list (answer key, layer 3)

**Changed:** added `scripts/reference/travspec.py` (script evaluation into a specification, weighted picks, conditions, the `WorldDef` pickers, the `Days.csv` traveler list and day facts, the criminal faces made at day set-up) and `scripts/checks/travspec_check.py`; updated `docs/travelers-txt-format.md`, `days-csv-format.md` (criminals are made every day; exact text of the day facts), `port-requirements.md` and the checks README.
**Why:** third layer of the Python reference of traveler creation from a master seed.
**Tested how:** re-read `applyToSpec`, `assignVar`, `makeTravelerSpec`, the condition closure, `ExpressionTester`, `Probability.select`, the `WorldDef` pickers, `PurposeDef`/`AutoPaperDef.getMatches`, `splitAndTrim`, `getAccumulatedRow` and the end of the `Day` constructor; read the criminal gender comparison from the raw instructions; ran the demonstration for days 1 and 8 and `travspec_check.py` over all 31 days and 12 master seeds.
**Result:** 4,932 specifications built with no failure and no empty detail; day 1 and day 8 lists and rules read sensibly (day 8 has Jorji's scripted face, name and id). New findings: every day makes three criminal faces at set-up, using the face cycler and the traveler generator; `Day/Rules` and `Day/Features` end in `;`; `HIRING_ENGINEERS` tests `Game/Rules`, which nothing sets, so that condition never holds.
**Still broken / not tested:** not compared with the running game. Story facts and facts set during the day are inputs (empty by default). Whether a `Day` object is constructed more than once per day (which would use the cycler again) is not known. The number in `Game/Visitor<n>` is still unconfirmed.
**Next:** layer 4: errors (`ErrorLib`, `ErrorMaker.makeError`, the additional-error roll); then document values and papers; then one script that chains the layers for a whole traveler.

## 2026-10-13 Reference script for building the person (traveler answer key, layer 2)

**Changed:** added `scripts/reference/person.py` (the `Traveler` constructor: draw order, scripted-face parser, face metadata, id number, fingerprints, height, weight, birth date) and `scripts/checks/person_check.py`; noted both in `docs/traveler-build.md`; settled one open item in `docs/player-actions.md` (`Want` and `Reject` patterns are case-insensitive); added the check to the checks README.
**Why:** second layer of the Python reference of traveler creation from a master seed.
**Tested how:** re-read the decompiled constructor, `makeRandomIdNumber`, `FingerprintCode.randomize`, `getMetadata`, `lerpScale`, `get_heightInCm` and `getBirthDate`; read nine constants from the DLL; ran the demonstration (`person.py 12345 1 6 extracted\art\assets`) and `person_check.py`; checked one person's age, height and weight by hand.
**Result:** draw counts match the write-up in all eight cases tried; fingerprints never break the two "must differ" rules over 2000 seeds; the name cycler advances for scripted names; all 35 scripted face values in `Travelers.txt` build.
**Still broken / not tested:** not compared with the running game. The demonstration's people are not what the game would produce for that seed, because the other layers' draws are missing. Rounding of the height to centimetres assumes Haxe's `Math.round` is "add 0.5 and round down" (not read in this build). Criminal selection and a saved name position are not modelled.
**Next:** layer 3: evaluating a traveler script into a specification (the day's traveler list, `=` lines, conditions, `RANDOM100`, filling unset details), then errors and document values.

## 2026-10-13 Reference script for the face and name cyclers (traveler answer key, layer 1)

**Changed:** added `scripts/reference/cyclers.py` (shuffle, maximum-separation reshuffle, `ShuffledSequence`, `FaceCycler`, `NameCycler`); added an `overview` mode to `scripts/reference/faces.py` (one labelled picture of every base face); noted both in `docs/traveler-build.md`.
**Why:** first layer of the Python reference of traveler creation from a master seed (second half of step 2 in `PROGRESS.md`); the overview was asked for to pick faces by eye.
**Tested how:** re-read the decompiled `ShuffledSequence`, `makeShuffled`, `getShuffledWithMaxSeparation`, `FaceCycler` and `NameCycler` before writing; ran `cyclers.py` with master seeds 12345 and 987654; ran `faces.py overview` and looked at the picture.
**Result:** self-checks pass (permutations, four-pass repeat, overlapping seeds, no repeated name in a pass; 1341 male and 1300 female name entries, no carriage returns). The overview shows all 45 faces with artwork.
**Still broken / not tested:** not compared with the running game. A saved name position is not modelled. The two "draw of exactly 1.0" cases follow Haxe's documented array behaviour, not checked in this build.
**Next:** layer 2: the person (the `Traveler` constructor: id number, fingerprints, height, weight, birth date) on top of the cyclers and `faces.py`; then scripts, errors and document values.

## 2026-10-13 Faces: the loader, how a face is built, and the pixel height

**Changed:** wrote `docs/faces.md`; added `scripts/reference/faces.py` (builds a face from the local sheet images, needs Pillow) and `scripts/checks/faces_check.py`; updated `docs/traveler-build.md`, `data-files.md`, `port-requirements.md` and the checks README.
**Why:** step 2 in `PROGRESS.md`: the traveler's height comes from the face picture, so the face-building procedure was the last unknown in creating a traveler.
**Tested how:** read the decompiled functions in full (`decompiled/faces.clean.c`, `image.clean.c`, `affine.clean.c`); settled one ambiguous branch and one dropped value from the raw instructions; read four constants from the DLL; ran `faces_check.py`; built five faces with `faces.py` and looked at them; ran the height survey over every head and shoulders pairing.
**Result:** the faces come out correctly assembled (palettes, mirroring and the document version included). Data findings: sheet `M6` has artwork only for piece 24; one female face has its shoulder dots in the opposite order (harmless). Face heights by the reference script: men with random faces 1.645 m to 1.964 m, women 1.618 m to 1.909 m; no pairing gives a zero height.
**Still broken / not tested:** not compared pixel-for-pixel with the running game. `Image.paste`, the PNG decoder, `getDocImage` and `getPhotoHeadImage` not read. `docs/PROGRESS.md` not updated (only on request).
**Next:** the Python reference of traveler creation from a master seed (the second half of step 2), then step 3 (remaining data files).

## 2026-10-13 The player's actions and judging mistakes (booth part 2)

**Changed:** wrote `docs/player-actions.md`; added `scripts/checks/actions_check.py`; updated `docs/responses-and-events.md`, `operations-and-fact-validity.md`, `facts-xml-format.md`, `port-requirements.md`, `data-files.md` and the checks README to point at it.
**Why:** next step 1 in `PROGRESS.md`: stamping, handing back, confiscating, interrogating, buttons, bomb and poison, and how mistakes and penalties are decided.
**Tested how:** read the decompiled functions in full (`decompiled/actions.clean.c`, `judging.clean.c`, `judging2.clean.c`); checked dropped arguments in the raw instructions; read the constants 1.0, 2.0, 5.0 and 15.0 from the DLL; ran `actions_check.py` against the data files.
**Result:** the stamp flags are confirmed as bits 2/4/8; all 45 response names in `Travelers.txt` are accounted for (19 fixed, 23 `Give-`, 2 `Interrogate-<button>-Replace`, 1 `LinkClicked-`); all 141 invalidate lines in `Errors.txt` carry an `Interrogate` response; penalties are 5, 5, 10, 15... from the third citation of a day.
**Still broken / not tested:** not compared with the running game. The screen code that calls these functions is not studied. `docs/PROGRESS.md` not updated (only on request), so three of its open questions (stamp bits, built response names, the `=!` note in the port rules) are now settled but still listed there.
**Next:** step 2 in `PROGRESS.md`: faces (`FaceLib` and `Face` constructors), then the Python reference of traveler creation.

## 2026-10-13 Second handoff: PROGRESS.md and the data-file index brought up to date

**Changed:** rewrote `docs/PROGRESS.md` (summary, estimate, doc list, next steps, open questions, verification, local-only files, scripts, working agreements); updated `docs/data-files.md` (Travelers.txt, Errors.txt, Faces.xml, Bodies.xml and Text.xml rows).
**Why:** the session's context was nearly full; `PROGRESS.md` had not been updated since the first handoff (it is now updated only on request).
**Tested how:** not applicable (documentation). Checked that `decompiled/ghidra_backup_named/` no longer exists and updated the local-files table to say so.
**Result:** a new session can start from `docs/PROGRESS.md`; the next step is part 2 of the booth responses (the player's actions and judging mistakes).
**Still broken / not tested:** nothing new.
**Next:** see `docs/PROGRESS.md`, "Next steps".

## 2026-10-13 Booth events, responses and operations studied (part 1)

**Changed:** wrote `docs/responses-and-events.md`; added `scripts/checks/responses_check.py`; updated `docs/travelers-txt-format.md`, `docs/operations-and-fact-validity.md`, `docs/port-requirements.md` and the checks README.
**Why:** to know what the booth does at each step of a visit, how scripted responses and their conditions run, and how citations are decided.
**Tested how:** decompiled and read in full 20 functions (`BoothEngine.handleEvent`, the response runners, `expandConditionalOps`, `applyOps`, the operation queue, `BoothEnv` default-response lookup and condition testing, the engine constructor); read dropped text keys and timing constants from the raw instructions; checked `Travelers.txt` response names, `@` commands and the `DEFAULT` entry against the engine with the new script.
**Result:** every event of a visit is written down, including the order of `Intro`, `Approved`/`Denied` and `Leave` responses and when defaults are used; response conditions see any fact; conditional groups are flattened, other named groups are skipped until asked for; Say operations and anything behind them are queued 1.5 s apart (3 s for slow travelers); all 14 kinds of `@` command used in the data are handled; the citation reasons (confiscation, cited facts, missing denial reason) and statistics are written down. Settles the `=!` question: that group never runs.
**Still broken / not tested:** the player's actions (stamping, giving papers back, confiscating, interrogating, detaining, fingerprinting, searching), `hasErrors`, `getCiteText`, `mistakeCaught` and `Day.addCitation` are part 2. The stamp-result bit values are inferred. Not compared with the running game.
**Next:** part 2: the player's actions and how mistakes are judged.

## 2026-10-13 Speech studied

**Changed:** wrote `docs/speech.md`; added `scripts/checks/speech_check.py`; updated `docs/travelers-txt-format.md`, `docs/errors-txt-format.md`, `docs/operations-and-fact-validity.md`, `docs/fact-values.md`, `docs/value-helpers.md`, `docs/data-files.md`, `docs/port-requirements.md` and the checks README.
**Why:** say lines in traveler scripts and errors become text through `BoothEnv.getSpeech` and `Speeches.txt`; this was next in the plan.
**Tested how:** decompiled and read in full 11 functions (`getSpeech`, `SpeechLib`, `Response`, `Speech`, `expandComplexVars`, `getLocalizedText`, `getRemappedFactId`, the line picker); checked two dropped arguments in the raw instructions; checked `Speeches.txt` and every say line in `Travelers.txt` and `Errors.txt` with the new script.
**Result:** a say line is a response id (a leading `$` is optional) or literal text. A response picks one line among those whose `=value` and `?expression` fit, with one draw, then expands `$` references and `${fact}` fields. `@` makes the inspector speak, `;` gives alternatives (one draw), `~` pauses, `[m]`/`[f]` switch by the face's gender. All 40 `$` lines and all 74 error speech ids resolve. Found: one response reads a fact that does not exist (`WorkPermit/Emblem/MinistryOfAdmission`), so one of its lines can never be picked; six responses are named nowhere found.
**Still broken / not tested:** `testExpression` and what the recorded speech fact path is used for are not studied. Gender switches are unused in the English data; language packs not checked. Not compared with the running game.
**Next:** running responses (`BoothEngine.handleEvent`, `testExpression`).

## 2026-10-13 Haxe StringMap and IntMap order worked out

**Changed:** wrote `docs/haxe-maps.md`; added `scripts/reference/haxemap.py`, `scripts/ghidra/EmulateStringHash.java` and `scripts/checks/map_order_check.py`; updated `docs/papers-on-desk.md`, `docs/value-helpers.md`, `docs/port-requirements.md`, `docs/ghidra-workflow.md` and the checks README.
**Why:** the order of these lookup tables decides random draws in fact generation and in aliases.
**Tested how:** decompiled and read in full both tables, their iterators and `String.GetHashCode`; read the load factors (0.77, 0.7) and the swap-set insert from the raw instructions. Ran the game's own `StringMap.lookup` and `GetHashCode` in Ghidra's emulator for 12 strings and compared with the Python reference. Self-tested the reference tables with 200 random runs. Applied them to `Facts.xml`, `Text.xml` and the name lists.
**Result:** the emulator and the reference agree on all 12 hashes (raw and mixed). The tables are Haxe's khash-style open addressing. `VaccineCert` generates its dates before its drugs; 19 documents generate facts in an order different from file order; the English alias groups are ordered `CK, IUY, JL, aeiou, jl, bh, GPQ, BH, gpq, AEIOU, iuy, ck`; 1,237 of 5,278 name parts have their alias positions walked out of left-to-right order. Self-test: contents always matched a Python dictionary.
**Still broken / not tested:** table insertion, growth and walking checked by reading and self-test only, not in the emulator (needs the allocator). Not compared with the running game.
**Next:** speech (`BoothEnv.getSpeech`, `Speeches.txt`), then running responses.

## 2026-10-13 Helpers behind wrong values and dates studied

**Changed:** wrote `docs/value-helpers.md`; added `scripts/reference/gdate.py`; updated `docs/fact-values.md`, `docs/data-files.md` and `docs/port-requirements.md`. `docs/PROGRESS.md` not updated (now updated only on request).
**Why:** `makeFactValue` relies on these helpers for wrong names, aliases, typos, wrong faces, wrong fingerprints and every date; they were next in the plan.
**Tested how:** decompiled and read in full 30 functions (`TravelerName`, `Lang` alias and typo code, `Uppercaser`, `FaceSpec.getInvalid`, `FingerprintCode.makeInvalid`/`fromString`, `Settings` date formats, `GregorianDate`); read dropped thresholds, date constants, the alias text key (`env_typochars`) and the format arithmetic from the raw instructions; checked `Text.xml` and `UpperCase.txt`; ran `gdate.py`, which checks the date conversion both ways against Python's calendar.
**Result:** all helpers written down with their exact draws. A wrong name takes one or two names from the shared name cycler; an alias changes one letter within a set of similar letters; a typo deletes one letter; a wrong face shifts all four pieces; wrong fingerprints differ on every finger. `gdate.py` agrees with the real calendar for all 146,462 days from 1800 to 2200 (23 Nov 1982 = Julian Day 2445296.5).
**Still broken / not tested:** alias swap-set order and letter-position order are hash orders (`StringMap`, `IntMap`), not studied; `SpeechLib.applyGenderSwitches` and loading the saved date format not studied. Not compared with the running game.
**Next:** Haxe `StringMap` and `IntMap` iteration order.

## 2026-10-13 Start-up and seeds studied

**Changed:** wrote `docs/run-and-seeds.md`; added `scripts/reference/seeds.py`; corrected `docs/rand.md`; updated `docs/traveler-build.md`, `docs/port-requirements.md` and `docs/PROGRESS.md`.
**Why:** a traveler cannot be reproduced without knowing where the face cycler, name cycler and story seed get their seeds; this was first in the next-steps list.
**Tested how:** decompiled and read in full the Unity start-up (`HostUnity.CreateGame`), the `Game` and `Bootstrap` constructors, `setLanguage`, `advanceStorySeed`, `autoReapplyRandomSeed`, the day-run and booth-run constructors, Haxe `Math.random` and its setup, `System.Random()`, `CommandLine.fromArgs` and `Trace`; read the `LOAD_TO_SCREEN` branch of `Game.applyScreenChange`; read the seed-scaling constant (16777215) from the raw instructions. Ran `seeds.py` for master seeds 0 and 16777214; its story seeds for master 0 equal `rand.py`'s first three outputs for seed 73.
**Result:** each launch takes a master seed from the system tick count; story seeds come from `Rand(master + 73)`, one at start-up and one per loaded save (the story seed is not saved); the face cycler and name cycler start from the master seed, and only the name position is saved. **Correction:** `docs/rand.md` said nothing uses `System.Random`; the start-up does, through a call the first search could not see. The command-line word `trace` turns on one of the two debug-log switches; nothing found turns on the other.
**Still broken / not tested:** nothing checked against the running game; the rest of `applyScreenChange`, saves, the test automation, where the log output goes, and a full search for writes to `Trace.showVerbose` are not done.
**Next:** the helpers used by the value generator (see `docs/PROGRESS.md`).

## 2026-10-13 Building the traveler (the person) studied

**Changed:** wrote `docs/traveler-build.md`; added `scripts/checks/traveler_build_check.py`; updated `docs/traveler-creation.md`, `docs/fact-values.md`, `docs/rand.md`, `docs/port-requirements.md`, `docs/PROGRESS.md` and the checks README.
**Why:** the `Traveler` constructor decides the person behind the documents (face, name, id number, fingerprints, height, weight, criminal); it was next in `docs/PROGRESS.md`.
**Tested how:** decompiled and read in full the constructor and 45 helpers (face and name cyclers, shuffled sequences, face metadata, fingerprints, criminals, id numbers); recovered from the raw instructions the six variable names the decompiler dropped, all numeric constants, the face-metadata lookup keys and one substring length; checked the findings against `Travelers.txt`, `Errors.txt`, `NamesM.txt`, `NamesF.txt`, `Bodies.xml` and `Faces.xml` with the new check script.
**Result:** the exact order of the booth's random draws while building a person is written down (vaccine count, optional contraband type, optional face parts, confusing-gender or criminal pick, optional id number, fingerprints, height). Faces and names come from separate long-lived "cyclers", not from the day's seed; the face cycler's sequences have overlapping seeds, and the name position is saved with the game and advances even for scripted names. Weight comes from the face's body-mass index and height through a gender-specific factor. All error names the code looks for exist in `Errors.txt`. `canDetain` and `genderForced` are never set by the data.
**Still broken / not tested:** where the face and name cyclers are created and seeded is not studied, so no traveler can be reproduced yet; the face image height, `Faces.xml` loading and `GregorianDate` are not studied. Not compared with the running game.
**Next:** where the run is set up (cycler seeds, story seed); see `docs/PROGRESS.md`.

## 2026-10-13 Adding and removing papers studied

**Changed:** wrote `docs/papers-on-desk.md`; added `scripts/checks/papers_on_desk_check.py`; updated `docs/operations-and-fact-validity.md`, `docs/traveler-creation.md`, `docs/fact-values.md`, `docs/facts-xml-format.md`, `docs/port-requirements.md`, `docs/PROGRESS.md` and the checks README.
**Why:** every document's values are created when it is put on the desk (`BoothEnv.addPaper`); this was the first item in the next-steps list.
**Tested how:** decompiled and read in full `addPaper`, `addBulletinForDay` and 35 helpers; read four dropped numbers from the raw instructions (three in the bulletin code, one in `PaperDef.getIdAndIndex`); re-read the remove-paper branch of `applyOp`; checked the findings against `Facts.xml`, `Papers.xml`, `Days.csv` and `Errors.txt` with the new check script.
**Result:** the sequence is written down: money, achievement, tokens, papers-seen list, expiration date (one draw only when the document has an `ExpirationDate` fact), fresh copy of the document's facts, generation of every empty fact (146 of 191), merge that keeps existing values, then clearing of "confusing" facts. Stackable papers get no facts. Removing a paper keeps its facts. The bulletin's page numbers match all 13 bulletin pages in `Papers.xml`. New exactness problem found: a paper's facts are generated in the hash order of a Haxe `StringMap`, and `VaccineCert` has two facts that draw random numbers, so the port needs that hash order.
**Still broken / not tested:** Haxe `StringMap` order not studied; token list, news articles and `Bulletin/PageMask` use not studied; callers of `addPaper` outside `BoothEnv` not searched. Achievement awarding deliberately not followed (platform feature, out of scope). Not compared with the running game.
**Next:** the `Traveler` constructor (see `docs/PROGRESS.md`).

## 2026-10-13 Handoff: state, open items and reading notes written down

**Changed:** wrote `docs/PROGRESS.md` (current state, ordered next steps, open questions, local-only files, verification ideas) and `docs/port-requirements.md` (exactness rules for the Rust port); added a "runtime helpers" and "calls by slot number" guide to `docs/ghidra-workflow.md`; copied the session's 12 one-off check scripts from the temporary folder into `scripts/checks/` with a README; resolved the "extra filter" note in `docs/facts-xml-format.md`; added a "Start here" pointer and three tooling facts to `CLAUDE.md`.
**Why:** the session's context was nearly full; knowledge that existed only in the conversation or a temporary folder would have been lost.
**Tested how:** re-ran two of the copied check scripts from their new location (`days_shape.py`, `errors_check.py`).
**Result:** both print the same counts as before (20 rows of 34 columns; 11 templates, 110 errors). A new session can start from `docs/PROGRESS.md`.
**Still broken / not tested:** the other ten check scripts were not re-run after copying.
**Next:** see `docs/PROGRESS.md`, "Next steps".

## 2026-10-13 Document value generator studied

**Changed:** wrote `docs/fact-values.md`; updated two notes in `docs/operations-and-fact-validity.md`.
**Why:** `BoothEnv.makeFactValue` decides what every field on every document says, valid or wrong.
**Tested how:** decompiled and read the whole function (1,516 lines after cleaning) and `app.Num.lerpScale`; read its 16 numeric constants from the DLL; named the methods it calls by slot number from the recovered metadata; checked three dropped-argument calls and the `++` arithmetic in `applyOp` against the raw instructions.
**Result:** all 30 kinds of fact are tabulated with their valid and invalid values and the random draws each makes. Findings: "confusing" only changes `Gender` (it keeps the correct letter); an invalid weight is always lower, never higher; a valid vaccine certificate always includes polio and an invalid one never does; valid access permits always include Arstotzka; several fields get typos only when the `HARDER` feature is on. The `++` addition in `applyOp` is confirmed.
**Still broken / not tested:** the helpers this function calls (name alteration, aliases and typos, wrong faces, fingerprints, birth date, id numbers, date formatting) are not studied, so no reference implementation exists yet. Not compared with the running game.
**Next:** `BoothEnv.addPaper`, then the `Traveler` constructor.

## 2026-10-12 Operations and fact validity studied

**Changed:** wrote `docs/operations-and-fact-validity.md`; updated notes in `docs/facts-xml-format.md` and `docs/errors-txt-format.md`.
**Why:** to know what applying an error actually does to the facts on a traveler's documents.
**Tested how:** decompiled and read in full 8 `BoothEnv` functions (`applyOp`, `setFactInvalid`, `setFactValid`, `setFactValue`, `findInvalidFactPath`, `isValid`, `getFactValue`, `getFactValueText`); checked `Errors.txt` and `Travelers.txt` for anything that invalidates `Traveler/Nationality`.
**Result:** each operation kind's effect is written down. A fact is invalid if it is on the invalid list or if a listed fact's current value invalidates it per `Facts.xml`. Invalidating a fact generates a wrong value at once; `~` means "confusing"; validating regenerates a value only for editable facts. The misspelled `whennot` in `Facts.xml` is shown to have no effect with the current data.
**Still broken / not tested:** `makeFactValue`, `addPaper` and `getSpeech` are not studied. The `++` arithmetic was dropped by the decompiler and is assumed from the visible `--` case. Not compared with the running game.
**Next:** `BoothEnv.makeFactValue`.

## 2026-10-12 Errors.txt and error selection studied

**Changed:** wrote `docs/errors-txt-format.md`; added template expansion to `scripts/reference/tabtree.py`; corrected the template section of `docs/tab-tree-format.md`; updated `docs/data-files.md`.
**Why:** `Errors.txt` defines what can be wrong with a traveler, and `ErrorMaker` decides which error they get.
**Tested how:** decompiled 12 functions and read 11 in full (the twelfth for its logic, with its debug-logging lines filtered out); read two dropped details from the raw instructions; expanded the templates in the real file with the reference reader and checked every error against the code and against `Facts.xml` and `Travelers.txt`.
**Result:** 11 templates, 110 errors (3 always, 107 random, 76 groups). Errors are selected by matching case-insensitive patterns against their names, filtered by requirements, then picked with two random draws while avoiding the last four groups used. All 82 template uses expand cleanly (768 nodes become 981). Every requirement, condition and fact path in the file is valid. No error uses `<rare>`, so that branch never fires.
**Correction:** `docs/tab-tree-format.md` said template arguments are `$0`, `$1`, ...; they are numbered from 1. It also said it was unknown whether any file uses templates; `Errors.txt` does.
**Still broken / not tested:** what applying an error does, the `~` prefix on 22 fact paths, and how invalid values are generated are not studied. Not compared with the running game.
**Next:** `BoothEnv.applyOp` and `setFactInvalid`, then `makeFactValue`.

## 2026-10-12 Traveler creation sequence studied (top level)

**Changed:** wrote `docs/traveler-creation.md`; updated the `FILL` entry in `docs/days-csv-format.md` and the seed note in `docs/rand.md`.
**Why:** to know the order of events when a traveler arrives, before studying the large functions each step calls.
**Tested how:** decompiled and read in full 10 functions (`BoothEnv.makeNewTraveler`, the `BoothEnv` constructor, `applyError`, four `Day` methods, `ErrorContext`); recovered two dropped arguments from the raw instructions; checked the `FILL` column of `Days.csv`.
**Result:** the 12-step creation sequence and the 10-step booth setup are written down, including which random generator each uses and exactly when the additional-error roll consumes a draw. `FILL` is confirmed as the template for travelers after the scripted list (the last list entry repeats). `BoothEnv`'s generator is seeded with the day seed minus `0x7FFFF000`.
**Still broken / not tested:** the `Traveler` constructor, the error system (`Errors.txt`, `ErrorLib`, `ErrorMaker`), `addPaper`, `makeFactValue` and `applyOp` are not studied. Nothing is checked against the running game.
**Next:** the error system, starting with `Errors.txt`.

## 2026-10-12 Traveler script meaning studied (creation side)

**Changed:** rewrote `docs/travelers-txt-format.md` with confirmed meanings; added `scripts/ghidra/DumpAssembly.java`; added `__pycache__/` to `.gitignore`; updated `docs/data-files.md` and `docs/ghidra-workflow.md`.
**Why:** to know what each line of a traveler script does, which the structure-only pass left unconfirmed.
**Tested how:** decompiled and read in full 20 functions (`TravelerContext`, `OpHelper.makeOp`/`getRunOps`, `ExpressionTester`, `joinQuoted`); read the `RANDOM100` calculation from the raw instructions; walked every line of the real file with the reference tree reader and checked it against the line kinds the code accepts at each level.
**Result:** every block-level and operation-level line kind is identified, and the real file contains nothing the code would reject. The order of random draws when a traveler is created is written down. Notable: `BREAK` stops the whole traveler; a single-value `=` still makes a random draw; conditions have no operator precedence and ignore case; `fallback` discards the result and builds another entry. One data error found: a condition in `EZIC_DIPLO` uses `=!` instead of `!=`.
**Still broken / not tested:** nothing is tested against the running game. How responses run, how a specification becomes a traveler with documents, and how response conditions are evaluated are not studied. Whether `$name` speech lines refer to `Speeches.txt` is not confirmed.
**Next:** `BoothEnv.makeNewTraveler`: how a specification becomes a traveler and their documents.

## 2026-10-12 Indented-tree reader studied; Travelers.txt structure mapped

**Changed:** wrote `docs/tab-tree-format.md`, `docs/travelers-txt-format.md` and `docs/data-files.md`; added `scripts/reference/tabtree.py`.
**Why:** travelers are defined in `Travelers.txt`, which is a script in an indented-tree format; the port needs the same reader before the script's meaning can be studied.
**Tested how:** decompiled and read in full 13 functions (`TabParser`, `Node`, the tokeniser, `Res.getTabParser`/`getText`/`toAsset`); wrote a reference reader and ran it on the real file; cross-checked against `Days.csv`; read the file's comments; searched the code for every data file name.
**Result:** the reference reader parses the whole file without error (185 top-level entries, 2,974 nodes, depth 6). All 142 traveler ids used by `Days.csv` and all 113 `INCLUDE` targets resolve. One 12-line block comment is removed. Every data file is now mapped to the class that loads it; three files (`Threads.txt`, `TravelerGraph.txt`, `Version.txt`) are never asked for by name.
**Still broken / not tested:** the meaning of every line kind in `Travelers.txt` is unconfirmed; the code that interprets the tree has not been read. Whether the template feature is used anywhere is not determined. The reference reader has not been compared with the game's own tree.
**Next:** the code that turns a traveler's tree into a `TravelerSpec` and runs its responses.

## 2026-10-12 Random number generator studied and checked against the machine code

**Changed:** wrote `docs/rand.md`; added `scripts/reference/rand.py` and `scripts/ghidra/EmulateRand.java`; added an emulator note to `docs/ghidra-workflow.md`; corrected the "pick one" description in `docs/facts-xml-format.md`.
**Why:** every generated traveler, document and event depends on `app.Rand`; the port must reproduce it exactly.
**Tested how:** decompiled and read all nine methods; ran the game's real constructor and `nextInt` code in Ghidra's emulator for seven seeds and compared the state plus 20 outputs each with the Python reference; searched the code for any other randomness source.
**Result:** it is the published sfc32 generator with the game's own seeding (three constants, seed in the counter, 15 discarded outputs). All seven emulator lines match the reference exactly. `random()` divides by 2^31 - 1, so it can return exactly 1.0. Nothing in the game uses any other random source.
**Still broken / not tested:** not compared against the running game. The division in `nextFloat` was not emulated (divisor read from the DLL). The seeds used by the 13 generator creation sites other than `Day` are not studied, including where a new game's story seed comes from.
**Next:** how travelers are defined (`Travelers.txt`) and generated.

## 2026-10-12 Correction: `journalist` is a real purpose; comments were skipped

**Changed:** corrected `docs/facts-xml-format.md` (new section "The comments matter"); added comment notes to `docs/papers-xml-format.md`; added two steps to the study method in `docs/ghidra-workflow.md`.
**Why:** I described the `journalist` purpose as undefined and suggested it was cut content. The user pointed out journalists exist in the game.
**Tested how:** searched all data files and the code's strings for `journalist` and `RuleDetainKolechia`; extracted and read all 68 comments in `Facts.xml` and all 43 in `Papers.xml`.
**Result:** the user was right. `Facts.xml` line 21 has `<purpose val="journalist"/>` commented out with the note "set manually only", and `Travelers.txt` sets `= purpose journalist` for two scripted travelers. The cause of my error: the XML parser I used for the inventory drops comments, and I never read them. `RuleDetainKolechia` is a fact whose definition is commented out while one group still refers to it.
**Still broken / not tested:** comments in the other data files (`Days.csv` has none; the `.txt` files use `#`) have not been reviewed.
**Next:** unchanged: `app.Rand`, then traveler and fact generation.

## 2026-10-12 Facts.xml format studied in full

**Changed:** wrote `docs/facts-xml-format.md`; `scripts/ghidra/clean_decompile.py` now collapses checked type casts; updated its note in `docs/ghidra-workflow.md`.
**Why:** `Facts.xml` holds the world (nations, purposes, durations), every document's facts, and the definitions of what a fact's value can invalidate. Days, papers and travelers all depend on it.
**Tested how:** inventoried all tags and attributes; decompiled and read in full 45 functions (loaders, the query methods, random-pick helpers, the XML attribute lookup); searched the code for attribute names that no loader used; cross-checked every section of the file against the code and against `Papers.xml`.
**Result:** the file is not valid XML (a raw `&&` in one attribute). 191 written facts expand to 203. `<invalidate when>` is a plain equality test, not an expression. Attribute names are case-sensitive, so the file's `whennot` (code reads `whenNot`) is never read, and neither are document `cite` (code reads `desc`), nation `citizen` and loc `section`. Two dangling references found (`Rules/RuleDetainKolechia`, purpose `journalist`). Random-pick procedures written down for exact reproduction.
**Still broken / not tested:** no reader written for the port. Fact value generation, how invalidation and groups decide errors, the `<confiscation when>` expression evaluator and `app.Rand` not studied. Whether `*` is stripped in `<cite when="*...">` and the error-pattern filter in random purpose are not confirmed.
**Next:** `app.Rand`, then how a traveler and their facts are generated.

## 2026-10-12 Papers.xml format studied in full

**Changed:** wrote `docs/papers-xml-format.md`; added `scripts/ghidra/clean_decompile.py`; added a study method and two tool notes to `docs/ghidra-workflow.md`.
**Why:** `Papers.xml` defines every document, its pages and what is drawn on them.
**Tested how:** inventoried all tags and attributes; decompiled and read in full 17 loader and helper functions; compared the strings each loader uses with the file's attribute names; checked every attribute value in the file against what the code accepts.
**Result:** 68 papers, 120 pages, 509 marks, all accounted for. Marks inherit defaults paper -> page -> mark. Text or image values starting with `$` are fact ids filled in per traveler. Three attributes are never read (`fontlinespacing`, mark `format`, mark `section`). Papers are stored in reverse file order, which decides which `Passport` a nation-less lookup returns. Side finding: `Facts.xml` is not well-formed XML (strict parser fails at line 96).
**Still broken / not tested:** no reader written for the port. Mark layout and drawing, the phone/tablet rewrites, the carousel's role and language overrides not studied. The Rust toolchain was checked in passing: `rustc` 1.99 and the `wasm32-unknown-unknown` target are installed; `trunk`, `wasm-pack` and `wasm-bindgen` are not.
**Next:** `Facts.xml`, since papers, days and travelers all depend on facts.

## 2026-10-12 Days.csv: rest of the Day setup read, guesses corrected

**Changed:** rewrote `docs/days-csv-format.md`; added `scripts/ghidra/ListStringUses.java`.
**Why:** the first pass only skimmed two-thirds of the `Day` constructor and matched rows to fields by name.
**Tested how:** read the remaining ~900 decompiled lines; listed the string constants in machine-code order to identify lookups where the decompiler dropped the row name; searched for users of the `RPAGE`, `NEWS` and `DESC` strings; read the enum orders from `dump.cs`; printed the short rows from the file.
**Result:** every row is now confirmed. Three earlier guesses were wrong or incomplete: `RPAGE` is not used at all (no such string in the code); `NEWS` is read by `DayLib.getNewsIds`, not the constructor; `GUARDS` is a string of flag characters (`0`-`4`, `J`, `F`), not a number. `DURATION_SLOW` confirmed as phone-only.
**Still broken / not tested:** no reader written for the port. `app.Rand`, `DayNews`, face generation and text templates not studied.
**Next:** `Papers.xml`.

## 2026-10-12 Days.csv format studied

**Changed:** wrote `docs/days-csv-format.md`. No code changed.
**Why:** `Days.csv` defines what happens on each day; the port has to read it the same way the game does.
**Tested how:** parsed the file with a standard CSV reader (20 rows, 34 columns, all rows the same width); decompiled `data.CsvTable`, `data.DayLib` and the `play.day.Day` constructor and read the table parser, the carry-over logic and the first third of the constructor.
**Result:** table is sideways (rows are properties, columns are days). `+Name` / `-Name` carry over between days. 11 of 20 rows confirmed in code, plus the date and random-seed formulas; the rest are inferred from names and marked so.
**Still broken / not tested:** second half of the `Day` constructor only skimmed. No parser written for the port, so nothing is tested end to end. `app.Rand` not studied.
**Next:** `Papers.xml`.

## 2026-10-12 Art.dat decrypted and unpacked

**Changed:** added `scripts/ghidra/FindReferences.java`, `scripts/extract/decrypt_art.py`, `scripts/extract/unpack_art.py`; wrote `docs/art-dat-format.md`; added a pitfall note to `docs/ghidra-workflow.md`; added `/.claude/settings.local.json` to `.gitignore`.
**Why:** the game's content (images, fonts, day/paper/traveler definitions) is in one encrypted archive; the port needs to read it.
**Tested how:** cut `Art.dat` out of `sharedassets0.assets`, ran both scripts, checked PNG signatures and that the listed sizes add up to the file length.
**Result:** decryption and unpacking both worked on the first run. 614 files (572 PNG, 12 fonts, 14 XML, 14 text, 2 CSV); 3,309,984 of 3,309,984 bytes accounted for; 572 of 572 PNGs have a valid signature.
**Still broken / not tested:** no script for cutting `Art.dat` out of the Unity file (offsets found by hand). Only one image opened and looked at (`papers/PassportInnerArstotzka.png`, displays correctly). Data file formats, the language zips, `Res.toAsset`, audio and `EncryptedStore` not studied. The four 2026-10-12 commits predate this; these changes are uncommitted.
**Next:** study the formats of the files in `assets/data/`, starting with `Days.csv` and `Papers.xml`.

## 2026-10-12 Data layouts and typed signatures loaded into Ghidra

**Changed:** added `scripts/ghidra/ApplyIl2CppTypes.java`; ran it on the Ghidra project; updated `docs/ghidra-workflow.md`; backup of the names-only project in `decompiled/ghidra_backup_named/`.
**Why:** fields showed as raw offsets and virtual calls as table offsets, which made the code slow and error-prone to read.
**Tested how:** printed `play_day_BoothEngine_o` from Ghidra and compared all 29 field offsets with `dump.cs`; re-decompiled `getLeaveDir` and `get_opQueHasItems`.
**Result:** all 29 offsets match. 35,667 data types; signatures applied to 25,220 of 25,256 functions. Decompiled code now shows `(__this->fields).env`, `.traveler`, `get_hasBomb`, `preventStashCount`. First import attempt left booleans as `bool.conflict` (my script redefined `bool`); fixed by removing that line, restoring the backup and re-importing.
**Still broken / not tested:** 36 signatures not applied (which ones is unknown). Only one class's layout compared. String constants still show as `StringLiteral_N`. The two Ghidra analysis errors are identified as non-game code (engine runtime, `haxe.lang.FieldLookup`), not fixed.
**Next:** decide which part of the game to read first.

## 2026-10-12 Ghidra analysis, naming and first decompile all work

**Changed:** saved Ghidra project in `decompiled/ghidra/`; added `scripts/ghidra/DecompileFunctions.java`; wrote `docs/ghidra-workflow.md`; marked `STATUS.md` resolved.
**Why:** milestone 1 needs readable function bodies with real names.
**Tested how:** ran `analyzeHeadless` import, then `ApplyIl2CppNames.java`, then `DecompileFunctions.java` on `0x180467c80` and `0x180468060`; looked up the string constants and field offsets they use.
**Result:** analysis took 15.9 min, project is 224 MB. 25,256 functions named, 0 addresses without a function. `BoothEngine.getLeaveDir` returns strings like `left`, `right`, `right-bomb`; `get_opQueHasItems` reads offset 0x40, the `opQue` field. Names match code.
**Still broken / not tested:** only two functions checked. Struct layouts not loaded, so fields show as raw offsets and virtual calls as table offsets. Two Ghidra analysis errors not investigated.
**Next:** decide what to read first; consider loading struct layouts from `il2cpp.h` to make fields readable.

## 2026-10-12 Tools moved to C:\tools, git initialised, direct Ghidra run started

**Changed:** moved Il2CppDumper to `C:\tools\Il2CppDumper-6.7.46`; removed project `tools/` and its `.gitignore` line; created `C:\Users\farha\.claude\CLAUDE.md` listing shared tool paths; deleted the empty stray `papersplease_rea\papersplease_rea` repo (origin unknown); ran `git init` in the project root (no commit); added `scripts/ghidra/ApplyIl2CppNames.java`; updated `CLAUDE.md` tooling state.
**Why:** shared tools belong outside the project; REA cannot analyse the DLL, so Ghidra is run directly with a saved project in `decompiled/ghidra/`.
**Tested how:** `git status` after init; checked `script.json` field names against the naming script.
**Result:** `git status` lists only `.claude/`, `.gitignore`, `CLAUDE.md`, `MODLOG.md`, `STATUS.md`, `docs/` (the game folders are ignored). Ghidra import started and picked the PE loader, x86 64-bit.
**Still broken / not tested:** Ghidra analysis not finished. `ApplyIl2CppNames.java` has never been run. Il2CppDumper not re-run from its new location.
**Next:** when analysis finishes, run the naming script, then decompile one named function.

## 2026-10-12 REA/Ghidra decompile of GameAssembly.dll: failed twice

**Changed:** nothing in the project; wrote `STATUS.md`.
**Why:** wanted to read one named function's decompiled body and load the recovered names into Ghidra.
**Tested how:** REA `binary_overview`, then REA `procedure_pseudo_code` on `0x180467c80` (`BoothEngine.getLeaveDir`).
**Result:** both failed with `provider_timeout` at 330,000 ms. REA also reports renaming as unsupported on Windows ("Windows Ghidra P0 does not admit database mutation").
**Still broken / not tested:** no function body has been read. No recovered name has been checked against real code.
**Next:** waiting for a decision; options are listed in `STATUS.md` (first choice: run Ghidra headless directly with a saved project).

## 2026-10-12 IL2CPP names recovered with Il2CppDumper

**Changed:** copied the game into `game/`; downloaded Il2CppDumper v6.7.46 into `tools/`; ran it into `dumps/il2cppdumper/`; added `/tools/` to `.gitignore`; wrote `docs/il2cpp-name-recovery.md`.
**Why:** `GameAssembly.dll` is unreadable without the class and method names stored in `global-metadata.dat`.
**Tested how:** compared file counts and SHA-256 of the copy; read the metadata header; counted the dumper output; cross-checked method addresses against the DLL's `.pdata` function table.
**Result:** copy matches (67 files, 94,154,205 bytes). Metadata v27, not encrypted. 4,299 types, 29,623 methods with addresses, 1,351 types in the game's own code. 100% of addresses are in the code section, 90.5% sit exactly on a `.pdata` function start. The game is Haxe compiled to C#.
**Still broken / not tested:** names are not loaded into Ghidra/REA yet. No decompiled function has been compared against its name. The 9.5% of addresses not in `.pdata` are unexplained (probably small leaf functions).
**Next:** finish the Ghidra analysis, try applying `script.json` names through REA, and decompile one named game function as a check.
