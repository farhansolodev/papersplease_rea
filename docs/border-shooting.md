# The border scene, part 3: shooting

Studied on 2026-10-14. During an attack the player can unlock a rifle and
shoot at the figures in the top view. This doc covers the rifle buttons, a
shot, how the day's "attack result" is decided, bullet holes, the grenade's
flight, the slow motion, and the helpers the game's test player uses to aim.

It builds on part 1 (`border-figures.md`: figures, paths, the hit test) and
part 2 (`border-scene.md`: the attack scenes, explosions, how the day ends).

Not covered: the cameras, panning and the endless scoreboard (part 4,
`border-view.md`).

Check: section 8 of `scripts/checks/border_events_check.py`.

**Nothing here was compared with the running game.** Everything was read from
the decompiled code unless it says "inferred".

Functions read in full: `Border.snipe`, `checkSniped`, `react`,
`getSelectedRifleButton`, `rifleButton_onClick`, `set_snipingEnabled` and its
delayed part, `getPersonIsNearGuards`, `debugSnipeAll`,
`autoGetLivingTargetPerson` with its three tests, `autoGetNextSnipeWorldPoint`,
`autoIsAttackUnderway`; `RifleButton` (`react`, `set_state`, `set_selected`,
`set_numBullets`, `update`, its four sound callbacks, and the state set-up
in its constructor; the picture layout in the constructor was skimmed);
`Grenade` (`throwFrom`, `step`); `Day.setAttackResultWithPriority`,
`Day.killFriendlyGuard`, `Day.get_hasFriendlyGuard`; `ArrayUtil.makeShuffled`;
`Tweener.timer`, `Tween.step`, `Ent.tweener`, and the part of
`Trunk.treeUpdate` that steps them. Machine instructions were read for the
rifle's unlocking time. 5 more number constants were read from the DLL.

## When the player can shoot

Three things are needed:

1. **The day has the `SNIPING` feature** (from day 16). Without it
   `set_snipingEnabled` does nothing. Day 2 has an attack but no sniping: the
   scene simply plays out.
2. **The attack scene has switched sniping on** (part 2: 3 s into `runner`
   and `bikerunner`, 5 s into `bikeattack`, 11 s into `truckwreck`). That
   moves the tranquilliser button from `OFF` to `LOCKED`, and the kill button
   0.5 s later, and sets the scene's time scale (below; on desktop that
   changes nothing).
3. **A rifle is unlocked with its key and selected.**

## The two rifle buttons

| | Tranquilliser | Kill |
|---|---|---|
| Created with | `Tranq`, 3 shots | `Kill`, 2 shots |
| Shot sound | `border-tranqshot` | `border-gunshot` |
| Key (a desk paper) | `KeyTranq` | `KeyKill` |
| Path given to a figure it hits | `tranq` | `shot` |

`KeyTranq` is handed out by the `PAPERS` row of `Days.csv` on day 16;
`KeyKill` comes from a traveler script (`Travelers.txt`). Both are papers
that stay for the rest of the game (`Facts.xml`).

Each button has its own small state machine:

| State | What the player sees and can do |
|---|---|
| `OFF` | Out of view |
| `LOCKED` | Slides in (sound `button-drop`). Dragging the right key over it shows the key in the lock (sound `rifle-keyinsert`); dragging it away takes it out again (same sound). Letting go with the key in: `UNLOCKING` |
| `UNLOCKING` | Sound `rifle-unlock`, the key is shown turned. 0.5 s later: `UNLOCKED` |
| `UNLOCKED` | The rifle is out (sound `booth-intro`). Clicking the lock puts it away (`DOCKED`). Clicking the rifle, if it is not the selected one, selects it |
| `DOCKED` | Put away (sound `booth-intro`). Clicking the lock brings it back (`UNLOCKED`) |

Selecting a rifle deselects the other and plays `rifle-cock`. Each rifle
has a scope cursor picture that is passed along when the scene tests for a
press; how it is shown was not read. `resetLeavingPeopleAndEnemies` (part 2)
refills them to 2 and 3 shots.

What happens to the key paper after unlocking was not followed (it is
hidden while in the lock).

## A shot

With sniping on and a rifle selected, a pointer press inside the background
picture calls `snipe(point)`. Otherwise the press goes to the pan control.

1. Nothing happens if the point is outside the background, no rifle is
   selected, or the rifle is empty.
2. One shot is used up.
3. The day's attack result becomes at least "failed, fired the gun".
4. The rifle's shot sound plays.
5. A bullet hole is stamped into the background picture, centred on the
   point (below).
6. The white flash starts.
7. **Every figure whose hit box contains the point is hit**, in this order:

   | Who | If hit |
   |---|---|
   | Each figure in the waiting line | Attack result "hit the target" if its strip prefix contains `Target`, else "hit an innocent" |
   | Each of the ten leaving figures | "hit an innocent" |
   | The runner, if alive | "solved". He gets the rifle's path. If the scene has never created an enemy figure that day, the state goes straight to `waiting-to-fade-to-night` |
   | Guards 0 to 4, stopping at the first one hit | "hit a guard" |
   | Each living enemy | "solved" |

8. Panic (part 2), whether or not anything was hit.

"Is hit" (`checkSniped`): the figure is alive and its hit box contains the
point (part 1: its box now, or its box of the previous frame). It is then
given the rifle's path, `shot` or `tranq`. If its current animation name
contains `bike`, it gets `bike-explode` instead, whose start event sets off
an explosion. The runner is tested the same way but always gets the rifle's
path.

All four of those paths use an animation marked as a death, so a figure that
is hit **counts as dead from that moment, with either rifle**. A
tranquillised attacker is as "dead" for `checkEnemiesDead` as a shot one.
The difference between the rifles is only the animation and the "with the
tranquilliser" mark on the attack result.

One shot can hit several figures if their boxes overlap, and can set several
results; the rule below decides which one stays.

## The attack result

The day keeps one attack result. `setAttackResultWithPriority` replaces it
only by one that comes **later in this list**, so the worst thing that
happened wins and nothing can lower it:

| Order | Result | Set by |
|---|---|---|
| 0 | none | the start of the day |
| 1 | failed, did nothing | sniping being switched on |
| 2 | failed, fired the gun | any shot |
| 3 | solved | hitting the runner or an enemy |
| 4 | hit an innocent (with or without the tranquilliser) | hitting a line or leaving figure |
| 5 | hit a guard (same) | hitting a guard |
| 6 | hit the target (same) | hitting the line's target figure |

When the scene fades out (part 2, `fade-to-night`), results 4, 5 and 6 lead
to the endings `killed-innocent` / `tranqed-innocent`, `killed-guard` /
`tranqed-guard`, `killed-target` / `tranqed-target`. Results 0 to 3 go to
the night, which stores the result in the fact `Night/AttackResult` and
shows a message for "did nothing", "fired the gun" or "solved"; a stopped
attack also adds a bonus line to the budget (`night.md`).

Separately, when the scene fades out with the friendly guard on duty and
`guard4` dead, `Day.killFriendlyGuard` sets the story fact
`Game/FriendlyGuardDead` to `YES`. "Has the friendly guard" means his state
is "guarding" or "chat".

## Bullet holes

`BulletHoles.png` is 32 x 8: four holes of 8 x 8. Each shot pastes the next
one into the **background picture itself**, at the point minus 4 in both
directions (rounded down), so holes stay for the rest of the day's scene.

Which of the four comes next is a shuffled run that repeats: the order is
made once, at construction, from a generator seeded with one whole-number
draw from the border generator (part 2). The shuffle (`makeShuffled`): start
with 0, 1, 2, 3; for `n` = 4, 3, 2, 1: swap the item at `n - 1` with the
item at `int(r x n)`. Four draws from that private generator.

## The grenade

`throwGrenade(pos, speed)` (part 2 gives the two throws) creates a `Grenade`
picture and steps it every frame with the **scene's** clock:

1. vertical speed += 50 x `dt` (gravity);
2. x += horizontal speed x `dt`; y += the new vertical speed x `dt`;
3. when y has passed **the starting height + 10**: it has landed
   (`grenade_onHit`, part 2), once;
4. a "started falling" callback exists, but nothing sets it.

For the two throws in the game that gives, roughly: the overhand throw
(speed 60, -50) lands after about 2.2 s, about 130 units to the right; the
underhand throw (-40, -20) after about 1.15 s, about 46 units to the left.
(Worked out from the formulas with exact time; the game steps per frame, so
it differs a little.)

## Slow motion, and which clock runs what

Switching sniping on sets the scene's time scale to the layout's
`borderSnipingTimescale`. Looked up in part 4 (`border-view.md`): it is
**1.0 on the desktop layout**, 0.9 on tablet and 0.8 on phone. So the
desktop game has no slow motion; the scene's clock and the game's clock run
at the same rate there, and the table below only matters for the portrait
layouts. Nothing in the code read here sets it back to 1; a new day builds
a new scene.

| Runs on the scene's clock (slowed) | Runs on the game's clock (not slowed) |
|---|---|
| Figures, the waiting line | Every delayed call: the attack delay, the 0.1 to 2 s delays in part 2, the kill button appearing |
| The state machine's times (3 s, 4.5 s, 11 s, 40 s...) | The rifle buttons' own states and slides |
| The alarm's 1.8 s spacing | The booth button's blinking |
| The grenade | The blinking of the sniping surround (on for 0.3 s of every 0.6 s while a loaded rifle is selected) |
| The explosion picture, the white flash | |

The delayed calls are stepped by the screen tree (`Trunk.treeUpdate`) with
the game's clock, just before each object's own update. This answers the
open point in part 2.

## Helpers for the game's test player

Not part of normal play; listed so they are not mistaken for it.

- `autoIsAttackUnderway`: the state is one of the four attack scenes.
- `autoGetLivingTargetPerson(kind)`:

  | Kind | Who |
  |---|---|
  | `Enemies` | the runner if alive and on screen; else the first enemy that is alive, on screen and not near a guard |
  | `Enemy(id)` | the first enemy with that id that is not near a guard |
  | `Guard` | `guard2` |
  | `ManInRed` | the line's target figure |
  | `Innocent` | the third figure from the front of the line |

  Only a living figure is returned.
- "Near a guard" (`getPersonIsNearGuards`): some guard other than the figure
  itself has its picture less than 35 units away.
- `autoGetNextSnipeWorldPoint(kind)`: that figure's picture x and its feet
  y minus 9, turned into screen coordinates.
- `debugSnipeAll`: selects the tranquilliser, gives it 3 shots and shoots at
  each enemy and the runner, 9 above their feet.

## What this means for the port

- A hit is a point-in-box test against every figure, including the previous
  frame's box, so fast figures are easier to hit than their picture
  suggests.
- "Dead" is a property of the path's animation, not of the rifle.
- The attack result is a single "worst so far" value; six endings hang off
  it.
- (Corrected 2026-10-14. This said "two clocks are needed during an attack:
  one that slows and one that does not". That holds for the phone and
  tablet layouts only. On desktop the sniping time scale is 1.0
  (`border-view.md`), so a desktop port can use one clock.)

## Results of the check

`python -I scripts\checks\border_events_check.py scripts\reference extracted\art\assets\data`
(run 2026-10-14), last section:

- `shot`, `tranq`, `bike-explode` and `enemy-grenaded` exist, have no points
  and no `next`, and all four use a death animation.
- All 10 shooting sounds exist in `Sounds.xml`; both key papers exist in
  `Papers.xml`; all six endings exist in `Ends.xml`.
- The only attack day without the `SNIPING` feature is day 2.
- `BulletHoles.png` is 32 x 8, matching the four 8 x 8 pieces the code cuts.

## Not known / not tested

- Nothing was compared with the running game.
- (Answered in part 4, `border-view.md`: on desktop the hit box,
  `Layout.borderPersonHitSize`, is 8 wide and 18 high, and the slow-motion
  scale, `Layout.borderSnipingTimescale`, is 1.0, meaning none.)
- How a press becomes a point (`Input.getPointerJustDown`) and the scope
  cursor.
- What the key paper does after unlocking, and whether an unlocked rifle
  stays unlocked on later days.
- The rifle buttons' slide positions and the bullet pictures (drawing).
- (`app.Clock` was read in part 4, `border-view.md`: it follows real time,
  capped at 0.1 s a frame; it has a global speed factor, 1.0 unless changed,
  and a "pause for one frame" function. Two users of "pause for one
  frame" are now known (`save-format.md`, part 2): the game's `paused`
  state calls it every frame, and so does the resume overlay shown after
  a stash restore. Other users, and who changes the speed factor, were
  not searched.)
