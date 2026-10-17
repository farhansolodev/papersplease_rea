# The screens

How each screen of the game is put together and what it does every frame.
How a screen is asked for and built is in `save-format.md`, part 2. The
rules behind a screen are in that topic's own doc (for the night:
`night.md`).

- **Part 1** (2026-10-14): what every screen is built on (`GameScreen`, and
  the switches every on-screen object carries), and the night screen.
- **Part 2** (2026-10-14): the title screen and the menu helper (`Menu`).
- **Part 3** (2026-10-14): the load screen and the confirm box
  (`Confirm`).
- **Part 4** (2026-10-14): the pause screen, the settings screen and the
  settings list they share; which key pauses; who writes the settings
  file. It also corrects one layout value of part 2.
- **Part 5** (2026-10-14): the page player that shows the intro and every
  ending (`Intro`), the intro screen, the ending screen, and how the
  endings seen are recorded (`EndBits`).
- **Part 6** (2026-10-15): the credits screen (`CreditScreen`) and how it
  scrolls the credits list; the game's frame rate, which sets the scroll
  speed, is written up in `border-view.md`.
- **Part 7** (2026-10-16): the endless code box (`UnlockConfirm`), the
  endless screen (`EndlessScreen`), the box shown after an endless run,
  and the local best score per course and style.
- Part 8 (the language pack) is `language-pack.md`, part 9 (buttons)
  `buttons.md`, and **part 10** (2026-10-16), the night screen's family
  pictures, `night-pictures.md`.
- **Part 11** (2026-10-16): the day screen (`DayScreen`), the wait
  screen, the screen shake, the screen flash and fade cover, and the news
  screen's magnifier. Desktop has no tutorial, no wait screen and no
  magnifier.
- Left out by the user's decision (2026-10-16), so not studied: the
  language chooser (`LangChooser`) and the age-rating screen and box
  (`RatingScreen`, `RatingPopup`, shown only for Korean). The port is
  English only, with no Language row and no age rating.

---

# Part 1: the base of a screen, and the night screen

Studied on 2026-10-14 by code reading. **One screenshot of the real night
screen was compared afterwards, the same day** ("Compared with a
screenshot" below): it confirms the order of the budget lines and several
positions. Everything that moves or needs a click is still not watched;
the list is at the end.

## What was read

Read in full, from files decompiled for this part (all 228 `play.night`
functions) and older ones. Those files were removed on 2026-10-15 as
duplicates; the same functions are in `decompiled/all/`
(`play_night.clean.c`, `play_screen.clean.c`, `app_ent.clean.c`,
`app_misc.clean.c` for `app.Stater`, `play_ui.clean.c`; search the whole
folder, since a few sit in another part's file):

| Class | Functions |
|---|---|
| `play.screen.NightScreen` | constructor `0x1806d8990`, `onClickSleep` `0x1806d93c0`, `restoreFromStash` `0x1806d9470`, `update` `0x1806d94a0` (all four it has) |
| `play.screen.GameScreen` | constructor `0x18057bdf0`, `enablePause` `0x18057d7a0`, `get_canPause`, `pauseButton_onClick`, `update` `0x18057e240`, `draw`, `makePushButton` `0x18057dc80` |
| `play.night.ent.BudgetEnt` | its five state functions (`0x1806c2160`, `0x1806c2360`, `0x1806c24a0`, `0x1806c2780`, `0x1806c28b0`), `updateBudgetTotal` `0x1806c7830`, `update` `0x1806c7f60`, `sleepButton_onClick`, `skipRevealAnimation`, `autoIsAnimating`, `createMessageTexts`, `calcSplit`, `draw`. The constructor `0x1806c2a70`: see the note below |
| `play.night.ent.BudgetLineEnt` | constructor `0x1806c80f0`, `react` `0x1806c9fe0`, `set_enabled` `0x1806ca190`, `get_enabled`, `flashCheck`, `tween_flashCheck`, `draw`, `width`, `height`, the colour constants |
| `play.night.Budget`, `Line` | `addLine`, `balance`, `get_total`, `getRenameSleepButton`; the `Line` constructor and `get_renameSleepButton` (read again; they agree with `night.md`) |
| `play.night.Family` | `buildMessage` `0x180757930` and its two helper functions, `getSummary` `0x1807588a0`, `makeVisuals`, `getSpeechGender` |
| `data.DayLib` | `getNightMessages` `0x180447cf0` |
| `play.ui.RevealTextEnt` | `set_text`, `stepReveal` `0x18077ca10`, `revealAll`, `isFullyRevealed`, the punctuation lists |
| `app.ent.Ent`, `app.ent.Trunk` | the constructor's starting switches, `get_active`, `set_active`, `treeUpdate`, `treeDraw`, `treeReact` |
| `app.Stater`, `app.State` | `step`, `setDuration`, `enter` (the rest is described in `border-scene.md`) |

**The `BudgetEnt` constructor is 2,300 lines** of decompiler output, most
of it type checks. Its order of work, its states and its strings were read
(the strings also in machine-code order with `ListStringUses.java`, which
recovered one name the decompiler dropped). Three things were then checked
in its instructions (`decompiled/budgetent_ctor_asm.txt`), because the
decompiler's version was unreliable there: the choice of line height and
message font (the decompiler had the comparisons the wrong way round and
reused one variable for two things), the desktop rectangle, and the
sleep button's height on screen. The rest of its pixel arithmetic was read
from the decompiler only.

(`play.ui.DiagramLine` was not read here; read since, on 2026-10-16,
`ui-parts.md`: it is a dotted line.) (`app.vis.Text` was on this list;
read on 2026-10-16, `text-drawing.md`.) (`GameScreen.shake` was on this
list; read since, in part 11.) (`play.ui.Button` was on this list;
read since, on 2026-10-16, `buttons.md`.) (`GameScreen.addHeader` and
`addMediaButtons` were on this list; they are read since, in part 4.)
(The `FamilyVisuals` constructor and `FamilyVisualsDim` were on this
list; read since, on 2026-10-16, `night-pictures.md`.)

Numbers the decompiler showed only as addresses were read with
`read_doubles.py`.

## The switches on every on-screen object

Everything on screen (a screen, a button, a line of the budget) is an
"entity" (`app.ent.Ent`) in a tree: a screen holds its parts, which hold
their parts. Each entity has a number of on/off switches, kept in one
field called `flags`. A new entity starts with 29, which is 1 + 4 + 8 + 16.

Every frame the game walks the tree three times: to update, to draw, and to
hand out input (`Trunk.treeUpdate`, `treeDraw`, `treeReact`). What each
switch does in those walks:

| Switch | Name in the code | Without it |
|---|---|---|
| 1 | `active` | The entity is not updated, not drawn and gets no input, and neither does anything inside it |
| 4 | `flagEnableReact` | The entity gets no input, and neither does anything inside it. It is still drawn and updated |
| 8 | (no name seen) | The parts inside it get no input; the entity itself still does |
| 16 | (no name seen) | The entity is not updated, and neither is anything inside it. It is still drawn |

Switch 2 is not tested in any of the three walks. Drawing needs only
switch 1. For input, the parts inside an entity are asked before the
entity itself.

**This answers an open question of `save-format.md`, part 2**: the fade to
another screen and the resume overlay clear switches 4 and 16 of the
current screen. So the screen and everything in it stop getting input and
stop being updated, and are still drawn. (The earlier guess, "no update,
no input", was right.)

## What every screen is built on (`GameScreen`)

- A screen is an entity with a list of pictures of its own (`visuals`,
  drawn in order by `draw`), a song name (`songId`) and a screen shaker
  (`ScreenShake`, made by the constructor as a child of the screen; how
  it shakes is in part 11).
- `enablePause(black)` marks the screen as one that can be paused
  (`canPause`). If the layout has `showPauseButton` set, it also makes a
  pause button in the top right corner (4 pixels from the top), white, or
  black when `black` is true. The button is added to the screen on the
  first `update`. A click calls `GameTransition.setPause(true)`.
  **Desktop has no such button**: the `Layout` constructor sets
  `showPauseButton` in its two portrait blocks only (settled in part 2,
  "The desktop block of the layout"; part 1 first left this open). On
  desktop the pause is on a key: Escape (part 4, "Which key pauses").
- `makePushButton(parent, text, align, red)` builds the game's standard
  wide button from `PushButton.png` (129 x 38) or `PushButtonRed.png`,
  with text colour `0x556855`, or `0xcc2e2e` on the red one. The picture
  is cut into an upper and a lower half of 19 rows, both given to the
  button's `normal` mode: the upper half (a dotted outline) is the normal
  picture and the lower half (filled) the pressed one, and the pressed
  text is black. (This sentence first left the second half's use open;
  answered on 2026-10-16, `buttons.md`.)

## The night screen (`NightScreen`)

It does very little itself:

1. Built with: the all-time statistics, the story state and the day.
2. Song `Theme`. `enablePause` is called, so **the night screen can be
   paused**.
3. It creates one `BudgetEnt`, which is the whole visible screen, and gives
   it `onClickSleep` to call when the sleep button is clicked.
4. It publishes the all-time statistics (`AlltimeStats.publishStats`; that
   class talks to the platform's service and was not read: rule 4).
5. Every frame: the play time of the story goes up by the frame's time.
   So time on the night screen counts as play time.
6. After a stash restore (not possible in desktop play, `save-format.md`):
   the reveal animation is skipped.

## What `BudgetEnt` builds, in order

1. **The night itself.** A `Family` object is created from the game data,
   the day's night generator, the statistics, the story state, the day's
   summary and the "easy mode" setting. This is where everything in
   `night.md` under "Building the night" happens: the budget lines, the
   messages, the events. So the night's facts are worked out when the
   screen is built, before anything is shown.
2. The header picture `NightReport.png`, centred at the top.
3. The rectangle the budget may use, chosen by the layout's shape.
4. The family pictures (`Family.makeVisuals`; read since, on 2026-10-16:
   `night-pictures.md`).
5. The sleep button: a standard button with the text `budget_sleep`
   ("SLEEP") and the id `sleep`.
6. The texts `night_endof` ("END OF") and `night_day` ("DAY" and the day
   number).
7. One text per message of the night (`Family.messages`), centred, white,
   word-wrapped, stacked with 5 pixels between them, in a font chosen by
   "Making it fit" below.
8. **One line entity per budget line, in the budget's order**, top to
   bottom. So the order on screen is the order of `Budget.lines`, which is
   the order the game's sort leaves (`nights-txt-format.md`).
9. The small "cannot" picture `BudgetLineCant.png` (12 x 12), hidden.
10. A rule under the lines, and the total text.
11. `updateBudgetTotal` is called once (see "Balancing").
12. The reveal animation is set up and started.

### Making it fit (read from the instructions)

The budget lines come in two heights: **tall**, 17 pixels, in the font
`title_tall`, and **short**, 13 pixels, in the font `large`. Which one is
used, and the font of the messages, depends on what fits the height of the
budget rectangle. With n = the number of budget lines, T = the ascent of
the font `title_tall` plus 5 (room for the total), and M = the height of
all the messages in the font tried:

1. Messages in `large`. If the rectangle is higher than 17 x n + T + M:
   **tall lines**. Done.
2. Otherwise, if it is higher than 13 x n + T + M: **short lines**,
   messages stay in `large`. Done.
3. Otherwise short lines, and the messages are made again in `regular`.
   If 13 x n + T + M is still more than the rectangle: again in
   `regular_short2`, wrapped at the screen width minus 2. If it is still
   more: the divider above the family pictures is hidden
   (`FamilyVisuals.hideTopDivider`). **On desktop this does nothing**:
   only the two portrait layouts make that divider (`night-pictures.md`,
   found 2026-10-16).

This does not depend on the screen shape.

## A budget line on screen (`BudgetLineEnt`)

- Left: the line's name. Right: its amount, right-aligned.
- A line that must be paid has nothing else and **ignores clicks**.
- An optional line has a tick circle after the amount. The picture
  `BudgetLineCheck.png` (12 x 24) holds both states: the upper half is a
  circle with a filled dot (**ticked**), the lower half an empty circle
  (**not ticked**).
- Colours: white (`0xffffffff`) for an amount of 0 or more; red
  (`0xffcc2e2e`) for a cost; grey-green (`0xff556855`) for an optional line
  that is not ticked. The circle takes the same colour.
- Tall or short, as decided in "Making it fit" above.

### Does a line start ticked? Yes

(From the code; seen in the game on one night since, "Compared with a
screenshot" below.)

The screen does not decide this; it shows what the budget line says. A
line's ticked state is set when the line is made (`Line` constructor):
ticked if it must be paid or is "optional, default yes", not ticked if it
is "optional, default no". The line entity's constructor then calls
`set_enabled(get_enabled())`, which only shows that state.

The standard optional lines (food, heat, medicine) are "optional, default
yes" (`Budget.addLine`: a cost with no setting given). **So food, heat and
every medicine line start ticked**, unless balancing unticks them at once
(below). Only a line from `Nights.txt` marked `NO` starts unticked
(`nights-txt-format.md`).

### What a click does

`react`, for an optional line only: when the pointer goes down anywhere on
the line (its whole width and height, not only the circle):

1. The ticked state is flipped.
2. A sound plays: `button-drop` if the line is now ticked, `button-down`
   if it is now unticked.
3. `updateBudgetTotal` runs (next section).

There is no other way to change a line. Lines that are not yet revealed
(below) are inactive and cannot be clicked.

## Balancing: when it runs and what the player sees

`Budget.balance` (`night.md`) is called from exactly one place,
`BudgetEnt.updateBudgetTotal`, and that runs at two moments: once while the
screen is built, and after every click on an optional line. (Searched: the
only other mention of `updateBudgetTotal` in the `play.night` and
`play.screen` code is the table that lets a function be called by name.)

`updateBudgetTotal`, in order:

1. `balance()`: while the total of ticked lines is below 0, go from the
   **bottom** line upwards and untick every optional ticked line, stopping
   when the total is 0 or more.
2. If nothing was unticked: no flash. If something was: the "cannot"
   picture is centred on the tick circle of the **last line unticked**
   (the highest one), and a flash starts.
3. Every line entity re-reads its line, so a line that balancing unticked
   shows as unticked.
4. The total text becomes `$` and the total, right-aligned.
5. The sleep button's text: if a ticked line asks for another one
   (`RenameSleepButton`, `nights-txt-format.md`), that text; otherwise
   `budget_sleep`.

The flash (`BudgetEnt.update`): for 2.1 seconds the total text is shown
only in the second half of every 0.3 seconds, and the "cannot" picture is
shown exactly when the total is. Afterwards the total is steady and the
picture hidden.

**Two consequences, by the code, not watched in the game:**

- With too little money at the start, the screen opens with the bottom
  optional lines already unticked.
- Ticking a line you cannot afford does not always bounce back. Balancing
  starts from the bottom, so it unticks ticked lines **below** the one
  clicked first, and stops as soon as the money is enough. The clicked
  line can stay ticked while a lower one pays for it.

Worked example, run through the reference's budget (`nights.py`; savings
5, five paid travelers, rent 20, the son sick). The reference's line order
here is salary, savings, rent, medicine, food, heat:

| Step | Medicine | Food | Heat | Total | Mark on |
|---|---|---|---|---|---|
| Screen opens (balancing unticks heat, then food) | ticked | - | - | 5 | food |
| Click medicine | - | - | - | 10 | |
| Click heat | - | - | ticked | 0 | |
| Click medicine (5 short) | **ticked** | - | **-** | 5 | heat |
| Click food (15 short) | ticked | - | - | 5 | food |

In the fourth step the player ticks medicine and it is heat that goes.
This follows from the code and from the reference's line order. The line
order was since confirmed for one other night ("Compared with a
screenshot"); the unticking itself was not watched in the game.

The port must do the same: flip the line, then run the same bottom-up loop.

## The reveal animation

`BudgetEnt` runs a small state machine (the general one, `app.Stater`,
described in `border-scene.md`), stepped every frame with the frame's time.

| State | What happens |
|---|---|
| `off` | On entry: every message hidden, every budget line switched inactive, the rule and the total hidden. After **1.0 second**: `revealText` |
| `revealText` | Every frame, going through the messages in order: show the message and advance its letters; stop at the first message that is still appearing. When none is: `revealBudget` |
| `revealBudget` | Every frame: n = the whole part of (seconds in this state x 4). The first n lines are active (visible and clickable). When n changes and is not above the number of lines + 1, the sound `text-reveal` plays. The rule shows once n reaches the number of lines, the total once n reaches that + 1, and at + 2 the state becomes `on`. On leaving: every optional line's tick circle blinks for **2 seconds** (`flashCheck`, next paragraph) |
| `on` | On entry: every message shown in full, every line active, rule and total shown |

So the lines appear one per quarter of a second.

The blink of the tick circles (`flashCheck`, `tween_flashCheck`), now read
to the end: a timed change of 2.0 seconds ("Timed changes" below) calls
`tween_flashCheck(t)` every frame with t going from 0 to 1. The circle is
shown when the whole part of (t + 0.01) x 5 is odd. So: hidden for the
first 0.38 s, shown 0.4 s, hidden 0.4 s, shown 0.4 s, hidden 0.4 s, and
shown from 1.98 s on. "Shown" means the ticked or the empty circle,
whichever the line's state is; "hidden" means neither.

### Timed changes (`Tweener`, `Tween`)

Every entity can have a `Tweener`: a list of timed changes that the tree
walk steps each frame, just before the entity's own update
(`Trunk.treeUpdate`). Read on 2026-10-14: `Tweener.tween` `0x180680610`,
`add`, `stepAll`, the `Tween` constructor and `Tween.step` `0x18067f7c0`
(`Tween.step` and `Tweener.timer` had already been read for
`border-shooting.md`).

- `tween(function, duration)` first stops any running change that uses
  the same function, then starts a new one: t = 0, lasting `duration`
  **seconds** (never less than 0).
- Each frame the function is called with t (at most 1). Then, if t has
  reached 1, the change ends (and a "when done" function runs, if one was
  given); otherwise t grows by the frame's time divided by the duration.
  With a duration of 0, t jumps to 1.
- So the function is called once with 0, then every frame, and a last
  time with exactly 1.

This settles three values that earlier text had to call "taken to be
seconds": the 2.0 of the blinking circles here, the 0.5 of the load
screen's sliding buttons (part 3), and the 0.5 of the camera noise in
`border-view.md`.

How a message appears (`RevealTextEnt.stepReveal`): a countdown starts at
0.05 seconds; each time it runs out the next letter is shown and the
countdown gets more time: **0.5 s** after `.` or `。`, **0.25 s** after `,`
or `、`, **0.04 s** after any other letter. The sound `text-reveal` plays
at every third letter.

`skipRevealAnimation` jumps straight to `on`; it is used after a stash
restore and can be called by name (the test player; `autoIsAnimating`
answers "not yet in `on`").

**Nothing in this code hides or disables the sleep button during the
reveal.** By the code it can be clicked from the first frame. Not watched.

## The sleep button

1. `BudgetEnt.sleepButton_onClick` calls the function it was given, with
   the `Family`, and then forgets it. A second click does nothing.
2. `NightScreen.onClickSleep(family)`:
   - `family.applyBudget()`: everything in `night.md` under "Going to
     sleep", with the lines as they are ticked at that moment.
   - If no ending is wanted (`family.wantEndId` is empty):
     `GameTransition.advanceToNextDay()`. That is where the story is saved
     (`save-format.md`, part 2).
   - Otherwise: `GameTransition.fadeToEnd(wantEndId)`. The debt and death
     endings, and any ending a night event asked for, go this way.

## The family sentences (`Family.buildMessage`)

`buildMessage(language, prefix, members)` makes sentences such as "Your
son and wife have died.":

1. The text id is the prefix followed by the **number of members**
   (`family_died_2`). It is looked up among the texts with placeholders.
   If there is no such text the result is empty.
2. `$0`, `$1`... are filled with the members' message names (the texts
   `family_<member>_message`: "son", "wife", "mother-in-law"...).
3. For each member, counted from 0: text between `[m0]` and `[/m0]` is
   kept if that member is male and removed if not; `[f0]`...`[/f0]` the
   other way round. The tags themselves are removed.
4. The whole sentence then goes through the gender switches of
   `speech.md`, with: mixed if the members include both a male and a
   non-male, female if only non-male, male otherwise.

The two numbers the decompiler dropped (the member count in step 1, the
member index in step 3) were read from the instructions
(`decompiled/asm_family_buildmessage.txt`).

`Text.xml` (English) has no `[m` tag anywhere, so in English only steps 1
and 2 do anything. The reference script's `build_message` does steps 1 and
2 and gives the same result for English.

## Two small functions

- `DayLib.getNightMessages(day)` reads the cell `NIGHTMSG` of that day from
  `Days.csv` and splits it into lines. **`Days.csv` has no `NIGHTMSG`**,
  and no other data file contains the word (searched). What the table
  reader returns for a name that is not there was not read; inferred: no
  messages. The reference passes none.
- `Family.getSummary(story facts)` returns four values without building a
  family: `numFamily` = `Night/FamilyAlive` (4 if not set), `savings` =
  `Night/Savings` (30 if not set), `numTokens` = the number of entries in
  `Night/TokenIds`, and `apartment` = `Night/Apartment` (`C8` if not set).
  Its one caller is `LoadScreen.loadButton_onClick`, which shows them in
  the box before continuing a save (part 3; the names were read there).

## Random draws: none found

The `Family` is given the day's night generator (`Day.nightRand`) and
stores it. In all 228 `play.night` functions there is no call to a
generator (searched for `nextInt`, `nextFloat`, `random` and for uses of
the stored field: it is only stored, and readable by name). Not searched:
code outside `play.night` that could fetch it by name, and the three
`play.ui` classes the screen uses.

## The first night 3 of the hand-played game

(`night.md`, "An open conflict about night 3".) What this part adds, from
the code:

- On that night food, heat and three medicine lines started **ticked**:
  the money was enough (40 + 8 x 5 - 20 rent = 60, and 45 of costs), so
  balancing unticked nothing. Left alone, the save would show savings 15.
- The save shows 60: nothing bought. The only way to get there on this
  screen is to click each of the five lines once.
- So the code agrees with the user's explanation (they unticked the lines
  thinking they were ticking them). What was actually clicked cannot be
  known from the save. The other candidate, "something about when the
  budget is applied is missing", is ruled out as far as the screen goes:
  the budget is applied in one place, on the sleep click, with the lines
  as shown.

## Layout (desktop)

The screen is 570 x 320 and the shape is `LANDSCAPE` (`border-view.md`).
For that shape, **checked in the instructions**: the budget rectangle is
made with the numbers 185, 34, 200 and (screen height - 38) = 282, and the
sleep button is put at y = (screen height - 42) = 278. The four numbers
are taken to be x, y, width and height, from how the rectangle is used
later (lines start at its x, amounts are right-aligned at its width, the
fit test uses the fourth as a height); the rectangle class itself was not
read.

From the decompiler: a line's amount is right-aligned at the rectangle's
width and the tick circle starts 10 pixels after it. Both, and the
rectangle's x and width, agree with the screenshot to within a pixel or
two (next section). The rest of the placement (header, texts, the split
between messages and lines in `calcSplit`) is left for the drawing step.
The family pictures' positions are in `night-pictures.md` (2026-10-16).

The width the messages wrap at (`Layout.nightMessageWidth`) is the screen
width minus 50 in the desktop block: **520** (settled in part 2; part 1
first left open which block is the desktop one).

## Compared with a screenshot (2026-10-14)

The user supplied one screenshot of the night screen of the real game. It
is the night of day 3 of their replay of that morning (`save-format.md`,
"The replay"): salary for 10 travelers, savings 40, three members sick.
The user confirmed it is from that replay itself, taken before this part
was written, and that **it shows the screen as it opened: no line had
been clicked.** The picture is not kept in the project (the user's
choice).

**The order of the lines matches the reference exactly.** On screen, top
to bottom: `SALARY (10)` 50, `SAVINGS` 40, `RENT` -20, `FOOD` -20,
`MEDICINE (MIL)` -5, `MEDICINE (WIFE)` -5, `HEAT` -10, `MEDICINE (SON)`
-5, total `$25`. The reference's budget for the same night gives the same
eight lines in the same order and the same total.

How strong this is: one night, eight lines. The comparison function alone
(income first, then lines that must be paid) would allow 240 orders of
these eight lines; the reference picks one of them through its copy of the
game's sort, and that one is on the screen. An order that keeps the lines
as they were added would have savings first and heat before the
medicines. So the sort is confirmed for this case, including its odd
effects (salary above savings, heat between the medicine lines). **Before
this, the doc said the predicted order "looks odd enough to doubt": that
doubt was wrong** (corrected 2026-10-14). Other line counts (the table at
the end) and nights with penalties or bribes are not covered by one
picture.

Also seen in the picture, each matching the code reading:

- Income lines white, cost lines red, the tick circles red with a filled
  dot on all five optional lines. **The lines start ticked: seen.** The
  user reports the screen opened like this, with nothing clicked. That is
  one night, with enough money for everything, and it rests on the
  picture plus the user's word for "nothing clicked".
- **The whole row is the click area: supported by an observation.** The
  user reports that the mouse cursor becomes a pointing hand anywhere on
  an optional row, also between the name and the amount, not only on the
  text or the circle. (In the picture the hand is on the HEAT row between
  the two.) That fits `react` testing the line's whole rectangle. (What
  changes the cursor was not read here; read since, on 2026-10-16,
  `input-handling.md`: `BudgetLineEnt.react` asks `checkPointerJustDown`
  for its whole rectangle with no cursor given, and the default is the
  hand.) A click there was not reported.
- The fixed lines (salary, savings, rent) have no circle.
- A dotted rule under the lines and the total with a `$`, right-aligned
  with the amounts.
- The header "END OF" and "DAY 3"; one message, "Your family needs
  medicine." (three sick, none very sick: `night.md`).
- No pause button anywhere (part 2: desktop has none).
- SLEEP bottom right.

Measured in the picture (pixels counted with a script; the picture's scale
was taken from the header picture, 374 game pixels wide, which gives 1.63
screenshot pixels per game pixel, and the header was assumed centred):

| What | Code | Picture |
|---|---|---|
| Distance from line to line | 17 (tall lines) | 17.0 (27.8 screenshot pixels) |
| Left edge of the line names | 185 | 185.1 |
| Right edge of the amounts | 385 | 383.7 |
| Right edge of the tick circles | 407 (385 + 10 + 12) | 407.0 |

The amounts ending a good pixel short of 385 fits a letter's built-in
spacing on its right; that was not checked in the font. Vertical positions were
not compared (the window's title bar makes the top uncertain).

What the picture shows of the parts not read at the time (`FamilyVisuals`;
read since, on 2026-10-16, and compared with this description in
`night-pictures.md`: it agrees): on the right, one row per living member
with round badges (COLD, SICK, HUNGRY) and the name under them; top right,
the apartment class ("8 CLASS"); on the left, a column of seven dotted
circles, a booklet picture marked "x5", and four dotted rectangles.

## Not studied

- (`FamilyVisuals` and `FamilyVisualsDim`, every picture of the family,
  the apartment, the tokens and the passports, were listed here; studied
  since, on 2026-10-16, as part 10: `night-pictures.md`.)
- The exact placement of everything (see "Layout").
- (`play.ui.DiagramLine`, the rule, was listed here; read since,
  `ui-parts.md`.) (`app.vis.Text` was listed here;
  read on 2026-10-16, `text-drawing.md`.) (`play.ui.Button`'s
  modes were listed here; read since, on 2026-10-16, `buttons.md`.) (The tween helper behind `flashCheck` was
  listed here at first; it is read since, "Timed changes" above. Its
  core, `Tween.step`, had in fact been read in an earlier session for
  `border-shooting.md`; this part missed that when it was written.)
- What `revealAll` does with its sound (its condition uses a counter whose
  writer was not looked up).
- What the "instant" option of `Stater.go` changes. This screen sets no
  blend time, so it should not matter here (inferred).
- Where the day fills in its summary, and how a script's `Night <id>`
  command adds to the night events (still open from `night.md`).
- (Answered in part 4: Escape pauses; the pause screen is described
  there.)

## Things to watch in the game

Item 1 was checked against a screenshot for one case (three sick; see
"Compared with a screenshot"), and item 2 was seen on the same night.
Item 3 is half seen (the cursor, not a click). Items 4 to 6 have not been
watched. None of this needs watching before the port is built: the code
is the source, and watching only guards against a misreading. The
cheapest time for it is when the port's night screen exists and can be
put next to the game's.

1. **The order of the lines.** The screen shows the budget's lines in the
   budget's own order. The reference (`nights.py`) predicts an order that
   changes with the number of lines, because the game's sort moves equal
   lines around (`nights-txt-format.md`). **The last row is confirmed by
   the screenshot**; the other three are still predictions:

   | Sick members | Predicted order, top to bottom |
   |---|---|
   | 0 | savings, salary, rent, **heat, food** |
   | 1 | **salary, savings**, rent, medicine, food, heat |
   | 2 | savings, salary, rent, heat, medicine, medicine, food |
   | 3 | salary, savings, rent, food, medicine, medicine, heat, medicine |

   (Standard lines only, no penalties or bribes, savings and salary above
   0; the amounts themselves do not change the order. The medicine lines
   are added in the order wife, son, mother-in-law, uncle, and in the last
   row they end up as mother-in-law, wife, then heat, then son.) A night
   with no one sick would be a good second case: heat above food.
2. Food and heat show a **filled dot** when the screen has finished
   appearing (with enough money). **Seen** on one night: food, heat and
   three medicine lines all opened ticked.
3. A click anywhere on such a line, not only on the circle, flips it, and
   the line turns grey-green when unticked. (Seen so far: the cursor
   turns into a hand anywhere on the row. The click and the colour were
   not reported.)
4. The appearing: about one second of nothing, the messages letter by
   letter, then one line every quarter second, then the circles blink.
5. With too little money: the screen opens with lines already unticked,
   and ticking one you cannot afford makes the total blink for about two
   seconds with a small mark on a line.
6. Whether SLEEP can be clicked before the lines have appeared.

---

# Part 2: the title screen and the menu helper

Studied on 2026-10-14. Code reading only: **nothing in this part was
compared with the running game**, although the user saw the title screen
in the stash test of the same day (`save-format.md`): "story" and
"endless", which agrees with the two buttons below.

## What was read

From `decompiled/all/play_screen.clean.c` (condensed copy
`play_screen.short.c`; read at the time in an older copy of the same
functions, removed on 2026-10-15 as a duplicate):

| Class | Functions |
|---|---|
| `play.screen.TitleScreen` | constructor `0x180673be0`, `menu_onClick` `0x1806764f0`, `update` `0x180676bc0`, `react` `0x1806769f0`, `unlockConfirm_onDone` `0x180676b10`, `downloadUrl` `0x1806762d0`, `draw`. `confirm_onClick` is the shared empty function: it does nothing |
| `play.screen.Menu` | all of it: constructor, `addButton`, `addImageButton`, `addPushButton`, `applyCenterY`, `button_onClick`, `getButton`, `getCenterButtonsBounds`, `manageButton`, `setAllButtonsActive` |

Checked in the instructions: the two arguments the decompiler dropped in
`update` (`decompiled/titlescreen_update_asm.txt`), and the layout values
(`decompiled/layout_ctor_asm.txt`). Seven number constants read with
`read_doubles.py`.

**Not read:** `UnlockConfirm` (the box that asks for the endless code;
read since, part 7),
`app.aud.Music` (what a "beat" is; read since, 2026-10-17,
`audio-layer.md`), the platform
functions `canExit`, `osName` and `decoratedVersion`, the test tooling
class `SoakTapper`. (`play.ui.Button` was on this list; read since,
`buttons.md`.)

## The desktop block of the layout

The `Layout` constructor has three blocks, one per platform kind
(`border-view.md`). `border-view.md` found that `borderShowSnipingSurround`
is set in the two portrait blocks and not in the desktop one. The same two
blocks, and only they, write `showPauseButton`, so the third block is the
desktop one; it is also the only block that writes `titleShowVersion`.
(This sentence first named `menuItemPaddingY` as a second field written
only in those two blocks. That was wrong and was corrected on 2026-10-14
in part 4: all three blocks write it.) Values for desktop, read from the
instructions:

| Value | Desktop | Where it comes from |
|---|---|---|
| `showPauseButton` | false | Written only in the portrait blocks |
| `nightMessageWidth` | 520 | Screen width - 50, in the desktop block |
| `titleShowVersion` | **true** | Written only in the desktop block |
| `titleStackFooter` | false | The start value; only one portrait block sets it |
| `titleLogoScale` | 1.0 | The start value; the desktop block does not change it |
| `titleLogoTop` | 28 | The start value |
| `titleMenuCenterY` | 260 | The start value |
| `menuItemPaddingY` | **10** | Written in the desktop block (`0x18049d1ac`); the portrait blocks set 20. **Corrected 2026-10-14 (part 4):** this row said 0, "no write found outside the portrait blocks"; the write was there and was missed |

"The start value" means no instruction in the desktop block stores to
that field through the register holding the layout; a store by another
route would have been missed. The other seven rows were checked against
the listing again when the last row was corrected, and hold.

## What the title screen builds, in order

1. Song `Theme`. `enablePause` is **not** called: the title screen cannot
   be paused.
2. `rising` is set to true if this is the first title screen made since
   the game was started (a counter kept for the whole run), and the
   counter goes up.
3. A black background the size of the screen.
4. A container entity, placed one screen height down (off screen). The
   logo and the buttons are inside it, so they move with it.
5. The logo `Title.png`, centred, at `titleLogoTop` inside the container.
6. A `Menu` on the container, centred at `titleMenuCenterY`, with these
   buttons:

   | Id | Kind | Text or picture | Made when | Where |
   |---|---|---|---|---|
   | `story` | standard button | `menu_story` | always | centre column |
   | `endless` | standard button | `menu_endless` | not with the command-line word `expo` | centre column |
   | `quit` | picture | `QuitButton.png` (17 rows per state) | the platform says the game can exit, and not `expo` | top right, 10 from the edges. Inactive at first |
   | `settings` | picture | `SettingsButton.png` (29 rows per state) | always; inactive with `expo` | bottom left, 10 from the edges |
   | `credit` | text on a 140 x 12 bar | `created_by`, font `regular`, colour `0xff556855` | always | bottom centre |
   | `version` | picture with text | `VersionButton.png` (12 rows), the platform's version text, colour `0x3b483b` | `titleShowVersion` (desktop) | bottom right |

7. A helper for the test tooling (`SoakTapper`, given 13 numbers).

On the portrait shape that sets `titleStackFooter`, the credit and
settings buttons are stacked in the middle instead.

## What each button does (`menu_onClick`)

| Id | What happens |
|---|---|
| `story` | Fade to the screen `load` (the load screen, where a new story is also started) |
| `endless` | If the setting `endlessUnlocked` is on: fade to the screen `endless`. If not: a box asking for a code is shown (`UnlockConfirm`, with the text `endless_unlock` and the code `endless_code` from the language's fixed values). When the box reports success: the setting is turned on and the game fades to `endless` (the box and the endless screen: part 7) |
| `quit` | `GameTransition.quit()` |
| `credit` | Fade to the screen `credit` |
| `settings` | Fade to the screen `settings` |
| `version`, `newversion` | Opens a web address in the system's browser: the language's `url_check_updates`, followed by the game version and the system's name |

No button with the id `newversion` is made in the functions read.

**For the port (your decision, noted here because of rule 4):** the
`version` button is the only thing on this screen that reaches outside the
game. It opens the developer's "check for updates" page. It is not online
play, anti-cheat or DRM, so I did not stop, and I did not study how the
link is opened. A browser port has no use for it; I suggest leaving the
button out, or showing the version as plain text.

## The rising title (`update`)

Every frame, from the music that was handed to the screen:

- **If the music is not playing**: everything is put in its final place at
  once (container at the top, logo at `titleLogoTop`, quit button active).
- Otherwise b = the music's beat x 0.5 + 0.035.
  - **Rising**, while this is the first title screen of the run, the
    player has not skipped, and b is below 20: the container moves up in
    **20 steps**, one per whole number of b. Its distance from the final
    place is (screen height - `titleLogoTop`) x (1 - p), rounded, where
    p = (the whole part of b + a quick ease over the first fifth of each
    step) / 20, and at most 1. On desktop that is 292 pixels, 14.6 a step.
  - **After that**: the container is at the top, the quit button is
    active, and the logo bobs with the music: with x = the fraction part
    of b x 0.5, the logo sits 5 pixels lower from x = 0.1 to x = 0.5 and
    eases in and out over a tenth on each side.
- While rising, the screen's switch 8 is cleared, so **the buttons cannot
  be clicked until the title has arrived** (part 1, "The switches").

`react`: while rising, any click or any key sets `skipped`, which ends the
rise on the next frame. (Separately, taps in the top left 50 x 50 pixels
are counted by the test tooling's `SoakTapper`; the right rhythm starts
the soak test, `save-format.md`.)

What a "beat" of the music is was not read here; read on 2026-10-17
(step 6b, `audio-layer.md`, "The beat"): a fixed tempo table that fits
`Theme`, 100 beats a minute at first. So **the rise takes about 23.6 s**,
in 20 steps about 1.2 s apart, and the logo bobs once a bar (2.4 s at
first, 1.92 s at the fastest).

## The menu helper (`Menu`)

A `Menu` belongs to one entity (the host) and keeps its buttons by id.

- `addPushButton(id, text)`: a standard button (`makePushButton`), centred
  horizontally and added to the **centre column**. An id of `back` or
  `cancel` also makes it the back button (`setAsBackButton`: Escape
  presses it, read in part 4).
- `addImageButton(id, picture, rows, font)`: a button from a picture whose
  upper `rows` rows are one state and the next `rows` rows the other (the
  whole picture if `rows` is 0). Not in the centre column; the caller
  places it.
- `manageButton(button, inColumn)`: takes over a button made elsewhere.
- Every button's click calls the menu's one `whenClick` with the
  button's id.
- `applyCenterY`, run after each `addPushButton`: the column is centred on
  `centerY`. Its height is the buttons' heights plus `menuItemPaddingY`
  between them, but at most the screen height minus the notch height
  minus 40; the buttons are then spread evenly over that height.
- `setAllButtonsActive(on)` switches every button of the menu on or off;
  `getCenterButtonsBounds` gives the rectangle around the column.

## Not studied

- (`UnlockConfirm`, how the code is typed and checked: read since, part 7,
  "The code box".)
- (The music's beat, so the rise's length in seconds and the bob's
  tempo, was listed here: read on 2026-10-17, `audio-layer.md`; the rise
  takes about 23.6 s.)
- (`play.ui.Button` beyond its key and mouse handling was listed here;
  read since, on 2026-10-16, `buttons.md`. What a "back button" is was
  also listed, inferred from the name to be the button a back key
  presses. Read since, part 4: Escape presses it, on release.)
- Whether a `newversion` button is made anywhere.
- (`Layout.notchHeight` on desktop was listed here, inferred 0; the
  emulator run of the constructor gives 0, 2026-10-16,
  `booth-layout.md`.)

## Things to watch in the game

1. At the first start the title rises in visible steps with the music,
   about 1.2 s apart, for about 24 s (`audio-layer.md`);
   a click or key makes it jump to its place. After going to another
   screen and back, it does not rise again.
2. The buttons do not react until the title has arrived.
3. The logo moves down and up by a few pixels in time with the music.
4. Bottom right shows the version; bottom left the settings button; the
   quit button appears top right only once the title has arrived.

---

# Part 3: the load screen

Studied on 2026-10-14. Code reading only: **nothing in this part was
compared with the running game.** The user has used this screen (the
replay of `save-format.md` was started from it), but what it looked like
was not recorded.

This is the screen "Story" on the title leads to. It shows the tree of
saves (`save-format.md`, part 1) as a grid of buttons, starts a new story,
continues from any save, and deletes saves.

## What was read

From `decompiled/all/play_screen.clean.c` (condensed copy
`play_screen.short.c`; read at the time in an older copy of the same
functions, removed on 2026-10-15 as a duplicate):

| Class | Functions |
|---|---|
| `play.screen.LoadScreen` | `loadButton_onClick` `0x1806f4810`, `confirm_onClick` `0x1806f3780`, `createLoadButtons` `0x1806f3c20` and its two helper functions, `addLoadButton` `0x1806f32b0`, `deleteButton_onClick`, `menu_onClick`, `set_mode`, `react`, `update`, `applyScroll`, `set_scrollX`, `set_scrollY`, `get_scrollMaxX`, `get_scrollMaxY`, `getLoadButtonsHolderX`, the constants. The constructor `0x1806ee2e0`: see the note below |
| `play.screen.LoadButton` | constructor `0x1806ea750`, `button_onClick`, `setMode`, `getMatches`, `lerpFrom`, `lerpPos`, `draw` |
| `play.screen.LoadScreenDim` | constructor (the sizes) |
| `play.screen.LoadTabTemplate` | constructor (the pictures) |
| `play.screen.LoadMode` | the two modes |
| `play.screen.Confirm` | `show` `0x18093d4f0`, `button_onClick`, `react`, the constants |

The text ids and one picture name the decompiler dropped were recovered
from the strings in machine-code order (`ListStringUses.java`,
`decompiled/loadscreen_strings.txt`).

**The `LoadScreen` constructor (800 condensed lines) was read for its
order of work and its parts, not for positions.** Most of its numbers are
passed through boxed values the decompiler dropped; none was looked up in
the instructions. What is said below about where things sit comes from
`LoadScreenDim` and `LoadButton`, which are plain.

**Not read:** `LoadButton.drawConnectingLine` (229 lines: the line from a
save to the save it continues), the `Confirm` constructor (its frame),
the two "passthrough"
helper classes. (`play.ui.Button` was on this list; read since,
`buttons.md`, which also gives the delete button's three bands.)

## The sizes (`LoadScreenDim`)

Computed from the layout. On desktop (570 x 320; the notch height is
taken as 0, inferred):

| Value | Desktop | Rule |
|---|---|---|
| `horizontal` | true | The layout's aspect is `LANDSCAPE` |
| Button | 59 x 29 | fixed |
| Cell | 70 x 40 | 70 x 40 in landscape, 66 x 36 in portrait |
| Grid start | x 8, y 34 | landscape: 8 and (day header height 9 + 25) |
| Top and bottom margin of the scrolling area | 42 and 42 | screen height x 42 / 320 (the top one plus the notch) |
| Height of the scrolling area | 235 | what is left, minus 1 |
| Delete button margins | 14 and 10 | 14 fixed; screen height x 10 / 320 |
| Most tracks | **5** | `kMaxTracks` |
| Day headers made | **31** | `kMaxDays` |
| Faded colour | `0xff546754` | used for the connecting lines and the day numbers |

In landscape, "which of the two numbers `landOrPort` returns" is inferred
from its name and from the result making sense (a 59-wide button in a
70-wide cell).

## What the screen is made of

Song `Theme`. No `enablePause`: the screen cannot be paused. In the order
the constructor builds them:

1. A scrolling group, and in front of it a fixed group with two bands
   that cover the scrolling area's top and bottom.
2. A menu with one button, `back` (`menu_back`), which fades to `title`.
3. The heading `load_title` ("Select day to continue or start a new
   game"), font `title_tall`, white, centred in the top band.
4. **A row of small marks for the endings**, driven by the all-time
   statistic `EndBits`: one mark per ending, in the faded colour when that
   ending's bit is not set. (This note first said the sizes, places and
   other colour were not recovered and the number of marks was inferred.
   Answered in part 5, "What the load screen does with `EndBits`": the
   row is made only when `EndBits` is not 0; one 3 x 3 mark per ending id
   (20, read from the code, no longer inferred), 4 pixels apart; white
   when reached. The row's place is still not followed.)
5. A day header for each of 31 days: the picture `LoadDay.png` and the day
   number. Only the headers up to the highest saved day are shown.
6. Two or three copies of the picture `LoadDrag.png` (three in landscape).
   Each is shown only while some save button lies beyond it: inferred to
   be the hint that the grid can be dragged further.
7. The delete button (`LoadDelete.png`, with a second look for the
   deleting mode), bottom right.
8. The save buttons (next section).
9. The view is scrolled so that **the newest save's button** is in the
   middle (`SaveNode.getLatestHeader`), as far as the scroll limits allow.
10. The confirm box, hidden. Then the mode is set to normal.

Scrolling: pressing on the grid and dragging scrolls it, with momentum
(`KineticScroll`, read on 2026-10-16 in `ui-parts.md`: a rubber band past
the ends and a spring back). In landscape only sideways: the vertical
limit is 0. The sideways limit is the width of the days in use plus the
margins, minus the screen width.

## The save buttons

`createLoadButtons` asks the save manager for the tree
(`SaveManager.getRoot`: this is the "read the tree" of `save-format.md`,
and this function is its only caller outside the save manager) and walks
it (`addLoadButton`):

- Every node gets one button. In landscape its place is
  x = 8 + 70 x (day - 1), y = 34 + 40 x track. So **days run left to
  right and tracks top to bottom**. (In portrait the two are swapped.)
- **Tracks**: the root is on track 0. A node's **first** child stays on
  the same track. Every further child goes on a new track: one below the
  lowest track used so far by the children before it. The number of
  tracks is the lowest track used, plus 1.
- Each button has a line object in the faded colour and knows its
  parent's button; from the names (`drawConnectingLine`, not read) the
  line joins the two.

What a button shows:

| Node | Picture | Text |
|---|---|---|
| The root (the header that `isNew`; button id `new-root`) | `LoadButtonNew.png` | none |
| The newest save | `LoadButtonLatest.png` | date and money |
| Any other save | `LoadButtonSet.png` | date and money |

The text is two centred lines in the font `regular`, white: the save's
date as month/day hour:minute (`%m/%d %H:%M`), and the header's money
followed by `C`. In the deleting mode a save's button also shows
`LoadButtonDel.png` over it. The root's button is given no deleting
look.

When the buttons are made again (after a delete), a button whose save was
there before slides from its old place to the new one over **0.5
seconds**, eased (a timed change, part 1, "Timed changes"; a button that
moved less than a pixel does not slide), and the whole grid slides over
the same 0.5 seconds if the number of tracks changed.

## Clicking a button, normal mode (`loadButton_onClick`)

1. **If the node already has a child and there are 5 tracks**: a box with
   `load_confirm_full` ("Save tracks full. Continue from a right-most save
   or delete a save branch to free up a track.") and one button, `ok`.
   Nothing else happens. This applies to the root as well.
2. Otherwise, **the root**: `GameTransition.loadToScreen(root header,
   "intro")`. A new story starts with the intro (`save-format.md`: a load
   of `NEW`).
3. Otherwise, **a save**: its facts are loaded and a box is shown with the
   text `load_summary`:

   | Placeholder | Value |
   |---|---|
   | `$day` | the header's day |
   | `$news` | the first headline of that day's newspaper, cut to 27 characters and `...` if longer than 30 |
   | `$savings` | `Night/Savings` |
   | `$family` | `Night/FamilyAlive` |
   | `$tokens` | the number of entries in `Night/TokenIds` |
   | `$apt` | `Night/Apartment` |

   (The last four come from `Family.getSummary`, part 1, whose value names
   are now known: `savings`, `numFamily`, `numTokens`, `apartment`.)
   Buttons: `continue` (`load_continue`) and `cancel` (`confirm_cancel`).
   **Continue**: `GameTransition.loadToScreen(header, "news")`.

For the headline the screen builds that day's news with a **new generator
seeded 0** of its own. It does not touch the game's generators, and the
headline shown need not be the one the day will have (which headlines
need a draw: `news-txt-format.md`).

Rule 1 is what keeps the tree at 5 tracks: continuing from a save that
has no child yet extends its track, continuing from one that has makes a
new track.

## Deleting

The delete button switches between the normal and the deleting mode
(`deleteButton_onClick`); every save button changes its look.

In the deleting mode a click on a save (the root ignores it):

1. A box asks, with `load_confirm_delete_single` ("Delete this day $0
   save?") when the save's day is the deepest day below it, and with
   `load_confirm_delete_multi` ("Delete this save branch from day $0 to
   day $1?") otherwise. Buttons: `delete` (`load_delete`, marked
   dangerous: the red button) and `cancel`. (That $0 and $1 are the save's
   day and the deepest day is inferred from the text and from the two
   values passed; the values themselves were dropped by the decompiler.)
2. On `delete` (`confirm_onClick`): the save manager deletes that id
   (what goes with it: `save-format.md`, part 1), the buttons are made
   again, and the mode goes back to normal.

## The confirm box (`Confirm`)

Used here and by other screens. `show(callback, message, options)`:

- An option has an `id` and a `text`, and may have `dangerous` (a red
  button), `backButton` and `freezeAfterClick`.
- One standard button per option, stacked 10 apart (button height 19),
  centred in a frame that is centred on the screen; the message above
  them.
- An option with the id `back` or `cancel`, or with `backButton`, becomes
  the back button.
- A click: the box hides, or, with `freezeAfterClick`, stays on screen but
  stops taking input (its switch 4 is cleared, part 1). Then the callback
  gets the option's id.
- While shown, the box blocks input to whatever is under it for the rest
  of the frame.

The `continue` option carries a third value and the `delete` option the
`dangerous` one. That the third value of `continue` is `freezeAfterClick`
was first inferred here from the order of the names; it is confirmed
since (part 4, "How the option fields were identified": the field list
of one option of `loadButton_onClick` is exactly `id`, `text`,
`freezeAfterClick`, and of another exactly `id`, `dangerous`, `text`).
That its value is "true" is still inferred.

## For the port

- The tree, the 5-track limit and the track rule must match, or saves
  made in a different order would land elsewhere.
- The summary box needs the news of the day built once, with a generator
  of its own seeded 0.
- The date on a button is the save's real date and time
  (`save-format.md`), so a browser port needs a clock for it.

## Not studied

- Positions in the constructor (heading, the row of ending marks, day
  headers, drag hints, the bands). (The ending marks' colours, size and
  spacing are read since part 5.)
- `drawConnectingLine`: the shape of the line between a save and its
  parent.
- The passthrough helpers, the `Confirm` constructor. (`KineticScroll`
  was listed here; read since, `ui-parts.md`.)
- The portrait arrangement beyond what `LoadScreenDim` says.
- Whether the root's header day is 1 (its place in the grid assumes it).

## Things to watch in the game

Best with the copy of a real save folder that has a branch
(`extracted/saverun`: four saves, two of them on day 4).

1. Days run left to right; the second day-4 save sits one row below the
   first, with a line back to day 3.
2. The newest save has a different look, and the screen opens scrolled to
   it.
3. A click on a save shows day, a headline, credits, family, tokens and
   apartment, with CONTINUE and a cancel button.
4. The delete button changes every save's look; a click then asks before
   deleting, with a red DELETE button.
5. A row of small marks for the endings near the heading.

---

# Part 4: the pause screen and the settings screen

Studied on 2026-10-14. Code reading only: **nothing in this part was
compared with the running game.**

Two screens that show the same list of settings: the pause screen, which
appears over a day, a night, the newspaper or the intro, and the settings
screen, which the title's settings button opens. This part also answers
three questions older parts left open: which key pauses, who writes the
settings file, and who reads the forced-layout file `platover`.

## What was read

From `decompiled/all/` (`play_screen.clean.c`, `top.clean.c`,
`play_misc.clean.c`, `app_ent.clean.c`; read at the time in older
copies of the same functions and three small files decompiled for this
part, removed on 2026-10-15 as duplicates):

| Class | Functions |
|---|---|
| `play.screen.PauseScreen` | constructor `0x1808035e0`, `menu_onClick` `0x1808046b0`, `showConfirm` `0x180804ab0` (all it has) |
| `play.screen.SettingsScreen` | constructor `0x180715910`, `menu_onClick` `0x1807168f0` (all it has) |
| `play.screen.SettingsMenu` | constructor `0x180710150`, `update` `0x1807154b0`, `updateDateFormatText`, all 13 click handlers, `width`, `height` |
| `play.screen.SettingsMenuPurpose` | its two values, `Pause` and `Title` |
| `play.screen.SettingRow` | constructor `0x1808685f0`, `addCheckboxButton`, `addPlusMinusButtons`, `addVolumeBar`, `addLanguageButton`, `addPlatformButton`, `addRatingButton`, `addVisual`, `makeModeImages`, `splitOntoTwoLinesIfNecessary`, `react`, `draw`, `width`, `height`, the two setters |
| `play.screen.SettingDim` | constructor (the sizes) |
| `play.screen.PlatformChangeConfirm` | `button_onClick` only |
| `play.screen.GameScreen` | `addHeader` `0x18057cbb0`, `addMediaButtons` `0x18057d370` (part 1 had left both unread) |
| `Game` | `update` `0x18058c9b0` (the pause key, the settings check, the screenshot key), `applySettings` `0x1805895e0`, `queueScreenChangeToSettings`, the `settings` branch of `applyScreenChange`, the three functions of the `paused` state |
| `play.Settings` | the ten setters |
| `app.ent.Key` | the class setup `0x18048b510` (the key numbers) |
| `InputWrapper`, `HostUnity` | `InputWrapper` constructor `0x1804aa420` (which real key each number is), `GetKeyState`; in `HostUnity.Update` only the loop that reads the keys |
| `play.screen.RatingScreen`, `LangChooser` | `isRequired`, `hasUserAddedLanguages` |

Read afterwards, the same day, from the whole-game decompile in
`decompiled/all/` (made for the Escape question): `play.ui.Button`
(`react`, `setAsBackButton`, the constructor's defaults),
`ButtonHelper.react`, `app.ent.Input` (`getKeyDown`, `getKeyJustDown`,
`getKeyJustUp`, `maskKeyUntilRelease`, `update`), `Trunk.treeReact`,
`SafeChildIter`, `Booth.react`, `StampDesk.react`, `TitleScreen.react`
and `update` again, the back buttons of the endless, credits, unlock,
device and language screens, and the stamp-bar choice in the `Booth`
constructor's instructions.

Checked beyond the decompiler: the strings of the `SettingsMenu`,
`PauseScreen`, `addCheckboxButton` and `addPlatformButton` code in
machine-code order (`ListStringUses.java`; this recovered the text id
`language_author` and the mode names `off` and `phone`); the instructions
of `SettingsMenu.musicButton_whenClick` (the decompiler dropped the value
passed to the setter); the layout values in the existing
`decompiled/layout_ctor_asm.txt`; 12 number constants with
`read_doubles.py`. Two searches for callers with `FindReferences.java`
(below).

**Not read:** (`play.ui.Button` beyond `react`, `setAsBackButton`, the
constructor's defaults and `ButtonHelper.react`, which were read
afterwards for "Escape on the pause screen": read since, on 2026-10-16,
`buttons.md`), the `PlatformChangeConfirm` constructor
and `show`, `RatingPopup`,
`LangChooser` beyond the one function (it is its own screen),
`Menu.applyCenterY` again (taken from part 2), the platform functions
`canVibrate`, `setFullscreen`, `getFullscreen`, `setCategoryVolume`.
(`Bootstrap.setLanguage` was on this list; it is read since, on
2026-10-16, `language-pack.md`.) (`getAvailableLanguageCodes` was on this list;
it is read since part 6: the `.zip` files in `StreamingAssets/loc`.)

## Which key pauses: Escape

Every frame `Game.update` asks, in this order: does the current screen say
it can be paused, was key number 5 pressed this frame, is the game's own
state `on` (`save-format.md`, part 2). If all three hold, the key is masked
until it is released and the state goes to `paused`.

The game's keys are numbers (`app.ent.Key`; the class setup writes them
one by one, 0 to 10). The Unity side turns each into a real key
(`InputWrapper`'s table), and `HostUnity.Update` reads all 11 every frame:

| Number | Name in the code | Real key | Unity key code |
|---|---|---|---|
| 0 | `TAB` | Tab | 9 |
| 1 | `SPACE` | Space | 32 |
| 2 | `ENTER` | Enter | 13 |
| 3 | `LEFT` | Left arrow | 276 |
| 4 | `RIGHT` | Right arrow | 275 |
| **5** | **`ESCAPE`** | **Escape** | 27 |
| 6 | `T` | T | 116 |
| 7 | `DEVMENU` | Unity's `Tilde` (~) | 126 |
| 8 | `AUTOPLAY_ABORT` | L | 108 |
| 9 | `AUTOPLAY_PAUSE` | P | 112 |
| 10 | `SCREENSHOT` | O | 111 |

The key codes are the numbers in the table; their names were looked up in
Unity's own key list in `dumps/il2cppdumper/dump.cs`. What each key is
used for: "Every key the game reads" below. (This sentence first said
keys 0 to 4 and 6 to 9 were not followed; they were, later the same day.)

**Key 10, read in passing:** in the same function, pressing O draws the
whole screen into a picture and saves it as
`Screenshot-<year>-<month>-<day>-<hour>-<minute>-<second>.png` in the
platform's documents folder (`getDocumentsDirectory`, not read), and logs
"Saving screenshot to: ...". No condition around it was seen in this
function, such as a debug switch.

**Which screens can be paused.** A screen can be paused if its constructor
calls `enablePause` (part 1). A search of the 471 `play.screen` functions
for that call finds four callers: the day screen, the night screen, the
news screen and the intro screen. The title, load and settings
constructors were read and do not call it; so was the ending screen's,
in part 5 (it does not call it), and so was the credits screen's, in
part 6 (it does not call it either), and the endless screen's, in
part 7 (it does not call it; this rested on the search alone until
then).

## The pause screen (`PauseScreen`)

It is made when the game enters `paused` and removed when it leaves
(`save-format.md`, part 2: sound effects paused, a song playing on (this
said "sound paused" until 2026-10-17, `audio-layer.md`), the screen under it hidden, the
sound `button-drop`; on leaving, `hover-up`). It is built on `GameScreen`
like every screen. In order:

1. The header with the text `menu_paused` ("PAUSED"); see "The header"
   below.
2. A `Menu` (part 2). On desktop, without the command-line word `expo`:
   centred on y = screen height x 270 / 320 (270), with three standard
   buttons:

   | Id | Text | What a click does |
   |---|---|---|
   | `resume` | `menu_resume` ("RESUME") | `GameTransition.setPause(false)`: back to the game |
   | `mainmenu` | `menu_mainmenu` ("MAIN MENU") | a confirm box (below) |
   | `quit` | `menu_quit` ("QUIT") | a confirm box (below) |

   On the other layouts, or with `expo`, there is no `quit` button, and
   the two others are placed by hand: `mainmenu` at the layout's
   `standardFooterButtonY`, `resume` above it.
3. `resume` is made the back button (`setAsBackButton`): its shortcut key
   is Escape ("Escape on the pause screen" below).
4. The settings list (`SettingsMenu`, in its `Pause` form, below), centred
   left to right, and up and down centred between the bottom of the header
   and the top of the `resume` button.
5. With `expo` only: the settings list is switched off (its "active"
   switch is cleared, part 1), `resume` is centred on the screen and
   `mainmenu` sits 20 below it.

The standard button is 19 high (part 3; confirmed from the code on
2026-10-16: a button is as high as its picture, here half of the 38-row
`PushButton.png`, `buttons.md`). With the gap of 10 (the layout
table below), the three buttons take 77 pixels, so on desktop they run
from about y 231 to 308. This sum was done by hand; `applyCenterY`'s own
rounding was not re-read.

**The confirm boxes.** `mainmenu` and `quit` each open the confirm box of
part 3 with an empty message and two options: the action itself (id
`confirm-mainmenu` or `confirm-quit`, with the same text as the button
that opened it) and `confirm-cancel` (`confirm_cancel`, "CANCEL"). The
action option is marked `dangerous` (a red button) and
`freezeAfterClick` (the box stays on screen, frozen, after the click); the
cancel option is marked `backButton`, so Escape presses it. All three
values are true (visible in the code). Which fields the options have was
read from the names of their field lists ("How the option fields were
identified" below).

| Option | What it does |
|---|---|
| `confirm-mainmenu` | `GameTransition.fadeToMainMenu()` |
| `confirm-quit` | `GameTransition.quit()` |
| `confirm-cancel` | Only forgets the box, so a new one is made next time |

**What "main menu" costs the player** follows from `save-format.md`: the
story is saved only on going to the next day, so leaving a day or a night
through this button loses that day (on desktop the stash is not read
back). Inferred from those rules, not followed through `fadeToMainMenu`.

**One id with no button:** `menu_onClick` also handles the id `credit`
(it opens the language's `url_twitter` address in the system's browser).
The constructor makes no button with that id.

## Escape on the pause screen: it resumes

Read on 2026-10-14, after the first version of this part had left it
open (`decompiled/all/play_ui.c` and `app_ent.c`, decompiled for this):

- **A back button is a button whose shortcut key is Escape.**
  `Button.setAsBackButton` sets the button's `shortcutKey` to 5; a new
  button has -1 (none). (`Menu.addPushButton` does this for the ids
  `back` and `cancel`, part 2; `Confirm` for those ids and for options
  marked `backButton`, part 3.)
- **A shortcut key clicks the button on release.** Each frame
  (`ButtonHelper.react` `0x1806a3d60`), unless the button lies under a
  blocked area of the screen: while the key is held the button shows
  pressed and the sound `button-down` plays once; when the key is let go
  the sound `button-up` plays and the button counts as clicked, exactly as
  a mouse click. Under a blocked area only the mouse works.
- **Masking.** When `Game.update` pauses on Escape it masks the key until
  it is released (`Input.maskKeyUntilRelease`): from then until the key
  goes up, the game sees Escape as not pressed (`Input.update`
  `0x1804b1220`). So the press that paused does not also press RESUME.
- **Who gets the key first.** Input goes to the newest parts of a screen
  first (the tree walk for input runs through an entity's children from
  last to first, `Trunk.treeReact` with `SafeChildIter.start(true)`; the
  update and draw walks run first to last). A confirm box is made after
  the buttons, so it gets input before them, and when it is shown it
  blocks the whole screen area for the rest of the frame (part 3).

Together, on the pause screen:

1. **Escape, pressed and let go again: the game resumes.** RESUME goes
   down while the key is held, with the `button-down` sound; on release
   `button-up` plays and `GameTransition.setPause(false)` runs. The
   game's own state then goes back to `on`, with the sound `hover-up`.
2. **With the MAIN MENU or QUIT box open, Escape presses CANCEL**: the
   box goes away and the game stays paused. RESUME, under the box, does
   not see the key that frame.
3. Holding Escape down does nothing more until it is let go.

Not watched in the game: on the watch list.

**How the option fields were identified.** A Haxe object written in the
code (such as a confirm option) is made from a list of its fields' name
numbers (hashes, sorted), which the decompiler shows only as the name of
a data block (`Field_<PrivateImplementationDetails>_2F51E3F2...`). That
name is the SHA-256 of the list's bytes. The name number of a field is
computed from its name (each character: number x 223 + character code,
kept to 31 bits; checked against five numbers the code shows, such as
`id` = `0x5bdb` and `text` = `0x4cf9ccad`). Trying every combination of
the five option fields gave exactly one match for each of the four lists
in the screens code: the two options of the pause screen above, and the
two of the load screen (part 3). So this is a match out of 31 possible
combinations per list, by a hash, not a guess from the order of names.

## Every key the game reads, and everything Escape does

Searched on 2026-10-14 in the whole game, decompiled for this
(`decompiled/all/`, 6,856 functions: every function of the game's own
classes except the social service and Steam, `ghidra-workflow.md`). The
search covered every call of the six key functions of `app.ent.Input`
(by name, and through the slot-number helpers), every write of a
button's `shortcutKey`, and every place Unity's own key input is read.
What it found is complete for the code Ghidra decompiled; the two
functions it could not (the `Booth` and `Layout` constructors) were
checked in their instruction listings for button shortcut calls, and
have none.

**Keys tested by number** (the only places in the game):

| Key | Where | What it does |
|---|---|---|
| Escape (5) | `Game.update` | Pauses (above) |
| O (10) | `Game.update` | Saves a screenshot (above) |
| Space (1) | `Booth.react` (the booth during a day) | Opens or closes inspect mode, **if the player has the upgrade `INSPECT_HOTKEY`** |
| Tab (0) or Enter (2) | `Booth.react` | Opens or closes the stamp bar, **if the player has the upgrade `STAMPBAR_HOTKEY`** and inspect mode is not open |
| Left (3), Right (4) | `Booth.react` | The paper in focus on the desk turns a page back or forward (`flipPageIfPossible`), no upgrade needed |
| Tab (0) | `StampDesk.react` | Opens or closes that kind of stamp bar, with no upgrade test |
| L (8), P (9) | the test player (`AutoPlayer.stepAndGetInput`) | Stop the test player, pause it. Only when the test player runs (`comparing-with-the-game.md`) |
| T (6), the developer key (7) | nowhere | Read every frame, never tested |
| any key | `TitleScreen.react` | Skips the rising title (part 2) |

The upgrades are bought at night (`nights-txt-format.md`, the
`Upgrade-...` commands). **Two stamp bars:** the booth makes a `StampBar`
unless the screen shape is `PORTRAIT_THIN`, and replaces it with a
`StampDesk` when it has a carousel (from the `Booth` constructor's
instructions). The booth has a carousel only with the shape
`PORTRAIT_THIN`, the phone layout (settled on 2026-10-16 from the same
instructions, `desk-pictures.md`; this was inferred from the names). So
on desktop the stamp bar is a `StampBar`, and the Tab key goes only
through `Booth.react`, with the upgrade test.

**Shortcut keys on buttons:** the only shortcut any button gets is
Escape, through `setAsBackButton`. So everything Escape does besides
pausing is a back button. All of them in the game:

| Screen or box | Button | Escape does |
|---|---|---|
| Day, night, news, intro screens | none | Pauses (if the game is running) |
| Pause screen | RESUME | Resumes |
| Pause screen, MAIN MENU / QUIT box | CANCEL | Closes the box |
| **Title screen** | the QUIT picture button | **Quits the game, with no question**, once the title has arrived (the button exists when the platform says the game can exit and without `expo`, part 2) |
| Settings screen | DONE (`back`) | Back to the title |
| Load screen | back (`back`) | Back to the title |
| Load screen, continue / delete boxes | CANCEL (`cancel`) | Closes the box |
| Load screen, "tracks full" box | none (its one option is `ok`) | Nothing |
| Credits screen | back (`back`) | Back to the title |
| Endless screen | back (`back`) | Back to the title |
| Endless code box (`UnlockConfirm`) | CANCEL | Closes the box, no unlock |
| Endless screen's hidden "clear achievements" box (21 quick presses in the top right corner, each within half a second of the last; read in part 7, where this row's earlier "20 quick taps" was corrected on 2026-10-16) | CANCEL | Closes the box |
| Device box (`PlatformChangeConfirm`, not on desktop) | CANCEL | Closes the box |
| Language chooser | none: its CANCEL is made without `setAsBackButton` | Nothing |
| Ending screen | none | Nothing (it cannot be paused either) |

Each back button clicks when Escape is let go, and only if no box is
shown over it.

**A trap on the first title screen (predicted from the code, not
seen).** While the title rises, any key skips the rise
(`TitleScreen.react`). The skip masks only the mouse
(`maskAllPointersDownUntilRelease`), not the key. On the next frame
`TitleScreen.update` ends the rise and switches the QUIT button on. If
the key that skipped was Escape and it is still held on that frame
(likely: a key press usually lasts several frames), QUIT sees Escape held
and **the game quits when the key is let go**. Any other key only skips.
This happens only on the first title screen of a run, the one that
rises.

For the port: with the user's decision of no quit option, Escape on the
title does nothing, and the trap does not exist.

## The header (`GameScreen.addHeader`)

Called by the pause screen, the settings screen, the credits screen, the
endless screen and the ending screen's statistics page (the endless call,
first found only by a search, is read since part 7: it is made only when
the layout's `headerInEndless` is on, so **not on desktop**, and with an
empty title; the ending screen's call is
read since part 5, title `menu_stats`, and the credits screen's since
part 6, title `menu_credits`). It adds:

- the picture `ScreenHeader.png`, centred left to right, at the layout's
  `gameScreenHeaderY` (13 on desktop: the start value, which the desktop
  block does not change);
- if a title is given: the title in the font `title_tall`, white on a
  black background with 8 pixels of padding left and right, centred left
  to right, and placed so that its middle is on the picture's bottom edge.

It returns the y of the bottom of the title (of the picture, if there is
no title). The two screens use that number to centre the settings list.

## The settings screen (`SettingsScreen`)

Built when the screen `settings` is asked for (`save-format.md`, part 2).
`Game.applyScreenChange` gives it three things: the platform's version
text, the list of language codes the platform found
(`getAvailableLanguageCodes`), and the launch setting
`allowPhoneTabletPlatformChange` (`save-format.md`: only on Android or an
iPad). It does not call `enablePause`. In order:

1. Song `Theme`.
2. The header with `menu_settings` ("SETTINGS").
3. A `Menu` centred on the layout's `standardFooterButtonY` (290 on
   desktop), with one standard button, id `back`, text `menu_done`
   ("DONE"). A click fades to the screen `title`.
4. The settings list in its `Title` form, centred left to right, and up
   and down centred between the bottom of the header and the top of the
   DONE button.
5. Only on layouts that do not show the version on the title (so not on
   desktop): the version text, font `regular`, colour `0xff3b483b`, 10
   pixels from the right and bottom edges.
6. Two picture buttons (`addMediaButtons`): `web` (`WebpageButton.png`, 11
   rows per state) 20 pixels from the left edge, and `twitter`
   (`TwitterButton.png`, 11 rows per state) 20 pixels from the right edge,
   both 10 below the notch (the top of the screen on desktop, where the
   notch height is taken as 0, inferred as in part 2).

**For the port (your decision, as with the title's `version` button):**
`web` and `twitter` open the language's `url_homepage` and `url_twitter`
in the system's browser. They are plain links, not online play or DRM, so
I did not stop, and I did not study how a link is opened. Suggested:
leave them out.

## The settings list (`SettingsMenu`)

One object that both screens create, told which of two forms to take. It
holds a list of rows and stacks them top to bottom.

| Row (text id, English) | Kind | `Pause` form | `Title` form | Made when |
|---|---|---|---|---|
| `menu_fullscreen` "Fullscreen" | tick box | yes | yes | the layout is the desktop one |
| `menu_nudity` "Nudity" | tick box | yes | yes | always |
| `menu_easy` "Easy Mode" | tick box | no | yes | always |
| `menu_vibration` "Vibration" | tick box | yes | yes | the platform says it can vibrate (`canVibrate`: the base answers false and the desktop host does not provide vibration, so **no row on desktop**; read in step 6b, `audio-layer.md`, corrected here 2026-10-17; not seen in the game) |
| `menu_dateformat` "Date Format" | minus and plus | no | yes | always |
| `menu_music` "Music" | bar, minus and plus | yes | yes | always |
| `menu_sound` "Sound" | bar, minus and plus | yes | yes | always |
| `menu_device` "Device" | phone / tablet button | no | yes | the change is allowed **and** the layout is not the desktop one |
| `menu_language` "Language" | language button, or minus and plus | no | yes | always |
| (no text) | rating picture button | yes | yes | the language code is `ko` (`RatingScreen.isRequired`) |

The rows appear in this order. So on a desktop PC in English the pause
screen shows **Fullscreen, Nudity, Music, Sound**, and the settings screen
**Fullscreen, Nudity, Easy Mode, Date Format, Music, Sound, Language**
(no Vibration row: `canVibrate` answers false on desktop, `audio-layer.md`; updated 2026-10-17).

What each row does:

| Row | A click |
|---|---|
| Fullscreen, Nudity, Easy Mode, Vibration | Flips the setting |
| Easy Mode, when switched **on** | Also shows the tip `menu_easytip` ("+ 20 credits per day") for **3 seconds** (on desktop to the right of the row, 30 pixels right of the button column). Switching it off hides the tip at once |
| Vibration, when switched on | Also vibrates once |
| Date Format | Minus: the format index down by 1, not below 0. Plus: up by 1, not above the last (there are three, `value-helpers.md`). The row shows the chosen format's example text, right-aligned before the buttons |
| Music, Sound: minus and plus | The volume is first rounded to the nearest tenth, then moved by 0.1, and kept within 0 to 1. So eleven steps |
| Music, Sound: the bar | While the pointer is held down on the bar, the volume is the pointer's place along the bar (0 at its left end, 1 at its right), rounded to the nearest tenth and kept within 0 to 1. The pointer shows the hand over the bar |
| Device | Opens a box with `phone`, `tablet` and cancel (`PlatformChangeConfirm`). A choice goes to `GameTransition.requestPlatformChange` (`save-format.md`, part 2). Never on desktop |
| Language, the usual form | Opens the language chooser (`LangChooser`, a screen of its own, not read; left out of the port by the user's decision, 2026-10-16) |
| Language, when the player has added languages | Minus and plus step through the available language codes, wrapping round at both ends, and set the language code |
| Rating | Opens `RatingPopup` (not read; left out of the port by the user's decision, 2026-10-16) |

"The player has added languages" means: the platform's list of language
codes is not the same, entry for entry, as the lines of `Languages.txt`
(`LangChooser.hasUserAddedLanguages`).

The Language row also shows the language's own name (`language_name`,
"ENGLISH") right-aligned before the button, and under it, in the small
font `small_tight`, the text `language_author`, unless that text is empty,
`Author` or `-`. In English it is `Author`, so nothing is shown.

**The rows follow the settings, not the clicks.** A click only calls a
setter. Every frame `SettingsMenu.update` compares the settings' change
counter with the one it saw last; when it differs it sets every tick box,
both bars, the device button and the date text from the settings again.
So a change made elsewhere (the fullscreen key of the system, below)
shows up in the list too.

## Who writes the settings file

**One place: `Game.update`, through `Game.applySettings`.** This answers
the question `save-format.md` left open.

- Each of the ten setters of `play.Settings` does the same two things when
  the new value differs from the old: it stores the value and adds 1 to
  the settings' change counter (`generation`). (`set_dateFormatIndex`
  also keeps the index within the list.) None of them writes the file.
- Every frame `Game.update` compares that counter with its own copy. If
  they differ it calls `applySettings`, which:
  1. if the language code differs from the loaded language: loads the new
     language (`Bootstrap.setLanguage`), rebuilds the game's standing
     objects, and asks for the settings screen to be built again (through
     the rating screen first if that language needs one);
  2. sets the music volume and the sound volume in the audio layer, each
     as **the setting squared** (a setting of 0.5 plays at 0.25; the host
     turns it into decibels on the mixer, `audio.md`);
  3. sets fullscreen;
  4. calls `Settings.save` (which writes the `settings` entry if the
     counter differs from its value at the last load, `save-format.md`);
  5. takes the counter as its own copy.
- If the counters are equal, `Game.update` instead compares the window's
  real fullscreen state with the setting, and if they differ, **sets the
  setting from the window**. That changes the counter, so the next frame
  applies and saves. (So switching fullscreen by the system's own means
  ends up in the settings file. Which means those are was not read.)

So the file is written on the frame after any setting changes, whoever
changed it. The callers of the setters found in the `play.screen` code:
the handlers above, `TitleScreen.unlockConfirm_onDone`
(`endlessUnlocked`), `EndlessScreen.set_endlessId` (`endlessIdStr`) and
`LangChooser.update` (`languageCode`). A search of the decompiled files
for other callers of `Settings.save` found only the settings' own
call-by-name table; the files decompiled so far are not the whole
program.

This fits what was seen with the real save folder (`save-format.md`): the
`settings` file appeared when the user changed a volume, not at start-up.

## Who reads `platover`: nobody found

`platover` is read by `Settings.getPlatformKindOverride` and written by
`Settings.setPlatformKindOverride`. A search of the whole program for
code that refers to each (`FindReferences.java`):

| Function | Callers found |
|---|---|
| `setPlatformKindOverride` `0x180870b30` | 1: `Game.applyTransition` (the `REQUEST_PLATFORM_CHANGE` request) |
| `getPlatformKindOverride` `0x18086faf0` | **none** |

Both are plain (static) functions, which are called directly, so a caller
would show up as it does for the first. **Observed: no code in this build
calls the reader.** A call from code Ghidra did not turn into
instructions would be missed. And on desktop the file is never written
either: the Device row is not made there. For a desktop port the forced
layout can be left out.

## A row on screen (`SettingRow`, `SettingDim`)

The sizes come from the layout (`SettingDim`). On desktop:

| Value | Desktop | Rule |
|---|---|---|
| Button | 15 x 15 | the layout's `settingsButtonSize` |
| Padding | 4 | `settingsPadding` |
| Row height | 19 | padding + button height |
| Button column x | 180 | `settingsButtonX` (the start value; the desktop block does not change it) |
| Bar width | 50 | button width x 50 / 15 |
| Font ascent | 16 | of the font `title_tall` (`fonts.md`) |

A row is an entity with a list of pictures and texts, and buttons as its
children. Positions inside a row, on desktop:

- **The label**: font `title_tall`, white, at x 0. Its y is cap height
  minus ascent (12 - 16 = -4), the same shift every text in a row gets.
- **A button** (tick box, minus, language, device): at the button column,
  x 180; y = floor(ascent / 2 - button height / 2) - 1, which is -1.
- **Plus**: right of minus, at x 180 + minus's width + padding (199).
- **The bar**: three filled rectangles, left of the buttons. A white one
  50 x 16 at x 126 (button column - padding - bar width), y -1; a black
  one 48 x 14 one pixel in; and the level, white, at most 46 x 12, two
  pixels in. The level's width is 46 x the volume; under one pixel it is
  not drawn.
- **A text before the buttons** (date format, language name):
  right-aligned so that it ends at x 176 (button column - padding).
- **The rating button**: the given picture with a 2-pixel margin (white
  when pressed), centred on x 109 (half of button column + 2 x (padding + button width)).

**Button pictures (`makeModeImages`).** Each button has a normal and a
pressed picture, made at run time from a small icon
(`SettingButtonOn.png`, `SettingButtonOff.png`, `SettingButtonPlus.png`,
`SettingButtonMinus.png`, `SettingButtonLanguage.png`,
`SettingButtonPlatform.png`). The box is button-sized (the language and
device buttons are two columns wide: 2 x 15 + 4 = 34), taller if the icon
needs it, filled black, with a dotted white border (every second pixel).
The pressed picture has its inside, 2 pixels in from each edge, filled
white. The icon is then pasted in the middle of both, with the paste mode
`BLEND`. (The picture functions used here are called by number; this
sentence first said their names were not resolved and that "copy", "fill
a rectangle" and "paste" were read from their arguments. Resolved on
2026-10-16 from their slots in the class dump: `copy`, `clone`, `fill`
and `paste`, which confirms that reading; `buttons.md`, which also gives
the border dots exactly: a dot where x + y is even.) The tick box has two looks, `off` and `on`, each with its own
pair; the device button has `phone` and `tablet` (the upper and lower half
of its picture).

**A label that does not fit** (`splitOntoTwoLinesIfNecessary`, run on
every row once all are made): if the label's right end reaches to within
the padding of the leftmost other thing in the row, everything except the
label moves down by one row height and the row becomes one row height
taller. This is how a long translated label gets a line of its own.

**Stacking.** The list puts the rows under each other, each at the sum of
the heights before it. The list's height is that sum minus the padding;
its width is the widest row (the rightmost end of anything in it). On
desktop, if no label needs a second line, the pause form is 4 x 19 - 4 =
72 high. The settings form has 7 rows; its height also depends on the
language button, whose row grows if the button with its padding is taller
than 19 (the icon's height was not looked up).

## A correction to part 2: the gap between menu buttons

Part 2 said the desktop block of the layout does not write
`menuItemPaddingY`, so that it is 0 on desktop. **That was wrong
(corrected 2026-10-14, in this part).** The listing has three writes to
that field, one in each block: 20, 20 and, in the desktop block at
`0x18049d1ac`, **10**. Part 2's table and the sentence before it are
corrected. The identification of the desktop block does not depend on it:
`showPauseButton` is written in two blocks only, and the third block is
also the only one that writes `titleShowVersion`.

Nothing else was built on the 0: no position in parts 2 or 3 was computed
from it. The desktop values read for this part, from the same listing:

| Value | Desktop | Where it comes from |
|---|---|---|
| `menuItemPaddingY` | **10** | written in the desktop block |
| `settingsPadding` | 4 | written in the desktop block |
| `settingsTipsOnTop` | false | written in the desktop block (from a register that holds 0 there) |
| `settingsButtonX` | 180 | the start value; one portrait block changes it (to 152) |
| `settingsButtonSize` | 15 x 15 | written in the desktop block |
| `standardFooterButtonY` | 290 | screen height x 290 / 320, in the desktop block |
| `gameScreenHeaderY` | 13 | the start value; one portrait block changes it |

## For the port

- Escape pauses, on the day, night, news and intro screens only.
  Everywhere else it presses the screen's back button, on release (the
  table in "Every key the game reads"); the port needs the same idea of
  one back button per screen or box.
- The pause list is four rows on desktop: Fullscreen, Nudity, Music,
  Sound. Easy mode, date format and language can only be changed from the
  title's settings screen.
- Volume is stored in tenths from 0 to 1 and played **squared**.
- A setting is applied and saved on the frame after it changes; nothing
  needs an "apply" or "save" button.
- Fullscreen follows the window both ways: the setting sets the window,
  and a window changed from outside sets the setting. In a browser this
  is the fullscreen request and the browser's own Escape/F11 handling;
  how to map it is a design decision.
- **Decided by the user (2026-10-14): the `web` and `twitter` buttons
  are left out, and there is no quit option** (neither the pause screen's
  QUIT, made on desktop without any check, nor the title's `quit`
  button, part 2).
- Escape is also the browser's own "leave fullscreen" key; in fullscreen
  the browser may take the first press for itself. Not tested; for the
  design.
- Not needed for desktop: the Device row, `platover`, vibration.
- **Decided by the user (2026-10-16): English only.** No Language row,
  no language chooser, and no age rating (the rating row, `RatingPopup`
  and `RatingScreen`, which only Korean uses). Whatever English itself
  needs from its language pack is still needed (`language-pack.md`).

## Not studied

- (`play.ui.Button`'s modes and pictures were listed here: read since,
  on 2026-10-16, `buttons.md`. How it reacts and what a back button does
  were listed too; they are read since, "Escape on the pause screen".)
- The `PlatformChangeConfirm` box. (`LangChooser`, `RatingPopup` and
  `RatingScreen` were listed here; they are left out of the port by the
  user's decision of 2026-10-16 and will not be studied.)
- (What `canVibrate` answers on desktop was listed here: false, no Vibration row, read in step 6b, `audio-layer.md`; not seen in the game.)
- What "rebuilds the game's standing objects" covers after a language
  change (`Game.createDefaultEnts`). Not needed for an English-only port.
  (`Bootstrap.setLanguage` was listed here; it is read since, on
  2026-10-16: it loads the pack and builds new data, day run, booth run
  and entity environment, `language-pack.md`.)
- What the nudity setting changes: its readers were not looked up. (Easy
  mode's effect is known: the night adds the event `EASY_MODE` when the
  setting is on, `night.md`.)
- The height of the icons, so the exact height of the language row and of
  the settings list.
- Where the documents folder for screenshots is. (What keys 0 to 4 and 6
  to 9 do was listed here; answered the same day, "Every key the game
  reads".)
- (When the booth has a carousel was listed here: only with the shape
  `PORTRAIT_THIN`, so a desktop booth has a `StampBar`; settled on
  2026-10-16, `desk-pictures.md`.)
- The portrait arrangements.

## Things to watch in the game

Each takes under a minute.

1. During a day, **Escape** shows PAUSED with four rows (Fullscreen,
   Nudity, Music, Sound) above RESUME, MAIN MENU, QUIT. On the title
   screen Escape does not pause.
2. Escape, pressed again, resumes, when the key is let go (RESUME looks
   pressed while it is held).
3. MAIN MENU and QUIT each ask first, with the same word on a red button
   and CANCEL. With that box open, Escape closes the box and the game
   stays paused.
4. The title's settings button shows seven rows: Fullscreen, Nudity, Easy
   Mode, Date Format, Music, Sound, Language, with DONE at the bottom and
   two small picture buttons in the top corners. Whether a Vibration row (by the code there is none, `audio-layer.md`)
   is there.
5. Ticking Easy Mode shows "+ 20 credits per day" beside it for about 3
   seconds.
6. Minus and plus on Music move the bar in ten steps; holding the mouse
   on the bar and moving sets it directly.
7. With a save folder of the project (`savedir`, `save-format.md`): the
   `settings.sav` file's time changes right after a click that changes a
   setting, and not after a click that changes nothing (plus at full
   volume).
8. Pressing **O** writes a `Screenshot-...png` somewhere in the user's
   documents (this is outside the project folder; say if you would rather
   not try it).
9. On the settings, load and credits screens, Escape goes back to the
   title. In the language chooser it does nothing.
10. On the title screen, once it has finished rising, Escape closes the
    game at once.
11. The trap: at the very first title screen after starting the game,
    press Escape once while the title is still rising. Predicted: the
    title jumps into place and the game closes when the key is let go. A
    very quick tap might only skip.
12. In a day with the upgrades bought: Space switches inspect mode, Tab
    or Enter opens and closes the stamp bar; Left and Right turn the page
    of the paper under the mouse, with or without upgrades.

---

# Part 5: the intro, the endings and the page player

Studied on 2026-10-14. Code reading only: **nothing in this part was
compared with the running game.**

The intro (the five pages before day 1) and every ending (`Ends.xml`) are
shown by the same object, the page player `play.screen.Intro`: a picture,
a caption under it, and a NEXT button. The intro screen and the ending
screen each wrap one page player. What the pages hold (`image`, `text`,
`color`, `sound`, `when`) is in `ends-xml-format.md`; this part is how
they are shown.

## What was read

From the whole-game decompile in `decompiled/all/` (`play_screen.clean.c`
and others; part of it was read at the time in an older copy, removed on
2026-10-15 as a duplicate):

| Class | Functions |
|---|---|
| `play.screen.Intro` | constructor `0x1808fae90`, its three state functions (show a page `Intro_85` `0x180483eb0`, the wipe `Intro_132` `0x1804837c0`, end of the wipe `Intro_146` `0x180483c50`), the condition helper `Intro_94`, the sound helper `Intro_106`, `update`, `draw`, `react` `0x1808fcde0`, `endFlipNow`, `nexButton_onClick`, the class setup (all it has) |
| `play.screen.IntroScreen` | constructor `0x180482d70`, `draw`, `intro_onDone` (all it has) |
| `play.screen.EndScreen` | constructor `0x1807b9800`, its state function `EndScreen_81` `0x1807b96a0`, `intro_onDone`, `menu_onClick`, `update`, `restoreFromStash`, `get_statsText`, the class setup (all it has) |
| `app.Stater`, `app.State` | `go`, `step`, `get_stateTime`, `State.enter`, `State.step`, `State.apply` (the state machine of `border-scene.md`, now read for how a state's in-between time works) |
| `app.Interp`, `app.Num` | the `Interp` constructor, `get`, `lerp`; `Num.lerpScale` |
| `play.ui.RevealTextEnt` | `set_text`, `stepReveal`, `revealAll` (in `decompiled/all/play_ui.clean.c`) |
| others | `GameScreen.enablePause`, `Layout.getFitScale`, `Ent.worldRect`, the shared `width`/`height` of full-screen entities, `app.vis.Sprite.width`, `play.AlltimeStats.awardAchievement`, the start of `AlltimeStats.or`, and the `EndBits` lines of the `LoadScreen` constructor |

Checked beyond the decompiler (one read-only Ghidra run, output in
`decompiled/part5_run1.txt`): the instructions of the `EndScreen`
constructor (the decompiler dropped the times of its states and the
true/false values it stores), and the strings of the `Intro` and
`EndScreen` constructors in machine-code order (this recovered the NEXT
button's text id `menu_next`). Ten number constants were read with
`read_doubles.py`. The desktop value of `introTextWidth` was read from
`decompiled/layout_ctor_asm.txt`, and the texts from `Text.xml`.

## The page player (`Intro`)

It is made with the story's facts, a list of pages, and one switch:
whether the player may hurry a page (`allowSkip`). It covers the whole
screen. It holds two picture holders, the **current** one and the
**next** one, a caption (a typing text, `RevealTextEnt`, font
`title_tall`, white, several lines, a fixed width) and the NEXT button
(text `menu_next`, "NEXT"). It runs a small state machine with two states:

| State | What happens |
|---|---|
| `flipping` | On entering: show the page (below). For the first 1 second: the wipe. After that, every frame: type the caption on. When the last letter is out: go to `idle`. On leaving: the new picture becomes the current one, and the whole caption is shown. The NEXT button is hidden throughout |
| `idle` | Nothing moves. The NEXT button is shown |

The player starts in `flipping` on page 1.

**Showing a page (entering `flipping`):**

1. Pages whose `when` condition is false are passed over (the page number
   moves on). If no page is left, nothing else happens (see "An extra
   click" below).
2. The caption is emptied, given its colour (`color`, else white), then
   given its text (`text`; `$fact` reads a story fact; `&quote;` becomes
   `"`). It is centred left to right on the screen and up and down on a
   fixed line (below). The letters start hidden.
3. If the page has a `sound`, it is set to play **2 seconds** later.
4. The picture (`assets/intro/` + `image`, or the file a `$fact` names)
   is put into the **next** holder and centred left to right. If a
   `$fact` is not set, the next holder keeps what it had: the picture
   already on screen.

**The wipe (the first second of `flipping`):** a line moves across the
current picture from its right edge to its left edge, at a steady speed,
in 1 second. Left of the line the old picture shows; right of it, the
new one. So the new page is uncovered from the right, sweeping left.
(The line's place is rounded to whole pixels each frame. That the cut
is in screen positions, not in the picture's own, is inferred: in the
picture's own positions the numbers would not line up with the
picture.)

**The caption** starts typing only after the wipe, at the speed of every
typing text (part 1, "Timed changes"): 0.05 s before the first letter,
then 0.04 s per letter, 0.25 s after a comma, 0.5 s after a full stop,
and the sound `text-reveal` at every third letter.

**NEXT** (`nexButton_onClick`) moves to the following page and goes back
to `flipping`. After the last page it calls the player's "when done"
function instead, which the screen around it supplies.

**Hurrying a page** (`react`, `endFlipNow`): only when hurrying is
allowed (the intro, not the endings) and only **from the second page
on**. Pressing the mouse anywhere on the screen while a page is in
`flipping` goes straight to `idle`: the new picture is shown whole, the
whole caption appears, and NEXT appears. In `idle` such a press does
nothing. (The NEXT button is asked before the page player, but it is
hidden while `flipping`, so the press reaches the player.) `revealAll`
plays `text-reveal` once if the typing had not finished, by the name of
the field it tests; that field (`revealCount`) was not followed.

**The first page:** the current holder has no picture yet. If an empty
holder counts as 0 wide, the wipe line stays at the left edge and the
first picture appears at once. `Sprite.width` gives the width of the
holder's drawing rectangle, and what that is for an empty holder was not
followed, so this is **inferred**. The caption still waits the 1 second.

**An extra click (by the code; does not happen with the present data):**
if every page after the one on screen is passed over by its condition,
NEXT starts a `flipping` that shows nothing new. The same page stays up,
NEXT comes back after about 1 second, and a second click ends the pages.
No ending's last page has a condition (`escape`'s last page, also used
by `flee`, has none), so this never happens with the game's files.

**Its clock:** the state machine is stepped every frame with the frame
time of the game's clock (`update`), so a pause stops it.

### Layout (desktop, 570 x 320)

| What | Value | How |
|---|---|---|
| Picture size | 240 x 160, scale 1 | The class's `kImageW`, `kImageH`; all 29 pictures in `assets/intro/` are 240 x 160 (checked). `getFitScale` gives 1 when 240 fits the width and 160 fits the room left (below); otherwise 2/3 |
| Picture top | y = 32 | Room = footer y - 40 - (320 - footer y) = 290 - 40 - 30 = 220. The block of picture (160), gap (35, that is 35/320 of the height) and one caption line (20) is centred in it: floor(220/2 + 30 - (160 + 35 + 20)/2) = 32. The 20 is `title_tall`'s line height from `fonts.md`'s reference script, not from the game |
| Picture left | x = 165 | Centred: floor(285 - 240/2) |
| Caption centre line | y = 227 | 32 + 160 + 35 |
| Caption | 380 wide; its top at floor(227 - height/2) | `introTextWidth`, 380 on desktop (`0x18049d310`, the third of its three writes, in the same block as the desktop write of `menuItemPaddingY`). Its left edge is floor(285 - width/2), where `width` is the widest of its wrapped lines, not 380 (`app.vis.Text`, read on 2026-10-16, `text-drawing.md`; this said it was not read). No code sets its alignment (searched by name), so its lines start at that edge. Its height is lines x 20 |
| NEXT | top at y = 290, centred left to right | y = `standardFooterButtonY` itself. A `Menu` would centre its button on 290 instead; this one is placed by hand, so it sits about 10 pixels lower than the ending screen's button (the button is 19 rows high, part 1) |

## The intro screen (`IntroScreen`)

Built when a new game starts (`save-format.md`, part 2: a new game goes
to `intro` first).

1. Song `Theme`.
2. A black rectangle over the whole screen.
3. A page player with the five pages of `Intro.xml`, **hurrying allowed**.
4. `enablePause`: the intro can be paused (Escape, part 4).
5. When the pages are done: a fade to the screen `news`, the newspaper of
   day 1.

## The ending screen (`EndScreen`)

Built from the ending's id, the all-time record and the story's facts.
Its constructor, in order:

1. Looks up the ending (`getEndNode`). Song = its `music`.
2. A `Menu` centred on y = 290 with **one** button: `credits`
   (`menu_credits`, "CREDITS") when `gocredits` is exactly `true`,
   otherwise `mainmenu` (`menu_mainmenu`, "MAIN MENU"). The button is
   switched off (switch 1: not drawn, no input) for now.
3. The statistics text: font `title_tall`, white, lines aligned left, no
   wrapping. Its text is `stats_text` from `Text.xml` with its fill-ins:

   | Fill-in | Value |
   |---|---|
   | `$time` | `Game/Stat/PlayTime` (whole seconds) as `MM:SS`, or `HH:MM:SS` (`StringUtil.formatTime`, `border-view.md`) |
   | `$processed`, `$approved`, `$denied`, `$detained`, `$citations`, `$stamps` | `Game/Stat/NumProcessed`, `NumApproved`, `NumDenied`, `NumDetained`, `NumCitations`, `NumStamps` (`0` when unset) |
   | `$endnum` | the ending's `num` |
   | `$endtotal` | the number of endings, 20 |

   In English: "Played for $time / $processed travelers processed /
   $approved approved / $denied denied / $detained detained / $citations
   citations earned / $stamps stamps applied / Ending $endnum of
   $endtotal". The block is centred left to right; its top is at y = 95
   (95/320 of the height). Hidden for now.
4. A page player with the ending's pages (`getEndPages`, so `flee` gets
   `escape`'s), **hurrying not allowed**.
5. A black rectangle over the whole screen, drawn on layer 100, hidden.
6. Its own state machine, three states (times read from the
   instructions):

   | State | What happens |
   |---|---|
   | `intro` | The pages play. The black rectangle is hidden |
   | `transition` | Entered when the pages are done. The black rectangle shows at once and fades in from clear to black over **2 seconds**, then stays black for **2 more seconds**. On leaving: the page player is switched off (switch 1), the header "STATS" is added (`menu_stats`, `GameScreen.addHeader`, part 4), the statistics text is shown and the button is switched on |
   | `stats` | The black fades out over **2 seconds**; the rectangle is hidden at the end of the fade |

   So from the last NEXT click: 2 s to black, 2 s of black, and 2 s of
   fading in on the statistics page. (How the two waits add up: while a
   state is fading in, its own clock does not run, `Stater.step`; the
   2-second length of `transition` is counted after its fade.)
7. Starts in `intro`, at once (no fade).
8. If the ending has `achieve`: awards it (`AlltimeStats.awardAchievement`:
   added to the record's list `_Achievements`, a save of the record is
   queued, and the platform's service is told; out of scope, rule 4).
9. **Records the ending as seen**: `EndBits` in the all-time record gets
   the bit for this ending, 1 shifted left by (`num` - 1). So ending 1 is
   bit 0 and ending 20 is bit 19. (`AlltimeStats.or` was read as far as:
   an unset statistic is set to the value; a set one is read back as a
   number. That it is then combined with "or" and saved is from the
   function's name: inferred.)
10. Writes an ending stash (`GameTransition.makeEndStash`, the
    `MAKE_STASH_END` of `save-format.md`).

The ending screen does not call `enablePause`, so it **cannot be
paused**, and it has no back button: Escape does nothing there (part 4).

**The button:** `mainmenu` fades to the title; `credits` fades to the
credits screen (`credit`). The click handler also knows an id `quit`
(close the game), but this screen makes no button with that id.

**What the load screen does with `EndBits`** (read for this part from
the `LoadScreen` constructor; part 3 had left it open): the row of marks
is made only when `EndBits` is not 0, so a player with no ending sees no
row. There is one mark per ending id (`getEndIds`, 20). Mark i (from 0)
is white when bit i is set, so it stands for ending number i + 1, and in
the load screen's faded colour (`kColorFaded`, `0xff546754`) when not.
Each mark is a 3 x 3 square, each 4 pixels right of the one before
(mark 0, ending 1, is leftmost). The row's place is
worked out from other values of that constructor, which were not
followed.

**Restoring an ending stash** (`restoreFromStash`): the screen is built
again by the same constructor, so the ending starts again from its first
page, and steps 8 to 10 run again (the bit and the achievement are
already there; a new ending stash is written). Then the first page's
wipe and typing are finished at once (`endFlipNow`). The stash keeps only
the ending's id, not the page (`save-format.md`).

### A second click after the last page (predicted from the code, not seen)

After the last NEXT, the page player stays in `idle` with its NEXT button
on, under the black rectangle, until `transition` ends 4 seconds later. A
second click on that spot in those 4 seconds would call "pages done"
again, so the screen would enter `transition` again. Leaving
`transition` runs its end step, so the statistics, the button and the
header would be put up at once under the black. Then the fade and the
wait would start over, and at their end a second "STATS" header would be
added over the first. Whether the black rectangle (layer 100) is drawn
over the NEXT button, and so whether the button can still be seen, was
not followed. The intro screen has no such problem: its "pages done"
starts a fade, and a fade stops the screen's input (part 1).

## For the port

- One page player for the intro and the endings; a flag for hurrying.
- Per page: 1 s wipe from the right, then the caption types on, then NEXT.
  The page's sound plays 2 s after the page starts, whether or not the
  page was hurried.
- The ending's 2 + 2 + 2 seconds to the statistics page, with the button
  switched on only when the statistics appear.
- `EndBits` as a 20-bit number, bit (num - 1) per ending.
- The class setup's `kTextWidth` = 250 of the ending screen: no reader
  was found in the decompiled screens code (the only use is the setup
  that writes it). Not needed.
- Decide whether to copy the second-click behaviour above, after seeing
  it in the game. A port can simply ignore clicks once the pages are done.

## Not studied

- What `Sprite.width` answers for an empty holder, so whether the first
  page wipes or appears at once.
- (`app.vis.Text`'s width for a fixed-width text was listed here; read
  on 2026-10-16, `text-drawing.md`: the widest wrapped line. The caption's
  left edge therefore depends on its text.)
- In which positions a clip rectangle is applied (`app.vis`), taken to be
  screen positions.
- `RevealTextEnt.revealCount`.
- Draw order between the page player and the ending's black rectangle.
- `AlltimeStats.or` after the read-back, and how the all-time record is
  saved.
- (Where the songs `Theme`, `Death` and `Victory` are defined: answered
  on 2026-10-17, `audio.md`: they are the three songs stored in the Unity
  files, played by file name `<song>.ogg`.)

## Things to watch in the game

Each takes under a minute; a new game shows the intro.

1. The first intro page: does its picture appear at once, or wipe in?
   The caption should start about 1 second after the page appears.
2. Pages 2 to 5: the new picture is uncovered from the right edge,
   sweeping left over 1 second; then the caption types on; then NEXT.
3. On pages 2 to 5, a click during the wipe or the typing shows the page
   whole at once. On page 1 a click does nothing until NEXT appears.
4. Escape during the intro pauses.
5. After the fifth page's NEXT: a fade to the newspaper of day 1.
6. An ending (any): clicks during a page do not hurry it. After the last
   NEXT: black over 2 s, black for 2 s, then STATS fades in over 2 s with
   the statistics and one button. Escape does nothing.
7. The statistics' last line reads "Ending n of 20", with the ending's
   number from `Ends.xml`.
8. On the next visit to the load screen, a row of 20 small marks with
   one white mark: the ending's number, counted from the left (by the
   code each mark is 4 pixels right of the one before, so ending 1 is
   leftmost).
9. The second click (above): click NEXT's spot twice quickly on an
   ending's last page.

---

# Part 6: the credits screen

Studied on 2026-10-15. Code reading only: **nothing in this part was
compared with the running game.**

The credits screen shows the list described in `credits-txt-format.md`
(what each line of `Credits.txt` becomes and how the lines are stacked)
and scrolls it. This part is the screen around the list: who opens it,
where the list sits, how fast it moves, and what the buttons do.

## What was read

From the whole-game decompile in `decompiled/all/`:

| Class | Functions |
|---|---|
| `play.screen.CreditScreen` | constructor `0x180946900`, `menu_onClick` `0x180947b70`, `react` `0x180947d40`, `update` `0x180947db0`, `draw`, the two `.ctor` wrappers (everything it has besides Haxe's field-access helpers) |
| `play.screen.CreditList` | constructor `0x1809447e0` again, `height`, `width`, `draw` (the rest was read for `credits-txt-format.md`) |
| `Game.applyScreenChange` | the `credit` branch |
| `HostUnity.UnityPlatformDisk` | `getAvailableLanguageCodes` `0x1809a8390` |
| `app.ent.Input` | `getPointerOver` `0x1804af0f0`, `getPointerOverEvenIfCaptured` |
| `play.screen.Menu` | `addPushButton` `0x1808ad720` (its alignment argument), `applyCenterY` |
| `HostUnity`, `play.ui.FramerateCounter` | `HostUnity.Update` `0x1809e8e80` in full, `applyFrameSync` `0x1809ea8d0`, `limitFps` `0x180886980`: the frame rate, written up in `border-view.md` |

Eleven number constants were read with `read_doubles.py`. Which field
the constructor writes on the DONE button (its position's x) and which
flag `react` reads on a pointer (`down`) were read from the field
layouts in `dumps/il2cppdumper/il2cpp.h`. The test player has a step
`ClickThroughCredits`; only its name was read.

## Who opens it

Two buttons fade to the screen `credit`: the title screen's "created by
Lucas Pope" text at the bottom centre (id `credit`, part 2), and the
ending screen's CREDITS button, which only the endings marked
`gocredits` have (part 5). `Game.applyScreenChange` builds the screen
and gives it the platform's list of available language codes, the same
list the settings screen gets (part 4).

## Which languages are "available"

`getAvailableLanguageCodes` lists the `.zip` files in the game's
`StreamingAssets/loc` folder, takes each file's name without `.zip`,
sorts the names, and keeps the list for later calls. This install has 16:
`cs de en es eu fr id it ja ko pl pt-BR ru tr ukr zh`. So both
conditions in `Credits.txt` (`have-lang-id`, `have-lang-eu`) are met and
the list shows all 113 of its lines (`credits-txt-format.md`).

## What the screen builds, in order

1. The hold time `kStopWait` = 4 seconds.
2. Song `Victory`.
3. The header with `menu_credits` ("CREDITS"), part 4. It returns the
   bottom of the title; call it B.
4. A `Menu` centred on y = screen height x 290 / 320 (whole numbers),
   which is 290 on desktop, with one standard button: id `back`, text
   `menu_done` ("DONE"). It is made with the alignment LEFT when the
   screen shape is `LANDSCAPE` (desktop), CENTER otherwise. Its id makes
   it a back button, so Escape presses it (part 4).
5. The scroll area (`centerRect`): from x 0, the screen's full width
   (570), from y = B + 2 down to y 320, the bottom of the screen. Then:
   - on `LANDSCAPE`: the DONE button's x is set to 20, so it sits at the
     bottom left, and the area keeps its height;
   - on the portrait shapes: the area is cut to end 10 pixels above the
     DONE button's top.
6. The stop position `kStopY` = the area's top + 80.
7. The credits list, told: clip top = the area's top, clip bottom = the
   area's bottom, "offscreen" value = the area's bottom - `kStopY`, and
   the language list. It is centred left to right: x = floor(570 x 0.5 -
   260 x 0.5) = 155 on desktop.
8. The scroll position starts at `kStopY`, and the countdown at 4 seconds.
9. The two picture buttons `web` and `twitter` (`addMediaButtons`, the
   same as on the settings screen, part 4).

It does not call `enablePause`, so Escape never pauses here; it presses
DONE. (Part 4 said this rested on a search only; the constructor is now
read.)

**Desktop numbers.** B depends on the height of the title text. The
title is one line of `title_tall` with padding only left and right, so
its height is the font's line height, 20 in the reference script
(`app.vis.Text`, read on 2026-10-16, `text-drawing.md`; this paragraph
said it was not read and the 20 was an assumption). So: the header
picture is at y 13 and 54 high, so its bottom edge is 67; the title's
middle is on that edge, so B = 77; the area runs from y 79 to 320;
`kStopY` = 159; the offscreen value is 161.

## What the first view shows

The list's top starts at `kStopY`. `[OFFSCREEN]` moves the next line to
the offscreen value - 18 in the list's own positions, which on screen is
the area's bottom - 18, whatever B is. In `Credits.txt` the line after
`[OFFSCREEN]` is a role heading, and a role adds 20 pixels before itself
(`credits-txt-format.md`), so it starts 2 pixels below the bottom of the
area, where the list is clipped: out of sight. **So the first view shows
only the lines before `[OFFSCREEN]`** (one role and one name, 80 pixels
below the header) above an empty area, and holds for 4 seconds. This
confirms, from the numbers, what `credits-txt-format.md` had inferred
about `[OFFSCREEN]`.

## Every frame (`update`)

1. `GameScreen.update`.
2. If the countdown is above 0: it goes down by the frame time (the
   game's clock), not below 0. The list does not move.
3. Otherwise:
   1. The step is 0.5 pixel, or 2 pixels while "fast" (below).
   2. The scroll position (a y, so smaller is higher on the screen) goes
      down by the step: the list moves up.
   3. If the position is now less than minus the list's height (the
      list's bottom has gone past the top of the screen), it becomes 320:
      the list starts again from below the screen.
   4. If the position was greater than `kStopY` before this frame's step
      and is less now, it is put exactly on `kStopY` and the countdown
      starts again at 4 seconds.
4. The list's y = the scroll position rounded down.

So the screen loops for as long as it is open: the first view held for 4
seconds; the whole list scrolls up and out of the top; the list comes up
again from the bottom; it stops at the first view; 4 seconds; and so on.
The frame of the jump to 320 cannot stop at once: step 3.4 compares with
the position from before the jump.

**The scroll moves by frame, not by time**: 0.5 pixel a frame. Only the
hold is timed. At the game's usual 60 frames a second (`border-view.md`,
"The frame rate") that is 30 pixels a second, 120 while fast; where the
game runs at 65 frames a second, 32.5 and 130.

### Fast

Every frame (`react`) the screen asks the input for a pointer over the
scroll area (`Input.getPointerOver`). If one is found, "fast" is that
pointer's `down` flag; if none, it is off. So **holding the mouse button
with the pointer anywhere in the area** (the full width, from just under
the header to the bottom) scrolls 4 times as fast, and letting go slows
it again. `getPointerOver` prefers a pointer that is held, and passes over
pointers that another part of the screen has taken (captured) or that lie
in a blocked area of the screen. Whether pressing DONE captures the
pointer, so that the press does not also speed up the list, was not
followed.

### How long one loop takes (an estimate)

The list's height was estimated at 2,272 pixels with every language, by
a one-off script using the fonts reference (`fonts.py`) and the picture
sizes, taking a text block as its number of lines times its font's line
height. That is the game's rule for these texts, which set no padding or
line spacing (`app.vis.Text`, read on 2026-10-16, `text-drawing.md`; this
said it was an assumption). The total was not recomputed. One loop moves the list by
its height + 320 pixels, about 2,590 pixels: about 5,180 frames, so
about 86 seconds at 60 frames a second, plus the 4-second hold. Held
fast throughout: about 22 seconds.

## What the buttons do (`menu_onClick`)

| Id | What happens |
|---|---|
| `back` (DONE, or Escape) | Fade to the screen `title`, also when the screen was opened from an ending |
| `web` | Opens the language's `url_homepage` in the system's browser |
| `twitter` | Opens the language's `url_twitter` in the system's browser |

## For the port

- The screen as above: header CREDITS, DONE at the bottom left, the list
  centred and clipped to the area under the header, the loop with its
  4-second hold at the first view, song `Victory`, Escape as DONE.
- **Speed: a decision.** The original ties the speed to the frame rate.
  Suggested: 30 pixels a second, 120 while held, measured in time; this
  equals the original at 60 frames a second. It belongs with the open
  frame-time question (`border-view.md`).
- `web` and `twitter`: on the settings screen you decided to leave them
  out (2026-10-14). These are the same two buttons; suggested: leave
  them out here too. Still yours to confirm.
- Which languages count as available is set by which language packs the
  port ships; two blocks of the list depend on it.

## Not studied

- (`app.vis.Text`'s height was listed here, which made B, `kStopY` and
  the list's height estimates; read on 2026-10-16, `text-drawing.md`. B
  and `kStopY` now follow; the list's height of about 2,272 was not
  recomputed.)
- (What the LEFT alignment changes inside `GameScreen.makePushButton`,
  and the DONE button's size, were listed here. Answered on 2026-10-16,
  `buttons.md`: LEFT puts the text 2 pixels from the button's left edge
  instead of centring it; the button itself still sits at x 20. A push
  button is the size of its picture's half, 129 x 38 / 2 = **129 x 19**.)
- Whether pressing DONE stops the fast scroll.
- The test player's `ClickThroughCredits` step beyond its name.
- (Where the song `Victory` is defined: answered on 2026-10-17,
  `audio.md`, as in part 5.)

## Things to watch in the game

On the title screen, click "created by Lucas Pope" at the bottom.

1. The header CREDITS and, about 80 pixels under it, the first credit
   alone, with nothing else visible, for 4 seconds. The song is
   `Victory`, the one three endings use (`ends-xml-format.md`).
2. Then the list scrolls up slowly: about 30 pixels a second, so roughly
   10 seconds for a screen's height.
3. Holding the mouse button anywhere under the header scrolls 4 times as
   fast; letting go slows it again.
4. After the last line ("Glory to Arstotzka") has left the top, the list
   comes up again from the bottom and stops at the first view for 4
   seconds. One loop: about one and a half minutes (estimate).
5. DONE at the bottom left goes back to the title; Escape does the same
   and never pauses here.
6. The Indonesian and Basque translation credits are both in the list
   (both language packs are installed).

---

# Part 7: the endless code box and the endless screen

Studied on 2026-10-16 by code reading, then **watched in the running
game the same day** by the user, in a separate save folder ("Compared
with the running game" below): everything on the watch list matched, and
the files the game wrote confirm the stored choice and the local best
score. Before that test the user had never played endless mode.

The title's ENDLESS button opens a box asking for a code, unless endless
mode is already unlocked (part 2, "What each button does"). The right
code unlocks it for good and fades to the endless screen, where the
player picks a **style** (Timed, Perfection, Endurance) and a **course**
(1 to 4) and presses PLAY. When a run ends, the endless screen comes back
with a box showing the result. Styles, courses and scoring are in
`endless-mode.md`.

**Leaderboards: left out of the port** (the user's decision, 2026-10-16:
the port will not be published, so it will have no leaderboards). Where
the screen touches them is recorded below, so that the port knows what to
drop; nothing behind those calls was read.

## What was read

From the whole-game decompile in `decompiled/all/`:

| Class | Functions |
|---|---|
| `play.screen.UnlockConfirm` | constructor `0x1806859c0`, `show` `0x180688850`, `button_onClick` `0x1806881f0`, `tween_flash` `0x180688970`, `draw`, the static values (everything it has besides Haxe's field-access helpers) |
| `play.screen.TitleScreen` | `menu_onClick` and `unlockConfirm_onDone` again (part 2) |
| `play.screen.EndlessScreen` | constructor `0x1807c1390`, `select` `0x1807c74d0`, `styleButton_onClick`, `courseButton_onClick`, `menu_onClick` `0x1807c6210`, `react` `0x1807c6910`, `update` `0x1807c8640`, `refreshScoreTexts` `0x1807c6fc0`, `get_endlessId`, `set_endlessId`, `secretConfirm_onClick`, `presskit_prep` `0x1807c6380`, `setLeaderboardsButtonActive`, `alltimeStats_onGotRankedScore`, the static values (all of it besides the field-access helpers) |
| `Game.applyScreenChange` | the `endless` branch, and where its result argument comes from |
| `play.day.Endless` | `end` `0x1807c97a0` |
| `play.day.EndlessResult` | `getDescription` `0x1807beb30` |
| `play.AlltimeStats` | `addScore`, `addScoreLocal` `0x1808cd060`, `getRankedScore` `0x1808cd5b0`, `get_hasLeaderboards`; `awardAchievement` was seen in passing |
| `play.ScoreEntry` | `fromString`, `isBetterThan` `0x1808608d0`, `toString` |
| `data.EndlessId`, `data.EndlessLib` | the `EndlessId` constructor `0x1807bc560`, `toString`, `toLeaderboardId`; `getEndlessIdFromString`, `getStyle`, `get_defaultStyle`, `get_defaultCourse` |
| `play.Settings` | `set_endlessIdStr`, and the `endlessId` line of `load` |

**Not read** (rule 4, online): what `AlltimeStats` asks of the platform
(`connectToSocialIfNotConnected`, `showLeaderboards`,
`clearAchievements`, the platform's `getLeaderboardScore`,
`reportLeaderboardScore` and `hasLeaderboards`).

One Ghidra run (`DumpAssembly.java` on the two constructors,
`refreshScoreTexts`, `ScoreEntry.isBetterThan` and `ScoreEntry.toString`;
output in `decompiled/part7_run1.txt`) settled four things the decompiler
dropped: the digit on each key of the code box, the number shown as a
score, the first text of a score field (empty), and that each course
picture is attached to its button. 20 number constants were read with
`read_doubles.py`. Slot numbers were looked up in `dump.cs` (`Button`,
`Mode`, `Image`, `GameTransition`, `Confirm`, `Align`), field positions
of `Pointer` there too, picture sizes in `extracted/art/assets/`, and the
texts in `Text.xml`.

## The code box (`UnlockConfirm`)

**Made once, then reused.** The first click on ENDLESS (while
`endlessUnlocked` is off) makes the box with the text `endless_unlock`
("Complete story mode with your job intact to unlock endless mode") and
the code `endless_code` from the language's fixed values: **62131**
(`text-xml-format.md`). Later clicks show the same box again (`show`).

**What it builds** (desktop numbers: screen 570 x 320):

| Part | What and where |
|---|---|
| Shade | A black rectangle at half opacity over the whole screen |
| Box | `ConfirmBox.png` (244 x 192), centred: x 163, y 64 |
| Message | Font `title_tall`, white, centred, wrapped to 214 pixels (box width - 2 x 15). x = floor((570 - its width) / 2); y = box top + 18 - ascent + cap height |
| Typed digits | Font `fixed`, white. Centred in the box by the width of the text `1 2 3 4 5 `; y = floor((message y + message height + box top + 100) / 2 - ascent / 2) - ascent + cap height, so about halfway between the message's bottom and the keys |
| Underlines | One per digit of the code (5): white, 9 x 1, at x = digits' x + 12 x n - 2, 3 pixels below the digits' cap line. 12 pixels is two characters of `fixed` (a digit and a space, `fonts.md`) |
| Keys | 10 picture buttons from `NumpadButton.png` (35 x 42: the upper 21 rows when up, the lower 21 when pressed), in 2 rows of 5, 3 pixels apart. Labels, read in the instructions: **1 2 3 4 5** on the top row, **6 7 8 9 0** below (key n, counted from 0, shows (n + 1) mod 10). On desktop: x 191, 229, 267, 305, 343; y 164 and 188. Ids `numpad1` ... `numpad9`, `numpad0`. Label colour white, up and pressed |
| CANCEL | A standard push button (part 1), text `confirm_cancel`, centred in the box, its bottom 15 pixels above the box's bottom (x 220, y 222). It is the back button, so Escape presses it |

`show`: switches the box on, empties the typed digits, and lets every key
take input again (switch 4, part 1).

**A key click** (`button_onClick`):

1. The digit is added to what was typed, and the display shows it with
   spaces between the digits (`6 2 1`).
2. Nothing more happens until as many digits as the code has are typed.
3. Then, if they differ from the code, the display changes to
   `endless_wrongcode`, "S O R R Y". Either way every key (and CANCEL)
   stops taking input, and a 3-second timed change starts (`tween_flash`,
   part 1, "Timed changes").
4. During those 3 seconds the display blinks: it is shown while
   (t x 5) mod 1 is under 0.5, so **five blinks**.
5. At the end the title is told the result (`unlockConfirm_onDone`).
   - **Right code**: the box stays on screen while the title turns on
     the setting `endlessUnlocked` and fades to the endless screen. The
     settings file is written on the next frame (part 4, "Who writes the
     settings file"), so the code is never asked for again.
   - **Wrong code**: the box closes. Clicking ENDLESS again shows it
     empty.

**CANCEL** tells the title "not unlocked" (it does nothing with that)
and closes the box.

`UnlockConfirm` has no `react` of its own, unlike `Confirm` (part 3),
which blocks input to what lies under it. Whether the title's buttons
under the box still take clicks was not established (it depends on the
order in which the title's children get input; not read).

Two of its static values, 10 and 19, are not used by any of its
functions.

## The endless screen (`EndlessScreen`)

Built by `Game.applyScreenChange` for the screen name `endless` with the
all-time statistics and, only when the request was
`FADE_TO_ENDLESS_RESULT`, the result of the run that just ended
(`save-format.md`, part 2). Its song is `Theme`. It cannot be paused: its
constructor does not call `enablePause` (read; part 4 had this from a
search only).

### What it builds (desktop)

| Part | What and where |
|---|---|
| Header | **None on desktop**: the header is added only when the layout's `headerInEndless` is on, and the desktop block has it off (`border-view.md`) |
| Title | `EndlessTitle.png` (62 x 27): an infinity sign, no words. Centred: x 254, y 15 |
| Style buttons | One per style, in the file's order (timed, perfection, endurance). Picture `EndlessStyleButton.png` (130 x 160: upper half up, lower half pressed), so each button is 130 x 80. Spaced 20 apart (screen width x 20 / 570) and centred as a row: x 70, 220, 370; y 60 |
| Course buttons | One per course (course1 to course4). Picture `EndlessCourseButton.png` (80 x 120), so 80 x 60, spaced 20 and centred: x 95, 195, 295, 395; y 170 (60 + 110) |
| Score texts | One per course **and** style (12): font `regular`, white, centred, more than one line allowed, empty and hidden at first. Each sits 2 pixels under its course button (y 232) and is centred on the button's middle. Only those of the selected style are shown (below) |
| PLAY | A push button of the screen's menu (text `menu_play`), centred left to right, y 280 |
| BACK | A push button (text `menu_back`, LEFT alignment) at x 20, y 280. It is the back button |
| Leaderboards | A picture button `LeaderboardsButton.png` (43 x 66, 33 rows per state) at x 497 (570 - width - 30), y 270. **Switched on only when the platform says it has leaderboards** (on the GOG copy it was not shown at all, seen 2026-10-16); if it is on and overlaps BACK, the two are put side by side, centred. Leave out of the port |
| Selection line | A white line with rounded corners (radius 4) around the selected style and course (below) |

Inside each **style button** (drawn with it, in both states):

- the style's `icon` picture (8 x 8), copied with its grey `0xffb5b5b5`
  turned white, centred, y 10;
- the style's `name`, font `title_tall`, white, centred; y = icon bottom
  + 7 - ascent + cap height;
- the style's `desc`, font `large`, white, centred, wrapped to 120
  pixels (button width - 10); y = name's y + name's height + 6 - ascent +
  cap height.

Inside each **course button**: the course's `button` picture
(`EndlessCourse1.png` ..., 80 x 60), centred, so it fills the button.

**This answers `endless-mode.md`'s question about the three missing
pictures**: the screen never asks for the style's `button` picture
(`EndlessStyleTimed.png` ...). It builds every style button from
`EndlessStyleButton.png` plus the style's icon. A search of the
decompile for reads of that field by name found only the style's own
constructor and its by-name table (a read by position cannot be found
this way).

The constructor's other branches (the two portrait layouts) place the
rows differently and were not followed in detail.

### Selecting (`select`)

The selection is one style and one course together (an `EndlessId`).
The screen starts with the one stored in the settings (`endlessIdStr`,
saved as `endlessId`, written like `perfection:course2`).

- **Unknown or missing names fall back to the second entry of the
  file**, not the first: style `perfection` and course `course2`
  (`EndlessId` constructor, `get_defaultStyle`, `get_defaultCourse`:
  index 1). No starting value for `endlessIdStr` was found in the
  settings code, so a first visit starts on **Perfection, Course 2**
  (seen in the game on 2026-10-16 with a new, empty save folder).
- A click on a style button keeps the course and selects that style; a
  click on a course button keeps the style and selects that course.

`select`:

1. Stores the selection in the settings (the file is written on the next
   frame, part 4).
2. Shows the score texts of the selected style, hides the others.
3. Redraws the selection line. With s = the style button and c = the
   course button, the line runs from s's top left corner along its top to
   its right edge, down that edge, across to c's right edge, down to c's
   bottom, along c's bottom to its left edge, up that edge, across to s's
   left edge and up to the start. The two crossings lie in the 30-pixel
   gap between the rows, 7 pixels from its top and 7 from its bottom (on
   desktop y 147 and 163: (170 - 140) / 2 - 2 x radius = 7); which
   crossing is the upper one depends on whether s's right edge is left
   of c's. The line is set fully drawn (`visibleT` = 1); no animation
   was found.

Every frame (`update`): the line is hidden while a confirm box is on
screen; the score texts are refreshed when the all-time statistics
change; the leaderboards button follows the platform.

### PLAY and BACK (`menu_onClick`)

| Id | What happens |
|---|---|
| `play` | `GameTransition.fadeToEndlessDay` with the selection: the day screen for the course's day, with a new `Endless` run (`save-format.md`, part 2, "Building the screen") |
| `back` | Fade to the title |
| `leaderboards` | Asks the platform to show the selection's leaderboard. Leave out |

### The score under each course

`refreshScoreTexts` fills each of the 12 score texts from
`AlltimeStats.getRankedScore` with the leaderboard name of its pair
(`EndlessId.toLeaderboardId`: the style's `leaderboard`, a space, the
course's `leaderboard`, for example `Perfection Course 2`):

- If the platform has a score for that name, that score is used (and
  copied into the local record, below), with its rank.
- **Otherwise the local record is used**: the entry
  `_Leaderboard:<leaderboard name>` of the all-time statistics, a text
  `score,time` (for example `_Leaderboard:Perfection Course 2` =
  `14,95`). Its rank is -1.
- The text is empty if there is no score (or a negative one). Otherwise
  it is the score (checked in the instructions), and when the rank is
  above 0 a second line `endless_ranked` ("Ranked #3"). **Offline only
  the number shows**: the local record has no rank.
- After the text is set it is centred again on the button's middle.

**So this is not only a leaderboard feature**: without any online
service the screen shows the player's best score for each course in the
selected style. This corrects `endless-mode.md`, which said the
`leaderboard` names were needed only for leaderboards (corrected there
on 2026-10-16).

When the platform answers later (`alltimeStats_onGotRankedScore`), the
text of that pair is rewritten the same way. With no platform this does
not happen (not read further).

### How the local best score is kept

When a run ends (`Endless.end`, the only caller found):

1. The run's score is taken: the final score, or the highest score
   reached for a style with `reportscoremax` (Endurance,
   `endless-mode.md`). The time is the run's clock in whole seconds.
2. `AlltimeStats.addScore`: first `addScoreLocal`, then the score is
   reported to the platform (leave out).
3. `addScoreLocal` replaces the stored `_Leaderboard:<name>` entry only
   if the new one is better (`ScoreEntry.isBetterThan`, read in the
   instructions): **a higher score wins; on an equal score, the longer
   time wins**. With no stored entry the new one is always stored. Then
   the statistics file is saved (its one-second countdown,
   `save-format.md`).
4. An `EndlessResult` (style, course, score, time) is made and the game
   fades to the endless screen with it (`FADE_TO_ENDLESS_RESULT`).

### The result box

When the screen is built with a result it shows a confirm box (part 3)
at once, with one button `confirm_ok` ("OKAY") and the text
`endless_complete` with the result filled in
(`EndlessResult.getDescription`):

```
<style name>
<course name>

<time>
<score> Points
```

(the time goes through `StringUtil.formatTime`, not read). The selection
line is hidden while the box is up. Clicking OKAY closes it; nothing else
happens (no callback is given).

Without a result the constructor instead asks the platform to connect
(`connectToSocialIfNotConnected`, leave out). In both cases it then asks
`getRankedScore` once for each of the 12 pairs without using the answer
(inferred: so that an online service fetches them; not read), and fills
the score texts.

### Hidden things

- **A "clear achievements" box.** A new press (`Pointer.justDown`) in
  the top right corner (x at least 520, y under 50), repeated quickly:
  each press within half a second of the one before adds one to a count,
  a slower one resets it to 0. When the count reaches 20 (so 21 quick
  presses, the first one only starting the count), a confirm box asks
  "Clear Achievements?" (English, written in the code) with CLEAR and
  CANCEL. CLEAR calls `AlltimeStats.clearAchievements` (not read:
  achievements belong to the platform). Part 4's table of back buttons
  said 20 taps; corrected there on 2026-10-16. **For the port: leave
  out** (no achievements).
- **`presskit_prep`**: selects Perfection / Course 2 and writes made-up
  numbers into the Perfection score texts (14, 20, 17, 8 for courses 1
  to 4), by the name apparently for press screenshots. Nothing calls it
  except the class's own call-by-name table; its name appears in no
  other function of the decompile. **For the port: leave out.**
- Four static values of the class (15, 2, 4 and the colour `0xff546754`)
  are set when the class is set up and read nowhere in the decompile
  (inferred: the compiler wrote the numbers into the code where they are
  used).

## Compared with the running game (2026-10-16)

The user ran the GOG copy in `game/` with `savedir` pointing at a new,
empty folder, `extracted/endlessrun` (gitignored), so the unlock stayed
out of the real settings. They went through the watch list below, played
one Perfection run on Course 2 and closed the game. The folder was then
decoded with `scripts/reference/savefile.py`.

**Seen by the user** (their answers to items 1 to 6 of the watch list):
all six as described. Two notes: the "title picture" is the infinity
sign `EndlessTitle.png`, which the list first called only "the title
picture" (wording fixed); and **there was no leaderboards button at
all**, so on this copy the platform does not report leaderboards. The
time's format in the result box was not noted. Only one run was played,
so "a worse later run does not replace it" (item 6) could not have been
seen.

**In the files** (written by the game):

| Part 7 says | The folder holds | Agrees |
|---|---|---|
| The right code turns on `endlessUnlocked` | `settings.sav`: `endlessUnlocked = true` | Yes |
| The choice is stored as `style:course` | `endlessId = perfection:course2` | Yes (the screen stores its choice as soon as it opens, so this alone does not show the fallback; the user saw it on screen) |
| The best score is kept as `_Leaderboard:<style> <course>` = `score,time`, time in whole seconds | `stats.sav`: `_Leaderboard:Perfection Course 2 = 0,33` | Yes |
| An endless run writes no story save | No `headers` or `save_` file | Yes |

So **the local best score is kept on a copy with no leaderboards**,
which is what the port needs.

The score was **0**, with `NumProcessed = 1` and `NumCitations = 1` in
the same file. A correct traveler at 33 seconds would have given about
10 points in Perfection, so most likely the one traveler drew a
citation, which ends a Perfection run, and no points were added. That
the citation was handled first and the points then ignored (actions are
ignored once the run is ending, `endless-mode.md`) is inferred; the
order was not read.

Evidence strength: one run, one style and course, one person watching;
the four file values are exact.

## For the port

- The code box as above: code 62131, keys 1 to 9 and 0, five blinks
  over 3 seconds, "S O R R Y" on a wrong code, Escape as CANCEL;
  `endlessUnlocked` in the settings afterwards.
- The endless screen with the two rows, the selection line, PLAY and
  BACK, the selection stored as `style:course` with Perfection / Course
  2 as the fallback, and the result box after a run.
- **Keep the local best scores** (`_Leaderboard:<style> <course>` =
  `score,time` in the all-time statistics; better = higher score, then
  longer time) and show them under the courses. Drop the rank line, the
  leaderboards button, every platform call, the clear-achievements box
  and `presskit_prep`.
- If the port reads the original game's statistics file, the same keys
  carry over; otherwise the names can be the port's own.

## Not studied

- The constructor's portrait branches (tablet, phone).
- The code box's digit line and the style buttons' description lines are
  given as formulas, not pixels. (`app.vis.Text`'s height, which they
  waited on, is read since 2026-10-16, `text-drawing.md`: lines x line
  height for these texts; the pixels were not worked out.)
- (What the LEFT alignment changes in BACK's push button was listed here,
  as in part 6. Answered on 2026-10-16, `buttons.md`: the text sits 2
  pixels from the button's left edge instead of being centred.)
- `StringUtil.formatTime`, so the look of the time in the result box.
- Whether the title's buttons can be clicked through the code box.
- (`play.ui.DiagramLine`'s drawing, dotted or solid, was listed here:
  **dotted**, single pixels two apart; read on 2026-10-16,
  `ui-parts.md`.)
- Everything behind the platform calls named above (rule 4).

## Things to watch in the game

On the title screen, click ENDLESS. (Watching this needs the game to
run, with the user's go-ahead.)

1. A box with "Complete story mode with your job intact to unlock
   endless mode", five underlines, keys 1 2 3 4 5 / 6 7 8 9 0 and
   CANCEL. Escape closes it.
2. Type a wrong five-digit code: the digits appear with spaces between
   them, then "S O R R Y" blinks five times over about 3 seconds and the
   box closes.
3. Open it again (it is empty) and type 6 2 1 3 1: the digits blink five
   times, then the game fades to the endless screen. ENDLESS goes
   straight there from then on.
4. The endless screen: no header, the title picture (an infinity sign)
   at the top, three
   style buttons (Timed, Perfection, Endurance, each with an icon, name
   and description), four course buttons below, PLAY in the middle at the
   bottom and BACK at the bottom left. **Perfection and Course 2 are
   selected**, with a white outline around both. No leaderboards button
   (seen on 2026-10-16: none at all on this GOG copy). No score
   under the courses (no runs played yet).
5. Clicking another style or course moves the outline; leaving and coming
   back keeps the choice.
6. After a run (PLAY, then the run ends), the endless screen comes back
   with a box: style, course, time and "N Points", and OKAY. The number
   then shows under that course while that style is selected, and a
   worse later run does not replace it.

---

# Part 11: the day screen, the wait screen, the screen shake, the screen flash and the news magnifier

Studied on 2026-10-16 by code reading. What the decompiler dropped was
read from the instructions: one read-only Ghidra run
(`decompiled/part11_run1.txt`, `DumpAssembly.java` on `Math.Cos`,
`Math.Sin`, `ScreenShake.update`, `Game.createStater` and the function
that ends the flash), and the `Booth` constructor's listing of
2026-10-14 (`decompiled/booth_ctor_asm.txt`) for when the booth shakes.
Numbers with `read_doubles.py`. **Not run in the game.** The reference
script is `scripts/reference/screenfx.py`.

These are the last small classes of `play.screen` that matter on
desktop. Two of them never appear on desktop (the wait screen and the
magnifier); they are described briefly so the port knows what it leaves
out.

## What was read

From the whole-game decompile in `decompiled/all/`:

| Class | Functions |
|---|---|
| `play.screen.DayScreen` | constructor `0x18044b860`, `makeStash`, `restoreFromStash`, the field list (all of it besides the field-access helpers) |
| `play.screen.WaitScreen` | constructor `0x1807d4b40`; `draw` is shared code (`0x1801c5ac0`, also `RatingScreen.draw` and `Booth.draw`) |
| `play.screen.ScreenShake` | constructor `0x180862cb0`, `start` `0x180863570`, `update` `0x1808635e0`, `clear` |
| `play.screen.GameScreen` | `shake` `0x18057e120`, the constructor again (part 1) |
| `play.screen.ScreenFlash` | constructor `0x1808615f0`, `applyFlash` `0x1808627f0`, `draw`, `clear`, `startFlash`, `get_fadeT`, `set_fadeT`, `get_flashT`, `set_flashT`, `get_isFading` (all of it besides the field-access helpers) |
| `play.screen.NewsScreenMagnifier` | constructor `0x1806d4bb0`, static constructor, `react` `0x1806d5790`, `draw` |
| `play.screen.NewsScreen` | the constructor's scaling part again |
| `Layout` | `getFitScale` `0x1804a1920` |
| `Game` | the ScreenFlash part of the constructor, `applyTransition` (`FLASH_TO_TITLE`, `REQUEST_PLATFORM_CHANGE`), `createStater` and its `flashing-to-title` function `0x18058a580`, `draw`, `wantPlatformKind` |
| `play.day.booth.Booth` | `timeBombExplode`, the `#poison-touch` part of `paper_onUnhandledLinkClicked`, the four timed functions of its `poisoned` state (closures 589, 593, 597, 601) |
| `play.day.border.Border` | `spawnExplosion` (the shake), the grenade-on-the-booth function (the flash) |
| `play.GameTransition` | `flashToTitle` |
| `app.Num` | `lerpScale` |

Every caller of `GameScreen.shake`, `ScreenFlash.startFlash`,
`applyFlash`, `flashToTitle` and the `WaitScreen` and `Tutor`
constructors was found by searching the whole decompile.

## The day screen (`DayScreen`)

The screen `day` (how it is asked for: `save-format.md`, part 2). It
holds the day, the booth, the border scene and, on phones only, a
tutorial. The constructor, in order:

1. The base of every screen (part 1), which also makes the screen's
   shaker (below).
2. The booth: `Booth(screen, boothEnvRun, day)`.
3. The border scene: `Border(screen, day, booth, day.borderRand)`
   (`border-figures.md`).
4. **The tutorial (`Tutor`), only when the day is day 1, not an endless
   day, and the run's platform is `PHONE`** (`day.run.platformKind`
   compared with the third value of `PlatformKind`: `DESKTOP`, `TABLET`,
   `PHONE`, in that order in `dump.cs`). No other code makes a `Tutor`
   (whole-decompile search; the test player only checks for one). **So
   desktop has no tutorial**, also not on day 1.
5. `enablePause(true)`: the screen can be paused (Escape on desktop,
   part 4). The black pause button is made only where the layout has
   `showPauseButton`, which desktop does not (part 1).

The constructor sets no song. The screen has no `update`, `draw` or
`react` of its own (it keeps the base screen's): the booth and the
border scene are its children and run through the entity tree (part 1).

`makeStash` stores the booth's stash, then the border's.
`restoreFromStash` restores the booth, then the border, and if both
worked stops a running tutorial (`abort`); on desktop there is none.
This matches `save-format.md`, part 2.

## The wait screen (`WaitScreen`): phones and tablets only

The screen `wait` is queued only by `REQUEST_PLATFORM_CHANGE`
(`save-format.md`, part 2), which only the settings' Device row sends,
and that row is not made on desktop (part 4). It shows
`assets/Wait.png` (47 x 7) centred: `x = floor((kPixelWidth - 47) / 2)`,
`y = floor((kPixelHeight - 7) / 2)`, and draws nothing else. While it
is the current screen and the game's state has been `on` for more than
0.01 s, `Game.wantPlatformKind` returns the requested layout instead of
the current one. That value is read by the Unity host and by the test
player (neither followed further). **Leave it out of the port.**

## The screen shake (`ScreenShake`, `GameScreen.shake`)

**Every screen has its own shaker.** The `GameScreen` constructor makes a
`ScreenShake` as a child of the screen (field `screenShake`). It moves
the whole screen: it sets the screen's position, and everything in the
screen is drawn relative to it.

**Its random generator** is made in the shaker's constructor with the
fixed seed `0x6500065` (105,906,277). So each new screen starts a fresh
generator with the same seed; it is used for nothing else.

**Starting** (`GameScreen.shake(ent, duration, magnitude)`): from `ent`,
the function walks up through the parents to the first `GameScreen` and
calls its shaker's `start`. If no parent is a screen, nothing happens.
`start` records the duration, the magnitude and the game clock's
current time (the trunk's clock). A shake started while another runs
replaces it.

**Every update** of the shaker, while a shake runs (start time not 0):

```
elapsed = clamp(now - start, 0, duration)
amount  = (1 - elapsed / duration) ^ 1.5 * magnitude
if amount < 0.001:
    stop (start time = 0); screen position = (0, 0)          (no draw)
else:
    angle = random() * 2 * pi                                 (one draw)
    screen x = floor(cos(angle) * amount)
    screen y = floor(sin(angle) * amount)
```

`lerpScale` clamps (read), which gives the `clamp`. The order of
`cos` for x and `sin` for y was read in the instructions:
`Math.Cos` and `Math.Sin` are one-jump functions to the two runtime
helpers the decompiler calls `FUN_18012fb50` and `FUN_180130a00`, and
`update` calls the first for x and the second for y. (`border-view.md`
had inferred that `FUN_180130a00` is the sine; this confirms it.)

So the screen jumps to a new whole-pixel offset every frame, smaller and
smaller, and because of `floor` it leans up and left: with magnitude 2
the offsets run from -2 to +1 in practice (+2 only for an angle of
exactly 0). A screen whose update switch is off (part 1) does not move
its shake either: the offset stays where it is.

**Who shakes** (every caller in the whole decompile):

| When | Duration, magnitude |
|---|---|
| An explosion in the border scene (`Border.spawnExplosion`, `border-scene.md`) | 1 s, 2 |
| The booth's `poisoned` state, on entering | 0.5 s, 2 |
| the same, 2 s after entering | 1 s, 2 |
| the same, 4 s after entering | 6 s, 3 |

**The `poisoned` state** is entered when a paper's `#poison-touch` link
is clicked and the booth is not already in that state
(`Booth.paper_onUnhandledLinkClicked`). In `Papers.xml` that link
belongs to the `$Powder1` mark (line 442). The booth then also tells the
engine (`setPaperPoisoned`, its argument not checked) and plays
`poison-apply`. **6 s after entering, the state asks for a flash to the
title of 3 s** (below). The four timed steps were read in the `Booth`
constructor's instructions: the state is added under the name
`poisoned`, then one function on entering and three at 2, 4 and 6 s,
then the next state begins.

Inferred from the flash's game state (it clears the screen's update
switch, `save-format.md` part 2): from 6 s on the day screen is no
longer updated, so the last shake freezes at whatever offset it had,
under the flash. The reference script follows this (`screenfx.py
poison`: 210 draws at 60 frames a second, if a shake started in a
frame is applied in that frame; that order was not read).

## The screen flash (`ScreenFlash`)

One object for the whole game, made by `Game` at start-up with the
platform's width and height (not a screen, not in the entity tree).
`Game.draw` draws it **after the whole entity tree, at (0, 0)**, so it
covers everything and is not moved by a shake.

It holds two full-screen fills, both on layer 10 and hidden at first:

| Fill | Colour | Its alpha is called |
|---|---|---|
| The fade cover | black, opaque colour (0, 0, 0, 1) | `fadeT` |
| The flash | white (1, 1, 1, 1) | `flashT` |

Setting `fadeT` or `flashT` sets that fill's alpha; 0 hides it, anything
else shows it. The black cover is drawn first, the white over it.

**The fade between screens** is the black cover. `Game`'s states
(`save-format.md`, part 2) tween `fadeT`: read from the instructions,
`on` takes it to 0, `off` to 1 (both over 0.125 s, or 0.005 s with
`skipSlowStuff`), and `off-instant` to 1 at once.

**A flash to the title** (`FLASH_TO_TITLE(d)`, from
`GameTransition.flashToTitle(d)`): `Game` calls `startFlash(d, 2)` and
goes to its state `flashing-to-title`. There, every frame, with `t` the
time in that state:

```
after = clamp((t - d) / 2, 0, 1)
if after > 0:  white alpha = 1 - after;  black alpha = 1
else:          white alpha = min(1, t / d)
when t >= d + 2: go to state off-instant, pending screen = title
```

So the screen turns white over `d` seconds, then the white fades over 2
seconds to a black screen, and the title screen is built (and fades in
from black by the `on` state). The state's exit to `off-instant` was
read in the instructions (`save-format.md` had it as dropped by the
decompiler). `clear` hides the white only; `Game.applyScreenChange`
calls it.

**Who flashes** (every caller of `flashToTitle`):

| When | `d` | Title after |
|---|---|---|
| The booth's time bomb explodes (`Booth.timeBombExplode`, after the sound `booth-boom`) | 0.1 s | 2.1 s |
| A grenade lands on the booth (`border-scene.md`; 2 s after it lands) | 0.1 s | 2.1 s |
| The booth's `poisoned` state, 6 s after entering | 3 s | 5 s (11 s after the touch) |

`get_isFading` (black cover shown and its alpha above 0.01) is read only
by the test player. The class also has three fields named
`shakeStartTime`, `shakeDuration` and `shakeMagnitude`: none of its own
functions uses them, and a search of the whole decompile for the three
names found only `ScreenFlash`'s and `ScreenShake`'s own code.

## The news screen's magnifier (`NewsScreenMagnifier`): never on desktop

`Layout.getFitScale(w, h, availableH)` returns 1 when `w` fits the
screen width and `h` fits `availableH`, else 2/3. The news screen
passes the newspaper's size and its button's y, and adds the magnifier
only when the scale is below 0.999. **On desktop the newspaper (365 x
220) fits** (570 wide, button at y 290), so the scale is 1, the
newspaper sits at x = floor((570 - 365) / 2) = 102,
y = floor(290 / 2 - 220 / 2) = 35, and there is no magnifier.

Where it is used (layouts where the newspaper does not fit): while a
pointer is held on the newspaper, a strip of the full-size newspaper
(as wide as the newspaper or the screen, whichever is less, and 75 high)
around the pointer is shown with its bottom edge 20 pixels above the
pointer, centred on it left to right, kept inside the screen, with a black shadow of alpha
128/255 offset 5 to the right and down; sounds `inspect-highlight` when
it appears and `inspect-unhighlight` when it goes. **Leave it out of the
port.**

## For the port

- The day screen: the booth and the border scene, pausable, **no
  tutorial**.
- One shaker per screen with its own generator (seed 105,906,277),
  the formula above, whole pixels; the fade and flash are drawn over the
  screen and do not shake. The four shakes and three flashes in the
  tables. Exact shake offsets only matter for a frame-identical picture:
  the shaker's generator feeds nothing else.
- The fade cover and the flash to the title as above.
- Leave out the wait screen, the magnifier and `Tutor`.

## Not studied

- `play.day.booth.Tutor` (phone only).
- How the Unity host uses `wantPlatformKind`.
- Whether the platform's width and height that size the flash are game
  pixels or window pixels.
- The order inside one frame of a state's timed functions and the
  screen's update (when a shake started in a frame first moves the
  screen); the reference script assumes the same frame.
- What `setPaperPoisoned`'s argument means in the `#poison-touch` case.

## Things to watch in the game

(Watching needs the game to run, with the user's go-ahead.)

1. **Day 1 on desktop: nothing from a tutorial.** (On phones a `Tutor`
   runs on day 1; what it shows was not read.)
2. **A border explosion** (an attack day): the whole screen jitters for
   about a second, by a pixel or two, mostly up and left.
3. **The time bomb exploding** (for example a wire cut out of order):
   the booth sound, the
   screen goes white almost at once, fades to black over 2 seconds,
   then the title screen.
4. **Touching the poison powder** on a paper: a short shake at once,
   another at 2 s, a longer stronger one at 4 s; at 6 s the screen
   whitens over 3 seconds (the shake freezes), fades to black over 2,
   and the title appears about 11 seconds after the touch.
