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
- Not written yet: ending player, endless-mode screens, language chooser,
  pause screen, settings, credits.

---

# Part 1: the base of a screen, and the night screen

Studied on 2026-10-14 by code reading. **One screenshot of the real night
screen was compared afterwards, the same day** ("Compared with a
screenshot" below): it confirms the order of the budget lines and several
positions. Everything that moves or needs a click is still not watched;
the list is at the end.

## What was read

Read in full, from `decompiled/night_screen.clean.c` (all 228
`play.night` functions, decompiled for this part), `screens.clean.c`,
`ent.clean.c`, `stater.clean.c` and `revealtext.clean.c`:

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

**Not read:** the `FamilyVisuals` constructor (1,930 lines: the family
portraits, the apartment, the tokens, the passports) and
`FamilyVisualsDim`; `play.ui.Button`, `play.ui.DiagramLine`,
`app.vis.Text`; `GameScreen.addHeader`, `addMediaButtons`, `shake`.

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
  drawn in order by `draw`), a song name (`songId`) and a screen shaker.
- `enablePause(black)` marks the screen as one that can be paused
  (`canPause`). If the layout has `showPauseButton` set, it also makes a
  pause button in the top right corner (4 pixels from the top), white, or
  black when `black` is true. The button is added to the screen on the
  first `update`. A click calls `GameTransition.setPause(true)`.
  **Desktop has no such button**: the `Layout` constructor sets
  `showPauseButton` in its two portrait blocks only (settled in part 2,
  "The desktop block of the layout"; part 1 first left this open). On
  desktop the pause is on a key (`save-format.md`).
- `makePushButton(parent, text, align, red)` builds the game's standard
  wide button from `PushButton.png` (129 x 38) or `PushButtonRed.png`,
  with text colour `0x556855`, or `0xcc2e2e` on the red one. The picture
  is cut into an upper and a lower half of 19 rows, both given to the
  button's `normal` mode; what the second half is for (pressed, by the
  look of the picture) is in `play.ui.Button`, not read.

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
4. The family pictures (`Family.makeVisuals`, not read).
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
   (`FamilyVisuals.hideTopDivider`).

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
| `revealBudget` | Every frame: n = the whole part of (seconds in this state x 4). The first n lines are active (visible and clickable). When n changes and is not above the number of lines + 1, the sound `text-reveal` plays. The rule shows once n reaches the number of lines, the total once n reaches that + 1, and at + 2 the state becomes `on`. On leaving: every optional line's tick circle blinks (`flashCheck`: hidden and shown in turn, six steps, ending shown, if the tween helper counts from 0 to 1 as its use suggests; inferred: over 2.0 seconds, from the `2.0` passed to it. The helper was not read) |
| `on` | On entry: every message shown in full, every line active, rule and total shown |

So the lines appear one per quarter of a second.

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
between messages and lines in `calcSplit`, the family pictures) is left
for the drawing step.

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
  the two.) That fits `react` testing the line's whole rectangle. What
  changes the cursor was not read, and a click there was not reported.
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

What the picture shows of the parts **not read** (`FamilyVisuals`), noted
for the part that will read them: on the right, one row per living member
with round badges (COLD, SICK, HUNGRY) and the name under them; top right,
the apartment class ("8 CLASS"); on the left, a column of seven dotted
circles, a booklet picture marked "x5", and four dotted rectangles.

## Not studied

- `FamilyVisuals` and `FamilyVisualsDim`: every picture of the family, the
  apartment, the tokens and the passports. Proposed as its own part.
- The exact placement of everything (see "Layout").
- `play.ui.Button` (how a button reacts, its modes), `play.ui.DiagramLine`
  (the rule), `app.vis.Text`, the tween helper behind `flashCheck`.
- What `revealAll` does with its sound (its condition uses a counter whose
  writer was not looked up).
- What the "instant" option of `Stater.go` changes. This screen sets no
  blend time, so it should not matter here (inferred).
- Where the day fills in its summary, and how a script's `Night <id>`
  command adds to the night events (still open from `night.md`).
- Which key pauses, and the pause screen.

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

From `decompiled/screens.clean.c` (condensed copy `screens.short.c`):

| Class | Functions |
|---|---|
| `play.screen.TitleScreen` | constructor `0x180673be0`, `menu_onClick` `0x1806764f0`, `update` `0x180676bc0`, `react` `0x1806769f0`, `unlockConfirm_onDone` `0x180676b10`, `downloadUrl` `0x1806762d0`, `draw`. `confirm_onClick` is the shared empty function: it does nothing |
| `play.screen.Menu` | all of it: constructor, `addButton`, `addImageButton`, `addPushButton`, `applyCenterY`, `button_onClick`, `getButton`, `getCenterButtonsBounds`, `manageButton`, `setAllButtonsActive` |

Checked in the instructions: the two arguments the decompiler dropped in
`update` (`decompiled/titlescreen_update_asm.txt`), and the layout values
(`decompiled/layout_ctor_asm.txt`). Seven number constants read with
`read_doubles.py`.

**Not read:** `UnlockConfirm` (the box that asks for the endless code),
`play.ui.Button`, `app.aud.Music` (what a "beat" is), the platform
functions `canExit`, `osName` and `decoratedVersion`, the test tooling
class `SoakTapper`.

## The desktop block of the layout

The `Layout` constructor has three blocks, one per platform kind
(`border-view.md`). `border-view.md` found that `borderShowSnipingSurround`
is set in the two portrait blocks and not in the desktop one. The same two
blocks, and only they, write `showPauseButton` and `menuItemPaddingY`, so
the third block is the desktop one. Values for desktop, read from the
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
| `menuItemPaddingY` | 0 | No write found outside the portrait blocks (both set 20) |

"No write found" means no instruction that stores to that field through
the register holding the layout; a store by another route would have been
missed.

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
| `endless` | If the setting `endlessUnlocked` is on: fade to the screen `endless`. If not: a box asking for a code is shown (`UnlockConfirm`, with the text `endless_unlock` and the code `endless_code` from the language's fixed values). When the box reports success: the setting is turned on and the game fades to `endless` |
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

What a "beat" of the music is, and so how long the rise takes in seconds,
was not read.

## The menu helper (`Menu`)

A `Menu` belongs to one entity (the host) and keeps its buttons by id.

- `addPushButton(id, text)`: a standard button (`makePushButton`), centred
  horizontally and added to the **centre column**. An id of `back` or
  `cancel` also makes it the back button (`setAsBackButton`, not read).
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

- `UnlockConfirm`: how the code is typed and checked.
- The music's beat, so the rise's length in seconds and the bob's tempo.
- `play.ui.Button`, including what "back button" means (inferred from the
  name: the button a back key presses).
- Whether a `newversion` button is made anywhere.
- `Layout.notchHeight` on desktop (inferred 0: there is no notch).

## Things to watch in the game

1. At the first start the title rises in visible steps with the music;
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

From `decompiled/screens.clean.c` (condensed copy `screens.short.c`):

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
`play.ui.KineticScroll` (dragging with momentum), the two "passthrough"
helper classes, `play.ui.Button`.

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
   ending's bit is not set. (Sizes, places and the other colour were not
   recovered. The number of marks is taken from the endings list:
   inferred.)
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
(`KineticScroll`, not read). In landscape only sideways: the vertical
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
there before slides from its old place to the new one (a tween given 0.5,
inferred seconds, eased), and the whole grid slides if the number of
tracks changed.

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
`dangerous` one. From the order of their names, the third value of
`continue` is `freezeAfterClick`; that its value is "true" is inferred.

## For the port

- The tree, the 5-track limit and the track rule must match, or saves
  made in a different order would land elsewhere.
- The summary box needs the news of the day built once, with a generator
  of its own seeded 0.
- The date on a button is the save's real date and time
  (`save-format.md`), so a browser port needs a clock for it.

## Not studied

- Positions in the constructor (heading, ending marks, day headers, drag
  hints, the bands), and the ending marks' second colour.
- `drawConnectingLine`: the shape of the line between a save and its
  parent.
- `KineticScroll`, the passthrough helpers, the `Confirm` constructor.
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
