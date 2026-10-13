# The night: family, budget and what happens on sleeping

Studied on 2026-10-13. This is the logic behind the end-of-day screen: who
is in the family, how hunger, cold and sickness work, which budget lines
appear, which events run, and what happens when the player goes to sleep.
The events themselves and the event file are in `nights-txt-format.md`.

Functions read in full: the `play.night.Family` constructor, `applyBudget`,
`getMember`, `getEveryoneIsDead`, `getNumMembersAlive`, `adjustAllStats`;
`play.night.FamilyMember` (constructor, `get_isAlive`, `get_isSick`,
`get_isVerySick`, `get_emotionFlags`, `updateSickness`, `adjustStat`,
`toString`, `fromString`); `play.night.Stat`; `play.night.Budget`
(constructor, `get_profit`, `get_total`, `updateLineCost`, `balance`,
`willPay`). The strings and branches the decompiler dropped in the
constructor (which attack event, which sickness message) were read from the
raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## What the night is given

A `Family` object is built from: the game data, a random generator (not used
by anything read here), the saved story's facts, the day's summary, and an
"easy mode" switch. The summary (`play.day.Summary`) carries: the day number,
travelers processed **paid** and **unpaid**, the number of penalties and
their cost, bribe money, the attack result, whether there was an attack, a
bomber or a poisoning, token ids, the day's night event ids, and escape
passports collected.

## Saved facts

| Fact | Default | Meaning |
|---|---|---|
| `Night/Savings` | 30 | Money carried over |
| `Night/Rent` | -20 | Tonight's rent (negative) |
| `Night/Heat` | -10 | Tonight's heating cost |
| `Night/Apartment` | `C8` | Apartment class |
| `Night/HaveNiece` | 0 | 1 once the niece is adopted |
| `Night/HaveFamilyPassports` | 1 | Set to 0 by `TakeFamilyPassports` |
| `Night/NumEscapePassports` | 0 | Passports collected for the escape |
| `Night/Flags` | 0 | Bit 1: the "after 6PM" message has been shown |
| `Night/TokenIds` | empty | Tokens collected, separated by `;` |
| `Night/Calendar` | empty | Scheduled events (`nights-txt-format.md`) |
| `Night/<member>` | empty | One family member's state |
| `Night/AttackResult` | set each night | `NONE`, `FAILED_DIDNOTHING`, `FAILED_FIREDGUN`, `SOLVED`, or `HIT_INNOCENT_` / `HIT_GUARD_` / `HIT_TARGET_` followed by `RIFLE` or `TRANQ` |
| `Night/Profit` | set each night | See step 9 below |
| `Night/FamilyAlive` | set on sleeping | Number of living members |

## The family

Members, in this order: wife, son, mother-in-law (`mil`), uncle, and the
niece last if `Night/HaveNiece` is not 0. Each has three counters that start
at 0 and cannot pass their limit:

| Member | Sick limit | Hungry limit | Cold limit |
|---|---|---|---|
| wife | 5 | 2 | 3 |
| son | 4 | 1 | 3 |
| mil | 4 | 2 | 4 |
| uncle | 3 | 3 | 3 |
| niece | 4 | 2 | 3 |

- **Alive** while sick is below its limit. **Sick** when sick is above 0.
  **Very sick** when sick is at the limit minus one.
- A member is saved as text such as
  `hungry=0 cold=0 sick=0 justDied=false alive=true`, plus `moodEmotion=...`
  when a mood is set. (The pairs go through a lookup table when written, so
  their order in a real save was not determined.) This is the text that
  conditions like `Night/wife has alive=true` test.
- The face shown combines flags: dead alone; otherwise hungry (hungry above
  0), cold (cold above 0), very sick or sick, and the mood if any; plain "ok"
  when none apply.

## Building the night (the `Family` constructor), in order

1. **Rent and heat first**: the day's night events are scanned and only
   their top-level lines that set `Night/Rent` or `Night/Heat` are run
   (`nights-txt-format.md`). So a rent rise shows in the same night's
   budget.
2. Read the calendar and the family members from the saved facts.
3. Set `Night/AttackResult`.
4. **Standard budget lines**, added in this order (each addition re-sorts
   the list, see `nights-txt-format.md`):

   | Line | Amount | Kind |
   |---|---|---|
   | `SAVINGS` | `Night/Savings` | fixed (it is not negative) |
   | `SALARY (n)` | 5 per **paid** traveler; `n` is their number | fixed |
   | `PENALTIES (n)` | minus the penalty cost; only if there were penalties | fixed |
   | `BRIBES` | the bribe money; only if not 0 | fixed |
   | `RENT` | `Night/Rent` | fixed |
   | `FOOD` | -5 per living member | optional, ticked |
   | `HEAT` | `Night/Heat` | optional, ticked (fixed if it is 0) |
   | `MEDICINE (WHO)` | -5, one line per living member who is sick | optional, ticked |

   "Fixed" and "optional" follow the rule for a line with no tick setting:
   a cost is optional and ticked, anything else is always applied.
5. **Attack message**: result `FAILED_DIDNOTHING`, `FAILED_FIREDGUN` or
   `SOLVED` runs the event `ATTACK_DIDNOTHING`, `ATTACK_FIREDGUN` or
   `ATTACK_SOLVED`. Result `NONE` runs `ATTACK_DIDNOTHING` if there was an
   attack of any kind or a bomber. Other results run nothing here.
6. If there was a poisoning: the event `POISONING`.
7. The day's own night messages from `Days.csv` (`DayLib.getNightMessages`,
   not read) are added to the message list.
8. If the "after 6PM" flag is not set and there were unpaid travelers: the
   event `AFTER_6PM`. Then messages for the family: who died last night
   (`family_died_<count>`), and one sickness line: `family_verysick_1` or
   `_many` if anyone is very sick, otherwise `family_sick_1` or `_many`.
9. `Night/NumEscapePassports` becomes the smaller of (living members + 1)
   and (its old value + passports collected today). `Night/Profit` is set to
   the budget's **profit**: every income line plus every fixed line.
10. **Events**: the day's night events in order, then the events the
    calendar holds for this day in the order they were scheduled, then
    `EASY_MODE` if easy mode is on.

The calendar is never pruned: past entries stay in the saved text.

## Balancing (`Budget.balance`)

While the total of ticked lines is negative: going from the **last** line
upwards, untick each line that is optional and ticked. It stops as soon as
the total is not negative, and reports the last line it unticked. Fixed lines
are never unticked, so the total can stay negative. When the screen calls
this is not read.

## Going to sleep (`applyBudget`), in order

1. Add the day's tokens to `Night/TokenIds`.
2. If there were unpaid travelers, set the "after 6PM" flag.
3. `Night/Savings` = the total of ticked lines.
4. Heat ticked: everyone's cold goes down one, otherwise up one. Food
   ticked: everyone's hungry goes down one, otherwise up one. (Dead members
   do not change.)
5. For each member whose medicine line is ticked: sick goes down one.
6. Each budget line with YES / NO lines runs the matching group.
7. Each living member: if hungry is at its limit, sick goes up one; if cold
   is at its limit, sick goes up one (both can apply); the mood is cleared;
   a member who just reached the sick limit is marked "just died". For a
   member already dead the mark is cleared.
8. Save the calendar, `Night/FamilyAlive` and each member.
9. On the last day (the number of days in `Days.csv`): run the event
   `FINAL`.
10. If no ending has been asked for: total below 0 gives the ending
    `in-debt`; otherwise everyone dead gives `family-dead`.

## Check

`scripts/checks/night_check.py` (run 2026-10-13), using the `Family` class in
`scripts/reference/nights.py`:

- All 32 text entries the night code asks for exist in `Text.xml`.
- Night 1 with 8 paid travelers: savings 30, salary 40, rent 20, heat 10,
  food 20, leaving 20.
- A rent rise appears in the same night's budget. With too little money,
  balancing unticks food and then heat; the family gets hungry and cold, the
  son (hungry limit 1) is sick at once, and a negative total gives `in-debt`.
- Never paying for food or heat: the son dies on night 3, the others on
  night 4, ending `family-dead`.
- Sickness: a very sick son gives "Your son will die without medicine." and
  medicine lines for son and wife; paying lowers both by one.
- A stopped attack adds the "SHARPSHOOTER BONUS" line; the after-6PM message
  shows once and not again.
- All 31 story days run with their own night events and whatever the
  calendar scheduled, without error; the last night chooses an ending.

## Notes for the port

- Order matters in "going to sleep": comfort and medicine first, then YES /
  NO lines, then sickness and deaths, then the ending.
- Counters move one step at a time and stop at 0 and at their limit.
- `Night/Profit` is computed before the night's events add their lines.

## Not studied

- The night screen (`NightScreen`): when `balance` is called, how ticking
  works, the sleep button, how the wanted ending is acted on.
- `Family.buildMessage` (the reference infers it from the text entries),
  `Family.getSummary`, `DayLib.getNightMessages`, `MapUtil.toSimpleString`,
  the `FactAdaptor` classes (taken at face value: a fact path plus a
  default).
- Where the day fills in the summary, and how a script's `Night <id>`
  command adds to its night events.
- What the random generator given to `Family` is used for (nothing in the
  functions read).
- Nothing here has been compared with the running game.
