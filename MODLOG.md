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
```

## 2026-10-14 The screens, part 2: the title screen and the menu helper

**Changed:** `docs/screens.md` (new part 2: what the title screen builds, what each button does, the rising title and the bobbing logo, the `Menu` class, the desktop values of eight layout fields; and two sentences of part 1 that had left the desktop pause button and message width open). `docs/run-and-seeds.md` (what `expo` does on the title screen). `docs/PROGRESS.md`. Machine-only: `decompiled/screens.short.c` (condensed copy of all `play.screen` functions) and `titlescreen_update_asm.txt`.
**Why:** next part of the screens step.
**Tested how:** code reading only; the game was not run. One read-only Ghidra run (`DumpAssembly.java 0x180676bc0`) for two arguments the decompiler dropped in `TitleScreen.update`. The layout values were read from the existing `decompiled/layout_ctor_asm.txt` by listing every store to each field. Seven number constants read with `read_doubles.py`.
**Result:** the title has the buttons `story`, `endless`, `quit`, `settings`, `credit` and, on desktop only, `version`. "Story" leads to the load screen; "endless" asks for a code unless the setting `endlessUnlocked` is on. On the first title screen of a run the whole screen rises in 20 steps tied to the music's beat and the buttons cannot be clicked until it arrives; any click or key skips it. The desktop block of the `Layout` constructor is identified (it is the one block that writes neither `showPauseButton` nor `menuItemPaddingY`, matching what `border-view.md` found for another field), which settles two points part 1 left open: desktop has no on-screen pause button, and night messages wrap at 520 pixels.
**Corrected in older docs:** `screens.md` part 1 (the two open sentences above, now answered with a note that part 1 had left them open); `docs/PROGRESS.md` (the same open question). `run-and-seeds.md` gained a clause; nothing in it was wrong.
**Still broken / not tested:** nothing watched in the running game beyond the user having seen "story" and "endless" on the title in the stash test. Not read: `UnlockConfirm`, `play.ui.Button`, `app.aud.Music` (so the rise's length in seconds is unknown), the platform functions, `SoakTapper`. "No write found" for a layout field means no store through the register holding the layout; another route would have been missed. The `version` button opens a web page: noted for the user as a port decision, not studied.

## 2026-10-14 The screens, part 1: the base of a screen and the night screen

**Changed:** new `docs/screens.md` (part 1: the entity switches, `GameScreen`, the night screen: what it builds, ticking, balancing, the appearing animation, the sleep button, `Family.buildMessage`, a list of things to watch in the game). Comments only in `scripts/reference/nights.py` (two notes that said `Family.buildMessage` was not read). `docs/PROGRESS.md`. Decompiled into the gitignored `decompiled/`: `night_screen` (all 228 `play.night` functions and `DayLib.getNightMessages`, with cleaned and condensed copies), `revealtext` (32 `play.ui.RevealTextEnt` functions), `gamescreen.short.c`, `budgetent_ctor_asm.txt`, `budgetent_ctor_strings.txt`, `asm_family_buildmessage.txt`.
**Why:** next step in `docs/PROGRESS.md` (the screens, the night screen first). Questions: does a budget line start ticked, what does a click do, when is the budget balanced, what does the sleep button do, does the screen draw random numbers.
**Tested how:** code reading only; the game was not run. Four Ghidra runs, all read-only. Checked in the machine instructions where the decompiler was unreliable: the choice of tall or short budget lines and of the message font (the decompiler had the comparisons reversed and one variable doing two jobs), the desktop budget rectangle and sleep button height, the two numbers dropped in `Family.buildMessage`, and the name of the state that follows the 1-second wait (from the string order). 18 number constants read with `read_doubles.py`. Two worked budget examples were run through the existing reference (one-off, no script added). `night_check.py`, `nights_check.py` and `save_night_check.py` re-run.
**Result:** food, heat and medicine lines start ticked; a click anywhere on an optional line flips it; `Budget.balance` runs once when the screen is built and after every click, from the bottom line up, so a tick that cannot be afforded can untick a lower line instead; the budget is applied in one place, on the sleep click. Appearing: 1.0 s of nothing, messages letter by letter (0.04 s a letter, 0.25 s after a comma, 0.5 s after a full stop), then one line per 0.25 s. No call to a random generator in any of the 228 `play.night` functions. Entity switches: 1 active, 4 takes input, 8 its parts take input, 16 is updated. The three checks: `problems: none`, `problems: none`, `0 problems`, as before. **One draft statement was wrong and was fixed before it was kept:** the first draft said line height depends on the screen shape; the instructions show it depends on whether everything fits.
**Corrected in older docs:** `night.md` (when `balance` is called; "the random generator is not used by anything read here" is now "by none of the night code"; `getNightMessages` is read; the "Not studied" entries; the night-3 conflict now says what the screen's code shows). `save-format.md` (three places that said the meaning of screen flags 4 and 16 was not read). `nights-txt-format.md` and `data-files.md` (the night screen and `buildMessage` are studied). `docs/PROGRESS.md` (open questions of the seventh and eighth sessions, the "Older" night entry).
**Still broken / not tested:** nothing here was watched in the running game. In particular the order of the budget lines on screen: the reference predicts an order that changes with the number of lines (heat above food with no one sick, salary above savings with one sick), which looks doubtful and would be settled by one look at a night screen. Not read: `FamilyVisuals` (the family pictures, a 1,930-line constructor), `play.ui.Button`, `DiagramLine`, the tween helper, most pixel positions. Not established: which layout branch is the desktop one for `showPauseButton` and `nightMessageWidth`; what the table reader returns for the missing `NIGHTMSG` name. No new check script was written: this part has nothing of its own that a script could compare with a data file.

## 2026-10-14 Saves, part 2: what the "Story" screen showed in the stash test

**Changed:** `docs/save-format.md` (step 3 of "The stash test in the running game" and its "how strong" paragraph), `docs/PROGRESS.md` (next steps, item 3).
**Why:** the entry below left one thing unrecorded; the user has now answered it.
**Tested how:** the user's report of the screen after clicking "Story" in the second launch of the test.
**Result:** only a new-game entry, nothing to continue. The day played in the first launch was lost, as the code says for a quit in the middle of a day. The folder agrees: no `headers` and no save file.
**Still broken / not tested:** one observation, and with no earlier save in the folder. A quit in the middle of a later day, where the story should continue from the save after the previous night, was not tried in this test (the user's two-sitting game of part 1 is consistent with it).

## 2026-10-14 Saves, part 2: the stash test in the running game

**Changed:** new `scripts/reference/hxserial.py` (a reader for the text Haxe's general serializer writes, limited to the codes a stash uses) and `scripts/checks/stash_check.py` with its row in `scripts/checks/README.md`; `docs/save-format.md` (new "The stash test in the running game", and the "not seen in the game" sentences of part 2 changed to say what was seen and what was not); `docs/PROGRESS.md`. New gitignored folders: `extracted/stashrun` (the test's save folder) and `extracted/stash_sample` (a copy taken after the first launch, with the stash).
**Why:** part 2 was code reading only. The user agreed to test its main claim: desktop writes a stash and never reads it.
**Tested how:** the user launched the desktop game twice with `savedir extracted\stashrun`. Launch 1: new story, day 1 until the first traveler had left, then Alt+F4. Launch 2: stop at the first screen, then click "Story". The folder was listed after the close, at the first screen and after the click. The stash was decrypted with `savefile.py`, read with `hxserial.py` and compared with the doc by `stash_check.py`.
**Result:** all three expectations held. After launch 1: `stash.sav` present (last written 10:49:34, 18,096 hex characters). At the first screen of launch 2: the user saw the title with "story" and "endless" and no resume button; the file was still there with the same time. After the click on "Story": the file was gone. `stash_check.py` on the copy: `0 problems`: one `StashedGame`, kind `DAY`, layout `DESKTOP`, stash version 7, game version 1.4.11.124; all 8 stash classes have exactly the fields the code declares; 7 story facts; day 1 with one traveler made and one paid; three desk papers, all `NORMAL` at whole-pixel positions; booth facts only for `Rules` (51) and `Bulletin` (20), none for `Transcript`; border pan 0; no random-generator object. `stash_check.py` on a folder without a stash prints one `PROBLEM` line, as it should.
**Still broken / not tested:** one stash of one kind, from day 1 with one traveler. Not tested: a night or ending stash, the blocker (bomb, poison, special exit), the days that need two travelers, the stash being rewritten at later empty booths, a restore (not possible in normal desktop play; the test player's `stash` word would do it and was not run). The serializer's code was not studied; `hxserial.py` was written from the format's public description and handles only what it needed. What the "Story" screen showed after the lost day was not recorded.

## 2026-10-14 Saves, part 2: moving between screens, and the stash

**Changed:** `docs/save-format.md` (new "Part 2": the 19 requests, queueing a screen, the game's five states, building a screen, and the stash: when it is written, deleted and read, what it holds, how it is restored). No script changed. Decompiled into the gitignored `decompiled/`: `stash` (199 functions: `play.stash.*`, `play.GameTransition`, `UnstashOverlay`, `Day`'s three stash functions, two screens), `screens` (all 471 `play.screen` functions, for searching), `stash_helpers` (3), `booth_ctor_asm.txt` (instructions of the `Booth` constructor and `HostUnity.CreateGame`), and condensed views `stash*.short.c`, `game_stater.short.c`, `loadscreen_btn.short.c`.
**Why:** next step in `docs/PROGRESS.md`. Questions: what triggers a stash, does desktop use it, is a continued story loaded or restored, what does a stash hold, what does the rest of `Game.applyScreenChange` do.
**Tested how:** code reading only; the game was not run. Two claims were checked in the machine instructions: the stash callback is the first "on entry" function of the booth state `empty` (the decompiler times out on the `Booth` constructor), and `HostUnity.CreateGame` passes "platform kind is not `DESKTOP`" as the resume option. Callers were searched by slot name in every decompiled file. `save_check.py` was re-run on the real folder.
**Result:** a stash is written on every platform (each time the booth becomes empty once a traveler has been made, when the night screen is queued, when an ending opens) and deleted when any screen other than `night` or `end` is queued. The desktop game never reads it at start-up, and the only caller of a restore request is the test player; so on desktop closing the game mid-day loses the day and a continued story is a load. A stash holds the story facts, the day's counters and the desk with an empty booth, and no random generator state. `save_check.py`: `0 problems`, as before. The three stash-less quits in the real folder agree with the code (no traveler had been processed on the day of any quit).
**Corrected in older docs:** `save-format.md` (part 1 guessed "a stash is deleted once used": wrong, restoring does not delete it; "loading was probably exercised once" is now "the second sitting was a load"; the "no stash after a quit" lines; the callers of load, save and delete; `platover`'s writer; "Not studied"). `rand.md` (its guess that the generator's save-state functions serve the stash was wrong: the stash holds no generator state). `border-scene.md` (two "when is the scene stashed" notes answered). `border-shooting.md` (two users of "pause for one frame" now known). `run-and-seeds.md` (the rest of `applyScreenChange` is read; what each branch does to seeds). `newspaper-picture.md` (the news screen is built on going to the next day and on a load). `comparing-with-the-game.md` (what the plan word `stash` does). `desk-drawing-draws.md` (a stash restore does not happen in normal desktop play). `docs/PROGRESS.md` open questions.
**Still broken / not tested:** nothing about the stash was seen in the running game, on any platform: no `stash.sav` has been seen or read, and the serializer's text format was not studied. Not read: what screen flags 4 and 16 do, which key is number 5 (pause), the booth's states beyond `empty`, who handles an invalid stash at start-up on phone and tablet. `play.ui` and `app` were not searched for restore requests. The fade and wait times (0.125 s, 1 s) come from the decompiler and were not checked in the instructions. The `play.screen` functions were searched, not read: that is the next step.

## 2026-10-14 Saves, part 1: the user's replay adds a load, a branch and a night with purchases

**Changed:** `scripts/checks/save_night_check.py` (it now replays the night before every save from that save's parent, so a branch works; before, it followed one line of saves only); its row in `scripts/checks/README.md`; `docs/save-format.md` (new subsection "The replay: a load and a branch"), `docs/night.md`, `docs/traveler-build.md`, `docs/run-and-seeds.md`, `docs/PROGRESS.md`.
**Why:** the user launched the game a third time, loaded the day-3 save, replayed the day, bought everything at night and quit early in day 4. That exercises three things the first folder did not.
**Tested how:** ran `savefile.py`, `save_check.py` and `save_night_check.py` on the folder again; compared the new save's facts with the day-3 save and with the other day-4 save.
**Result:** 8 of 8 files reproduced, 4 saves, `0 problems` in both checks. The two day-4 saves sit side by side under day 3, older first. The new save's parent is the loaded save, although the loaded file itself names the day-2 save: loading overwrote `Save/ParentId` as the code says. Its play time is the loaded save's 905 plus 423. The night before it is reproduced by exactly 1 of 352 possibilities: 10 paid, food, heat and three medicines bought (savings 25, profit 70, three sickness counters down by one). `names` went from 20 to 30 for 10 travelers processed.
**Still broken / not tested:** why the first night 3's save shows nothing bought while the user remembers buying is still not known; the replay shows the rules are right, not what was clicked the first time. The user confirmed afterwards that every line was ticked on the replayed night, and that the check's output on their machine matches. For the first night 3 the user's explanation is that they probably unticked everything by mistake; that fits but is not confirmed, and whether a line starts ticked is left for the night screen. Deleting a save, the stash and `platover` are still not exercised. Which save carries the `latest` mark cannot be seen in the file.

## 2026-10-14 Saves, part 1: the user's answers, one correction, one open conflict

**Changed:** `docs/save-format.md` ("Compared with a real save"), `docs/night.md` ("Not studied"), `docs/traveler-build.md` and `docs/run-and-seeds.md` (the `names` sentences), `docs/PROGRESS.md` (open questions, the note for part 2). No script changed.
**Why:** the user answered the two questions left by the entry below. It was one story played in two sittings (quit, then continued). Nothing was bought on nights 1 and 2; on night 3 the user remembers buying everything, medicine included.
**Tested how:** read the folder's file times to the second and compared the play-time statistic with the clock between saves; re-read the night-3 numbers in the save.
**Result:** the break between the sittings is about 20 seconds into day 3 (play time 428 s against 521 s on the clock between the last two saves; settings written 2 min 16 s after the day-3 save; all-time play time 41 s above the last save's). **Corrected:** the docs said the 20th name in `names` was taken on day 4; `names.sav` was last written at 08:02:05, before the day-4 save at 08:03:09, so it was not, and which traveler took it is unknown. New from the two sittings: the name position carried over from the first launch to the second (20 names in the file, 8 travelers processed in the second launch). **Open conflict:** the save after night 3 has savings 60 and the son dead, which cannot be "bought everything" (that leaves 15 and nobody dies); the user's memory says otherwise.
**Still broken / not tested:** the night-3 conflict is not resolved; three possibilities are listed in `night.md` and none was checked. Whether the second sitting resumed by loading the save or by restoring a stash is not known, so "loading was exercised" is only probable; and only the last quit is evidence that a desktop quit leaves no stash. The entry below says "this folder shows one playthrough, and where the other went is not known": answered here, there was no other.

## 2026-10-14 New step in the plan: sort the open questions before the design

**Changed:** `docs/PROGRESS.md` only: a new step 7 under "Next steps, in order", between audio extraction and the design step (which becomes step 8). It says to sort every open question into five kinds and to answer the cheap ones that could bite during the build.
**Why:** the user asked what happens to the open questions (about 60). They were collected but no step dealt with them, and one surfacing in the middle of the build costs more than one answered before it.
**Tested how:** read the list back in place; the steps are numbered 1 to 8 with no gap.
**Result:** the step is in the plan.
**Still broken / not tested:** nothing was sorted or answered in this change; the list of open questions is as long as before.

## 2026-10-14 Saves, part 1: where a save lives and what is in it

**Changed:** new `docs/save-format.md`; new reference script `scripts/reference/savefile.py`; new checks `scripts/checks/save_check.py` and `scripts/checks/save_night_check.py` (both listed in `scripts/checks/README.md`, where a broken row for `compare_with_log.py` was also repaired: `scripts\reference` had been split by a stray line break); `docs/PROGRESS.md`. Machine-only (gitignored): `decompiled/saves.c`, `saves_facts.c`, `saves_maputil.c` and their `.clean.c` files; the real save folder `extracted/saverun/`.
**Why:** step 3 of the plan, split in two with the user's agreement. Part 1: how a save is stored, its format and what it holds. The user chose to produce a real save by playing (option B).
**Tested how:** decompiled 150 + 53 + 20 functions (selectors: `play.EncryptedStore`, `play.save.`, `play.StoryState`, `play.AlltimeStats`, `play.Settings`, `app.XXTea`, the six `UnityPlatformDisk` addresses; `data.FactSet`, `data.FactValue`; `app.MapUtil`) and read the ones listed at the top of the doc; read 5 number constants; recovered 5 dropped string arguments with `ListStringUses.java`. The user then launched the game with `savedir extracted\saverun` and played three days and nights into day 4 by hand. Ran `savefile.py`, `save_check.py` and `save_night_check.py` on that folder.
**Result:** every stored item is a `<name>.sav` text file of upper-case hex: `PPSAVE1` + the value, NUL-padded, XXTEA with a second key string (literal 3240, not written in the repo). `headers` is a tab-indented tree of `id;parentId;time;day;money;family` lines; `save_<id>` is the story facts as `<facts><f v= p=/>...`, nothing else. The story is saved in one place found so far: on advancing to the next day, after the day number goes up. On the real folder: 7 of 7 files decrypt and re-encrypt to the identical text; 3 of 3 headers match their save's day, money and family; the parent rule holds 3 of 3; `0 problems`. Side result: the night model reproduces each of the three nights with exactly one of 24, 56 and 288 possibilities (4, 6, 8 travelers paid, nothing bought), `0 problems`.
**Still broken / not tested:** one folder, one line of three saves: no branch, load, delete, `stash` or `platover` was exercised. The user has not yet confirmed from memory that nothing was bought on those nights. Part 2 (the stash, the rest of `Game.applyScreenChange`) is not read. The callers of delete and "read the tree" are in screens not decompiled yet. `play.AlltimeStats` was read only for its local file (`load`, `save`, `queSave`, `update`); the rest talks to the platform's achievements and leaderboards service and was left alone (rule 4), which the user was told. The fact order in a save was not compared with `haxemap.py`. The "children sorted by time" check is empty on this folder (no save has two children). The user said they played twice; this folder shows one playthrough, and where the other went is not known.
**Older docs corrected (the "keep older docs true" rule):** open notes answered in place: `art-dat-format.md` and `il2cpp-name-recovery.md` (what the encrypted store holds), `run-and-seeds.md` (the save format and `StoryState.load` are studied; the story seed's absence seen in real saves; what a real `names` entry looks like), `value-helpers.md` (where the saved date format is loaded, in two places), `traveler-build.md` (a real `names` entry), `night.md` (the order of a member's saved pairs, which was "not determined"; and "nothing here has been compared with the running game" replaced by what the three nights confirm and what they do not). No earlier statement was found to be wrong. `data-files.md` needed no change. Nothing was built on the notes that changed.

## 2026-10-14 The border scene, part 4: the view, the cameras, the endless scoreboard

**Changed:** new `docs/border-view.md`; `scripts/checks/border_events_check.py` gained a last section for it (its `README.md` row updated); one bullet in `docs/ghidra-workflow.md` (a function too big for the decompiler); `docs/PROGRESS.md`. Decompiled output (gitignored): `decompiled/border_view*.c`, `border_view*_log.txt`, `layout_ctor_asm_raw.txt`, `layout_ctor_asm.txt`.
**Why:** the last part of the border scene, plus the two layout values part 3 left open (hit box, slow-motion scale), which the user asked to include.
**Tested how:** read `BorderPan`, `Border.panToPeople` and its five callers, `KineticScroll`, `BorderCam`, the `BorderCamRenderer` constructor and `applyPalette`, `Booth.attachBorderCamsToBorder`, `EndlessScoreboard` (desktop branch of the constructor, `update`, the message handler), `FlashingScore`, `app.Clock`, and the senders in `Endless`; read machine instructions for the `Layout` constructor, the two bike-scene offsets and the total-score value; read 30 number constants; ran the extended check and re-ran `border_figures_check.py` and `paths_check.py`.
**Result:** the game has three layouts, and on the desktop one the scene (570 wide) fits the window (570 wide), so the view cannot move; the camera screens are created only when the layout has rectangles for them, which only the tablet layout does; the sniping time scale is 1.0 on desktop (0.9 tablet, 0.8 phone). Desktop hit box: 8 x 18. The bike-scene view offsets are 50 and 40. The scoreboard is three texts fed by three messages, each flashing 7 times in 2 s. The game's frame time is real elapsed time capped at 0.1 s; the test player fixes it at 1/20 s. All three checks print `problems: none`.
**Still broken / not tested:** nothing compared with the running game; the "desktop has no panning, cameras or slow motion" finding rests on the code's layout values. The decompiler failed on the `Layout` constructor (timeout at 120 s), so it was read as instructions and only for the fields needed. Skimmed only: `BorderCamVisual.buildTiles`, the phone branch of the scoreboard. Two math helpers (sine, remainder) are identified from how they are called. `StringUtil.formatTime`'s arithmetic was dropped by the decompiler and not checked in the instructions. Mistake made and caught during the step: two shell searches used a function name containing `$$` in Git Bash, which silently matched nothing and printed the wrong function; the name was then found with the search tool instead.
**Older docs corrected (the "keep older docs true" rule):** two statements were wrong or missing a condition and are marked as corrected: `rand.md` ("`BorderCam` is created twice per day": only on the tablet layout) and `border-shooting.md` ("two clocks are needed during an attack": only on phone and tablet), plus the port note in `border-figures.md` ("plus one generator per camera"). Open notes answered in place: `border-shooting.md` (slow-motion scale, hit box, `app.Clock`), `border-figures.md` (hit box size, whether `dt` varies, the camera generators), `border-scene.md` (construction step 9, the sniping time scale in two places, `pan-right`, the part 4 list with the two offsets), `borderanim-xml-format.md` and `data-files.md` (cameras and panning now studied), `endless-mode.md` (the scoreboard display). Nothing built on the wrong statements: no reference script or check models cameras, slow motion or a second clock.

## 2026-10-14 New rule in CLAUDE.md: keep older docs true

**Changed:** `CLAUDE.md` only. A new bullet under "How to work", after "One thing at a time": when a step answers an older "not studied / not checked / unknown" note, or shows an earlier finding, inference or guess was wrong, fix that sentence in the same step, mark a wrong statement as corrected with the date, and check what was built on it. The "When to update" cell for `docs/<topic>.md` in the file table says the same in short.
**Why:** the doc sweep (entry below) found 36 out-of-date notes because older docs were not revisited. The user approved the rule and asked for it to cover earlier statements that turned out wrong as well.
**Tested how:** read both edits back in place.
**Result:** the bullet sits between "One thing at a time" and "Running the original game needs my go-ahead"; the table row is updated.
**Still broken / not tested:** whether later steps follow the rule can only be seen in later steps; not tested. The sweep did not look for earlier statements that are wrong, only for notes answered later, so that half of the rule has not been applied to the existing docs.

## 2026-10-14 The border scene, part 3: shooting

**Changed:** new `docs/border-shooting.md`; `scripts/checks/border_events_check.py` gained a shooting section (its `README.md` row updated); pointers updated in `docs/border-scene.md` and `docs/border-figures.md`; `docs/PROGRESS.md`. Decompiled output (gitignored): `decompiled/border_shoot.short.c`, `shoot_misc*.c`, `shoot_asm.txt`, `ent*.c`.
**Why:** part 3 of the border scene: what a shot does, how the day's attack result is decided, the rifle buttons and keys, the grenade's flight, and which clock the delayed calls use (left open in part 2).
**Tested how:** read `Border.snipe`, `checkSniped`, `react` and the test player's aiming helpers, `RifleButton`, `Grenade`, `Day.setAttackResultWithPriority`, `ArrayUtil.makeShuffled`, the delayed-call classes and the part of `Trunk.treeUpdate` that steps them; read machine instructions for the unlocking time; read 5 number constants; ran the extended check and re-ran `border_figures_check.py` and `paths_check.py`.
**Result:** a shot hits every figure whose box contains the point; a hit figure gets a path with a death animation, so it counts as dead with either rifle. The attack result is one "worst so far" value in a fixed order of seven, and three of them lead to the six shooting endings. Delayed calls run on the game's clock, the scene's state times on the slowed scene clock. `BulletHoles.png` is 32 x 8, matching the four 8 x 8 pieces read from the code. All three checks print `problems: none`.
**Still broken / not tested:** nothing compared with the running game. Two layout values were not looked up (hit box size, slow-motion scale). What the night does with "solved" and "failed", and what the key paper does after unlocking, were not followed. The cameras and panning (part 4) are not read.
**Older docs corrected (the "keep older docs true" rule, for parts 2 and 3):** `days-csv-format.md` (which guard each `GUARDS` character puts on duty; the "not studied" line on features and guard flags), `traveler-build.md` (`leaveDir` is now known), `borderanim-xml-format.md` (how figures are created; what is still unread), `data-files.md` (the `BorderAnim.xml` row), `run-and-seeds.md` (`makeFromState` has been read), `border-figures.md` and `border-scene.md` (pointers to part 3; the delayed-call clock, which part 2 listed as unknown). No earlier statement was found to be wrong. The check gained one cross-check from this search: the four `leaveDir` values in `Travelers.txt`, one of which (`right-police`) is used as a path name, as the code reading predicted.

## 2026-10-14 Doc sweep: out-of-date "not studied" notes corrected

**Changed:** 36 small text fixes in 18 docs: `il2cpp-name-recovery.md`, `art-dat-format.md`, `data-files.md`, `errors-txt-format.md`, `run-and-seeds.md`, `comparing-with-the-game.md`, `nights-txt-format.md`, `traveler-build.md`, `traveler-creation.md`, `days-csv-format.md`, `travelers-txt-format.md`, `papers-xml-format.md`, `languages-list.md`, `borderanim-xml-format.md`, `rand.md`, `speech.md`, `fact-values.md`, `tab-tree-format.md`. Each replaces a "not studied / not checked / not compared" note with what is now known and the doc that holds it. The small-jobs bullet in `docs/PROGRESS.md` now says what was left alone. No findings were added; no code or script changed.
**Why:** the user asked for it after the XXTEA line (entry below) showed older docs were not being revisited.
**Tested how:** before each fix, read the passage and the later doc that answers it (for example `night.md` for the `Family` constructor, `comparing-with-the-game.md` for what the runs confirm). Afterwards searched `docs/` for the phrases that had been targeted and listed the changed files with `git diff --stat`.
**Result:** the targeted phrases are gone except one that is still true (`run-and-seeds.md`: the display options are not studied). 20 files changed including this one, all documentation.
**Still broken / not tested:** "compared with the running game" was only changed where `comparing-with-the-game.md` names the topic (seed chain, script reading, the person, document values, error picks, spoken lines), and the new wording says the evidence is indirect: one seed, days 1 to 4, through draw counts. The same line was left in `papers-on-desk.md`, `operations-and-fact-validity.md`, `value-helpers.md` and `haxe-maps.md` because the records do not say which parts the runs exercised. The docs were not re-read in full, so a confident statement that is wrong would not have been found.

## 2026-10-14 Out-of-date XXTEA line corrected in il2cpp-name-recovery.md

**Changed:** one bullet in `docs/il2cpp-name-recovery.md` ("Findings about the game"): it said where XXTEA is used was unknown. It now names the two known uses and says a search for other callers has not been run. One bullet added to "Small jobs" in `docs/PROGRESS.md` listing the other docs where out-of-date statements were found.
**Why:** the user asked where XXTEA is used; the line was written on 2026-10-12 before `Art.dat` was decrypted and never revisited.
**Tested how:** read the bullet back; checked both uses against `docs/art-dat-format.md`. To look for more of the same, searched `docs/` for "not studied", "not checked", "unknown" and similar (about 200 hits) and cross-checked the ones a later doc might have answered.
**Result:** the bullet matches `art-dat-format.md`. The search found roughly 28 more out-of-date statements in 12 other docs; none were changed in this step.
**Still broken / not tested:** the other out-of-date statements are still there. The search only finds "not known" notes that were answered later; it cannot find a confident statement that is wrong. Not every doc was read in full. The earlier entry "PROGRESS.md brought up to date" says the stale "not compared with the game" statements were removed from `errors-txt-format.md`; one is still in its "Not studied" list.

## 2026-10-14 The border scene, part 2: Border itself

**Changed:** new `docs/border-scene.md`; new check `scripts/checks/border_events_check.py` (listed in `scripts/checks/README.md`); new reading aid `scripts/ghidra/condense_decompile.py` (described in `docs/ghidra-workflow.md`); pointers updated in `docs/border-figures.md`, `docs/paths-xml-format.md` and `docs/data-files.md`; `docs/PROGRESS.md`. Decompiled output (gitignored): `decompiled/border.short.c`, `stater*.c`, `booth_border_calls.short.c`, `border_ctor_asm.txt`, `border_ctor_strings.txt`.
**Why:** part 2 of the border scene: what runs it. Which figures exist, the state machine, what each path event does, the attacks, how the day ends there, and whether anything that matters to play uses the border generator.
**Tested how:** read the `Border` constructor and every `Border` function outside shooting and panning, all its callbacks, the state machine classes and seven `Booth` methods it calls, using the condensed view (8,479 lines down to 4,327); read machine instructions for the constructor's end, the attack delay and the announcement text; read 23 number constants; ran the new check, and re-ran `border_figures_check.py` and `paths_check.py`.
**Result:** `Border` is a 12-state machine plus about two dozen event handlers; the choreography is in `Paths.xml`. All 76 path names in the code exist in the data, all 36 event texts in the data are handled, and every event name the code tests for is sent by some path. An attack starts `6 + 4 x r` seconds after the first unscripted traveler steps in, drawn from the border generator, so attack timing cannot be reproduced from the seed. A day with an attack has no time limit. Saving the scene stores only the pan position. All three checks print `problems: none`.
**Still broken / not tested:** nothing compared with the running game. Shooting (part 3) and the cameras (part 4) are not read. The "tweener" behind the delayed calls was not read, so whether those delays follow the slowed scene clock is unknown. One finding is from code only and looks odd: a truck attacker skipping his throw animation in one case.

## 2026-10-14 The border scene, part 1: figures and the waiting line

**Changed:** new `docs/border-figures.md`; new check `scripts/checks/border_figures_check.py` (listed in `scripts/checks/README.md`); `docs/paths-xml-format.md` (the attribute meanings that were guesses are replaced by what the code does, with a pointer to the new doc); `docs/rand.md` (the cameras' seeds); one line of `docs/data-files.md`; `docs/PROGRESS.md` (the comparison run marked as postponed by the user, the border scene split into four parts, open questions). Decompiled output (gitignored): `decompiled/border*.c`, `border_callers*.c`, `border_misc*.c`, `border_waitingline_asm.txt`, `border_misc_log.txt`.
**Why:** the user postponed the longer comparison run, so the next step is the border scene. Part 1 answers how a figure follows a path over time and which random generator the scene uses.
**Tested how:** decompiled all 314 `play.day.border` functions and listed every generator use in them; read `Person`, `WaitingLine` and `CustomTile` in full, plus the callers needed (`Border.update`, `addPerson`, the `DayScreen` constructor); read the machine instructions of five `WaitingLine` functions and `CustomTile.stepAnim` where the decompiler dropped values; read 20 number constants from the DLL; ran the new check and re-ran `paths_check.py`.
**Result:** the scene uses the day's `borderRand` (day seed + 0x2000), one shared generator for `Border`, the line and every figure; the two cameras have their own (day seed + 1 and + 2). `hold` is a timer from the moment the path is set, not a wait after arriving (the earlier guess was wrong); `warp`, `snap`, `delay`, `face` and the `die` event are now read from the code. The queue is a ring of the same figures; building a line of 100 costs 1,500 draws. `border_figures_check.py` prints `problems: none`; `paths_check.py` still prints `problems: none`.
**Still broken / not tested:** nothing was compared with the running game. No reference script models the frame-by-frame movement. `Border` itself (events, guards, attacks), sniping and the cameras are not read. Open items are listed at the end of `border-figures.md`.

## 2026-10-14 "Next:" line removed from the MODLOG template

**Changed:** the entry template at the top of `MODLOG.md` no longer has a `**Next:**` line. Older entries keep theirs.
**Why:** next steps now live only in `docs/PROGRESS.md`, so they are not written in two places.
**Tested how:** read the template back after the edit; searched the file for `**Next:**`.
**Result:** the template has six fields; `**Next:**` remains only in entries dated before this one.
**Still broken / not tested:** nothing to test; documentation only.

## 2026-10-14 The newspaper picture

**Changed:** new `docs/newspaper-picture.md`; new reference script `scripts/reference/newsimage.py` and check `scripts/checks/newsimage_check.py` (listed in `scripts/checks/README.md`); `docs/news-txt-format.md` now points to the new doc and states the main-headline answer; `docs/PROGRESS.md` updated. Decompiled output (gitignored): `decompiled/newsimage*.c`, `newsscreen*.c`, `imgtransformed*.c`, `asm_newsimage.txt`.
**Why:** step 1 of the next-steps list: how the newspaper is drawn, whether the first article is the main headline, and which random generator it uses.
**Tested how:** read `DayNewsImage.make`, `LayoutImage` and `NewsScreen` in full; read three dropped arguments from the raw instructions; read 15 number constants from the DLL; ran `newsimage_check.py` on the 12 layout pictures and on 200 master seeds x 31 days; re-ran `news_check.py`.
**Result:** article `i` goes into layout rectangle `i` (red, green, blue, yellow, magenta) and red is the single largest in all 12 layouts, so the first article is the main headline. The picture uses `day.newsRand`, the same generator as the headline choice, and draws about 190 more times (179 to 204 word marks plus one, then 3 per stamp and 3 per face picture). Both checks print `problems: none`.
**Still broken / not tested:** nothing compared with the running game. Text fitting is not modelled (needs `app.vis.Text`), so which titles fall back to the regular font is unknown. The stamp angle looks like `r * 60 - 30` used as radians; the two maths calls were not identified. `newsRand` users were searched only in the decompiled files on disk.
**Next:** step 1 of `PROGRESS.md` (a longer comparison run, needs the go-ahead) or step 2 (the border scene).

## 2026-10-14 Rules gathered into CLAUDE.md; STATUS.md folded into the topic docs

**Changed:** `CLAUDE.md` gained the rules that were spread elsewhere (plan first, the model note at session start, `PROGRESS.md` updated every step, correct over fast, thin evidence, go-ahead for each game launch, file tools over here-documents), a table of what each file is for, and a changed "two attempts" rule (stuck report goes in the step's doc, with a "Currently stuck" entry in `PROGRESS.md`). `docs/PROGRESS.md`: "Working agreements" removed, "Currently stuck" added, opening paragraph corrected. `STATUS.md` deleted: its REA record moved to the end of `docs/ghidra-workflow.md`, its booth random-number record to the end of `docs/comparing-with-the-game.md`. `docs/ghidra-workflow.md` gained two habits that were working agreements. Mentions of `STATUS.md` fixed in `docs/desk-drawing-draws.md` and the files above. Outside the repo: Claude's four memory notes for this project deleted and their index emptied.
**Why:** the same rules were written in three places (`CLAUDE.md`, `PROGRESS.md`, memory notes) and already disagreed about when `PROGRESS.md` is updated; `STATUS.md` no longer matched its original template. Now each kind of information has one home.
**Tested how:** compared every line of the committed `STATUS.md` records with the two topic docs by script; searched the project for remaining mentions of `STATUS.md`; checked each of the ten former working agreements has a home.
**Result:** 106 and 24 lines checked, all found word for word except the two references changed on purpose. `STATUS.md` is now named only in older `MODLOG.md` entries, which are history and were left alone. Documentation only; no code changed.
**Still broken / not tested:** whether a new session follows the new opening routine (model note, then a plan) can only be seen in a new session; not tested.
**Next:** the newspaper picture (step 1 of the list in `PROGRESS.md`).

## 2026-10-14 PROGRESS.md brought up to date

**Changed:** rewrote `docs/PROGRESS.md` for the end of the fourth session (state, doc list, next steps, open questions, verification method, machine-only files, working agreements); `docs/ghidra-workflow.md` gained the two newer helper scripts and two working habits; removed stale "not compared with the game" statements from `docs/comparing-with-the-game.md` and `docs/errors-txt-format.md`.
**Why:** the user asked, before starting a new session.
**Tested how:** checked the file against `MODLOG.md`, the list of docs and scripts on disk, and the data folder's file count (31).
**Result:** documentation only; no code changed.
**Still broken / not tested:** the percentage estimates are rough guesses.
**Next:** the newspaper picture (step 1 of the list in `PROGRESS.md`).

## 2026-10-14 The three unread data files looked at (Threads.txt, TravelerGraph.txt, Version.txt)

**Changed:** added `docs/unused-data-files.md` and `scripts/checks/notes_files_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** to close the list of data files: every file in the data folder now has a write-up.
**Tested how:** searched the code's strings for the names and for any way to build a data file name from parts; counted how the files' contents match `Travelers.txt` and `News.txt`.
**Result:** none of the three is loaded: data files are always asked for by one of 30 whole names, and these are not among them. `Version.txt` holds `1.4.11.124`; `Threads.txt` is an outline of the story (all 35 of its `@` names are news articles); `TravelerGraph.txt` describes response flows.
**Still broken / not tested:** not tested by running the game without the files. The meaning of the marks in the two note files is inferred from their content.
**Next:** all data files are written up. The user's choice of what follows.

## 2026-10-14 The test-tooling files studied (TestScenarios.xml, Auto.txt)

**Changed:** added `docs/test-tooling-files.md` and `scripts/checks/testfiles_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data files. `Auto.txt` is a recipe for reaching every ending, useful later as a test plan for the port.
**Tested how:** read the `TestScenarioLib` and `TestScenario` constructors in full and the route loaders in part; ran `testfiles_check.py`.
**Result:** 12 test scenarios (start at a day, a night or a traveler, with saved facts set first); 33 test routes (21 story, 12 endless); every ending in `Ends.xml` has a route; all bases exist. Check prints `problems: none`. One scenario names a traveler `BOSS` that does not exist in `Travelers.txt`.
**Still broken / not tested:** what starts a scenario; the order in which instruction blocks are consulted; how each action word is carried out. Only routes 1 and 20 have ever been run.
**Next:** the three files nothing asks for by name (`Threads.txt`, `TravelerGraph.txt`, `Version.txt`).

## 2026-10-14 Languages.txt and Languages.png studied

**Changed:** added `docs/languages-list.md` and `scripts/checks/languages_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data files.
**Tested how:** read the parts of `play.screen.LangChooser` that use the files; ran `languages_check.py` (it also lists the names of the language packs in the project's copy of the game; nothing was opened or changed there).
**Result:** 16 codes, one per line, split at line feeds and not trimmed; the picture is 16 rows of 110x20, one name per code in the same order; the 16 language packs match the codes exactly. Check prints `problems: none`.
**Still broken / not tested:** the chooser screen, where user-added languages come from, and loading a language pack are not studied. Nothing compared with the running game.
**Next:** the test tooling files (`TestScenarios.xml`, `Auto.txt`), then the three files nothing asks for by name.

## 2026-10-14 Credits.txt studied

**Changed:** added `docs/credits-txt-format.md` and `scripts/checks/credits_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data file.
**Tested how:** read `play.screen.CreditList` in full; ran `credits_check.py`.
**Result:** an indented tree; the first word of a line picks its kind (`+` role, `/` team, `-` small, `$` finale, `[SPACE]`, `[OFFSCREEN]`, `[IMAGE] file`, `? have-lang-xx` condition, otherwise a name); 113 lines with all languages, 109 with English only; all three pictures exist. Check prints `problems: none`.
**Still broken / not tested:** who shows and scrolls the list; the exact code test for dropping a marker word was scrambled (the result is clear). Nothing compared with the running game.
**Next:** `Languages.txt` and `Languages.png`.

## 2026-10-14 BorderAnim.xml studied

**Changed:** added `docs/borderanim-xml-format.md` and `scripts/checks/borderanim_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data file (the pictures of the figures in the top view).
**Tested how:** read `AtlasLib.make`, `app.vis.Atlas`, `border.Person.setAnim` and part of `border.CustomTile`; ran `borderanim_check.py` against the file, its sheet and `Paths.xml`.
**Result:** a picture atlas of 247 rectangles on a 512x732 sheet, none overlapping or outside; frames are grouped purely by "name starts with prefix, in file order"; all 37 animation suffixes of `Paths.xml` have pictures; five prefixes also collect another group's frames (for example `Guard0-Idle` and `Guard0-IdleB`). Check prints `problems: none`.
**Still broken / not tested:** whether the five prefix clashes are visible in the game; the end of a non-looping animation; the border scene itself. Nothing compared with the running game.
**Next:** `Credits.txt`.

## 2026-10-14 Paths.xml studied

**Changed:** added `docs/paths-xml-format.md`, `scripts/reference/paths.py`, `scripts/checks/paths_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data file (the movement of the figures in the top view).
**Tested how:** read `data.PathLib`, `data.Path`, `data.Anim` and `XmlUtil.getNextSibling`; ran `paths_check.py`.
**Result:** 39 animations and 309 paths (118 unnamed, reached through `next="NEXT"`); every attribute in the file is read by the code; all `next` targets, animation names and sound ids exist; a point's `randomize` costs two draws from whatever generator the caller passes. Check prints `problems: none`.
**Still broken / not tested:** the number in the automatic `auto-<number>` ids was not recovered (nothing refers to them). How the border scene follows paths, and what the 36 events do, is not studied. Nothing compared with the running game.
**Next:** `BorderAnim.xml`.

## 2026-10-14 Fonts.xml and the font files studied

**Changed:** added `docs/fonts.md`, `scripts/reference/fonts.py` (loads the fonts, measures and breaks text), `scripts/checks/fonts_check.py`; `docs/data-files.md` and the checks README updated.
**Why:** next unstudied data file; the port needs the font measurements to lay out documents.
**Tested how:** read `data.FontLib`, `data.FontDef` and `app.vis.Font`; ran `fonts_check.py` on the extracted files.
**Result:** 16 fonts over 12 font files, all present, one sheet each; the game files letters by the `letter` attribute, ignores the file's own line height and has no kerning; with this data `letter` and `id` agree everywhere. Check prints `problems: none`.
**Still broken / not tested:** nothing compared with the running game. The order of steps in line breaking was reconstructed from scrambled decompiler output; edge cases not tested. Drawing text and language-pack fonts not studied.
**Next:** `Paths.xml`.

## 2026-10-14 Booth random numbers now match the game: drawing papers on the desk draws too

**Changed:** added `scripts/reference/desk.py` (the draws made when a paper gets its picture: tilt, photo, position ranges, seals) and `docs/desk-drawing-draws.md`; `scripts/checks/compare_with_log.py` now replays desk draws and spoken lines by default (`--no-desk`, `--no-speech` to leave one out) and applies the log's add-paper, remove-paper and validate lines; `STATUS.md` entry marked resolved; `docs/comparing-with-the-game.md`, `docs/emblems-and-bodies.md`, `docs/traveler-creation.md`, `scripts/checks/README.md` updated.
**Why:** the reference's error picks differed from the game's from day 4 (open problem in `STATUS.md`).
**Tested how:** decompiled all 1,433 booth-class functions and listed every use of a generator; read the paper constructor, the page-drawing code and `getImage`; then ran `compare_with_log.py` on both saved logs (no new game run), with each part left out as a control, and with 0 to 5 start-of-day draws in an experiment script.
**Result:** route 20, days 1 to 4: 36 of 36 travelers match on every field including errors (was 34); route 1: 8 of 8. Without desk draws 30 of 36, without speech 32 of 36; only 3 start-of-day draws (as the code says) gives 36.
**Still broken / not tested:** pages drawn again when turned (the bulletin's criminal photos would draw each visit); fingerprint, thumbprint and contraband pictures; the identity record; a hidden paper shown later; the invalid seal. `booth_check.py` was not re-run (it does not use `desk.py`, and `booth.py` was not changed). Evidence is one seed, days 1 to 4.
**Next:** the user's choice: a longer run (later days, another seed) to test the untested parts, or go back to the remaining data files.

## 2026-10-13 The test player's capture setting: ruled out by reading

**Changed:** `STATUS.md` (attempt 4 recorded).
**Why:** to see whether frame capture could give pictures of documents where the audit could not.
**Tested how:** read `test.auto.CaptureWorker` and decompiled `app.FrameRecorder`. The game was not run.
**Result:** capture pipes frames to `/usr/local/bin/ffmpeg` and writes `/Users/pope/Projects/Please/Temp/capture.mov`, fixed paths from the developer's Mac, and uses the same software renderer that produced the empty audit picture. Not usable here without creating files and installing a program outside the project. Not run.
**Still broken / not tested:** the booth generator problem in `STATUS.md` is unchanged.
**Next:** the user's choice: reason from the code, a debugger, or park the problem.

## 2026-10-13 Test player's audit pictures tried: unusable in this build

**Changed:** `STATUS.md` (third attempt recorded, idea removed from the untried list).
**Why:** to get faces and passport pictures for a known seed, as direct evidence of where the reference and the game part ways.
**Tested how:** decompiled the whole test player (682 functions) and read where it adds face and paper pictures and where it saves them; ran route 1, seed 12345, with `audits` / `face` / `paper Passport` and an existing `audits` folder; examined the saved file's pixels.
**Result:** a file `audits/1-in-debt.png` was written at the end of the route, sized for 8 faces, but it holds no pictures: mostly transparent, thin vertical lines and stray coloured dots. No passport pictures were added. Dead end as it stands.
**Still broken / not tested:** the booth generator problem in `STATUS.md` is unchanged. Why the audit picture is empty was not investigated; the `capture` option was not tried.
**Next:** the user's choice among the remaining ideas in `STATUS.md` (reason from the code; more runs; a debugger), or park the problem.

## 2026-10-13 Booth random numbers out of step with the game: two attempts failed, STATUS.md written

**Changed:** added `scripts/reference/speech.py` (stock-line lookup with its draws); `compare_with_log.py` gained `--speech` (replay the lines the game spoke); wrote the open problem into `STATUS.md`; corrected `docs/comparing-with-the-game.md`.
**Why:** to explain why the error picked on day 4 differs from the game's.
**Tested how:** compared the reference's error candidates with the game's for day 4; re-read `getSpeech` and its random pick; replayed the game's spoken lines; searched simple offsets and single dropped draws; counted how many candidates each logged pick had.
**Result:** the candidate lists match the game's exactly, so the reference is at a different position in the booth's generator. Spoken stock lines do draw from that generator (confirmed in the code), but replaying them does not fix the picks, and no simple offset does. **Correction:** the earlier statement that days 2 and 3 confirm the booth's draw counts was wrong; those picks had one or two real options each, so matching them is weak evidence. Who comes, with which papers and always-errors, still matches for all 36 travelers.
**Still broken / not tested:** the booth generator's position relative to the game is unexplained. The log prints no value that depends on it directly. `--speech` is experimental and off by default.
**Next:** see "Ideas not tried yet" in `STATUS.md`; the most promising is getting faces or document pictures out of the test player's audits.

## 2026-10-13 Second comparison run: days 1 to 3 match fully, day 4 shows the first difference

**Changed:** recorded the run in `docs/comparing-with-the-game.md`.
**Why:** day 1 has no random errors; a longer route tests the booth's random numbers.
**Tested how:** ran the project's copy of the game with the plan set to route 20, seed 12345, `trace`; stopped it by hand during day 4 at the user's suggestion; ran `compare_with_log.py` on the copied log.
**Result:** 35 travelers. Entry, nationality, duration, purpose and papers match 35 of 35. On days 1 to 3 every field matches for all 29 travelers, including all random errors. On day 4 the error differs for 2 of 6 travelers, starting at the second, right after the game first used the stock intro lines `$ask-purpose` / `$state-purpose`.
**Still broken / not tested:** the day-4 difference is not explained. Likely the speech lines or other booth actions draw from the booth's generator, which the reference does not model; not confirmed. Names, faces, id numbers and document values are still not compared.
**Next:** find what draws from the booth's generator between travelers (speech first), add it to the reference, and re-run the comparison on the same log.

## 2026-10-13 First comparison with the running game: day 1 matches

**Changed:** added `scripts/checks/compare_with_log.py`; recorded the run in `docs/comparing-with-the-game.md`; corrected `docs/run-and-seeds.md` and a comment in `scripts/reference/seeds.py` (a new game plays with the second story seed).
**Why:** first test of the reference against the real game instead of against the data files.
**Tested how:** with the user's go-ahead, ran the project's copy of the game once with `savedir extracted\\autorun` and an `auto.plan` of route 1, seed 12345, `trace`; copied Unity's `Player.log` into the gitignored `extracted/autorun/`; ran `compare_with_log.py` on it.
**Result:** the test player works in the released build and finished route 1 in 1 minute 27 seconds (`in-debt`, 8 travelers on day 1). All 8 travelers match the reference on entry, nationality, duration, purpose, papers and errors. Failure on the way: the first comparison matched only 4 of 8; a search over 20,160 variations of the draw rules explained nothing; the cause was the story seed (a new game draws a fresh one, so play uses the second), after which 8 of 8 match.
**Still broken / not tested:** random errors, the booth generator's draws (names, faces, id numbers, document values) and later days are not yet compared: day 1 has no random errors and the log does not print names or values. `booth.py` and `news.py` still take the first story seed when run as scripts; only the comparison script uses the second.
**Next:** a longer route (for example route 20, all 31 days) to compare error choices day by day; make the reference scripts' own demonstrations use the new-game story seed.

## 2026-10-13 What the game's test player does, and a prepared first run (no launch)

**Changed:** extended `docs/comparing-with-the-game.md`; created the gitignored `extracted/autorun/auto.plan` (route 1, seed 12345, trace).
**Why:** to be sure a test-player run is safe and to know what its log will contain before asking to launch.
**Tested how:** read `Auto.txt`; decompiled and read the rest of the `AutoGame` constructor, `AutoGame.log`, `autoReapplyRandomSeed`, `Traveler.getDescription` and the in-memory disk's save and load. The game was not run.
**Result:** the automated game keeps saves in memory only, replaces the online part with a blank object, and seeds itself exactly like `seeds.py` (first story seed). The log line per traveler gives entry id, nationality, purpose, duration, papers and error id; not name, face, id number or document values. `booth.py` predicts for seed 12345, day 1: `FINALLY_RETURN_HOME`, `SMALL_CHECKPOINT` (Impor, immigrate), `WAITED_FOREVER` (Republia, visit, 2 months).
**Still broken / not tested:** nothing run. Unknown: how long a route takes, where Unity's log lands, whether `-logFile` is accepted, how the automation's booth actions use the booth's random numbers, and what Unity itself touches outside the project at start-up.
**Next:** with the user's go-ahead, one launch of the project's copy of the game with `savedir extracted\\autorun`; then compare the log with the prediction.

## 2026-10-13 How to compare with the running game: reading step (no launch)

**Changed:** added `docs/comparing-with-the-game.md` and `scripts/ghidra/FindStaticWrites.java` (lists the memory writes that follow each use of a class record, to find who changes a class's static values); updated the debug-log section of `docs/run-and-seeds.md`.
**Why:** everything so far is checked only against the data files; this settles whether the game's own log can be used for a comparison.
**Tested how:** decompiled and read `Trace`, `AutoPlan`, the Unity save-folder set-up and log function, and the relevant parts of `Game.applyScreenChange`, `HostUnity.CreateGame` and the `AutoGame` constructor; ran the new search over all 423 uses of the `Trace` class. The game was not run.
**Result:** the detailed log (`showVerbose`) is turned on in exactly three places, all belonging to the test automation; the command-line word `trace` alone cannot do it. The automation starts when a valid `auto.plan` file exists in the save folder; the plan can set the master seed (`seed <n>`) and the log (`trace`); the save folder can be pointed anywhere with the command-line word `savedir`. Log lines go to Unity's `Debug.Log`. Failure on the way: one decompile request by name matched nothing (the name needed its address).
**Still broken / not tested:** nothing was run, so none of this is tested. Not read: what the automation actually does (`Auto.txt`, `AutoGame`'s play, `auto.log`, its leaderboard and stash steps), what the detailed lines contain, where `Player.log` lands.
**Next:** read the automation enough to be sure it is safe and offline, then ask for the go-ahead for one launch with `savedir` inside the project.

## 2026-10-13 Endless mode: Endlesses.xml and Endless.csv (remaining data files, seventh)

**Changed:** added `docs/endless-mode.md` and `scripts/checks/endless_check.py`; updated `docs/data-files.md` and the checks README.
**Why:** next of the remaining data files; these are game rules rather than drawing.
**Tested how:** read both files; decompiled and read `EndlessLib`, `EndlessCourse`, `EndlessStyle`, `Action`, `ScoreScale` and `play.day.Endless`; read the dropped sign of the clock change from the raw instructions; ran `endless_check.py`, which models the scoring.
**Result:** `problems: none`. Three styles (timed, perfection, endurance) and four courses; the scoring model reproduces the styles' own descriptions (perfection 10 points falling to 1 over ten minutes; endurance citations costing 5, 10, 15, ...; timed losing 30 s per citation). `Endless.csv` uses the `Days.csv` format with four columns. Finding: the three style button pictures named in the file are not in the extracted assets.
**Still broken / not tested:** not compared with the running game. Not read: the endless screens, which booth events raise the three actions, how a run's seed is chosen, the unlock code check; whether the missing pictures are ever asked for.
**Next:** the last data files (`Paths.xml`, `Fonts.xml`, `BorderAnim.xml`), which are about what is drawn; or `PROGRESS.md` step 2 or 3.

## 2026-10-13 Emblems.xml and Bodies.xml (remaining data files, sixth)

**Changed:** added `docs/emblems-and-bodies.md` and `scripts/checks/emblems_bodies_check.py`; updated `docs/data-files.md` and the checks README.
**Why:** next of the remaining data files; both feed the documents and the body search.
**Tested how:** read both files; decompiled and read `EmblemLib` (constructor, `getEmblemImage`, its helpers) and `BodyLib` (all six functions); ran `emblems_bodies_check.py`, which measures the pictures and models the emblem pick and the contraband cut-out.
**Result:** `problems: none`. Findings: an emblem sheet's first `valid` cells are the genuine ones and the rest wrong ones, picked with one draw; `canrotate` in `Emblems.xml` is not read; a `contrabandTypes` value starting with `$` names a picture file (`$Gun0` is `Contra-Gun0.png`), which settles an open question; body `M1` has no offsets and uses `0 0`; all sheets divide evenly and no contraband cut-out leaves its picture.
**Still broken / not tested:** not compared with the running game. Not studied: composing the search photo, stamping emblems on documents, which generator those picks use, `getValidImage` in detail.
**Next:** the next data file (`Paths.xml`, `Fonts.xml`, `BorderAnim.xml`, the endless-mode files).

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
