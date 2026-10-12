# Speech: how a "say" line becomes what someone says

Studied on 2026-10-13. A say line (`" ...` in `Travelers.txt`, a bare id in
`Errors.txt`) is turned into a speech by `BoothEnv.getSpeech`. It is either
the id of a stock **response** in `Speeches.txt`, from which one fitting
line is picked, or literal text.

Functions read in full: `play.day.BoothEnv.getSpeech` (`0x1804798f0`),
`expandComplexVars`, `getLocalizedText`, `getRemappedFactId`;
`data.SpeechLib` (static setup, constructor, `getResponse`,
`applyGenderSwitches`); the `Response` and `Speech` constructors;
`ArrayUtil.getRandomItem` for lines. Two arguments the decompiler dropped
(the id passed to `getResponse`, the path passed to `getValue`) were checked
in the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## Speeches.txt

An indented-tree file (`tab-tree-format.md`), read with the same reader
(no templates). Each top-level entry is a **response**:

```
response-id [Fact/Path]
	[=value] [?expression] text words...
```

Each child line is one possible line:

- an optional first word `=value`: the line is only possible when the
  response's fact currently has exactly this value;
- then an optional word `?expression` (written without spaces): only when
  the expression is true (`BoothEnv.testExpression`, studied with
  responses);
- the remaining words, joined with single spaces, are the text.

Responses are kept in a table by id. The file has 98 responses (14 with a
fact path) and 296 lines (75 with `=`, 14 with `?`). No id repeats.

## Looking up a line (`getSpeech(id, overridePath)`)

1. A missing id becomes `default`. A leading `$` is removed, unless the next
   character is `{`.
2. The speaker is the **inspector** if the id starts with `ask`.
3. The gender used for the text is that of the traveler's **face** (not of
   their documents). With no traveler, the female forms are used.
4. **If the id is a response:**
   - The fact path is the override if given, otherwise the response's own.
     Its current value is read (paths starting `Day/` from the day's facts,
     `Game/` or `Night/` from the saved story, anything else from the
     booth); a missing fact gives an empty value.
   - The candidates are the lines, in file order, whose `=value` is absent
     or equal to that value and whose `?expression` is absent or true.
   - **No candidate**: an empty speech (nothing is said).
   - Otherwise **one draw** picks a candidate. Then, scanning left to right,
     each word starting with `$` is replaced by the text of
     `getSpeech(that word, same override)`, which makes its own draws; the
     scan continues after the inserted text. Then `${path}` fields are
     filled in (below). The speech is made (below) with the fact path.
5. **Otherwise the id is literal text.** If it contains a `[...]` of at
   least three characters, the text is everything before it and the speech's
   fact path is what is inside; anything after the `]` is dropped. Then
   `${path}` fields are filled in and the speech is made.

## Making the speech (`Speech` constructor)

In this order:

- text starting with `@`: the **inspector** speaks; the `@` is removed;
- text containing `;`: split at `;`, each part trimmed, and **one draw**
  picks a part;
- text ending with `~`: **pause after** the line; the `~` is removed;
- gender switches: `[m]...[/m]` is kept (without the tags) for a male
  speaker and removed otherwise; `[f]...[/f]` likewise for female;
  `[x]...[/x]` (mixed) is always removed here.

## `${path}` fields (`expandComplexVars`)

Each `${path}` is replaced by the current text of that fact (same three
stores as above; missing gives empty), repeatedly until none is left.

## Where say lines come from

Script: `scripts/checks/speech_check.py`.

- **`Travelers.txt`**: 1,175 say lines. 40 start with `$` and all name a
  response; 2 more are response ids without the `$`. The other 1,133 are
  literal: 107 start with `@`, 46 end with `~`, 6 use `;` alternatives, 2 use
  `${...}` (`Game/NumDetains`, `Game/NumCitations`), and 4 end with a fact
  path in brackets (for example `[Speech/Purpose]`), none with text after
  it.
- **`Errors.txt`**: 255 say lines in `Interrogate` groups (74 distinct), all
  response ids.
- **The code and other data**: `ask-search` and `detain` exist as strings in
  the code; `trade-fingerprints` is named by `Facts.xml` (`saytrade` of
  `Fingerprints`).
- Six responses are named nowhere found: `missing-seal`, `wrong-seal`,
  `ask-wrong-weight`, `wrong-weight`, `ask-wrong-diplonation`,
  `wrong-diplonation`. Whether the code builds these names from parts was
  not searched.
- **`[m]`, `[f]` and `[x]` appear nowhere in the English data.** The
  language packs may use them; not checked.
- **Data slip**: `ask-forgery-asylumgrant` reads the fact
  `WorkPermit/Emblem/MinistryOfAdmission`, which is not a fact in
  `Facts.xml`. Its value is therefore always empty and its `=NONE` line can
  never be picked.

## Two text helpers read alongside

- `getLocalizedText(paper, fact)`: a fact id starting with `%` names a fact
  path whose value is looked up in the localization table; otherwise the
  booth fact's display text.
- `getRemappedFactId(id)`: if the day's rule table has the id (`Rule0`,
  `Rule1`, ...), the rule's name; otherwise the day's news remap if it has
  the id; otherwise the id unchanged.

## Notes for the port

- Draws: one per response with any candidate, plus those of each `$`
  reference, plus one for each `;` alternative (also in literal lines).
  None of the expressions in `Speeches.txt` uses `RANDOM100`, so the `?`
  tests draw nothing with the current data.
- Use the face's gender, not the documents', for gender switches.

## Not studied

- `testExpression` and how responses run (next step).
- What a speech's fact path is used for after the Say operation records it
  (inferred: comparing what was said with the documents, for example
  `Speech/Purpose`).
- Nothing here has been compared with the running game.
