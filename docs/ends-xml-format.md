# Ends.xml and Intro.xml: the endings and the intro

Studied on 2026-10-13. `Ends.xml` holds the twenty endings as picture-and-text
slide shows; `Intro.xml` holds the opening slide show in the same page
format.

Functions read in full: the `data.EndLib` constructor, `getEndNode`,
`getEndNum`, `getEndIds`, `getEndPages`; the closure of `play.screen.Intro`
that shows a page (`Intro_85`), its condition helper (`Intro_94`) and its
sound helper (`Intro_106`). Read in part: the `play.screen.EndScreen`
constructor (where it reads the ending's attributes) and `menu_onClick`. One
constant was read from the DLL.

Everything here is confirmed in the code unless marked otherwise.

## The files

```xml
<end id="escape" achieve="ACH_END_ESCAPE" music="Victory" num="18" gocredits="true">
	<page image="NightTrain.png" text="You board the late train..."/>
	<page image="Shutter.png" sound="stamp-down" text="*KACHUNK*" when="End/FamilyTakeCount >= 2"/>
	<page image="Obrinspector.png" color="0xb19600" text="Your documents."/>
</end>
```

`<end>` attributes:

| Attribute | Meaning |
|---|---|
| `id` | The ending's name, used by `End <id>` commands and by the code |
| `num` | Its number, shown in the closing statistics as "ending n of 20" and recorded in the player's all-time record |
| `music` | The song for the ending screen (`Death` or `Victory`) |
| `gocredits` | Exactly `true`: the button after the slides reads "credits" and leads to the credits. Otherwise it reads "main menu" and leads to the title |
| `achieve` | An achievement to award (out of scope for the port) |
| `pages` | Use another ending's pages instead of this one's (`flee` uses `escape`'s) |

`<page>` attributes:

| Attribute | Meaning |
|---|---|
| `image` | A picture from `assets/intro/`. If it starts with `$`, the rest is a saved fact whose text is the file name; if that fact is not set, the picture is left as it was |
| `text` | The caption. If it starts with `$`, the rest is a saved fact and its text is shown (empty if unset). Otherwise `&quote;` is replaced by `"` |
| `color` | Caption colour as a number (`0xRRGGBB`); white (`0xffffff`) when absent |
| `sound` | A sound played 2 seconds after the page appears |
| `when` | A condition; the page is **skipped** when it is false |

`when` is split at single spaces and tested with the same tester as traveler
scripts and night events (`==`, `>=`, ... joined by `&&` / `||`); the left
side is read as a saved fact, empty if unset.

`Intro.xml` has a root `<intro>` with five `<page>` entries using only
`image` and `text`. `EndLib` loads both files; the intro's pages are kept as
a list.

Asking for an ending id that does not exist raises an error ("End not
found:").

## What the ending screen does with it

The `EndScreen` is given the ending id and the saved story's facts. It sets
the song, builds the closing statistics text (`stats_text` filled with play
time and the counts under `Game/Stat/...`, plus the ending's `num` and the
total number of endings), and plays the pages through the same page player as
the intro, with skipping not allowed. It also awards the achievement,
records the ending number in the all-time record (`EndBits`) and has the
button described above. (This paragraph first said `EndBits` was not
read in detail and the moment of each step was not worked out. Answered
on 2026-10-14 in `screens.md`, part 5, "The ending screen": everything
is done in the constructor, in this order: song, button (switched off),
statistics text (hidden), page player, achievement, `EndBits` gets bit
`num` - 1, ending stash. The statistics and the button appear after the
last page, a 2-second fade to black and 2 seconds of black.)

## Check against the data files

`scripts/checks/ends_check.py` (run 2026-10-13):

- 20 endings, ids unique, numbers 1 to 20 each used once. 17 use the song
  `Death`, 3 use `Victory`; the same three (`escape`, `help-ezic-hold-fire`,
  `ignore-ezic`) go to the credits. 5 have an achievement.
- 149 pages. Every attribute in the files is one the code reads.
- **The file is not strict XML**: its 20 separator comments are rows of
  dashes, which a standard XML reader rejects. The game's own reader accepts
  them. The port must strip comments leniently (the check does).
- All 20 fixed pictures exist in `assets/intro/`, as do `Passport1.png` to
  `Passport6.png`, which `End/FamilyPassportsImage` can name
  (`nights-txt-format.md`, the `Escape` command).
- The three facts pages refer to (`End/FamilyEscapeIntro`,
  `End/FamilyEscapeFinal`, `End/FamilyPassportsImage`) and the one fact the
  conditions test (`End/FamilyTakeCount`) are all set by the `Escape`
  command.
- One sound is used, `stamp-down`, defined in `Sounds.xml`. The song names
  `Death` and `Victory` are not ids in `Sounds.xml`: a song is the stored
  clip `<name>.ogg`, and `Death.ogg` and `Victory.ogg` are two of the
  three stored songs (`audio.md`, 2026-10-17; this said until then that
  where songs are defined was not studied).
- Two colours are used: `0xb19600` (the Obristan inspector speaking) and
  `0xd3ecd3` (the player speaking).
- `escape` / `flee`: taking 0 to 5 family members shows 16, 19, 20, 21, 22
  or 23 pages, with one stamp sound per person crossing (1 to 6).
- **Who asks for each ending**: 6 from `Nights.txt` (`End` commands), 4 from
  `Travelers.txt`, and 10 whose id is among the code's strings (`in-debt`,
  `family-dead`, `flee`, `escape`, and the six `killed-` / `tranqed-`
  endings; the last six are asked for by the border scene's shooting
  results, `border-scene.md` and `border-shooting.md`. This line first
  said where was not read; that was already answered by the border-scene
  step and is corrected here on 2026-10-14).

## Notes for the port

- Strip `<!-- ... -->` comments before parsing, or use a lenient reader.
- A page whose condition is false is skipped entirely, including its sound.
- `flee` and `escape` differ only in id, number, achievement, song and
  where the button leads; the pages and their conditions are shared.

## Not studied

- (Answered 2026-10-14 in `screens.md`, part 5: the page player's
  timing and input, whether the intro can be skipped (a page can be
  hurried from page 2 on; the intro as a whole cannot be skipped), the
  rest of the `EndScreen` constructor, and how `EndBits` stores the
  endings seen. Where the six shooting endings are asked for was
  answered by the border-scene step, `border-shooting.md`.)
- (Where songs are defined: answered on 2026-10-17, `audio.md`.)
- Nothing here has been compared with the running game.
