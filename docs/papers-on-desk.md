# Papers on the desk: adding, removing and keeping them

Studied on 2026-10-13. A "paper" here is anything with facts that the booth
tracks: documents the traveler hands over, the rulebook, the bulletin, the
transcript, and three invisible holders (`Traveler`, `Speech`, `Booth`).

Functions read in full: `play.day.BoothEnv.addPaper` (`0x180471a30`),
`addBulletinForDay`, `getNextMultiPaperIndex`, `getStayingPaperIds`,
`saveStayingPaperIds`, `getPaperIdWithIndexes`, `hasPaper`, `hadPaper`,
`getPaperIsVisible`, `canPutInFiler`, `getPaperNameInFiler`,
`debugGetPaperExpirationDate`, `clearTraveler`; seven `data.FactLib` lookups
(`getFacts`, `isMultiPaper`, `getPaperMoney`, `getPaperAchievementId`,
`getClearConfusionFactPaths`, `generatePaperExpirationDate`, `getPaperStay`,
`getPaperPersistsForGame`); `data.FactSet` (`combine`, `clone`, `add`, `get`,
`set`), `Fact.clone`, the `FactValue` constructor and `isSet`; the
`PaperInfo` constructor; `PaperDef.makeIdWithIndex` and `getIdAndIndex`;
`StringUtil.compareStrings` and `toPronounCase`; `NewsArticle.textForBulletin`;
`GregorianDate.new`; `Lambda.has`. The "Remove paper" branch of `applyOp` was
re-read. Four numbers the decompiler dropped (three in the bulletin code, one
in `getIdAndIndex`) were read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## What the booth keeps

- **The desk table** (`paperInfos`): one record per paper on the desk, keyed
  by its *id with index*. A record holds the paper id, its index, the id with
  index, and an expiration date.
- **The booth's facts** (`facts`): every fact of every paper, keyed by path
  (`Passport/Name`).
- **Papers seen** (`hadPaperIds`): every paper id added since the current
  traveler arrived, in the order added. When a new traveler arrives it is
  reset to the papers that stayed (`traveler-creation.md`, step 2).

**Id with index.** Index 0 gives the plain id (`Money5`); any other index `n`
gives `id_n` (`Money5_2`). Read back by splitting at the first `_`: the text
before it is the id, the number after it the index (0 if it is not a
number, and 0 when there is no `_`).

## Adding a paper (`addPaper`)

In this order:

1. **Money.** If the document's `money` in `Facts.xml` is not 0, it is added
   to the day's bribe money. (`Money5`, `Money10`, `Money20` give 5, 10, 20.)
2. **Achievement.** If the document has an `achieve` id, the run's all-time
   statistics object is asked to award it. Not followed further:
   achievements belong to the platform layer, which is out of scope.
3. **Tokens.** If the id starts with `Token`, the rest of the id (for
   example `Arstotzka` from `TokenArstotzka`) is appended to the day's token
   list. Seven documents qualify. What the token list is used for is not
   studied.
4. **Papers seen.** The id is appended to the papers-seen list if it is not
   already there.
5. **Ordinary papers** (not `multi`):
   - If the id is already on the desk, skip to step 7. Nothing is
     regenerated.
   - Otherwise work out an **expiration date**: the traveler's duration in
     months is read as a number (0 when there is no traveler, as during booth
     setup) and passed with today's date to the document's expiration-date
     rule (`facts-xml-format.md`). That rule makes **one random draw** if the
     document has an `ExpirationDate` fact and none otherwise.
   - Put the paper on the desk with index 0 and that date.
   - Take a **fresh copy** of the document's facts from `Facts.xml`. Each
     fact starts with its written `val` (its display text is `loc` when
     given).
   - For each fact in that copy **whose value is empty**, generate one:
     `makeFactValue(path, valid = path is not currently invalid, confusing =
     false)` (`fact-values.md`). The copy is a string-keyed table and is
     walked in **its internal (hash) order**, not file order.
   - **Merge** the copy into the booth's facts. A path the booth already has
     keeps its old value; the new one is discarded (with a debug message when
     they differ). New paths are added.
6. **Stackable papers** (`multi="true"`): the index is one more than the
   highest index of that id on the desk, so the first copy is index 0. The
   record's expiration date is 0. **No facts are looked at or generated.**
   (All seven `multi` documents have no facts in `Facts.xml`, so nothing is
   lost.)
7. **Clear confusion.** For each `<clearconfusion path>` of the document: if
   that path is currently marked confusing, it is validated
   (`setFactValid`, see `operations-and-fact-validity.md`). This step runs
   even when the paper was already on the desk.

### Valid or wrong?

A generated value is wrong exactly when its path is already invalid at that
moment (on the invalid list, or invalidated through a `Facts.xml` link from
a fact on the list). With no traveler present nothing is invalid.

- **When a traveler is created**, all papers are added (step 9 of
  `traveler-creation.md`) after the invalid list was reset and before any
  error is applied. So every value starts valid, and errors make specific
  ones wrong afterwards.
- **A paper added later** (the "Add paper" operation from a response or an
  error) gets wrong values for any of its facts that are already invalid.

Values are generated even when the merge will discard them, so their random
draws still happen. This occurs when a path already exists, for example
after a paper was removed and added back, or when an error set a value on a
paper before that paper arrived.

## Removing a paper (the "Remove paper" operation)

Only if the exact id with index is on the desk: its record is removed, the
staying papers are saved (below), and the `money` of the id part is
subtracted from the day's bribe money. **The paper's facts stay** in the
booth's facts, and the papers-seen list is unchanged. If the same paper is
added again it keeps its old values (new ones are generated, consuming
draws, and discarded).

## Questions the rest of the game asks

| Question | Answer |
|---|---|
| Is paper `X` on the desk? (`hasPaper`) | `X` is a key of the desk table and `X/Exists` is not invalid. For stackable papers this only sees the copy with index 0 |
| Did the traveler give `X`? (`hadPaper`) | `X` is in the papers-seen list, `X/Exists` is not invalid, and `X` is visible |
| Is `X` visible? (`getPaperIsVisible`) | The booth fact `X/Visible` is not `NO`. A missing fact counts as visible |
| Which papers are shown? (`getPaperIdWithIndexes`) | Desk keys whose `/Exists` is not invalid and that are visible, **sorted** by plain character-code comparison. Sorting removes the hash order |
| Can `X` go in the filer? (`canPutInFiler`) | Yes, unless the current traveler's `noFilerPaperId` is `X` (always yes with no traveler) |
| Filer label (`getPaperNameInFiler`) | Localized paper name, ` - `, the traveler's name in its default layout; for ids containing `Passport`, a line break and the localized nationality |

## Staying papers

`getStayingPaperIds` lists the ids of desk papers whose `stay` is `game`.
`saveStayingPaperIds` joins them with `;` and stores them in the story fact
`Game/StayingPapers`. It runs after every Add paper and Remove paper
operation. The `BoothEnv` constructor adds each listed paper back
(`traveler-creation.md`, step 10).

- The list is in the desk table's hash order.
- A stackable paper is listed once per copy, under its plain id, so adding
  them back recreates indexes 0, 1, ... (`BizCard` is the only stackable
  paper that stays for the game.)
- With the current data none of the 15 game-staying documents draws random
  numbers or needs a traveler when added (checked; see below), so the order
  of the list does not change any random draw.

## The bulletin (`addBulletinForDay`)

Called once by the `BoothEnv` constructor. The day's bulletin is a list of
notice-page texts built from `Days.csv` (`days-csv-format.md`); it is empty,
never missing, when the day has no bulletin text.

1. Add paper `Bulletin`.
2. For each notice text `i` (counting from 0): if it contains `[PAGESNOTE]`,
   remove the marker and set `Bulletin/PagesNote` to `BulletinPagesNote.png`.
   Set `Bulletin/Notice<i>` to the text. Its page id is `notice<i>`.
3. Set `Bulletin/Emblem<n-1>` to `BulletinEmblem`, where `n` is the number
   of notice pages: the emblem goes on the last notice page. With no notice
   pages this is `Bulletin/Emblem-1`, which no page shows.
4. The page list is the notice pages, then the day's extra page ids (`BPAGES`
   plus `touchtut` and `criminals` as described in `days-csv-format.md`).
5. In story mode only (not endless), if the day's news has articles: add page
   `news`, and for each article whose bulletin text (its title, or its
   subtitle when there is no title) is present, set `Bulletin/<the article's
   fact id>` to it. News itself is not studied.
6. For each page `i`, set `Bulletin/PageNumber<Page>` to `"<i+1>/<count>"`.
   `<Page>` is the page id with its first letter, and every letter after a
   space, in upper case (`notice0` becomes `Notice0`).
7. Set `Bulletin/PageMask` to the page ids joined with `-`. (Unlike
   `Rules/PageMask`, there is no trailing `-`.)

## Check against the data files

Script: `scripts/checks/papers_on_desk_check.py` (see its README entry).

- `Facts.xml`: 7 `multi` documents (`BrothelFlyer`, `Money5`, `Money10`,
  `Money20`, `Citation`, `FilerEnvelope`, `BizCard`), none with facts.
  3 `money` documents. 7 `Token...` documents.
- Of the 191 written facts, 45 have a value and 146 are empty, so 146 are
  generated when their document is added.
- **Only `VaccineCert` has two facts that make random draws when generated
  valid** (`VaccineDates` and `VaccineDrugs`). Which of the two is generated
  first depends on the hash order above: `VaccineDates` (`haxe-maps.md`).
- No `game`- or `day`-staying document has a fact that draws when valid, an
  `ExpirationDate`, or a fact that needs a traveler (40 documents checked).
- `<clearconfusion>`: 25 entries on 3 documents (`Fingerprints`,
  `IdentityRecord`, `Photo`), each clearing facts on other documents.
  Every one of the 22 `~` paths in `Errors.txt` is cleared by some document.
  Two cleared paths are never made confusing: `Photo/HeadFront`, and
  `Rules/RuleFingerprintKolechia`, whose fact is commented out in
  `Facts.xml`. Both are harmless (the test "is it confusing?" is simply
  false).
- `Papers.xml`: the `Bulletin` paper has 13 pages, and each has a mark
  showing exactly `PageNumber<Page>` as built in step 6. Its pages show
  `Notice0`, `Notice1`, `Emblem0` and `Emblem1`. No day has more than two
  notice pages. Every `BPAGES` id is a bulletin page. `[PAGESNOTE]` appears
  in 5 cells of `Days.csv`.

## Notes for the port

- **Order of generation within a paper is the hash order of a Haxe
  `StringMap`** built by inserting the document's facts in file order. To
  reproduce the random draws (at least for `VaccineCert`, and for every paper
  added after errors exist), the port needs that order. It is worked out in
  `haxe-maps.md`: 19 documents differ from file order, and for `VaccineCert`
  the dates are generated before the drugs.
- Generate values for empty facts even when the path already exists, and
  then keep the old value.
- Removing a paper does not remove its facts.
- A stackable paper's index is one more than the highest present, not the
  lowest free one.

## Not studied

- What the token list and `Bulletin/PageMask` are used for; news articles
  (`DayNews`, `NewsArticle`).
- `AlltimeStats.awardAchievement` (out of scope).
- `TravelerName.getFormatted` (the filer label) and the localization lookup.
- Every caller of `addPaper` outside `BoothEnv` (calls by slot number are
  hard to search for).
- Nothing here has been compared with the running game.
