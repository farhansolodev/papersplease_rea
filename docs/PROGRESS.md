# Where the project stands

**Read this first in a new session.** Last updated 2026-10-13, at the end of
the first long session. `MODLOG.md` has the step-by-step history; this file
is the current state, what to do next and what is still open.

## One-paragraph summary

The game is Haxe compiled to C# and then to native code by Unity IL2CPP.
Names, data layouts and typed signatures are recovered and loaded into a
saved Ghidra project, so any function can be decompiled by name. The
content archive (`Art.dat`) is decrypted and unpacked: 614 images, fonts and
plain-text data files. The game is strongly data-driven. The chain from "a
day starts" to "this traveler's passport has a wrong expiry date" is traced
at the top level from the code. No Rust code exists yet.

## How far along

Rough estimate: **8 to 10% of the work**, about 2% of the time. Estimated
total: 100 to 200 hours of sessions, low confidence.

| Stage | Share | State |
|---|---|---|
| 1. Tools to read the code | 3% | Done |
| 2. Getting assets out | 5% | About half: images, fonts, data done; audio, language packs, scripted `Art.dat` cut-out not done |
| 3. Understanding the data files | 12% | 5 of about 17 studied (table below) |
| 4. Understanding the game logic | 30% | Traveler creation, errors, fact values traced; much else untouched |
| 5. Building the browser game in Rust | 40% | Not started. Rust 1.99 and `wasm32-unknown-unknown` are installed; `trunk`, `wasm-pack`, `wasm-bindgen` are not; Bevy not tried |
| 6. Comparing with the original | 10% | Not started; see "Verification" below |

## What is documented

| Doc | Covers |
|---|---|
| `il2cpp-name-recovery.md` | Il2CppDumper run and checks |
| `ghidra-workflow.md` | Commands, scripts, how to read decompiled output, the study method |
| `art-dat-format.md` | The encrypted archive |
| `data-files.md` | Index of every data file and its loader |
| `days-csv-format.md` | `Days.csv`, fully |
| `papers-xml-format.md` | `Papers.xml`, fully (layout and drawing not studied) |
| `facts-xml-format.md` | `Facts.xml`, fully, plus random-pick procedures |
| `rand.md` | The random generator, checked against the machine code |
| `tab-tree-format.md` | The indented-tree reader and templates |
| `travelers-txt-format.md` | Traveler scripts, up to traveler creation |
| `errors-txt-format.md` | `Errors.txt` and error selection |
| `traveler-creation.md` | The sequence that creates a traveler |
| `operations-and-fact-validity.md` | Running an operation; invalid facts |
| `fact-values.md` | How each document value is generated |
| `papers-on-desk.md` | Adding and removing papers, staying papers, the bulletin |
| `traveler-build.md` | Building the person: face, name, id, fingerprints, height, weight, criminals |
| `port-requirements.md` | Exactness rules the Rust port must follow |

## Next steps, in order

(Done 2026-10-13: `BoothEnv.addPaper` and the bulletin, see
`papers-on-desk.md`; the `Traveler` constructor, see `traveler-build.md`.)

1. **Where the run is set up**: where the face and name cyclers are created
   and seeded (`BoothEnvRun`, `play.Bootstrap`), and where a new game's
   story seed comes from. Needed before any traveler can be reproduced.
2. **Helpers used by the value generator**: `TravelerName`
   (`getFormatted`, `getRandomInvalidated`, `getRandomAlias`),
   `Lang.makeAlias` / `makeTypo` / `getReplaced`, `FaceSpec.getInvalid`,
   `FingerprintCode.makeInvalid`, `Settings.formatDate`, `GregorianDate`
   (`afterYears`, `afterDays`), and the face image's height in pixels
   (`Face` constructor).
3. **Haxe `StringMap` order.** Adding a paper generates its facts in the
   hash order of a `StringMap`, and the order decides which random draws
   each fact gets (`papers-on-desk.md`). Study `haxe.ds.StringMap` as
   compiled here (its hash function, which probably calls
   `String.GetHashCode`, how the table grows, how iteration walks it), check
   it in the Ghidra emulator, and add it to `scripts/reference/`.
4. **Speech**: `BoothEnv.getSpeech` (`0x1804798f0`), `Speeches.txt`,
   `data.SpeechLib`. Settles how `$name` (travelers) and bare ids (errors)
   become text.
5. **Running responses**: `BoothEngine.handleEvent` (`0x180468a30`, about
   8 KB), `BoothEnv.findDefaultRunOpNode` (`0x180476030`),
   `BoothEnv.testExpression` (`0x180480ec0`) and
   `BoothEnv.expandExpressionLhs` (`0x180475f20`). Settles what each event
   and button does, how `DEFAULT` is used, and how response conditions with
   `Traveler/...` on the left are evaluated.
6. Remaining data files (see `data-files.md`): faces and bodies, names,
   news, nights, ends, paths, sounds, text, fonts, emblems.
7. Saves (`play.EncryptedStore`, `play.save`), where the story seed comes
   from, and the night and ending screens.
8. Audio extraction (probably `sharedassets0.resource`; not checked) and the
   language zips in `StreamingAssets/loc/`.
9. Rendering and input side of the original (`app.vis`, `play.ui`,
   `play.screen`), then design and build the Rust port.

Once steps 1 to 3 are done, a reference implementation of traveler creation
can be written in Python (like `scripts/reference/rand.py`) and used as the
answer key for testing the Rust code.

## Open questions and unconfirmed items

Collected from the docs, so they are not lost:

- `Facts.xml` `<cite when="*...">`: whether the `*` is stripped before the
  "contains" test (one entry, `*bomb`).
- `Error.requiredPaperIds` appears never to be filled. Not searched: whether
  anything else calls `collectPaperIds`.
- Whether there is exactly one `BoothEngine` (and so one `BoothEnv` and one
  "recent error groups" memory) per day.
- The misspelled `=!` in `EZIC_DIPLO`: always false only if response
  conditions use `ExpressionTester.test`. Step 5 settles this.
- `Game/Visitor<n>`: `n` is probably the day number.
- `DURATION_SLOW` applies when the platform is `PHONE`; fine for a desktop
  port, noted in case mobile matters.
- Who uses `TabParser.expandParams` besides `ErrorLib` was not searched
  beyond the data files studied.
- Where a new game's story seed comes from, and the seeds of 12 minor
  generators (`rand.md`).
- 20 traveler entries nothing refers to (`travelers-txt-format.md`), and
  three data files never loaded by name (`Threads.txt`,
  `TravelerGraph.txt`, `Version.txt`). Purpose unknown.
- One `contrabandTypes` value in `Travelers.txt` is `$Gun0`; what the `$`
  means there is not known. What `canDetain`, `forceDeny`, `slow`,
  `leaveDir` and `special` do in play (`traveler-build.md`).
- What the day's token list (filled by `Token...` papers) and
  `Bulletin/PageMask` are used for; which classes outside `BoothEnv` call
  `addPaper` (`papers-on-desk.md`).
- Two Ghidra analysis errors and 36 functions without a typed signature
  (`ghidra-workflow.md`); neither has mattered so far.
- Nothing has been compared with the running game.

## Verification against the original: ideas not tried

The stated problem: the original's screen cannot be seen, so ports are
checked with numbers and logs.

- **Emulator** (works, used for `app.Rand`): run small self-contained
  functions of the real code in Ghidra's emulator. See `EmulateRand.java`.
- **The game's own debug logging.** Many functions call
  `Trace.customPrint` behind two flags stored in `Trace`'s static data
  (for example "New Traveler:" with a full description, "Additional
  error:", "ErrorIds:"). If those flags can be switched on, the original
  would log exactly the numbers needed. Not investigated: where the flags
  are set and where the output goes.
- **The game's own test automation.** `test.auto.*` (103 classes),
  `Auto.txt` and `TestScenarios.xml` are still in the build. Not
  investigated.
- **Save files** as a source of seeds and day facts. Not investigated.

## Things that exist only on this machine

All gitignored. Nothing below is in git.

| Path | Size | What | How to recreate |
|---|---|---|---|
| `game/` | 90 MB | Copy of the GOG install | Copy `C:\GOG Games\PapersPlease` |
| `dumps/il2cppdumper/` | 31 MB | Names, layouts, string table | `il2cpp-name-recovery.md` |
| `decompiled/ghidra/` | about 480 MB | Analysed Ghidra project with names and types | `ghidra-workflow.md` steps 1 to 3 (about 20 minutes) |
| `decompiled/ghidra_backup_named/` | 478 MB | Older copy of that project, names only | Not needed any more; safe to delete |
| `decompiled/*.c`, `*.clean.c` | small | Decompiled functions read this session | Step 4 of `ghidra-workflow.md` |
| `extracted/Art.dat` | 3 MB | Archive cut from `sharedassets0.assets` by hand | Offsets in `art-dat-format.md` |
| `extracted/art/` | 9 MB | The 614 unpacked files | `art-dat-format.md` commands |

Outside the project: `C:\tools\Il2CppDumper-6.7.46`, `C:\tools\ghidra_12.1.4_PUBLIC`,
and `C:\Users\farha\.claude\CLAUDE.md` (lists those tool paths for every
project). Ghidra also keeps a small cache in
`C:\Users\farha\AppData\Local\ghidra\`.

## Scripts

| Folder | What |
|---|---|
| `scripts/ghidra/` | Ghidra scripts (names, types, decompile, references, string uses, assembly dump, emulator) and `clean_decompile.py` |
| `scripts/extract/` | `decrypt_art.py`, `unpack_art.py` |
| `scripts/reference/` | Reference implementations checked against the game: `rand.py`, `tabtree.py` |
| `scripts/checks/` | The one-off checks run against the real data files this session; see its `README.md` |

## Working agreements reached this session

- **Correct over fast.** Read whole functions; never present a name match as
  a finding; read data-file comments; search other files before calling
  anything unused; do not explain "why" without evidence. The study method
  is in `ghidra-workflow.md`.
- When the decompiler drops something, check the raw instructions
  (`DumpAssembly.java`) instead of guessing.
- One step at a time, each with a doc, a `MODLOG.md` entry and its own
  commit. Commits only when asked.
- REA's Ghidra tools cannot be used on `GameAssembly.dll` (`STATUS.md`).
