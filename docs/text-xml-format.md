# Text.xml: the game's text entries

Studied on 2026-10-13. `Text.xml` holds the English text the code asks for by
id: menu labels, budget lines, family words, citation texts, dates and so on.
(Speech is in `Speeches.txt`, document text in `Papers.xml` and `Facts.xml`.)

Functions read in full: the `data.Lang` constructor and static setup,
`loadFromXml`, `cleanHtml`, `isMap`, `formatVerboseDate`; the `data.Repl`
constructor and `get`; the `data.LangFixed` constructor. `getReplaced`,
`makeAlias`, `makeTypo` and `buildAliasSwapSets` were read earlier
(`value-helpers.md`). One dropped number was read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## The file

```xml
<data>
<item id="budget_salary"><t>SALARY ($0)</t></item>
<item id="date_verbose"><t>$month $day, $year</t></item>
</data>
```

One `<item id="...">` per entry, each holding one `<t>` with the text.

## Loading (`Lang.loadFromXml`)

For each `<item>` under the first element of the file, in order:

- If an entry with this id **already exists, the item is ignored** (the
  first one loaded wins).
- The text is the content of `<t>` with leading white space removed, then
  cleaned: the two characters `\n`, and `<br>` and `<br/>`, each become a
  line break; `&amp;`, `&lt;`, `&gt;` become `&`, `<`, `>`. (The six
  replacements are applied in the order a lookup table is walked,
  `haxe-maps.md`; it would only matter for text like `&amp;lt;`.)
- The entry is stored twice under its id: as plain text (`lang.text`) and
  as a "fill-in" object (`lang.repl`, class `Repl`) whose `get(a, b, c)`
  fills the placeholders (`getReplaced`, `value-helpers.md`).

The `Lang` constructor loads `Text.xml` this way, sets the characters a typo
never lands on to `-`, `.` and space, and builds the alias swap sets
(`value-helpers.md`).

## Placeholders

- Numbered: `$0`, `$1`, ... filled from up to three values, or from a list
  (the family sentences use up to `$4`).
- Named: `$name`, filled from a table of names to values. Used by
  `stats_text`, `load_summary`, `endless_complete`, `date_verbose`,
  `bulletin_default`, `bulletin_notice` and `bulletin_endless`.

## The long date (`Lang.formatVerboseDate`)

`date_verbose` filled with: `month` = the entry `month_<n>` where `n` is the
month counted from **1** (the date type counts months from 0; the code adds
one), `day` = the entry `day_<d>` (`day_1` is `1st`, ...), `year` = the
year. Example: `November 23rd, 1982`.

## Values fixed in the code, not in the file (`LangFixed`)

Three web addresses (the game's homepage, its update check and a social
page), the Steam leaderboards address, and the endless-mode unlock code
`62131` (the same number the `ignore-ezic` ending shows). The web addresses
and leaderboards are outside the port's scope (offline, single player).

## Check against the data file

`scripts/checks/text_check.py` (run 2026-10-13):

- 192 entries, each exactly one `<t>`; no repeated id, no comment, no
  attribute other than `id`.
- **None of the six replacements is needed by the English file**: it has no
  `\n`, `<br>` or `&...;` at all. 16 entries contain real line breaks. No
  entry starts or ends with white space; none is empty.
- 30 entries use numbered placeholders, none skipping a number; 7 use named
  ones (listed above).
- The long date: `date_verbose`, `month_1` to `month_12` and `day_1` to
  `day_31` all exist.
- Who asks for each id: 106 ids appear whole among the code's strings; 65
  are built from a prefix in the code (`day_`, `month_`, `family_died_`,
  `family_escape_with_`, `family_escape_without_`, `family_flee_final_`);
  1 is named in another data file.
- **20 ids have no reference found** in the code's strings or the other data
  files: `language_code`, `menu_checkforupdates`, `load_latest`, four
  `steam_...` messages, eight `emotion_...` words, `entry_approved`,
  `entry_denied`, `stamp_approved`, `stamp_denied`, `stamp_reason`. They may
  be reached in a way these searches do not see; that was not pursued.
- Three code strings look like text ids but are not in the file:
  `endless_code` (a `LangFixed` field), `title_news` and `title_tall`
  (font names. For `title_tall` this is confirmed since `screens.md`
  part 5, 2026-10-14: the page player and the ending screen look it up in
  the font list, with the error "Font not found:"; it was first written
  as "not checked further". `title_news` is still taken from its name).

## Notes for the port

- Keep "first one wins" if language packs are ever loaded through the same
  routine.
- Month entries are numbered from 1, unlike the date type.

## Not studied

- The language packs (`data.loc`, `StreamingAssets/loc/`): how a pack's text
  replaces these entries and in what order relative to `Text.xml`.
  `loadFromXml` is called through the object, so its other callers were not
  listed.
- Text wrapping and the `wrap_hyphen` entry; fonts (`Fonts.xml`).
- Nothing here has been compared with the running game.
