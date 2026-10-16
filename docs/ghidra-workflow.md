# Reading the game's code with Ghidra

How to get decompiled, named code out of `GameAssembly.dll`. Confirmed on
2026-10-12.

REA is not used for this DLL: its Ghidra requests time out after 5.5 minutes
and the full analysis takes about 16 (the record is under "Dead end" at the
end of this doc). Ghidra's command-line mode, `analyzeHeadless`, is run
directly instead.

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
address. Names look like `namespace.Class$$method`. A selector `@<file>`
reads selectors from a text file, one per line (added 2026-10-14; it
avoids the `$$` trouble below and the limit on command-line length).

### The whole game, decompiled once (2026-10-14)

`decompiled/all/` holds every function of the game's own classes, one
file per part of the game (`play_day_booth.c`, `play_screen.c`,
`app_vis.c`, `data.c`, `top.c` for the classes without a namespace, and so
on), so a question like "who else does this?" can be answered by
searching one folder. The address lists come from

```powershell
python -I scripts\ghidra\game_function_lists.py dumps\il2cppdumper\script.json decompiled\all\lists
```

which lists the namespaces `play`, `app`, `data`, `test` and the game's
classes without a namespace: 6,858 addresses in 15 lists. It leaves out
the Haxe and .NET runtime, Unity, Steamworks, and on purpose the
platform's social service (achievements, leaderboards) and the Steam
wrappers, 209 functions (rule 4). Then one Ghidra run per list file:

```powershell
analyzeHeadless.bat ... -postScript DecompileFunctions.java decompiled\all\play_ui.c "@decompiled\all\lists\play_ui.txt"
```

Several `-postScript` pairs can go in one run. The two first lists (454
functions) took 67 seconds; the other 13 lists, in one run, 1,051 seconds
(17.5 minutes). Result: 6,856 of 6,858 decompiled. The two that time out
are the ones known to be too big, the `Booth` and `Layout` constructors;
their instruction listings are `decompiled/booth_ctor_asm.txt` and
`layout_ctor_asm.txt`. Each `.c` file has a cleaned `.clean.c` copy
(`clean_decompile.py`); `play_ui`, `app_ent` and `play_screen` also have
a condensed `.short.c`. A function whose address is shared with an
earlier list is written only there, so search the whole folder, not one
file. The older per-topic decompiles in `decompiled/` were removed on
2026-10-15: every function in them was in this folder, identical or
better (`MODLOG.md`). Kept at the top of `decompiled/`: 16 `.c` and
`.clean.c` files with library functions the game calls (Haxe's maps,
`Array.sort`, `Lambda.has`, `Xml`, ...), which this folder does not
hold, and all `.txt` files (instruction listings, string lists, logs).

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
- **A called function's name can be wrong.** When several methods compile to
  identical code they share one address, and only the first name is shown.
  Seen so far: `Locale__GetText` standing in for a pass-through conversion,
  and `play_night_CalendarEvent___ctor` standing in for the `haxe.io.Bytes`
  constructor. If a callee's name makes no sense in context, check the
  "also:" names in its comment.

To find which functions use an address (a string constant or a function):
`-readOnly -postScript FindReferences.java 0xADDRESS`.

To list the string constants a function uses, in machine-code order (for
when the decompiler drops a string argument from a call):
`-readOnly -postScript ListStringUses.java 0xFUNCTION`.

To print a function's machine instructions, with numeric constants shown
(for when the decompiler drops a calculation):
`-readOnly -postScript DumpAssembly.java 0xFUNCTION`.

To find every place that writes to a class's static values (for example
"what turns this switch on?"):
`-readOnly -postScript FindStaticWrites.java 0xTYPEINFO [window]`.

To read number constants the decompiler shows only as `DAT_180a36c30`
(no Ghidra needed; it reads the file directly):
`python -I scripts\ghidra\read_doubles.py game\GameAssembly.dll 0x180a36c30 ...`.

Habits that paid off:

- **When the decompiler drops something, do not guess.** Check the raw
  instructions (`DumpAssembly.java`) or the constants (`read_doubles.py`).
- **When something does not match the game, look for every user of the
  thing in question before guessing.** The booth's random-number problem was
  solved by decompiling all the booth classes and listing every use of a
  generator, after four narrower attempts failed (the record is under "Dead
  ends" in `comparing-with-the-game.md`).
- **Decompile a whole class family at once and search it**, when the
  question is "who else uses this?". A name prefix selects many functions:
  `DecompileFunctions.java out.c "play.day.booth." "play.day.BoothEnv"`.
  About 1,400 functions take 15 minutes. Virtual calls do not show up in
  `FindReferences`, so searching the decompiled text for the member's name
  (for example `.rand` or `_27_random`) is the reliable way.
- In PowerShell, a name containing `$$` sometimes selects nothing; use the
  function's address or a prefix without `$$` instead.
- **A function can be too big for the decompiler.** The `Layout` constructor
  (`0x180496810`, about 5,400 instructions) fails with "process: timeout"
  after the script's 120 s limit. Its values were read from
  `DumpAssembly.java` output instead: find the object's register (there
  `R13`), then search the listing for writes to the field offsets from
  `dump.cs` (`[R13 + 0x90]` and so on). The record is in `border-view.md`.
  Since 2026-10-16 the whole constructor is run in the emulator instead
  (`EmulateLayout.java`, below), which gives every field at once.

## Running the game's code in the emulator

Ghidra can execute a function's machine code without running the game. This
gives ground truth for small, self-contained functions (pure arithmetic, no
calls into the engine). `EmulateRand.java` is the worked example: it builds a
fake object in scratch memory, points a fake class record's method slot at
the real function, and calls the real constructor and `nextInt`.

Notes for reuse: a class's method table starts at offset `0x138` with 16
bytes per slot; arguments go in `RCX`, `RDX`, `R8`, `R9`; the function must
not reach the one-time metadata setup block or any engine call.

`EmulateStringHash.java` is the second example: it builds a fake string
(length at `0x10`, UTF-16 text from `0x14`, ending in a NUL) and a fake
`StringMap`, runs the real `StringMap.lookup`, and stops at breakpoints
placed partway through to read values from registers. Breakpoints are the
way to read an intermediate result without letting the code reach the
allocator or an exception path.

`EmulateLayout.java` (2026-10-16) is the third, and runs a whole
constructor of about 5,400 instructions. Two ideas make that possible:

- IL2CPP reads every class and string through a slot in the program's
  data (the `..._TypeInfo` and `StringLiteral_N` symbols); in the file
  these hold placeholder numbers, filled only when the game starts. The
  script writes its own fake class records and strings into those slots
  first. A fake class's static block holds fake enum values (index at
  `+0x10`), and its method table points at stub addresses, so a call
  through an object is caught.
- When the emulated code enters a function other than the one being run,
  the script looks at the function's name: the allocator, boxing, simple
  constructors, casts, write barriers and class set-up are done by the
  script itself (a stub) and the call returns; pure helpers can be
  allowed to run; anything else is printed and returns 0, so nothing is
  skipped silently. A null-reference error stops the run with its
  address.

The run's output is raw object memory; `scripts/reference/layout_dump.py`
decodes it with the offsets from `dump.cs`. Check a run against values
known by other means: `layout_check.py` compares 35 values read by hand
earlier, and all match.

## Cleaning the output for reading

```powershell
python -I scripts\ghidra\clean_decompile.py decompiled\in.c dumps\il2cppdumper\stringliteral.json decompiled\out.c
```

Removes four kinds of runtime boilerplate (the metadata setup block, class
initialisation checks, bare null checks, garbage-collector write barriers),
collapses checked type casts to one line (`dest = (T cast)src;`) and shows
string constants as their text. It prints how many of each it changed. On
the Facts loaders it cut 1,506 lines to 1,005. A few cast checks with an
unusual shape are left as they are.

### A shorter view for long classes

```powershell
python -I scripts\ghidra\condense_decompile.py decompiled\in.clean.c decompiled\out.short.c 'name filter'
```

Works on a cleaned file. It joins statements that the decompiler split over
several lines, drops variable declarations and null checks, and shortens
field access (`this.rand`), calls through an object (`CALL setPath#28(obj, ...)`,
where 28 is the slot) and object creation (`new Person`). The optional third
argument is a pattern; only functions whose header line matches are written.
Put it in **single** quotes in PowerShell, or `$$` gets mangled.

On `Border` it cut 8,479 lines to 4,327. It is a reading aid only: when a
line looks odd, go back to the `.clean.c` file. Two things to know: a
dropped null check leaves a comment listing the fields it loaded
(`//   v = x.field`), and a local variable that Ghidra named `__this` is
shown as `this`, the same as the real one.

## Method for studying a data file

1. Inventory the file: every tag, attribute and count. **Read the comments
   too.** An XML parser drops them, and they hold the designer's notes and
   switched-off entries. Skipping them led to wrongly describing the
   `journalist` purpose as undefined.
2. Find the loader with `FindReferences.java` on the file-name string.
3. Decompile the loader and everything it calls; clean; read all of it.
4. List the strings each loader uses and compare with the file's attribute
   names. An attribute with no matching string is unused or read elsewhere;
   check with `FindReferences.java`.
5. Check every attribute value in the file against what the code accepts.
6. Before calling something unused or left over, search the other data files
   and the code's strings for it.
7. Write down what is confirmed, and mark anything else as inferred. Do not
   explain why something is the way it is (for example "cut content")
   without evidence.

## Runtime helpers you will see everywhere

Identified by how they are used across many functions. None carries game
logic.

| In the output | What it is |
|---|---|
| `thunk_FUN_1800f3b80(X_TypeInfo)` | Create a new object of class `X` |
| `FUN_180126c60(type, n)` | Create a new array of `n` items |
| `il2cpp_value_box(type, &v)` | Wrap a number or boolean as an object. **The decompiler often drops the value**; check the instructions if it matters |
| `FUN_1800029d0(obj, X_TypeInfo)` | "Is this an `X`?": returns the object or nothing |
| `FUN_180126c20(obj, ...)` | Raise "wrong type" |
| `FUN_1801271d0()` | Raise "null reference" |
| `FUN_1801271a0(exception, ...)` | Raise an exception (usually after building an error message) |
| `thunk_FUN_1800eeee0(&X)` | One-time metadata setup, or fetch of a late-loaded constant |
| `thunk_FUN_180125b00(...)` | Garbage-collector bookkeeping after storing a field |
| `haxe_lang_Runtime__getField(obj, "name", hash, ...)` | Read a field by name from a loosely typed object |
| `haxe_lang_Runtime__callField(it, "hasNext" / "next", ...)` | Step through a collection |
| `Mono_Globalization_Unicode_ContractionComparer___ctor(obj)` | The shared empty constructor; means "plain new object" |
| `ScreenChange___ctor(obj, a, b)` | A shared two-field constructor. Seen for `FactGroupPath`, `FactGroup` and citation entries |
| `play_DateFormat___ctor(obj, a, b, c)` | A shared three-field constructor |
| `play_night_CalendarEvent___ctor` | Stands in for the `haxe.io.Bytes` constructor |
| `Locale__GetText(x)` | A pass-through; returns `x` |
| A block building `"Source/….hx"`, a function name and a line number, ending in `Trace__customPrint` | Debug logging. Skip it, but note the message text: it often names what the code is doing |

### Calls by slot number

A call through an object looks like
`(*(obj->klass->vtable)._38_get.methodPtr)(obj, args, …)`. The number is the
method's slot. Two things go wrong:

- **Trampolines.** `FUN_180034940`, `FUN_180034970`, `FUN_180034a10`,
  `FUN_180034a60`, `FUN_180068300` and `FUN_180056080` are generic "call
  slot N" helpers. Their first argument is the slot number, the second is
  the object, the rest are the real arguments (in the instructions: `ECX` =
  slot, `RDX` = object, `R8`, `R9` = arguments). The decompiler frequently
  drops arguments on these.
- **Wrong class, wrong name.** If Ghidra has the variable typed as the wrong
  class, the name after the slot number is wrong but the number is right.
  Look the number up in `dump.cs`, where each method has a `Slot: N`
  comment. A method's entry sits at offset `0x138 + 16 * N` in the class
  record.

Slots worth knowing:

| Class | Slots |
|---|---|
| `haxe.ds.StringMap` | 36 `set`, 38 `get`, 41 `exists`, 43 `remove` (when mis-typed as `ObjectMap` these print as `get`, `exists`, `iterator`, `toString`) |
| `haxe.ds.List` | 25 `add` (to the back), 26 `push` (to the **front**), 28 `last`, 32 `remove` (first match), 34 `join` |
| `app.Rand` | 25 `nextInt`, 26 `nextFloat`, 27 `random` |
| `data.FactSet` | 25 `get`, 26 `set`, 28 `getValue`, 29 `getValueText` |
| `data.Node` | 25 `findNode`, 26 `expandParams`, 27 `getExpanded`, 28 `consume` |

### Objects written in the code, and their field names

A Haxe object written as `{id: ..., text: ...}` is built from a list of
its fields' name numbers and a list of values. The decompiler shows the
first list only as `RuntimeHelpers.InitializeArray(arr,
Field_<PrivateImplementationDetails>_<64 hex digits>)`. Two facts make it
readable (found 2026-10-14, `screens.md` part 4):

- The 64 hex digits are the **SHA-256 of the list's bytes** (the numbers
  as 4-byte little-endian integers, in ascending order).
- A field's name number is computed from its name: start at 0, for each
  character take number x 223 + character code, keeping 32 bits; at the
  end keep the low 31 bits. Checked: `id` = `0x5bdb`, `text` =
  `0x4cf9ccad`, `dangerous` = `0x128cfd8a`, `backButton` = `0x186a4779`,
  `menu_onClick` = `0x76eaf0c9`, all as the code shows them.

So: take the candidate field names (from the code that reads the object,
which uses `getField` with the name and number), compute their numbers,
try each combination, and compare the SHA-256 with the block's name. A
match identifies the fields exactly. The values are in the second list,
in the same order; booleans are often visible as `local = 1` before
`il2cpp_value_box`.

### Static data and enum values

`*(X_TypeInfo + 0xb8)` is class `X`'s block of static values. For a Haxe
enum, the values sit in it in declaration order, 8 bytes apart, so
`+ 0x10` is the third value. The order is listed in `dump.cs`. An enum
object's number is at `obj + 0x10` (`_hx_index`).

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

## Dead end: REA's Ghidra requests time out (resolved 2026-10-12)

Moved here on 2026-10-14 from the former `STATUS.md`. Only the heading
levels and one reference to this doc were changed.

### Goal

Milestone 1: get a readable view of the game's code: (a) recover the IL2CPP
class and method names, and (b) read decompiled function bodies with those
names attached.

### Outcome

Both parts work. See `docs/il2cpp-name-recovery.md` and
this doc.

### The dead end: REA cannot analyse GameAssembly.dll on this machine

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

### What fixed it

Running Ghidra's `analyzeHeadless` directly with a project saved in
`decompiled/ghidra/`, plus two scripts in `scripts/ghidra/`.

### Not tried (no longer needed)

- A REA timeout or analyzer setting.
- Cpp2IL.
