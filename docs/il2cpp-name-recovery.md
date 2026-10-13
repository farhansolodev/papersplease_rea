# IL2CPP name recovery

How the class and method names for `GameAssembly.dll` were recovered.
Confirmed on 2026-10-12 against game version v1.4.11.124 (63294).

## Inputs (copies in `game/`, gitignored)

| File | Size | SHA-256 |
|---|---|---|
| `game/GameAssembly.dll` | 13,838,848 | `2A815DDE6361553C1B66DC765AF02D650717082D62EBAFAAECE4D8CE3B85A48F` |
| `game/PapersPlease_Data/il2cpp_data/Metadata/global-metadata.dat` | 3,247,268 | `9032B4D6D22CDF9527CB6483353D20F48F9182C961C5D712733E4A0AE48D3DA3` |

Both hashes match the originals in `C:\GOG Games\PapersPlease`.

## What the files look like

- `global-metadata.dat`: starts with the standard signature `AF 1B B1 FA`,
  format version 27. Not encrypted or obfuscated.
- `GameAssembly.dll`: plain x64 PE, image base `0x180000000`, not packed.
  Sections: `.text` (1.3 MB, engine glue), `il2cpp` (8.7 MB at RVA `0x155000`,
  all the compiled C# code), `.rdata`, `.data`, `.pdata`, `.reloc`.

## Tool

Il2CppDumper v6.7.46, file `Il2CppDumper-net6-v6.7.46.zip` (406,027 bytes,
SHA-256 `DB9BBBC538E33ABFB057C7757AE5D6C1F16A05FDC0D13AF8A5A67EA31FAABA0C`)
from https://github.com/Perfare/Il2CppDumper/releases. Installed at
`C:\tools\Il2CppDumper-6.7.46` (shared, outside this project). Runs on the already-installed .NET 6
runtime. One change to its `config.json`: `RequireAnyKey` set to `false` so it
does not wait for a key press.

## Command

```powershell
dotnet C:\tools\Il2CppDumper-6.7.46\Il2CppDumper.dll `
  game\GameAssembly.dll `
  game\PapersPlease_Data\il2cpp_data\Metadata\global-metadata.dat `
  dumps\il2cppdumper
```

The tool reported metadata version 27, il2cpp version 27.1,
`CodeRegistration` at `0x180b51e00`, `MetadataRegistration` at `0x180b585f0`.

## Output (`dumps/il2cppdumper/`, gitignored)

| File | What it is |
|---|---|
| `dump.cs` | Every class with its fields (and field offsets) and methods (and code addresses). No method bodies. |
| `script.json` | Address-to-name table: 34,101 method entries, 10,106 string literals. |
| `il2cpp.h` | C struct layouts for every class, for use in a decompiler. |
| `stringliteral.json` | All string constants used by the code. |
| `DummyDll/` | Empty-bodied .NET assemblies with the same class shapes. |

Addresses in `script.json` are RVAs (offsets from the image base). Add
`0x180000000` to get the address a decompiler shows.

## Checks

- 39 assemblies, 4,299 type definitions, 29,623 methods with an address.
- All 25,256 unique method addresses fall inside the `il2cpp` code section.
- 22,855 of them (90.5%) are exactly a function start listed in the DLL's
  `.pdata` exception table. The other 9.5% are probably small functions that
  need no `.pdata` entry; this is not verified.
- Not yet checked: a named function's decompiled body matching what its name
  says.

## Findings about the game

- **The game is written in Haxe**, compiled to C#, then to native code by
  IL2CPP. Evidence: `haxe.*` runtime namespaces, classes deriving from
  `HxObject`, `__hx_getField` / `__hx_setField` helper methods, and closure
  classes named like `Booth___hx_ctor_play_day_booth_Booth_283__Fun` (the
  number looks like a source line; not verified).
- The game's own code is `Assembly-CSharp.dll`: 1,351 types (type indexes
  2946 to 4296). Largest namespaces: `play.day.booth` (237), `data` (175),
  `test.auto` (103), `play.day` (90), `play.day.border` (85), `app` (59),
  `play.screen` (48), `play.night` (41).
- `com.rlabrecque.steamworks.net.dll` (Steamworks.NET) is linked into this GOG
  build, and `app.plat` has `PlatformSocial*` classes (achievements,
  leaderboards). This is the online layer. Per project rule 4 it is out of
  scope and will not be analysed or ported.
- `app.XXTea` exists (with a helper class in `app._XXTea`). XXTEA is an
  encryption algorithm. Corrected 2026-10-14; this line used to say its use
  was unknown. Found since: it decrypts the content archive `Art.dat`
  (confirmed by decrypting the real file, `art-dat-format.md`), and
  `play.EncryptedStore.get` calls its `decryptString` (what that store holds
  is not studied; saves are a later step). Whether anything else calls it
  has not been searched.
- `format.png` and `haxe.zip` are in the game code, so it likely reads PNG and
  ZIP data itself (the `StreamingAssets/loc/*.zip` files). Not verified.
