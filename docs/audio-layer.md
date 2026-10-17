# The game-side audio layer (`app.aud`)

Studied on 2026-10-17 (step 6b). This is the game's own sound code
between the screens and the Unity host: which sound starts, how a
sound's volume fades, how a song changes, rooms, pausing, stopping, and
the music's beat that the title screen follows. The Unity host that
actually plays the clips (`HostUnity.UnityPlatformAudio`, at most 32 at
once, the volume settings in decibels) is in `audio.md`; `Sounds.xml`,
which lists the effects, is in `sounds-xml-format.md`.

Sources: code reading of all of `app.aud` in
`decompiled/all/app_aud.clean.c` (`Speaker`, `SpeakerSound`, `Music`,
`MusicBeat`, `PlayState`, `AudioCategory`; its 26 field-access plumbing
functions only skimmed), `app.Num.lerpScale`, `app.Clock`, and every
caller found by a search of `decompiled/all/` (below). Two Ghidra runs
for what the decompiler showed unclearly (`decompiled/aud_run1.txt`,
`aud_run2.txt`), the saved instructions of the `Booth` constructor
(`decompiled/booth_ctor_asm.txt`), six constants read from the DLL. One
measurement of the extracted songs (`scripts/checks/music_beat_check.py`).
**Nothing here was listened to in the game.**

Terms used below:

- **Effect**: any sound from `Sounds.xml`. **Song**: one of the three
  music recordings (`Theme`, `Death`, `Victory`). The code calls these
  two kinds **categories** (`Effect` = 0, `Music` = 1).
- **One-shot**: an effect that does not loop.
- **Play id**: the number the speaker gives each sound it starts (1, 2,
  3... for the whole run; 0 means "nothing started").
- **Volume** here is the game's own multiplier for one sound, 0 to 1, on
  top of the sound's `vol` from `Sounds.xml` and the player's volume
  setting (both in `audio.md`).
- **Fade**: the volume moving gradually to a new value.
- **Beat, bar, bpm**: a beat is one count of the music's pulse; a bar is
  4 beats here; bpm is beats per minute (the tempo).

## Who owns what

The game start-up object (`play.Bootstrap`, its constructor) makes **one
`Speaker`** and **one `Music`** for the whole run; every screen and the
booth use those. The speaker has its own clock (`app.Clock`) with
`maxDeltaTime` 100,000 s, so **sound time is real time with no cap**:
after a stall a fade jumps ahead, while the game's clock moves at most
0.1 s a frame (`border-view.md`). Like every clock it would follow the
test player's fixed frame time (`fixedFrameDelta`), and its first step is
0.

Each frame, `Game.update` steps the game, updates the screens (the
booth's update is part of that), then `Music.update`, the statistics,
the input, and **last `Speaker.update`** (read in `Game.update`).

## Playing an effect (`Speaker.play(id)`)

1. The id is looked up in `Sounds.xml`'s table. Unknown: nothing plays,
   the result is 0 (and a debug-log line, "Sound not found").
2. **Room**: if the sound has a `room` and the speaker's room is set and
   different, nothing plays (result 0).
3. **The ignore switch**: if the sound does not loop and the speaker is
   ignoring one-shots this frame (below), nothing plays (result 0).
4. Otherwise: the next play id; **only now is the recording chosen**
   (`SoundDef.get_filename`, the random or shuffled pick of
   `sounds-xml-format.md`), so a sound that is skipped does not move its
   recording order on; the host is told `start(id, Effect, file, loop,
   vol)` with the sound's `vol` as its volume; and the sound is added to
   the speaker's list with volume scale `vol` and fade time `fade` (from
   `Sounds.xml`, 3 s when absent).

## Playing a song (`Speaker.music(song)`)

The next play id; `start(id, Music, "<song>.ogg", loop = true, volume =
1)`; added to the list with volume scale 1 and **fade time 4 s**. Rooms
and the ignore switch do not apply. Only `Music` calls it.

## One sound's volume (`SpeakerSound`)

A sound starts with volume 1 and state `PLAYING`.

- **`setVolume(v, fade)`**: with `fade`, a straight-line fade from the
  current volume to `v` over the sound's fade time, starting at the
  sound's current age. Without `fade`, the volume becomes `v` at once.
- **`update(dt)`** (from `Speaker.update`, every frame): age += dt. While
  the volume differs from its target it is recomputed on the straight
  line (held at the line's ends), **jumps to the target once less than
  0.01 away**, and the host is told the new value: `setVolume(id,
  scale x volume)`.
- So **an instant volume change is never sent to the host**: it sets
  the volume and the target together, and `update` talks to the host
  only while they differ. (Checked in the instructions,
  `aud_run2.txt`: neither path of `setVolume` calls the host.) The
  booth's ambient loops run into this (below).
- **`stop(fade)`**: with `fade`, state `STOPPING` and a fade to 0; the
  first update at which the volume is 0.001 or less stops it at the
  host. Without, it is stopped at the host at once.

`Speaker.update` also asks the host for each sound's position in
seconds; a sound the host no longer has (position −1) is dropped from
the list, but **not on its first update**. So a sound the host could not
start (an unknown file, or a 33rd sound, `audio.md`) still counts as
playing for one update.

A song's fade-out (4 s, from volume 1): at 60 frames a second the volume
is 1 − k/240 after k frames, jumps to 0 at frame 238 (3.97 s), and the
host stops it in that frame.

## Stopping, pausing and the ignore switch: who calls what

Found by a search of `decompiled/all/` for each method by name (the
game calls them through the object's method table, which the decompile
shows by name), plus the `Booth` constructor's instructions. Calls
written as raw table offsets were looked for near uses of the speaker
and none was found; a function that is not fully decompiled could still
hide one.

| Call | Who | What it does |
|---|---|---|
| `stopAll(fade = true)`, defaults: effects only | `Game.applyScreenChange`, step 1 of every screen change (`save-format.md`, part 2; the second argument is empty in the instructions, `aud_run1.txt`, so the default holds) | **Every effect fades out over its own fade time** (3 s for most, 1 s for the two ambient loops). **Songs are not touched**: step 5's `Music.play` decides |
| `stopAll(false, false)` | `Game.applyTransition`, `START_AUTO_SOAK` (the test player) and `REQUEST_PLATFORM_CHANGE` (phones and tablets) | Everything, songs too, stopped at once |
| `ignoreNonLoopingPlaysThisFrame` | `Game.applyScreenChange`, after the old screen is removed and before the new one is built | **One-shots asked for in the rest of that frame are dropped**, so the new screen's constructor and its first update are silent unless they loop. `Speaker.update`, last in the frame, turns the switch off |
| `pauseAll` / `resumeAll` | The game's `paused` state, on entry and exit (`save-format.md`, part 2) | **Pauses the effects category only: the song keeps playing under the pause screen.** The pause sound `button-drop` is started after the pause, so it is heard. Fades go on during the pause (the speaker's clock is not the one the pause holds) |
| `setVolume(id, v)` (fade by default) | `Booth.update` only | The ambient loops (below) |
| `room` | `Booth.update` only (the field is written directly; `setRoom` has no caller) | Below |
| `stop(id)` | Only `Music` | |
| `vibrate` | The stamp and the settings' vibration button | Phones only: the desktop host does not provide vibration (the base `canVibrate` answers false) |

## The booth's ambient loops and the room

The `Booth` constructor (in its instructions) starts `border-ambient`
(`vol` 0.5) and `booth-ambient` (`vol` 0.4), both looping with a 1 s
fade, and sets both to volume 0 **at once**.

Every frame, `Booth.update` looks at the booth's own state. In the
states `off`, `intro`, `empty`, `busy-with-border`, `waiting-to-detain`
and `detaining` (by their names: no traveler being dealt with in the
booth; the booth's state machine is not fully read, `border-scene.md`)
it asks for `border-ambient` at 1, `booth-ambient` at 0, and sets **no
room**; in any other state (with no state at all too) the opposite, and
the room `booth`.

- Both calls fade, and they are made **every frame**, so each frame
  starts a new 1-second fade from the current volume. The result is not
  a straight line but a smooth approach: each frame closes the fraction
  dt / 1 s of the remaining gap. At 60 frames a second a loop is at 0.64
  after 1 s and reaches its target (the 0.01 jump) after 275 frames,
  4.58 s.
- **By the code, not heard: one ambient plays at its full level at first.**
  The constructor's instant 0 never reaches the host, which keeps the
  sound at the volume it started with (0.5 or 0.4). The loop whose first
  target is 1 starts fading at once and is fine (its host volume drops
  to nearly 0 in the first frame and then rises). The loop whose first
  target is 0 is already "at" 0 as far as the game knows, so the host is
  never told, and **it keeps playing at its full level until its target
  first becomes 1**; from then on it behaves. Inferred from the state
  names (the first state of a day was not read): at the start of a day
  the booth is in `off`, `intro` or `empty`, so `booth-ambient` would be
  heard at full level together with `border-ambient` until the first
  traveler comes in.
- **Room**: the only sound with a room is `car-driveby` (`border`). So
  **car sounds are dropped while a traveler is in the booth** (room
  `booth`) and play when the room is not set. The room is never set
  back after the day; no other screen plays `car-driveby`.

## Songs (`Music`)

`Game.applyScreenChange`, step 5, calls `Music.play` with the new
screen's song (`GameScreen.songId`; `screens.md`):

- **The same song as the last one asked for: nothing happens**, so it
  plays on without a break (for example title to load screen, both
  `Theme`).
- **Another song, while one plays**: the old one fades out over 4 s (a
  straight line). `Music.update` sees, in the first frame after the old
  one is gone, that it has stopped, and starts the new one **from its
  beginning**. At 60 frames a second the new song starts in frame 239
  after the request, 3.98 s.
- **No song** (the day screen sets none): the song fades out over 4 s
  and nothing follows. So a day starts with `Theme` fading out under the
  booth, and the night screen starts `Theme` again from the beginning.
- **A request during a fade-out** changes which song follows; the
  fade-out starts again from the current volume, over another 4 s.

`Music.beat` is the song's position (as the host last reported it, in
seconds) turned into beats by `MusicBeat`.

## The beat (`MusicBeat`)

`Music` makes the only `MusicBeat`, always with the built-in table
(the constructor's other form, a single fixed tempo, is never used). The
table, bars counted from 1:

| From bar | 1 | 5 | 11 | 16 | 21 | 25 | 29 | 33 | 37 | 39 | 41 | 45 | 46 | 47 | 48 | 49 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bpm | 100 | 102.5 | 105 | 107.5 | 110 | 112.5 | 115 | 117.5 | 120 | 122.5 | 125 | 125 | 110 | 100 | 90 | end |
| Starts at (s) | 0 | 9.600 | 23.649 | 35.077 | 46.240 | 54.967 | 63.501 | 71.849 | 80.019 | 84.019 | 87.937 | 95.617 | 97.537 | 99.719 | 102.119 | 104.786 |

So 48 bars of 4 beats, 192 beats in 104.786 s: the music speeds up from
100 to 125 bpm and slows down over the last four bars.

- `getBeat(seconds)`: walks the table, each stretch adding its beats in
  proportion (held to the stretch). Past the end it stays at 192.
- `getTime(beat)`: the exact inverse (checked to 3 x 10⁻¹⁴).
- `getBpm(beat)`: the tempo of the bar beat / 4 + 1; past the table, the
  first tempo, 100. Nothing outside `app.aud` calls `getTime` or
  `getBpm` by name.

**The table fits `Theme`** (measured, not code): in
`music_beat_check.py`'s onset analysis of the extracted recording, the
table's beat times line up with the note starts with a score of 12.3 at
exactly the table's tempo (scale 1.000) and a shift of +0.05 s, while the
best steady tempo scores 4.9. `Theme`'s first sound is at 0.045 s, which
matches the shift. `Victory` is a steady 105 bpm (score 14.8; the table
4.6); `Death` fits neither. The table runs 1.7 s longer than `Theme`
(103.05 s), so its last stretch is never reached: when the song loops,
the beat goes from about 189.4 back to 0.

### The title screen's rise in seconds

`screens.md`, part 2, gives the rule: b = beat x 0.5 + 0.035, the title
rises one step each time b passes a whole number, while b is below 20.
With the table:

- **The rise takes 23.6 s** (it ends at beat 39.93, just before bar 11),
  in 20 steps about 1.2 s apart (1.16 s for the first, 1.17 s at
  102.5 bpm; the steps start at 0, 1.16, 2.36, ... 22.44 s).
- The logo's bob is one cycle per bar: 2.4 s at 100 bpm, 1.92 s at the
  fastest, 125 bpm.

Computed by `aud_check.py` from the table; not watched.

## For the port

- One speaker and one music player for the whole run; sound time from
  real time, uncapped.
- Effects: skip rules in the order above (unknown, room, ignore switch);
  pick the recording only when the sound starts.
- Fades are straight lines over the sound's fade time, jumping to the
  target within 0.01; a stopping sound is stopped at 0.001 or below.
- A screen change: every effect fades out (songs not), then one-shots
  are ignored to the end of that frame; `Music.play` with the new
  screen's song as above.
- The pause screen pauses effects only.
- The ambient loops: a fade restarted every frame, so the smooth
  approach above. **A decision for `DESIGN.md`: whether to keep the
  "one ambient at full level until its first fade-in"**, which is what
  the code does (not heard).
- The beat: the table above, applied to the song's position.
- Vibration: none on desktop.

## Check

`scripts/checks/aud_check.py` (pure Python; the host is a stand-in that
keeps time, not game code):

    python -I scripts\checks\aud_check.py scripts\reference extracted\art\assets\data

Run on 2026-10-17: `problems: none`. It checks the table (16 entries,
192 beats, 104.786 s, the inverse, tempos at chosen beats), the title's
rise end (23.608 s), a song change and a fade to no song (238 frames to
the stop, the new song in frame 239), a song the host lacks, the booth's
loops (host volumes after the constructor, the smooth approach, 275
frames), rooms, unknown ids, the ignore switch (and that a skipped sound
does not move its recording order), the pause, `stopAll` both ways, a
1-second fade-out (60 frames). Two of its expected frame counts were
first worked out wrong by hand (238 and 274; the right ones are 237
frames of fading before the stop in frame 238, and 275, from
ln 0.01 / ln(59/60) = 274.01); the code was right, the expectations were
corrected.

`scripts/checks/music_beat_check.py` (needs numpy, which the system
Python has; about 20 seconds):

    python -I scripts\checks\music_beat_check.py scripts\reference extracted\audio

Run on 2026-10-17: `problems: none`, with the scores above. A first,
simpler attempt (energy steps instead of spectral change) could not tell
the table from a steady tempo (scores 0.80 against 0.79 to 0.83) and was
dropped.

## Not studied

- Which booth state a day starts in, so which ambient is the one heard
  at full level at first (inferred `booth-ambient`, above).
- The booth's state machine as a whole (`border-scene.md`): the six
  "border" states are known only by name.
- Whether anything calls `SetPauseForAppLostFocus` (`audio.md`).
- Whether the game ever has 32 sounds at once (`audio.md`).

## Things to listen for in the game

1. Pausing (Escape) on the night screen: `Theme` keeps playing under the
   pause screen. Pausing during a day: the street noise and the booth's
   hum stop until the game resumes.
2. Going from the news screen into the day: `Theme` fades out over about
   4 s.
3. At the start of a day, before the first traveler: both the street
   noise and the booth's hum, the hum at full level (the "full level at
   first" item above).
4. When a traveler comes in, the street noise fades out over a few
   seconds and the hum fades in; no car sounds while the traveler is in
   the booth.
5. Leaving the title for the load screen and back: `Theme` plays on
   without restarting.
6. The title's rise at the first start takes about 24 seconds and its
   steps fall on the music's beats.
