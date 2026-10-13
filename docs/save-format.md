# Saves: where they live and what is in them

Studied on 2026-10-14 (saves, part 1). Part 2, not done yet, is the rest of
`Game.applyScreenChange` and the "stash" (the snapshot the game takes to
resume in the middle of a day).

Functions read in full: `play.EncryptedStore` (all), `app.XXTea`
(`encryptString`, `decryptString`, `btea_encode`, `btea_decode`,
`toKeyArray`), `HostUnity.UnityPlatformDisk` (all six),
`play.save.SaveHeader`, `SaveNode` and `SaveManager` (all), `play.StoryState`
(all), `data.FactSet.toXmlDoc`, `fromXmlDoc`, `setValueStringArray` and the
plain setters, the `data.FactValue` constructor, `app.MapUtil.toXml` and
`fromXml`, and from `play.Settings`: the constructor, `load`, `save`,
`toString`, `setFromString`, the two platform-override functions. From
`play.AlltimeStats` only `load`, `save`, `queSave` and `update` were read:
the rest of that class talks to the platform's achievements and leaderboards
service, which is out of scope (online). Six number constants were read from
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
| `stash` | `SaveManager` | The suspend snapshot (part 2) |
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
settings' change counter differs from its value at the last load; who calls
it was not followed. (In the real folder the file appeared when the user
changed a volume, not at start-up.)

**Statistics.** `stats` is the all-time table: names to whole numbers. It
is read at start-up. A change starts a one-second countdown and the file is
written when it runs out. The rest of `AlltimeStats` (achievements,
leaderboards) was not read: out of scope.

**Forced layout.** `platover.sav` holds `tablet` or `phone`, unencrypted,
and makes the game use that layout. Who reads and writes it was not
followed.

## When the game saves and loads

From the code read so far (the callers found in the files already
decompiled; the title and load screens are not decompiled yet):

- At start-up `play.Bootstrap` creates the store, the settings (which load
  themselves), the save manager, the statistics, and a `NORMAL` story state.
- **Load**: `Game.applyScreenChange`, transition `LOAD_TO_SCREEN`. The story
  state loads the given id, then a new story seed is drawn. Starting a new
  game is a load of `NEW` (`run-and-seeds.md`).
- **Save**: `Game.applyScreenChange`, transition `ADVANCE_TO_NEXTDAY`:
  `Game/Day` goes up by one, **then** the story state is saved. This is the
  only story save found. So a save is taken after a night, and holds the
  state at the start of the following day.
- Delete and "read the tree" are not called from anything decompiled so
  far; inferred: the load screen (not read).

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
about 20 seconds into day 4. By the code read so far, continuing a story
loads the newest save, so **loading was probably exercised once**. Not
certain: if the first quit left a stash, the second sitting may have
resumed from that instead, and a stash is deleted once used. Part 2 will
say whether desktop does that.

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
- Again no `stash` after quitting in the middle of a day.

How strong this is: the format is confirmed for one folder from one story:
four saves, one branch, three launches, one certain load. **Not
exercised**: deleting, a save whose day is not later than its parent's, an
orphan, the `stash` and `platover` entries, text with characters above 127.

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
  `stash`.** One observation. The first quit says nothing either way: a
  stash written then could have been used and deleted by the second
  sitting. How the stash is triggered is part 2.
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

## Reference script and checks

```
python -I scripts/reference/savefile.py extracted/saverun dumps/il2cppdumper/stringliteral.json
python -I scripts/reference/savefile.py extracted/saverun dumps/il2cppdumper/stringliteral.json --dump headers
python -I scripts/checks/save_check.py scripts/reference extracted/saverun dumps/il2cppdumper/stringliteral.json
python -I scripts/checks/save_night_check.py scripts/reference extracted/art/assets/data extracted/saverun dumps/il2cppdumper/stringliteral.json
```

The first prints every entry in plain text, the second one entry's whole
text. `savefile.py` can also encrypt (`store_set`), which the check uses.
The save folder is gitignored: it is the user's own play data.

## Not studied

- Part 2: the rest of `Game.applyScreenChange`, and the stash
  (`play.stash.*`, `Game.stashSave`, `restoreFromStash`, the `stash` entry,
  which is written with Haxe's general serializer).
- Who calls delete and "read the tree", who asks for the settings to be
  written, who reads and writes `platover`: the screens, not decompiled.
- Whether anything saves the story outside `ADVANCE_TO_NEXTDAY`. Only the
  files decompiled so far were searched, and calls through an object do not
  show up in a reference search (`ghidra-workflow.md`).
- When "the day is not later than the parent's day" applies in play.
- Who sets `Game/Stat/Day`. In the real folder the all-time `Day` is 4
  while the last save's `Game/Stat/Day` is 3.
- `AlltimeStats` beyond its file: out of scope (online service).
- The order of facts in a save was not compared with `haxemap.py`.
- Two arguments the decompiler dropped were not checked in the machine
  instructions: the id passed to `StoryState.load` in `LOAD_TO_SCREEN`, and
  the manager passed to `StoryState.save` in `ADVANCE_TO_NEXTDAY`. Both are
  what the functions' signatures require.
