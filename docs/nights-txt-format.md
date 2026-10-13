# Nights.txt and how a night event is run

Studied on 2026-10-13. `Nights.txt` holds the events of the end-of-day
screen: the messages, the extra budget lines with their tick boxes, and what
happens when a line is paid or not. This doc covers the file, the calendar of
scheduled events, and how one event's lines are run. **The family's health,
the standard budget lines and balancing the budget are not covered** (see
"Not studied").

Functions read in full: the `data.NightLib` constructor, `findEvent`,
`hasEvent`; the `data.NightEvent` constructor; `play.night.Calendar`
(constructor, `fromString`, `addEvent`, `getEvents`, `toString`) and
`CalendarEvent` (`fromString`, `toString`); `play.night.Family`:
`applyEventWithId`, `applyEvent`, `applyOp`, `expandExpressionLhs`,
`applyRentAndHeatAffectingEvents` and the closure used by `Escape`;
`play.night.Budget.addLine` with its sorting function,
`getRenameSleepButton`; the `Line` constructor and `get_renameSleepButton`;
`OpHelper.makeOp` and `getRunOps` (re-read). Read in part:
`Family.applyBudget` (only where it runs a line's YES / NO lines). Two
constants were read from the DLL and five dropped arguments from the raw
instructions.

Everything here is confirmed in the code unless marked otherwise.

## The file

An indented tree (`tab-tree-format.md`) with the same line signs as
`Travelers.txt`, turned into operations by the same `OpHelper.makeOp`
(`travelers-txt-format.md`). The night code gives several signs a different
meaning:

```
BUY_UPGRADE1                                   <- event id
	? Game/Day < 31                             <- condition
		" Booth Upgrade Available: TAB key...    <- message
		> UPGRADE BOOTH | -5 | NO                <- budget line: label | amount | tick
			> YES                                 <- run if the line is ticked
				@ Upgrade-STAMPBAR_HOTKEY          <- command
				+ 3 BUY_UPGRADE2                   <- schedule an event 3 nights later
			> NO                                  <- run if it is not ticked
				+ 1 BUY_UPGRADE1
```

| Line | In `Nights.txt` | What the night code does |
|---|---|---|
| `" text` | 49 | Adds the text to the night's list of messages |
| `? condition` | 53 | Tests the condition; if true, runs the lines under it (after the rest of this line's own work, in order) |
| `> label \| amount \| tick` | 37 | Adds a **budget line** (below) |
| `> YES`, `> NO` | 23 and 13 | Only directly under a budget line. Not run when the event runs; run later, when the budget is applied |
| `+ days EVENT` | 19 | **Schedules** `EVENT` for `days` nights after the day that just ended. (In `Travelers.txt` the same sign adds a paper) |
| `= Fact/Path value` | 40 | Sets a fact of the saved story. `++N` / `--N` add to or subtract from the fact's number (read with `getValueInt` and no default; that an unset fact counts as 0 is assumed, that function was not read); anything else is stored as written |
| `@ command` | 46 | A command (below) |
| `-`, `!`, `^`, `\` lines | 0 | Nothing |

Conditions use the same tester as traveler scripts (`==`, `!=`, `has`,
`!has`, `<`, `<=`, `>`, `>=`, joined left to right by `&&` and `||`). The
left side is always looked up as a fact of the saved story.

`NightLib` keeps a table from event id to the event's top-level operations.
Asking for an id that does not exist raises an error ("Night event not
found:").

### Budget lines

The text after `>` is split at `|` and trimmed. Fewer than two parts raises
an error.

- part 1: the label shown; part 2: the amount (negative costs money);
- part 3: `MUSTPAY` (always paid, no choice), `YES` (optional, ticked to
  start with) or `NO` (optional, not ticked). **When it is missing**: a
  negative amount is optional and ticked, a positive amount is always paid.

The line remembers its YES / NO lines if it has any. After **every** added
line the whole list is sorted again: income (positive) before costs, and
within those, must-pay lines before optional ones; anything else counts as
equal. The sort is the game's quicksort, which swaps equal lines
(`news-txt-format.md`), so lines of the same kind do not stay in the order
they were added. Example from `nights_check.py`: `ESCAPE` with three
passports and little money adds "ESCAPE (SELF)" and then "ESCAPE (SELF+2)",
and they end up in the opposite order.

When the budget is applied (`Family.applyBudget`), each line that has YES /
NO lines runs its `YES` group if it is ticked and its `NO` group otherwise.
A line with no group of that name runs nothing.

### Commands

| Command | Effect |
|---|---|
| `Upgrade-INSPECT_HOTKEY`, `-INSPECT_DOUBLECLICK`, `-RULEBOOK_TABS`, `-STAMPBAR_HOTKEY`, `-BOOTH_MULTITOUCH` | Gives the player that booth upgrade |
| `MakeSonHappy`, `MakeSonSad` | If the son is alive, sets his mood |
| `AdoptNiece` | Sets "have niece" to 1 |
| `RemoveSavings` | Sets savings to 0 and updates the savings budget line |
| `TakeFamilyPassports` | Sets "have family passports" to 0 |
| `GivePaper <paper>` | Adds the paper to the list fact `Night/Papers<n>`, `n` being the day that just ended, unless already there. (`days-csv-format.md`: a day's extra papers include this list) |
| `TakePaper <paper>` | Removes the paper from `Game/StayingPapers` |
| `End <id>` | Asks for that ending, **only if no ending has been asked for yet** |
| `Include <event>` | Runs another event's lines here |
| `Achievement <id>` | Awards an achievement (out of scope for the port) |
| `Escape <n>` | Below |
| `RenameSleepButton <text id>` | Nothing when run. The budget looks for it in the YES lines of ticked lines and, if found, shows that text entry on the sleep button (`budget_escape`) |
| anything else | Nothing |

The fixed-name commands are tested first, then the ones with an argument in
the order shown.

`Escape <n>`: the living family members, in the fixed order son, wife, niece,
uncle, mother-in-law, are split into the first `n - 1` (taken along) and the
rest (left behind). It sets the wanted ending to `flee` if anyone is left
behind and `escape` otherwise (**replacing** any ending already asked for),
and the saved facts `End/FamilyEscapeIntro` and `End/FamilyEscapeFinal`
(sentences built from text entries), `End/FamilyPassportsImage` =
`Passport<taken + 1>.png` and `End/FamilyTakeCount` = the number taken.

## The calendar

A list of (day, event id) pairs, saved in one story fact as
`day:event;day:event` (the fact is `Night/Calendar`: the name is among the
code's strings; that the calendar uses it is in the `Family` constructor,
not read yet). A piece that does not have exactly two parts is skipped.
`+ days EVENT` appends (ended day + days, event). `getEvents(day)` returns
that day's events in the order they were added.

## One special pass: rent and heat

`applyRentAndHeatAffectingEvents(ids)` goes through the given events and
runs only their **top-level** set-fact lines for `Night/Rent` and
`Night/Heat`. With the data that is `APARTMENT_RENT` (rent becomes 25). When
it is called is in the `Family` constructor, not read yet.

## Check against the data files

`scripts/checks/nights_check.py` (run 2026-10-13), using the reference
script `scripts/reference/nights.py`:

- 40 events, no repeated id. Lines: 73 `>` (37 budget lines, 23 `YES`,
  13 `NO`), 53 `?`, 49 `"`, 46 `@`, 40 `=`, 19 `+`. No sign the night code
  ignores is used.
- Budget lines: 24 have three parts (21 `NO`, 2 `YES`, 1 `MUSTPAY`), 13
  have two. Every amount is a whole number. Every `YES` / `NO` group sits
  directly under a budget line. Five positive amounts are optional: the
  three "MOVE TO CLASS-8" refunds (not ticked) and the two "EZIC GIFT" lines
  (ticked: "Uncheck to burn it").
- `+` lines: 1, 2, 3, 6 or 8 nights ahead; all 11 scheduled events exist.
- Commands: every one is known to the code. All `Include` targets exist;
  the six `End` ids are in `Ends.xml`; `FamilyPhoto`, `SonDrawing` and
  `Watch` are in `Papers.xml`; `budget_escape` is a text entry.
- Facts tested or set: 16 tested, 6 set. Three exist only in data files
  (`Night/ApartmentTimer`, `Night/EzicPayout`, `Game/EzicAgentsApproved`);
  the rest are also named in the code.
- **Every event is named by something**: 13 in the `NIGHTEVENTS` row of
  `Days.csv`, 4 by `Night` commands in `Travelers.txt` (`EZIC_REWARD`,
  `FRIENDLY_GUARD_PAYOUT`, `HANGINGS_PENALTY`, `SELL_WATCH`), 11 scheduled,
  6 included, and 7 whose id is among the code's strings (`AFTER_6PM`,
  `ATTACK_DIDNOTHING`, `ATTACK_FIREDGUN`, `ATTACK_SOLVED`, `EASY_MODE`,
  `FINAL`, `POISONING`; where the code uses them is not read yet, and
  `POISONING` is also a news id).
- Commented out in the file: `SISTER_LOAN`, `STOLE_TOO_MANY_PASSPORTS`, and
  a `+ 1 SISTER_LOAN` line in `EZIC_CLEARED`.
- Behaviour of the reference: the apartment offer, move and timer; the
  detain bonus (5 for 2-3 detains up to 30 for 12 or more, leaving the
  remainder); escape with three passports (son and wife taken, three left
  behind, ending `flee`, `Passport3.png`); `FINAL` choosing an ending and a
  second `End` not replacing it; the calendar text round trip.

## Notes for the port

- `+` means "schedule" here and "add a paper" in traveler scripts.
- Re-sort the budget after each added line with the same quicksort.
- A true condition's lines run right away, before the next line of the
  event; YES / NO lines run only when the budget is applied.
- `End` keeps the first ending asked for; `Escape` overrides it.

## Not studied

- (Studied since, in `night.md`: the `Family` constructor, the family
  members, the standard budget lines, `applyBudget`, balancing. The fact
  names behind `AdoptNiece`, `RemoveSavings` and `TakeFamilyPassports` are
  confirmed there.)
- `Family.buildMessage` (the escape sentences) and the night screen itself.
- How a traveler script's `Night <id>` command reaches the night.
- Nothing here has been compared with the running game.
