# The booth, part 1: what it is made of and how a day starts (`Booth`)

Studied on 2026-11-04, for milestone 4 (the booth with no travelers).
This part covers what the `Booth` constructor builds on desktop, in
which order (the order decides what is drawn over what), its state
machine as far as a day's start, its per-frame `update`, and three of
its parts read in full or nearly: the shutter, the console and the
console's clock. The papers on the desk are in `desk-pictures.md` and
`desk-movement.md`; the layout values in `booth-layout.md`.

Everything here is from the code; **nothing was compared with the
running game**.

Words used here:

- **entity**: an on-screen object in the game's tree of parts
  (`app.ent.Ent`); a parent is drawn before its children, children in
  their order (`screen-output.md`, `screens.md` part 1);
- **group entity** (`GroupEnt`): an entity that only draws a list of
  pictures;
- **state machine** (`app.Stater`): named states, each with functions
  run on entering, every frame, on leaving (`ENTER`, `STEP`, `EXIT`),
  values it moves towards over an "interp" time, and a duration after
  which it goes to a next state (`fade.rs` has the rules as read for
  milestone 3b);
- **booth coordinates**: as in `booth-layout.md`, the screen moved up by
  103.

## How the constructor was read

The decompiler had always timed out on this function (about 5,800
instructions) at the 120-second limit of `DecompileFunctions.java`, so
earlier steps read pieces of its instruction listing
(`decompiled/booth_ctor_asm.txt`). On 2026-11-04 the script got an
optional longer limit (the environment variable `PP_DECOMPILE_TIMEOUT`,
which also raises the decompiler's output limits); with 2,400 seconds
allowed, **the decompile finished in about 5 minutes**:
`decompiled/booth_ctor.c` (2,539 lines), cleaned and condensed copies
beside it. Its positions were checked against the instruction listing
for the wall, the shutter and the counter (the same arithmetic). The
`Layout` constructor was not retried (its values come from the
emulator, `booth-layout.md`).

## What the constructor builds, in order (desktop)

The booth is an entity at y = `Layout.booth.y` (103). Desktop's shape is
`LANDSCAPE` and its console kind `UNDEROVER`, so the phone branches
(criminal poster, carousel, rack, pincher, drop remote, key desk, stamp
desk, touch glows) are skipped. In the order made (which is the child
order, except where noted):

1. Its own clock (`boothClock`) and the `BoothEngine` (the booth's rules,
   `responses-and-events.md`), with 11 callbacks
   (`engine_onPapersAdded` and the rest). The list of staying papers at
   the start is taken from the engine.
2. Four things the inspect mode can mark: `Booth/Counter`, `Booth/Face`,
   `Booth/Clock`, `Booth/Weight` with their layout rectangles
   (`inspect-mode.md`).
3. **The wall picture** `assets/BoothWall.png` (178 x 135) at x =
   floor(floor(wall x + wall w / 2) − width / 2) = 0, y = wall y = 0,
   layer `layerWall` (−3). **Nothing draws it**: no code reads the field
   `wallSprite` except the field-access helpers (`__hx_getField`,
   `__hx_setField`, `__hx_getFields`), and it is in no group entity
   (whole-decompile search for the field and its hash `0x749710af`). So
   by the code the picture is made and never shown. In the window
   instead: the shutter (closed, it covers the window wholly: strips from
   y 0 to 107, x −1 to 179) over its shadow; with the shutter open, the
   traveler and what lies behind (not read for an open shutter yet).
4. The traveler entity (`TravelerEnt`, the person in the window) at
   x = wall x (0), given the wall's width (178). Read only in part.
5. **The shutter** (below), started open if the day's first traveler is
   the secret police (`Day.getFirstTravelerIsSecretPolice`), else
   closed; at x = floor(floor(0 + 178 / 2) − 180 / 2) = −1, y = 0.
6. The curtain (`Curtain`, for the body search; read only in part: its
   picture `assets/Curtain.png` is placed at the wall's corner and cut
   to the wall).
7. **The counter**: a group entity with `assets/Counter.png`
   (178 x 73) at x = 0 (centred on the counter rectangle as above),
   y = counter y (105).
8. **The console's under-picture**: a group entity with
   `assets/ConsoleUnder.png` (178 x 51) at x 0, y = console y (166).
   Made only for the `UNDEROVER` console kind (desktop's).
9. **The console** (`ConsoleEnt`, below) at the console's corner
   (0, 166).
10. **The shutter switch**: a button (`play.ui.Button`, `buttons.md`)
    with two looks, `down` (`assets/ShutterSwitchDown.png`) and `up`
    (`ShutterSwitchUp.png`), at `Layout.shutterSwitch` (150, 4); a click
    calls `shutterSwitch_onClick`. The shutter keeps it as its
    `switchButton`.
11. **The desk**: `assets/Desk.png` (512 x 512) at the desk's corner
    (178, 0), in a group entity together with **a hint text**: the text
    `booth_dragdocs` of `Text.xml` in the font `ui_regular`, colour
    `0xFF322525`, background `0xFF191212`, padding 6 across and 2 down,
    at x = floor(floor(178 + 392 / 2) − text width / 2), y = 217 − 5 −
    text height (5 pixels above the booth's bottom). (The phone branch
    has no hint.) Who hides the hint, and when, was not read.
12. The papers' root entity (`papersRootEnt`): every paper is a child of
    it.
13. Then **the console is moved to the end of the booth's children**
    (`orderChildToEnd`, `UNDEROVER` only). So the console's top picture
    is drawn after the papers: closed papers on the counter go under it,
    between the under-picture (8) and the top picture. The two console
    pictures are the same size; the top one presumably has holes where
    the dock places are (**inferred**, not checked in the pictures).
14. The speech bubbles (`SpeechChat`) at the wall's corner.
15. The three drop buttons (fingerprint, search, detain;
    `DropButton`), at x = desk x + their layout x (178 + 277, 191, 105),
    top y = desk y (0). Read only as far as the constructor's calls.
16. **The stamp bar** (`StampBar`, the desktop one), given the day's
    date, with `onApplyStampInk`. Not read yet.
17. **The drawer** (`Filer`, `desk-movement.md`) only when the day's
    feature flags have `0x20`, at `Layout.filer` x (198), with the
    confiscation rule's description; two `whenOpened` callbacks.
18. No booth header on desktop (`boothHeaderHeight` 0).
19. The inspect mode (`InspectUi`) only when the feature flags have 1.
20. **The day's opening card** (`introGroupEnt`): a black fill
    (0, 0, 0, alpha 1) the size of the booth (570 x 217), and over it a
    typing text (`RevealTextEnt`, `ui-parts.md`) in `title_tall`,
    colour `0xFFFFFF` (alpha 0: letters not yet typed keep the label's
    alpha, so they are hidden, and a typed letter gets alpha 1, so it is
    white; the typing rules as read for milestone 3c, `ui-parts.md`,
    `port/core/src/reveal_text.rs`),
    several lines allowed, saying the day's long date
    (`formatVerboseDate`, `text-xml-format.md`), plus a line break and
    the day's title when the day has one. It is centred across the booth
    and at y = floor(217 / 2 − its height / 2 − 20). One reveal step is
    made at once.
21. The console's date is set to the day's date.
22. The two ambient loops are started and set to 0 at once
    (`audio-layer.md`). The Nudity setting is copied.
23. The state machine (below).
24. The wall's paper order is read from `Game/MountedPapers` and the
    engine is started (`BoothEngine.start`: the day's papers are added,
    `papers-on-desk.md`), then `applyMountedPaperIdsOrder`.
25. **The first state: `off`**, entered at once (instant), or `empty`
    when the debug switch `skipSlowStuff` is on (not in normal play).

## The state machine (the start of a day)

The booth's states, with the constructor's line numbers of their
functions (the functions are decompiled as
`Booth___hx_ctor_play_day_booth_Booth_<line>__Fun`). Read here: `off`,
`intro`, `intro-instant`, `empty`. The others are listed as made; their
functions are not read yet.

| State | Enter | Every frame | Leave | Moves | Time, then |
|---|---|---|---|---|---|
| `off` | 381: the booth's switch 8 cleared (its parts get no input) | 385: one step of the opening card's typing | 389: switch 8 set again | the opening card active, at y 0 | none (left by `startIntro`) |
| `intro` | 399: the sound `booth-intro` | | 403: the opening card's text hidden | the card: `active` to false with `STEP(1.0)` (it stays until the end), y to 217 (the booth's height) along `BOUNCEBACK(0.2, 1)` | interp 1.0 s, duration 0, then `empty` |
| `intro-instant` | 413: the engine's first event, then `ENTERING_START` (before 6 PM or not), the traveler set and snapped to his place, the inspect mode prepared, `booth-intro` | | 422: the card's text hidden; the engine's second event | as `intro` | interp 1.0 s, then `welcoming` |
| `empty` | 432: the engine's first event; a day stash made if the engine allows (`save-format.md`) | 437: when the day's time is up, `done` | | the card inactive | |
| `entering` | 445 | 466 | 471 | | then `working` (time not read), 485 on the way |
| `working` | 493 | at 0.5 s: 497; 501 | 523 | | |
| `waiting-to-detain` | 531 | 540 | | | |
| `detaining` | 547 | 553 | | the card inactive at y 0 at once; the black fill to alpha 0.5 | interp 0.25 s; 567 |
| `poisoned` | 589 | at 2 s, 4 s, 6 s: 593, 597, 601 | | | |
| `waiting-to-leave` | 608 | 614 | | | |
| `resisting` | 624 | 628 | | | |
| `leaving` | 635 | 642 | | | |
| (one more, name not seen in the decompile) | | at 3 s, 8 s, 30 s: 659, 664, 671 | | | |

`intro-instant` is for a day whose first traveler is the secret police
(the shutter starts open): the card drops and the traveler is already
in the window. **Who calls `startIntro`**: one call in the border scene
(`play_day_border.clean.c`, the call at line 6834) and one in the
booth's own field helper. The border's is `Border.person_onEvent`, on
the event `start-intro` (read on 2026-11-05, part 2; this said which
border function it is was not read).
`startIntro` goes to `intro`, or to `intro-instant` when the first
traveler is the secret police.

So **a day opens like this** (by the code): the booth part of the
screen is black with the date typing in the middle; the border scene
above runs; when the border scene says so, `booth-intro` plays and the
black card falls off the bottom over one second with a small bounce,
and the booth is `empty` (no traveler yet).

The curves `STEP` and `BOUNCEBACK` (`app.Interp`) were read on
2026-11-05 (part 2 below, "The curves"; this said not read yet).

## Every frame (`Booth.update`, read in full)

1. The booth's clock moves on; the state machine steps with its `dt`;
   the story's play time grows; an endless day's own update.
2. **The console clock's hour**: 6 while waiting for the first traveler;
   otherwise, unless the state is `busy-with-border` (then not set),
   lerpScale(booth clock time, 0, day minutes x 60, 6, 18): **the clock
   runs from 6:00 to 18:00 over the day's length**.
3. The weight on the console: the text `Booth/Weight` of the booth's
   facts when the traveler stands at his place (`Position`'s second
   value), else empty.
4. The ambient loops and the room by the state (`audio-layer.md`, "The
   booth's ambient loops"): in `off`, `intro`, `empty`,
   `busy-with-border`, `waiting-to-detain` and `detaining` the border's
   sound, else the booth's.
5. The time bomb's beeps (every 5, 3, 2, 1 or 0.5 s as its 60 seconds
   run down; at 0 `timeBombExplode`).
6. `time-up` plays on the frame the booth clock passes the day's length
   (not while waiting for the first traveler).
7. A changed Nudity setting is passed to the engine.

## The shutter (`Shutter`, read in full but its draw order inside the traveler)

- Its picture `assets/Shutter.png` (180 x 120) is cut into **six strips
  20 pixels high** (rows 0, 20, ..., 100), each a sprite.
- A **shadow**: a filled box the picture's width (180) and the wall's
  height (107), colour (0.098, 0.0706, 0.0706, 1) as 4-byte floats
  (`0x3DC8C8C9`, `0x3D909091` twice, 1.0), which are 25/255 and 18/255:
  `0xFF191212`; on `layerShutterShadow` (−1).
- Two states: `closed` (0.35 s to `openT` 0 along `BOUNCEBACK(0.1, 1)`)
  and `open` (1.0 s to `openT` 1 along `SMOOTHERSTEP(0, 1)`). Their enter
  functions (constructor lines 33 and 42, read on 2026-11-05; this said
  not read) play `shutter-drop` and set the switch's look `down`, or play
  `shutter-rise` and set `up`. It starts in its state at once; at that
  moment the switch is not yet given to it, so the switch keeps its first
  look, `down`.
- `set_openT(t)`: with h the shadow's height (107), top = (−40 − h) x t +
  h; strip i of n (6) gets y = floor(min(i x (h / n), top − (n − i) x
  strip height x 0.5 − strip height x 0.5)), the strip height being the
  first strip's (20) (checked in the instructions on 2026-11-05,
  `decompiled/booth4a_run1.txt`; this said "to be checked"). Closed
  (t = 0): y 0, 17, 35, 53, 71 and 87. The shadow's y = floor(min(0,
  top − h + 40)); the traveler entity is told `t`.
- `isFullyRaised`: open and more than 0.01 s in that state.
- Drawing: the shadow, then the traveler's parts that go in front of the
  shadow (`TravelerEnt.drawInFrontOfShutterShadow`: nothing while the
  traveler entity is not visible, which it is not until a traveler is
  set; read 2026-11-05), then the six strips.

## The console (`ConsoleEnt`, read in full) and its clock

At the console's corner (0, 166). With the `UNDEROVER` kind:

| Part | What | Where (in the console) |
|---|---|---|
| Top picture | `assets/Console.png` (178 x 51), whole | x = floor(floor(0 + 178 / 2) − 178 / 2) = 0, y 0 |
| Clock | `ConsoleClock` (below) | `consoleClock` (9, 21) |
| Transcript bolt | `assets/ConsoleBolt.png` (9 x 7), hidden in the state `idle`; the state `flashBolt` (2 s, then `idle`) blinks it with `FLASH(5.0)` | `consoleTranscriptBolt` (85, 31) |
| Date | font `digits`, colour `0xFF422A1C`, the date as the Date Format setting writes it (`Settings.formatDate`) | x 4, y = 48 − the font's ascent |
| Traveler count | font `digits`, colour `0xFF6A522F`, the count as two digits ("00" at first) | x 86, y = 42 − ascent + cap height |
| Weight | font `digits`, colour `0xFF422A1C`, "---" at first; a new weight without "kg", **right-aligned** to x 164 (x = 164 − its width, cut toward zero) | y = 34 − ascent |

They are drawn in that order (top picture, clock, bolt, date, count,
weight). Other kinds (not desktop) use two halves of the picture or a
centred one.

**The clock** is a 16 x 16 picture made again on each `set_hour(h)`:

- cleared, or filled with `0xFF422A1C` when h ≥ 18, or when h > 16 and
  fmod(h x 20, 1) > 0.75 (so in the last two hours it goes dark for a
  quarter of every 3 minutes of clock time, and stays dark from 18:00);
- the minute hand: a 32 x 16 picture of `0xFF422A1C` drawn with an
  affine transform (`Image.draw`, `fact-pictures.md`): moved up by half
  its height, scaled to 8 x 1 pixels, turned by the matrix (cos, −sin;
  sin, cos) of minus the angle π/2 − 2π x fmod(h, 1), and moved to the
  picture's middle (8, 8); so at a whole hour it points straight up;
- the hour hand: the same, scaled to 6 x 2, with the angle π/2 − 2π x
  h / 12 (at 6:00 it points down);
- `assets/ClockPin.png` (2 x 3) pasted at (7, 7), mode `REPLACE`.

(The `fmod` arguments and the angles' signs were read in the
instructions on 2026-11-05, `decompiled/booth4a_run1.txt`; this said they
were needed. The port draws the 6:00 picture: `day.rs`, `clock_picture`.)

## Part 2 (2026-11-05, for milestone 4a)

Read for the port's first booth screen (`milestone-4.md`, "4a"), in the
decompile unless said otherwise; one Ghidra run for two functions'
instructions (`decompiled/booth4a_run1.txt`); constants with
`read_doubles.py`. The port and the reference
(`scripts/reference/boothscreen.py`) follow it.

### The state machine's rules (`app.Stater`, `app.State`, read in full)

These hold for everything that uses it (the port's `stater.rs`; `fade.rs`
had them for the screen change only):

- A state has functions with a time (`ENTER`, `STEP`, `AT_STEP(t)`,
  `EXIT`, and two interp-time kinds not used here), targets (an object and
  properties with values, plain or an `Interp`), an interp time (0 by
  default) and a duration with a next state (none by default).
- `go(name, instant)`: the current state's `EXIT` functions; with no
  current state the change counts as instant. Not instant: the new
  state's targets' present values are kept (the snapshot), the state is
  entered (`ENTER` functions, its at-time functions made ready again, its
  clock to 0, its targets set at blend 0 from the snapshot) and the
  countdown set to its interp time; with interp time 0 the targets are put
  in place. Instant: entered without a snapshot, the targets in place.
  Then, when the countdown is 0, the targets are applied once more at 1.
- Applying a target at t: from the snapshot's value (or the target
  itself when there is none) to the target, by its `Interp` or, for a
  plain value, straight (numbers) or jumping at t = 0.5 (anything else).
- `step(dt)`: while the countdown is not 0, the targets at t = 1 −
  countdown / interp time (at most 1); at t ≥ 1 the countdown becomes 0
  and a state with duration 0 and a next state goes there; otherwise the
  countdown loses dt (exactly 0 becomes −1, so the next step ends the
  blend). Once settled: a state with a duration ≥ 0 and a next state goes
  there when its clock has reached the duration; otherwise its clock
  gains dt and its `STEP` functions and due `AT_STEP` functions run, in
  the order added. **So `STEP` functions do not run while a state
  blends.**

### The curves (`app.Interp.get`)

t is first held to its segment (0 to 1 by default). `STEP(t0)`: the start
value below t0, the target from it. `LINEAR`: a straight line. `POW(p)`
and `INVPOW(p)`: t^p and 1 − (1 − t)^p. `SMOOTHSTEP` and
`SMOOTHERSTEP(e0, e1)`: `app.Num`'s. `BOUNCEBACK(perc, count)`: with
k = floor((count + 0.5) t + 0.5) and amp = 1, or (k / (count + 1) −
1 / (count + 1)) x (−perc) + perc when k / (count + 1) ≥ 1 / (count + 1),
the value is 1 − |cos((count + 0.5) π t)| x amp: it reaches the target,
comes back by perc of the way, and lands on it at t = 1. `FLASH(n)`:
for t below 0.999, the target while fmod(t n, 1) ≥ 0.5 and its opposite
(a true / false value) otherwise; from 0.999 on, the target.
`RISEFALL(mid)`: up to 1 at mid, down to 0 at 1. (This answers the notes
on `BOUNCEBACK` and `INVPOW` in `desk-movement.md` and `buttons.md`.)

### The clocks (`app.Clock.update`)

A clock's **first update gives dt 0** (it only takes the time); later
ones give the time since the last. The booth's own clock and the
border's are new with the day screen, so on its first frame neither
moves. The typing (`stepReveal`) and the booth button's blink use the
game's clock.

### The start of a day, frame by frame

- The border constructor's walk-in: a free leaving figure gets
  `enter-right` and `moveToStop(1)`, so it follows the path from its
  first point, 60 units at the default speed 10; each border frame adds
  dt x 10; when the distance reaches 60 the path's end event
  `start-intro` comes (`Border.person_onEvent`): the booth goes to
  `intro` (`intro-instant` for the secret police) and the border to
  `ready-to-call` (`border-scene.md`, "The start of the day"). At 60
  frames a second that is frame 362.
- `intro` blends for 1.0 s, then (duration 0) `empty`: the card is gone
  on the 61st frame after.
- `ready-to-call` (border constructor lines 272, 276, 290): entering
  gives the booth button input; every settled frame its look is
  `highlight` when fmod(game time, 0.75) ≤ 0.375, else `normal`; leaving
  sets `normal`.
- The booth button (`OuterBooth.png`, `buttons.md`): `normal` is rows 0
  to 37, `highlight` rows 38 to 75, both 56 wide, at (146, 65).
- The border's first state `off` runs a boss day's view every frame (not
  read further).

### The opening card's text

A story day's title is the empty text (the `Day` constructor sets `""`;
the only other writer is the field-access helper), and the booth checks
for a missing title, not an empty one, so the card says the long date, a
line break and nothing: **two lines**, 40 pixels high in `title_tall`, at
(226, 68) in the booth for day 1 (on one line it would be at y 78). The
text is set while one-line, then made several-line, which lays it out
again.

### The console's weight

`ConsoleEnt.set_weight` changes the text only when the new weight
differs from the field `weight`, which the constructor never sets. The
booth's first update sets it to the empty text (no traveler at his
place), so the "---" the constructor wrote is replaced at once: **it is
never seen**.

### The stamp bar (`StampBar` constructor and `BarPiecesEnt`, read)

- Two stamps, `Approved` (x 160) and `Denied` (x 40), inside a bar of
  `StampBarTop.png` (280 x 47), `StampBarMid.png` (280 x 16) under it and
  `StampBarBot.png` (280 x 20) under that, at y = `Layout.stampBar` y
  (24). The bar draws its top, its bottom, its stamps, then its middle.
- Its states: `open` (0.75 s, x to 570 − the bar's width, along
  `BOUNCEBACK(0.1, 1)`; input on at 0.25 s) and `closed` (x to 570 − 10
  along `BOUNCEBACK(0.05, 1)`; input off), started `closed` at once:
  **10 pixels of the bar show at the desk's right edge**; the stamps (x 600
  and more) are off the screen.
- A reason stamp in its own bar (`ReasonStampBar*.png`) at x 182 above
  the desk, `closed` (hidden) at the start, and the reason drop button.
- Day 1 has no features (`Days.csv`), so no drawer and no inspect mode.

### Other parts at the start

- The curtain starts `open`: its two halves are hidden.
- The traveler entity's `visible` is never set by its constructor
  (false): it draws nothing until a traveler is set.
- The rifle buttons start out of view (`border-shooting.md`); the
  border's truck wreck and bombed wall are hidden.
- The shutter's first `closed` plays `shutter-drop` in the frame of the
  screen change, which ignores one-shot sounds (`audio-layer.md`).

## Not read yet (for milestone 4)

- (The stamp bar, the curtain's start, the traveler entity with nobody
  there, the border's pictures at the start of a day, who calls
  `startIntro` and `app.Interp`'s curves were listed here: read on
  2026-11-05, part 2 above.)
- The drawer's constructor positions beyond `desk-movement.md`, the drop
  buttons' constructor, `Stamp`'s drawing.
- The functions of the states from `entering` on, and `Booth.react`.
- The border's figures at the start of a day (guards, the waiting line):
  `border-figures.md` has their rules; not drawn yet.
- Who hides the desk's hint text.

## Things to watch in the game

None was done.

1. A day opens on a black booth with the date typing in the middle,
   then the black falls away downward with a small bounce.
2. The console clock shows 6:00 until the first traveler is called, then
   runs to 18:00 by the end of the day.
3. A hint at the bottom of the desk (the text `booth_dragdocs`).
4. Closed papers on the counter pass under the console's top picture.
