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
| `News.txt` | `data.NewsArticleLib` | Studied: `news-txt-format.md` (the file and which headlines a day gets; drawing the newspaper not studied) |
| `Nights.txt` | `data.NightLib` | Studied: `nights-txt-format.md` (the file, the calendar, running an event; the family and the budget itself not studied) |
| `Ends.xml`, `Intro.xml` | `data.EndLib` | Studied: `ends-xml-format.md` (the files and what each attribute does; the slide player's timing not studied) |
| `Endlesses.xml` | `data.EndlessLib` | Studied: `endless-mode.md` (styles, courses, scoring; the endless screens not studied) |
| `Faces.xml` | `data.FaceLib` | Studied: `faces.md` (the loader and how a face picture is built); how the metadata of four pieces is combined in `traveler-build.md` |
| `Bodies.xml` | `data.BodyLib` | Studied: `emblems-and-bodies.md` (drawing the search photo not studied) |
| `Emblems.xml` | `data.EmblemLib` | Studied: `emblems-and-bodies.md` (stamping emblems on documents not studied) |
| `Fonts.xml` | `data.FontLib` | Studied: `fonts.md` (the file, the `.fnt` files, measurements, line breaking; drawing text not studied) |
| `Paths.xml` | `data.PathLib` | Studied: `paths-xml-format.md` (the file, building a path, points along it; how the border scene uses paths and events not studied) |
| `Sounds.xml` | `data.SoundDefLib` | Studied: `sounds-xml-format.md` (the file, which recording plays, how songs are named; the audio files are not extracted yet) |
| `BorderAnim.xml` | `data.AtlasLib` (asked for by `play.day.border.Border`) | Studied: `borderanim-xml-format.md` (the atlas and how an animation finds its frames; the border scene itself not studied) |
| `Text.xml` | `data.Lang` | Studied: `text-xml-format.md` (the loader, placeholders, the long date); aliases and typos in `value-helpers.md` |
| `UpperCase.txt` | `data.Uppercaser` | Studied: `value-helpers.md` |
| `NamesF.txt`, `NamesM.txt` | `data.NameLib`, `data.NameCycler` | Studied: `traveler-build.md` |
| `Credits.txt` | `play.screen.CreditList` | Not studied |
| `Languages.txt`, `Languages.png` | `play.screen.LangChooser` | Not studied |
| `TestScenarios.xml` | `data.TestScenarioLib` | Test tooling; not studied |
| `Auto.txt` | `test.auto.AutoRouteSet` | Test tooling; not studied |
| `Threads.txt` | nothing asks for it by name | Not read by the game as far as the name search shows |
| `TravelerGraph.txt` | nothing asks for it by name | Same |
| `Version.txt` | nothing asks for it by name | Same |

Two names the code asks for are not in the archive: `Loc.csv` and
`LocVersion.txt`, requested by `data.loc.Pack.loadInternal`. Each language
zip in `StreamingAssets/loc/` contains a CSV and text files; that these are
the same files is inferred.

`data.loc.Extractors.init` also names many of these files. It is part of the
localization tooling and is not studied.

Shared formats and helpers:

- `tab-tree-format.md`: the indented-tree reader (`Travelers.txt`,
  `Errors.txt`, `Speeches.txt`).
- `rand.md`: the random number generator.
- `art-dat-format.md`: the archive all of these come from.
