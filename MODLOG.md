# MODLOG

A running log of what changed and what was tested. Newest entries go at the top,
below this header. "Tested" means it was actually run; otherwise write
"not tested". Log failures too. Keep each field to a line or two.

```markdown
## [Date] [short title]

**Changed:** what was changed, and in which files
**Why:** the problem or goal
**Tested how:** what was done to check it
**Result:** what happened, with numbers or log lines where possible
**Still broken / not tested:** be honest
**Next:** what to do next
```

## 2026-10-12 Data layouts and typed signatures loaded into Ghidra

**Changed:** added `scripts/ghidra/ApplyIl2CppTypes.java`; ran it on the Ghidra project; updated `docs/ghidra-workflow.md`; backup of the names-only project in `decompiled/ghidra_backup_named/`.
**Why:** fields showed as raw offsets and virtual calls as table offsets, which made the code slow and error-prone to read.
**Tested how:** printed `play_day_BoothEngine_o` from Ghidra and compared all 29 field offsets with `dump.cs`; re-decompiled `getLeaveDir` and `get_opQueHasItems`.
**Result:** all 29 offsets match. 35,667 data types; signatures applied to 25,220 of 25,256 functions. Decompiled code now shows `(__this->fields).env`, `.traveler`, `get_hasBomb`, `preventStashCount`. First import attempt left booleans as `bool.conflict` (my script redefined `bool`); fixed by removing that line, restoring the backup and re-importing.
**Still broken / not tested:** 36 signatures not applied (which ones is unknown). Only one class's layout compared. String constants still show as `StringLiteral_N`. The two Ghidra analysis errors are identified as non-game code (engine runtime, `haxe.lang.FieldLookup`), not fixed.
**Next:** decide which part of the game to read first.

## 2026-10-12 Ghidra analysis, naming and first decompile all work

**Changed:** saved Ghidra project in `decompiled/ghidra/`; added `scripts/ghidra/DecompileFunctions.java`; wrote `docs/ghidra-workflow.md`; marked `STATUS.md` resolved.
**Why:** milestone 1 needs readable function bodies with real names.
**Tested how:** ran `analyzeHeadless` import, then `ApplyIl2CppNames.java`, then `DecompileFunctions.java` on `0x180467c80` and `0x180468060`; looked up the string constants and field offsets they use.
**Result:** analysis took 15.9 min, project is 224 MB. 25,256 functions named, 0 addresses without a function. `BoothEngine.getLeaveDir` returns strings like `left`, `right`, `right-bomb`; `get_opQueHasItems` reads offset 0x40, the `opQue` field. Names match code.
**Still broken / not tested:** only two functions checked. Struct layouts not loaded, so fields show as raw offsets and virtual calls as table offsets. Two Ghidra analysis errors not investigated.
**Next:** decide what to read first; consider loading struct layouts from `il2cpp.h` to make fields readable.

## 2026-10-12 Tools moved to C:\tools, git initialised, direct Ghidra run started

**Changed:** moved Il2CppDumper to `C:\tools\Il2CppDumper-6.7.46`; removed project `tools/` and its `.gitignore` line; created `C:\Users\farha\.claude\CLAUDE.md` listing shared tool paths; deleted the empty stray `papersplease_rea\papersplease_rea` repo (origin unknown); ran `git init` in the project root (no commit); added `scripts/ghidra/ApplyIl2CppNames.java`; updated `CLAUDE.md` tooling state.
**Why:** shared tools belong outside the project; REA cannot analyse the DLL, so Ghidra is run directly with a saved project in `decompiled/ghidra/`.
**Tested how:** `git status` after init; checked `script.json` field names against the naming script.
**Result:** `git status` lists only `.claude/`, `.gitignore`, `CLAUDE.md`, `MODLOG.md`, `STATUS.md`, `docs/` (the game folders are ignored). Ghidra import started and picked the PE loader, x86 64-bit.
**Still broken / not tested:** Ghidra analysis not finished. `ApplyIl2CppNames.java` has never been run. Il2CppDumper not re-run from its new location.
**Next:** when analysis finishes, run the naming script, then decompile one named function.

## 2026-10-12 REA/Ghidra decompile of GameAssembly.dll: failed twice

**Changed:** nothing in the project; wrote `STATUS.md`.
**Why:** wanted to read one named function's decompiled body and load the recovered names into Ghidra.
**Tested how:** REA `binary_overview`, then REA `procedure_pseudo_code` on `0x180467c80` (`BoothEngine.getLeaveDir`).
**Result:** both failed with `provider_timeout` at 330,000 ms. REA also reports renaming as unsupported on Windows ("Windows Ghidra P0 does not admit database mutation").
**Still broken / not tested:** no function body has been read. No recovered name has been checked against real code.
**Next:** waiting for a decision; options are listed in `STATUS.md` (first choice: run Ghidra headless directly with a saved project).

## 2026-10-12 IL2CPP names recovered with Il2CppDumper

**Changed:** copied the game into `game/`; downloaded Il2CppDumper v6.7.46 into `tools/`; ran it into `dumps/il2cppdumper/`; added `/tools/` to `.gitignore`; wrote `docs/il2cpp-name-recovery.md`.
**Why:** `GameAssembly.dll` is unreadable without the class and method names stored in `global-metadata.dat`.
**Tested how:** compared file counts and SHA-256 of the copy; read the metadata header; counted the dumper output; cross-checked method addresses against the DLL's `.pdata` function table.
**Result:** copy matches (67 files, 94,154,205 bytes). Metadata v27, not encrypted. 4,299 types, 29,623 methods with addresses, 1,351 types in the game's own code. 100% of addresses are in the code section, 90.5% sit exactly on a `.pdata` function start. The game is Haxe compiled to C#.
**Still broken / not tested:** names are not loaded into Ghidra/REA yet. No decompiled function has been compared against its name. The 9.5% of addresses not in `.pdata` are unexplained (probably small leaf functions).
**Next:** finish the Ghidra analysis, try applying `script.json` names through REA, and decompile one named game function as a check.
