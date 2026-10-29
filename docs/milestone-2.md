# Milestone 2: sound

Built 2026-10-29 (step 12). The user said "just start on the work", so the
plan was not put to them first; the choices made without asking are under
"Decisions" and can be changed. The plan is the milestone's row in
`DESIGN.md` ("Milestones"): the start screen with its options and "click to
start"; `Theme` playing at once on a first visit while it still downloads,
then kept in the browser, so an offline reload plays it; a test page that
plays any effect; the sound player and the volume rule.

## How to try it

From the project folder (the first command takes a few minutes when the
Rust code changed; it also makes the packs and, the first time, encodes the
songs with ffmpeg, about 10 seconds):

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080`. You should see:

1. **The start screen** (every page has it now): "PAPERS, PLEASE", two
   sliders for music and sound volume (0.0 to 1.0 in tenths, both 1.0 at
   first), a "Full screen" box, a choice of picture size ("Sharp pixels" or
   "Fill the window"), a loading bar, then **Click to start**. The options
   are kept in the browser, so they are as you left them on the next visit.
2. After the click, the title screen as in milestone 1b, with **`Theme`
   playing** and looping. The title does not rise yet (milestone 3).
3. `http://localhost:8080/?page=sounds` is the **sound test page**: every
   effect (108) and song (3) in four columns, the chosen one boxed in blue,
   playing ones green. The keys (click the picture first if they do
   nothing):
   - arrow keys choose;
   - **Enter** plays the chosen sound once, **L** plays it looping;
   - **S** stops everything;
   - **Space** pauses and resumes the effects (songs go on, as under the
     game's pause screen);
   - **1** / **2** lower / raise the sound setting by 0.1, **3** / **4** the
     music setting; the line under the grid shows the setting and the
     decibels it gives (the setting squared). These keys do not save the
     setting.
   The effects arrive a moment after the start (the effects pack loads in
   the background); until then the first line says "loading".
4. To see the song streamed and kept (developer tools, F12): on the
   **Network** panel, a first visit (or one after `?nosw`, below) shows one
   request for `songs/Theme.<code>.ogg` while it plays; afterwards
   **Application > Cache Storage > pp-...** holds it. With "Offline" ticked
   on the Network panel, a reload still plays `Theme`. To watch the
   streaming itself, set the Network panel's throttling to a slow
   connection before the first visit: the song should start before its
   download ends.
5. `?nosw` removes the service worker and everything it kept (as before),
   for a fresh first visit.

## What was built

| Part | Where | Notes |
|---|---|---|
| Sound files | `scripts/build_assets/build_audio.py` | `effects.pack`: the 108 effects as the game stores them (IMA ADPCM, cut out of `sharedassets0.resource` unchanged, with channels, rate and length; 5.8 MB). `songs/<Song>.ogg`: the three songs re-encoded to Ogg Vorbis by ffmpeg (6.7 MB together). Both only in `build/` |
| ADPCM decoder | `port/core/src/adpcm.rs` | The game's block layout (`audio.md`); decodes the pack's effects |
| Volume rule | `port/core/src/sound.rs` | A setting is tenths from 0 to 1; the category's volume is its square (`Game.applySettings`) |
| Sound test page | `port/core/src/soundtest.rs` | Drawn by the core in the `regular` font |
| Picture size | `port/core/src/screen.rs` | `stretch`: the largest size with the picture's shape, any zoom |
| Sound player | `port/www/audio.js` | The browser's version of `UnityPlatformAudio` (below) |
| Start screen and loader | `port/www/index.html` | Options, download with progress, the click, the effects in the background |
| Song streaming and keeping | `port/www/sw.js` | Below |
| Host | `port/web/src/main.rs`, `port/web/src/sound.rs` | Reads the settings, sets the category volumes, starts `Theme` on the title, hands the decoded effects to the player, the sound test page's keys, the stretched picture |
| Build | `scripts/build_web.py`, `scripts/serve.py` | Effects pack, songs (in `songs/`, listed apart), `audio.js`; `.ogg` served as `audio/ogg` |
| Checks | `port/core/tests/adpcm.rs`, `scripts/checks/web_offline_check.mjs` | Below |

### The sound player (`port/www/audio.js`)

It does what the original's Unity host does (`audio.md`, "How the host
plays a sound"), with the browser's Web Audio:

- **`start(id, category, file, loop, volume)`**: nothing plays, silently,
  when the file is unknown or 32 sounds already play. Effects play from
  the decoded samples; songs from their file through the browser's own
  media player (an `<audio>` element), which is what lets a song start
  while it downloads. Every sound goes through its own volume, then its
  category's (music or effects), then to the speakers.
- **`setCategoryVolume`**: held to 0.0001..1, turned into decibels
  (20 x log10) and back into a gain, as the original's mixer does; so a
  setting of 0 plays at -80 dB, not silent.
- **`stop`, `setVolume`, `position`** (seconds, -1 for an unknown id),
  **`setCategoryPause`** (resuming a category resumes only what that
  category's pause paused), **`update`** (frees finished one-shots).
- Not copied: the pause when the window loses focus (no caller found in
  the game, `audio.md`).

The game side (`app.aud`: the speaker's fades, rooms, song changes, the
beat) is not built yet: it comes with milestone 3, which needs it for the
title's rise. For now the host starts `Theme` itself on the title page, as
`Speaker.music` would (looping, volume 1).

### Songs: streamed once and kept (`port/www/sw.js`)

As `DESIGN.md`, "Loading and caching", item 3, describes. The service
worker answers every request under `songs/`:

- **Kept already:** answered from Cache Storage, a partial request
  ("Range", `bytes=a-b`) with just that part.
- **First time:** the whole file is downloaded once; as it arrives it is
  split in two, one copy going on to the media player, the other written
  into Cache Storage. If the download is cut off the write fails and
  nothing is kept. A second request for the same song while it is still
  downloading goes to the network as it is (usually a small part), so
  the song is not downloaded whole twice.
- A song is not downloaded when the worker installs; a song an older
  build kept is carried over to the new build's cache.
- On a first visit the page waits (at most 15 s) for the service worker to
  take charge before it offers "Click to start", because only then does
  the song pass through it. The worker is now registered after the game
  has downloaded, so its own copy comes from the browser's download cache
  instead of a second download.

### Effects in the background

The start pack still holds only the pictures, fonts and texts. The effects
pack (all 108) is downloaded after the click; the host decodes it when it
arrives and hands every effect to the player. Splitting out the effects
the title and menus need into the start pack (`DESIGN.md`, item 1) waits
for milestone 3, which is when those screens first make a sound.

## Decisions

Made without asking, since the user said to start; each is reversible:

- **The songs' format** (open in `DESIGN.md` until now): **Ogg Vorbis
  re-encoded with ffmpeg** at quality 6 (about 190 kbit/s; the game
  stores them at about 160). This was the suggested way and needs no
  download. It is lossy a second time (not listened to side by side). The
  lengths are exact: 4,544,505, 4,100,728 and 6,955,201 samples per
  channel, the same as the game's (read with `ffprobe`).
- **The effects: the game's own ADPCM data, decoded by the port** (the
  suggested way): exact, and smaller (5.8 MB) than WAV (21 MB).
- **The sound player is in the page's JavaScript, not in the Rust host.**
  `DESIGN.md` put it in the host "through the browser's Web Audio"; the
  host now only passes the commands on (`port/web/src/sound.rs`). Why:
  the player is all browser calls, and in JavaScript it needs no new
  browser bindings compiled into the WebAssembly. Nothing of the game is
  in it.
- **The start screen**: the four suggested options; volumes as tenths,
  stored with the game's own names (`musicVolume`, `soundVolume`,
  `fullscreen`) in the browser's local storage under `pp.settings`, so
  the settings screen (milestone 3) can share them. Full screen is
  entered on the click (a browser allows it only then). "Fill the window"
  keeps the picture's shape (black bars on the other side).
- **The start screen is shown for every page**, test pages included, so
  every page can play sound.

## What was measured

All on this machine, 2026-10-29.

| What | Value |
|---|---|
| WebAssembly | 26,423,219 bytes (5.48 MB gzip), 21 KB more than after 1b |
| Effects pack | 5,799,262 bytes (4.73 MB gzip: ADPCM hardly compresses) |
| Songs | `Death` 1,909,235, `Theme` 2,010,095, `Victory` 2,819,604 bytes (6.7 MB; the game stores 6.5 MB) |
| Start pack | 2,030,052 bytes, unchanged |
| `audio.js`, `index.html`, `sw.js` | 6, 12 and 6 KB |
| Release build | 3 min 20 s after the change (whole `build_web.py` 3 min 38 s); encoding the three songs about 10 s, only when they change |
| `cargo test -p pp_core` | 54 unit tests; `tests/adpcm.rs` decodes and compares all 108 effects in about 2 to 4 s |

## What was checked, and how

- `cargo test -p pp_core` (`--nocapture` for the new test): 54 unit tests
  pass (new: the ADPCM block layout, the volume rule, the stretched
  picture, the test page's choice), the 35 font pages and the title as
  before, and `tests/adpcm.rs`: **all 108 effects decoded by the port are
  identical to FMOD's WAV files, sample for sample**.
- `node scripts/checks/web_offline_check.mjs 8080` in headless Edge, with
  `scripts/serve.py` running. It now clicks each page's start button with
  a real mouse click. Its new parts:
  - "Fill the window" at 1400 x 900: the picture 1400 x 786 at y 57, as
    computed.
  - The title: `Theme` plays (its position passes 1 s); the song is then
    in Cache Storage; **the server sent it whole exactly once** (counted
    by the server, `/_served.json`), and the service worker reports its
    copy complete, 2,010,095 of 2,010,095 bytes. Category volumes 1 and 1
    for settings of 1.0.
  - The sound test page: the 108 effects reach the player; three (the
    shortest stereo 44.1 kHz, mono 44.1 kHz and mono 22.05 kHz) read back
    from the browser's sound buffers are **identical to the WAV files**;
    L plays the first effect looping (`booth-ambient.wav`), S stops it,
    key 1 makes the sound setting 0.9 and the effects gain 0.81.
  - With the network switched off: the font page and then the title
    start, and **`Theme` plays from Cache Storage**.
  - Everything from milestones 0, 1a and 1b still passes.
- The last build passed the check **4 times out of 4**. Earlier builds
  of the same day failed some runs; see "Dead ends". In one of the four,
  the media player asked for a part of the song while it was still
  downloading, and that part was served without a second whole download.

## Findings

- **Chrome refuses a song whose parts come from two places.** While a
  song was downloading, a second request from the player (for a part of
  the file) went straight to the network. Chrome then stopped with "no
  supported source was found". The worker now makes that answer itself
  too (`sw.js`, `answerSong`).
- **The browser stops and restarts the service worker on its own**, so
  nothing kept in its memory survives (seen once: the song was kept, but
  the worker's download count was empty). The check now counts downloads
  at the server.
- **The app's built-in browser pane does not run service workers**:
  registering fails with "an unknown error occurred when fetching the
  script" and the server never sees a request for `sw.js`. The page now
  carries on at once when that happens, without waiting 15 s for a
  worker (the first version waited). In that pane nothing is kept for
  offline use; this is the pane, not the build (headless Edge runs the
  worker).

## Dead ends

- **Goal:** the check's song part passing every time.
- **What works (tested):** the last build, 4 runs out of 4.
- **The problem:** all runs of the day, in order: 2 runs before the
  partial-request fix (1 passed, 1 failed on Chrome's refusal, above).
  After the fix and before the last build, 13 runs: 8 passed; 3 failed
  in ways not explained (twice `Theme` was not in Cache Storage after
  30 s with no error reported, once the effects pack's download failed,
  "Failed to fetch", on the sound test page); 2 failed because the check
  then counted downloads in the worker's memory, which the browser had
  wiped (the check's fault, fixed). One passing run also printed "Failed
  to fetch"; probably the background effects download cut off when the
  check left the page (not checked).
- **What was tried:** the partial-request fix; the worker reports its
  errors to the page's console (none was reported in any run since); a
  count of how far the copy into the cache got, and the worker's start
  time, printed when the song is missing (no failure since, so no
  numbers yet).
- **Ideas not tried:** read the worker's own console through the
  browser's debugging connection; collect the song in memory and write it
  to the cache in one piece when complete, instead of as a stream; run
  the check many more times to measure how often it fails.
- **Inferred, not shown:** if the browser stops the worker during the
  first download, the copy is lost and the next visit streams the song
  again, which is the designed fallback; whether the playing song is cut
  too was not seen.

## Not tested

- **Listening.** Nothing here was heard by a person: no one has checked
  that the songs, re-encoded, sound like the game's, that the effects
  sound right, or that `Theme`'s loop point has no gap. The checks
  measure positions and samples only.
- **Streaming on a slow connection**, that a song really starts before
  its download ends. Locally the whole song arrives in milliseconds.
  (How to watch it is in "How to try it", item 4.)
- **Firefox**, and Chrome or Edge in a visible window by hand.
- "Full screen" on the start screen (headless Edge has no screen).
- The pause of the effects category in the browser (Space on the test
  page): built, not checked.
- 33 sounds at once (the 33rd should be silently dropped).
- A song carried over from an older build's cache, and a service worker
  update to a new build.
- Anything against the running game.
