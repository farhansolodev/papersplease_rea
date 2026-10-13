# Comparing the reference with the running game

Started on 2026-10-13. Goal: make the original game print, for a **known
seed**, the same facts the Python reference predicts (`booth.py`), so the two
can be compared. This doc records what the code offers for that, then the
runs made so far (further down). **Current result: for seed 12345 the
reference matches the game on every logged field for the 36 travelers of
days 1 to 4.** The first sections were written from reading the code, before
any run.

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
`Player.log`. (Written before any run. The first run, below, showed where
it lands on this machine:
`%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\Player.log`. Unity's
standard `-logFile <path>` option should redirect it; that is still not
checked.) The automation additionally uses a file named `auto.log` in the
save folder (what it writes there is under "What the automated game does").

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
| `stash`, `slow` | `stash`: each time the game writes a stash, restore from it and click the resume button (`save-format.md`, part 2; read 2026-10-14, not run). `slow`: run slowly |
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

## What the automated game does (second reading step, 2026-10-13)

Also read: the rest of the `AutoGame` constructor, `AutoGame.log`,
`advanceToNextPlaythrough` (in part), `Bootstrap.autoReapplyRandomSeed`,
`Traveler.getDescription`, and `PlatformDiskMemWrapper` (`setPersistentString`,
`getPersistentString`, `clear`).

- **Saves stay in memory.** The automated game wraps the disk in a
  "memory" version whose save and load only use a table in memory. So it
  neither reads nor writes real save files, and the name order starts fresh
  from the seed (no saved position).
- **The online part is replaced by a blank one.** It installs a plain
  `PlatformSocial` object (the do-nothing base class) in place of whatever
  the platform set up, so leaderboards and achievements go nowhere.
- **Seed.** The plan's seed becomes the game's master seed. Before each
  route, `autoReapplyRandomSeed` rebuilds the two seed generators (master +
  26 and + 73), the face cycler and the name cycler from it and draws the
  story seed: the same chain as `seeds.py`, first story seed.
- **Routes** (`Auto.txt`): `story 1` to `20` each play to one ending
  (`1` is `in-debt`, ... `20` is `ignore-ezic`), `story 40` collects all
  tokens, `endless 100` to `111` play the endless styles and courses. The
  rest of the file says what to do with particular travelers on each route.
- **Its own log**: `auto.log` in the save folder, appended to. It starts
  with a line of dashes, then the date, the game version, the platform kind
  and `#<seed>`; later "Finished in ..." and one line per route (not read
  in detail).
- **The traveler line** (through `Trace`, so in Unity's log): `New
  Traveler:` followed by the entry id, the nationality, the duration with
  `months`, the purpose, then `PAPERS:` the starting papers, `ERRORS:` the
  error id or `-`, and `RESPONSE:` the traveler's response lines. A second
  error is logged as `Additional error: ...`.

So the log gives, per traveler: **who (script entry), nationality, purpose,
duration, papers and errors**. It does not print the name, face, id number
or document values. That is still a real test: the nationality, purpose and
papers come from the script reading and its random draws, and each error
choice depends on every booth draw made before it, so a day of matching
errors confirms the draw counts of the whole pipeline indirectly.

## Prepared for the first run (not run)

- `extracted/autorun/auto.plan` (gitignored), containing route 1, seed
  12345 and `trace`.
- The reference's prediction for that seed, day 1, from `booth.py`:
  `FINALLY_RETURN_HOME` (Arstotzka, native, passport, no error), then
  `SMALL_CHECKPOINT` (Impor, immigrate, passport), then `WAITED_FOREVER`
  (Republia, visit, 2 months, passport).

## First run: 2026-10-13, route 1, seed 12345 (run with the user's go-ahead)

Command, using the project's copy of the game:

    game\PapersPlease.exe savedir C:\Users\farha\dev\papersplease_rea\extracted\autorun

What happened:

- The test player started and played by itself: title, new game, intro,
  newspaper, day 1 (8 travelers), the night, the `in-debt` ending, back to
  the title. `auto.log` reports `in-debt (ending #1) -> 01:27s 80MB OK`.
  The game was then closed.
- Unity's log was written to
  `%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\Player.log` (outside the
  project; a copy is kept in the gitignored
  `extracted/autorun/Player.route1.seed12345.log`). It holds the game's own
  lines: `[Game]`, `[BoothEnv] New Traveler:`, `[ErrorLib]`, `[BoothEngine]`
  responses, every operation applied, and the test player's steps.
- The game's own files stayed in `extracted/autorun` (`auto.log`); no save
  file was written.

Comparison (`scripts/checks/compare_with_log.py`): **all 8 travelers match
the reference on every logged field**: script entry, nationality, duration,
purpose, starting papers, error, always-errors and additional error.

One thing the reference had wrong, found by this run: **which story seed a
new game uses.** With the first story seed only 4 of 8 travelers matched
(and those by chance: fixed scripts and likely outcomes). With the second
seed all 8 match; the third and fourth give 3 and 4. So starting a new game
draws a new story seed, exactly as loading a save does (`run-and-seeds.md`
now says so). Before finding this, a search over 20,160 variations of the
draw rules was tried and explained nothing, which was the hint that the
rules were right and the seed was wrong.

What this run confirms, against the real game:

- the seed chain from the master seed to the day's traveler generator
  (`rand.py`, `seeds.py`, the `+ 0x4000` day generator);
- reading a traveler script: weighted choices, the purpose, job, district,
  duration, city and gender draws and their order, the automatic papers
  (`travspec.py`), over 8 travelers and about 55 draws;
- the three criminal draws at day set-up (they come first on the same
  generator);
- the always-error for foreigners on day 1.

What it does **not** yet test: random errors (day 1 has none), anything
drawn from the booth's generator (name, face, id number, document values,
error choice), later days, the night's numbers.

## Second run: 2026-10-13, route 20, seed 12345 (stopped during day 4)

Same command, plan changed to route 20. The game played about 40 seconds per
day; it was closed by hand during day 4, with 35 travelers logged (copy in
`extracted/autorun/Player.route20.seed12345.log`).

Comparison (`compare_with_log.py`):

- **Entry, nationality, duration, purpose and papers: 35 of 35.**
- Days 1 to 3 (29 travelers): every logged field matches, including the
  errors chosen on days 2 and 3. **This is weaker evidence than it looks**
  (corrected the same day): those picks were among 3 candidates and the
  "recently used groups" rule left one or two real options, so matching
  them is worth about a coin-flip or two. It does not confirm the booth's
  draw counts.
- **Day 4: the first error difference, at the second traveler** (game
  `EntryPermit-WrongPurpose<speech>`, reference
  `Passport-WrongFaceError...`), and again at the sixth. The other four
  travelers of day 4 match.

Where the day-4 difference starts: between the first and second traveler of
day 4 the game ran, for the first time in this run, the default "Intro"
response with the stock lines `$ask-purpose` and `$state-purpose` (day 4
introduces the entry permit, so the inspector asks the purpose). The
reference does not model speech or the player's actions at all
(`traveler-creation.md`), so any random draw those make from the booth's
generator is missing from it. The code confirms that every stock line looked up draws
once from the booth's generator, on every day. But replaying the game's
spoken lines in the reference (`scripts/reference/speech.py`,
`compare_with_log.py --speech`) does **not** make the errors match: it makes
days 2 and 3 worse and leaves day 4 different. Two attempts failed to
explain the difference at the time (the record is under "Dead ends" at the
end of this doc).

## Solved, 2026-10-14: the desk's drawing also draws

Reading all the booth code showed that giving a paper its picture on the
desk uses the booth's generator too (`desk-drawing-draws.md`). With those
draws and the spoken lines both replayed, `compare_with_log.py` matches the
game on **every logged field for all 36 travelers** of this run, including
the day-4 picks among 14 candidates, and all 8 of the first run. No new run
of the game was needed. Leaving out either part gives 30 or 32 of 36.

So the booth's draw counts are now confirmed for days 1 to 4 of one seed:
the person, the document values, the error choice, the additional error,
the desk draws and the spoken lines, since one miscounted draw anywhere
would change the later picks. Later days' documents are not yet tested.

## Still not known

- How long a route takes on screen, and what the fast-forward settings do
  when the plan has no `ffw` line.
- Whether the game's command-line reader minds Unity's own `-logFile`
  option. (Where `Player.log` lands without it is known: see the first
  run.)
- What the automation's actions draw from the booth's random numbers beyond
  what is now modelled: turning to a page with random marks draws again
  (`desk-drawing-draws.md`); not seen in days 1 to 4.
- What Unity itself does outside the project when the game starts (its own
  log folder, window settings in the registry, any network use of its own).
  This is the same as for any launch of the game and is not something the
  game's code decides.
- Running the game needs the user's go-ahead (`CLAUDE.md`).

## Dead ends: the booth's random numbers fell out of step with the game (resolved 2026-10-14)

The full record of the problem met in the second run above, moved here on
2026-10-14 from the former `STATUS.md`. Only the heading levels and one
reference to this doc were changed.

### Outcome

**Solved by reading the code (attempt 5).** Drawing a paper's picture on the
desk uses the booth's own generator: one draw for each paper's tilt, one for
a passport photo, two for a mark with a position range, three for a seal.
The reference did not count any of these. With them in
(`scripts/reference/desk.py`, `docs/desk-drawing-draws.md`) **and** the
spoken lines replayed (attempt 1's `speech.py`, which was right all along
but could not work alone), `compare_with_log.py` matches the game on every
logged field for all 36 travelers of the route-20 run and all 8 of the
route-1 run. Leaving either part out breaks it (30 and 32 of 36).

How it was found: all 1,433 functions of the booth classes were decompiled
and searched for any use of a generator. That listed three places not seen
before (`booth.Paper`'s constructor, `BoothEnv.getImage`,
`PaperInnerVisuals`). The lesson: attempt 2 searched for a *fixed* number of
missing draws per traveler, but the real number depends on which papers the
traveler has (2, 3 or 4 each), so no fixed offset could fit.

What is still not tested is listed at the end of
`docs/desk-drawing-draws.md` (pages drawn again when turned, fingerprint
pictures). The rest of this entry is the record as written while the
problem was open.

### Goal

Make the Python reference (`scripts/reference/booth.py`) choose the same
**errors** as the running game for a whole day, not just produce the same
travelers. Error choices use the booth's random generator, which is also
used for building each person, generating document values, and picking
spoken lines.

### What works (tested against the real game)

Two runs of the game's own test player, seed 12345
(this doc, logs in the gitignored
`extracted/autorun/`), compared with
`scripts/checks/compare_with_log.py`:

- Script entry, nationality, duration, purpose and starting papers match
  for all 36 travelers logged over days 1 to 4. These come from the day's
  **traveler** generator, so the seed chain and the script reading are
  confirmed.
- The always-errors match for all 36.
- The **candidate lists** for error choices match the game's exactly
  (checked for day 4: same 14 errors in the same order).

### The problem

The error picked among several candidates differs from the game's for some
travelers. The first clear case is day 4, traveler 2: 14 candidates, the
game picked `EntryPermit-WrongPurpose<speech>`, the reference
`Passport-WrongFaceError...`. Same candidates, different pick, so the
reference is at a different position in the booth's generator.

### Evidence

- The booth has one generator (`BoothEnv.rand`); the error maker shares it.
- `getSpeech` draws from it once per stock response looked up
  (`decompiled/speech.clean.c`), and the game speaks stock lines for every
  traveler (`$ask-approved`, interrogation lines, and from day 4
  `$ask-purpose`, `$state-purpose`, ...). The reference did not model this.
- **Correction of an earlier claim:** I wrote that days 2 and 3 "match
  fully, including every random error" and that this confirmed the booth's
  draw counts. It does not. On those days the picks were among 3 candidates,
  and the "recently used groups" rule left only one or two real options
  (day 2: one coin-flip, then a forced choice). Matching them is weak
  evidence, roughly a coin-flip or two.

### What was tried

1. **Replaying the spoken lines.** Added `scripts/reference/speech.py`
   (stock-line lookup with its draws) and made the comparison replay every
   `SAY` line the game logged for each traveler. Result: worse on days 2 and
   3 (4 of the 3-candidate picks now differ) and day 4 still differs. So
   either the replay is wrong (which logged lines really cause a lookup, or
   how many draws each makes), or the reference's own draw counts per
   traveler are wrong, or both.
2. **Simple offsets.** Searched for a fixed number of extra draws at day
   start, per traveler, or per traveler with an entry permit that would make
   day 4 match: none fits both differing travelers. With speech replayed,
   dropping any one draw from building the person does not fix it either
   (best 32 of 36).

Neither attempt explains the difference, so I stopped here.

3. **Audit pictures from the test player (2026-10-13).** Read the audit
   code: with `audits` / `face` in the plan the test player adds each
   traveler's face picture to a grid, with `paper <pattern>` the inner
   picture of matching papers, and saves the grid as
   `<save folder>/audits/<route number>-<route name>.png` when a route
   finishes (only if the `audits` folder already exists). Ran route 1 with
   `face` and `paper Passport`. A file was written (1200x120, room for 8
   faces), but **its contents are not pictures**: mostly transparent, with
   thin vertical white lines and scattered coloured dots, and pixel values
   that look like leftover memory. No passport pictures were added at all.
   So in this released build the audit picture is unusable as it stands.
   Not investigated: why (the pictures may live only on the graphics card
   in this build).
4. **The `capture` setting (2026-10-13): ruled out by reading, not run.**
   It records a film, not pictures: `test.auto.CaptureWorker` draws each
   frame with the same software renderer the audit uses and pipes it to the
   program `/usr/local/bin/ffmpeg`, writing
   `/Users/pope/Projects/Please/Temp/capture.mov`. Both are fixed paths from
   the developer's Mac. Neither exists here; making them exist would mean
   creating files and installing a program outside the project, and the
   renderer already gave an empty picture in attempt 3.

### Why it is hard to see

The log prints who comes and which error is chosen, but **no value that
depends directly on the booth's generator** (no name, id number, face or
document value), and error picks carry only a little information each. So
the position in the generator can only be inferred indirectly.

### Ideas listed while it was open (the first one solved it)

- **Reason from the code instead of the log:** read, in order, everything
  between two `makeNewTraveler` calls that touches `BoothEnv.rand` (the
  engine's handling of each event, `getSpeech` callers, `addPaper` for
  papers added during a visit, the transcript) and model it, then compare.
- **More informative picks:** runs with other seeds, looking only at each
  day's first many-candidate pick, to collect enough evidence to tell
  hypotheses apart.
- **Read the generator directly** with a debugger attached to the game (may
  need a tool; ask first).
