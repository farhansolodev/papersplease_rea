# The border scene, part 4: the view, the cameras, the endless scoreboard

The last part of the border scene (`play.day.border.*`). Part 1 is
`border-figures.md`, part 2 `border-scene.md`, part 3 `border-shooting.md`.
Studied 2026-10-14.

This part covers: sliding the top view left and right ("panning",
`BorderPan`), keeping the view on a figure during an attack
(`Border.panToPeople`), the two small camera screens (`BorderCam` and its
two helper classes), the scoreboard shown in endless mode
(`EndlessScoreboard`, `FlashingScore`), and the layout values all of these
depend on. It also answers three older open points: the figures' hit box,
the slow-motion scale during shooting, and whether the game's frame time
varies.

## The short version

**Almost nothing in this part is visible in the desktop game, which is what
the port copies.** The game has three screen layouts, and the code in this
part exists mainly for the two portrait (phone and tablet) ones:

| | Desktop | Tablet | Phone |
|---|---|---|---|
| Layout shape | `LANDSCAPE` | `PORTRAIT_WIDE` | `PORTRAIT_THIN` |
| Can the view slide sideways? | **No**: the scene is 570 wide and so is the window | Yes | Yes |
| Camera screens | **None** | Two | None |
| Slow motion while shooting | **None** (scale 1.0) | 0.9 | 0.8 |
| Frame around the scene while shooting | No | Yes | Yes |

On desktop the pan code still runs every frame, but every result is forced
back to position 0. What does matter for the port: the scoreboard (endless
mode), the hit box size, and the frame-time rule.

## What was read

Read in full from the decompiled code: `BorderPan` (constructor, `update`,
`react`, `panToSide`, `followPersonForOneFrame`, `makeStash`,
`restoreFromStash`), `Border.panToPeople` and its five callers,
`play.ui.KineticScroll` (the drag-and-coast helper), `BorderCam`
(constructor, `draw`, `react`, `tween_buttonPressed`), the
`BorderCamRenderer` constructor and `applyPalette`,
`Booth.attachBorderCamsToBorder`, `EndlessScoreboard` (`update`, `draw`,
`endless_onNotifyScoreboard`, `toSignedString`, and the desktop branch of
the constructor), all of `FlashingScore`, `app.Clock`, and the three places
in `play.day.Endless` that notify the scoreboard.

Read from machine instructions (the decompiler dropped the values or gave
up): the `Layout` constructor, which is too large for the decompiler (it
timed out after 120 s); the two fixed offsets in the bike scenes; the number
shown as the total score. 30 number constants were read from the DLL with
`read_doubles.py`.

Skimmed, not read line by line: `BorderCamVisual.buildTiles`, and the phone
branch of the scoreboard constructor.

## The layout values (`Layout`)

`Layout` is one object holding every position and size of the screen. Its
constructor picks one of three blocks by the platform kind: `DESKTOP` gives
shape `LANDSCAPE` and a fixed 570 x 320 pixel screen; `TABLET` gives
`PORTRAIT_WIDE`; anything else gives `PORTRAIT_THIN`. The two portrait
shapes compute their size from the device's screen.

Values for the desktop block (all read from the instructions):

| Value | Desktop | Notes |
|---|---|---|
| Screen (`kPixelWidth` x `kPixelHeight`) | 570 x 320 | |
| The border scene's rectangle (`border`) | x 0, y 0, 570 wide, 103 high | |
| `borderScale` | 1.0 | The phone block sets 2/3 |
| `borderPersonHitSize` | **8 wide, 18 high** | The figures' hit box (part 3) |
| `borderSnipingTimescale` | **1.0** | Set to 1.0 before the blocks; the desktop block leaves it. Phone 0.8, tablet 0.9 |
| `borderShowSnipingSurround` | false | Never set in the desktop block; set to true in both portrait blocks |
| `borderCamRectL`, `borderCamRectR` | **not set (empty)** | Only the tablet block sets them |
| `borderOuterBoothButton` | (146, 65) | The booth button of part 2 |
| `tranqRifleButtonY` | 113 | |
| `endlessScoreboardPos` | (180, 2) | |
| `endlessScoreboardScrollWithBorder` | true | |
| `headerInEndless` | false | |

Fixed numbers set for every layout (`Layout`'s static values):
`kBorderFullWidth` 570, `kBorderFullHeight` 103, `kEndlessScoreboardWidth`
180, `kDesktopPixelWidth` 570, `kDesktopPixelHeight` 320.

Not looked up: the tablet and phone values beyond the few named here.

## Panning (`BorderPan`)

"Pan" = the horizontal position of the view on the scene, in pixels. 0 is
the left end.

### Set-up

- Window size = (screen width, height of the border rectangle).
- Largest pan = (scene width - window width, scene height - window height),
  each not below 0. **On desktop both are 0.**
- A drag helper (`KineticScroll`) with decay 0.95, horizontal.
- "Wanted side" starts as `NONE`. The five values are `NONE`, `LEFT`,
  `RIGHT`, `BOUNCE_LEFT`, `BOUNCE_RIGHT`.

### Every frame (`update`, called from `Border.update`)

Nothing below happens on a frame where the player is dragging (the helper
was touched on this or the previous frame). Otherwise, by the wanted side:

1. **`NONE`, nobody to follow.** The drag helper lets the view coast on with
   the speed the finger left it (the speed decays). If the view has gone
   past the left end, the wanted side becomes `BOUNCE_LEFT`; past the right
   end, `BOUNCE_RIGHT`. The coasting speed is remembered as the bounce's
   strength and the helper's speed is cleared.
2. **`NONE`, somebody to follow** (set for one frame by `panToPeople`, see
   below). The target is the point that puts the figure in the middle:
   `(figure x + offset) x borderScale - half the window width`, and the same
   for y without the offset. The view moves toward the target by at most
   `speed x dt` sideways, where the speed is between 100 and 1,000 pixels a
   second in proportion to the distance left (1,000 at a full scene width),
   and by at most `500 x dt` up or down. It never overshoots. Then the
   figure is forgotten and a 2-frame countdown is set.
3. **`LEFT` or `RIGHT`** (a requested slide to one end, `panToSide`). The
   speed starts at 500 pixels a second and gains 1,500 a second; the view
   moves by `speed x dt`. On reaching the end it stops there and the wanted
   side becomes the matching bounce.
4. **`BOUNCE_LEFT` or `BOUNCE_RIGHT`.** With `v` = the speed at the moment
   of impact (not above 400): the bounce is `4 + 6 x v/400` pixels deep and
   lasts `0.2 + 0.2 x v/400` seconds. The view dips back into the scene by
   one smooth arc and returns to the end; then the wanted side is `NONE`.
   (The arc function is called with pi x progress, so it is taken to be a
   sine. Inferred from that; the function itself was not identified.)

Last, every frame: the pan is rounded to a whole pixel and forced into the
range 0 to the largest pan, and the 2-frame countdown goes down by one.

`Border.update` then places things from the pan: the scene's x = the border
rectangle's x minus the pan; the layer of things that must not slide
(`nonScrollingEnt`) and the frame shown while shooting get x = the pan, so
they stay still on screen.

### What moves the view

| What | Effect |
|---|---|
| The player drags on the scene (`react`) | The view follows the finger. Ignored while a rifle is selected for shooting (`Border.react` does not pass input on then) and while the 2-frame follow countdown runs. Sets the wanted side to `NONE` |
| `panToSide(left)` | Slide to that end. Called by: the path events `pan-right`, `bomber-alarm` (both to the right) and `watch-poisoning` (to the figure's side); `tutorForcePanLeft` (only if the pan is above 0); a press on a camera screen (below) |
| `panToPeople(p0, p1, p2, offset)` | Follow, for this frame, the first of the three figures that exists, is alive and whose picture is inside the scene (x from 0 to 570, y from 0 to 103). Callers below |

`panToSide` first nudges the view 2 pixels away from the end it is heading
for, if it is nearer than that.

Callers of `panToPeople`, all "every frame" functions of a state (part 2):

| State | Followed | Offset |
|---|---|---|
| `off` and `waiting-for-chat`, on a boss day | the boss; failing that, his car, but only in the state's first 3 s | 0 |
| `runner` (unless the day has a border target) | the runner | 0 to 50, in proportion to the runner's x between 185 and 320 |
| `truckwreck` | `enemy0`; failing that `enemy1`; failing that the truck | 0 |
| `bikeattack` | `enemy0` | 50 |
| `bikerunner` | `enemy1` | 40 |

The two bike offsets were dropped by the decompiler and are read from the
instructions; part 2 listed them as missing.

Because a state renews the follow every frame, the 2-frame countdown never
runs out during such a state, so the player cannot drag the view then.

### Saving

`makeStash()` returns one number: 0 if the wanted side is `LEFT`, the
largest pan if it is `RIGHT`, else the current pan. `restoreFromStash(p)`
sets the pan to `p`. (Part 2 already said that saving the scene stores only
the pan position; this is the detail.)

### On desktop

The largest pan is 0, so the final step of `update` sets the pan to 0 every
frame, whatever happened before it. `panToSide`, `panToPeople`, dragging and
the bounce all run and change nothing that is drawn. The saved number is
always 0.

## The cameras (`BorderCam`)

Two small screens that each show one end of the scene, so that a player on a
narrow screen can see both ends at once and jump the view there.

`Booth.attachBorderCamsToBorder` creates them **only if the layout has both
camera rectangles**, which only the tablet block sets. So the desktop game
has no cameras, and their random generators (day seed + 1 and + 2, part 1)
are never created there.

For the record, what they do where they exist:

- One shared renderer makes half-size copies of the scene's background
  picture and of the figures' picture atlas, and recolours both to four
  colours taken from `BorderCamPalette.png` (the pixels at x = 0, 10, 20 and
  30 of its top row). A pixel's first colour byte decides: below 64 the
  first colour, below 96 the second, below 128 the third, else the fourth.
  Fully transparent pixels are left alone.
- Each camera shows a rectangle of the scene the size of its layout
  rectangle divided by 0.5: the left one starts at x = 30, the right one
  ends 20 short of the scene's right edge (x = 570 - width - 20). It draws
  the recoloured background and every figure tile that overlaps the
  rectangle.
- A press on a camera: the view slides to that camera's side
  (`panToSide`), the sound `border-pan` plays, and for 0.5 s the camera
  shows `BorderCamNoise.png` instead, at a new random position every frame
  (two draws per frame from the camera's own generator). While the noise
  shows, presses are ignored. (0.5 is the number handed to the game's
  "tweener" with the function to call; it is taken to be the duration in
  seconds, as for the delayed calls in part 3.)

## The endless scoreboard (`EndlessScoreboard`)

Created by the `Border` constructor in endless mode (part 2, step 8). It is
attached to the scene itself when `endlessScoreboardScrollWithBorder` is
true (desktop), otherwise to the layer that does not slide; its position is
`endlessScoreboardPos`, (180, 2) on desktop.

### What it is made of (desktop)

Drawn in this order: the background picture `EndlessScore.png` (180 x 11,
matching `kEndlessScoreboardWidth`), the style's icon, and three texts in
the font `fixed`, colour `B5B5B5`.

| Piece | Where (x within the scoreboard) | Shows |
|---|---|---|
| Icon | 33 | The style's `icon` picture from `Endlesses.xml` (8 x 8) |
| Clock | right edge at 91 | See below |
| Extra | left edge at 102 | The current points multiplier, with a sign: `+10` |
| Total | right edge at 177 | The score |

Vertically each is centred on the background's middle (5.5): the icon's top
is `floor(5.5 - icon height / 2)`, a text's top is
`floor(5.5 - font ascent / 2)`.

At the start the clock shows the formatted time 0, the total shows `0`, and
the remembered multiplier is 0 (so the first frame already counts as a
change, below).

The phone shape builds a different, wider strip (a 23 pixel high filled bar
across the screen); not read in detail.

### Every frame (`update`)

1. Ask the style's score scale for the multiplier at the run's clock time
   (`ScoreScale.getScale`, `endless-mode.md`). If it differs from the
   remembered one: remember it, set the extra text to it with a sign, and
   flash the extra text against blank.
2. The clock text: with no time limit, the run's time counting up; with a
   time limit, the time left (`limit - time`, not below 0). The format
   (`StringUtil.formatTime`) is whole seconds as `MM:SS`, with `HH:` in
   front when the hours are not 0, each part two digits. (The arithmetic
   inside was dropped by the decompiler; the shape is read from the string
   building, so the exact rounding is inferred.)
3. Step the three flashing texts with the run clock's `dt`.

### Notifications from the run (`Endless` to the scoreboard)

`Endless` holds one callback, `whenNotifyScoreboard`, which the scoreboard
sets to its own handler. Three messages exist:

| Message | Sent by | The scoreboard does |
|---|---|---|
| `ADD_SCORE(points)` | `Endless.handleAction`, after the score changes (also for negative points) | Total = the new score. Flash the total: the signed points (`+1`, `-5`) against blank |
| `LOSE_TIME(seconds)` | `handleAction`, when the action has a `time` value. The number is the action's `time` as written in the data | Flash the clock: the signed number against the clock's own text |
| `END_GAME` | `Endless.queEnd`, together with the foghorn and the 8 s countdown | Flash all three: blank against their own text |

Note on `LOSE_TIME`: the name says "lose", but it is sent for every action
with a `time` value, and the number is not negated. With the data, a
citation in the timed style (`time` -30) flashes `-30`, and a detention
(`time` 5) flashes `+5`.

### A flashing text (`FlashingScore`)

Each holds its real text, an anchor x (left or right edge, by the text's
alignment) and a centre y. `flash(a, b)` shows two texts in turn for 2
seconds: `a`, `b`, `a`, `b`, `a`, `b`, `a`, seven stretches of 2/7 s, then
the real text again. If `b` is not given, it is the real text at that
moment. Setting the real text during a flash is remembered but not shown
until the flash ends (so a flashing clock keeps showing the time from when
the flash started). After every change the text is re-aligned to its
anchor.

The seven stretches come from the code's two numbers (7 flashes, 2.0 s) and
were reproduced by the check's small model at 60 frames a second. The
remainder function used for the on-off decision is assumed to be `fmod`.

## The game's clock (`app.Clock`) and frame time

Answers the open point in parts 1 and 2.

- `dt` (the time step of a frame) = the system time now minus the system
  time at the previous frame, so **it varies from frame to frame**.
- It is capped at 0.1 s (`maxDeltaTime`): after a long stall the clock
  moves 0.1 s and the rest is dropped for good.
- System time is multiplied by a global speed, 1.0 unless changed (who
  changes it was not searched).
- **Exception:** if the static value `fixedFrameDelta` is not 0, every frame
  is exactly that long, whatever the real time. One writer was found: the
  test player's input class (`test.auto.AutoInput`) sets it to 1/20 s in its
  constructor. So runs of the test player advance 0.05 s of game time per
  frame. (Found by searching the decompiled files on disk for writes to the
  clock's static values; other writers in code not decompiled so far are
  possible.)
- A frame can also be given a forced `dt` by the caller of `Clock.update`
  (who does that was not followed).

## Random draws

None in panning or the scoreboard. The cameras draw twice per frame during
the 0.5 s after a press, from their own generators, and exist only on the
tablet layout.

## What this means for the port

- A desktop port needs no panning, no cameras and no slow motion. The view
  is the whole 570 x 103 scene at pan 0.
- The path events `pan-right`, `bomber-alarm` and `watch-poisoning` keep
  their other effects (part 2); their "view to the side" half does nothing
  on desktop.
- The hit box for shooting is 8 x 18.
- The scoreboard is small and fully specified above for desktop: three
  texts, three messages, one 2-second flash rule.
- Frame time: the original steps by real elapsed time, capped at 0.1 s.
  Anything that depends on frame boundaries (part 1's "events fire when a
  threshold is crossed") therefore differs slightly between runs of the
  original too. A port that wants repeatable behaviour can use a fixed
  step, as the game's own test player does (1/20 s).

## Results of the check

`python -I scripts\checks\border_events_check.py scripts\reference extracted\art\assets\data`
(run 2026-10-14) prints `problems: none`. Its new last section shows:

- Desktop: scene 570 x 103, window 570 wide, so the view can move by 0.
- The pictures the scoreboard and cameras name all exist:
  `EndlessScore.png` (180 x 11), `BorderCamNoise.png` (84 x 70),
  `BorderCamPalette.png` (40 x 10), and the three style icons (8 x 8 each).
- The font `fixed` is in `Fonts.xml`; the sound `border-pan` is in
  `Sounds.xml`.
- The flash model gives seven stretches, starting and ending on the flash
  text.

The check compares the data files with what the code asks for, and runs two
small models of what was read. It is not a comparison with the running game.

## Not known / not tested

- **Nothing was compared with the running game.** In particular "the desktop
  game has no panning, no cameras and no slow motion" rests on the code and
  the layout values only. The layout constructor writes a log line with the
  shape and sizes; it was not found in the saved logs of the test-player
  runs.
- Whether anything outside the `Layout` constructor fills in the camera
  rectangles later. In the decompiled files on disk (all booth and border
  classes) only `attachBorderCamsToBorder` and `BorderCam` use them, and
  neither writes them.
- The tablet and phone layout values, the phone branch of the scoreboard,
  and `BorderCamVisual.buildTiles` line by line.
- The two math helpers (sine in the bounce, remainder in the flash) are
  identified from how they are called, not from their code.
- `StringUtil.formatTime`'s arithmetic (see above).
- `app.vis.Text` (measuring and drawing text) is not read; the scoreboard's
  text positions depend on its `width` and on the font's ascent.
- Who creates `Endless` and when its clock starts.
