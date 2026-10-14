# The screens

How each screen of the game is put together and what it does every frame.
How a screen is asked for and built is in `save-format.md`, part 2. The
rules behind a screen are in that topic's own doc (for the night:
`night.md`).

- **Part 1** (2026-10-14): what every screen is built on (`GameScreen`, and
  the switches every on-screen object carries), and the night screen.
- Not written yet: title, ending player, endless-mode screens, language
  chooser, load screen, pause screen, settings, credits.

---

# Part 1: the base of a screen, and the night screen

Studied on 2026-10-14. Code reading only: **nothing in this part was
compared with the running game.** A list of things that can be watched in
the game is at the end.

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
  By the instructions of the `Layout` constructor, `showPauseButton` is
  set in two of its three layout branches; which branch is the desktop
  one was not established here, so whether desktop has the button is
  **not known** (the pause itself is on a key: `save-format.md`).
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
This follows from the code and from the reference's line order; neither
was watched in the game.

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
  family: `Night/FamilyAlive` (4 if not set), `Night/Savings` (30 if not
  set), the number of entries in `Night/TokenIds`, and `Night/Apartment`
  (`C8` if not set). Its one caller is `LoadScreen.loadButton_onClick`
  (the load screen, a later part).

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

From the decompiler only: a line's amount is right-aligned at the
rectangle's width and the tick circle starts 10 pixels after it. The rest
of the placement (header, texts, the split between messages and lines in
`calcSplit`, the family pictures) is left for the drawing step.

The width the messages wrap at (`Layout.nightMessageWidth`) is the screen
width minus 20 in one layout branch and minus 50 in the other two; which
is the desktop one was not established.

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

None of these has been watched. Any normal night will do for 1 to 4.

1. **The order of the lines. This is the one that matters most.** The
   screen shows the budget's lines in the budget's own order. The
   reference (`nights.py`) predicts an order that changes with the number
   of lines, because the game's sort moves equal lines around
   (`nights-txt-format.md`):

   | Sick members | Predicted order, top to bottom |
   |---|---|
   | 0 | savings, salary, rent, **heat, food** |
   | 1 | **salary, savings**, rent, medicine, food, heat |
   | 2 | savings, salary, rent, heat, medicine, medicine, food |
   | 3 | salary, savings, rent, food, medicine, medicine, heat, medicine |

   (Standard lines only, no penalties or bribes, savings and salary above
   0; the amounts themselves do not change the order.) This order has never
   been compared with the screen, and it looks odd enough to doubt. If the
   game shows a steady order (savings, salary, rent, food, heat,
   medicine), then the sort in the reference is wrong for the budget, and
   so is the order in which balancing unticks lines. The comparison
   function was read again in this part and matches the reference; the
   sort routine itself was not re-read.
2. Food and heat show a **filled dot** when the screen has finished
   appearing (with enough money).
3. A click anywhere on such a line, not only on the circle, flips it, and
   the line turns grey-green when unticked.
4. The appearing: about one second of nothing, the messages letter by
   letter, then one line every quarter second, then the circles blink.
5. With too little money: the screen opens with lines already unticked,
   and ticking one you cannot afford makes the total blink for about two
   seconds with a small mark on a line.
6. Whether SLEEP can be clicked before the lines have appeared.
