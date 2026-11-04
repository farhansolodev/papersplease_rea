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
| 4b | The rulebook (docked, dragged, opened, its pages), the shutter switch, the pause screen | Not started |
| 4c | The clock running, the stamp bar, stamping | Not started |
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

## Next: 4b

The rulebook docked on the console, dragged closed and open, its pages and
links, its return to the dock (`desk-pictures.md`, `desk-movement.md`,
`page-layout.md`; the day's rule texts need `BoothEnv`'s text lookup, to
read); the shutter switch (`Booth.shutterSwitch_onClick`, the shutter's
`open` state: `SMOOTHERSTEP`); Escape and the pause screen (reading list at
the end of `milestone-3.md`).
