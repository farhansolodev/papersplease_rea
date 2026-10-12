# Reading the game's code with Ghidra

How to get decompiled, named code out of `GameAssembly.dll`. Confirmed on
2026-10-12.

REA is not used for this DLL: its Ghidra requests time out after 5.5 minutes
and the full analysis takes about 16 (see `STATUS.md`). Ghidra's command-line
mode, `analyzeHeadless`, is run directly instead.

## 1. Analyse once (done; about 16 minutes)

```powershell
$env:GHIDRA_HEADLESS_MAXMEM = "6G"
C:\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat decompiled\ghidra PapersPlease `
  -import game\GameAssembly.dll
```

The saved project is `decompiled/ghidra/PapersPlease.gpr` plus
`PapersPlease.rep/` (224 MB, gitignored). Peak memory seen was about 3.8 GB.
Ghidra logged two errors; see "Known analysis errors" below.

## 2. Apply the recovered names (done; 30 seconds)

```powershell
C:\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat decompiled\ghidra PapersPlease `
  -process GameAssembly.dll -noanalysis -scriptPath scripts\ghidra `
  -postScript ApplyIl2CppNames.java dumps\il2cppdumper\script.json
```

Result: 25,256 functions named (every unique method address), 1,846 of them
were functions Ghidra had not found itself, 8,028 metadata labels and 10,106
string-literal labels applied.

Il2CppDumper's own Ghidra scripts are not used: they need Jython, which this
Ghidra install does not have.

## 3. Load the data layouts and typed signatures (done; 1.4 minutes)

```powershell
C:\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat decompiled\ghidra PapersPlease `
  -process GameAssembly.dll -noanalysis -scriptPath scripts\ghidra `
  -postScript ApplyIl2CppTypes.java types dumps\il2cppdumper\il2cpp.h `
  -postScript ApplyIl2CppTypes.java signatures dumps\il2cppdumper\script.json
```

Result: about 35,000 data types imported from `il2cpp.h`; typed signatures
applied to 25,220 of 25,256 functions (36 not applied, not investigated).

`il2cpp.h` uses C++ inheritance (`struct A_Fields : B_Fields {`), which
Ghidra's C parser rejects. The script rewrites each one so the base struct
becomes a first member called `super`. Check: all 29 field offsets of
`play_day_BoothEngine_o` in Ghidra equal the offsets in `dump.cs`. Only that
one class was compared.

To print a struct's layout:
`-readOnly -postScript ApplyIl2CppTypes.java show play_day_BoothEngine_o`

A copy of the project from before this step (names only, 478 MB) is in
`decompiled/ghidra_backup_named/`.

## 4. Decompile functions on demand (a few seconds each)

```powershell
C:\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat decompiled\ghidra PapersPlease `
  -process GameAssembly.dll -noanalysis -readOnly -scriptPath scripts\ghidra `
  -postScript DecompileFunctions.java decompiled\out.c "play.day.BoothEngine$$"
```

Each selector after the output file is either a name prefix or a `0x`
address. Names look like `namespace.Class$$method`.

## How to read the output

- **Function names, parameter types and return types** are real. The comment
  above each function gives the original signature and any other names
  sharing that code.
- **Fields** show by name: `(__this->fields).opQue`. Inherited fields sit
  under one or more `super.` levels.
- **Virtual calls** (calls through an object) show the method name and its
  slot number: `(*(obj->klass->vtable)._27_get_hasBomb.methodPtr)(obj, ...)`.
- **String constants** still appear as `StringLiteral_N`. `N` is the index
  into the `ScriptString` list in `script.json` (same order as
  `stringliteral.json`).
- Every method has a trailing `MethodInfo *method` parameter. It is IL2CPP
  plumbing; ignore it.
- The block of `thunk_FUN_1800eeee0(&StringLiteral_N)` calls at the top of a
  function is IL2CPP's one-time setup and carries no game logic.
- `FUN_1801271d0()` at the end is the null-reference error path.
- "Unknown calling convention -- yet parameter storage is locked" is a
  harmless Ghidra notice caused by applying signatures.

## Known analysis errors

Ghidra logged two errors during the first analysis. `1801523d0` is in the
`.text` section (engine runtime support, not game code). `180263f09` is inside
`haxe.lang.FieldLookup$$.cctor`, the Haxe runtime's field-name table setup.
Neither is game logic.

## Check that the names match the code

`play.day.BoothEngine$$getLeaveDir` at `0x180467c80` decompiles to code that
compares strings and returns one of `left`, `right`, `right-bomb`,
`right-guard`, `left-guard`, `right-boss`, `right-poisoned`, `left-poisoned`.
`get_opQueHasItems` reads offset `0x40`, which `dump.cs` lists as the `opQue`
field. Both match their names. Only these two functions have been checked.

After step 3, the same function reads
`(__this->fields).env`, `(ppVar1->fields).traveler`, `get_hasBomb`,
`(ppVar2->fields).special` and `(__this->fields).preventStashCount = 10000`.