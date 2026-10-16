# Index of the game's data files

Where each file in `extracted/art/assets/data/` is loaded, and how far it has
been studied. The loader column comes from searching the code for each file
name (2026-10-12). "Studied" means the loader was read in full and the file
cross-checked, with a write-up in `docs/`.

| File | Loaded by | Status |
|---|---|---|
| `Days.csv` | `data.DayLib` (via `Db`) | Studied: `days-csv-format.md` |
| `Endless.csv` | `data.DayLib` (via `Db`) | Studied: `endless-mode.md` |
| `Papers.xml` | `data.PaperDefLib` | Studied: `papers-xml-format.md` |
| `Facts.xml` | `data.FactLib` | Studied: `facts-xml-format.md` |
| `Travelers.txt` | `data.TravelerLib` | Studied: `travelers-txt-format.md`; responses at the booth in `responses-and-events.md` and `player-actions.md` |
| `Errors.txt` | `data.ErrorLib` | Studied: `errors-txt-format.md`; applying an error in `operations-and-fact-validity.md` |
| `Speeches.txt` | `data.SpeechLib` | Studied: `speech.md` |
| `News.txt` | `data.NewsArticleLib` | Studied: `news-txt-format.md` (the file and which headlines a day gets) and `newspaper-picture.md` (drawing the newspaper, and which real headlines are cut) |
| `Nights.txt` | `data.NightLib` | Studied: `nights-txt-format.md` (the file, the calendar, running an event) and `night.md` (the family and the budget) and `screens.md`, part 1 (the night screen) |
| `Ends.xml`, `Intro.xml` | `data.EndLib` | Studied: `ends-xml-format.md` (the files and what each attribute does); the slide player's timing and input in `screens.md`, part 5 (this cell said "not studied" until 2026-10-14) |
| `Endlesses.xml` | `data.EndlessLib` | Studied: `endless-mode.md` (styles, courses, scoring); the endless screen that shows them: `screens.md`, part 7 |
| `Faces.xml` | `data.FaceLib` | Studied: `faces.md` (the loader and how a face picture is built); how the metadata of four pieces is combined in `traveler-build.md` |
| `Bodies.xml` | `data.BodyLib` | Studied: `emblems-and-bodies.md`; the search photo's pictures in `fact-pictures.md` |
| `Emblems.xml` | `data.EmblemLib` | Studied: `emblems-and-bodies.md`; the seal on a page in `page-layout.md`, the rulebook's seal sheets and the bulletin seal in `fact-pictures.md` |
| `Fonts.xml` | `data.FontLib` | Studied: `fonts.md` (the file, the `.fnt` files, measurements, line breaking); drawing text in `text-drawing.md` |
| `Paths.xml` | `data.PathLib` | Studied: `paths-xml-format.md` (the file, building a path, points along it) and `border-figures.md` (how a figure follows a path, the waiting line), `border-scene.md` (what each event does, which paths the code starts) |
| `Sounds.xml` | `data.SoundDefLib` | Studied: `sounds-xml-format.md` (the file, which recording plays, how songs are named; the audio files are not extracted yet) |
| `BorderAnim.xml` | `data.AtlasLib` (asked for by `play.day.border.Border`) | Studied: `borderanim-xml-format.md` (the atlas and how an animation finds its frames). Of the border scene itself, the figures and the waiting line (`border-figures.md`) `Border` (`border-scene.md`), shooting (`border-shooting.md`) and the cameras and panning (`border-view.md`) are studied |
| `Text.xml` | `data.Lang` | Studied: `text-xml-format.md` (the loader, placeholders, the long date); aliases and typos in `value-helpers.md` |
| `UpperCase.txt` | `data.Uppercaser` | Studied: `value-helpers.md` |
| `NamesF.txt`, `NamesM.txt` | `data.NameLib`, `data.NameCycler` | Studied: `traveler-build.md` |
| `Credits.txt` | `play.screen.CreditList` | Studied: `credits-txt-format.md` (the file and the layout of the list); the screen that shows and scrolls it: `screens.md` part 6 |
| `Languages.txt`, `Languages.png` | `play.screen.LangChooser` | Studied: `languages-list.md` (the two files; the chooser screen is left out of the port by the user's decision, 2026-10-16, and not studied; loading a language pack: `language-pack.md`) |
| `TestScenarios.xml` | `data.TestScenarioLib` | Test tooling. Studied: `test-tooling-files.md` (the file; what starts a scenario not studied) |
| `Auto.txt` | `test.auto.AutoRouteSet` | Test tooling. Studied: `test-tooling-files.md` (the file's structure; how each action is carried out not studied) |
| `Threads.txt` | nothing | Not read by the game: `unused-data-files.md` (a developer's outline of the story) |
| `TravelerGraph.txt` | nothing | Not read by the game: `unused-data-files.md` |
| `Version.txt` | nothing | Not read by the game: `unused-data-files.md` (holds `1.4.11.124`) |

Two names the code asks for are not in the archive: `Loc.csv` and
`LocVersion.txt`, requested by `data.loc.Pack.loadInternal`. They come
from the language pack: each zip in `StreamingAssets/loc/` holds
`/data/Loc.csv` and `/data/LocVersion.txt`, which the loader names
`assets/data/...` (read 2026-10-16, `language-pack.md`; this paragraph
first said that these are the same files was inferred).

`data.loc.Extractors.init` also names many of these files. **Corrected on
2026-10-16:** this paragraph said it was "part of the localization tooling"
and not studied. It is not tooling: the game itself runs it every time it
reads one of these files, to put the language pack's text into them, in
English too. Which files, and the 23 texts the English pack changes, are in
`language-pack.md`.

Shared formats and helpers:

- `tab-tree-format.md`: the indented-tree reader (`Travelers.txt`,
  `Errors.txt`, `Speeches.txt`).
- `rand.md`: the random number generator.
- `art-dat-format.md`: the archive all of these come from.
