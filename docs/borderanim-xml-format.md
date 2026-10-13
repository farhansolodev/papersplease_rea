# BorderAnim.xml: the picture atlas of the border scene

Studied on 2026-10-14. `BorderAnim.xml` is a **picture atlas**: a list
saying where each small picture sits on one big sheet, `BorderAnim.png`. The
pictures are the frames of the figures in the top view (guards, the people
in the queue, the attackers, the truck, the explosion).

Check: `scripts/checks/borderanim_check.py`. There is no reference script;
the loader is a few lines.

Functions read in full: `data.AtlasLib.make`; `app.vis.Atlas` (constructor,
`addSource`, `getSequence`, `getSourceRect`); `play.day.border.Person.setAnim`.
Read in part: `play.day.border.CustomTile` (`init`, `get_currentFrame`,
`restartAnim`, `stepAnim`). **Not studied here:** the rest of the border
scene. Its figures and waiting line (`border-figures.md`) and `Border`
itself (`border-scene.md`) and shooting (`border-shooting.md`) have been
studied since; the cameras and panning have not.

## The file

    <TextureAtlas imagePath="BorderAnim.png">
        <SubTexture name="Boom-00" x="11" y="1" width="64" height="64"/>
        ...

The loader (`AtlasLib.make(image file, xml file)`) takes the first element of
the file and reads every `<SubTexture>` child in file order:

| Attribute | Use |
|---|---|
| `name` | the picture's name |
| `x`, `y`, `width`, `height` | its rectangle on the sheet (read as decimal numbers) |

**`imagePath` is not read**: the caller passes the sheet's file name itself
(`assets/BorderAnim.png` is among the code's strings).

Each picture gets a number: its position in the file, from 0.

## How an animation finds its frames

`Atlas.getSequence(prefix)` returns the numbers of **all pictures whose name
starts with `prefix`, in file order**, and remembers the answer. That is all
there is to grouping: no parsing of frame numbers.

A figure (`border.Person`) has a name prefix such as `Guard0` or `Enemy`.
When it takes an animation from `Paths.xml` (`paths-xml-format.md`):

- the sequence prefix is the figure's prefix plus the animation's `suffix`
  when moving sideways, or `suffixv` when moving up or down. For the
  animation whose suffix is `-Idle`, the figure's own idle suffix is used
  instead (`-Idle` unless the figure was created with another one);
- the speed is `fps` (sideways) or `fpsv`; `fps` 0 means "do not animate";
- `loop`, `offset` and `death` are copied; `sound`, if any, is played;
- a non-looping animation starts again from its first frame.

The animated picture advances by `seconds passed * fps` frames each step and
shows frame number `floor(frame) mod number of frames`. (What exactly happens
at the end of a non-looping animation was not read in full.)

## Cross-check with the files

`borderanim_check.py` (run 2026-10-14, needs Pillow):

- Root `<TextureAtlas>` with 247 `<SubTexture>` children, each with exactly
  the five attributes. The sheet is 512 x 732.
- No name repeats, no rectangle leaves the sheet, no two rectangles overlap.
- The file is **not** in alphabetical order, so "file order" matters.
- Two naming styles for frames: `Boom-00`, `Boom-01`... (25 groups) and
  `Enemy-WalkH 1`, `Enemy-WalkH 2`... (32 groups). In every group the
  numbers run upward in file order, and all frames of a group have the same
  size. Group sizes: mostly 4 frames; the explosion and one other have 13.
- Every one of the 37 animation suffixes in `Paths.xml` has at least one
  picture group ending in it. The figure prefixes this gives: `Enemy`,
  `Guard0`, `Guard1`, `Man0`, `Target0`, `Truck`, `CarA`, `BossCar`.
- Nine groups are not reached through an animation suffix: `ABlank`, `Boom`,
  `Grenade`, `Enemy-Throw0`, `Enemy-Throw1`, `Guard0-IdleB`, `Guard1-IdleB`,
  `Truck-Drive0`, `Truck-Drive1`. They must be asked for by name from code
  (`-IdleB` looks like an alternative idle suffix).
- **Five prefix clashes.** Because the search is "starts with", these
  prefixes also collect another group's frames:
  `Guard0-Idle` / `Guard0-IdleB`, `Guard1-Idle` / `Guard1-IdleB`,
  `Enemy-Throw` / `Enemy-Throw0` and `Enemy-Throw1`,
  `Enemy-BikePassenger` / `Enemy-BikePassengerTurn`. Whether that is
  visible in the game (idle uses `fps` 0, so only one frame shows) was not
  worked out. The port must use the same "starts with" rule, not a tidier
  one, or these animations would get a different number of frames.

## Not known / not tested

- (Answered since: which figures are created, with which prefixes and idle
  endings, is the table at the top of `border-scene.md`; the waiting line's
  figures are in `border-figures.md`.) Still not studied: the cameras and
  panning.
- Nothing here was compared with the running game.
