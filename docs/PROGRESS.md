# Where the project stands

**Read this first in a new session.** Last updated 2026-10-13, at the end of
the second long session. `MODLOG.md` has the step-by-step history; this file
is the current state, what to do next and what is still open. It is updated
only when the user asks (see "Working agreements"), so the newest
`MODLOG.md` entries may be ahead of it.

## One-paragraph summary

The game is Haxe compiled to C# and then to native code by Unity IL2CPP.
Names, data layouts and typed signatures are recovered and loaded into a
saved Ghidra project, so any function can be decompiled by name. The
content archive (`Art.dat`) is decrypted and unpacked: 614 images, fonts and
plain-text data files. The game is strongly data-driven. Traced from the
code so far: how a launch picks its master seed and derives every day's
random numbers; how a traveler is chosen, built (face, name, id,
fingerprints, height, weight, criminals) and given documents with right or
deliberately wrong values; how errors are chosen and applied; how say lines
become speech; how the booth runs a visit, its scripted responses and
button commands, and when it issues a citation. Reference implementations
exist for the random generator, the date maths, the seed chain and Haxe's
lookup tables, each checked (against the game's machine code or the real
calendar). No Rust code exists yet.

## How far along

Rough estimate: **about 20% of the work**, low confidence. Estimated total:
100 to 200 hours of sessions.

| Stage | Share | State |
|---|---|---|
| 1. Tools to read the code | 3% | Done |
| 2. Getting assets out | 5% | About half: images, fonts, data done; audio, language packs, scripted `Art.dat` cut-out not done |
| 3. Understanding the data files | 12% | 8 of the 23 game data files studied, 3 more in part (`data-files.md`) |
| 4. Understanding the game logic | 30% | Roughly 40%: the traveler pipeline, speech and booth events are done; the player's actions, judging mistakes, news, nights, endings, saves, endless mode and the screen side are not |
| 5. Building the browser game in Rust | 40% | Not started. Rust 1.99 and `wasm32-unknown-unknown` are installed; `trunk`, `wasm-pack`, `wasm-bindgen` are not; Bevy not tried |
| 6. Comparing with the original | 10% | Not started; see "Verification" below |

## What is documented

| Doc | Covers |
|---|---|
| `il2cpp-name-recovery.md` | Il2CppDumper run and checks |
| `ghidra-workflow.md` | Commands, scripts, how to read decompiled output, the emulator, the study method |
| `art-dat-format.md` | The encrypted archive |
| `data-files.md` | Index of every data file, its loader and how far it is studied |
| `days-csv-format.md` | `Days.csv`, fully |
| `papers-xml-format.md` | `Papers.xml`, fully (layout and drawing not studied) |
| `facts-xml-format.md` | `Facts.xml`, fully, plus random-pick procedures |
| `rand.md` | The random generator, checked against the machine code |
| `run-and-seeds.md` | Start-up: the master seed, story seeds, cyclers, command-line words, the debug log switches |
| `tab-tree-format.md` | The indented-tree reader and templates |
| `travelers-txt-format.md` | Traveler scripts |
| `errors-txt-format.md` | `Errors.txt` and error selection |
| `traveler-creation.md` | The sequence that creates a traveler |
| `traveler-build.md` | Building the person: face, name, id, fingerprints, height, weight, criminals |
| `operations-and-fact-validity.md` | Running an operation; invalid facts |
| `fact-values.md` | How each document value is generated |
| `value-helpers.md` | Wrong names, aliases, typos, wrong faces and fingerprints, dates and date formats |
| `papers-on-desk.md` | Adding and removing papers, staying papers, the bulletin |
| `haxe-maps.md` | Haxe's `StringMap` and `IntMap`: hash, layout and the order they are walked in |
| `speech.md` | `Speeches.txt` and how say lines become speech |
| `responses-and-events.md` | Part 1: the booth's events, responses, conditions, operation queue, button commands, citations |
| `port-requirements.md` | Exactness rules the Rust port must follow |

## Next steps, in order

(Done in the second session: papers on the desk, building the traveler,
start-up and seeds, the value helpers, Haxe's lookup tables, speech, and part 1
of the booth responses. See the docs above and `MODLOG.md`.)

1. **Booth responses, part 2: the player's actions and judging mistakes.**
   `BoothEngine` (`0x1804640f0` constructor; methods listed in `dump.cs`):
   `stampPaper`, `canGivePaperToTraveler` / `givePaperToTraveler` (the
   `Give-...` responses), `confiscatePaper`, `putPaperInFiler` /
   `removePaperFromFiler`, `interrogateFactPaths` (inspect mode) with
   `BoothEnv.getOpForInvalidFactPaths` and `getFactRelationship`,
   `clickAction` (fingerprint, search, detain, denial reason),
   `printSearchPhoto`, poison and time bomb, `handlePaperCustomLinkClicked`,
   `addNewEnvPapers`, `setEnabled` / `getEnabled`, `StampApproval`; and
   `BoothEnv.hasErrors`, `getCiteText`, `wantConfiscatePassport`, where
   `mistakeCaught` is set, `Day.addCitation` and penalties. Also fact
   groups / correlation (`FactGroup.autoGetCorrelationPairs`).
2. **Faces**: `FaceLib` constructor (`Faces.xml` into metadata keys) and the
   `Face` constructor (`heightInPixels`, which sets the traveler's height).
   With that, nothing blocks a **Python reference implementation of traveler
   creation** driven from a master seed (`run-and-seeds.md`), to serve as
   the answer key for testing the Rust code.
3. Remaining data files (`data-files.md`): news (`DayNews`,
   `NewsArticle`), nights, ends, paths, sounds, text (`Lang.loadFromXml`),
   fonts, emblems, bodies.
4. Saves (`play.EncryptedStore`, `play.save`, `StoryState.load`), the rest
   of `Game.applyScreenChange` (new game versus load), endless mode, and the
   night and ending screens.
5. Audio extraction (probably `sharedassets0.resource`; not checked) and the
   language zips in `StreamingAssets/loc/`. This does not depend on steps 1
   to 4 and can be moved earlier if wanted; it may need a Unity asset tool
   (ask before downloading).
6. Rendering and input side of the original (`app.vis`, `play.ui`,
   `play.screen`), then design and build the Rust port.

## Open questions and unconfirmed items

Collected from the docs, so they are not lost:

- The stamp-result flags: that `APPROVED`, `DENIED`, `REASONED` are bits 2,
  4 and 8 is inferred (`responses-and-events.md`); part 2 checks it.
- 26 response names are not whole strings in the code (`Give-...`,
  `Interrogate-Detain-Replace`, `Interrogate-Search-Replace`,
  `LinkClicked-EzicNote-open`); that the code builds them is inferred.
- `Facts.xml` `<cite when="*...">`: whether the `*` is stripped before the
  "contains" test (one entry, `*bomb`).
- `Error.requiredPaperIds` appears never to be filled. Not searched: whether
  anything else calls `collectPaperIds`.
- Whether there is exactly one `BoothEngine` (and so one `BoothEnv` and one
  "recent error groups" memory) per day.
- `Game/Visitor<n>`: `n` is probably the day number.
- `DURATION_SLOW` applies when the platform is `PHONE`; fine for a desktop
  port, noted in case mobile matters.
- Who uses `TabParser.expandParams` besides `ErrorLib` was not searched
  beyond the data files studied.
- The seeds of 7 minor generators (`rand.md`).
- 20 traveler entries nothing refers to (`travelers-txt-format.md`), and
  three data files never loaded by name (`Threads.txt`,
  `TravelerGraph.txt`, `Version.txt`). Purpose unknown.
- Six speech responses named nowhere found (`speech.md`); whether the code
  builds their names was not searched. `[m]`/`[f]` gender switches are unused
  in English; the language packs were not checked.
- One `contrabandTypes` value in `Travelers.txt` is `$Gun0`; what the `$`
  means there is not known. What `canDetain`, `forceDeny`, `slow`,
  `leaveDir` and `special` do in play beyond what part 1 shows.
- What the day's token list (filled by `Token...` papers) and
  `Bulletin/PageMask` are used for; which classes outside `BoothEnv` call
  `addPaper` (`papers-on-desk.md`).
- `FingerprintCode.fromString`: who calls it.
- Where the saved date-format setting is loaded.
- Data slips recorded (not questions): `ask-forgery-asylumgrant` reads a fact
  that does not exist (`speech.md`); `=!` in `EZIC_DIPLO` makes a group
  that never runs (`responses-and-events.md`).
- Two Ghidra analysis errors and 36 functions without a typed signature
  (`ghidra-workflow.md`); neither has mattered so far.
- Nothing has been compared with the running game.

## Verification against the original

The stated problem: the original's screen cannot be seen, so the port is
checked with numbers and logs.

- **Emulator** (works): run self-contained pieces of the real code in
  Ghidra's emulator. Used for `app.Rand` (`EmulateRand.java`) and the
  string hash (`EmulateStringHash.java`). Breakpoints let it read an
  intermediate result before the code reaches the allocator.
- **Reference scripts** checked so far: `rand.py` (emulator), `gdate.py`
  (every day 1800 to 2200 against Python's calendar), `haxemap.py` (hash in
  the emulator; table logic by reading and a self-test).
- **The game's own debug logging.** Many functions call
  `Trace.customPrint` behind two switches, `Trace.enabled` and
  `Trace.showVerbose` (for example "New Traveler:" with a full description,
  "Additional error:", "ErrorIds:"). The command-line word `trace` turns on
  `enabled`; nothing found so far turns on `showVerbose`
  (`run-and-seeds.md`). Not done: a full search for writes to
  `showVerbose`, finding where the output goes, and running the game with
  `trace` (needs the user's go-ahead).
- **The test automation** (`test.auto.*`, 103 classes; `Auto.txt`,
  `TestScenarios.xml`) can replay from a fixed master seed
  (`autoReapplyRandomSeed`) and is chosen at start-up when a valid plan
  exists (`AutoPlan.make`, command-line word `soak`). Not studied.
- **Save files**: the story seed is not saved (`run-and-seeds.md`), so saves
  give day facts but not the randomness. Not investigated further.

## Things that exist only on this machine

All gitignored. Nothing below is in git.

| Path | Size | What | How to recreate |
|---|---|---|---|
| `game/` | 90 MB | Copy of the GOG install | Copy `C:\GOG Games\PapersPlease` |
| `dumps/il2cppdumper/` | 31 MB | Names, layouts, string table | `il2cpp-name-recovery.md` |
| `decompiled/ghidra/` | about 480 MB | Analysed Ghidra project with names and types | `ghidra-workflow.md` steps 1 to 3 (about 20 minutes) |
| `decompiled/*.c`, `*.clean.c`, `*.txt` | small | Decompiled functions and instruction dumps read in the sessions (about 85 files) | Step 4 of `ghidra-workflow.md` |
| `extracted/Art.dat` | 3 MB | Archive cut from `sharedassets0.assets` by hand | Offsets in `art-dat-format.md` |
| `extracted/art/` | 9 MB | The 614 unpacked files | `art-dat-format.md` commands |

(The older backup `decompiled/ghidra_backup_named/` no longer exists.)

Outside the project: `C:\tools\Il2CppDumper-6.7.46`, `C:\tools\ghidra_12.1.4_PUBLIC`,
`C:\Users\farha\.claude\CLAUDE.md` (lists those tool paths for every
project), and Claude's memory notes for this project in
`C:\Users\farha\.claude\projects\C--Users-farha-dev-papersplease-rea\memory\`.
Ghidra also keeps a small cache in `C:\Users\farha\AppData\Local\ghidra\`.

## Scripts

| Folder | What |
|---|---|
| `scripts/ghidra/` | Ghidra scripts (names, types, decompile, references, string uses, assembly dump, the two emulator checks) and `clean_decompile.py` |
| `scripts/extract/` | `decrypt_art.py`, `unpack_art.py` |
| `scripts/reference/` | Reference implementations: `rand.py` (checked in the emulator), `tabtree.py` (checked against the data files), `seeds.py` (master seed to day seeds; from the code, not checked against the running game), `gdate.py` (checked against Python's calendar), `haxemap.py` (hash checked in the emulator) |
| `scripts/checks/` | Checks run against the real data files; see its `README.md` for each script's arguments |

## Working agreements

- **Correct over fast.** Read whole functions; never present a name match as
  a finding; read data-file comments; search other files before calling
  anything unused; do not explain "why" without evidence. The study method
  is in `ghidra-workflow.md`.
- When the decompiler drops something, check the raw instructions
  (`DumpAssembly.java`) instead of guessing.
- One step at a time, each with a doc, a `MODLOG.md` entry and its own
  commit. Commits only when asked. When two steps share edits, they are
  still split into separate commits.
- **`docs/PROGRESS.md` is updated only when the user asks** (usually before
  the conversation fills up). Each step still gets its doc and a `MODLOG.md`
  entry. (Also saved in Claude's memory notes.)
- Before a step that needs a download (for example a Unity asset tool for
  audio), say the tool's name, source and size and wait.
- Running the original game (for example with `trace`) needs the user's
  go-ahead.
- REA's Ghidra tools cannot be used on `GameAssembly.dll` (`STATUS.md`).
