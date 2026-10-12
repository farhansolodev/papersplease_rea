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
