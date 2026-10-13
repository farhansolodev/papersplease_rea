# Art.dat: the game's content archive

Confirmed on 2026-10-12 by decrypting and unpacking the real file.

Almost all game content (images, fonts and the data files that define days,
papers, travelers and text) is in one encrypted archive called `Art.dat`. The
game's code is mostly an engine that runs on this data.

## Where it is

`Art.dat` is a Unity TextAsset (a raw data blob) inside
`game/PapersPlease_Data/sharedassets0.assets`. In this build:

- asset name `Art.dat` at file offset `0x4C0C`
- 4-byte little-endian length at `0x4C14`: 3,309,984
- data at `0x4C18`

Those offsets were found by searching for the name, not by parsing the Unity
file format, so they are specific to this exact file.
SHA-256 of the extracted blob:
`C55EECB5100F6DBA08ACEA3AA2EFE7675FA2F2109125717A479CBDB457727E99`.

## How the game loads it

From the constructor of class `Res` (`0x180775820`):

1. `platformDisk.getAssetBytes("assets/Art.dat")`. On this platform that is
   `HostUnity.UnityPlatformDisk`, which returns the TextAsset's bytes. Any
   other name must start with `loc/` and is read from `StreamingAssets`.
2. `app.XXTea.decryptInPlace(bytes, key)` decrypts the whole buffer.
3. A 16-bit length, then that many bytes of text, are read and passed to
   `haxe.Unserializer.run`, giving an array of `{name, size}` objects.
4. For each entry with `size > 0`, `size` bytes are read and turned into an
   asset by `Res.toAsset(name, bytes, mogrifier)`, stored in a name-to-asset
   map. Names containing `/layout/` are skipped unless an override directory
   (phone or tablet layout) is active, in which case they replace the default
   asset of the same name.

## Encryption

Standard XXTEA (a small block cipher), applied once to the entire file as a
single block of 32-bit little-endian words.

- Constant `DELTA = 0x9E3779B9`, rounds `6 + 52 / word_count` (6 here).
- Key: take the MD5 hash of the key string as 32 hex characters, cut it into
  four 8-character pieces, and read each as a hexadecimal number.
- The key string is string literal 8555 in Il2CppDumper's output (16
  characters). It is deliberately not written in this repo; the scripts read
  it from `dumps/il2cppdumper/stringliteral.json`.

The same cipher class has `decryptString`, used by `play.EncryptedStore.get`.
That store holds the saves, the settings, the statistics and the name
order's position, each as a `.sav` file of hexadecimal text with a
different key string (studied 2026-10-14, `save-format.md`).

## Archive layout after decryption

| Part | Size | Contents |
|---|---|---|
| Length | 2 bytes, little-endian | Size of the table of contents (30,159) |
| Table of contents | 30,159 bytes | Haxe-serialized array of `{name, size}` |
| File data | rest | Files back to back, in table order, no padding |

The table uses Haxe's text serialization: `a...h` array, `o...g` object,
`y<len>:<url-encoded text>` string, `R<n>` reference to the n-th earlier
string, `i<n>` integer.

## Contents

614 files, 3,279,823 bytes of file data; the lengths add up to the file size
exactly.

| Type | Files | Bytes | Notes |
|---|---|---|---|
| `.png` | 572 | 1,151,136 | All 572 start with a valid PNG signature |
| `.fnt` | 12 | 1,712,354 | Text XML starting `<font>`; bitmap font descriptions |
| `.xml` | 14 | 186,114 | Data definitions |
| `.txt` | 14 | 213,624 | Data and text |
| `.csv` | 2 | 16,595 | `Days.csv`, `Endless.csv` |

Folders: `assets/` (155 files), `assets/papers/` (225), `assets/faces/` (60),
`assets/layout/phone/` and `tablet/` (77), `assets/intro/` (29),
`assets/fonts/` (24), `assets/achievements/` (13), `assets/data/` (31).

`assets/data/` holds the game definitions: `Days.csv`, `Papers.xml`,
`Facts.xml`, `Travelers.txt`, `TravelerGraph.txt`, `Paths.xml`, `Faces.xml`,
`Bodies.xml`, `Ends.xml`, `Nights.txt`, `News.txt`, `Speeches.txt`,
`Errors.txt`, `Sounds.xml`, `Text.xml`, `Fonts.xml` and others. All 31 files
there have been studied since; `data-files.md` lists each one with its
write-up.

There is no audio in `Art.dat`. `Sounds.xml` exists, so the audio is
elsewhere, most likely `sharedassets0.resource` (12 MB). Not verified.

## Commands

```powershell
python -I scripts\extract\decrypt_art.py extracted\Art.dat dumps\il2cppdumper\stringliteral.json extracted\Art.dec
python -I scripts\extract\unpack_art.py extracted\Art.dec extracted\art
```

`extracted/Art.dat` itself was cut out of `sharedassets0.assets` by hand using
the offsets above; there is no script for that step yet.

## Not done

- Each `StreamingAssets/loc/<lang>.zip` holds localized replacements (130
  PNGs, a CSV, an XML and two text files for English). They are plain zips;
  how `Res.loadLanguage` merges them is not studied.
- `Res.toAsset` was read in full for the text files (`tab-tree-format.md`),
  but how it turns bytes into images and fonts is not written up anywhere.
