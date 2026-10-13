# Where the project stands

**Read this first in a new session.** Last updated 2026-10-14, in the
sixth session (after part 1 of the border scene: the figures and the waiting
line). `MODLOG.md` has the step-by-step history; this file is
the current state, what to do next and what is still open. It is updated at
the end of every step. The rules for how to work are in `CLAUDE.md`, not
here.

## One-paragraph summary

The game is Haxe compiled to C# and then to native code by Unity IL2CPP.
Names, data layouts and typed signatures are recovered and loaded into a
saved Ghidra project, so any function can be decompiled by name. The
content archive (`Art.dat`) is decrypted and unpacked: 614 images, fonts and
plain-text data files. The game is strongly data-driven. **Every data file
now has a write-up.** Traced from the code: the seed chain from launch to
each day; how a traveler is chosen, built and given documents with right or
deliberately wrong values; how errors are chosen and applied; speech; the
booth's events, the player's actions and how mistakes are judged; faces;
the day's headlines and the newspaper picture; the night (family, budget, endings by debt or death);
endings, text, sounds, seals, bodies, endless mode, fonts, the border
scene's paths and pictures, how its figures follow a path and how the
waiting line works, credits, languages. A Python reference builds
complete travelers from a master seed, and **it now matches the running
game**: the game's own test player was run with a fixed seed, and for the 36
travelers of days 1 to 4 the reference gives the same entry, nationality,
purpose, papers and errors as the game's log. No Rust code exists yet.

## How far along

Rough estimate: **about 40% of the work**, low confidence. Estimated total:
100 to 200 hours of sessions.

| Stage | Share | State |
|---|---|---|
| 1. Tools to read the code | 3% | Done |
| 2. Getting assets out | 5% | About half: images, fonts, data done; audio, language packs, scripted `Art.dat` cut-out not done |
| 3. Understanding the data files | 12% | Done: all 31 files in the data folder are written up (`data-files.md`). The 3 that the game does not read are noted as such |
| 4. Understanding the game logic | 30% | Roughly 75%. Done: the traveler pipeline (with a Python reference that matches the game), speech, booth events, player actions, judging, faces, news selection, the night's rules, the newspaper picture, endless-mode rules, part 1 of 4 of the border scene (figures and the waiting line). Not done: the rest of the border scene, saves, the screens (title, night, ending, endless, language chooser), drawing text and documents |
| 5. Building the browser game in Rust | 40% | Not started. Rust 1.99 and `wasm32-unknown-unknown` are installed; `trunk`, `wasm-pack`, `wasm-bindgen` are not; Bevy not tried |
| 6. Comparing with the original | 10% | Started and working: a repeatable method exists and days 1 to 4 of one seed match (see "Verification") |

## What is documented

| Doc | Covers |
|---|---|
| `il2cpp-name-recovery.md` | Il2CppDumper run and checks |
| `ghidra-workflow.md` | Commands, scripts, how to read decompiled output, the emulator, the study method |
| `art-dat-format.md` | The encrypted archive |
| `data-files.md` | Index of every data file, its loader and its write-up |
| `port-requirements.md` | Exactness rules the Rust port must follow |
| **Base** | |
| `rand.md` | The random generator, checked against the machine code |
| `run-and-seeds.md` | Start-up: the master seed, story seeds (a new game uses the second one), cyclers, command-line words, the debug log switches |
| `tab-tree-format.md` | The indented-tree reader and templates |
| `haxe-maps.md` | Haxe's `StringMap` and `IntMap`: hash, layout, walking order |
| **Travelers and the booth** | |
| `days-csv-format.md` | `Days.csv` |
| `papers-xml-format.md` | `Papers.xml` (layout and drawing not studied) |
| `facts-xml-format.md` | `Facts.xml`, plus random-pick procedures |
| `travelers-txt-format.md` | Traveler scripts |
| `errors-txt-format.md` | `Errors.txt` and error selection |
| `traveler-creation.md` | The sequence that creates a traveler |
| `traveler-build.md` | Building the person: face, name, id, fingerprints, height, weight, criminals |
| `operations-and-fact-validity.md` | Running an operation; invalid facts |
| `fact-values.md` | How each document value is generated |
| `value-helpers.md` | Wrong names, aliases, typos, wrong faces and fingerprints, dates |
| `papers-on-desk.md` | Adding and removing papers, staying papers, the bulletin |
| `desk-drawing-draws.md` | **The random draws made when a paper is drawn on the desk** (tilt, photo, seal). Needed to stay in step with the game |
| `speech.md` | `Speeches.txt` and how say lines become speech (each stock line draws) |
| `responses-and-events.md` | The booth's events, responses, conditions, operation queue, button commands, citations |
| `player-actions.md` | Stamping, giving and confiscating, the filer, interrogation, fingerprint / search / detain, poison and bomb, judging, penalties |
| `faces.md` | `Faces.xml`, face sheets, how a face picture is composed |
| `emblems-and-bodies.md` | `Emblems.xml` (seals) and `Bodies.xml` (body types, contraband) |
| **Around the day** | |
| `news-txt-format.md` | `News.txt`, which headlines a day gets and in what order |
| `newspaper-picture.md` | The newspaper picture: the six layout pictures, which article goes in which rectangle, what is drawn, its random draws; the news screen. Text fitting not modelled |
| `nights-txt-format.md` | `Nights.txt`: scheduled events, budget lines, the calendar |
| `night.md` | The night itself: family members, the budget, illness, hunger, cold, the debt and death endings |
| `ends-xml-format.md` | `Ends.xml` and `Intro.xml`: the 20 endings and the intro slides |
| `endless-mode.md` | `Endlesses.xml`, `Endless.csv`: styles, courses, scoring |
| `text-xml-format.md` | `Text.xml`: texts, placeholders, the long date |
| `sounds-xml-format.md` | `Sounds.xml`: which recording plays, song names |
| `fonts.md` | `Fonts.xml` and the `.fnt` files: measurements, text width, line breaking |
| `paths-xml-format.md` | `Paths.xml`: paths and animations of the figures in the top view |
| `borderanim-xml-format.md` | `BorderAnim.xml`: the picture atlas and how an animation finds its frames |
| `border-figures.md` | **The border scene, part 1**: which random generator it uses, how a figure follows a path frame by frame (what `hold`, `delay`, `snap`, `warp`, `face` and the event attributes do), the waiting line (building, moving up, the ring of reused figures, dispersing, panic) and its random draws |
| `credits-txt-format.md` | `Credits.txt` and the layout of the credits list |
| `languages-list.md` | `Languages.txt`, `Languages.png` |
| `test-tooling-files.md` | `TestScenarios.xml`, `Auto.txt` (a recipe for reaching every ending) |
| `unused-data-files.md` | `Threads.txt`, `TravelerGraph.txt`, `Version.txt`: not read by the game |
| **Checking against the original** | |
| `comparing-with-the-game.md` | The game's test player: the `auto.plan` file, how to run it with a fixed seed, the log it writes, and the results of the runs so far |

## Currently stuck

Nothing.

Two earlier problems are solved. Their records are kept with their topics,
so the dead ends are not repeated: REA's Ghidra requests timing out (end of
`ghidra-workflow.md`), and the booth's random numbers falling out of step
with the game (end of `comparing-with-the-game.md`).

## Next steps, in order

(Done in the fourth session: the booth layer of the reference; every
remaining data file; the night's rules; the method for comparing with the
running game and the first two runs; finding and fixing why the reference's
error picks left the game's. Done in the fifth: the newspaper picture. Done
in the sixth: part 1 of the border scene.)

1. **A longer comparison run of the game**: **postponed by the user on
   2026-10-14** ("skip for now"). Do not start it without being asked; it
   also needs the go-ahead for each launch. What it would test: later days
   and a second seed, for what days 1 to 4 never exercised. The list is at
   the end of `desk-drawing-draws.md`: pages
   drawn again when turned, the fingerprint / thumbprint / contraband
   pictures, the identity record, a hidden paper shown later, invalid seals,
   criminal photos on the bulletin. It would also test documents that only
   appear later (work pass, id card, access permit, vaccine certificate...).
   A full route takes about 40 seconds per day.
2. **The border scene** (`play.day.border.*`, 314 functions, all decompiled
   into `decompiled/border.clean.c`), in four parts:
   - Part 1, **done**: `Person` and `WaitingLine` (`border-figures.md`).
   - **Part 2, next**: `Border` itself. Who is created and where, the state
     machine, what each of the 36 path events does
     (`Border.person_onEvent`), guards, the attacks, explosions, how path
     names are built from parts, `Border`'s own random draws, saving and
     restoring the scene (`makeStash`).
   - Part 3: sniping (`RifleButton`, `AutoSnipeTarget`, `Grenade`,
     `Border.snipe` and `checkSniped`).
   - Part 4: the cameras and panning (`BorderCam`, `BorderCamRenderer`,
     `BorderCamVisual`, `BorderPan`) and the endless scoreboard
     (`EndlessScoreboard`, `FlashingScore`).
3. **Saves** (`play.EncryptedStore`, `play.save`, `StoryState.load`), and
   the rest of `Game.applyScreenChange` (new game versus load).
4. **The screens**: title, the night screen, the ending player (slide
   timing), the endless-mode screens, the language chooser, who shows and
   scrolls the credits. (The news screen is done except its magnifier,
   `newspaper-picture.md`.)
5. **Drawing**: how text is placed (`app.vis.Text`; the newspaper's title
   and subtitle rules in `newspaper-picture.md` wait on this), how a document page is
   laid out (`PaperInnerVisuals`, read only for its random draws), the
   search photo, the rest of `app.vis` and `play.ui`; input handling.
6. **Audio extraction** (probably `sharedassets0.resource`; not checked) and
   the language zips in `StreamingAssets/loc/`. Independent of the steps
   above; may need a Unity asset tool (ask before downloading).
7. **Design and build the Rust port** (`docs/DESIGN.md` does not exist yet).
   `Auto.txt` can serve as a test plan: it lists what to do to reach each
   ending.

Small jobs that fit anywhere:

- `scripts/reference/booth.py` and `news.py`, when run by hand as scripts,
  still use the **first** story seed. A new game uses the second
  (`run-and-seeds.md`); `compare_with_log.py` already does this correctly.
- `booth.py` does not call `desk.py` or `speech.py` itself; only
  `compare_with_log.py` chains them. A single "play a day" reference that
  owns all three would be tidier.
- `scripts/checks/booth_check.py` was not re-run after `desk.py` was added
  (`booth.py` itself was not changed).

## Open questions and unconfirmed items

Collected from the docs, so they are not lost:

**From the sixth session** (`border-figures.md`)

- The border generator's draws follow real time after the scene is built
  (standing figures draw every 2 to 4 seconds). So the original does not
  play the border scene the same way twice. Whether anything that matters to
  play draws from it later is a part 2 question; how closely the port copies
  it is a design decision.
- Whether the game's frame time (`dt`) varies; `app.Clock` was not read.
- `Person.endPath` uses the `next` of whatever path the figure has **after**
  its end event was handled. Whether any `Border` handler runs into this.
- Whether anything outside the border classes uses `Day.borderRand`.
- `Endless.csv` leaves `LINE` blank in four columns; the line length that
  gives was not followed.
- Whether the game's log has anything about the border scene that could be
  compared.

**From the fourth session**

- Drawing a page again repeats its random draws (`desk-drawing-draws.md`).
  So in the original, which pages the player looks at can change later
  travelers. Whether the port copies this exactly is a design decision.
- The draws inside the fingerprint, thumbprint and contraband pictures were
  not read.
- The evidence that the reference matches the game is one seed, days 1 to 4
  (36 travelers), plus day 1 of a second route.
- `Paths.xml`: the number in automatic path names (`auto-<number>`) was not
  recovered; nothing refers to those names.
- `BorderAnim.xml`: five animation prefixes also collect another group's
  frames (for example `Guard0-Idle` and `Guard0-IdleB`); whether that shows
  in the game is not known.
- `Fonts`: the order of steps in line breaking was reconstructed from
  scrambled decompiler output; edge cases untested.
- `TestScenarios.xml`: what starts a scenario. `Auto.txt`: the order in
  which instruction blocks are consulted, and how each action is carried
  out.
- Where user-added languages come from; how a language pack is loaded.
- The test player's audit pictures come out empty in this build, and its
  frame capture needs files that only existed on the developer's Mac
  (`comparing-with-the-game.md`, "Dead ends"). Neither is usable.

**Older**

- Whether a `Day` object is constructed more than once per day. Each
  construction makes three criminal faces (using the face cycler and the
  traveler generator) and a `DayNews`.
- The newspaper (`newspaper-picture.md`): nothing in it has been compared
  with the running game; which headlines fall back to the regular font or
  lose their subtitle is not known until `app.vis.Text` is read; the
  stamp's angle (the number appears to be used as radians); whether a stamp
  needs a title; whether anything else uses the news generator; whether the
  news screen is built on every day and after loading.
- The news entry `DIPLOMAT_FIRST` is named by nothing found; who sets
  `Day.whenAddNews`; whether endless mode has news.
- Other callers of `Array.sort` (an unstable quicksort) have not been
  listed. Known users: the news list and the night's budget.
- A wrong `Purpose` for an Arstotzkan never ends in the reference
  (`fact-values.md`); the data never asks for it.
- Face sheet `M6` has artwork for one face only (piece 24); face `F1:0` has
  its shoulder dots in reverse order (`faces.md`).
- A saved name-cycler position and the non-English alias swap sets are not
  modelled in the reference scripts.
- `FilerEnvelope/Title`, `Citation/Message` and `Citation/Penalty` have no
  fact definitions in `Facts.xml` (`player-actions.md`).
- `Facts.xml` `<cite when="*...">`: whether the `*` is stripped before the
  "contains" test (one entry, `*bomb`).
- `Error.requiredPaperIds` appears never to be filled. Not searched: whether
  anything else calls `collectPaperIds`.
- Whether there is exactly one `BoothEngine` (and so one `BoothEnv` and one
  "recent error groups" memory) per day. (The comparison runs are consistent
  with one per day.)
- `Game/Visitor<n>`: `n` is probably the day number.
- `DURATION_SLOW` applies when the platform is `PHONE`; fine for a desktop
  port.
- Who uses `TabParser.expandParams` besides `ErrorLib`.
- The seeds of 6 minor generators (`rand.md`; `BorderCam`'s is now known).
- 20 traveler entries nothing refers to (`travelers-txt-format.md`).
- Six speech responses named nowhere found (`speech.md`). `[m]`/`[f]` gender
  switches are unused in English; the language packs were not checked.
- What `canDetain`, `forceDeny`, `slow`, `leaveDir` and `special` do in play
  beyond what `responses-and-events.md` shows.
- What the day's token list (filled by `Token...` papers) and
  `Bulletin/PageMask` are used for; which classes outside `BoothEnv` call
  `addPaper`.
- Where the saved date-format setting is loaded.
- The night: the screen itself, and anything the night does that is not in
  `night.md`'s list. The night's numbers were not compared with the game
  (route 1 ended in debt after day 1 as the rules predict, which is weak
  evidence).
- Data slips recorded (not questions): `ask-forgery-asylumgrant` reads a
  fact that does not exist (`speech.md`); `=!` in `EZIC_DIPLO` makes a group
  that never runs (`responses-and-events.md`); the 4th recording of a sound
  with more than three never plays (`sounds-xml-format.md`); one test
  scenario names a traveler `BOSS` that does not exist.
- Two Ghidra analysis errors and 36 functions without a typed signature
  (`ghidra-workflow.md`); neither has mattered so far.

## Verification against the original

The stated problem: the original's screen cannot be seen, so the port is
checked with numbers and logs.

- **The game's own test player (works, the main method).** The game ships
  with an automated player. A file `auto.plan` in the save folder switches
  it on, fixes the master seed and turns on the detailed log; the command
  line word `savedir <folder>` moves the save folder into this project, and
  the test player keeps its saves in memory, so real saves are untouched.
  Full instructions and the log format: `comparing-with-the-game.md`.

      game\PapersPlease.exe savedir C:\Users\farha\dev\papersplease_rea\extracted\autorun

  The log lands in `%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\Player.log`
  (Unity's own folder, outside the project); copies of the runs so far are
  in the gitignored `extracted/autorun/`. **Each launch needs the user's
  go-ahead.**
- **Comparing a log with the reference**:

      python -I scripts\checks\compare_with_log.py scripts\reference extracted\art\assets extracted\autorun\Player.route20.seed12345.log 12345

  Result so far: route 20, seed 12345, days 1 to 4: 36 of 36 travelers match
  on entry, nationality, duration, purpose, papers, error, always-errors and
  additional error. Route 1, day 1: 8 of 8. Without the desk draws 30 of 36;
  without the spoken lines 32 of 36.
- What that confirms: the seed chain; reading traveler scripts; the person,
  document values, error choice and additional error (by their draw
  counts); the desk draws; the spoken-line draws. What the log cannot show:
  names, faces, id numbers and document values directly (they are only
  confirmed through the draw counts).
- **Emulator** (works): run self-contained pieces of the real code in
  Ghidra's emulator. Used for `app.Rand` (`EmulateRand.java`) and the
  string hash (`EmulateStringHash.java`).
- **Reference scripts checked against the code or the calendar**: `rand.py`
  (emulator), `gdate.py` (every day 1800 to 2200), `haxemap.py`.
- **Checks against the data files**: one script per data file in
  `scripts/checks/` (arguments in its `README.md`). These compare the files
  with what the code reads; they are not comparisons with the running game.
- **Save files**: the story seed is not saved, so saves give day facts but
  not the randomness. Not investigated further.

## Things that exist only on this machine

All gitignored. Nothing below is in git.

| Path | Size | What | How to recreate |
|---|---|---|---|
| `game/` | 90 MB | Copy of the GOG install | Copy `C:\GOG Games\PapersPlease` |
| `dumps/il2cppdumper/` | 31 MB | Names, layouts, string table | `il2cpp-name-recovery.md` |
| `decompiled/ghidra/` | about 480 MB | Analysed Ghidra project with names and types | `ghidra-workflow.md` steps 1 to 3 (about 20 minutes) |
| `decompiled/*.c`, `*.clean.c`, `*.txt` | tens of MB | Decompiled functions read in the sessions (about 80 cleaned files). The big ones: `boothall` (all 1,433 booth-class functions), `testauto` (the whole test player), `border` (all 314 border-scene functions; takes about 3 minutes) | Step 4 of `ghidra-workflow.md`; `boothall` takes about 15 minutes |
| `extracted/checks/` | small | Test face pictures, the overview of all faces, the face height survey | `faces.py` (`show`, `overview`, `survey`) |
| `extracted/Art.dat` | 3 MB | Archive cut from `sharedassets0.assets` by hand | Offsets in `art-dat-format.md` |
| `extracted/art/` | 9 MB | The 614 unpacked files | `art-dat-format.md` commands |
| `extracted/autorun/` | 2 MB | The test player's folder: `auto.plan`, `auto.log`, copies of three `Player.log` runs, and scratch scripts from the fourth session (`show.sh` prints one decompiled function with the noise removed; `rand_uses2.py` lists functions matching a pattern; `log_step.py`; several experiments) | The logs: run the game as above (needs the go-ahead). The scratch scripts are conveniences, not needed |

Outside the project: `C:\tools\Il2CppDumper-6.7.46`, `C:\tools\ghidra_12.1.4_PUBLIC`,
and `C:\Users\farha\.claude\CLAUDE.md` (lists those tool paths for every
project).
Ghidra also keeps a small cache in `C:\Users\farha\AppData\Local\ghidra\`.
Running the game writes Unity's `Player.log` under
`%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\`.

## Scripts

| Folder | What |
|---|---|
| `scripts/ghidra/` | Ghidra scripts (names, types, decompile, references, static writes, string uses, assembly dump, the two emulator checks), `clean_decompile.py`, and `read_doubles.py` (reads the number constants the decompiler shows only as addresses) |
| `scripts/extract/` | `decrypt_art.py`, `unpack_art.py` |
| `scripts/reference/` | Reference implementations. Base: `rand.py`, `tabtree.py`, `seeds.py`, `gdate.py`, `haxemap.py`. Traveler answer key, in layers: `cyclers.py`, `faces.py` (needs Pillow), `person.py`, `travspec.py`, `errormaker.py`, `values.py`, `factlib.py`, `booth.py` (everything chained), plus what happens between travelers: `desk.py` (draws when papers are drawn) and `speech.py` (spoken lines). Others: `news.py` (headlines), `newsimage.py` (newspaper layout and draws; needs Pillow), `nights.py` (night events, budget, the family), `fonts.py`, `paths.py` |
| `scripts/checks/` | Checks against the real data files, and `compare_with_log.py` against the running game's log; see its `README.md` for each script's arguments |
