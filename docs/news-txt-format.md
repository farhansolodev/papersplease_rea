# News.txt and the day's headlines

Studied on 2026-10-13. `News.txt` holds every newspaper headline. This doc
covers the file, which headlines a day gets, their order, and the names the
booth's bulletin uses for them. Drawing the newspaper is in
`newspaper-picture.md`.

Functions read in full: the `data.NewsArticleLib` constructor and
`getArticles`; the `data.NewsArticle` constructor, `compare` and
`get_textForBulletin`; the `play.day.DayNews` constructor and
`getStorageFactPath`; `play.day.Day.addTravelerNews`;
`data.DayLib.getNewsIds`; `data.FactSet.getValueStringArray`;
`app.StringUtil.compareStrings`; `Array.sort` and `Array.quicksort`;
`BoothEnv.getRemappedFactId` and `Paper.getRemappedFactId`. Read in part: the
`Day` constructor (where it makes the news) and
`LoadScreen.loadButton_onClick` (where it makes a second one). Four numbers
the decompiler dropped were read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## The file

`News.txt` is an indented tree (`tab-tree-format.md`): `#` starts a comment,
`#*` to `*#` is a block comment, words are split on spaces.

```
KILLERATHLETE                                  <- entry id, at the left margin
	* Republian Track Star Wanted For Murder!   <- an article with a title
		- Vince Lestrade's Whereabouts Unknown   <- its subtitle
		@ Face:M-3-3-10-10                       <- its picture
		= NewsKA0                                <- its fact name
	* Vince Lestrade: Profile                    <- a second article
		- Girlfriend Killed In Jealous Rage?
		= NewsKA1
KILLERATHLETE_APPROVED
	- Vince Lestrade Spotted in Arstotzka        <- an article with only a subtitle
```

Each line directly under an entry is one **article**:

| First sign | Meaning |
|---|---|
| `*` | The rest of the line, words joined by single spaces, is the **title** |
| `-` | The rest of the line is the **subtitle**; the article has no title |
| anything else | An article with neither (none in the file) |

Lines under an article:

| Sign | Meaning |
|---|---|
| `-` | Subtitle (rest of the line) |
| `@` | Picture: the next word. All five in the file are `Face:` followed by a face spec of five parts (`faces.md`) |
| `=` | Fact name: the next word |
| `$` | Stamp image: the next word. Always `NewsEzicStamp.png` |
| anything else | Ignored (none in the file) |

Each article gets a **score**: 1000 if it has a fact name, plus 100 for a
title, plus 10 for a subtitle, plus 1 for a picture. The stamp does not
count.

The file is kept as the parsed tree. `getArticles(id)` finds the entry and
builds **new** article objects every time it is called; an unknown id gives
an empty list (and a debug-log line "News not found:").

## Which headlines a day gets (`DayNews`)

A `DayNews` is made in the `Day` constructor with the day's news random
generator (day seed + `0x1000`, `run-and-seeds.md`), the saved story's facts
and the day number.

1. **The ids.** The day's `NEWS` cell in `Days.csv`, one id per line
   (`splitAndTrim`), followed by the ids stored in the saved story under
   `Game/Day<n-1>TravelerNews`, where `n` is the day number: **the previous
   day's** traveler news. (The `- 1` was read from the instructions.)
2. **The articles** of each id, in that order, are put in one list, and the
   list is sorted (below).
3. **Fillers.** If there are fewer than 3 **ids** (ids, not articles), the
   four kinds `WEATHER, SPORTS, POLITICS, ENTERTAINMENT` are shuffled
   (`makeShuffled`, four draws), and for each missing id one kind is taken
   in shuffled order: the entry `RANDOM_<kind>`, and one draw `r` picks
   article `floor(count * r)` of it. The fillers are sorted among
   themselves and added **after** the day's articles.
4. **Names.** Going through the final list: an article without a fact name
   gets `NewsDefault<k>`, where `k` counts only the articles named this way,
   from 0. Then the table `factIdRemap` gets `News<i>` -> the article's fact
   name, where `i` is the article's position, from 0.

### Traveler news

The script command `News <id>` (`responses-and-events.md`) calls
`Day.addTravelerNews`: the id is appended to the saved fact
`Game/Day<today>TravelerNews` (ids separated by `;`) unless it is already
there, and the day's `whenAddNews` callback is called if one is set. So what
a traveler triggers today is in tomorrow's paper.

### The sort

`NewsArticle.compare(a, b)`: if the scores are equal and both have a fact
name, compare the names by character code; otherwise `b.score - a.score`
(higher score first).

`Array.sort` in this build is a plain quicksort around the middle item
(`quicksort(lo, hi)`: pivot `items[(lo + hi) >> 1]`; move `i` up while the
item is before the pivot and `i < hi`; move `j` down while the item is after
the pivot and `j > lo`; if `i <= j` swap and step both; repeat while
`i <= j`; then sort `lo..j` and `i..hi`). **It does not keep equal items in
their original order.** In particular two equal items are always swapped.

Result with the data (`news_check.py`): on days 2, 3, 13 and 16 the day's
entry has two articles with the same score, so they end up in the opposite
order to the file. For example day 2's list is "Analysts Upbeat" and then
"Grestin Checkpoint a Success!". The newspaper puts the first article of the
list in its largest rectangle (`newspaper-picture.md`), so "Analysts Upbeat"
is day 2's main headline.

## How the names are used

- **The bulletin** (`papers-on-desk.md`, step 5): in story mode, for each
  article with text, the booth fact `Bulletin/<fact name>` is set to the
  article's bulletin text: the title, or the subtitle when there is no
  title.
- **The bulletin's news page** (`Papers.xml`) shows the marks `$News0`,
  `$News1` and `$News2`. `getRemappedFactId` turns such a name into the real
  one: first the day's rule table (`Rule0`, ... , `speech.md`), then
  `factIdRemap`, otherwise the name unchanged. So `News0` is whatever
  article came first that day.
- **Scripts refer to the real names.** `Travelers.txt` uses
  `Bulletin/NewsKA0`, `Bulletin/NewsKA1` (the Vince Lestrade articles) and
  `Bulletin/NewsWB0` (the whistleblower). These three are the only `=`
  lines in the file. They are not defined in `Facts.xml`, which only has
  `Bulletin/News0` to `News3`.
- **The load screen** builds a `DayNews` for the saved game's day (from
  `Game/Day`, default 1) with a generator seeded 0, and shows the first
  article's title, cut to 27 characters plus `...` when longer than 30, in
  the text `load_summary`.

## Check against the data files

`scripts/checks/news_check.py` (run 2026-10-13), using the reference script
`scripts/reference/news.py`:

- 57 entries, no repeated id; 64 articles: 54 with a title, 10 with only a
  subtitle. By score: 46 have a title and a subtitle (110), 10 a subtitle
  only (10), 2 a title only (100), 3 a title, subtitle and picture (111),
  and the 3 with a fact name score 1110 (one) and 1111 (two, with a
  picture).
- 50 entries have one article and 7 have two. No entry has more.
- No sign in the file is one the code ignores; nothing is nested deeper than
  an article's detail lines; every `@`, `=` and `$` line has exactly one
  word after the sign.
- 33 entries are named in the `NEWS` row of `Days.csv` and 19 by `News`
  commands in `Travelers.txt`; none by both. Every id named there exists.
- The four `RANDOM_...` entries each have **one** article that is not
  commented out ("The Weather", "Sports", "Politics", "Entertainment",
  subtitle only). The longer lists of weather and politics headlines are
  inside comments. So the filler draw always picks the same article; it is
  still made.
- **`DIPLOMAT_FIRST` is named by nothing**: not in the `NEWS` row, not by a
  `News` command, and the text is not among the code's strings. (The same
  word is a traveler entry on day 8, and appears in `Threads.txt`, which
  the game does not load by name.) Its headline "Kolechia Sends Top-Level Diplomat" is
  therefore never shown, as far as these searches go.
- Commented out in the file: `JOURNO2` and `EZIC_ATTACK2` to `5`.
- Over all 31 days and 200 master seeds with no traveler news: a day has 0,
  1 or 2 ids and so 3, 2 or 1 fillers; draws from the news generator are 7,
  6 and 5 (four for the shuffle, one per filler); the most articles on one
  day is 4 (one id with two articles plus two fillers), which matches the
  four facts `News0` to `News3`; only days 10 and 28 (no id) have a first
  article that depends on the seed.
- The sort: 2,000 random lists all come out highest score first, 1,500 of
  them in a different order from a stable sort.
- Traveler news: three commands on day 5 (one repeated) store two ids, and
  they appear on day 6 after that day's own id, and not on day 5 or 7.

## Notes for the port

- The paper's traveler news comes from **yesterday's** fact.
- Reproduce the quicksort exactly; a standard library sort gives a different
  order for equal scores (`port-requirements.md`).
- Make the filler draws even though each list has one choice, so the news
  generator stays in step.
- Fillers are counted from the number of ids, so a day with one id that has
  two articles shows four items.

## Not studied

- (Drawing the newspaper was studied on 2026-10-14: `newspaper-picture.md`.)
- Who sets `Day.whenAddNews` and what it does.
- Whether endless mode builds a `DayNews` from `Endless.csv` (the bulletin
  skips news there).
- Nothing here has been compared with the running game.
