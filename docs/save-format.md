# Saves: where they live and what is in them

Studied on 2026-10-14 in two parts. Part 1 is the save folder, the
encryption, the tree of saves and what one save holds. Part 2, further
down under "Part 2", is how the game moves between screens (the rest of
`Game.applyScreenChange`) and the "stash": a snapshot of the point the
player has reached, meant for resuming after the game was closed.

Part 1, functions read in full: `play.EncryptedStore` (all), `app.XXTea`
(`encryptString`, `decryptString`, `btea_encode`, `btea_decode`,
`toKeyArray`), `HostUnity.UnityPlatformDisk` (all six),
`play.save.SaveHeader`, `SaveNode` and `SaveManager` (all), `play.StoryState`
(all), `data.FactSet.toXmlDoc`, `fromXmlDoc`, `setValueStringArray` and the
plain setters, the `data.FactValue` constructor, `app.MapUtil.toXml` and
`fromXml`, and from `play.Settings`: the constructor, `load`, `save`,
`toString`, `setFromString`, the two platform-override functions. From
`play.AlltimeStats` only `load`, `save`, `queSave` and `update` were read:
the rest of that class talks to the platform's achievements and leaderboards
service, which is out of scope (online). (Its local score keeping was read
later, on 2026-10-16: `addScore`, `addScoreLocal`, `getRankedScore`, in
`screens.md`, part 7.) Six number constants were read from
the DLL and five dropped string arguments were recovered with
`ListStringUses.java`.

Everything below is from the code unless a line says it was seen in a real
save. The real save is described under "Compared with a real save".

## The save folder

`UnityPlatformDisk` keeps one folder. It is the path after the command-line
word `savedir`, if given. Otherwise it is Windows' application-data folder
plus `3909\PapersPlease` (Unity's `persistentDataPath` is used only if
Windows gives no application-data folder).

Every stored item is one text file in that folder: **`<name>.sav`**.

- Reading: if the file exists, its whole text; otherwise "nothing".
- Writing: the folder is created if missing, then the text is written.
- Writing "nothing" deletes the file if it exists.

The test player swaps this disk for one that keeps everything in memory
(`comparing-with-the-game.md`), which is why its runs leave no save files.

## The encrypted store

`play.EncryptedStore` sits on top of the disk and is what the rest of the
game uses. It has two operations.

**Set** `name` to a value: the text `PPSAVE1` is put in front of the value,
the result is encrypted, and the encrypted text is written to `<name>.sav`.
Setting "nothing" deletes the file.

**Get** `name`: read the file; no file gives "nothing". Decrypt. If the
result does not start with `PPSAVE1`, the answer is "nothing" (so a damaged
or foreign file is treated as missing, with no error). Otherwise the answer
is everything after `PPSAVE1`.

### The encryption (`XXTea.encryptString`)

The cipher is the same XXTEA as for `Art.dat` (`art-dat-format.md`): the
constant `0x9E3779B9`, `6 + 52 / word_count` rounds (whole-number division),
and four key words taken from the MD5 hash of a key string. Only the key
string and the packing differ.

1. The text is padded with NUL characters (character code 0) until its
   length is a multiple of 4.
2. Every 4 characters become one 32-bit number, the first character in the
   highest byte. Character codes are **not** cut down to 8 bits, so a
   character above 255 would spill into its neighbours and come back wrong.
   (In the real save the highest character code is 121; nothing above 127
   was seen.)
3. The numbers are encrypted as one XXTEA block.
4. Each number is written as 8 hexadecimal digits, upper case, and the
   pieces are joined with nothing in between. That hexadecimal text is the
   file.

Decrypting reverses this: 8 hex digits per number, decrypt, 4 characters
per number. **The padding NULs are not removed**, so a value read back can
end in up to three NUL characters. Empty text decrypts to empty text.

The key string is string literal 3240 in Il2CppDumper's output (16
characters). Like the `Art.dat` key it is deliberately not written in this
repo; `savefile.py` reads it from `dumps/il2cppdumper/stringliteral.json`.

## What is stored

| Name | Written by | Content |
|---|---|---|
| `headers` | `SaveManager` | The tree of saves, as indented text (below) |
| `save_<id>` | `SaveManager` | One save: the story facts as XML (below) |
| `settings` | `Settings` | The player's settings as XML |
| `stats` | `AlltimeStats` | All-time statistics as XML |
| `names` | `NameCycler` | Where the name order has got to (`traveler-build.md`) |
| `stash` | `SaveManager` | The resume snapshot: at most one, written and deleted as the game moves between screens ("The stash" below). Seen and read in a real folder on 2026-10-14 |
| `platover` | `Settings` | `tablet` or `phone`: a forced layout. **Not encrypted**; written straight to the disk |

The test player's `auto.plan` and `auto.log` live in the same folder but
are not part of the store (`comparing-with-the-game.md`).

## The tree of saves (`headers`)

The game keeps every save and remembers which save each one was continued
from. That is the branching timeline of the load screen.

### One save's line (`SaveHeader`)

Six values joined with `;`:

```
id;parentId;time;day;money;family
```

| Value | Meaning |
|---|---|
| `id` | 32 random characters from `A`-`Z` and `0`-`9`. The root's id is `NEW` |
| `parentId` | The id of the save this one was continued from; `NEW` for a first save; empty for the root |
| `time` | When it was saved: milliseconds since 1970-01-01 UTC, as a decimal number (for example `1791924498479.45`) |
| `day` | The fact `Game/Day` (the day that is about to be played) |
| `money` | The fact `Night/Savings` |
| `family` | The fact `Night/FamilyAlive` |

The id's characters are picked with `Math.random()`, the .NET generator,
not with any of the game's seeded generators.

A new header starts as: id `NEW`, empty parent, the current time, day 1,
money 0, family 0. Reading a line whose whole text is `NEW` gives that too.

### The text

One line per save. A save's line is indented one tab more than the save it
hangs under, and is followed by its own children. The first line is the
root. Each line ends with a line feed. It is read with the game's indented-
tree reader (`tab-tree-format.md`); a line has no spaces, so it is one
parameter.

When the text is read (`SaveNode.fromTabNode`):

- Only the first top-level line and what hangs under it is used. No
  `headers` entry, or an empty one, gives a lone root.
- A child whose id is `NEW` is dropped, with everything under it.
- Each save's children are sorted by time, oldest first. (This uses Haxe's
  `Array.sort`, the unstable sort noted in `news-txt-format.md`.)
- The save with the newest time in the whole tree is marked `latest`
  (unless that is the root).

Helpers on a tree node: the newest header and the newest node under it, the
highest day under it, the number of saves under it, find by id (itself
first, then its children in order), insert, remove.

- **Insert** finds the node whose id is the header's `parentId` and adds the
  save under it, unless a child with the same id is already there. If the
  parent is not found nothing is added and nothing is reported (a message
  goes to the debug log only when it is switched on).
- **Remove** finds the node and takes it out of its parent's children. The
  root has no parent, so it is found but stays.

## Saving, loading, deleting (`SaveManager`)

The manager reads the tree from `headers` afresh for each of these.

**Save** a fact set, in order:

1. Make a header from the facts: a new random id, `parentId` from the fact
   `Save/ParentId` (default `NEW`), the day, money and family as above, the
   current time.
2. If the header's day is not later than the fact `Save/ParentDay` (default
   1), the parent becomes `NEW`: the save hangs directly under the root.
3. Insert the header into the tree and write the tree back to `headers`.
4. Write the facts as XML to `save_<id>`.
5. Only then set the facts `Save/ParentId` to the new id and
   `Save/ParentDay` to the header's day. So a save file holds the id and
   day of the save **before** it, not its own.

**Load** an id: `NEW`, or an id with no file, gives an empty fact set.
Otherwise the XML is read back into a fact set, and `Save/ParentId` is set
to the loaded id and `Save/ParentDay` to its `Game/Day`. Whatever is saved
next therefore hangs under the loaded save.

**Delete** an id: remove it from the tree, write `headers`, then delete its
file and the files of every save under it, children first. Deleting a save
deletes everything that was continued from it.

`makeBackup` is called at the start of save and delete. In this build it is
an empty function.

A save takes no part in the game's randomness: nothing in it is a seed, and
the id uses .NET's generator. Loading draws a new story seed
(`run-and-seeds.md`).

## One save (`save_<id>`)

The whole story state is one **fact set**: a list of named text values
(`facts-xml-format.md` describes facts). A save is that list and nothing
else:

```
<facts><f v="2" p="Game/Day"/><f v="30" p="Night/Savings"/>...</facts>
```

- One `f` per fact: `p` is the fact's path, `v` its text. No line breaks,
  no XML declaration.
- Only a fact's text is saved. A fact value can also carry a name, a date
  and a translated text; none of these is written, and on loading they are
  empty.
- The facts are written in the order the game's string map walks them
  (`haxe-maps.md`), which is not alphabetical and changes as facts are
  added. Seen in the real saves: the same two facts swap places between two
  saves. The order was not compared with `haxemap.py`.
- Seen in the real saves: `v` is written before `p`. The code sets `p`
  first; the written order comes from the XML printer (inferred: attributes
  are kept in a map too). A reader must go by attribute name.

### The story state (`StoryState`)

`StoryState` holds the fact set, the id of the save it came from (`NEW` at
first), the all-time statistics, and which set of booth upgrades the
platform has. How it starts depends on a "purpose":

| Purpose | Facts at the start |
|---|---|
| `NORMAL` | Empty |
| `FROMEXISTING` | A copy of a given fact set |
| `FORENDLESS` | Empty, then every upgrade the platform allows is given |
| `SKIPTODAY` | Empty, then filled in for the given day (the debug jump, below) |

In every case the fact `Game/Device` is then set to `desktop`, `tablet` or
`phone`. The same happens after loading and after restoring a stash.

- `load(manager, id)`: remember the id, replace the facts with the loaded
  set, set `Game/Device`.
- `save(manager)`: save the facts and remember the new id.
- **Upgrades** are the fact `Game/Upgrades`: upgrade names joined with `;`.
  "Has upgrade" is a plain "the text contains the name" test. The allowed
  upgrades are, for desktop: `INSPECT_HOTKEY`, `STAMPBAR_HOTKEY`,
  `RULEBOOK_TABS`, `INSPECT_DOUBLECLICK`; tablet: `BOOTH_MULTITOUCH`,
  `RULEBOOK_TABS`; phone: `RULEBOOK_TABS`.
- **Statistics** are facts named `Game/Stat/<name>`. Adding to one also adds
  to the all-time statistics; "raise to at least" does the same. Play time
  is counted by adding 1 to `Game/Stat/PlayTime` for every full second.
- The day number is the fact `Game/Day` (default 1).

### The debug jump to a day (`applySkipToDay`)

Used by the "skip to day" and "skip to traveler" jumps
(`comparing-with-the-game.md`). It fakes the facts a player would plausibly
have on that day `d`:

- `Game/StayingPapers`, only when `d` is below 100: `EzicNote` on day 9;
  `EzicGrid` on 10 to 15; `EzicHoles` on 11 to 15; `PlaqueOne` from 11;
  `BizCard` four times on day 13, three on 14, two on 15, one on 16;
  `Arskickers` on 14 to 22; `KeyTranq` from 17; `SonDrawing` from 20;
  `PlaqueTwo` from 21; `Watch` on 22 and 23; `KeyKill` from 24; `Locket` on
  26 and 27; `FamilyPhoto` from 30; `VictimPhoto` on day 30.
- `Night/TokenIds`: `Impor` from day 5, `Antegria` from 6, `Obristan` from
  7, `Arstotzka` from 17, `Republia` from 24, `Kolechia` from 26,
  `UnitedFed` from 31.
- Upgrades: the platform's list in order, number `i` (from 0) once `d` is
  above `5 + 3i`.
- Family: wife, son, mother-in-law and uncle set to `alive=true`; from day
  22 `Night/HaveNiece` is 1 and the niece is alive; from day 29
  `Night/NumEscapePassports` is `2d - 56` held between 0 and 5, and
  `Night/HaveFamilyPassports` is 0.
- `Game/Day` is set to `d`.

This is a developer tool; the port does not need it unless the same jumps
are wanted for testing.

## Settings, statistics, the forced layout

`settings` and `stats` share one XML shape (`MapUtil.toXml`):

```
<members><entry key="musicVolume" val="1"/>...</members>
```

**Settings.** Nine values are written: `fullscreen`, `nudity`,
`musicVolume`, `soundVolume`, `easyMode`, `dateFormatIndex`, `endlessId`,
`endlessUnlocked`, `languageCode`. The vibration setting is not written.
A new `Settings` starts with both volumes 1.0, vibration on, the platform's
default language, and nudity on only on desktop; its constructor then loads
the `settings` entry if there is one, each value falling back to the
current one when missing. This is where the saved date format comes from
(`value-helpers.md`). `Settings.save` writes the entry only if the
settings' change counter differs from its value at the last load. Who
calls it is known since 2026-10-14 (`screens.md`, part 4, "Who writes the
settings file"): `Game.applySettings`, which `Game.update` runs on the
frame after any setter has changed a value. (That fits the real folder:
the file appeared when the user changed a volume, not at start-up.)

**Statistics.** `stats` is the all-time table: names to values, whole
numbers for the counters and texts for the two kinds of entry below
(until 2026-10-16 this said "names to whole numbers"). It
is read at start-up. A change starts a one-second countdown and the file is
written when it runs out. The rest of `AlltimeStats` (achievements,
leaderboards) was not read: out of scope. One part of it is local and was
read on 2026-10-16 (`screens.md`, part 7): the best endless score per
style and course is kept in this same table, under the name
`_Leaderboard:<style> <course>` (for example
`_Leaderboard:Perfection Course 2`), as a text `score,time`; seen in
passing, `awardAchievement` keeps the achievements won under
`_Achievements`, a list of ids. So the table is not only names to whole
numbers (the first sentence of this paragraph was written from the real
folder, whose statistics hold only whole numbers). Checked on 2026-10-16: the three
copies of `stats.sav` on this machine (`extracted/saverun`, `stashrun`,
`stash_sample`) hold only whole numbers under `Day`, `PlayTime`,
`NumStamps`, `NumApproved`, `NumProcessed` and `NumDenied` (`NumDenied`
only in `saverun`), and neither of the two names; no endless run was
played for them.

**Forced layout.** `platover.sav` holds `tablet` or `phone`, unencrypted,
and makes the game use that layout. It is written when a
`REQUEST_PLATFORM_CHANGE` request arrives ("Requests" below). One caller
was found, `SettingsMenu.platformChangeConfirm_onDone`. The settings
screen is told at creation whether the change is allowed, and the launch
code allows it only on Android or an iPad. What the screen does with
that, read on 2026-10-14 (`screens.md`, part 4): it shows a "Device" row
only if the change is allowed and the layout is not the desktop one. Who
reads the file: **no caller of the reader,
`Settings.getPlatformKindOverride`, was found anywhere in this build**
(same place, "Who reads `platover`").

## When the game saves and loads

From the code (part 2 read the rest of `Game.applyScreenChange`; of the
screens only the call sites named here were read):

- At start-up `play.Bootstrap` creates the store, the settings (which load
  themselves), the save manager, the statistics, and a `NORMAL` story state.
- **Load**: `Game.applyScreenChange`, transition `LOAD_TO_SCREEN`. The story
  state loads the given id, then a new story seed is drawn. Starting a new
  game is a load of `NEW` (`run-and-seeds.md`). Two callers were found,
  both in the load screen. `LoadScreen.loadButton_onClick`: when the
  clicked entry's header is the new one (`isNew`), it asks for that header
  and the screen `intro`; otherwise it shows a summary box, and the box's
  "continue" (`confirm_onClick`) asks for the save and the screen `news`.
- **Save**: `Game.applyScreenChange`, transition `ADVANCE_TO_NEXTDAY`:
  `Game/Day` goes up by one, **then** the story state is saved. This is the
  only story save in `Game`, and `Game` is the only caller of
  `StoryState.save` found in the decompiled files (the booth classes, the
  border, the screens, the test player). So a save is taken after a night,
  and holds the state at the start of the following day. One caller of the
  request was found: `NightScreen.onClickSleep`.
- **Delete**: `LoadScreen.confirm_onClick`, on the answer `delete`, calls
  the save manager's delete with the save's id. "Read the tree"
  (`SaveManager.getRoot`) is called by `LoadScreen.createLoadButtons`,
  each time the load screen makes its buttons; the load screen is
  described in `screens.md`, part 3 (read on 2026-10-14).
- **Closing the game in the middle of a day, on desktop, loses that day.**
  The story goes on from the save taken after the last night. The game
  does write a snapshot during the day (the stash, below), but the desktop
  build never reads it back.

# Part 2: moving between screens, and the stash

Studied on 2026-10-14. Read in full: from `Game`: `applyScreenChange`,
`applyTransition`, `queueScreenChange`, `boot`, `getDaySafe`,
`fadeToTitle`, `createStater` and its callbacks, `restoreFromStash`,
`stashSaveDay`, `stashSaveNight`, `stashSaveEnd`, `stashSave`; all of
`play.GameTransition`; the four stash functions of `SaveManager`;
`StoryState.restoreFromStash`; all 12 classes of `play.stash`; from `Day`:
`get_canStash`, `makeStash`, `restoreFromStash`,
`getFirstTravelerIsSecretPolice`; `makeStash` and `restoreFromStash` of
`DayScreen`, `Booth`, `BoothEngine`, `BoothEnv`, `Paper`, `DeskItem`,
`Border` and `BorderPan`; `restoreFromStash` of `NightScreen` and
`EndScreen`; `play.screen.UnstashOverlay`;
`Booth.applyMountedPaperIdsOrder`; the part of the test player that
exercises the stash.

Two things were read from the machine instructions instead: which booth
state the stash callback belongs to (the decompiler gives up on the
`Booth` constructor), and the start-up option that allows resuming (in
`HostUnity.CreateGame`). All 471 functions of `play.screen` were
decompiled and **searched** for callers; they were not read.

Part 2 was written from the code alone. The same day one test was run in
the real game ("The stash test in the running game" below): it confirmed
that the desktop game writes a day stash once the first traveler has
gone, starts at the title with the stash present and untouched, and
deletes it when another screen is asked for; and the stash file matched
the description of its content. Everything else in part 2 is from the
code only: the night and ending stashes, the blocker, restoring, the
screen changes other than these.

## Requests

Any part of the game asks for a change of screen, a save or a stash
through one shared object, `play.GameTransition`. It does nothing itself:
each of its functions builds a request and hands it to
`Game.applyTransition`. There are 19 kinds of request:

| Request | What `Game` does with it |
|---|---|
| `NONE` | Nothing |
| `FADE_TO_SCREEN(name, instant)` | Queues the screen `name` |
| `LOAD_TO_SCREEN(save, screen)` | Queues `screen`; the save is loaded when the screen is built |
| `FADE_TO_ENDLESS_DAY(endless id)` | Queues `day` |
| `FADE_TO_ENDLESS_RESULT(result)` | Queues `endless` |
| `FADE_TO_END(ending id)` | Queues `end` |
| `SKIP_TO_DAY(day)`, `SKIP_TO_TRAVELER(id, day)` | Queue `day` without a fade. The debug jumps (`comparing-with-the-game.md`) |
| `ADVANCE_TO_NEXTDAY` | Queues `news` |
| `FLASH_TO_TITLE(duration)` | Starts a screen flash; when it is over, the title is queued |
| `OPEN_EXTERNAL_LINK(address)` | Leaves full screen and opens the address. Ignored with the command-line word `expo` |
| `SET_PAUSE(yes or no)` | Game state `paused` or `on` |
| `MAKE_STASH_DAY` | Writes a day stash, if allowed (below) |
| `MAKE_STASH_END(ending id)` | Writes an ending stash |
| `STASH_RESTORE` | Restores from the stash; if that fails, goes to the title |
| `START_AUTO_SOAK` | Stops all sound and sets a flag for the test player |
| `REQUEST_PLATFORM_CHANGE(layout)` | If the layout differs from the current one: writes `platover` and queues the `wait` screen |
| `SHOW_RATING_SCREEN(function)` | Queues `rating` |
| `QUIT` | Asks the system to close the game |

## Queueing a screen (`Game.queueScreenChange`)

In this order:

1. **`news`**: if the day library has no day with the number in `Game/Day`,
   the game goes to the title instead and nothing else happens.
2. **`title`**, asked while the day screen shows an endless-mode day: the
   endless run is told to end (`Endless.end`) and nothing is queued here.
3. **The stash.** If the screen is `night`, a night stash is written. If it
   is `end`, a day stash is attempted. **For every other screen the stash
   is deleted.**
4. The game's own state goes to `off` (or `off-instant`), and the request
   is kept as the pending screen change.

`Game` has five states of its own (a small state machine,
`createStater`):

| State | What it does |
|---|---|
| `on` | Normal running. On entry the fade cover (`screenFlash`) fades out |
| `off` | On entry two flags of the current screen are cleared (4 and 16) and the fade cover fades in. After 1 second the pending screen change is applied and the state goes back to `on` |
| `off-instant` | The same with no fade and no wait |
| `flashing-to-title` | The same two flags are cleared, and the screen flash runs; when it is over, "title" becomes the pending change and the state is left (for which state: the decompiler dropped the argument) |
| `paused` | On entry: all sound paused, the pause screen created, the current screen hidden, the sound `button-drop`. Every frame it tells the clock to pause for one frame. On exit: sound resumed, pause screen removed, screen shown again, the sound `hover-up` |

What the two flags mean was read on 2026-10-14 (`screens.md`, part 1):
without 4 the screen and everything in it get no input, without 16 they
are not updated. They are still drawn.
Inferred from where they are cleared (here, and under the resume overlay
below): the screen is no longer updated and gets no input.

The fade is 0.125 s each way (half of 0.25). With the debug switch
`skipSlowStuff` it is 0.005 s and the 1-second wait is 0. These numbers
were read from the decompiler and the constants in the file; which
argument is the wait and which the fade was not checked in the
instructions.

`paused` is entered by `SET_PAUSE`, or in `Game.update` when key number 5
is pressed, the state is `on` and the current screen says it can be paused.
Key number 5 is Escape (looked up on 2026-10-14: `screens.md`, part 4,
which also describes the pause screen).

## Building the screen (`Game.applyScreenChange`)

1. All sound is stopped and the flash is cleared.
2. The current screen is removed.
3. Depending on the request that came with the screen change:

   | Request | Story state | The `Day` object |
   |---|---|---|
   | `LOAD_TO_SCREEN` | Loads the save; then a new story seed is drawn | Dropped |
   | `ADVANCE_TO_NEXTDAY` | `Game/Day` plus one, then saved | Dropped |
   | `FADE_TO_ENDLESS_DAY` | Replaced by a new `FORENDLESS` one | A new one for the course's day, with a new `Endless` object seeded from the endless seed generator |
   | `SKIP_TO_DAY` | Replaced by a new `SKIPTODAY` one; both log switches and `skipSlowStuff` are turned on | Dropped |
   | `SKIP_TO_TRAVELER` | The same; the day is looked up from the traveler id when none is given | A new one, told to make that traveler |
   | any other | Untouched | Kept |

4. The screen is built from its name: `intro`, `news`, `settings`, `end`,
   `endless`, `wait`, `title`, `day`, `load`, `night`, `credit`, `rating`.
   Any other name raises the error "Screen not found". `title` also
   drops the `Day` object. `news`, `day` and `night` are given the `Day`
   object through `getDaySafe`: the existing one, or, if there is none, a
   new one for the day number in `Game/Day`.
5. The screen's music is started and the screen is shown.

What follows from this:

- **In normal play there is one `Day` object per played day.** It is made
  when the news screen is built and the day and night screens reuse it. It
  is dropped by a load, by going on to the next day, by the title, and it
  is built again by a stash restore. This answers an old open question;
  the evidence is the code only.
- **The news screen is built at the start of every day and after a load**
  (a load asks for the screen `news`). A new game goes to `intro` first.

## The stash

The stash is one store entry, `stash` (the file `stash.sav`). It holds
enough to put the player back at the point reached: the story facts, the
day's counters, and either the desk as it was with the booth empty, or
"at the night screen", or "at this ending". There is never more than one.

### When it is written

Nothing in the writing path looks at the platform, so by the code this
happens on desktop too. The first row was seen on desktop in the test;
the other three were not tried.

| Moment | What is written |
|---|---|
| The booth enters its `empty` state. The callback is the first one registered on that state, for "on entry" (read from the instructions). Inferred, the booth's states not being fully read: once after the day's opening and again each time a traveler has gone | A day stash, if allowed (next list) |
| The screen `night` is queued | A night stash (only if a `Day` object exists) |
| The screen `end` is queued | A day stash, if allowed |
| The ending screen is built (end of the `EndScreen` constructor) | An ending stash |

A day stash is allowed only when all of these hold:

- The current screen is the day screen.
- The day is not an endless-mode day and its number is 1 to 31.
- At least one traveler has been made that day. On three kinds of day it
  takes two: when the day's first traveler id starts with `SECRET_POLICE`,
  when the friendly guard is in his `CHAT` state, or when the day has the
  boss (`days-csv-format.md` has `hasBoss` and `friendlyGuard`).
- The booth engine's stash blocker is at zero. The blocker is a counter,
  `preventStashCount`. It is set when the leaving direction is decided
  (`BoothEngine.getLeaveDir`): to 10000 when a traveler with a bomb leaves
  to the right or a poisoned traveler leaves either way, which in effect
  means no more day stashes that day; and to 2 when the traveler's own
  special exit
  is used (a `customLeaveDir` starting `left-` or `right-` that matches the
  stamp), which skips the stash at the next empty booth only. It goes down
  by one each time the booth becomes empty.

So a day stash is always a picture of an **empty booth between two
travelers**. A traveler in the booth is never stashed.

### When it is deleted

Whenever any screen other than `night` or `end` is queued: the news screen
of the next day, the day screen, the title, the load and settings screens
and so on. Restoring from a stash does not delete it. (Corrected
2026-10-14: part 1 guessed that "a stash is deleted once used".) Seen in
the test for one case: the file was still there at the title screen and
gone after the click on "Story".

Put together, in a story game the stash exists from the moment the first
traveler has gone (it is rewritten at each empty booth), through the
night, until the player goes to sleep or leaves for the title.

### When it is read

- **At start-up** (`Game.boot`), only when the start-up option
  `restoreFromStashIfPossible` is on. `HostUnity.CreateGame` sets that
  option to "the layout is not desktop" (checked in the instructions:
  the value passed is the result of comparing the platform kind with
  `DESKTOP`). The test player turns it off as well. So **the desktop game
  always starts at the title and never reads the stash**; the phone and
  tablet layouts resume from it. The desktop half was seen in the test:
  with a valid day stash in the folder the game opened on the title
  screen, with no resume button, and left the file as it was.
- **On a `STASH_RESTORE` request.** The only caller found is the test
  player. Searched: `Game`, the 1,433 booth-class functions, the border,
  all of `play.screen`, the save classes, the test player. Not searched:
  `play.ui` and `app`. The developer-menu hook `Game.setupDevMenu` is an
  empty function in this build.

The test player's part: with the word `stash` in `auto.plan` it watches a
counter that goes up with every stash written. When it changes, it drops
what it was doing, asks for a restore, waits for the button `stash-resume`
and clicks it. That is the developer's way of testing the feature, and it
would exercise it on desktop. Not run here.

### When a stash is refused

A stash is valid when its stash version is 7, its game version text equals
the running game's, it has story facts, and it has what its kind needs (a
day stash: the day and the day screen; a night stash: the day; an ending
stash: the ending id). An invalid stash is not written. Reading one that
is invalid raises an error (who handles it was not followed). A stash made
under another layout (desktop, tablet, phone) is not restored, and neither
is a day stash whose day number is not 1 to 31. When a restore fails the
game goes to the title.

### What it holds

| Part | Content |
|---|---|
| `StashedGame` | Stash version, game version, the kind (`DAY`, `NIGHT`, `END`), the layout, **a copy of all story facts**, the day, the day screen, the ending id |
| `StashedDay` | The day number, a copy of the day's own facts, and the day's counters: detained, travelers processed with and without pay, travelers made, bribe money, the attack result, "had a bomber", "had a poisoning"; and four lists: token ids, night event ids, citations, confiscated papers |
| `StashedDayScreen` | The booth and the border |
| `StashedBooth` | The engine, one entry per desk paper, shutter open or closed, criminal poster pinned or not, the booth clock's time |
| `StashedBoothEngine` | The number of travelers so far, and the booth environment |
| `StashedBoothEnv` | The facts of every document that stays for the day or the game (`facts-xml-format.md`, `stay`), except `Transcript`; and the ids of the day-staying papers the booth has at that moment |
| `StashedBoothPaperState` | For one desk paper: document id, position in whole pixels, open page, the tilt of its closed picture, its desk state and where it lies (`OUTER`, `INNER`, `FILER`, `MOUNT`). Only papers whose desk state is `REVEALING`, `NORMAL` or `RETURNINGTODOCK` are included |
| `StashedBorder` | One number, the view's pan position (`border-scene.md`, `border-view.md`) |

**Not in a stash:** any random generator's state or seed, the figures of
the border scene and the waiting line, speech, and a traveler (there is
none in an empty booth).

The entry's text is produced by Haxe's general serializer
(`haxe.Serializer`, a standard text encoding of objects), then stored like
every other entry: `PPSAVE1` in front, encrypted. The serializer's code
was not studied; the port does not need to read the original's stash. Its
text was read from the real stash instead, with a small reader written
from the format's public description (`scripts/reference/hxserial.py`).
What that stash shows: each object is written with its class name and
its field names, enum values are written by name, a text that occurs
again is written as a number pointing back to its first use, and the
whole 9,040-character text is one `StashedGame` object with nothing after
it.

### Restoring (`Game.restoreFromStash`)

1. No stash, or a stash from another layout: stop, "failed".
2. The story facts are replaced by a copy of the stash's, and `Game/Device`
   is set again.
3. If the stash has a day, **a new `Day` object is built** for that day
   number, as at the start of a day, and then its facts, counters and lists
   are overwritten from the stash. (Inferred, not followed: building it
   draws from the random generators again, for example for the three
   criminal faces, and nothing puts the generators back where they were.
   So the travelers after a restore need not be the ones that would have
   come.)
4. The screen `day`, `night` or `end` is built at once, without a fade.
5. The screen restores itself:
   - **Day**: the booth, then the border, then a running tutorial is
     stopped.
   - **Night**: the budget's reveal animation is skipped.
   - **Ending**: the opening flip is finished at once. (Since
     `screens.md` part 5: the ending screen is built by its normal
     constructor, so the ending starts again from its first page, and
     the achievement, the `EndBits` bit and a new ending stash are
     written again.)
   - Any other screen answers "failed".
6. A resume overlay (`UnstashOverlay`) is put over the screen. Every frame
   it tells the clock to pause for one frame, so the game stands still.
   After 10 frames it darkens the screen, shows an icon and a button with
   the text `menu_resume`, and clears the screen's flags 4 and 16 (the
   same two the fade-out clears: no input and no updates, `screens.md`,
   part 1). A click on the button sets them again
   and removes the overlay.

The booth's part (`Booth.restoreFromStash`):

- The engine gets its traveler count back. The environment adds each
  stashed day paper to the desk again and replaces its facts with the
  stash's.
- Each stashed paper entry is matched to the desk paper with the same
  document id. That paper is turned to the stashed page (which draws the
  page again, with its random draws: `desk-drawing-draws.md`), its closed
  picture is made again at the stashed tilt, and it is put back: a
  `NORMAL` paper goes to its stashed position and placement; a `REVEALING`
  or `RETURNINGTODOCK` one starts its reveal animation again.
- The shutter is set as it was. The booth clock is set to the stashed time
  minus 2.0 (`StashedBooth.kGraceTime` is 2; that the code's 2.0 is that
  constant is inferred). The traveler counter on the console is set. The
  criminal poster is shown if it was pinned.
- `applyMountedPaperIdsOrder` goes through the ids in the story fact
  `Game/MountedPapers` (separated by `;`) and makes one call on each paper
  that is mounted. What the call does was not looked up; inferred from the
  function's name: it puts the mounted papers back in their order.
- The booth's state is set to `empty`.

The border's part is in `border-scene.md` ("Saving and restoring"): the
scene is rebuilt in its plain waiting form and only the pan comes back.

### The stash and the real folder

The user's three quits (part 1, "Compared with a real save") each left no
`stash.sav`. By the code that is what should happen: each quit came early
in a day, and a day stash is first written when the first traveler of the
day has gone. The `names` file shows no name taken on day 4 in either of
the last two quits, so no traveler had even been made. For the first quit,
about 20 seconds into day 3, the counts do not rule out one traveler having
been called in; none had been processed.

That agrees with the code but is not a test of it. The test is next.

It also settles a question from part 1: the second sitting can only have
continued by **loading the save**, because the desktop game does not read
a stash at start-up.

### The stash test in the running game (2026-10-14)

The user ran the desktop game twice with `savedir` pointing at a new empty
folder, `extracted/stashrun`. The folder was looked at three times.

1. **First launch.** A new story; day 1 was played until the first
   traveler had been dealt with and had walked away; then the window was
   closed with Alt+F4 (not through the menu).
   **Seen:** `stash.sav` in the folder, last written at 10:49:34, with
   18,096 characters of hex text. No `headers` and no save, as expected
   before the first night.
2. **Second launch**, stopped at the first screen.
   **Seen** by the user: the title screen with "story" and "endless" and
   no resume button. In the folder: `stash.sav` still there, same time.
3. **A click on "Story".**
   **Seen:** `stash.sav` gone. Nothing else in the folder changed. The
   user saw only a new-game entry on the screen that opened, nothing to
   continue: the day played in the first launch was lost, as the code
   says for a quit in the middle of a day (here there was no save yet,
   so the whole story).

All three are what the code reading said. A copy of the folder as it was
after step 1 is kept in `extracted/stash_sample` (gitignored).

`scripts/checks/stash_check.py` reads that stash and compares it with this
doc. Its result: `0 problems`.

- The whole text is one `StashedGame`: kind `DAY`, layout `DESKTOP`, stash
  version 7, game version `1.4.11.124`.
- Every object has exactly the fields its class declares in the code (the
  ones summarised under "What it holds"), for all 8 stash classes.
- 7 story facts: `Game/Device`, `Game/StayingPapers`, and five statistics
  (one traveler processed, one approved, play time 56 s).
- The day: number 1, one traveler made, one processed with pay, three day
  facts (`Day/Id`, `Day/Rules`, `Day/Features`), one night event id.
- The booth: clock 46.717, shutter open, poster not pinned, traveler count
  1. Three desk papers, `Transcript`, `Rules` and `Bulletin`, all `NORMAL`,
  all at whole-pixel positions.
- The booth's facts: 51 of `Rules` and 20 of `Bulletin`, none of
  `Transcript`. The day papers are those same three documents, and
  `Facts.xml` gives all three `stay="day"`.
- The border: pan 0.
- No object of a random-generator class anywhere in it.

How strong this is: one stash, of one kind (`DAY`), from day 1 of a new
story, with one traveler processed. It confirms the writing moment, the
content of a day stash, that desktop start-up ignores the stash, one
deletion, and that the unfinished day is not offered again. **Not
tested:** a night or an ending stash; the blocker after a
bomb, poison or a special exit; the days that need two travelers; a
restore (it cannot happen in normal desktop play); the stash being
rewritten at each later empty booth (only one traveler was processed
here).

# Both parts: the real folder, notes for the port, open points

## Compared with a real save

On 2026-10-14 the user played a new story game by hand, from a normal
launch with `savedir extracted\saverun`, through three days and nights
into day 4, changed a volume setting along the way, and quit during day 4.
The folder then held `headers`, three `save_...` files, `settings`,
`stats` and `names`. No `stash` and no `platover`.

The user played it in **two sittings**: quit once, started the game again
and continued the story. Where the break was is inferred from the folder,
not remembered: the play-time statistic grows by 366 s between the first
two saves while the clock moved 370 s, but by 428 s between the last two
while the clock moved 521 s; the settings file (changed "the second time")
was written 2 minutes 16 seconds after the day-3 save; and the all-time
play time is 41 s more than the last save's. So the first sitting ended
about 20 seconds into day 3, and the second went on with day 3 and ended
about 20 seconds into day 4. The second sitting continued by **loading
the save**, so loading was exercised here too. (Part 1 left this open: a
stash might have been used instead. Part 2 answered it from the code: the
desktop game never reads a stash at start-up. Part 1 also said "a stash is
deleted once used"; that was a guess and is wrong, see "When it is
deleted".)

`scripts/checks/save_check.py` on that folder:

- All 7 files decrypt to the `PPSAVE1` prefix, and encrypting each
  decrypted value again gives the file's exact text, 7 of 7. That tests the
  cipher in both directions, the padding and the upper-case hex.
- `headers`: 4 lines (the root and 3 saves), each save one level deeper
  than the one before; every `parentId` equals the id of the line it hangs
  under; all ids are 32 characters of `A`-`Z`, `0`-`9`.
- 3 headers, 3 save files, one for each.
- In 3 of 3 saves the header's day, money and family equal the save's
  `Game/Day`, `Night/Savings` and `Night/FamilyAlive` (2/30/4, 3/40/4,
  4/60/3). The decompiler had dropped these three values where the header
  is written; the three saves differ in all three, so the order is not in
  doubt.
- The "parent" rule holds in 3 of 3: the first save has no `Save/ParentId`
  or `Save/ParentDay` fact at all; the second holds the first's id and day
  2; the third holds the second's id and day 3.
- `settings` has 9 entries, exactly the nine names above, and no vibration.
  `stats` has 6 whole numbers.
- `names` is two lines of `seed:position:reshuffles`, and the second seed
  is the first plus one (`traveler-build.md`).

What a real save holds (the day-3 save, 24 facts): `Game/Day`,
`Game/Device`, `Game/StayingPapers`, `Game/Brothel` (set by a traveler
script), six statistics (`Game/Stat/Day`, `PlayTime`, `NumProcessed`,
`NumApproved`, `NumDenied`, `NumStamps`), `Save/ParentId`,
`Save/ParentDay`, and the night's facts (`Night/Savings`, `Profit`,
`Flags`, `Calendar`, `TokenIds`, `AttackResult`, `NumEscapePassports`,
`FamilyAlive`, and one per family member). No seed and no random-generator
state, as the code said.

### The replay: a load and a branch

Later the same day the user started the game a third time, loaded the
**day-3** save (not the newest one), played day 3 again, bought everything
at night, and quit about a minute and a half into day 4. The folder then
held a fourth save, and both checks were run again (`0 problems`, 8 of 8
files reproduced):

- **A branch.** `headers` now has two day-4 saves on the same level under
  the day-3 save, the older one first, as the sort by time says. (Which
  one carries the `latest` mark is not in the file; it is worked out on
  reading.)
- **Loading sets the parent.** The new save's `parentId` is the day-3 save,
  and its file holds `Save/ParentId` = that id and `Save/ParentDay` = 3.
  The day-3 file itself holds the day-2 save's id and day 2, so had loading
  not overwritten the two facts, the new save would hang under day 2. This
  is real evidence for the load rule; the second sitting was not.
- **Loading replaces the facts.** The new save's `Game/Stat/PlayTime` is
  1328: the day-3 save's 905 plus the 423 seconds of the replay. The
  all-time statistic kept counting from where it was (1374 to 1873).
- **The other day-4 save was not touched**: same file time as before.
- Again no `stash` after quitting in the middle of a day (expected by the
  code: "The stash and the real folder").

How strong this is: the format is confirmed for one folder from one story:
four saves, one branch, three launches, two loads (one seen in the save's
parent link, one known from the code). **Not exercised**: deleting, a save
whose day is not later than its parent's, an orphan, the `platover` entry,
text with characters above 127. (The `stash` entry was exercised later
the same day in a separate folder: "The stash test in the running game".)

Three side results from the same folder:

- **The night rules match.** `scripts/checks/save_night_check.py` replays
  the night before each save with the model in
  `scripts/reference/nights.py`, starting from the parent save's facts and
  trying every number of paid travelers and every choice of food, heat and
  medicine. For each of the four saves exactly one possibility reproduces
  every saved night fact (24, 56, 288 and 352 tried): 4, 6 and 8 travelers
  paid with nothing bought, and for the replay 10 paid with food, heat and
  three medicines bought. Details in `night.md`. For the first night 3 the
  user's memory disagrees with the save (the user remembers buying
  everything then too); see `night.md`.
- **The last quit, about 20 seconds into day 4 on desktop, left no
  `stash`.** Part 2 explains it: a day stash is first written when the
  day's first traveler has gone, and none had. So this is not evidence
  that desktop writes no stash; by the code it does.
- **`names` shows 12 + 8 = 20 names taken, over both sittings.** The second
  launch therefore continued the saved name position, as the code says: had
  it started afresh, the file would count only the second sitting's names
  (day 3 had 8 travelers processed). 19 travelers were processed in all;
  which traveler took the 20th name is not known. (Corrected the same day:
  this first said the 20th was taken on day 4. The file was last written at
  08:02:05, before the day-4 save at 08:03:09, so it was not.) After the
  replay the file shows 18 + 12 = 30: ten more names for the ten travelers
  processed in it, and again none on day 4. That is the cleaner count: one
  name per traveler, and the position carried into a third launch.

## Notes for the port

- A save is the fact list, the day's number inside it, and nothing else.
  The port needs the same: save the facts after the night, with the day
  already advanced.
- The port's own save files do not have to be readable by the original, so
  the cipher, the hex text and the fact order need not be copied. What must
  be kept is the meaning: the tree of saves with parent links, "continuing
  from a save hangs the next save under it", and "deleting a save deletes
  what was continued from it".
- The header's day, money and family are copies of three facts, for the
  load screen. They are not a second source of truth.
- The name order's position is stored outside the saves and is shared by
  all of them (`traveler-build.md`).
- Loading draws a new story seed, so replaying a day from a save gives
  different random travelers (`run-and-seeds.md`).
- **The stash can be left out of a desktop port.** The desktop original
  writes it but never reads it in normal play, so the behaviour to match
  is: closing the game during a day or a night loses that day, and the
  story continues from the save taken after the previous night.
- If a resume in the middle of a day is wanted later (a browser tab is
  closed more easily than a game), the original's design is the model:
  take the snapshot only when the booth is empty, and keep facts, counters
  and the desk, not the random generators.
- Screen changes are a small fixed set of requests handled in one place,
  with a fade out, the change, and a fade in. The save happens inside the
  change to the next day's news screen, not in the night screen.

## Reference script and checks

```
python -I scripts/reference/savefile.py extracted/saverun dumps/il2cppdumper/stringliteral.json
python -I scripts/reference/savefile.py extracted/saverun dumps/il2cppdumper/stringliteral.json --dump headers
python -I scripts/checks/save_check.py scripts/reference extracted/saverun dumps/il2cppdumper/stringliteral.json
python -I scripts/checks/save_night_check.py scripts/reference extracted/art/assets/data extracted/saverun dumps/il2cppdumper/stringliteral.json
python -I scripts/checks/stash_check.py scripts/reference extracted/stash_sample dumps/il2cppdumper/stringliteral.json extracted/art/assets/data
```

The first prints every entry in plain text, the second one entry's whole
text. `savefile.py` can also encrypt (`store_set`), which the check uses.
The last one reads a real stash with `scripts/reference/hxserial.py` and
compares it with part 2. The save folders are gitignored: they are the
user's own play data.

## Not studied

- (Done in part 2: the rest of `Game.applyScreenChange` and the stash.)
- Of the stash, the running game has shown one day stash being written,
  the start at the title with it present, and its deletion ("The stash
  test in the running game"). Not seen: a night or ending stash, the
  blocker, a restore. The serializer's code was not studied; its text was
  read from the one real stash.
- Who handles the error raised by an invalid stash at start-up (phone and
  tablet only).
- Whether anything in `play.ui` or `app` asks for a stash restore (not
  searched).
- (Answered on 2026-10-14 in `screens.md`, part 1: flag 4 lets a screen
  and its parts get input, flag 16 lets them be updated.)
- The booth's own states beyond `empty` being where the day stash is
  taken. (Answered on 2026-10-14 in `screens.md`, part 4: key number 5 is
  Escape, and the pause screen is described there.)
- (Studied since, on 2026-10-14, in `screens.md`, part 3: the load screen,
  who reads the tree, its deleting mode, the 5-track limit. And in part
  4: the settings are written by `Game.applySettings`, run by
  `Game.update` on the frame after any setting changes, and no other
  caller of `Settings.save` was found in the decompiled files; no code
  that reads `platover` was found in the build.)
- (Answered in part 2: nothing saves the story outside
  `ADVANCE_TO_NEXTDAY`, in the files decompiled so far, which now include
  the booth classes, the border, the screens and the test player. Calls
  through an object were searched by the function's slot name, as
  `ghidra-workflow.md` advises.)
- When "the day is not later than the parent's day" applies in play.
- Who sets `Game/Stat/Day`. In the real folder the all-time `Day` is 4
  while the last save's `Game/Stat/Day` is 3.
- `AlltimeStats` beyond its file: out of scope (online service). Its
  local endless best scores are read since 2026-10-16 (`screens.md`,
  part 7).
- The order of facts in a save was not compared with `haxemap.py`.
- Two arguments the decompiler dropped were not checked in the machine
  instructions: the id passed to `StoryState.load` in `LOAD_TO_SCREEN`, and
  the manager passed to `StoryState.save` in `ADVANCE_TO_NEXTDAY`. Both are
  what the functions' signatures require.
