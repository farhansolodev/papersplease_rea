# Sounds.xml: sound effects, and how songs are named

Studied on 2026-10-13. `Sounds.xml` lists the game's sound effects. Songs are
not in it; they are found by name (below).

Functions read in full: the `data.SoundDefLib` constructor and `get`; the
`data.SoundDef` constructor and `get_filename`; the `app.aud.Speaker`
constructor, `play` and `music`; `app.aud.Music.play` and `playNow`. Three
constants were read from the DLL.

Everything here is confirmed in the code unless marked otherwise.

## The file

```xml
<sound id="stamp-down"/>
<sound id="border-ambient" loop="true" fade="1" vol="0.5"/>
<sound id="paper-dragstart" file="paper-dragstart0.wav paper-dragstart1.wav paper-dragstart2.wav"/>
<sound id="car-driveby" vol="0.2" room="border"/>
```

| Attribute | Meaning | When absent |
|---|---|---|
| `id` | The name the code and data files play it by | required |
| `file` | One or more recordings, separated by single spaces | one recording, `<id>.wav` |
| `loop` | Exactly `true`: the sound repeats until stopped | plays once |
| `vol` | Loudness, a number multiplied into the volume | 1 |
| `fade` | Fade time in seconds | 3 (and the sound is marked as having no fade of its own) |
| `room` | The sound plays only while the speaker is in this "room" | plays anywhere |

A repeated id stops the game with an error ("Sound already exists:").

The comments in the file are the sources of the recordings. They carry no
data.

## Which recording plays (`SoundDef.get_filename`)

- One recording: that one.
- Exactly two: one random draw picks between them (no sound has two).
- **More than two: a fixed shuffled order over the first three**, repeated
  (`ShuffledSequence` with a count of 3, `traveler-build.md`). The count is
  the number 3 in the code, not the number of recordings, so **a fourth
  recording is never played**. Two sounds have four: `text-reveal` and
  `chain-jingle`; `text-reveal3.wav` and `chain-jingle3.wav` are never
  heard.

All sounds share one random generator, seeded 23 when the file is loaded;
each sound with more than two recordings takes one number from it, in file
order, as the seed of its own order. This generator is separate from the
game's others, so sounds do not disturb the game's randomness.

## Playing a sound (`Speaker.play(id)`)

- An unknown id plays nothing (and writes a debug-log line).
- A sound with a `room` is skipped when the speaker's current room is set
  and different.
- A sound that does not loop is skipped while the speaker is told to ignore
  such sounds for the current frame.
- Otherwise the chosen recording starts in the "effects" category with the
  sound's loop flag and volume, and is tracked with its volume and fade so
  it can be faded or stopped later. The call returns a play number. The
  recording is picked only at this point, so a skipped sound does not
  move its recording order on (`audio-layer.md`, 2026-10-17). Who sets
  the room and the ignore switch, and what a fade does, is there too.

## Songs (`Speaker.music`, `Music.play`)

A song id is turned into the file name `<id>.ogg` and played looping at full
volume in the "music" category. There is no list of songs in the data files.
Asking for the song that is already playing does nothing; asking for a
different one fades the current one out and then starts the new one.
The song ids are `Theme`, `Death` and `Victory`, the only three songs
stored (`audio.md`, 2026-10-17; this said until then that the others
were in screen code not yet read): `Theme` for most menu screens,
`Victory` for the credits, `Death` or `Victory` for the endings
(`ends-xml-format.md`).

## Check against the data file

`scripts/checks/sounds_check.py` (run 2026-10-13):

- 94 sounds, no repeated id; every attribute is one the code reads.
- 2 loop (`border-ambient`, `booth-ambient`, both with a 1 second fade); 1
  has a room (`car-driveby`, `border`); 25 have a volume other than 1, the
  lowest 0.05.
- 85 sounds have one recording, 7 have three, 2 have four. 108 distinct
  recordings are named, all `.wav`. Three sounds reuse another sound's
  recording (the three `criminalposter-...` sounds), and `paper-totop` uses
  the `paper-dragstart` recordings at a quarter of the volume.
- Modelling the choice 600 times per sound: every recording of the
  three-recording sounds is played, never the same one twice running; the
  fourth recording of `text-reveal` and of `chain-jingle` is never played.
- Every sound is asked for by something: 81 ids appear among the code's
  strings and the other 13 appear by name in other data files (which files
  was not broken down). The six distinct `sound=` values in other data
  files are all defined.

## Notes for the port

- Use the fixed-count shuffled order, including its blind spot for a fourth
  recording, if the port is to sound the same.
- Sound choice has its own random generator; it must not draw from the
  game's.

## Not studied

- (The audio files were listed here as not extracted. Extracted on
  2026-10-17, `audio.md`: all 108 recordings named here and the 3 songs
  are stored, and nothing else; `scripts/checks/audio_check.py` confirms
  it. The two never-played 4th recordings are stored too.)
- (The Unity side that plays a recording, and the volume settings, were
  listed here; read on 2026-10-17, `audio.md`: at most 32 sounds at once,
  volume as setting squared.) (Fading (`SpeakerSound`), pausing, the
  speaker's "room" and the beat tracking in `Music` / `MusicBeat` were
  listed here as not studied; read on 2026-10-17, step 6b,
  `audio-layer.md`: straight-line fades over the sound's `fade`, the
  pause stops effects only, only the booth sets the room, and the beat
  is a fixed tempo table that fits `Theme`.)
- (The full list of song ids was listed here: `Theme`, `Death`,
  `Victory`, answered on 2026-10-17, `audio.md`.)
- Nothing here has been compared with the running game.
