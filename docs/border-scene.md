# The border scene, part 2: `Border`

Studied on 2026-10-14. `Border` is the class that runs the top view of the
checkpoint: it owns the figures, decides when the next person is called in,
starts the attacks, reacts to what the figures report, and ends the day.

Part 1 (`border-figures.md`) explains how one figure follows a path and how
the waiting line works. Read that first: this doc uses its words (path, stop,
strip, event).

Not covered here: shooting (`snipe`, `checkSniped`, the rifle buttons, the
grenade's flight, the test player's aiming helpers), which is part 3; the
cameras, panning and the endless scoreboard, which are part 4.

Check script: `scripts/checks/border_events_check.py`.

**Nothing here was compared with the running game.** Everything was read from
the decompiled code unless it says "inferred".

Functions read in full: the `Border` constructor; every callback function
`Border` creates, except the three used by the test player's aiming;
`addPerson`,
`booth_onTravelerLeaves`, `booth_onDetainStart`, `booth_onDetaineeLeaves`,
`checkEnemiesDead`, `getFreeLeavingPerson`, `makeEnemy`, `makeStash`,
`restoreFromStash`, `outerBoothButton_onClick`, `panic`,
`panicLeavingPersonRight`, `pauseForOneFrame`, `person_onEvent`,
`playAlarmSound`, `prepareForAttack`, `resetLeavingPeopleAndEnemies`, the
seven `send...` functions, `set_snipingEnabled`, `set_trafficEnabled`,
`showPersonSpeech`, `spawnExplosion`, `standDownRightGuards`,
`grenade_onHit`, `throwGrenade`, `update`, `waitingLine_onArriveInBooth`; the
state machine classes `app.Stater` (`go`, `step`) and `app.State`
(`addFunc`, `enter`, `step`, `exit`, `setDuration`); seven `Booth` methods
that `Border` calls. Machine instructions were read where the decompiler
dropped values: the end of the constructor, the attack delay, the
announcement text. 23 number constants were read from the DLL.

## The figures `Border` owns

Created in the constructor, in this order. Each costs **one draw** (the
figure's strip speed, see part 1). `Border` keeps them all in one list and
steps them in this order every frame, after the waiting line.

| Id | Strip prefix | Idle ending | Notes |
|---|---|---|---|
| `guard0` | `Guard0` | `-IdleB` | left side |
| `guard1` | `Guard0` | `-Idle` | left side |
| `guard2` | `Guard0` | `-Idle` | right side |
| `guard3` | `Guard0` | `-IdleB` | right side |
| `guard4` | `Guard1` if the day has the friendly guard, else `Guard0` | `-Idle` | right side |
| `runner` | `Man0` | `-Idle` | the person who runs for it in an attack |
| `truck` | `Truck` | `-Idle` | |
| `leaving` x 10 | `Man0` | `-Idle` | a pool; each starts on the path `leaving-free` |
| `traffic` | `CarA` | `Drive` | the passing car |
| `bosscar` | `BossCar` | `-Idle` | |

("Left" and "right" for the guards are from the path names and from which
ones `panic` and `standDownRightGuards` touch; the coordinates were not
plotted.)

Created later, when first needed, also one draw each: enemies (`makeEnemy`,
strip prefix `Enemy`), with ids `enemy0`, `enemy1`, `bike0`, `bike1`.

Two pools are reused instead of creating new figures:

- **Leaving people.** `getFreeLeavingPerson()` returns the first of the ten
  whose path is `leaving-free`. If none is free it picks one at random
  (**one draw**), busy or not.
- **Enemies.** `makeEnemy(id)` returns the first enemy whose path is
  `enemy-free`, **keeping its old id**, and only creates a new one when none
  is free.

`resetLeavingPeopleAndEnemies()` puts all of both pools back on their free
paths (and refills the rifles: 2 bullets, 3 tranquilliser darts).

On days with jailors (`J` in the `GUARDS` cell), `guard0` and `guard1` get
the alternative prefixes `jailor0` and `jailor1` (part 1, "Giving a figure a
path"). 4 of `guard0`'s 12 reachable named paths and 6 of `guard1`'s 16 have
a jailor twin; the rest are shared.

### `setPath(...)` followed by `moveToStop(1)`

This pair appears many times. Plain `setPath` would make a figure standing
elsewhere walk to the path's first point. `moveToStop(1)` right after it
switches the figure straight to "follow the path", so it starts **on** the
path once the path's delay has passed. Until then it stays where it was (for
a pool figure, off screen at -20, -20).

## Construction, in order

Only the steps that matter for logic and for the random draws:

1. Hook three booth callbacks: traveler leaves, detain starts, detainee
   leaves.
2. Pictures: background, the truck wreck and the bombed wall (both hidden),
   the two rifle buttons.
3. **The waiting line** (part 1): 15 draws per figure, 3 for a target.
4. The explosion picture (`Boom`, 10 pictures per second, hidden).
5. The figures in the table above: **19 draws**, plus **one draw** in the
   middle for the passing car's first path: `traffic<int(r x 4)>-wait`, made
   after the `traffic` figure and before `bosscar`.
6. The scene's own clock (time scale 1), the pan control, the booth button,
   two speech bubbles, the white flash.
7. **One whole-number draw** seeds the bullet-hole order (a shuffled run of
   4; part 3).
8. The endless scoreboard, in endless mode.
9. The booth's two border cameras (part 4).
10. The state machine (below).
11. Guards on duty. For each bit set in the day's guard flags, the guard gets
    `guard<n>-enter` and `moveToStop(1)`. Two exceptions: `guard1` gets
    `guard1-waitforchat` when the next traveler is the chatty prison guard;
    `guard4` gets `guard4-enterchat` when the friendly guard is in his
    "chat" state.
12. If the day has the boss: `sendBoss()` (below).
13. Start: state `off`, and a free leaving figure gets `enter-right` (it walks
    in from the right; the path's end event is `start-intro`). With the debug
    switch "skip slow stuff" the event `start-intro` is sent at once instead,
    and if the day is a traveler test the state goes to `calling-next`.

None of the paths in steps 11 to 13 has points with a random spread, so they
cost no draws. Only `waiting-line` and the three `rush-` paths do.

## The state machine

`Border` uses the game's general state machine (`app.Stater`). A state has a
name and a list of functions, each with a time:

| Time | When it runs |
|---|---|
| `ENTER` | once, when the state is entered |
| `STEP` | every frame while in the state |
| `AT_STEP(t)` | once, on the first frame where the time in the state has reached `t` seconds |
| `EXIT` | once, when the state is left |

A state can also have a duration and a follow-on state. `go(name)` runs the
old state's `EXIT` functions, then the new state's `ENTER` functions. The
time in a state is counted with the scene's own clock, which sniping slows
down (`set_snipingEnabled`).

`Border.update` steps the state machine every frame, before the figures.

| State | What happens |
|---|---|
| `off` | Every frame: on a boss day, keep the view on the boss (and on his car for the first 3 s) |
| `waiting-for-chat` | The same code as `off` |
| `ready-to-call` | The booth button can be clicked and blinks (highlight for 0.375 s of every 0.75 s). The tutorial can block it. On leaving: button back to normal |
| `calling-next` | On entering: tell the booth (`onCallingNextTraveler`), play `speech-announce`, show the text `border_next`. After 1 s: the waiting line moves up (`advance()`), or, if the next traveler is the chatty prison guard, `guard1` walks in (`guard1-enterchat-midday`) |
| `inspecting` | On entering: maybe schedule the day's attack (below). Every frame: when the booth is ready for the next traveler, go to `ready-to-call` |
| `runner`, `truckwreck`, `bikeattack`, `bikerunner` | The four attack scenes (below) |
| `poisoning` | On entering: mark the day as having had a poisoning; the booth goes "busy with border", watching only |
| `waiting-to-fade-to-night` | Lasts 5 s, then `fade-to-night` |
| `fade-to-night` | On entering: end the day (below) |

### The normal cycle

1. `ready-to-call`: the player clicks the booth button; if the booth is
   ready, go to `calling-next`.
2. `calling-next`: after 1 s the line moves up and its front figure walks to
   the door.
3. That figure's path ends with `arrived-in-booth`. The line puts the figure
   back at the far end and tells `Border`, which tells the booth to accept
   the next traveler and, unless an attack is pending, goes to `inspecting`.
4. `inspecting`: when the booth reports it is ready again, back to
   `ready-to-call`.

"The booth is ready" (`Booth.get_readyForNextTraveler`) means: the booth's
own state is `empty` or `intro`, time is not up, and in endless mode the
end countdown is not running.

### The booth button outside those states

- After the line has dispersed: `speech-announce` and the text
  `border_comeback`.
- Booth not ready, state `inspecting`, bubble not showing: `speech-announce`
  and one of `border_announce0`, `1`, `2`, chosen by **one draw**
  (`int(r x 3)`).

## The start of the day

The event `start-intro` (from the walk-in, step 13 above):

1. The booth starts its intro (instantly if the first traveler is the secret
   police).
2. First traveler is the secret police: state `inspecting`.
   Otherwise, friendly guard in "chat" state or a boss day:
   `waiting-for-chat`. Otherwise: `ready-to-call`.

## When the traveler leaves the booth

The booth calls `booth_onTravelerLeaves(direction)`. A free leaving figure
`p` is fetched first in every case.

| Direction | What happens |
|---|---|
| `left` | `p` gets `exit-left` |
| `right` | `p` gets `exit-right` |
| `right-bomb` | `p` gets `exit-right-bomb` |
| `right-poisoned`, `left-poisoned` | `p` gets `exit-right-poisoned` / `exit-left-poisoned` |
| `left-killer` | `p` gets `exit-left-killer` |
| `left-timebomber` | state `waiting-for-chat`; `guard1` gets `guard1-enterchat-timebomb`; `p` gets `exit-left-timebomber` |
| `right-boss` | the boss car gets `bosscar-exit`; `p` gets `boss-exit` |
| `right-guard` | `guard4` gets `guard4-exitchat` (`p` gets no path) |
| `left-guard` | `guard1` gets `guard1-exitchat` (`p` gets no path) |
| `right-elisa` | With the friendly guard: `guard4` is put at the end of `guard4-enter`, `p` gets `exit-right-elisa`, then `guard4` gets `guard4-elisa-reunite`. Without him: `p` gets `exit-right` |
| anything else | `p` gets a path **named by the direction text itself** |

Then `p.moveToStop(1)` in every case.

The chains started by `exit-left`, `exit-right`, `exit-left-killer`,
`exit-left-timebomber`, `exit-right-elisa`, `boss-enter` and `boss-exit` end
on `leaving-free`, which returns the figure to the pool. The poisoned, bomb
and detained ones do not; they are freed by `resetLeavingPeopleAndEnemies()`.

## Detaining

- `booth_onDetainStart(resisting)`: `guard0` and `guard1` get
  `guard<n>-detainstart`, or `guard<n>-resiststart` when the traveler
  resists.
- Event `detain-guards-waiting-outside`: the booth goes to its `detaining`
  state.
- `booth_onDetaineeLeaves(resisting)`: if not resisting, a free leaving
  figure gets `entrant-detainstart`.
- Event `detain-entrant-waiting-outside`: 1 s later that figure gets
  `entrant-detainfinish`, and each of `guard0` / `guard1` whose path name
  contains `detainstart` gets `guard<n>-detainfinish`.
- Event `detain-say-out`: `guard0` "says" the text `border_guardout`, with
  the sound `speech-out`.

## The end of the day

- **Time up.** `Border.update` checks `Booth.get_timeIsUp` every frame. The
  first time it is true: the foghorn plays and the line disperses (part 1).
  Time is up when: story mode, **the day has no attack**, the booth has seen
  at least the day's scripted number of travelers, and the booth clock has
  passed the day's length. So a day with an attack does not end by the
  clock; it ends through the attack.
- **`waiting-to-fade-to-night`** is entered by: an attack being over
  (`checkEnemiesDead`), an explosion that ends the day, and the events
  `finish-poisoning` and `poisoned-left-panic`. Five seconds later:
- **`fade-to-night`**: if the day has the friendly guard and `guard4` is
  dead, the day records his death. Then, by the day's attack result:

  | Attack result | Goes to |
  |---|---|
  | hit an innocent | ending `killed-innocent`, or `tranqed-innocent` |
  | hit a guard | ending `killed-guard`, or `tranqed-guard` |
  | hit the target | ending `killed-target`, or `tranqed-target` |
  | anything else | the night screen |

  (The ending ids are in `ends-xml-format.md`. How the result is set is
  part 3.)

Who moves from the booth's "day over" to this state when there was no attack
was not followed (it is on the booth side; `get_isWaitingToFadeToNight` is
there for someone to ask).

## Attacks

### When an attack starts

On entering `inspecting`: if no attack is pending, the day has made **more
travelers than its scripted number**, and the day's `ATTACK` is not `NONE`,
then the matching function below is scheduled **`6 + 4 x r` seconds later
(one draw)** and "attack pending" is set. While it is pending, an arriving
traveler no longer moves the state to `inspecting`.

| `ATTACK` | Function | State | Days |
|---|---|---|---|
| `RUNNER` | `sendRunner` | `runner` | 2, 18 |
| `RUNNERSHOT` | `sendRunnerShot` | `runner`, with "guards stop the attacker early" | 16, 23 |
| `BIKE` | `sendBikeAttack` | `bikeattack` | 21 |
| `BIKESHOT` | `sendBikeAttackShot` | `bikeattack`, with "guards stop the attacker early" | 28 |
| `BIKERUNNER` | `sendBikeRunner` | `bikerunner` | 26 |
| `TRUCK` | `sendTruck` | `truckwreck` | 31 |

So the border generator decides something the player can feel: how long
after the extra traveler steps in the attack begins.

### The four attack scenes

"Alarm off / on" refers to the alarm rule below. `prepareForAttack` puts all
five guards at the end of their `-enter` paths and makes them visible
(whatever the day's guard flags say), stops the passing car and hides the
explosion picture.

**`runner`**

| When | What |
|---|---|
| Enter | Hide the explosion. Guards on duty: `guard2-runner`; `guard3-runner` (or `guard3-runnerkill` when guards stop the attacker early); `guard4-runner`. The runner gets `runforit`. Alarm off |
| 3 s | Sniping on. Booth "busy with border". Alarm on |
| Every frame | Alarm. After 3 s: check whether the attack is over. Unless the day has a border target: keep the view on the runner |
| Exit | Right-side guards stand down |

**`truckwreck`**

| When | What |
|---|---|
| Enter | Sound `border-truckwreck`. `prepareForAttack`. Wreck and bombed wall hidden. Alarm off. Sniping off |
| 1 s | Truck: `truck-enter`. Guards: `truckg2-start`, `truckg3-start`, `truckg4-start`. Enemies `enemy0` and `enemy1`: `trucke0-start`, `trucke1-start`. Booth "busy with border" |
| 4 s | Passing car back on. Alarm on. Panic |
| 11 s | Sniping on |
| 40 s | `fade-to-night` directly |
| Every frame (from 1 s) | Reveal the wreck picture behind the truck (visible from 1.1 s). Alarm. After 15 s: check whether the attack is over. Keep the view on the enemies or the truck |

**`bikeattack`**

| When | What |
|---|---|
| Enter | `prepareForAttack`. Enemy `enemy0`: `enemy-bikeattack-start`. Guards: `g2ba-start`, `g3ba-start`, `g4ba-start` (or `g4ba-startkill` when guards stop the attacker early). Alarm off |
| 4.5 s | Panic |
| 5 s | Sniping on. Booth "busy with border". Alarm on |
| Every frame | Alarm. After 3 s: check whether the attack is over. Keep the view on `enemy0` |

**`bikerunner`**

| When | What |
|---|---|
| Enter | `prepareForAttack`. Enemies: `enemy0-bikerunner-start`, `enemy1-bikerunner-start`. Runner: `runner-bikerunner-start`. Guards: `g2br-start`, `g3br-start`, `g4br-start`. Alarm off |
| 3 s | Panic. Sniping on. Booth "busy with border". Alarm on |
| Every frame | Alarm. After 3 s: check whether the attack is over. Keep the view on `enemy1` |

What the figures then do (walk, shoot, throw, die) is entirely in the path
chains of `Paths.xml` and the events below.

### Shared pieces

- **Alarm** (`playAlarmSound`): plays `border-alarm` when more than 1.8 s of
  state time have passed since it last played, and each time also sends any
  leaving figure on `exit-right` running (`exit-right-panic`). "Alarm off"
  sets the last-played time to 1000 so it cannot play; "alarm on" sets it to
  -1000 so it plays at once.
- **Is the attack over?** (`checkEnemiesDead`): yes when the runner is dead
  or off screen, **and** every enemy is dead, off screen, or has `bike` in
  its id. Then the right-side guards stand down and the state becomes
  `waiting-to-fade-to-night`.
- **Standing down** (`standDownRightGuards`): 1 s later, each of `guard2`,
  `guard3`, `guard4` that is alive and on screen gets
  `guard-afterattack-kneel` if its current animation name contains `kneel`,
  else `guard-afterattack-stand`, after a delay of `1 + r` seconds (**one
  draw each**).
- **Panic** (`panic`), once per day: without jailors, guards 0 and 1 on duty
  get `guard<n>-panic`; the line panics (part 1); leaving figures on
  `exit-right` get `exit-right-panic` and those on `exit-left` get `panic-2`.
- **Explosion** (`spawnExplosion(pos, kill guards and end the day = yes)`):
  show the explosion at `pos`, shake the screen, start the white flash,
  panic, sound `border-boom`. Every living enemy within 30 units gets
  `enemy-grenaded`. With "kill guards and end the day": 0.1 s later guards
  2, 3 and 4 on duty get `guard<n>-grenaded`; the friendly guard is recorded
  as killed; state `waiting-to-fade-to-night`.
- **A grenade lands** (`grenade_onHit`): if it lands on the booth button's
  rectangle: sound `grenade-roll`, and 2 s later `booth-boom` and a flash to
  the title screen. Anywhere else: an explosion 10 units above the landing
  point, which kills the guards and ends the day.
- **Sniping on** (`set_snipingEnabled(true)`): does nothing unless the day
  has the `SNIPING` feature. Records the attack result "failed, did
  nothing" on the day (through a function named "set with priority", not
  read), slows the scene's clock to the layout's sniping time scale, and
  moves the rifle buttons from their `OFF` state to `LOCKED`, the second one
  0.5 s after the first (part 3).

## What each path event does

`Paths.xml` uses 36 different event texts. All 36 are handled, and nothing
in the code waits for an event the data never sends (checked by the script).
`arrived-in-booth` belongs to the waiting line (part 1); the rest are
`Border.person_onEvent`:

| Event | What happens |
|---|---|
| `start-intro` | See "The start of the day" |
| `start-chat` | Forget the boss figure; the booth accepts the next traveler |
| `end-chat` | State `ready-to-call` |
| `detain-say-out`, `detain-guards-waiting-outside`, `detain-entrant-waiting-outside` | See "Detaining" |
| `bomber-alarm` | View to the right. The day records "had a bomber". Booth "busy with border" |
| `bomber-explode` | The figure "says" `border_bomber` (sound `speech-bomber`). 2 s later it disappears and an explosion goes off 18 units above it, which kills the guards and ends the day |
| `throw-grenade` | 0.75 s later a grenade leaves from 4 right and 8 above the figure, with speed (60, -50) |
| `throw-grenade-underhand` | 1 s later a grenade leaves from 4 left of the figure, with speed (-40, -20) |
| `truck-planted-wall` | Story fact `Game/WallDestroyed` = `SOON` |
| `truck-blow-wall` | Explosion at (180, 26) that does **not** end the day. The bombed wall is shown. `Game/WallDestroyed` = `YES`. 2 s later the line rushes the wall (part 1) and the explosion picture is hidden |
| `trucke0-die` | If the second enemy is alive and on `trucke1-waiting`, it gets `enemy-throw-grenade-underhand` |
| `trucke1-decide` | If the first enemy is alive **and** the story fact `Game/HelpedEzic` is `YES`: nothing. Otherwise this figure gets `enemy-throw-grenade-underhand` |
| `watch-poisoning` | View to the side the figure is on (left if its picture is left of 170). State `poisoning` |
| `poisoned-right-send-guard` | `guard3` gets `guard-right-poisoned` and its idle strip becomes `-Idle` |
| `poisoned-left-panic` | The line panics around this figure (`poisonPanic`, part 1). State `waiting-to-fade-to-night` |
| `finish-poisoning` | State `waiting-to-fade-to-night` |
| `finish-boss` | The passing car is switched back on |
| `park-bike` | An enemy figure (`bike0` if the sender is `enemy0`, else `bike1`) gets `bike-parked` and is put where the sender stands. (The data file's comment on that path says the same: "position is overriden in code") |
| `call-elisa` | The figure "says" `border_elisa`, no sound |
| `pan-right` | View to the right |
| `spawn-explosion <x> <y>` | Explosion at the figure's position plus the offset; does not end the day. (One use: `bike-explode`, offset `5 -20`) |
| `tell <id> <path>` | Every living figure in `Border`'s list with that id gets that path. 12 different ones in the data, all naming a real id and a real path |

"Says" (`showPersonSpeech`) puts a speech bubble above the figure.

### One oddity: an end event that changes the same figure's path

Part 1 noted that `endPath` follows the `next` of whatever path the figure
has **after** its end event was handled. One case in the data runs into it:
`trucke1-waiting` ends with `trucke1-decide`, whose handler gives the same
figure `enemy-throw-grenade-underhand`. That path's `next` is
`enemy-throw-grenade-after`, so the figure is moved on to it at once. The
grenade is still thrown (the throw is the path's **start** event), but the
throwing animation would be replaced by the idle one in the same frame. When
the same path is reached the other two ways (`trucke0-die`, or as an
ordinary `next`), the animation plays in full. This is what the code says;
it was not watched in the game.

## The boss, the passing car

- `sendBoss()` (from the constructor on a boss day): passing car off; a free
  leaving figure becomes "the boss" and gets `boss-enter`; the boss car gets
  `bosscar-enter`; state `waiting-for-chat`.
- `set_trafficEnabled(true)`: the car gets `traffic0` (the traffic paths
  chain into each other). `false`: the car gets `traffic-stop`.

## Saving and restoring

`makeStash()` saves **one number**: the pan position. Nothing about figures,
states or the generator.

`restoreFromStash(s)`: free both pools and refill the rifles; state
`ready-to-call` at once; hide the call bubble; put each guard on duty at the
end of its `-enter` path; restore the pan. So after a restore the scene is
rebuilt in its plain "waiting" form. (When a stash is made and restored is
on the screen side; not followed.)

## What `Border` asks of the booth and the day

| Call | What it does (read from `Booth`) |
|---|---|
| `Booth.startIntro()` | Booth state `intro`, or `intro-instant` when the first traveler is the secret police |
| `Booth.onCallingNextTraveler()` | On the first call of the day (unless the chatty prison guard is next): start the booth clock and the endless timer. Always: put loose desk items away |
| `Booth.acceptNextTraveler()` | Booth state `empty` becomes `entering` |
| `Booth.get_readyForNextTraveler` | See "The normal cycle" |
| `Booth.get_timeIsUp` | See "The end of the day" |
| `Booth.goBusyWithBorder(watching only)` | Booth state `busy-with-border` |
| `Booth.onGuardsReadyToDetain()` | Booth state `detaining` |

From the day `Border` reads: line length, features, guard flags, jailors,
boss, friendly guard, attack, scripted and made traveler counts, attack
result, and whether the next or first traveler is one of the special ones.
It writes: "had a bomber", "had a poisoning", the friendly guard's death,
the attack result (through sniping), and the story fact `Game/WallDestroyed`.

## Every random draw `Border` makes

All from the day's border generator (part 1).

| When | Draws |
|---|---|
| Construction | the line (15 per figure); 19 figures; 1 for the car's first path; 1 whole number for the bullet holes. Fixed order |
| Entering `inspecting` with an attack due | 1: the attack's delay |
| Booth button while inspecting | 1: which announcement |
| A new enemy figure | 1 |
| No free leaving figure | 1 |
| Guards standing down | 1 per guard |
| The line: moving up, a figure arriving, dispersing, panic, rushing | part 1 |
| Every standing figure | 1 every 2 to 4 s (part 1) |

## What this means for the port

- The scene is a state machine plus path scripts. Almost all of an attack's
  choreography is data (`Paths.xml`); the code only starts the first paths
  and reacts to about two dozen events.
- Because idle figures draw from the same generator as the attack delay and
  the announcement, the original's attack timing is not reproducible from
  the seed alone. The port can use any fair draw for the `6 + 4 x r` delay;
  matching the original draw for draw is not possible even in principle
  unless frame times are identical.
- The same ten leaving figures and the same few enemy figures are reused; a
  reused enemy keeps its first id, which matters for `tell <id> ...` events.
- A day with an attack has no time limit.

## Results of the check

`python -I scripts\checks\border_events_check.py scripts\reference extracted\art\assets\data`
(run 2026-10-14) prints `problems: none`, and:

- All 76 path names in the `Border` code exist in `Paths.xml`.
- All 36 event texts in the data are handled; all 23 exact event names the
  code tests for are sent by some path.
- The 12 `tell` events all name a figure id `Border` creates and a path that
  exists; the one `spawn-explosion` has a two-number offset.
- One path (unnamed, the first after `trucke0-start`) has an empty `die`
  text. The code treats that as an event that matches nothing.
- All 8 texts and 11 sounds `Border` names exist in `Text.xml` and
  `Sounds.xml`.
- Attack days: 2, 16, 18, 21, 23, 26, 28, 31.

## Not known / not tested

- Nothing was compared with the running game.
- Part 3: shooting, the grenade's flight, how the attack result is set,
  `getPersonIsNearGuards`, the test player's aiming helpers.
- Part 4: `BorderPan`, the cameras, `panToPeople`'s offsets (two were
  dropped by the decompiler in the bike scenes), the endless scoreboard.
- The booth's own state machine (`empty`, `entering`, `intro`,
  `busy-with-border`, `detaining`...) is only described where `Border`
  touches it.
- Who sends the scene to `waiting-to-fade-to-night` on a day that ends by
  the clock.
- When the scene is stashed and restored.
- The "tweener" used for the delayed calls (1 s, 2 s, the attack delay): it
  was not read, so whether its delays run on the scene's slowed clock or on
  real time is not known.
- `Chip` (the picture class): the byte the code sets to make a figure
  visible was taken to be `visible` from its use; the class was not read.
- `ArrayUtil.makeShuffled` (bullet-hole order) was not read here.
