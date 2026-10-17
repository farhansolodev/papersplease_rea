# From launching the game to each day's random numbers

Studied on 2026-10-13. This answers "where does the randomness of a
playthrough come from?": how the game picks its master seed at start-up, and
how every generator used by days, faces and names is derived from it.

Functions read in full: `HostUnity.CreateGame` (`0x1809e7b00`), the `Game`
constructor (`0x180585270`), `Main.main`, the `play.Bootstrap` constructor
(`0x180435530`), `setLanguage`, `advanceStorySeed`,
`autoReapplyRandomSeed`, `set_storyState`; the `DayRun` and `BoothEnvRun`
constructors; Haxe's `Math` static setup and `Math.random`;
`System.Random`'s parameterless constructor; `app.CommandLine.fromArgs`;
`Trace` (`init`, `info`, `verbose`, `customPrint`, static setup). The
`LOAD_TO_SCREEN` branch of `Game.applyScreenChange` was read here; the rest
of that function was read on 2026-10-14 (`save-format.md`, part 2). The
seed-scaling constant was read from the raw
instructions.

Everything here is confirmed in the code unless marked otherwise.

## The master seed

The Unity start-up (`HostUnity.CreateGame`) builds the game's parameters
**without a seed**. The `Game` constructor then picks one:

```
master = floor(Math.random() * 16777215)
```

`Math.random()` is .NET's `System.Random.NextDouble()` on a generator made
once with the parameterless constructor, which seeds it from
`Environment.TickCount` (milliseconds since the computer started). So **every
launch has a different master seed**, between 0 and 16,777,214.

If the parameters do carry a seed, it is used as is. `Main.main`, a second
entry point, passes 0 and always starts the test automation; whether the
Windows build ever uses `Main.main` is not checked (inferred: no, Unity uses
`HostUnity`).

`HostUnity.CreateGame` also asks the test automation for a plan
(`test.auto.AutoPlan.make`, from the disk and the command line). If the plan
is valid, an automated game (`AutoGame`) is started instead of the normal
one. The plan file and what the automated game does are in
`comparing-with-the-game.md`.

## What `play.Bootstrap` derives from it

| Generator | Seed | Used for |
|---|---|---|
| `endlessSeedGenRand` | master + 26 | endless mode (how a run's seed is taken from it is not studied; the mode's rules are in `endless-mode.md`) |
| `storySeedGenRand` | master + 73 | story seeds (below) |
| face cycler | master (its parts use master + 1 to + 5, `traveler-build.md`) | random faces, for the whole launch |
| name cycler | master and master + 1, **only if no saved position exists** | names |

Then `setLanguage` (called at the end of the constructor, and again whenever
the language is changed) loads the language's data and creates:

- the **day run**, with `storySeed = storySeedGenRand.nextInt()`;
- the **booth run**, which holds the same face and name cyclers.

## The story seed

- First value: drawn when the day run is created (above).
- **Every time a save is loaded** (`LOAD_TO_SCREEN`), the story state is
  loaded from the save and then a **new story seed is drawn**
  (`advanceStorySeed`: `storySeed = storySeedGenRand.nextInt()`).
- **Starting a new game counts as a load** (the log of a real run shows
  `LOAD_TO_SCREEN(NEW;...)`), so a fresh game plays with the **second**
  story seed drawn, not the first. Confirmed against the running game on
  2026-10-13 (`comparing-with-the-game.md`): the first seed gives the wrong
  travelers, the second gives exactly the game's.
- Each day's generators come from it: `day * 50 + storySeed`, then `+ 0x1000`
  and so on (`days-csv-format.md`, `rand.md`).

So the story seed is **not stored in the save**. (Seen in real saves on
2026-10-14: a save is a list of 21 to 24 story facts and holds no seed,
`save-format.md`.) Loading the same save twice
in one launch gives two different story seeds, and so different random
travelers; relaunching gives a different sequence again. (That replays
differ fits how the game plays; the mechanism is what is confirmed here.)

## Faces and names over time

- The face cycler is created once per launch from the master seed and is
  never saved. Faces depend on the launch and on how many faces have been
  handed out since.
- The name cycler's position is saved in the encrypted store (`names`) after
  every name, and loaded at start-up when present. The saved position is a
  seed, a position and a reshuffle count (the fields of
  `ShuffledSequenceState`; `makeFromState`, read since, rebuilds the sequence
  by running the ordinary constructor with those three values), so the
  name order is fixed by the launch that first created it, and continues
  across launches. A real `names` entry (2026-10-14, `save-format.md`) is
  two lines of `seed:position:reshuffles`, for example `11240598:12:0` and
  `11240599:8:0`: the second seed is the first plus one, as the code says.
  By the code the first seed is the master seed of the launch that created
  the entry, so that launch's master seed can be read from the file; this
  was not tested (the reference was not run with that seed against
  anything).

## Consequences

- **A particular session of the original cannot be reproduced** without
  knowing its tick count at launch (and, for names, the saved position).
  Checking the port against the original therefore needs either the
  original's own logs, or running both from a chosen master seed.
- **For the port**: implement the same chain from a master seed: the two
  seed generators, the cyclers, a story seed per load, and day seeds from
  it. How the port picks its master seed was decided on 2026-10-17
  (`docs/DESIGN.md`: a random one at start, settable from the page
  address for tests).
- `autoReapplyRandomSeed` (used by the automation) recreates the two seed
  generators, both cyclers and the story seed from the master seed, which
  is how the automation can replay deterministically. (The automation calls
  it before each route, `comparing-with-the-game.md`; other callers were
  not searched for.)

## Reference script

`scripts/reference/seeds.py` computes the chain for a given master seed:

```
python -I scripts/reference/seeds.py 0 2 1 2
master 0: story seeds [697711081, 1537513867, 1445636628]
day 1: day=697711131 news=697715227 border=697719323 night=697723419 traveler=697727515 booth=-1449768421
...
```

The story seeds equal the first three outputs of `rand.py` for seed 73, as
they should. This checks the script against the description above. The
chain itself was confirmed against the running game later, for master seed
12345 (`comparing-with-the-game.md`).

## Command-line words

`CommandLine.fromArgs` (called from `HostUnity.Start`) recognises these
exact words, without dashes:

| Word | Effect (where known) |
|---|---|
| `trace` | turns on the game's debug log (`Trace.enabled`) |
| `soak <name>` | names an automated soak test; `soak auto` starts the test automation with a default plan (`comparing-with-the-game.md`) |
| `savedir <path>` | where saves go (quotes are removed) |
| `expo` | shows a pause button (exhibition mode). On the title screen it also leaves out the endless and quit buttons and switches the settings button off (`screens.md`, part 2) |
| `nosync` | turns off matching the frame rate to the screen: no vertical sync, a target of 65 frames a second (`border-view.md`, "The frame rate"; read 2026-10-15) |
| `stretch`, `720p`, `1080p` | full-screen display options: `1080p` / `720p` pick that screen size (about 60 Hz) instead of the monitor's own, `stretch` lets the picture be scaled to fill the screen (`screen-output.md`, "The screen picture and the window"; read 2026-10-17) |
| `fps` | a display option (not studied) |
| `nosteam` | Steam-related; **out of scope** (online platform) |

### The debug log

`Trace` has two switches: `enabled` and `showVerbose`. Both start off.
`trace` on the command line sets `enabled`. Most of the game's detailed
messages (for example "New Traveler:" and "Additional error:") are printed
only when **both** are on. A full search of writes (2026-10-13,
`comparing-with-the-game.md`) found that `showVerbose` is turned on only by
the test automation: its two debug jumps and an automated game whose plan
has `trace`. Messages go to the platform's log function, which is Unity's
`Debug.Log`. On this machine that file is
`%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\Player.log` (seen in the
runs recorded in `comparing-with-the-game.md`).

So `trace` alone gives only the less detailed messages. The detailed ones
need the automation and its `auto.plan` file, which can also set the master
seed. The game has since been run that way (`comparing-with-the-game.md`);
each launch needs your go-ahead.

## Not studied

- (Answered 2026-10-14, `save-format.md` part 2: the rest of
  `Game.applyScreenChange`. For seeds: a new game is a load of `NEW` and
  both draw a new story seed; going on to the next day saves and draws
  none; an endless day draws one number from the endless seed generator; a
  stash restore draws no story seed and puts no generator back.)
- (Studied 2026-10-14: `StoryState.load` and the save format,
  `save-format.md`.)
- (Studied since, in `comparing-with-the-game.md`: the test automation's
  plan and what an automated game does, where `Trace`'s output ends up, and
  what sets `showVerbose`. The rest of `test.auto.*` is not studied.)
- Compared with the running game: the seed chain, including which story
  seed a new game uses, for master seed 12345
  (`comparing-with-the-game.md`). Not compared: the tick-count master seed
  of a normal launch, the command-line words other than `savedir`. The
  saved name position's file was seen in a real save folder (above). That
  folder came from two launches of one story, and its positions add up to
  the names of both (20, against 8 travelers processed in the second
  launch alone), so a later launch does continue from the saved position.
  A third launch added 10 more to the same two lines, with the seeds
  unchanged (`save-format.md`).
