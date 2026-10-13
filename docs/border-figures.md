# The border scene, part 1: the figures and the waiting line

Studied on 2026-10-14. The border scene is the top view of the checkpoint:
the queue, the guards, the vehicles. This doc covers two of its classes:

- **`Person`**: one little figure (a queuing man, a guard, also the truck and
  the cars). It follows *paths* from `Paths.xml` (`paths-xml-format.md`).
- **`WaitingLine`**: the queue on the left, a list of `Person` figures.

Not covered: `Border` itself (who is created, the 36 path events, guards,
attacks, explosions), sniping, the camera, the scoreboard. Those are the
later parts of this step.

Check script: `scripts/checks/border_figures_check.py`. There is no reference
script for this part.

**Nothing here was compared with the running game.** Everything below was
read from the decompiled code unless it says "inferred".

Functions read in full: every `Person` and `WaitingLine` method except the
generated field-access ones (`__hx_getField` and the like), `CustomTile` (constructor, `init`, `stepAnim`, `restartAnim`,
`set_currentFrame`, `get_currentFrame`), `data.Path._getOnPath` and
`getDistForStop`, `app.Num.lerpScale`, `Border.addPerson`,
`Border.waitingLine_onArriveInBooth`, `Border.update`, the `DayScreen`
constructor, `Booth.attachBorderCamsToBorder`. Machine instructions were
read for `WaitingLine.advance`, `disperse`, `panic`, `poisonPanic`,
`rushWall` and `CustomTile.stepAnim`, because the decompiler dropped values
there. 20 number constants were read from the DLL.

## Which random generator the border scene uses

This was an open question. The answer:

- Each `Day` creates a generator called `borderRand` with the seed
  **day seed + 0x2000** (`days-csv-format.md`).
- The `DayScreen` constructor hands `day.borderRand` to the `Border` it
  creates. That is the only place in the code that creates a `Border`.
- `Border` hands the **same generator object** to the `WaitingLine` and to
  every `Person` it creates, and each `Person` hands it on when it asks the
  path library for a path. So the queue, the path points with a random
  spread, the idle fidgeting and `Border`'s own draws all take numbers from
  one generator, in the order they happen.
- The two border cameras (`BorderCam`) are the exception: each makes its own
  generator, seeded **day seed + 1** (left) and **day seed + 2** (right).
  They use it in one function (`tween_buttonPressed`, two draws; part 4).
- In all 314 border functions no other generator is created or used. (The
  bullet-hole order is a `ShuffledSequence` seeded by one draw from the
  border generator; part 2.)

**The draws depend on timing.** A standing figure makes one draw every 2 to
4 seconds of scene time (see "Each frame"), and the queue can hold 100
figures. So after the scene is built, the order of draws depends on how long
each frame took and on when the player acts. The first draws, made while the
scene is built, are in a fixed order (see "Building the line").

Not searched: whether anything outside the border classes uses `borderRand`.
In the decompiled files on disk only the `Day` constructor (writes it) and
the `DayScreen` constructor (reads it) name it.

## Words used below

- **Strip**: the row of pictures of one animation, for example `Man0-WalkH`.
  The name is the figure's *prefix* (`Man0`, `Target0`, ...) plus an ending
  from the animation. How a name finds its pictures is in
  `borderanim-xml-format.md`.
- **Frame**: one redraw of the screen. `dt` is the scene time since the
  previous frame, in seconds.
- **Stop**: a path can be divided into `numStops` equal parts. Stop `k` is at
  `min(1, k / numStops) x path length`. Only the waiting line uses more than
  one stop.
- **Feet position** (`pos`): where the figure is on the ground. The picture
  is drawn at `round(pos - (0, 7) + the animation's offset)`.

## A figure

Created with: the generator, a picture atlas, an id, a prefix, and an idle
strip ending (default `-Idle`).

On creation: the feet position is (-100, -100), the picture is at
(-1000, -1000) showing the idle strip, and **one draw** sets the strip speed
to `int(r x 5 + 5)` pictures per second. (Setting a path replaces that speed,
so the draw has no lasting effect once the figure has a path.) The figure has
no path yet, and a figure without a path does nothing each frame.

A figure reports events through one callback, `whenEvent(figure, text)`.
`Border.addPerson` points it at `Border.person_onEvent`; the waiting line
points it at its own handler.

### Giving a figure a path: `setPath(id, stops = 1, extra delay = 0)`

In this order:

1. If the figure has an **alternative prefix** and the id contains a `-`:
   replace everything before the first `-` with the alternative prefix, and
   use that id if such a path exists. (Only the queue's target figure has
   one: `waiting-line` becomes `target-line`.)
2. Remember whether the figure was dead, and the old path's `die` event.
3. Ask the path library for a **new copy** of the path, passing the
   generator: **two draws for every point with a random spread**.
4. Set the number of stops; target stop = 1; distance along the path = 0;
   "end event sent" = no.
5. Waiting time before moving = extra delay + the path's `delay`.
   Hold countdown = the path's `hold`.
6. Decide the mode:
   - no points, or `snap`: **stand** (no movement);
   - feet less than 1 unit from the first point: **follow the path**;
   - otherwise: **walk to the path** (straight to its first point).
7. If the waiting time is 0, switch to the path's animation now.
8. `snap`: put the feet on the path's first point. Otherwise, if `warp`: jump
   to stop 0 (see "Stops") and, if the path has points, set off for stop 1
   with the extra delay.
9. If the path has `face`: face left when it is `left`, right for anything
   else.
10. If the path has a `sound`, play it.
11. The figure is dead if the path's animation is a death animation. If it
    was alive before, is dead now, and the **old** path had a `die` event:
    send that event.
12. If the path has a `start` event, send it.

Note that steps 9 to 12 happen at once, even when the path has a delay.

### Each frame: `onEnterFrame(dt)`

Nothing happens without a path. Otherwise, in this order:

1. Remember the feet position as "previous position".
2. **Waiting time.** If it is above 0: lower it by `dt`, not below 0. If it
   just reached 0, switch to the path's animation. No movement this frame.
3. **Movement**, only when not waiting. Step = `dt x path speed`.
   - *Follow the path*: add the step to the distance. If the distance has
     reached the path length: **end the path** (below). Otherwise limit the
     distance to the target stop's distance and put the feet at that
     distance along the path.
   - *Walk to the path*: if the first point is closer than the step, put the
     feet on it and switch to *follow the path*; otherwise move the step
     straight towards it.
   - *Stand*: nothing.
4. **Direction and idling.** This step runs if the path's animation is
   `idle`, or if the path is not `snap`, has points and is at least 0.01
   long. Otherwise it is skipped (the figure keeps playing the path's
   animation on the spot).
   - If the feet moved since step 1 (more than 0.01 units): switch to the
     path's animation in its sideways form when the movement is more
     sideways than up-down, else its up-down form; if the path has no
     `face`, face left when moving left; reset the "motionless frames"
     counter.
   - If not: count a motionless frame. From the 4th in a row on: switch to
     the figure's idle strip if not already on it, stop animating, and run
     the **idle countdown**: lower it by `dt`; when it is used up, flip
     between idle pictures 0 and 1 and set the countdown to
     `2 + 2 x r` seconds (**one draw**).
5. **Animation.** If the strip is animating, advance it by `dt` (see
   "Strips"). If that made a non-repeating animation finish: on a `snap`
   path put the feet at the end of the path; then **end the path**.
6. **Hold.** If the hold countdown is above 0, lower it by `dt`; when it
   reaches 0 or less, **end the path**.
7. Place the picture from the feet position.

### Ending a path: `endPath()`

1. Distance = path length; if the path has points, feet = its last point.
2. If the path has an `end` event and it was not sent yet: mark it sent and
   send it.
3. If the figure's path has a `next`, set that path (`setPath(next)`).

Step 3 looks at the figure's path **after** the event was handled. If the
handler gave the figure a new path, that new path's `next` is what is used.
(The waiting line's handler does give a new path, `waiting-line`, which has
no `next`, so nothing follows.) Whether any `Border` handler runs into this
is a part 2 question.

A path with no `next` stays the figure's path. A figure that has arrived
keeps "ending" every frame, but the end event is sent only once.

### Stops

- `warpToStop(k)`: stand; target stop = `k`; put the feet at stop `k`. The
  facing and the sideways / up-down form come from the direction between the
  point 1 unit earlier on the path and the feet. Waiting time = the path's
  `delay`.
- `moveToStop(k, extra delay = 0)`: target stop = `k`; waiting time = extra
  delay + the path's `delay`; mode = *follow the path*.

### Strips (`CustomTile`)

- Switching animation: nothing happens if the animation and its form
  (sideways / up-down) are already the current ones. Otherwise the strip
  name becomes prefix + the animation's ending for that form; if the
  animation's sideways ending is `-Idle` (animations `idle` and
  `truck-stop`), the figure's own idle ending is used instead. The pictures
  are loaded again and the first one is shown. The animation's offset and
  its `death` mark are taken over, its sound is played if it has one.
- The strip animates if the animation's **sideways** speed is not 0; the
  speed used is the one for the current form.
- Advancing: picture number += `dt x speed`. Past the last picture, a
  repeating animation wraps around (the call there appears to be the C
  function `fmod`: inferred from its shape, not confirmed); a non-repeating
  one stays on its last picture and stops animating. That stop is what ends
  a path in step 5 above.
- A non-repeating animation is restarted from picture 0 when it is switched
  to. With speed 0 (for example `idle`) it then never finishes.

`Person.init()` and `Person.forceDirtyMatrixAndRecalculateSize()` are the
same code: both reload the strip's pictures. The decompiler shows that code
under the name `BorderCam.height`, because all three compile to identical
instructions.

### What the path attributes turn out to mean

`paths-xml-format.md` had these as inferred or not studied.

| Attribute | What the code does |
|---|---|
| `speed` | Units per second of scene time |
| `delay` | Seconds before the figure starts moving and before the path's animation starts. Events, sound and facing do not wait |
| `hold` | A timer started when the path is set (it also runs during `delay`). When it runs out the path ends, wherever the figure is: with points, the figure jumps to the last point |
| `snap` | Put the figure on the first point and do not move it. When a non-repeating animation finishes, the figure jumps to the last point. So a two-point `snap` path means "play this here, then appear there" |
| `warp` | Jump to the start of the path instead of walking to it, then follow it |
| `face` | Fixed facing for the whole path; without it the figure faces the way it moves |
| `start` | Event sent as soon as the path is set |
| `end` | Event sent once, when the path ends |
| `die` | Event sent when the figure is given a **death animation while on this path**. It is sent at the moment the next (death) path is set |

How a path can end, counted by the check script over all 309 paths:

| Way | Paths |
|---|---|
| The figure arrives | 123 |
| Hold runs out | 116 |
| Animation finishes | 53 |
| Arrives or animation finishes, whichever is first | 5 |
| Arrives or hold runs out | 1 |
| Never by itself | 11 |

None of the 11 that never end has a `next` or an `end` event, which fits
the reading above (it does not prove it).

### Two small helpers

- **Off screen** (`isOffscreen`): the picture's x is below 0 or above 570,
  or its y is below 0 or above 103.
- **Hit test** (`hitTestPoint`, used for shooting; part 3): a box of
  `Layout.borderPersonHitSize` centred on the picture position. A point
  counts as a hit if it is in the box now or in the box of the previous
  frame's position. The size's value was not looked up.

## The waiting line

Created by the `Border` constructor with the day's line length (`LINE` in
`Days.csv`: 100 on 14 days, down to 40) and "has a target" when the day has
the `BORDER_TARGET` feature (day 23 only, line of 70).

The list's **last** figure is the front of the queue; number 0 is the back.

### Building the line

For each of the `N` figures, number `i` from 0:

1. Create the figure: id `waiting`, prefix `Man0`. **1 draw.**
   With a target, figure number `N / 4` (rounded down) is instead id
   `waiting-target`, prefix `Target0`, alternative prefix `target`.
2. Point its events at the line.
3. `setPath("waiting-line", stops = N - 2)`. **12 draws** (six points with a
   random spread). The target gets `target-line`: same six corners, no
   spread, **0 draws**.
4. `warpToStop(min(i, N - 2))`.
5. Random idle start: **2 draws** (countdown = `r x 4` seconds; the second
   picks idle picture 0 or 1).

Then every figure gets one frame step of 0.1 seconds.

So a line costs 15 draws per ordinary figure and 3 for the target: 1,500
draws for a line of 100. Each figure has its own slightly different copy of
the path. Figures `N - 2` and `N - 1` both stand at the last stop.

### Moving up: `advance()`

Does nothing once the line has dispersed. Otherwise:

1. The front figure, if alive, gets the path `enter-left`: it walks to the
   booth door and, at the end, sends the event `arrived-in-booth`.
2. Every other living figure `i`, from the back: **1 draw**; it sets off for
   stop `i + 1` after `4 - 3 x i / (N - 1) + r` seconds. The back of the line
   starts moving last.

`Border` calls this from one callback set up in its constructor (when: part
2).

### Arriving in the booth

The line reacts to one event, `arrived-in-booth`:

1. The figure is taken out of the list and put back at position 0, the back.
2. It gets a fresh `waiting-line` path (**12 draws**; 0 for the target) and
   is placed at stop 0.
3. The line tells `Border`, which tells the booth to accept the next
   traveler.

So the queue is a ring: **the same `N` figures are used all day**, and the
line never gets shorter. The figure that walks in is not the traveler shown
in the booth; nothing here links the two.

### Leaving

In each of these, figures are handled from the back, dead figures are
skipped, and so are figures already on a path of that kind. The path number
is always `int(r x 3)`: 0, 1 or 2.

| What | When (caller) | Per figure, draws in this order |
|---|---|---|
| `disperse()` | Once, when the booth's time is up; the foghorn sound plays (`Border.update`). After this `advance()` does nothing | path number; delay = `2 + 5 x r` s. Path `disperse-<n>` (walk off to the left) |
| `panic()` | `Border.panic` | delay = `2 x r` s, plus 2 s if the prefix contains `Target`; path number. Path `panic-<n>` (run off to the left) |
| `poisonPanic(pos)` | `Border.person_onEvent` | See below |
| `rushWall()` | A `Border` callback | x = `r x 295 - 300`; y = `r x 70 + 25`; path number; delay = `2 x r` s; then 6 draws for the path's points. The figure is moved to (x, y) first, off to the left, then runs path `rush-<n>` |

`panic()` and `poisonPanic()` play the sound `crowd-panic`, but only the
first time either is called on a line.

`poisonPanic(pos)`: let `d2` be the **squared** distance from `pos` to the
figure's feet (no square root is taken).

- If `d2 < 20`: one draw; below 0.5 the figure collapses: one more draw,
  path `panic-poisoned` after `2 x r` seconds.
- Otherwise, and also when that draw was 0.5 or more: path number; then
  delay = `3 x (d2 - 10) / 90` limited to 0..3 seconds, plus `0.5 x r`. Path
  `panic-<n>`.

### Who steps the figures

`Border.update`, every frame: first its own clock (`dt` = the game clock's
`dt` x a time scale; a "pause for one frame" switch exists), then its state
machine and the explosion picture (part 2), then the line's figures from the
back, then the figures in `Border`'s own list, in list order. The line's
figures are not in `Border`'s list.

## What this means for the port

- One generator for the whole border scene, seeded day seed + 0x2000, plus
  one per camera.
- The 1,500 or so draws that build the line happen in a fixed order, so the
  starting picture can match the original. After that the draws follow real
  time, so the original itself does not play the border scene the same way
  twice. Whether anything that matters to play draws from this generator
  later is a part 2 question.
- Figures move by `dt x speed` each frame and events fire when a threshold
  is crossed, so the scene's timing depends slightly on the frame rate.
- One path (`guard1-waitforchat`) is a `warp` path whose two points are the
  same spot. Working out its direction divides by zero; the result is "not a
  number", which the comparisons treat as "not sideways, not left", and the
  path's `face="left"` then sets the facing. A port must give the same
  result without failing.

## Results of the check

`python -I scripts\checks\border_figures_check.py scripts\reference extracted\art\assets\data`
(run 2026-10-14) prints `problems: none`, and:

- All 12 paths the line names exist; the code can pick numbers 0 to 2 and
  the data has exactly `-0`, `-1`, `-2` of each kind.
- Draws on creation: `waiting-line` 12, each `rush-` path 6, the others 0.
- `enter-left` is the only path ending in `arrived-in-booth`.
- The target's only alternative path is `target-line`.
- All 21 `warp` and all 29 `snap` paths have points (the code would fail on
  one without). No path has both.
- `face` is only ever `left` (15) or `right` (11).
- No animation is still sideways but moving up-down (it would never play).

## Not known / not tested

- Nothing was compared with the running game. The game's log
  (`comparing-with-the-game.md`) was not checked for border lines.
- Whether the game's `dt` varies from frame to frame (`app.Clock` not read).
- The rounding function used to place the picture (`Math.round`) was not
  read.
- Which picture a queue figure shows in its first few frames: the idle start
  draw sets a picture number, but the pictures are then reloaded and the
  walk animation's speed is still in effect for 4 frames. The draws are
  certain; the exact first pictures are not worked out.
- `Endless.csv` leaves `LINE` blank in four columns; what length that gives
  was not followed.
- Whether a line shorter than 3 can happen. `Days.csv` never has one. The
  code would divide by zero stops (2 figures) or fail in `advance()` (none).
- `Atlas.getSequence` (how a strip name finds its pictures) was not re-read
  here; `borderanim-xml-format.md` covers it.
