# STATUS

Two entries. The first is open; the second (older) is resolved and kept so
the dead end is not repeated.

---

# Open, 2026-10-13: the booth's random numbers fall out of step with the game

## Goal

Make the Python reference (`scripts/reference/booth.py`) choose the same
**errors** as the running game for a whole day, not just produce the same
travelers. Error choices use the booth's random generator, which is also
used for building each person, generating document values, and picking
spoken lines.

## What works (tested against the real game)

Two runs of the game's own test player, seed 12345
(`docs/comparing-with-the-game.md`, logs in the gitignored
`extracted/autorun/`), compared with
`scripts/checks/compare_with_log.py`:

- Script entry, nationality, duration, purpose and starting papers match
  for all 36 travelers logged over days 1 to 4. These come from the day's
  **traveler** generator, so the seed chain and the script reading are
  confirmed.
- The always-errors match for all 36.
- The **candidate lists** for error choices match the game's exactly
  (checked for day 4: same 14 errors in the same order).

## The problem

The error picked among several candidates differs from the game's for some
travelers. The first clear case is day 4, traveler 2: 14 candidates, the
game picked `EntryPermit-WrongPurpose<speech>`, the reference
`Passport-WrongFaceError...`. Same candidates, different pick, so the
reference is at a different position in the booth's generator.

## Evidence

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

## What was tried

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
   in this build), or whether `capture` (frame captures) fares better.

## Why it is hard to see

The log prints who comes and which error is chosen, but **no value that
depends directly on the booth's generator** (no name, id number, face or
document value), and error picks carry only a little information each. So
the position in the generator can only be inferred indirectly.

## Ideas not tried yet

- **Reason from the code instead of the log:** read, in order, everything
  between two `makeNewTraveler` calls that touches `BoothEnv.rand` (the
  engine's handling of each event, `getSpeech` callers, `addPaper` for
  papers added during a visit, the transcript) and model it, then compare.
- **More informative picks:** runs with other seeds, looking only at each
  day's first many-candidate pick, to collect enough evidence to tell
  hypotheses apart.
- **Read the generator directly** with a debugger attached to the game (may
  need a tool; ask first).

---

# Resolved, 2026-10-12: REA's Ghidra requests time out

## Goal

Milestone 1: get a readable view of the game's code: (a) recover the IL2CPP
class and method names, and (b) read decompiled function bodies with those
names attached.

## Outcome

Both parts work. See `docs/il2cpp-name-recovery.md` and
`docs/ghidra-workflow.md`.

## The dead end: REA cannot analyse GameAssembly.dll on this machine

- `binary_overview` and `procedure_pseudo_code` both failed with
  `provider_timeout` at 330,000 ms (5.5 minutes).
- Cause, now measured: Ghidra's full analysis of this DLL takes 15.9 minutes.
  REA only answers after the full analysis and discards its temporary
  database on timeout, so retrying can never succeed.
- REA also reports `set_addresses_names` as unavailable on Windows ("Windows
  Ghidra P0 does not admit database mutation"), so it could not show the
  recovered names even if it finished.

Do not retry REA's Ghidra tools on this DLL unless REA gains a longer timeout
or a persistent database on Windows.

## What fixed it

Running Ghidra's `analyzeHeadless` directly with a project saved in
`decompiled/ghidra/`, plus two scripts in `scripts/ghidra/`.

## Not tried (no longer needed)

- A REA timeout or analyzer setting.
- Cpp2IL.
