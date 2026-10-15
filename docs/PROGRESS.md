# Where the project stands

**Read this first in a new session.** Last updated 2026-10-16, after the
screens, part 7: the endless code box and the endless screen, with the
local best score per course and style (`screens.md`; code reading only).
Earlier the same day a whole-game search showed nothing but the news
screen uses the day's news generator (`newspaper-picture.md`). Before
that 2026-10-15, in the
eleventh session (after the screens, part 6: the credits screen, and the
game's frame rate; parts 1 to 5, in the ninth and tenth sessions, were
the base of a screen, the night screen, the title screen, the menu
helper, the load screen, the confirm box, the pause screen, the settings
screen, and the intro and ending screens with their page player; all
code reading, plus one screenshot of the real night screen that
confirmed the budget's line order). Also on 2026-10-15: the older
per-topic decompiles were removed from `decompiled/`, which now holds
only `all/`, `ghidra/`, 16 library-function files and the `.txt`
listings (see "Things that exist only on this machine").
`MODLOG.md` has the step-by-step history; this file is
the current state, what to do next and what is still open. It is updated at
the end of every step. The rules for how to work are in `CLAUDE.md`, not
here.

## One-paragraph summary

The game is Haxe compiled to C# and then to native code by Unity IL2CPP.
Names, data layouts and typed signatures are recovered and loaded into a
saved Ghidra project, so any function can be decompiled by name, and
since the tenth session **all of the game's own code is decompiled once**
into `decompiled/all/` (6,856 functions), so any question can start with
a search. The
content archive (`Art.dat`) is decrypted and unpacked: 614 images, fonts and
plain-text data files. The game is strongly data-driven. **Every data file
now has a write-up.** Traced from the code: the seed chain from launch to
each day; how a traveler is chosen, built and given documents with right or
deliberately wrong values; how errors are chosen and applied; speech; the
booth's events, the player's actions and how mistakes are judged; faces;
the day's headlines and the newspaper picture; the night (family, budget, endings by debt or death);
endings, text, sounds, seals, bodies, endless mode, fonts, the border
scene's paths and pictures, how its figures follow a path, how the
waiting line works, and what runs the scene (its states, the 36 path events,
the four attack scenes, shooting and its six endings, how the day ends
there, the view, the endless scoreboard), credits, languages, the save
files (the encrypted store, the tree of saves, what one save holds; a real
save folder decrypts and matches), and how the game moves between screens
(19 kinds of request, one place that builds each screen, loads and saves),
with the "stash", a resume snapshot that the desktop game writes but never
reads back (seen in a test with the real game), and the first of the
screens: the night screen (lines start ticked, a click flips one, the
budget is balanced after every click, the appearing animation, the sleep
button), the title screen (its buttons, the title rising with the
music), the load screen (the save tree as a grid of at most 5 tracks,
continuing, starting anew, deleting), and the pause and settings screens
(Escape pauses; the list of settings they share; a changed setting is
applied and saved on the next frame; every key the game reads, and every
other use of Escape, which is always a screen's "back button"), and the
intro and the endings (one page player: a 1-second wipe from the right,
then the caption types on, then NEXT; the ending fades to its statistics
page over 2 + 2 + 2 seconds and records the ending in `EndBits`), and the
credits screen (the first credit held for 4 seconds, then the list
scrolls 0.5 pixel a frame, 4 times that while the mouse button is held,
and loops; the game runs at 60 frames a second on most screens), and the
endless screens (the code box: code 62131, five blinks over 3 seconds;
the endless screen: style and course rows, the choice kept in the
settings, a result box after a run, and the player's best score per
course kept locally even without leaderboards). The desktop
layout turned out to have no panning, no camera screens and no slow motion:
those exist only in the phone and tablet layouts. A Python reference builds
complete travelers from a master seed, and **it now matches the running
game**: the game's own test player was run with a fixed seed, and for the 36
travelers of days 1 to 4 the reference gives the same entry, nationality,
purpose, papers and errors as the game's log. The night model also
reproduces four hand-played nights exactly, from the facts in real saves.
No Rust code exists yet.

## How far along

Rough estimate: **about 40% of the work**, low confidence. Estimated total:
100 to 200 hours of sessions.

| Stage | Share | State |
|---|---|---|
| 1. Tools to read the code | 3% | Done |
| 2. Getting assets out | 5% | About half: images, fonts, data done; audio, language packs, scripted `Art.dat` cut-out not done |
| 3. Understanding the data files | 12% | Done: all 31 files in the data folder are written up (`data-files.md`). The 3 that the game does not read are noted as such |
| 4. Understanding the game logic | 30% | Roughly 80%. Done: the traveler pipeline (with a Python reference that matches the game), speech, booth events, player actions, judging, faces, news selection, the night's rules, the newspaper picture, endless-mode rules, the whole border scene in four parts (figures and the waiting line, `Border` itself, shooting, the view with the cameras and the endless scoreboard), saves in two parts (the store, the save tree, one save's content, settings and statistics files; screen changes and the stash). The screens, parts 1 to 7: the base of a screen, the night screen, the title screen, the menu helper, the load screen, the confirm box, the pause screen, the settings screen, the intro and ending screens with their page player, the credits screen, the endless code box and the endless screen (`screens.md`); the frame rate (`border-view.md`). Not done: the language chooser, the family pictures of the night screen, drawing text and documents |
| 5. Building the browser game in Rust | 40% | Not started. Rust 1.99 and `wasm32-unknown-unknown` are installed; `trunk`, `wasm-pack`, `wasm-bindgen` are not; Bevy not tried |
| 6. Comparing with the original | 10% | Started and working: a repeatable method exists and days 1 to 4 of one seed match; a real save folder gives a second method (see "Verification") |

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
| `save-format.md` | **Saves, part 1**: the save folder and its `.sav` files, the encryption, the tree of saves (`headers`), what one save holds (the story facts as XML), saving / loading / deleting, `StoryState`, the settings and statistics files, the debug jump's faked facts, and the comparison with a real save folder. **Part 2**: the 19 requests a part of the game can make (`GameTransition`), how a screen change is queued and built (`Game.queueScreenChange`, `applyScreenChange`), the game's own five states (fade, pause), and the stash: when it is written, deleted and read, what it holds, how it is restored |
| `screens.md` | **The screens, part 1**: the switches every on-screen object carries (active, takes input, is updated), what every screen is built on (`GameScreen`), and the night screen: what it builds and in what order, tall or short budget lines, ticking, when the budget is balanced and what the player sees, the appearing animation and its timings, the sleep button, the family sentences (`Family.buildMessage`). **Part 2**: the title screen (its buttons and what each does, the title rising in 20 steps with the music, the logo bobbing), the menu helper `Menu`, and the desktop values of eight layout fields. **Part 3**: the load screen (the grid of save buttons, how saves are put on up to 5 tracks, what a click does, the summary box, deleting) and the confirm box `Confirm`. **Part 4**: which key pauses (Escape) and the game's 11 key numbers, the pause screen, the settings screen, the settings list both share (its rows in each form, what each click does, how a row is laid out), who writes the settings file (`Game.applySettings`), that nothing in the build reads `platover`, the header helper, and seven more desktop layout values (one of them corrects part 2). **Part 5**: the page player of the intro and the endings (the wipe, the typing caption, NEXT, hurrying a page from page 2 of the intro), the intro screen, the ending screen (its steps, the statistics text, the 2 + 2 + 2-second fade, the button), `EndBits` and the load screen's ending marks, restoring an ending stash. **Part 6**: the credits screen (who opens it, which languages are available, where the list sits, the 4-second hold at the first view, the scroll by frame and the fast scroll while the mouse button is held, the loop, the buttons). **Part 7**: the endless code box (`UnlockConfirm`: the keys, the check, the blinking, the code 62131), the endless screen (its two rows, selecting and the stored choice with its fallback, the selection line, PLAY and BACK, the score under each course and the local best score kept in the statistics, the result box after a run, the hidden clear-achievements box and press-kit helper; where it touches leaderboards, left out by the user's decision). Each part ends with a list of things to watch in the game |
| `ends-xml-format.md` | `Ends.xml` and `Intro.xml`: the 20 endings and the intro slides |
| `endless-mode.md` | `Endlesses.xml`, `Endless.csv`: styles, courses, scoring (the endless screen is in `screens.md`, part 7) |
| `text-xml-format.md` | `Text.xml`: texts, placeholders, the long date |
| `sounds-xml-format.md` | `Sounds.xml`: which recording plays, song names |
| `fonts.md` | `Fonts.xml` and the `.fnt` files: measurements, text width, line breaking |
| `paths-xml-format.md` | `Paths.xml`: paths and animations of the figures in the top view |
| `borderanim-xml-format.md` | `BorderAnim.xml`: the picture atlas and how an animation finds its frames |
| `border-figures.md` | **The border scene, part 1**: which random generator it uses, how a figure follows a path frame by frame (what `hold`, `delay`, `snap`, `warp`, `face` and the event attributes do), the waiting line (building, moving up, the ring of reused figures, dispersing, panic) and its random draws |
| `border-scene.md` | **The border scene, part 2**: the figures `Border` owns, its 12 states, the normal call-in cycle, what happens when a traveler leaves or is detained, when and how the four attacks run, what each of the 36 path events does, explosions, how the day ends, saving, every random draw |
| `border-shooting.md` | **The border scene, part 3**: when the player can shoot, the two rifles and their keys, what a shot does and whom it hits, the attack result and its six endings, bullet holes, the grenade's flight, slow motion and which clock runs what, the test player's aiming helpers |
| `border-view.md` | **The border scene, part 4**: the three screen layouts and their border values (desktop: no panning, no cameras, no slow motion; hit box 8 x 18), how the view slides and follows a figure, the camera screens, the endless scoreboard and its flashing texts, the game's clock and frame time, and the frame rate (60 frames a second when the screen's refresh matches, otherwise 65; added 2026-10-15) |
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
in the sixth: the whole border scene, parts 1 to 4. Done in the seventh:
saves, part 1. Done in the eighth: saves, part 2. Done in the ninth: the
screens, parts 1 to 3. Done in the tenth: the screens, parts 4 and 5.
Done in the eleventh: the screens, part 6. Done on 2026-10-16: the
screens, part 7.)

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
2. **The border scene**: **done**, in four parts (`border-figures.md`,
   `border-scene.md`, `border-shooting.md`, `border-view.md`). The 314
   functions read are in `decompiled/all/` (311 in
   `play_day_border.clean.c`, 3 in `play_day_booth.clean.c`); a condensed
   copy of `Border` can be made with `condense_decompile.py` and a name
   filter. (They were read in older copies, removed on 2026-10-15 as
   duplicates.)
3. **Saves**: **done**, in two parts (`save-format.md`). Part 2 was code
   reading, and its main claim was then tested in the real game on
   2026-10-14: after the first traveler of day 1 had left and the window
   was closed, `stash.sav` was in the folder; the next launch showed the
   title screen and left the file alone; a click on "Story" deleted it,
   and the screen that opened offered only a new game (the unfinished day
   was lost). The stash's content matches the description (`stash_check.py`,
   `0 problems`).
4. **The screens, in progress.** Parts 1 to 7 are done (`screens.md`):
   the base of a screen (`GameScreen`, the entity switches), the night
   screen, the title screen, the menu helper `Menu`, the load screen, the
   confirm box `Confirm`, the pause screen, the settings screen and the
   settings list they share, the page player of the intro and the
   endings, the intro screen, the ending screen, the credits screen, the
   endless code box `UnlockConfirm` and the endless screen.
   **Next, part 8** (suggested: the language chooser `LangChooser`
   together with the rating screen `RatingScreen` / `RatingPopup`, since
   a language change goes through the rating screen when that language
   needs one, part 4). Still to do after that:
   `play.ui.Button`'s modes and pictures (what a
   back button does is read since part 4), and the family pictures of
   the night screen (`FamilyVisuals`, a 1,930-line constructor, proposed
   as its own part). (The news screen is done except its magnifier,
   `newspaper-picture.md`.) All of `play.screen` is decompiled in
   `decompiled/all/play_screen.clean.c` (466 functions, with a condensed
   copy `play_screen.short.c`; parts 1 to 5 were read in an older copy,
   removed on 2026-10-15 as a duplicate);
   read so far:
   `NightScreen`, `TitleScreen`, `Menu`,
   `LoadScreen` and its helpers (the constructor for its parts only, not
   its positions), most of `Confirm` and `GameScreen`, `PauseScreen`,
   `SettingsScreen`, `SettingsMenu`, `SettingRow`, `SettingDim`,
   `Intro`, `IntroScreen`, `EndScreen`, `CreditScreen`, `CreditList`,
   `UnlockConfirm`, `EndlessScreen` (its desktop branch in detail). How a
   screen is asked for and built is in `save-format.md`, part 2.
   The user's screenshot of a night screen (2026-10-14) confirmed the
   order of the budget lines for one night (`screens.md`, part 1). A
   second look, at a night with no one sick, would test a different
   line count; the other items of that list need a live screen.
5. **Drawing**: how text is placed (`app.vis.Text`; the newspaper's title
   and subtitle rules in `newspaper-picture.md` wait on this), how a document page is
   laid out (`PaperInnerVisuals`, read only for its random draws), the
   search photo, the rest of `app.vis` and `play.ui`; input handling.
6. **Audio extraction** (probably `sharedassets0.resource`; not checked) and
   the language zips in `StreamingAssets/loc/`. Independent of the steps
   above; may need a Unity asset tool (ask before downloading).
7. **Sort the open questions** (added 2026-10-14 at the user's request),
   before any design work. Go through every entry under "Open questions and
   unconfirmed items" once and put it in one of five kinds:
   answered by a step already done (then close it, in its doc too); needs
   the game to run (collect these as the list for the comparison run or
   for the user to watch); the user's decision (move to the list that
   opens `docs/DESIGN.md`); will not matter for a desktop port (say why and
   leave it); could bite during the build. Answer the last kind where it is
   cheap, and for the rest write what the port should assume meanwhile.
   Result: a shorter list in which every item says why it is still open.
   Mostly sorting and doc work (Sonnet); a question that needs code reading
   needs Opus.
8. **Design and build the Rust port** (`docs/DESIGN.md` does not exist yet).
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
- **Out-of-date "not studied" notes** were swept on 2026-10-14 (36 fixes in
  18 docs, `MODLOG.md`). Left as they are because the records do not say
  which parts the comparison runs exercised: the line "Nothing here has
  been compared with the running game" in `papers-on-desk.md`,
  `operations-and-fact-validity.md`, `value-helpers.md` and `haxe-maps.md`.
  The sweep only looked for "not known" notes answered later; the docs were
  not re-read in full.

## Open questions and unconfirmed items

Collected from the docs, so they are not lost:

**From 2026-10-16** (`screens.md`, part 7)

- **The code box and the endless screen have not been watched.** The
  list is at the end of `screens.md`, part 7. The user has not played
  endless mode; typing the code 62131 on the title's ENDLESS button
  unlocks it for good (the setting `endlessUnlocked`), so watching
  changes the user's own settings file. Suggested: do it in a copy of the
  save folder, as with the stash test.
- **Decided by the user (2026-10-16): no leaderboards in the port**, since
  it will not be published. To go into `docs/DESIGN.md`'s list of
  decisions. The local best score per course and style is not a
  leaderboard and is kept (`screens.md`, part 7, "For the port").
- Suggested, still the user's to confirm: leave out the endless screen's
  hidden "clear achievements" box and the `presskit_prep` helper.
- Whether the title's buttons can be clicked through the code box (it
  has no input handling of its own); `app.vis.Text`'s height, so some
  positions are formulas only; `StringUtil.formatTime` (the time in the
  result box); `DiagramLine`'s drawing.
- Whether the GOG build's platform reports leaderboards (that decides
  whether the original shows the leaderboards button); not checked, and
  not needed for the port.

**From the eleventh session** (`screens.md`, part 6; `border-view.md`,
"The frame rate")

- **The credits screen has not been watched.** The list is at the end of
  `screens.md`, part 6; the title's "created by" text opens it.
- **A decision for the port: the credits' speed.** The original scrolls
  0.5 pixel a frame (2 while the mouse button is held), so the speed
  follows the frame rate: 60 frames a second when the screen's refresh
  is near 60, 120 or 180 Hz, otherwise a target of 65. Suggested: 30 and
  120 pixels a second, by time. This joins the frame-time decision of
  the sixth session (below).
- The credits screen has the same `web` and `twitter` buttons as the
  settings screen, which the user decided to leave out there; suggested:
  leave them out here too (to confirm).
- Estimated, not read: the header's bottom (77 if the title is 20 high),
  so the scroll area's top (79) and the stop position (159), and the
  list's height (about 2,272), all waiting on `app.vis.Text`.
- Not followed: whether pressing DONE stops the fast scroll; what the
  LEFT alignment changes in `makePushButton`; which platform the frame
  settings in `HostUnity.CreateGame` are for.

**From the tenth session** (`screens.md`, part 5)

- **The intro and the endings have not been watched.** The list is at
  the end of `screens.md`, part 5; a new game shows the intro.
- Whether the first page's picture wipes in or appears at once rests on
  what an empty picture holder's width is (not followed); item 1 of the
  watch list settles it.
- **Predicted from the code, not seen:** a second click on NEXT's spot
  within 4 seconds of an ending's last page restarts the fade to black
  and adds a second STATS header. Item 9 of the watch list.
- The caption's exact left edge waits on `app.vis.Text` (step 5); the
  picture's top (y 32) uses `title_tall`'s line height from the
  reference script, not from the game.

**From the tenth session** (`screens.md`, part 4)

- **The pause and settings screens have not been watched.** The list is
  at the end of `screens.md`, part 4; each item takes under a minute.
- (Answered later the same session, `screens.md` part 4, "Escape on the
  pause screen": Escape pressed again resumes, on release, because RESUME
  is a back button and a back button's shortcut key is Escape; with a
  confirm box open, Escape presses its CANCEL. Not watched in the game.)
- **No code that reads `platover` was found in this build** (a search of
  the whole program for callers of the reader found none; the same
  search finds the writer's one caller). On desktop it is not written
  either. Suggested for the port: leave the forced layout out.
- **Decided by the user on 2026-10-14** (for the list that will open
  `docs/DESIGN.md`): the settings screen's `web` and `twitter` buttons
  are left out, and there is **no quit option** (neither the pause
  screen's QUIT nor the title's quit button). Still open: the title's
  `version` button (suggested: leave out), and how "fullscreen follows
  the window both ways" maps to a browser, where Escape is also the
  browser's own key for leaving fullscreen.
- Key O saves a screenshot to the platform's documents folder, with no
  condition seen around it. Where that folder is was not read. (What the
  other keys do is answered the same session from a search of the whole
  game: `screens.md` part 4, "Every key the game reads". In short: Space,
  Tab/Enter and the arrows work in the booth, two of them only with an
  upgrade; T and the developer key are never tested; every other use of
  Escape is a "back button".)
- **Predicted from the code, worth one look in the game**: on the first
  title screen of a run, pressing Escape to skip the rising title should
  also quit the game when the key is let go (the skip masks the mouse,
  not the key). Escape on the finished title quits at once in any case.
  Irrelevant to the port (no quit option), but it tests the reading.
- Which stamp bar a desktop booth has: a `StampBar` unless the booth has
  a carousel; when it has one was not settled (inferred: phone only).
- Whether a desktop PC shows a Vibration row (`canVibrate`, not read).
- What the nudity setting changes: its readers were not looked up.
- **A mistake of the ninth session, found and corrected**: `screens.md`
  part 2 said the gap between menu buttons (`menuItemPaddingY`) is 0 on
  desktop. It is 10; the write was in the listing and was missed. No
  position had been computed from it. The other seven layout values of
  that table were checked again and hold.
- The pause screen's click handler knows an id `credit` (it would open
  the Twitter address) for which no button is made.

**From the ninth session** (`screens.md`, part 1)

- **The night screen was compared with one screenshot of the real game**
  (the user's, of night 3 of the replay; `screens.md`, part 1, "Compared
  with a screenshot"). Nothing that moves or needs a click has been
  watched; that list is at the end of `screens.md`, part 1.
- **The order of the budget lines on screen: confirmed for one night.**
  The reference predicted eight lines in an odd-looking order (salary
  above savings, heat between the medicine lines) and the screenshot shows
  exactly that order and the same total. This entry first said the
  prediction "looks doubtful"; that doubt was wrong (corrected
  2026-10-14). It is the first check of the game's sort against the
  screen, and so also supports the order in which balancing unticks
  lines. Still predictions: the orders for none, one and two sick members
  (heat above food with no one sick), and nights with penalties or
  bribes.
- **The lines start ticked: seen on that night.** The user confirmed the
  screenshot shows the screen as it opened, with nothing clicked: food,
  heat and three medicine lines ticked. Also reported by the user: the
  cursor turns into a hand anywhere on an optional row, which fits the
  whole row being the click area (the click itself was not reported).
- **Watching the rest is optional.** The user asked whether the animation
  must be seen to rebuild it: no. The code is the source and the timings
  are read from it; watching only guards against a misreading, and is
  cheapest once the port's night screen can be put next to the game's.
- By the code, ticking a line that cannot be afforded can untick a lower
  line and leave the clicked one ticked. Not watched.
- By the code, nothing disables the sleep button while the screen is
  still appearing. Not watched.
- (Answered the same day, in part 2: desktop shows no pause button, and
  night messages wrap at 520 pixels. The desktop block of the `Layout`
  constructor is the one that does not write `showPauseButton`.)
- **The title screen (part 2) has not been watched either**, beyond the
  user having seen "story" and "endless" on it. Its list of things to
  watch is at the end of `screens.md`, part 2.
- **A decision for the port**: the title's `version` button opens the
  developer's "check for updates" web page. Suggested: leave it out or
  show plain text. Not studied further.
- What a "beat" of the music is (`app.aud.Music`), so how long the
  title's rise takes in seconds; whether a `newversion` button is made
  anywhere. (`UnlockConfirm`, how the endless code is typed and checked,
  was on this list: read on 2026-10-16, `screens.md`, part 7.)
- **The load screen (part 3) has not been watched.** Its list is at the
  end of `screens.md`, part 3; the save folder with a branch
  (`extracted/saverun`, used through a copy) would show most of it.
- The load screen's positions were not read (heading, ending marks, day
  headers, drag hints), nor the line drawn between a save and its parent
  (`LoadButton.drawConnectingLine`), nor dragging with momentum
  (`KineticScroll`).
- (Answered in the tenth session, `screens.md` part 5: the ending
  screen sets `EndBits`, bit `num` - 1 per ending; the load screen shows
  its row of marks only once at least one ending is reached.)
- **A point for the port**: a save button shows the save's real date and
  time, so the browser build needs a clock for it.
- The summary box before continuing a save builds that day's news with a
  generator of its own seeded 0; the headline it shows need not be the
  day's real first headline. Not followed further.
- `Days.csv` has no `NIGHTMSG`, which `DayLib.getNightMessages` asks for;
  what the table reader returns for a missing name was not read.
- Not read: `FamilyVisuals` (the family pictures), `play.ui.Button`,
  `DiagramLine`, what the "instant" option of `Stater.go` changes.
  (The tween helper was on this list; it is read since: a timed change
  lasts its number in seconds, so the tick circles blink for 2 seconds.
  `screens.md`, part 1, "Timed changes".)
- Entity switches 8 ("the parts inside get input") and 16 have no name in
  the code seen; switch 2 is tested nowhere in the three tree walks.

**From the eighth session** (`save-format.md`, part 2)

- **The stash was tested once in the running game** (`save-format.md`,
  "The stash test in the running game"). Seen on desktop: a day stash
  written after the day's first traveler had left; the title screen at
  the next start with the file untouched; the file deleted by a click on
  "Story"; a content that matches the description. Still from the code
  only: the night and ending stashes, the blocker (bomb, poison, special
  exit), the days that need two travelers, the rewrite at each later
  empty booth, and a restore. The serializer's code was not studied; its
  text is read by `hxserial.py`, which covers only what a stash uses.
- A design point for the port: the desktop original loses the current day
  when the game is closed. Whether the browser port should do better (a
  tab is closed easily) is the user's decision.
- (Answered in the ninth session, from the code: without flag 4 a screen
  and everything in it get no input, without 16 they are not updated;
  they are still drawn. `screens.md`, part 1.)
- (Answered in the tenth session: key number 5 is Escape. `screens.md`,
  part 4.)
- The fade (0.125 s each way) and the 1-second wait of a screen change
  were read from the decompiler, not checked in the instructions.
- Who handles the error an invalid stash raises at start-up (phone and
  tablet only). Whether anything in `play.ui` or `app` asks for a restore.
- After a stash restore a new `Day` is built and no random generator is
  put back, so the rest of the day would differ (inferred, not followed;
  does not arise on desktop).

**From the seventh session** (`save-format.md`)

- **The first night 3 of the hand-played game: probably explained, not
  confirmed.** Its save says nothing was bought (savings 60, the son
  dead); the user remembered buying everything. The user then replayed
  that day from the day-3 save and did tick everything: that save has
  savings 25 and nobody dead, and the night model follows it exactly. So
  the rules are not in doubt. The user's explanation for the first time:
  they probably unticked everything by mistake. **The night screen was
  read in the ninth session and agrees**: food, heat and medicine start
  ticked, a click flips a line, and that night the money was enough, so
  a save with nothing bought needs one click on each of the five lines
  (`screens.md`, part 1). What was actually clicked cannot be read from a
  save.
- The save format is confirmed on one folder: four saves, one branch,
  three launches, two loads. Not exercised: deleting, the `stash` and
  `platover` entries. (Answered in the eighth session: the second sitting
  resumed by loading the save; desktop never reads a stash at start-up.)
- (Answered in the tenth session, `screens.md`, part 4: the settings
  file is written by `Game.applySettings`, which `Game.update` runs on
  the frame after any setting changes; no code that reads `platover` was
  found.) ("Read the tree" is answered since the ninth session: the
  load screen calls it each time it makes its buttons, `screens.md`,
  part 3.) (Known since the
  eighth session: delete is `LoadScreen.confirm_onClick`; `platover` is
  written on a `REQUEST_PLATFORM_CHANGE` request from the settings menu.)
- (Answered in the eighth session: nothing saves the story outside
  `ADVANCE_TO_NEXTDAY`, in everything decompiled so far.)
- When "the saved day is not later than the parent's day" (the save then
  hangs under the root) applies in play.
- Who sets `Game/Stat/Day`.
- By the code, the first number in `names.sav` is the master seed of the
  launch that created the file (here 11240598). Not tested. If true, a
  hand-played game's first travelers could be predicted from it; how far
  that holds once the player's page turns add draws
  (`desk-drawing-draws.md`) is unknown.
- `play.AlltimeStats` beyond its local file talks to the platform's
  achievements and leaderboards service. Not read: out of scope (rule 4).
  The port needs only local statistics, which include the endless best
  scores (`_Leaderboard:<style> <course>`, read on 2026-10-16,
  `screens.md`, part 7, and `save-format.md`).
- Characters above 255 would be damaged by the save encryption (the code
  does not cut character codes to 8 bits). Nothing above 127 was seen in a
  real English save; other languages were not looked at.

**From the sixth session** (`border-figures.md`, `border-scene.md`,
`border-shooting.md`, `border-view.md`)

- The border generator's draws follow real time after the scene is built
  (standing figures draw every 2 to 4 seconds). So the original does not
  play the border scene the same way twice. One thing the player can feel
  draws from it: the delay before an attack starts (`6 + 4 x r` seconds).
  How closely the port copies this is a design decision.
- **Frame time is a design decision too.** The original steps by real
  elapsed time (capped at 0.1 s a frame); its own test player uses a fixed
  1/20 s (`border-view.md`). The port must pick one. (Known since the
  eleventh session: the original runs at 60 frames a second on most
  screens, 65 on the others, never above 70; `border-view.md`, "The frame
  rate". A few things move by frame, such as the credits.)
- "The desktop game has no panning, no cameras and no slow motion" comes
  from the layout values in the code only; it was not watched in the game.
  The user can confirm it by eye in a normal play session (day 2 has the
  first attack).
- The tablet and phone layout values were not looked up (not needed for a
  desktop port).
- Who changes the clock's global speed and who forces a frame's `dt`
  (`app.Clock`). ("Pause for one frame" has two known users since the
  eighth session: the game's `paused` state and the stash resume overlay.)
- What the rifle key paper does after unlocking, and whether an unlocked
  rifle stays unlocked on later days.
- Who sends the scene to `waiting-to-fade-to-night` on a day that ends by
  the clock. (When the scene is stashed and restored: answered in the
  eighth session, `save-format.md` part 2.)
- The booth's own state machine (`empty`, `entering`, `intro`,
  `busy-with-border`, `detaining`...) is only known where `Border` touches
  it, plus: the day stash is taken on entering `empty`. The decompiler
  times out on the `Booth` constructor, where the states are set up; its
  instructions are in `decompiled/booth_ctor_asm.txt` and list the state
  names and their callbacks in order.
- `trucke1-decide`: by the code, the truck's second attacker skips his
  throwing animation in one of three ways of reaching it
  (`border-scene.md`, "One oddity"). Not watched in the game.
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

- (Answered in the eighth session, from the code: in normal play one
  `Day` object is made per played day, when the news screen is built, and
  the day and night screens reuse it. A load, the title and going on to
  the next day drop it; a stash restore builds another. `save-format.md`,
  part 2.)
- The newspaper (`newspaper-picture.md`): nothing in it has been compared
  with the running game; which headlines fall back to the regular font or
  lose their subtitle is not known until `app.vis.Text` is read; the
  stamp's angle (the number appears to be used as radians); whether a stamp
  needs a title. (Whether anything else uses the news generator was
  answered on 2026-10-16: nothing does, `newspaper-picture.md`.) (The news
  screen is built on going to the next day and after a load:
  `save-format.md`, part 2.)
- The news entry `DIPLOMAT_FIRST` is named by nothing found; who sets
  `Day.whenAddNews`; whether endless mode has news (by the code an
  endless day is queued straight as the day screen, with no news screen;
  its bulletin was not checked).
- Other callers of `Array.sort` (an unstable quicksort) have not been
  listed. Known users: the news list, the night's budget and the children
  of a save in the save tree. (The reference's copy of this sort was
  confirmed against the screen for one budget of eight lines on
  2026-10-14: `screens.md`, part 1.)
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
- What `canDetain`, `forceDeny`, `slow` and `special` do in play beyond what
  `responses-and-events.md` shows. (`leaveDir` is known since part 2 of the
  border scene: it picks the exit path, `border-scene.md`.)
- What the day's token list (filled by `Token...` papers) and
  `Bulletin/PageMask` are used for; which classes outside `BoothEnv` call
  `addPaper`.
- The night: the screen itself is read since the ninth session
  (`screens.md`, part 1; its family pictures are not). Still open:
  anything the night does that is not in `night.md`'s list. The night's numbers were compared with the game on
  2026-10-14 for four nights of one hand-played game: three with nothing
  bought and one, a replay, with food, heat and three medicines bought
  (`night.md`, "Not studied"). Penalties, bribes, attacks, the scheduled
  events and the endings were not exercised.
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

- **A screenshot from the user (works, since 2026-10-14).** A picture the
  user pastes into the session can be read and measured. One night-screen
  picture confirmed the order of eight budget lines and four horizontal
  positions to about a pixel (`screens.md`, part 1, "Compared with a
  screenshot"). The scale was taken from a picture of known width in the
  shot. Pictures are not kept in the project.

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
- **A real save folder (works, the second method).** Start the game with
  `savedir` pointing at an empty folder in the project and play by hand;
  the folder then holds the saves, settings, statistics and name position
  as encrypted text files (`save-format.md`). The folder from 2026-10-14 is
  `extracted/saverun/` (gitignored).

      python -I scripts\reference\savefile.py extracted\saverun dumps\il2cppdumper\stringliteral.json
      python -I scripts\checks\save_check.py scripts\reference extracted\saverun dumps\il2cppdumper\stringliteral.json
      python -I scripts\checks\save_night_check.py scripts\reference extracted\art\assets\data extracted\saverun dumps\il2cppdumper\stringliteral.json

  Result so far: all 8 files decrypt and re-encrypt to the same text; the
  save tree (four saves, one branch) and each save agree with the code
  reading (`0 problems`); the night model reproduces the night before each
  of the four saves with exactly one of 24, 56, 288 and 352 possibilities,
  three with nothing bought and one with everything bought. A stash from a second folder (`extracted/stash_sample`, a day-1 stash
  after one traveler) is read and compared with the description by

      python -I scripts\checks\stash_check.py scripts\reference extracted\stash_sample dumps\il2cppdumper\stringliteral.json extracted\art\assets\data

  (`0 problems`). What a save can show: the story facts after
  each night (family, money, statistics, staying papers, script flags). What
  it cannot: the story seed is not saved, so it gives no randomness, and
  it does not record what the player did.

## Things that exist only on this machine

All gitignored. Nothing below is in git.

| Path | Size | What | How to recreate |
|---|---|---|---|
| `game/` | 90 MB | Copy of the GOG install | Copy `C:\GOG Games\PapersPlease` |
| `dumps/il2cppdumper/` | 31 MB | Names, layouts, string table | `il2cpp-name-recovery.md` |
| `decompiled/ghidra/` | about 590 MB | Analysed Ghidra project with names and types | `ghidra-workflow.md` steps 1 to 3 (about 20 minutes) |
| `decompiled/*.c`, `*.clean.c` (16 files), `decompiled/*.txt` (49 files) | about 4 MB | What is not in `decompiled/all/`. The `.c` files: library functions the game calls (Haxe's maps in `maps`, `Array.sort` in `news2`, `Lambda.has` in `paperhelpers2`, `Math.random` in `seedsrc`, `String.GetHashCode` in `strhash`, `Xml` and the XML parser in `xml`, three unnamed helpers in `border_misc` and `border_view2`; 41 functions in all), each with a cleaned copy. The `.txt` files: machine-code listings (among them `booth_ctor_asm.txt` and `layout_ctor_asm.txt`, the only readable form of the `Booth` and `Layout` constructors, on which the decompiler times out), string lists in machine-code order, and Ghidra logs with search results. The older decompiles of the game's own classes were removed on 2026-10-15: every function in them is in `decompiled/all/`, identical or better (`MODLOG.md`) | Step 4 of `ghidra-workflow.md`, with the addresses in each file's `// =====` lines; for a listing, `DumpAssembly.java` or `ListStringUses.java` with the address in its `MODLOG.md` entry |
| `extracted/checks/` | small | Test face pictures, the overview of all faces, the face height survey | `faces.py` (`show`, `overview`, `survey`) |
| `extracted/Art.dat` | 3 MB | Archive cut from `sharedassets0.assets` by hand | Offsets in `art-dat-format.md` |
| `extracted/art/` | 9 MB | The 614 unpacked files | `art-dat-format.md` commands |
| `extracted/saverun/` | small | A real save folder: the user's hand-played game of 2026-10-14 (four saves with one branch, settings, statistics, name position) | Play again with `savedir` pointing at an empty folder (`save-format.md`); the same game cannot be recreated |
| `extracted/stashrun/`, `extracted/stash_sample/` | small | The stash test of 2026-10-14: the test's save folder as it ended (no stash, it was deleted by the click on "Story"), and a copy taken after the first launch that still has `stash.sav` | Play again as described in `save-format.md` ("The stash test in the running game"); the same stash cannot be recreated |
| `decompiled/booth_ctor_asm.txt` | about 0.5 MB | Read for part 2 of `save-format.md`: the instructions of the `Booth` constructor and of `HostUnity.CreateGame`. (The stash, `GameTransition` and `play.screen` functions read for that part are in `decompiled/all/`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1801b9100` and `0x1809e7b00` |
| `decompiled/titlescreen_update_asm.txt`, `loadscreen_strings.txt` | small | For `screens.md`, parts 2 and 3: the instructions of `TitleScreen.update`, and the strings of three load-screen functions in machine-code order | `DumpAssembly.java 0x180676bc0`; `ListStringUses.java` with `0x1806f4810`, `0x1806ee2e0` and `0x18093d4f0` |
| `decompiled/all/` | about 44 MB | **The whole game decompiled once** (2026-10-14): every function of the game's own classes (6,856 of 6,858; not the social service and Steam), one file per part with a cleaned copy, the address lists in `lists/`, two Ghidra logs, and `booth_react.short.c`. Search here first for "who else does this?" | `ghidra-workflow.md`, "The whole game, decompiled once": `game_function_lists.py`, then `DecompileFunctions.java` with `@` list files (about 19 minutes), then `clean_decompile.py` on each file |
| `decompiled/part7_run1.txt` | under 1 MB | For `screens.md`, part 7: the instructions of the `UnlockConfirm` and `EndlessScreen` constructors, `EndlessScreen.refreshScoreTexts`, `ScoreEntry.isBetterThan` and `ScoreEntry.toString` | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1806859c0 0x1807c1390 0x1807c6fc0 0x1808608d0 0x180860900` |
| `decompiled/part5_run1.txt` | under 1 MB | For `screens.md`, part 5: the instructions of the `EndScreen` constructor and the strings of the `Intro` and `EndScreen` constructors in machine-code order | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1807b9800`; `ListStringUses.java` with `0x1808fae90` and `0x1807b9800` |
| `decompiled/settingsmenu_music_asm.txt`, `part4_run1.txt` to `part4_run3.txt` | small | For `screens.md`, part 4: the instructions of `SettingsMenu.musicButton_whenClick`, and the Ghidra output of three runs (string lists of four functions in machine-code order, three caller searches). (The key, `InputWrapper` and `HostUnity.Update` functions read for that part are in `decompiled/all/top.clean.c` and `app_ent.clean.c`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x180714b30`; `ListStringUses.java` with `0x180710150`, `0x180869f50`, `0x18086a9b0`, `0x1808035e0`; `FindReferences.java` with `0x18086FAF0`, `0x180870B30`, `0x1804AA120`, `0x180870210` |
| `decompiled/budgetent_ctor_asm.txt`, `budgetent_ctor_strings.txt`, `asm_family_buildmessage.txt` | small | For `screens.md`, part 1: the instructions of the `BudgetEnt` constructor and of `Family.buildMessage`; the `BudgetEnt` constructor's strings in machine-code order. (The `play.night`, `RevealTextEnt` and `GameScreen` functions read for that part are in `decompiled/all/`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1806c2a70` and `0x180757930`; `ListStringUses.java 0x1806c2a70` |
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
| `scripts/ghidra/` | `game_function_lists.py` (address lists of all the game's own functions, for the whole-game decompile); Ghidra scripts (names, types, decompile with `@` list files, references, static writes, string uses, assembly dump, the two emulator checks), `clean_decompile.py`, `condense_decompile.py` (a shorter view of a cleaned file, for long classes), and `read_doubles.py` (reads the number constants the decompiler shows only as addresses) |
| `scripts/extract/` | `decrypt_art.py`, `unpack_art.py` |
| `scripts/reference/` | Reference implementations. Base: `rand.py`, `tabtree.py`, `seeds.py`, `gdate.py`, `haxemap.py`. Traveler answer key, in layers: `cyclers.py`, `faces.py` (needs Pillow), `person.py`, `travspec.py`, `errormaker.py`, `values.py`, `factlib.py`, `booth.py` (everything chained), plus what happens between travelers: `desk.py` (draws when papers are drawn) and `speech.py` (spoken lines). Others: `news.py` (headlines), `newsimage.py` (newspaper layout and draws; needs Pillow), `nights.py` (night events, budget, the family), `fonts.py`, `paths.py`, `savefile.py` (reads and decrypts a save folder; can also encrypt), `hxserial.py` (reads the text of Haxe's general serializer, as far as a stash needs) |
| `scripts/checks/` | Checks against the real data files, `compare_with_log.py` against the running game's log, `save_check.py` and `save_night_check.py` against a real save folder, and `stash_check.py` against a real stash; see its `README.md` for each script's arguments |
