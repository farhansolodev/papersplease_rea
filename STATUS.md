# STATUS

Last updated 2026-10-12. **The problem below is resolved.** Kept so the dead
end is not repeated.

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
