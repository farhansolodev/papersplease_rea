# Comparing the reference with the running game

Started on 2026-10-13. Goal: make the original game print, for a **known
seed**, the same facts the Python reference predicts (`booth.py`), so the two
can be compared. This doc records what the code offers for that. **The game
has not been run yet**; everything below comes from reading the code.

Functions read in full: `Trace` (all ten functions);
`test.auto.AutoPlan` (constructor, `make`, `makeDefault`, `makeSeedForDay`,
`setDefault`, `setFromFile`); `HostUnity.UnityPlatformDisk` constructor;
`HostUnity.UnityPlatformSys.log`. Read in part: `Game.applyScreenChange` (the
two debug-skip branches), `HostUnity.CreateGame` and the `AutoGame`
constructor (where they use the plan). A new search script,
`scripts/ghidra/FindStaticWrites.java`, listed every write to the `Trace`
switches.

## The debug log's two switches

`Trace.enabled` and `Trace.showVerbose` both start off. The detailed lines
("New Traveler:", "Additional error:", ...) need both.

All 423 uses of the `Trace` class in the code were searched for writes to
its switches. **`showVerbose` is turned on in exactly three places**:

| Where | When |
|---|---|
| `Game.applyScreenChange`, twice | The debug jumps "skip to day" and "skip to traveler". They also turn `enabled` on. The test automation has methods that ask for them; whether anything else does (a developer menu, for example) was not searched |
| `AutoGame` constructor | When the automation's plan has `trace` (otherwise it turns `enabled` **off**) |

The command-line word `trace` only sets `enabled` (`Trace.init`, called from
the `Game` constructor). So **in a normal game the detailed log cannot be
switched on**; it needs the test automation.

Where the lines go: `Trace` hands each line to the platform's log function,
which on this build is Unity's `Debug.Log`. Unity writes that to its
`Player.log` (normally under the user's `AppData\LocalLow`; **not checked on
this machine**, and Unity's standard `-logFile <path>` option should redirect
it; also not checked). The automation additionally uses a file named
`auto.log` in the save folder (how, not read).

## The test automation and its plan file

At start-up `HostUnity.CreateGame` asks `AutoPlan.make` for a plan. If the
plan is valid, an automated game (`AutoGame`) runs instead of the normal one:
it **sets the master seed from the plan**, then plays by itself.

Where the plan comes from:

- Command line `soak auto`: a default plan: all routes, seed = today's date
  as `YYYYMMDD`, no trace.
- Otherwise the file **`auto.plan` in the save folder**, if it exists.
- No file: an empty, invalid plan, and the normal game starts.

The save folder (`UnityPlatformDisk`): the path after the command-line word
`savedir`, if given. Otherwise `%APPDATA%\3909\PapersPlease` (the code asks
Windows for the application-data folder and adds `3909\PapersPlease`;
`persistentDataPath` is only the fallback).

### Format of `auto.plan`

An indented tree (`tab-tree-format.md`). Lines the code looks for:

| Line | Effect |
|---|---|
| `routes` with children | Which automated routes to play: `all`, a number, or a range `3-7` |
| `seed <number>` | **The master seed.** `seed day` uses today's date |
| `trace` | Turns on both log switches |
| `skip <day>` | Skip straight to a day |
| `ffw` with children | When to stop fast-forwarding: `day <n>`, `trav <id or number>`, `screen <Name>`, `attack`, `pause`, `sentry` |
| `audits` with children | Extra checks: `face`, `ending`, `news`, `night`, `paper <pattern>` |
| `facts` with children | `name value` pairs (story facts to set, inferred) |
| `capture <n>` | Capture every n-th frame (inferred from the name) |
| `stash`, `slow` | Test the suspend feature; run slowly |
| `off` | Makes the plan invalid (the normal game starts) |

The plan is valid when it has routes (or `all`) and no `off` line.

## What this means for the comparison

A promising route, entirely with the game's own features:

1. Start the game with `savedir <a folder inside this project>`, so its
   saves and the plan live in the project and your real saves are untouched.
2. Put an `auto.plan` there with a chosen `seed`, `trace`, and a short route.
3. The game then plays itself from that seed and logs each traveler in
   detail. The log is compared with `booth.py` for the same seed.

Because the automation also performs the player's actions, whole days could
be compared, not only the first traveler, provided the reference replays the
same actions.

## Not known yet (to read before any launch)

- **What the automation does**: the routes in `Auto.txt`, how `AutoGame`
  plays a day, what it writes to `auto.log`, and whether it does anything
  beyond playing (it has leaderboard and stash test steps; anything online
  must be ruled out first).
- Exactly what the detailed log lines contain, and whether the story seed
  and day seeds are logged.
- Whether `autoReapplyRandomSeed` changes the seed chain compared with a
  normal launch (`run-and-seeds.md`).
- Where `Player.log` really lands and whether `-logFile` works.
- Running the game needs the user's go-ahead (`CLAUDE.md`).
