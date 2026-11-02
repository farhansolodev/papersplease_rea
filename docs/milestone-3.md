# Milestone 3: the title screen alive

Milestone 3 (`DESIGN.md`, "Milestones") is the game's cursor, buttons
with their pressed look and sounds, the title rising with the music, the
settings and pause screens with working volumes, the intro pages, and the
fades between screens. That is too much to try in one go, so it is split
into three, like milestone 1 (decided by me on 2026-11-03; the user said to
plan and go ahead without waiting):

| Part | What you can try | State |
|---|---|---|
| **3a** | The title alive: the game's own cursor, the title rising with `Theme`, a click or key skipping the rise, the logo bobbing, the buttons pressing and clicking with their sounds | **Built 2026-11-03** (below), tried by the user the same day |
| 3b | Screens: the fade between screens, the settings screen with working volumes (kept in the browser), the pause screen on Escape, Escape and the browser's full screen | Not started |
| 3c | The intro pages (the page player) | Not started |

## 3a: How to try it

From the project folder:

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080` and click "Click to start". You should
see:

1. **The title rises from the bottom** in 20 steps, one every 1.2 s or so,
   in time with `Theme`, for about 24 s. The buttons do nothing while it
   rises.
2. **A click or a game key skips the rise**: the title jumps to its place.
   The game keys are Tab, Space, Enter, the left and right arrows, Escape,
   T, L, P and O. Other keys are not game keys and do nothing.
3. Once the title is up, **the logo moves down and up by 5 pixels** once a
   bar of the music (every 2.4 s at first, faster later).
4. **The game draws its own cursor**, a small pixel arrow; the system's
   cursor is hidden over the game. Over a button it becomes **a hand**.
   (Before the mouse first moves over the game no cursor shows, as in the
   original.)
5. **The buttons** (STORY, ENDLESS, the settings button bottom left, the
   "created by" line): pressing one shows it filled with black text and
   plays a click; letting go over it plays the release click. Slide off
   while holding: it goes back to its outline; let go off it: nothing.
   Nothing happens after a click yet: the screens they lead to come in 3b
   and later milestones. (The browser's console shows "title: story
   clicked" and so on.)
6. A reload shows the rise again (every start of the page is a new run).

The button sounds come from the effects pack, which arrives a moment after
the start (milestone 2); a press in the first second or two may be silent.

## 3a: What was built

In the core (`port/core/src/`), all of it plain Rust, tested with
`cargo test`:

- `rand.rs`: the game's random generator `app.Rand` and its shuffled
  order (`ShuffledSequence`, without reshuffling), as
  `scripts/reference/rand.py` and `cyclers.py`. Needed now because
  `Sounds.xml`'s sounds with several recordings each take a draw when the
  file is read.
- `aud.rs`: the game-side audio layer `app.aud` (`audio-layer.md`):
  `Sounds.xml` as `SoundDefLib` reads it, the speaker (effects, songs,
  rooms, the ignore switch, pause and stop), one playing sound's
  straight-line fades, the music player (`Music`: the same song plays on, a
  change fades the old one out over 4 s), and the beat table
  (`MusicBeat`). It talks to the sound player through `AudioHost`, the
  original's `PlatformAudio`. The same as `scripts/reference/aud.py`.
- `input.rs`: pointer 0 and the keys as `app.ent.Input` and `Pointer` keep
  them (`input-handling.md`; the same as `scripts/reference/inputs.py`):
  just down and up, held inside the screen, taking the pointer, blocked
  areas, the double click, keys and pointers held back until released, and
  the drawn cursor's place (arrow at -1, -1; hand at -6, -2).
- `button.rs`: `play.ui.Button` (`buttons.md`): looks, the pressed state,
  the mouse and shortcut-key rules of `ButtonHelper.react` read again in
  full for this step, the press and click sounds, drawing.
- `num.rs`: Haxe's `Math.round` and `app.Num.smoothstep`.
- `title.rs`: the title screen is now a live screen. `rise()` is
  `TitleScreen.update`'s arithmetic (read again in the decompile and in
  `decompiled/titlescreen_update_asm.txt`): b = beat x 0.5 + 0.035; 20
  steps, each eased by `smoothstep(0, 0.2, b mod 1)`; the bob
  `round((smoothstep(0, 0.1, x) - smoothstep(0.5, 0.6, x)) x 5)` with x =
  (b x 0.5) mod 1. `react` is `TitleScreen.react`: while rising, a pointer
  press or any game key sets "skipped" and holds the mouse back until it is
  let go. The screen at rest (`TitleScreen::at_rest`) is milestone 1b's
  still, now drawn through the new button code.
- `screen.rs`: `game_pixel`, the window point to game pixels as
  `HostUnity.Update` does it.

In the host (`port/web/src/`): the sound player is the core's
`AudioHost` (`sound.rs`); `main.rs` reads the mouse (in game pixels, from
the picture's place in the window) and the 11 game keys, runs the title
screen per 1/60 s step in the original's frame order (input, the screen's
update, the music, the screen's input, the speaker), draws the cursor
last, and hides the system's cursor on the title page.

In the page (`port/www/index.html`): after the start, the game gets the
keyboard focus, and over the game the browser's own action for Tab,
Space, Enter and the arrow keys is stopped (for those keys only).

In the start pack (`scripts/build_assets/build_pack.py`):
`CursorArrow.png`, `CursorHand.png` and `data/Sounds.xml`. The English
language pack does not touch `Sounds.xml` (`en.zip` holds no sound file
and `language-pack.md` lists no change to it).

## 3a: Decisions (mine, reversible)

- **Milestone 3 split into 3a, 3b and 3c** (above).
- **The speaker's clock gets the fixed step**, 1/60 s per step, not the
  real elapsed time. The original gives its speaker real time with no cap
  (`audio-layer.md`); the two differ only when the browser falls behind by
  more than 0.1 s a frame (then the port's fades slow down with the game).
  `DESIGN.md`, "One frame", is corrected to say so.
- **A press is never lost between frames.** A key or mouse press that
  starts and ends within one browser frame, or falls in a frame that runs
  no step (a display faster than 60 Hz), counts as held for the next step.
  Found by the browser check: its key press and release arrive together,
  and the first build missed them (below).
- **The ids of the buttons' clicks are only logged** until the screens
  they open exist.
- Left out, as decided before: the quit button, the version button, the
  test tooling's `SoakTapper`.

## 3a: Checks

- `cargo test -p pp_core` (in `port/`, with `CARGO_HOME` set to
  `.cargo-home`): 81 unit tests (27 new) and the three comparisons with
  the Python references. New ones compare with the references' own
  numbers: the generator for three seeds and three shuffled orders
  (`rand.py`, `cyclers.py`); the beat at seven times and a song change
  taking 238 frames (`aud.py`); **the game's own `Sounds.xml`** read as
  `aud.py` reads it (94 sounds, 2 looping, 1 with a room, the same sums of
  volumes and fades, and the same 7 first recording picks for each of the 9
  sounds with several recordings). Others test the rules from the docs:
  the rise (277 after 1 s; still rising at 23.55 s, arrived at 23.65 s;
  never moving down), the bob (5 down at 0.6 s, up at 1.8 s), the button
  rules (press, slide off and on, let go outside, press outside and slide
  on, the right and bottom edges, Escape on a back button, a disabled
  button), the pointer rules (taking, blocking, the double click, held
  inside the screen, masks), the window-to-game-pixel rule.
- **The title at rest is still identical, byte for byte, to the Python
  reference** `titlescreen.py` (`tests/title.rs`), now drawn by the new
  button code.
- `node scripts/checks/web_offline_check.mjs 8080` in headless Edge, step
  1a rewritten for 3a: right after the start the picture differs from the
  still (118,062 bytes; the title rising); Space skips the rise and the
  canvas then equals the still byte for byte (5.4 s later in the second
  run, 3.6 s in the first: the logo must be in its up phase); the mouse
  over STORY changes only pixels inside the hand's picture; a press
  changes only STORY and the cursor; the release brings STORY back; the
  sound player was asked for `button-down.wav` then `button-up.wav`. All
  of milestones 0 to 2 still pass, offline start included. **2 runs, both
  passed.**
- A look in the app's browser pane (a visible window): the title rises
  from the bottom in steps and arrives after about 24 s; a hand over
  STORY, the arrow elsewhere.

## 3a: Measurements

- WebAssembly 26,447,590 bytes (26,423,219 after milestone 2).
- Start pack 2,040,820 bytes.

## 3a: Findings

- **A button does not block its rectangle.** `ButtonHelper.react`, read
  in full for this step, calls `getPointerOver` and never
  `getPointerJustDown` or `maskAreaUntilFrameEnd`. `input-handling.md`
  said the buttons block "through `getPointerJustDown` and their own
  code"; that was wrong and is corrected there (2026-11-03). Two buttons
  never overlap on the screens read so far, so nothing built on it
  changes.
- A button renews its hold on the pointer every frame the mouse button
  stays down, and the click comes on the frame the mouse button goes up,
  if the button was pressed the frame before and the pointer is still
  inside (as `buttons.md` says).
- `FUN_180131040` in `TitleScreen.update` is called with (b, 1.0), the
  fraction of b (C's `fmod`), from the instructions.

## 3a: Not tested

- **By the user, in detail.** The user tried 3a on 2026-11-03 and said
  "everything actually works quite well"; which browser, and which of the
  items under "How to try it" were looked at, was not recorded.
- **Against the running game**: the rise's timing and steps, the bob, the
  buttons and the cursor are from code reading only (`screens.md` part 2,
  "Things to watch in the game", and `buttons.md`'s list are still open).
- Whether the system's cursor is really hidden over the game: the pane's
  screenshots do not show the system cursor.
- A mouse button let go outside the browser window while held over a
  button (whether the browser reports the release).
- Firefox, Chrome by hand.
- The title's rise when `Theme` stalls on a slow first download (it
  should wait with the song).
- A second title screen of the run (no rise): needs screen changes (3b).

## 3a: Dead ends and failures

- **The first build did not skip the rise on a key** in the browser check
  ("the key did not skip the rise (no still within 8 s)"). The check sends
  the key's press and release together, so the browser's frame saw the key
  "just pressed" but no longer held, and the host passed on only "held".
  Fixed by remembering a press until a step has seen it (the decision
  above); the next two runs passed. Solved.

## After 3a: the frame counter (`?fps`)

Asked for by the user on 2026-11-03. Opening any page with `?fps` in the
address (for example `http://localhost:8080/?fps`) shows the browser's
frames per second in the window's top left corner, counted by the page
with the browser's frame timer and updated once a second. It is a
development aid, off by default.

- It is a box of the page (`port/www/index.html`) laid over the canvas,
  not part of the game's picture: the game's 570 x 320 picture is
  unchanged, and clicks pass through the box to the game. In a window
  where the picture reaches the corner (an exact multiple of 570 x 320,
  or "Fill the window") it covers a corner of what you see, not of the
  game's pixels.
- It counts what the browser draws, not the game's steps; those stay
  1/60 s each (`DESIGN.md`, decision 1). A count of the steps would need
  the Rust host; left out to keep the change to one file (my choice, the
  user asked for the simplest).
- Checked: the browser check's title step now runs with `?fps`. The
  counter shows a number, and the canvas is still byte for byte the
  reference after the skip; every other step passed (1 run). In the
  hidden headless browser and in the app's pane (hidden while I work)
  it read 0 to 4 fps: a hidden page is drawn only a few times a second,
  so those numbers say nothing about a visible window. The user tried it
  in a visible window the same day and said it looks right (the number
  shown was not recorded).

## Next: 3b

The plan for 3b, to be read before it is built: `save-format.md` part 2
(the screen change: `GameTransition`, `queueScreenChange`,
`applyScreenChange`, the fade), `screens.md` parts 1 and 4 (`GameScreen`,
`enablePause`, the pause screen, the settings screen and its rows, who
writes the settings), and `audio-layer.md` (a screen change fades the
effects out; the pause screen pauses effects only). Still open for it:
`DESIGN.md`'s fullscreen and Escape row, and splitting the title's and
menus' effects into the start pack (`milestone-2.md`).
