# Facts.xml: the world, the documents' facts and what can be wrong

Studied on 2026-10-12. Source: `extracted/art/assets/data/Facts.xml` and 45
decompiled functions, each read in full:

- loaders: `data.FactLib` constructor (`0x18073ed00`), `data.WorldDef`
  (`0x1807d8780`), `PurposeDef`, `AutoPaperDef`, `DocDef` (`0x1807a5990`),
  `FactDef` (`0x1809a0b80`), `InvalidateDef`, `ConfiscationDef`,
  `DocDef.addFactDefs`, `GroupDef.makeFromNode`, `addExpandedPaths`,
  `getNationalizedFactGroup`, `makeFromFactGroup`
- interpretation: all 16 `WorldDef` query methods, `PurposeDef.getMatches`,
  `AutoPaperDef.getMatches`, `DocDef.generateExpirationDate`,
  `FactDef.getInvalidatesPath`, `FactDef.getCite`, four `FactLib` lookups
- helpers: `app.Probability`, `app.ArrayUtil.getRandomItem` and
  `makeShuffled`, `Xml.get`, `Xml.exists`, `Xml.set`, `haxe.xml.Parser`

Everything here is confirmed in the code unless marked **inferred**.

## The file is not valid XML

One attribute value contains a raw `&&` (the `when` of a `<confiscation>`).
A strict XML reader stops there (line 96). The game's own reader accepts it.
The port needs a lenient reader, or must turn bare `&` into `&amp;` first.
That is the only problem: with the two `&` characters escaped, a strict
parser reads the whole file.

## The comments matter

The file has 68 comments. Most are section labels, but some are the
designer's notes and some hide entries that were switched off. An XML reader
drops them, so they have to be read separately. The ones that change how the
data should be understood:

- `<purpose val="journalist"/>` is commented out with the note "set manually
  only". `journalist` is a real purpose, given to scripted travelers in
  `Travelers.txt` (`= purpose journalist`, twice), and deliberately kept out
  of the list that random travelers draw from.
- `<job val="engineering"/>` is commented out with the same note.
- `<vaccine val="POLIO"/>` is commented out with the note "added
  automatically". The word `POLIO` exists in the game's code.
- The rule facts `RuleDetainKolechia` and `RuleFingerprintKolechia` are
  commented out, as is the group `MustFingerprint`. The group `MustDetain`
  is still live and still refers to `Rules/RuleDetainKolechia`.
- "Moved to code" above the facts `SealsMoa` and `SealsMol`, whose values
  are empty in the file.
- Notes on groups use the word "correlation", for example "Used for
  correlation only. Can never be directly invalid."

Attribute names are **case-sensitive**: lookups go straight to a string-keyed
map and no function on the path changes case. This matters below.

## Shape of the file

```
<facts>
  <nations>        7 <nation>
  <purposes>       7 <purpose>
  <autopapers>    10 <autopaper>
  <durations>      8 <duration>
  <districts>      8 <district>
  <jobs>          17 <job>
  <vaccines>       9 <vaccine>
  <confiscations>  2 <confiscation>
  <misc .../>      1
  <rulebook>      23 <page>
  <locs>         112 <loc>
  <groups>        59 <group>, holding 162 <path>
  <paper>         63, holding 191 <fact> and 25 <clearconfusion>
                      a <fact> holds <invalidate> (56) and <cite> (8)
```

## What a "fact" is

A fact is one named piece of information with a path of the form
`Document/Name`, for example a field on a passport. `Papers.xml` marks whose
text starts with `$` name a fact path, and the fact supplies the value.

`FactLib` builds four things: the world definition, a table of documents
keyed by id, a table of every fact keyed by path, and the fact groups. It
also lists the ids of every document whose `stay` is `day` or `game`.

## `<paper>`: a document's facts

The element is called `paper`, but 3 of the 63 are not papers in
`Papers.xml`: `Booth`, `Speech` and `Traveler`. Two papers in `Papers.xml`
have no entry here: `FingerprintsBlank` and `HintMissing`.

| Attribute | Field | Default | Notes |
|---|---|---|---|
| `id` | `id` | required | |
| `stay` | `stay` | none | `day` (25) or `game` (15). Read by `Papers.xml` loading |
| `multi` | `multi` | false | 7 documents |
| `noticeerrors` | `noticeErrors` | **true** | Default for the document's facts |
| `money` | `money` | 0 | Whole number. 3 documents |
| `achieve` | `achievementId` | none | Online feature; out of scope |
| `saytrade` | `sayTrade` | none | |
| `desc` | `cite` | none | **Never present in the file** |
| `cite` | | | **Not read.** The code reads `desc` into the field named `cite`. One document (`SecondPassport`) has it |

Children: each `<fact>` is expanded (below); each `<clearconfusion path>`
adds a path to `clearConfusionPaths`.

What `multi`, `money`, `stay` and `<clearconfusion>` do when the document is
put on the desk is in `papers-on-desk.md`.

## `<fact>`

| Attribute | Field | Default | Notes |
|---|---|---|---|
| `id` | `id` | required | May be empty (15 facts): the path is then just the document id |
| `val` | `val` | empty | |
| `editable` | `editable` | false | |
| `format` | `format` | none | Seen: name layouts such as `FIRST LAST`, `Last, First`, and `28` |
| `range` | `range` | `10 30` | Point `min max`. Seen: `120 720`, `10 30`, `1 14`, `5 30` |
| `noticeerrors` | `noticeErrors` | the document's value | |
| `cite` | a citation with no condition | none | 25 facts |
| `loc` | `valLoc` | same as `val` | Never present in the file |
| `prefix` | `prefix` | empty | Never present in the file |

`path` = document id, then `/` and the fact id when the id is not empty.

**Expansion** (`DocDef.addFactDefs`), which turns 191 written facts into 203:

- If the id contains `[NATIONS]`, one fact is made per nation. In the id,
  `[NATIONS]` becomes the nation name. In the value, `[NATIONS]` becomes the
  nation name and `[ISSUINGCITIES]` becomes that nation's cities, each passed
  through the localization table and joined with line breaks. (2 facts)
- Otherwise, if the value contains `[DISTRICTS]`, it is replaced by every
  district, localized and joined with line breaks. (1 fact)
- Otherwise the fact is used as written.

So a value can be a list of acceptable choices separated by line breaks.
When a document is put on the desk, a fact with a written value keeps it;
a fact with an empty value gets a generated one (`papers-on-desk.md`,
`fact-values.md`).

### `<invalidate path when>`: what a fact's value can break

`FactDef.getInvalidatesPath(currentValue, nation, otherPath)` is true when
some `<invalidate>` of this fact has:

- `path` equal to `otherPath`, and
- no `nation`, or `nation` equal to the given nation, and
- no `when`, or `when` exactly equal to the fact's current value, and
- no `whenNot`, or `whenNot` different from the current value.

`when` is a plain value compared for equality, not an expression. 31 of the
56 have one. Every `path` in the file names an existing fact.

**Mismatch in the data.** One entry is written `whennot="Arstotzka"` (all
lower case) with path `Rules/RuleArstotzkaOnly`. The code looks up
`whenNot`, and names are case-sensitive, so the attribute is not read and
that entry carries no condition. The `nation` attribute is supported by the
code but never used in the file. In practice the lost condition changes
nothing: see `operations-and-fact-validity.md`.

### `<cite when val>`: what to say when citing the fact

`FactDef.getCite(currentValue)` returns the `val` of the first citation
whose `when` is absent or equals the current value. A `when` starting with
`*` is a "contains" test rather than equality (one entry, `*bomb`); whether
the `*` itself is stripped before the test is **not confirmed**.

If no citation matches: for paths starting `Rules/` the fact's own value is
returned; for facts named `Exists` or `Visible` the localized template
`missing` is filled with the paper name; otherwise the template `cite` is
filled with the paper name and the fact name.

## `<groups>`: sets of facts that belong together

`<group id>` holds `<path val proxy?>` entries. The file's own comments and
the method name `FactGroup.autoGetCorrelationPairs` both call this
"correlation": the sets of facts that can be compared against each other.
How they are used in play (interrogating two marked facts, and the
agree/disagree test, including what `proxy` does) is in
`player-actions.md`.

- A `val` containing `*` is treated as a **regular expression**
  (case-insensitive) and replaced by every fact path it matches, each keeping
  the same `proxy`. 12 paths. The matches come out in the fact table's
  internal order, which is hash order, so a port must not assume file order.
- `[NATION]` in a group id, path or proxy is replaced by a nationality when
  the group is requested for that nationality. 4 groups.
- One plain path, `Rules/RuleDetainKolechia` in group `MustDetain`, names a
  fact whose definition is commented out in the file.

## The world sections

Most are kept as raw nodes and read when needed.

- **`<nation name cities citizen>`**: `cities` is a `;`-separated list.
  `citizen` is **not read**: the word does not exist in the game's code.
- **`<purpose val nations chance rule chooseforinvalid>`**: `nations` is
  space-separated; `chance` defaults to 1.0; `chooseforinvalid` defaults to
  **true**. A purpose applies to a nation and rule set when the nation is in
  its list and, if it has a `rule`, that rule's name occurs in the rules
  text.
- **`<autopaper id rule purposes>`**: a document a traveler should carry. It
  applies when the purpose is in its space-separated `purposes` (or it has
  none) and, if it has a `rule`, that rule is in force. These lists include
  `journalist`, the scripted-only purpose (see "The comments matter").
- **`<duration val text purposes>`**: `val` is in months. `purposes` is
  tested as a substring, not split into words.
- **`<district val>`, `<job val>`, `<vaccine val>`**: plain lists.
- **`<confiscation id when desc error>`**: all four required. `when` is a
  condition written as an expression (this is where the `&&` is). It is
  returned as text by `getConfiscationWhen` and tested with the booth's
  condition tester (`player-actions.md`, `responses-and-events.md`).
  Ids match the `CONFISCATE` row of `Days.csv` (`DistrictAltan`, `Native`).
- **`<misc>`**: attributes fetched by name; missing ones give empty text.
  Present: `hiddenAdditionalErrorPerc`, `speechAdditionalErrorPerc`,
  `tokenOrder`. All three names are used somewhere in the code; where is not
  studied.
- **`<rulebook><page id rule confiscation>`**: decides which rulebook pages
  are shown. A page is included when it has no `rule` or its rule is in
  force, and it has no `confiscation` or that equals the day's confiscation
  id. The result is the ids joined as `id-id-...-`. The 23 ids are exactly
  the page ids of the `Rules` paper in `Papers.xml`.
- **`<loc id val section>`**: a table from internal word to display text.
  Lookup returns the word itself when there is no entry. `section` is **not
  read**.

Rule tests throughout are **substring tests** on a rules text, so
`RuleNeedIdCard` would also match inside a longer rule name.

## Random choices

These decide how many numbers are drawn from the random generator, so the
port must match them exactly.

A "draw" is one call to `random()`, giving a fraction from 0.0 to 1.0
**inclusive** (see `docs/rand.md`).

- **Pick one from a list**: one draw `r`; index = `floor(length * r)`. If
  that equals the length (only when `r` is exactly 1.0), the result is
  nothing rather than an item.
- **Weighted pick** (`app.Probability`): one draw `r`; walk the choices
  adding up weights and return the first where `r * total < running sum`.
- **Shuffle** (`ArrayUtil.makeShuffled(count)`): start with `0..count-1`;
  for `i` from 0 to `count-1`, with `n = count - i`, one draw `r`, swap
  positions `n - 1` and `floor(r * n)`.
- **Random nationality**: with no purpose, a random nation; with a purpose,
  a random entry of that purpose's nation list.
- **Random purpose**: a weighted pick over purposes that apply, using
  `chance`. When choosing for an invalid traveler, purposes with
  `chooseforinvalid` false are left out. There is also a filter on error
  patterns: when patterns are given and at least one error matches them, a
  purpose is kept only if some matching error's required papers are all
  among the purpose's automatic papers. Because an error's required-paper
  list appears never to be filled (`errors-txt-format.md`), that test passes
  for the first matching error, so with the current code and data **the
  filter excludes nothing**. (Worked out from the decompiled
  `WorldDef.getRandomPurpose`; depends on the required-paper list really
  being empty, which is an open item in `PROGRESS.md`.)
- **Random duration**: a pick from durations whose `purposes` contains the
  purpose. **Issuing city**: a pick from the nation's cities.
- **Access nations**: shuffle the nations, drop Arstotzka unless asked to
  include it, then remove random entries until `count` remain (never
  removing Arstotzka when it is included).
- **Expiration date** (`DocDef.generateExpirationDate`): take the `range` of
  the document's `ExpirationDate` fact as `min max` days. If a duration in
  months is given and `max > 700`: `min = max(min, months * 31 + 5)` and
  `max = max(min + 60, max)`. Result: today plus
  `min + r * (max - min)` days. With no such fact, today.

## Cross-check of the file against the code

- All 63 document ids are distinct. Every `stay` is `day` or `game`.
- Every boolean is written `true` or `false`.
- Every `<invalidate>` path names a real fact after expansion (203 paths).
- All 23 rulebook page ids match the `Rules` paper's pages, both ways.
- Attributes in the file that are never read: document `cite`; invalidate
  `whennot`; nation `citizen`; loc `section`.
- Attributes the code supports that never appear: document `desc`; fact
  `loc` and `prefix`; invalidate `whenNot` and `nation`.
- One reference to a switched-off entry: group path
  `Rules/RuleDetainKolechia`.
- The seven `<purpose>` entries are only the purposes random travelers can
  get. `journalist` is used by `<autopaper>` and `<duration>` lists and set
  by hand for scripted travelers.
- Every rule named in the `RULES` row of `Days.csv` is a fact under `Rules`.
  Three rule facts are never used by any day: `RuleNoAntegria`,
  `RuleNoKolechia`, `RuleNoObristan`.

## Not studied

- How fact groups are used to decide what is an error. (Value generation and
  invalidation are now in `fact-values.md` and
  `operations-and-fact-validity.md`.)
- The expression evaluator for `<confiscation when>`.
- Most of `FactSet` and `FactValue`, and the `FactLib` methods not listed
  here or in `papers-on-desk.md`.
- No reader has been written for the port, so none of this is tested end to
  end.
