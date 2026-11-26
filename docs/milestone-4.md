# Milestone 4: the booth, no travelers

Milestone 4 (`DESIGN.md`, "Milestones") is day 1's screen: the booth, the
desk and console, the border scene's still picture, dragging the rulebook,
docking, the stamp bar, the clock, their sounds and the ambient loops; since
2026-11-04 also the pause screen (milestone 3d folded in, the user's
decision). On 2026-11-04 the user chose to plan milestones 4 and 5 at once,
as "day 1 playable", and gave the go-ahead for this split (`PROGRESS.md`,
step 16):

| Part | What you can try | State |
|---|---|---|
| **4a** | The booth at the start of day 1 (`?page=day`): the opening card typing the date and falling away, the booth as its constructor builds it, the border's background and blinking booth button, the ambient sounds | **Built 2026-11-05** (below), tried by the user the same day |
| **4b** | The shutter switch and the pause screen (Escape, RESUME, the settings rows, MAIN MENU and its confirm box) | **Built 2026-11-26** (below), not yet tried by the user |
| 4c | The rulebook (docked, dragged, opened, its pages and links, back to its dock, its sounds) | Not started |
| 4d | The clock running, the stamp bar, stamping | Not started |
| 5a, 5b | Travelers (milestone 5) | Not started |

## 4a: How to try it

From the project folder:

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080/?page=day` and click "Click to start". You
should see:

1. **A black booth** under the border scene's picture, with **"November
   23rd, 1982" typing on** in the middle (a soft typing sound every third
   letter).
2. **About 6 seconds after the start**, a short sound (`booth-intro`) and
   **the black card falls down out of the booth in about a second**, with a
   small bounce near the bottom.
3. **The booth**: the closed shutter (grey slats) in the traveler's window
   with its switch in the top right corner; the counter below; the console
   at the bottom left with the date "82.11.23", "00" travelers and a small
   clock at 6:00 (minute hand up, hour hand down); the dark desk with "DRAG
   DOCUMENTS HERE" at its bottom; the edge of the stamp bar at the right.
4. **The booth button on the border scene** (the little booth above the
   window) **blinks** with a white ring, about one and a third times a
   second.
5. **Sound**: the border's ambient noise; by the code the booth's hum is
   also heard at full level (`audio-layer.md`, "one ambient plays at its
   full level at first"; not compared with the game).

Nothing takes clicks yet (4b): the shutter switch, the booth button and the
desk do nothing. No figures walk at the border (milestone 6). A reload starts
the day again.

## 4a: What was built

- `port/core/src/stater.rs`: the game's general state machine
  (`app.Stater`, `app.State`) and the curves `STEP`, `LINEAR` and
  `BOUNCEBACK` (`app.Interp`), as read in full for this step
  (`booth-screen.md`, "The state machine's rules"). Generic over the
  properties and functions of its owner. The screen-change fader
  (`fade.rs`, milestone 3b) keeps its own copy of the same rules.
- `port/core/src/gdate.rs`: the game's date type (Julian day, months from
  0), its text format and the long date (`Lang.formatVerboseDate`), ported
  from `scripts/reference/gdate.py`.
- `port/core/src/picture.rs`: `Affine` and `Picture::draw_affine`
  (`Image.draw`), for the console clock's hands.
- `port/core/src/day.rs`: `DayScreen` for 4a: the booth's pieces in their
  drawing order, its states `off`, `intro`, `empty`, the border's `off` and
  `ready-to-call`, the walk-in figure's distance (it starts the intro), the
  clocks' first-frame rule, the ambient loops.
- `port/core/src/reveal_text.rs`: a `visible` switch (the intro's leave
  function hides the card's text).
- `port/core/src/game.rs`: `GameScreen::Day`, `Game::new_day`; a screen's
  song is now optional (the day screen asks for none, so the music fades
  out).
- The host's `?page=day` (`port/web/src/main.rs`), the page's note
  (`port/www/index.html`).
- The start pack: the booth's 12 pictures, `CheckpointBack.png`,
  `OuterBooth.png`, and the texts `booth_dragdocs`, `date_verbose`,
  `month_1` to 12, `day_1` to 31 (`scripts/build_assets/build_pack.py`).
- `scripts/reference/boothscreen.py`: the Python reference, written from
  the code before the Rust.
- `port/core/tests/day.rs`, and `port/core/tests/common/mod.rs` (the small
  JSON reader moved out of `tests/intro.rs`, which now uses it too).
- The browser check's step 1h (`scripts/checks/web_offline_check.mjs`).

## 4a: Decisions (mine, reversible)

- **The test address `?page=day`** starts the game on day 1's screen, as
  `?page=intro` does for the intro (an instant screen change on the first
  frame). The original reaches the day from the day-1 newspaper (milestone
  6).
- **The walk-in figure is kept as a distance only**: its path
  (`enter-right`, 60 units at speed 10) decides when the booth's intro
  starts, but it is not drawn. All border figures come with milestone 6.
- **The game's own sub-clocks** (the booth's and the border's
  `app.Clock`) give 0 on their first update and the fixed step after; the
  original's give the real time between updates (`border-view.md`, "The
  game's clock"), which with the fixed step is the step.

## 4a: Checks

- `cargo test -p pp_core`: 95 unit tests (new: the curves, a blend, the
  dates), and every earlier comparison still identical.
- `tests/day.rs`: the game's first 520 frames on `?page=day` against
  `boothscreen.py`: every frame's booth and border states, whether the card
  shows and its exact y (floats compared exactly), the letters shown and
  the button's look; the frames the 10 sound starts fall on (`border-ambient`
  and `booth-ambient` on frame 1, `text-reveal` on 7 frames, `booth-intro`
  on 362); six pictures byte for byte (frames 40, 362, 382, 410, 433, 451):
  all identical. A deliberate fault (the bounce's 0.2 made 0.21) made it
  fail with 3,420 bytes different, as it should.
- The browser check (`node scripts/checks/web_offline_check.mjs 8080`,
  headless Edge), 1 run after one fix to the step itself (below): all steps
  passed; step 1h: the card with the whole date identical to the
  reference, the booth identical outside the blinking button, `booth-intro`
  started.
- A look in the app's browser pane: the card, then the booth with the
  button blinking.

## 4a: Measurements

- WebAssembly 26,514,780 bytes; start pack 2,076,617 bytes (56 files, about
  12 KB more than 3c).
- In the hidden headless page the booth appeared 60 s after the card was
  complete (the page runs slowly while hidden, as in 3b); in the pane, which
  was also not in front, about 40 s after the start.

## 4a: Findings (by the code; nothing compared with the game)

Written up in `booth-screen.md`; the ones that show on screen:

- **The opening card stays about 6 seconds**: the first border figure walks
  60 units at 10 units a second, and the booth's intro starts when it
  arrives (frame 362 at 60 frames a second: frame 1 moves nothing, because
  a new clock's first update gives no time).
- **The date sits 10 pixels higher than it would on one line**: a story
  day's title is the empty text, not missing, so the card's text is the
  date plus a line break, two lines high.
- **The weight readout never shows "---"**: the console is made with "---",
  but the booth's first update sets the weight to the empty text (no
  traveler), which differs from the never-set weight and so replaces it.
- **The card falls in 61 frames** (from 363 to 423), along
  `BOUNCEBACK(0.2, 1)`: down to the bottom at a third of the second, back up
  by 20% (about 43 pixels) at two thirds, down again at the end.

## 4a: Not tested

- **By the user, in detail.** The user tried 4a on 2026-11-05 and said
  "all good" (which browser, and whether the sounds were listened to, not
  recorded).
- Against the running game: everything is code reading.
- Firefox; Chrome by hand; a window in front at a real 60 frames a second.
- The ambient sounds by ear (their volumes are only the code's rules).
- Days other than 1 (the date, the features, the secret-police start).

## 4a: Dead ends and failures

- The browser check's new step failed on its first run with "canvas is
  1280 x 720, not 570 x 320": it read the canvas before the page had
  resized it. The step now waits through that, as the intro's step
  effectively did by waiting for the song first.
- Three of my own unit-test expectations were wrong at first (a bounce
  back of 10 instead of 20, a blend one frame shorter, a timer one frame
  earlier: the last two are float sums of 1/60 landing a hair short). The
  tests now state the real values; the code was not changed for them.

## 4b: The plan (2026-11-26, written before building)

**The split.** The old 4b (rulebook, shutter switch, pause screen) is cut
in two, because the rulebook alone needs a new reading (`BoothEnv`'s text
lookup for the day's rule texts, the page player on the desk) and the
other two are read already. So: **4b = the shutter switch and the pause
screen**, **4c = the rulebook**, **4d = the clock running, the stamp bar,
stamping** (the old 4c). My decision, recorded in `DESIGN.md`; milestone
5 is unchanged.

**What 4b builds** (read on 2026-11-26 in `decompiled/all/`: the whole
`Shutter` class, `Booth.shutterSwitch_onClick`,
`BoothEngine.closeShutter`, `app.Num.smootherstep` and its constants,
`Game.update`'s pause test, the five functions of `Game`'s `paused`
state, `app.Clock.pauseForOneFrame` and `update`, `GameTransition`'s
`setPause` and `fadeToMainMenu`, `applyTransition`'s `SET_PAUSE`, the
whole `PauseScreen`, the whole `Confirm`, `Frame.buildTiles`):

1. **The shutter switch.** Once the booth's intro has begun (the `off`
   state's leave function gives the booth's parts input back), a click on
   the switch toggles the shutter, unless the booth is `busy-with-border`
   (never in 4b). Opening: state `open`, `shutter-rise`, the switch's
   look `up`, `openT` to 1 over 1.0 s along `SMOOTHERSTEP(0, 1)`
   (6t^5 - 15t^4 + 10t^3; the constants 1, 6, 15, 10 read from the DLL).
   Closing: first `BoothEngine.closeShutter`, which does something only
   with a traveler (none in 4b), then state `closed`, `shutter-drop`, the
   look `down`, `openT` to 0 over 0.35 s along `BOUNCEBACK(0.1, 1)`. The
   strips and the shadow follow `set_openT` (`booth-screen.md`). Behind
   an open shutter with nobody there, by the code, nothing is drawn (the
   wall picture is made but never drawn, `booth-screen.md`), so the
   window shows the black under everything; not compared with the game.
2. **Escape pauses.** First thing in `Game.update`: if the screen can be
   paused (the day and the intro screens), Escape went down this frame
   and the game's state is `on`, Escape is masked until it is let go and
   the state goes to `paused`. Entering `paused`: the effects are paused
   (the song plays on), the pause screen is made, the current screen is
   hidden (switch 1: not updated, not drawn, no input), `button-drop`.
   Every frame of `paused`, from the first: the game clock is paused for
   the frame (`pauseForOneFrame`: no time passes for the rest of the
   frame). Leaving: effects resumed, the pause screen removed, the screen
   shown, `hover-up`. The booth's and the border's own clocks are not
   updated while hidden, so their first update after a pause gives the
   time since their last update, capped at 0.1 s (`app.Clock`'s
   `maxDeltaTime`); the port gives the paused time plus the step, capped.
3. **The pause screen** (desktop): the header "PAUSED"; the menu
   centred on y 270 with RESUME and MAIN MENU (**QUIT left out, the
   user's decision**: the code's own menu helper then places two buttons,
   tops 246 and 270); RESUME is the back button (Escape presses it on
   release); the settings list in its `Pause` form (Fullscreen, Nudity,
   Music, Sound), centred left to right and between the header's bottom
   and RESUME's top.
4. **MAIN MENU** opens the confirm box (`Confirm.show` with an empty
   message): a black cover at alpha 0.5 over the whole screen,
   `ConfirmBox.png` as a nine-slice frame (borders 10) 244 wide and 98
   high at (163, 111), a red MAIN MENU button at (220, 131) and CANCEL at
   (220, 170). The box blocks all input under it for the frame. CANCEL
   (or Escape, its back button) hides it; MAIN MENU freezes it and fades
   to the title (leaving `paused` first, which shows the day again under
   the fade; the day is lost, as in the original).
5. **Full screen's first Escape** (`DESIGN.md`): in Chrome and Edge the
   page asks the Keyboard Lock interface for Escape while in full screen,
   so Escape reaches the game and pauses without leaving full screen;
   holding Escape leaves it, as the browser shows. In other browsers
   (Firefox has no Keyboard Lock) the page passes the Escape it could not
   keep to the game as one press, so the first Escape both leaves full
   screen and pauses.

**Checks planned:** unit tests (the curve, the clock catch-up, the
pause's frames); a new Python reference `pausescreen.py` for the pause
screen and the confirm box, compared byte for byte; `boothscreen.py`
extended with a scripted run (a click on the switch, Escape, RESUME,
the switch again) compared frame by frame in `tests/day.rs`; the browser
check's new step 1i; a look in the app's pane.

## 4b: How to try it

From the project folder:

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080/?page=day` and click "Click to start".
Wait for the black card to fall away (about 6 seconds), then:

1. **Click the shutter switch** (the little lever at the top right of the
   traveler's window, above the counter). You hear a click and the shutter
   rolls up over about a second, smoothly, with its sound; the lever flips
   up. **The window behind it is black**: by the code nothing is drawn
   there while nobody stands in the booth (`booth-screen.md`; not compared
   with the game). Click again: the shutter drops in about a third of a
   second with a small bounce and its sound, and the lever flips down.
2. **Press Escape**: the pause screen, with a short sound. "PAUSED" at the
   top, the rows Fullscreen, Nudity, Music and Sound, and RESUME and MAIN
   MENU below. The booth's ambient sound stops; nothing moves under the
   pause. The rows work as on the settings screen.
3. **Press Escape again** (or click RESUME): back to the booth, with a
   short sound, and everything carries on where it was (a shutter caught
   half way finishes its move).
4. **Escape, then MAIN MENU**: a box with a red MAIN MENU and CANCEL over a
   darkened pause screen. **Escape or CANCEL** closes the box; the red
   MAIN MENU fades to the title (the day is lost, as in the original).
5. **In full screen** (the start screen's box, or Fullscreen on the pause
   screen): in Chrome and Edge, Escape pauses and the window stays in full
   screen; holding Escape leaves full screen, as the browser says at the
   top. In Firefox the first Escape leaves full screen and also pauses.

The intro (`?page=intro`) can be paused too. Nothing else on the day
screen takes clicks yet: the booth button on the border, the desk and the
stamp bar come with 4c, 4d and milestone 5. A reload starts the day again.

## 4b: What was built

- `port/core/src/day.rs`: the shutter (`Shutter`'s two states, `openT`,
  the strips and the shadow placed by it), the switch taking clicks from
  the intro on (`Booth.shutterSwitch_onClick`), the screen's `react`; its
  own clocks now give the time of the frames they missed, at most 0.1 s
  (`app.Clock`'s `maxDeltaTime`).
- `port/core/src/num.rs`, `stater.rs`: `smootherstep` and the curve
  `SMOOTHERSTEP`.
- `port/core/src/fade.rs`: the game's `paused` state (no target, no
  blend, no duration; enter, every frame and leave events).
- `port/core/src/game.rs`: the pause key first in the frame (Escape on a
  screen that can be paused, while `on`; the key masked until let go), the
  `paused` state's functions (effects paused, the pause screen made, the
  screen hidden, `button-drop`; the game clock held every frame; on
  leaving effects resumed, the screen shown, `hover-up`), the pause
  screen's update, input and drawing, RESUME and MAIN MENU.
- `port/core/src/pause.rs` (new): `PauseScreen` and `Confirm` with the
  nine-slice frame (`Frame.buildTiles`).
- `port/core/src/settings_screen.rs`: the settings list (`SettingsMenu`)
  taken out of the settings screen so both screens use it, with its two
  forms; the header, the standard button and the menu column as helpers.
  The settings screen is drawn exactly as before (its test still passes).
- `port/core/src/pages.rs`: a stretched picture piece (for the frame).
- `port/web/src/platform.rs`, `main.rs`; `port/www/index.html`: Escape in
  full screen (Keyboard Lock in Chrome and Edge, the lost Escape handed to
  the game elsewhere).
- `port/www/audio.js`: a sound started while its category is paused now
  plays (a correction, below).
- The start pack: `PushButtonRed.png`, `ConfirmBox.png` and the texts
  `menu_paused`, `menu_resume`, `menu_mainmenu`, `confirm_cancel`.
- `scripts/reference/pausescreen.py` (new); `boothscreen.py` extended
  with the shutter, the clocks' catch-up and an input script;
  `fontpage.py` draws a colour given as four floats.
- `port/core/tests/pause.rs` (new); `tests/day.rs` extended.
- The browser check's step 1i (`scripts/checks/web_offline_check.mjs`).

## 4b: Decisions (mine, reversible)

In `DESIGN.md`, "Decided by me": the split of the old 4b into 4b and 4c
(and the old 4c renamed 4d); the pause screen's two buttons placed by the
menu helper on y 270; Escape in full screen. Also:

- **The paused frames count for the booth's own clocks**: the port's
  sub-clocks add up the steps of the frames they were not updated in and
  give at most 0.1 s, as the original's real-time clocks do; the exact
  value after a long pause in the original is `(0.1 + t) − t` for its
  system time t, a hair off 0.1, which the port does not copy.
- **A new confirm box per MAIN MENU**, as the original (CANCEL forgets the
  box; the hidden old one draws nothing and takes no input, so the port
  drops it).

## 4b: Checks

- `cargo test -p pp_core` (with `CARGO_HOME` set to `.cargo-home`): 99
  unit tests (new: the curve, the nine-slice frame, the menu centre, the
  `paused` state's events), and every earlier comparison still identical
  (the settings screen after its rewrite, the intro, 4a's day start).
- `tests/day.rs` against `boothscreen.py`: **720 frames**, now with the
  reference's input script played as real presses (the switch clicked on
  frame 512 and let go on 515, Escape on 532, Escape again on 592 to 595,
  the switch again on 672 to 675): every frame's booth and border states,
  the card, the letters, the button's look, **the shutter's state and its
  openT (floats compared exactly), the switch's look, whether paused, the
  game clock, the booth's own clock** (which gains 0.1 s on frame 596, the
  first after the pause, while the game clock gains 1/60); the frames of
  **20 sound starts** (`shutter-rise`, `shutter-drop`, `button-down`,
  `button-up`, `button-drop`, `hover-up` among them); **nine pictures**
  byte for byte (three new: the shutter opening, open, closing): all
  identical. A deliberate fault (SMOOTHERSTEP's 6 made 6.01) made it fail,
  as it should.
- `tests/pause.rs` against `pausescreen.py`: the pause screen
  (`pause_a`) identical; then a game on day 1 driven by real presses:
  Escape pauses (state `paused`, effects paused, `button-drop`), letting
  go does not press RESUME, no game time passes; a click on MAIN MENU
  opens the confirm box, drawn identical to `pause_b`; Escape presses
  CANCEL (the box goes, still paused); MAIN MENU and the red MAIN MENU
  leave the pause (`hover-up`, effects resumed) and the title is built on
  the 70th frame after the click, as every faded screen change.
- The browser check (`node scripts/checks/web_offline_check.mjs 8080`,
  headless Edge): **passed in full on the fourth run** (5 minutes). Its
  new step 1i, on the day page step 1h leaves: Escape gave the pause
  screen, identical to `pause_a` but for the cursor; MAIN MENU the confirm
  box, identical to `pause_b` but for the cursor; Escape CANCEL (the pause
  screen again); Escape RESUME (the booth again, identical but for the
  blinking button and the cursor); a click on the switch the open shutter
  (identical to `shutter_open` but for the blinking button and around the
  switch and cursor); the sounds `button-down`, `button-up`, `hover-up`,
  `shutter-rise` started (`button-drop` checked on the pause). Every
  earlier step passed as before. The three failed runs were faults in the
  check, not the build ("Dead ends" below).
- A look in the app's browser pane (`?page=day`, a real mouse and keys,
  sound not heard): the card, then the booth; a click on the switch
  raised the shutter (the lever up, the window black); Escape showed the
  pause screen; MAIN MENU the confirm box over it; Escape closed the box,
  Escape again went back to the booth with the shutter still open; a
  click closed it. The tab was closed afterwards.

## 4b: Measurements

- WebAssembly 26,527,498 bytes (12,718 more than 4a); start pack
  2,077,310 bytes (58 files).

## 4b: Findings (by the code; nothing compared with the game)

- **The empty confirm box doubles its button gap**: with no message the
  buttons are 20 apart, not 10 (`screens.md` part 3, corrected).
- **The shutter keeps the game's time, the booth's clocks do not**: after
  a pause the booth's and the border's own clocks jump by up to 0.1 s
  (their real-time cap), while the shutter, the typing and the blink,
  which use the game's clock, carry on smoothly. The pause itself holds
  the game's clock from its first frame.
- **An open shutter with nobody there shows black** (`booth-screen.md`).
- **RESUME is not pressed by the Escape that paused**: the key is masked
  until let go; the next Escape presses it on release.

## 4b: Not tested

- **By the user.** Nothing of 4b was tried by the user yet.
- Against the running game: everything is code reading.
- **Keyboard Lock and the Firefox hand-over**: headless Edge cannot show
  full screen to the check, and I cannot press keys in a real full-screen
  window; both paths are written from the browsers' documentation only.
- Firefox; Chrome by hand; the sounds by ear.
- Pausing the intro (`?page=intro`): built by the same rule (it calls
  `enablePause`), not checked.
- The pause screen's rows by hand (they are the settings screen's, which
  were tried in 3b).

## 4b: Dead ends and failures

- Two shell here-documents broke on quotes while editing (as `CLAUDE.md`
  warns); the edits were redone with scripts written by the file tools.
- The first `pausescreen.py` drew the red button's text with no alpha
  byte (`0xCC2E2E`), so it was invisible; the reference now uses
  `0xFFCC2E2E` (the port forces button text opaque, so it was right).
- **The first browser run failed in step 1h** ("booth_normal: not
  reached, 3,315 bytes differ in [0,108,177,209]", the window): the
  reference's input script then clicked the switch on frame 422, before
  4a's snapshot `booth_normal` (frame 433), so that picture showed a
  half-open shutter while the browser, with nobody clicking, showed it
  closed. The script now starts 150 frames after the intro (the run is
  720 frames), and 4a's snapshots are on their 4a frames again. Not a
  fault in the build.
- **The second run failed in step 1i** after CANCEL ("pause_a: not
  reached, 243 bytes differ in [278,278,292,295]"): with the mouse over
  MAIN MENU the game draws its hand cursor, which sits further left than
  the arrow the check allowed for. The allowance is now wider.
- **The third run passed 1i and every step to 1c, then stopped in step 2**
  with "hung for 5 minutes": that is the check's own limit on the whole
  run, which step 1i's extra minute pushed past; raised to 10 minutes.
  The fourth run passed everything in 5 minutes.
- My first version of `tests/pause.rs` drew the pause screen from a
  second copy of the pack, whose made pictures would have had other
  numbers; it now uses the game's own gallery.

## Next: 4c

The rulebook on the desk: docked on the console, dragged closed and open,
its pages and links, its return to its dock, its sounds
(`desk-pictures.md`, `desk-movement.md`, `page-layout.md`). To read first:
`BoothEnv`'s text lookup for the day's rule texts and the rulebook's page
player on the desk. Then 4d: the clock running, the stamp bar, stamping.
