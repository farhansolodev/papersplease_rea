# One-off checks

Small scripts written while studying the data files. Each compares a real
file from `extracted/art/assets/data/` with what the game's code accepts, and
prints counts. (Four compare with the running game's output instead:
`compare_with_log.py` with its log, `save_check.py` and
`save_night_check.py` with a save folder it wrote, `stash_check.py` with
a stash it wrote.) They back the "Cross-check" and "Checks" sections of the docs.
They are kept as evidence and as a starting point for port tests; they are
not polished tools.

Run from the project root with `python -I`. Paths below assume
`D = extracted\art\assets\data`.

| Script | Arguments | Backs |
|---|---|---|
| `days_shape.py` | `D\Days.csv` | `days-csv-format.md` |
| `xml_shape.py` | `D\Papers.xml` (any well-formed XML) | tag and attribute inventory |
| `papers_check.py` | `D\Papers.xml` | `papers-xml-format.md` |
| `facts_shape.py` | `D\Facts.xml` | inventory of `Facts.xml` (handles the raw `&&`) |
| `facts_check.py` | `D\Facts.xml D\Papers.xml dumps\il2cppdumper\stringliteral.json` | `facts-xml-format.md` |
| `trav_check.py` | `scripts\reference D\Travelers.txt D\Days.csv` | `tab-tree-format.md` |
| `trav_semantics.py` | `scripts\reference D\Travelers.txt` | `travelers-txt-format.md` |
| `trav_levels.py` | `scripts\reference D\Travelers.txt` | same (block level versus operation level) |
| `trav_refs.py` | `scripts\reference D\Travelers.txt D\Days.csv` | same (includes, events, buttons) |
| `errors_shape.py` | `scripts\reference D\Errors.txt` | `errors-txt-format.md` |
| `errors_check.py` | `scripts\reference D\Errors.txt D\Facts.xml` | same (after template expansion) |
| `errors_check2.py` | `scripts\reference D\Errors.txt D\Facts.xml D\Travelers.txt` | same (tilde paths, error names used by travelers) |
| `papers_on_desk_check.py` | `scripts\reference D\Facts.xml D\Papers.xml D\Days.csv D\Errors.txt` | `papers-on-desk.md` |
| `map_order_check.py` | `scripts\reference D\Facts.xml D\Text.xml D\NamesM.txt D\NamesF.txt` | `haxe-maps.md` |
| `responses_check.py` | `scripts\reference D\Travelers.txt dumps\il2cppdumper\stringliteral.json` | `responses-and-events.md` |
| `actions_check.py` | `scripts\reference D\Travelers.txt D\Errors.txt D\Papers.xml D\Facts.xml D\Text.xml D\Speeches.txt` | `player-actions.md` (also models the stamp-result rules and the penalty formula) |
| `faces_check.py` | `scripts\reference <assets>\faces D\Faces.xml <assets>\FacePalette.png` (`<assets>` = `extracted\art\assets`; needs Pillow) | `faces.md` |
| `person_check.py` | `scripts\reference <assets> D\Travelers.txt` (`<assets>` = `extracted\art\assets`; needs Pillow) | `traveler-build.md` (the reference script `person.py`) |
| `travspec_check.py` | `scripts\reference D dumps\il2cppdumper\stringliteral.json` | `travelers-txt-format.md` and `days-csv-format.md` (the reference script `travspec.py`) |
| `errormaker_check.py` | `scripts\reference D` | `errors-txt-format.md` (the reference script `errormaker.py`) |
| `booth_check.py` | `scripts\reference <assets> [master seeds]` (`<assets>` = `extracted\art\assets`; needs Pillow; about one minute per master seed, default 4; `0` runs only the short first part; progress lines go to the error stream) | `traveler-creation.md`, `fact-values.md`, `papers-on-desk.md` (the reference script `booth.py`, which chains all the layers) |
| `news_check.py` | `scripts\reference <assets>` (`<assets>` = `extracted\art\assets`) | `news-txt-format.md` (the reference script `news.py`) |
| `newsimage_check.py` | `scripts\reference <assets>` (`<assets>` = `extracted\art\assets`; needs Pillow) | `newspaper-picture.md` (the reference script `newsimage.py`) |
| `nights_check.py` | `scripts\reference D dumps\il2cppdumper\stringliteral.json` | `nights-txt-format.md` (the reference script `nights.py`) |
| `night_check.py` | `scripts\reference D` | `night.md` (the `Family` class in `nights.py`) |
| `ends_check.py` | `scripts\reference <assets> dumps\il2cppdumper\stringliteral.json` (`<assets>` = `extracted\art\assets`) | `ends-xml-format.md` |
| `text_check.py` | `D dumps\il2cppdumper\stringliteral.json` | `text-xml-format.md` |
| `sounds_check.py` | `scripts\reference D dumps\il2cppdumper\stringliteral.json` | `sounds-xml-format.md` |
| `emblems_bodies_check.py` | `scripts\reference <assets> dumps\il2cppdumper\stringliteral.json` (`<assets>` = `extracted\art\assets`; needs Pillow) | `emblems-and-bodies.md` |
| `endless_check.py` | `scripts\reference <assets>` (`<assets>` = `extracted\art\assets`) | `endless-mode.md` |
| `compare_with_log.py` | `scripts\reference <assets> <Player.log> <master seed> [--no-desk] [--no-speech]` (needs Pillow; the log comes from a test-player run of the real game) | `comparing-with-the-game.md`, `desk-drawing-draws.md` (the reference against the running game) |
| `fonts_check.py` | `scripts\reference <assets>` (`<assets>` = `extracted\art\assets`) | `fonts.md` (the reference script `fonts.py`) |
| `paths_check.py` | `scripts\reference D dumps\il2cppdumper\stringliteral.json` | `paths-xml-format.md` (the reference script `paths.py`) |
| `border_figures_check.py` | `scripts\reference D` | `border-figures.md` (uses the reference scripts `paths.py` and `travspec.py`) |
| `border_events_check.py` | `scripts\reference D` | `border-scene.md`, `border-shooting.md` and `border-view.md` (the path names, events, texts and sounds `Border` uses; the shot paths, keys, endings and bullet holes; the view's desktop numbers, the flash rule, and the pictures, font and sound the scoreboard and cameras name; the picture sizes need Pillow) |
| `borderanim_check.py` | `<assets>` (`<assets>` = `extracted\art\assets`; needs Pillow) | `borderanim-xml-format.md` |
| `credits_check.py` | `scripts\reference <assets>` (`<assets>` = `extracted\art\assets`) | `credits-txt-format.md` |
| `languages_check.py` | `<assets> game\PapersPlease_Data\StreamingAssets\loc` (`<assets>` = `extracted\art\assets`; needs Pillow) | `languages-list.md` |
| `testfiles_check.py` | `scripts\reference D` | `test-tooling-files.md` |
| `notes_files_check.py` | `D dumps\il2cppdumper\stringliteral.json` | `unused-data-files.md` |
| `speech_check.py` | `scripts\reference D\Speeches.txt D\Travelers.txt D\Errors.txt D\Facts.xml` | `speech.md` (also reads `dumps\il2cppdumper\stringliteral.json` if present) |
| `traveler_build_check.py` | `scripts\reference D\Travelers.txt D\Errors.txt D\NamesM.txt D\NamesF.txt D\Bodies.xml D\Faces.xml` | `traveler-build.md` |
| `save_check.py` | `scripts\reference <save folder> dumps\il2cppdumper\stringliteral.json` (a real save folder, for example `extracted\saverun`) | `save-format.md` (the reference script `savefile.py`: decrypting and re-encrypting every file, the tree of saves, header against facts, settings, statistics, names) |
| `stash_check.py` | `scripts\reference <folder with stash.sav> dumps\il2cppdumper\stringliteral.json D` (a stash the game wrote, for example `extracted\stash_sample`) | `save-format.md`, part 2 (reads the stash with `hxserial.py`: its kind and versions, the fields of each stash class, no generator state, the day's counters, the desk papers, which documents' facts are kept) |
| `save_night_check.py` | `scripts\reference D <save folder> dumps\il2cppdumper\stringliteral.json` | `night.md` and `save-format.md` (replays the night before each save of a real folder with `nights.py`, starting from the parent save's facts and trying every possibility, and counts the ones that give the saved facts) |
| `button_pictures_check.py` | `<assets>` (`<assets>` = `extracted\art\assets`; needs Pillow) | `buttons.md` (each button picture is where the code asks for it and divides exactly into the bands or columns the code cuts; the three phone-only pictures are absent from the main folder) |

The ones taking `scripts\reference` as their first argument import
`tabtree.py` from there.

The XML inventory scripts use a parser that **drops comments**. Read the
comments separately (see the study method in `docs/ghidra-workflow.md`).
