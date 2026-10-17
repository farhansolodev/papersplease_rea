# Audio: the stored sounds, their extraction, and how the host plays them

Studied on 2026-10-17 (step 6). This covers where the game's sound
recordings are kept, how they are taken out into files a browser can
play, and the Unity side of playing them (`HostUnity.UnityPlatformAudio`
and the scene's audio mixer). Which sound plays when, from the data
files, is in `sounds-xml-format.md`. The game-side audio layer
(`app.aud`: `Speaker`, `SpeakerSound`, `Music`, `MusicBeat`: fading,
rooms, the music's beat) is **not** studied here.

Sources: the Unity files read with UnityPy 1.25.4 (`.venv/`); the sound
data decoded with the FMOD library that UnityPy's `fmod_toolkit` 0.1.3
package brings along (`fmod.dll`, installed with UnityPy on 2026-10-17,
nothing new downloaded); code reading of all 15 functions of
`HostUnity.UnityPlatformAudio` (`decompiled/all/top.clean.c`) and of
`Game.applySettings`; one Ghidra run for the instructions of
`setCategoryVolume` and the maths function it calls
(`decompiled/audio_run1.txt`); four constants read from the DLL.
Nothing here was listened to or compared with the running game.

Terms used below:

- **Sample**: one number of the sound wave; 44,100 of them make a second
  at 44.1 kHz. Stereo has two per moment, one per channel.
- **PCM**: sound stored as plain samples, here 16-bit numbers. A WAV file
  is PCM with a 44-byte header.
- **ADPCM** (here IMA ADPCM): a simple compression that stores each sample
  as a 4-bit step from the previous one, a quarter of PCM's size. Lossy,
  but cheap to decode.
- **Vorbis**: the compression inside `.ogg` files, much smaller, lossy.
- **FMOD**: the sound engine Unity uses inside. Unity stores each clip as a
  small FMOD sound bank (an **FSB5** file).
- **Decibel (dB)**: a loudness ratio; 0 dB is unchanged, −6 dB is about
  half the wave's height, −80 dB is near silence.

## Where the sounds are

Not in `Art.dat` (`art-dat-format.md`). The scene's `HostUnity` object
(`level0`, `screen-output.md`, "The Unity files") holds two lists of 111
entries each, in the same order:

- `audioPaths`: the file names the game asks for, such as `stamp-down.wav`
  and `Theme.ogg`. 108 end in `.wav`, 3 in `.ogg`.
- `audioClips`: one `AudioClip` object per name, all in
  `sharedassets0.assets`.

Every clip's name is its file name without the extension (no exception).
Each clip keeps its sound data in `sharedassets0.resource`; the 111
pieces lie end to end and fill the whole file (12,272,544 bytes), with
nothing else in it.

Every clip has the load type **DecompressOnLoad** (Unity decodes the
whole clip to PCM when it loads) and is preloaded. Each piece is an FSB5
bank, version 1, holding exactly one sound:

| Names | Stored as | Channels, rate | Count |
|---|---|---|---|
| `.wav` (the effects) | IMA ADPCM (FSB5 codec 7; Unity format "ADPCM") | stereo 44,100 Hz | 80 |
| | | mono 44,100 Hz | 25 |
| | | mono 22,050 Hz (`ui-achievement`, `speech-inspector`, `speech-entrant`) | 3 |
| `.ogg` (the songs) | Vorbis (codec 15) | stereo 44,100 Hz | 3 |

So the names say `.wav` and `.ogg`, but the stored data are neither: the
names are only keys. The three songs are `Death.ogg` (93.0 s), `Theme.ogg`
(103.0 s) and `Victory.ogg` (157.7 s); the longest effect is
`border-ambient` (14.7 s).

### The ADPCM block layout

Found by writing an independent decoder and comparing it with FMOD's
output (below). Per channel, a block is 36 bytes: a 4-byte header (the
first sample as a signed 16-bit number, the step index, one unused byte)
and 32 bytes of 4-bit codes, low half of each byte first. A stereo block
is 72 bytes: both headers first, then the codes in turns of 4 bytes per
channel. **The header sample is the block's first sample, then 63 codes
follow; the block's 64th code is never used.** So a block gives 64
samples per channel. The step itself is the standard IMA ADPCM one. A
first try that skipped the header sample and used all 64 codes differed
on every one of the 108 effects.

## The extraction

`scripts/unity/audio_extract.py` (run with `.venv\Scripts\python`):

    .venv\Scripts\python -I scripts\unity\audio_extract.py game\PapersPlease_Data extracted\audio

It reads `HostUnity`'s two lists, has FMOD decode each clip, and writes
one 16-bit PCM WAV per name into `extracted/audio/` (gitignored), named by
the name with its extension made `.wav` (so `Theme.ogg` becomes
`Theme.wav`), plus `audio_index.json`: per name, the clip, Unity's
settings, where the stored piece lies, the FSB5 header and what FMOD gave.
It takes about 5 seconds. Result: 111 files, about 80 MB (83 MB of PCM:
the songs about 62 MB, the effects about 21 MB), against 12 MB stored.

FMOD gave 16-bit PCM for every clip, ADPCM and Vorbis alike, with
exactly the sample count in the FSB5 header, and that count agrees with
Unity's own clip length (its `m_Length` in seconds times the rate) to a
fraction of a sample. (`fmod_toolkit`'s own WAV helper is not used: its
conversion path for floating-point output is wrong when numpy is
missing, as here. FMOD did not give floating-point output, so it would
not have mattered, but the script writes the WAV itself.)

**What the WAV files are, by the evidence:** for the effects, exactly the
samples a standard IMA ADPCM decode of the stored data gives (two
decoders agree on all 108, sample for sample). That Unity's player
decodes them the same way is inferred from Unity being built on FMOD;
not tested by recording the game's output. For the songs, FMOD's Vorbis
decode; Vorbis decoders may differ in the last bit, so this is the
sound, not necessarily the exact samples the game plays. No independent
check of the songs' decode was made beyond their length.

## How the host plays a sound (`HostUnity.UnityPlatformAudio`)

All read in full; the reference is `host.AudioHost` and
`host.category_attenuation_db` in `scripts/reference/host.py`.

- **Set-up** (constructor): finds the mixer groups `Master/Music` and
  `Master/Effects`; makes a hidden object with **32 `AudioSource`s**, all
  free; builds a table from each name in `audioPaths` to the clip at the
  same place in `audioClips` (a repeated name would keep the later clip;
  there are none).
- **`start(playId, category, filename, loop, volume)`**: if the name is
  not in the table, or no source is free, **nothing plays and nothing is
  reported**. Otherwise a free source gets the clip, the volume, the loop
  flag and the category's mixer group (the music category goes to
  `Music`, any other category to `Effects`), starts, and is filed under
  the play id. So at most 32 sounds play at once; the 33rd is dropped.
- **`stop(playId)`**: stops the source, takes its clip away and frees it.
- **`Update`** (each frame): a source that is not playing, does not loop
  and is at sample 0 (so finished, not paused) is stopped and freed.
- **`setVolume(playId, volume)`**: the source's own volume.
- **`getPlayPosition(playId)`**: the source's time in seconds, or −1 for
  an unknown id.
- **Pausing**: each playing source has a pause state: none, paused by the
  game (`setCategoryPause`, for one category), or paused because the
  window lost focus (`SetPauseForAppLostFocus`). Resuming a category only
  resumes what that category's pause paused, and regaining focus only
  what losing focus paused. No caller of `SetPauseForAppLostFocus` was
  found by name in the decompiled game code (it may be called by Unity
  through a name the search cannot see; not followed).
- **`setCategoryVolume(category, volume)`**: holds the volume to
  0.0001..1, takes **20 x log10** of it and writes the result, in
  decibels, to the mixer's exposed parameter `<group name>Atten`
  (`MusicAtten` or `EffectsAtten`). The decompiler showed the maths
  function only as `FUN_180131510`; its instructions use the constants
  log10(2) (as 0.30078125 + 0.000248746) and 1/ln 10 (0.4342945), so it
  is `log10`. The three other constants: 0.0001, 1 and 20 (read as
  4-byte floats).

**The volume settings**: `Game.applySettings` (`screens.md`, part 4)
passes the music setting squared to the music category and the sound
setting squared to the effects category. So the loudness a setting gives
is a gain of setting² (held to at least 0.0001): 1 plays as stored, 0.5
at a quarter of the wave's height (−12 dB), and **0 at −80 dB, not
fully silent**.

## The mixer

Read from step 5b's dump (`extracted/unity/objects/`): one mixer,
`AudioMixer`, with a group `Master` and two groups under it, `Effects`
and `Music`; no effects on any group; one snapshot, `Snapshot`, which
sets every group's volume to 0 dB and pitch to 1. Two parameters are
exposed: their names are stored as hashes, which are the CRC32 of
`EffectsAtten` and `MusicAtten`, and they drive the volume of `Effects`
and of `Music`. So apart from the two volume settings the mixer changes
nothing: a sound plays at its stored level times its own volume
(`Sounds.xml`'s `vol`, `sounds-xml-format.md`) times the category's
setting².

## The songs

The game can play only the three stored songs. Who asks for them, from
a search of the whole decompile for the names:

- `Theme`: the constructors of the intro, title, news, night, load,
  settings and endless screens set it as the screen's song.
- `Victory`: the credits screen.
- `Death` or `Victory`: the ending screen, from the ending's `music`
  attribute in `Ends.xml` (17 endings `Death`, 3 `Victory`).

No other screen's constructor sets a song by that search (the day screen
sets none). How a screen's song is started, faded and
changed is in `app.aud.Music`, not studied.

## Check

`scripts/checks/audio_check.py` (pure Python):

    python -I scripts\checks\audio_check.py scripts\reference extracted\audio game\PapersPlease_Data\sharedassets0.resource extracted\art\assets\data extracted\unity

Run on 2026-10-17: `problems: none`. It checks: the 111 names, one WAV
each, headers, lengths against Unity and the FSB5 header; that the stored
pieces fill `sharedassets0.resource` end to end; an independent IMA ADPCM
decode of every effect against the WAV (108 of 108 identical); that
every recording `Sounds.xml` names is stored (108 of 108) and no stored
`.wav` is unnamed; that the songs asked for are the three stored; that no
file is silent; the mixer as above; `host.category_attenuation_db` and
`host.AudioHost`.

Observed, not explained: `traveler-breathein` peaks at 63 of 32,767 (about
−54 dB), far quieter than any other recording (the next, its partner
`traveler-breatheout`, at 237). Both decoders give the same samples, so
it is what is stored. 12 files reach full scale.

## For the port

- Load the sounds by the game's own names: `<id>.wav` names from
  `Sounds.xml`, `<song>.ogg` for songs. The extracted files carry the same
  names with `.wav` for all.
- Effects: the WAV files are the game's samples; any browser plays them
  (Web Audio resamples the 22,050 Hz ones).
- **A decision for `DESIGN.md`: how to ship the songs.** As WAV they are
  62 MB, too much for a page that loads them. Two ways, both needing a
  tool not installed (so the user's go-ahead for a download): rebuild
  the original Vorbis data into normal `.ogg` files without re-encoding
  (FSB5 removes Vorbis set-up headers, which tools such as vgmstream
  restore from a table), or re-encode the WAV files (to Ogg Vorbis or
  Opus, which loses a little quality again). The effects could stay WAV
  (21 MB) or be compressed the same way.
- Volume: gain = setting² held to 0.0001..1, per category, times the
  sound's own volume. Whether to keep "0 is −80 dB, not silent" is a
  detail for `DESIGN.md` (inaudible in practice).
- At most 32 sounds at once; a 33rd is silently dropped. Whether the game
  ever reaches 32 was not looked at.
- The mixer itself does nothing else, so the port needs no effects.

## Not studied

- `app.aud`: `Speaker` (rooms, fading, the "ignore one-shot sounds this
  frame" switch, pausing all, stopping all), `SpeakerSound`, `Music`
  (how songs fade and change), `MusicBeat` (the beat the title screen's
  rise follows, `screens.md`, part 2). The next audio step.
- Whether anything calls `SetPauseForAppLostFocus`, so whether sounds
  pause when the window loses focus.
- Unity's own mixing (how it resamples the 22,050 Hz clips, clipping
  when many sounds add up).
- **Nothing here has been heard or compared with the running game.**
  Watch list: the title's `Theme` plays; an ending plays `Death` or
  `Victory`; the 4th recordings `text-reveal3` and `chain-jingle3` are
  never heard (`sounds-xml-format.md`); a volume setting of 0 is
  silent to the ear; the traveler's breathing in is barely audible.
