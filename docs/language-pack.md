# The language pack, and what the English one changes

Studied on 2026-10-16 (part 8 of the screens step; not a screen itself).
Code reading, plus a comparison of `en.zip` with the main archive and a
script that applies the English pack to the data files (now the reference
script `scripts/reference/locpack.py`, below). **Nothing
here has been compared with the running game.**

Why it matters for an English-only port (the user's decision of
2026-10-16, `PROGRESS.md`): **English is loaded as a language pack too.**
The game always loads a pack, so the English the player sees is the data
files *after* `en.zip` has been applied to them. The pack fixes a few
typos and supplies one picture that is not in the main archive.

Terms used below:

- **Language pack**: one `.zip` file per language in the game's
  `StreamingAssets/loc/` folder, named `<code>.zip` (`en.zip`, `de.zip`...).
- **Main archive**: `Art.dat`, the encrypted bundle of pictures, fonts and
  data files (`art-dat-format.md`).
- **Context**: a label that says where a piece of text belongs, such as
  `traveler:WATCH_GIVER0` or `facts`. The pack matches text only inside the
  same context.

## What was read

Read in full: `Res.loadLanguage`, `Res.getAsset`, `getText`, `getImage`,
`getXml`, `getTabParser`, `getCsvTable`; `data.loc.Pack` (`load`,
`loadInternal`, the class setup with its two patterns, `cleanHtml`,
`makeEnKey`, `localize`, `localizeXml`, `localizeTab`, `localizeCsv`,
`localizeFromAnyContext`); `data.loc.Extractors.init`, `ignoreDollarSigns`
and the six small match functions it uses (`Extractors_init_32`, `_40`,
`_52`, `_57`, `_64`, `_96`); `TabExtractor` (`make`, `run`, `runSubs`),
`TabEntry` (constructor, `get_text`, the start of `set_text`),
`XmlExtractor` (`make`, `run`, `runChildren`, `select`), `XmlEntry`,
`CsvExtractor.run`, `CsvEntry`; `play.Bootstrap.setLanguage`; the language
choice in the `Bootstrap` constructor; `Platform.defaultLanguageCode` and
`convertLangSysCodeToDiskCode`. All in `decompiled/all/` (`top.clean.c`,
`data.clean.c`, `play_misc.clean.c`, `app_plat.clean.c`). No Ghidra run.

Not read: `Res.toAsset` beyond its name (how bytes become a picture),
`set_text` of `TabEntry` past its first lines, `data.CsvTable` (its
trimming is taken from `days-csv-format.md`), the "mogrifier" (only the
phone and tablet have one, `papers-xml-format.md`), `Game.createDefaultEnts`.

## When a language is loaded

`Bootstrap.setLanguage(code)` runs at the end of the `Bootstrap`
constructor, and again whenever the language setting changes
(`Game.applySettings`, `screens.md` part 4). It:

1. loads the pack (`Res.loadLanguage`, below);
2. builds a new `Db` (the game's data, read from the files through `Res`);
3. builds a new day run, which **draws a story seed**
   (`run-and-seeds.md`), and a new booth run;
4. builds a new `EntEnv`.

**Which language at start-up.** The `Bootstrap` constructor makes the
settings with a default language code, then checks the saved code against
the list of available packs (the `.zip` names in `StreamingAssets/loc/`,
`languages-list.md`). If the saved code is not in the list, the setting is
set to the default. The default (`Platform.defaultLanguageCode`) is the
system's two-letter language code matched against the available packs: the
first pack whose name equals it, or starts with it, or that it starts with;
**`en` if none matches**. So on a German Windows a fresh install starts in
German. (Read in the code; not run.)

## How a pack is loaded

`Res.loadLanguage(code)`:

1. Reads `loc/<code>.zip` from `StreamingAssets`. If that file is missing,
   reads `loc/en.zip` instead.
2. `Pack.load` opens the zip (Haxe's own zip reader, `haxe.zip.Reader`):
   - Every entry must be **stored, not compressed**; otherwise the load
     fails with "This language pack has compressed entries, which are not
     supported." (All 134 entries of `en.zip` are stored.)
   - Each entry's name loses a leading `/` or `./` and gets `assets/` in
     front: `/data/Text.xml` becomes `assets/data/Text.xml`, the same name
     the main archive uses.
   - `assets/data/Loc.csv` must exist ("Loc.csv not found.") and so must
     `assets/data/LocVersion.txt` ("Unknown language pack version."). The
     version is read as a whole number and stored; nothing reads it except
     the by-name field lookup.
   - `Loc.csv` is read as a CSV table (every cell trimmed,
     `days-csv-format.md`). Every row of the table gives
     `strings[context][key] = text` (whether the header row counts as a
     row was not read; it would only add a context named `CONTEXT`),
     where context is column 0, key is
     `makeEnKey(column 1)` and text is `cleanHtml(column 2)`. A later row
     with the same context and key replaces an earlier one. Then `Loc.csv`
     is dropped from the pack's files.
3. Every other file of the pack is turned into an asset (`Res.toAsset`, as
   for the main archive) and kept by name as the **localized assets**.
4. If tracing is on, logs `Loaded <n> localized assets (<code>)`. (Not seen
   in the logs kept in `extracted/autorun/`.)

**`makeEnKey(text)`**: remove every `\n` (a backslash and an n, as two
characters), every `<...>` tag and every `&...;` entity; then remove every
character that is not `A`-`Z`, `a`-`z`, `0`-`9` or `@`; the key is the
CRC-32 of what is left. So spaces, punctuation and line breaks do not
count, but letter case does. `Damnit.` and `Damn it.` have the same key.

**`cleanHtml(text)`**: replaces `\n` (two characters), `<br>` and `<br/>`
with a line break, `&amp;` with `&`, `&lt;` with `<`, `&gt;` with `>`.
Other entities, such as `&nbsp;`, stay as they are.

## How the game uses it

**Every file lookup tries the pack first.** `Res.getAsset(name)` returns
the pack's file of that name if there is one, otherwise the main archive's,
otherwise fails with "Res asset not found". Pictures and plain text go
through it. So a pack can replace any picture or file, or add one.

**Three kinds of data file are also rewritten as they are read:**

| Reader | What happens after reading |
|---|---|
| `getXml` | parse, then the pack's `localizeXml(xml, file name)` |
| `getTabParser` | parse, then `localizeTab(tree, file name)` (before templates are expanded) |
| `getCsvTable` | parse, then `localizeCsv(table, file name)` |

Each of these runs the **extractors** made for that file name (below).
An extractor picks text pieces out of the file, each with a context, and
for each piece `Pack.localize` does this: skip it if empty; look up the
context; if the context exists and has the piece's key, **replace the
piece's text** with the pack's text; otherwise leave it. (In the "not
found" case the code builds a message, `<code> <context> [<text>] (0x<key>)
NOT FOUND`, and then does nothing with it.)

`Text.xml` is read with `getText`, not `getXml`, so it is not rewritten:
the pack's own `Text.xml` simply replaces the archive's (`text-xml-format.md`).
`Errors.txt` and other files read without these readers are not touched.

### The extractors (`data.loc.Extractors.init`)

27 extractors, made once. Tab files (the indented-tree format,
`tab-tree-format.md`): the context is the prefix plus the first word of the
top-level entry; every line below it, at any depth, is tested.

| File | Context | Which lines, which words |
|---|---|---|
| `Speeches.txt` | `speech:<id>` | Every line. The text starts at word 0, or 1 if word 0 starts with `=` or `?`, one further if that word starts with `?`; a line whose only text word starts with `$` is skipped |
| `Travelers.txt` | `traveler:<id>` | Lines whose first word is `"` (spoken lines): words 1 to the end; skipped if the only word starts with `$` |
| `Travelers.txt` | `note:<id>` | Lines `= EzicNote/Message "..."`: words 2 to the end, kept as one quoted word |
| `News.txt` | `news:<id>` | Lines starting `*` (headline) or `-` (subtitle): words 1 to the end |
| `Nights.txt` | `night:<id>` | Lines starting `"`: words 1 to the end. Lines starting `>` whose next word is not `YES` or `NO`: words 1 up to a `\|` (budget lines) |

The text of a tab line is its words joined with single spaces. A replaced
text is split into words again.

XML files: the context is the prefix plus the `id` of each element found
by the first path (empty path: the file's top element), and the text is
the attribute named last in the second path.

| File | Context | Elements and attribute |
|---|---|---|
| `Facts.xml` | `facts` | `locs/loc/val`; `paper/fact/cite`; `paper/fact/cite/val`; `paper/cite`; `paper/fact/val` (not if the value has `[` or `.png`); `confiscations/confiscation/desc` and `/error` |
| `Papers.xml` | `paper:<id>` | `page/mark/text` (not if the value has `$`) |
| `Ends.xml` | `end:<id>` | `page/text` (not if it has `$`) |
| `Intro.xml` | `intro` | `page/text` (not if it has `$`) |
| `Faces.xml` | `face:<id>` | `head`, `eyes`, `mouth`, `nhead`, `neyes`, `nmouth` of each `sheet/face` |
| `Endlesses.xml` | `endless:<id>` | `name`, `desc`, `bulletin` of each `style`; `name` of each `course` |

CSV files: for each day column, `BULLETIN0` (context `bulletin:<day>A`) if
it is not empty, and for `Days.csv` also `BULLETIN1` (`bulletin:<day>B`).
`Endless.csv` gives `bullend:<column>A` only.

## What is in en.zip

134 files, all stored (not compressed):

| Files | Compared with the main archive |
|---|---|
| 129 pictures (`.png`) | **byte for byte the same** as the archive's file of the same name |
| `papers/BulletinInnerDiploTut.png` (150 x 200) | **not in the main archive.** `Papers.xml` asks for it (the bulletin page `diplotut`). The `de`, `fr` and `ko` packs have it too |
| `data/Text.xml` | byte for byte the same as the archive's |
| `data/Loc.csv` | 2,576 rows (a header and 2,575 entries), 749 contexts |
| `data/LocVersion.txt` | `1` |
| `data/UsedChars.txt` | 422 bytes: one line of the characters used (Latin, Polish, Turkish, Cyrillic letters). Nothing in the program names it (no string in the string table contains `UsedChars`); it is loaded as an asset and never asked for |

In `Loc.csv`, column 2 equals column 1 in all but 6 rows.

## What applying en.zip changes

`scripts/reference/locpack.py` applies the 27 extractors above to the data
files in `extracted/art/assets/data/` and the English `Loc.csv`, with the
key and clean-up rules above, and compares the pack's files with the
archive. (It was first a one-off script; it was kept as a reference
script at the user's request the same day, and gives the same result.)

    python -I scripts/reference/locpack.py extracted/art/assets game/PapersPlease_Data/StreamingAssets/loc/en.zip

What it does not model: `data.CsvTable` itself (Python's CSV reader with
every cell trimmed), Haxe's XML reader (a lenient clean-up before Python's,
as the checks do), and writing a changed text back (`TabEntry.set_text`).
Result:

- 2,102 text pieces found their row in the pack; 8 did not (they keep
  their text: the spoken lines `ask-missing-passport` and
  `ask-missing-entrypermit`, three `VALID` and the name `Corman Drex` in
  `Facts.xml`, and two values on the `SecondPassport` paper).
- **23 texts change:**

| Context (file) | Before | After |
|---|---|---|
| `traveler:EZIC_DIPLO_FOLLOW` (`Travelers.txt`) | `Appove the visa.` | `Approve the visa.` |
| `traveler:KID_KILLER2`, 2 lines | `Damnit.` | `Damn it.` |
| `traveler:WATCH_GIVER0` | `All Arsotzkans are same.` | `All Arstotzkans are same.` |
| `facts` (`Facts.xml`, `<loc id="Gender">`) | `Gender` | `Sex` |
| `facts` (`<loc id="district">`) | `$0 DISTRICT` | `$0  DISTRICT` (two spaces) |
| `note:...`, 13 EZIC notes (`Travelers.txt`) | `\n` written as two characters | a real line break |
| `endless:timed`, `perfection`, `endurance` (`Endlesses.xml`, `bulletin`) | `\n` as two characters | a real line break |

The data files' own comments confirm the first group was meant: the
`Appove` line in `Travelers.txt` is marked `# typo fixed in en.csv to avoid
breaking localizations`, and the `Arsotzkans` line `# typo fixed in English
localization`. In other travelers, `Damnit.` stays, because only
`KID_KILLER2`'s context has the changed row.

The `locs` table turns internal words into display text
(`facts-xml-format.md`), so `Gender` is shown as `Sex` wherever the game
displays that fact's name; where exactly was not followed.

For the EZIC notes the change is **probably invisible**: the page drawing
(`PaperInnerVisuals`) also turns a two-character `\n` into a line break in
one kind of text mark, and that looks like the path a note's message takes
(inferred; not followed). For the endless descriptions, whether anything
else would have converted `\n` was not followed.

**The other 345 contexts are not used by any extractor.** The pack's
table is read only by `localize` (which gets its contexts from the
extractors) and by `localizeFromAnyContext`, whose one caller is in test
code. The prefixes `text:`, `image:`, `achievement:` and `tweak-`, and the
two names below, are not strings anywhere in the program (searched in the
string table). They are:

| Kind | Count |
|---|---|
| `text:<id>`, one per `Text.xml` entry | 192 |
| a picture's name, such as `RulesInnerBooth` | 115 |
| `image:<file>.png` | 19 |
| `achievement:<id>` | 13 |
| `tweak-...` | 4 |
| `font-stylesheet-override`, `baked-captures-url` | 1 each |

All 115 picture names and all 19 `image:` names are pictures in `en.zip`.
Inferred from that: these rows list the text drawn inside each picture, for
translators who redraw it. That is also where the remaining changed rows
are (for example `RulesInnerBooth`'s `<br>` and `&amp;`, and
`BulletinInnerFilerTut`'s wider gap in `ALTAN DISTRICT`), so they change
nothing in English.

## For the port

- **English only** (the user's decision): the port needs the English pack's
  effect, not the pack mechanism. Two ways, a design decision:
  1. apply `en.zip` once when the assets are prepared, giving data files
     that already hold the 23 changed texts and adding
     `papers/BulletinInnerDiploTut.png` to the pictures; or
  2. load `en.zip` at run time and apply it as the original does.
  The first is simpler; either must give the 23 changes above.
  `scripts/reference/locpack.py` lists them, so a check can compare the
  port's data with it.
- The picture `papers/BulletinInnerDiploTut.png` must come from a pack;
  without it the bulletin page `diplotut` has no picture.
- The pack load draws nothing random by itself, but `setLanguage` draws the
  first story seed (`run-and-seeds.md`). A port with one fixed language
  still needs that draw.
- The original picks the system's language at the first start. An
  English-only port always uses English.

## Not studied

- Whether the text changes show in the running game. The quickest look:
  `traveler:WATCH_GIVER0` says "All Arstotzkans are same." (with the `t`);
  `KID_KILLER2` says "Damn it."; a cited sex mismatch should read `Sex`, not
  `Gender` (where that word appears was not followed).
- `Res.toAsset` for pictures and fonts, so whether a pack picture is
  treated in any way differently from an archive picture (inferred: no,
  the same function is called).
- `TabEntry.set_text` in full (how a replaced spoken line is split into
  words; read only far enough to see it re-splits by the same pattern as
  the tab reader).
- Whether a quoted note keeps its quotes when replaced (`quoted` flag).
- What the 8 "not found" pieces mean for other languages.
- Other languages' packs: not needed (English only).
