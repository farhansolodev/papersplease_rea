# Design decisions for the port

**Status (2026-10-17, step 8): the decisions list, the architecture and
the milestones are written.** The five questions before milestone 0 were
answered by the user the same day ("Answered before milestone 0"); the
user left the use of Bevy to me, and I chose Bevy as a thin host. Nothing
is built or tested yet; Bevy's libraries are downloaded.
The decisions list started from the sorting of the open questions
(step 7), and the open-question list in `PROGRESS.md` points here for the
`C` kind.

On 2026-10-17 the user accepted every suggested default below ("the suggested
actions are fine"). So each is **decided**, except two that were never a plain
suggestion and are marked **open** (the songs' format, which still needs a tool
download with its own go-ahead, and fullscreen in a browser). A decision can be
changed later: say so and this file is edited with the date.

## Decided by the user

| Decision | Date | Detail |
|---|---|---|
| English only: no Language row, no language chooser, no age rating | 2026-10-16 | `screens.md` part 7; English still loads its own pack (`language-pack.md`) |
| No leaderboards. The local best score per course and style is kept | 2026-10-16 | `screens.md` part 7 |
| The settings screen's `web` and `twitter` buttons are left out | 2026-10-14 | `screens.md` part 4 |
| No quit option: neither the pause screen's QUIT nor the title's quit button | 2026-10-14 | `screens.md` part 4 |
| The build goes in milestones, each one a browser build the user can open and try, to judge the look and feel as the project moves | 2026-10-17 | "Milestones", below |
| On a player's first visit the audio is streamed (it plays while it downloads) and saved to the browser's storage in the background, so the player does not wait for it before playing | 2026-10-17 | "Loading and caching", below |
| The game itself is kept in the browser's storage, so a later visit to the same address starts without downloading it again | 2026-10-17 | "Loading and caching", below |
| **The quads are drawn by software in `pp_core`, not by the graphics card.** The core draws each frame's quads into its own 570 x 320 picture (`port/core/src/raster.rs`); the host only shows that picture, as in milestone 0. Why: the pixels are exact and testable with `cargo test` against the Python reference on any machine, and no custom shader is needed. The cost is processor time per frame, to be measured when screens get busy (milestone 4); the quad list stays the interface, so the drawing can move to the graphics card later without touching the game. This replaces the first draft's "the host draws the quads on the graphics card" | 2026-10-18 (milestone 1 plan, recommended by me, accepted by the user) | "One frame", below; `milestone-1.md` |

## Needed before the first Rust code (all three decided 2026-10-17)

These change how the first code is written, so they come first.

1. **Frame time.** The original steps by real elapsed time, capped at 0.1 s a
   frame, at 60 frames a second on most screens (65 on the others, never above
   70). A few things move by frame (the credits). Its test player uses a fixed
   1/20 s. (`border-view.md`, "The frame rate".)
   *Decided 2026-10-17 (the user accepted the suggestion):* a fixed step of 1/60 s, with the browser's frame timer feeding
   it, and per-frame quantities kept as in the original.
2. **The random sequence.** In the original, redrawing a page repeats its
   random draws, so which pages the player looks at can change later travelers
   (`desk-drawing-draws.md`); the border scene's generator draws follow real
   time (standing figures draw every 2 to 4 seconds, an attack starts after
   `6 + 4 x r` seconds; `border-figures.md`, `border-scene.md`).
   *Decided 2026-10-17 (accepted):* copy the **booth side exactly** (traveler creation, desk draws,
   speech): the reference matches the game on it and it is the method for
   checking the port. For the **border scene** copy the draw order and the
   delays, but not the dependence on real time (that follows from decision 1).
3. **The English pack** (`language-pack.md`). *Decided 2026-10-17 (accepted):* apply it once, when
   the assets are prepared (`scripts/reference/locpack.py` already does it),
   not at run time. Either way the 23 changed texts and the picture that is
   only in the pack must come out.

## Can wait until the feature is built

| Decision | Decided 2026-10-17 (suggested default accepted), unless marked open | Where from |
|---|---|---|
| How the browser build gets the songs (62 MB as WAV) and the effects (21 MB as WAV) | **Open; settle before milestone 2.** Since step 8 the songs are streamed and kept in the browser ("Loading and caching"); the stored Vorbis data is 6.5 MB for the three songs. Chrome, Edge and Firefox (the chosen browsers) all play Ogg Vorbis by their documentation (not tested). Ways: (1) re-encode the WAV files to Ogg Vorbis at a high quality with the `ffmpeg` already on this machine (no download; a small, probably inaudible loss); (2) rebuild the stored Vorbis data into `.ogg` files without re-encoding (exact, but needs a tool download, `CLAUDE.md` rule 6). For the effects a third way: ship the game's own ADPCM data (about 5.5 MB) and decode it in the port, exact and with no tool, since a second decoder is already written and checked (`audio.md`). *Suggested:* (1) for the songs, the ADPCM way for the effects | `audio.md` |
| The ambient loop that plays at full level at a day's start, until first faded in (by the code; not heard) | Keep it, since it is what the code does. Hear it in the game first if you want to be sure | `audio-layer.md` |
| How the canvas fits the browser window, and its size in a window | Whole-number zoom with black bars, as the original's Pixel Perfect Camera is documented to do; a window of 570 x 320 doubled while the double stays under two thirds of the screen | `screen-output.md` |
| How the port picks its master seed | A random one at start, settable (for example from the page address) so a test can fix it | `run-and-seeds.md` |
| The credits' speed | 30 pixels a second, 120 while the button is held, by time | `screens.md` part 6 |
| The credits screen's `web` and `twitter` buttons | Leave out, like the settings screen's | `screens.md` part 6 |
| The title's `version` button (opens the developer's update page) | Leave out | `screens.md` part 2 |
| Fullscreen follows the window both ways; in a browser Escape also leaves fullscreen | **Open.** No default was suggested; decide when the settings screen is built (milestone 3). Since step 8 the start screen also has a fullscreen switch. A browser always leaves fullscreen on Escape, which in the game also pauses; whether the page still sees that Escape press is not checked (not tested) | `screens.md` part 4 |
| Key O (saves a screenshot to the documents folder) | Leave out | `screens.md` part 4 |
| The endless screen's hidden "clear achievements" box and `presskit_prep` | Leave out | `screens.md` part 7 |
| The host's second ("phantom") cursor | Leave out: the game's picture covers it, it shows only over full-screen black bars | `screen-output.md` |
| The forced layout (`platover`) | Leave out: nothing reads it in this build | `screens.md` part 4 |
| `Citation` message clip: the code takes the page's clip, so a long message is not cut at 36 pixels | Keep what the code does | `desk-pictures.md` |
| Fingerprint picture's alpha-1 background; seal sheet's one-pixel drop | Keep what the code does | `fact-pictures.md` |
| The desktop original loses the current day when the game is closed (a stash is written but never read back). A tab closes easily | Copy the original first; add day-resume later if wanted. If added, note that a restore builds a new `Day` with no generator put back (`save-format.md` part 2) | `save-format.md` |
| How the port stores saves | The browser's local storage, in the port's own format keeping the save tree; reading the original's encrypted files only if you want to import real saves. A save shows its real date, so the browser clock is used | `save-format.md` |

## Answered before milestone 0 (2026-10-17, step 8)

Five questions were put to the user after the first draft of this
architecture; the user answered all five the same day.

1. **Where the browser build is served: decided by the user.** On a web
   server the user runs locally; the converted game files the port needs
   are on that server ("I will host it locally so it's fine to host the
   necessary ported game files on the web server"). Rule 1 still holds
   for git and for any public host: the files stay out of the
   repository, and a server reachable from the internet would count as a
   public host. Two practical points:
   - The browser runs a service worker (the caching, below) only on
     `https://` addresses and on `http://localhost`. On this machine
     `localhost` works as it is. Opening the server from another device
     by its network address (`http://192.168...`) needs `https://` with a
     certificate that device trusts, or the game runs without caching.
     Settle when that is wanted.
   - Milestones are tried at `http://localhost:<port>` on this machine.
2. **Which browsers: decided by the user.** Current Chrome, Edge and
   Firefox on a desktop computer. Not Safari, not phones.
3. **A start screen: decided by the user**, "with potentially other
   options for the player to adjust". Browsers do not let a page play
   sound before the player has clicked or pressed a key on it, and the
   title's rise follows the song's beat (`audio-layer.md`), so the game
   starts on that click. It is a page of our own, shown while the start
   pack loads, not one of the game's screens. *Suggested contents*
   (settle in milestone 2):
   - the load progress, then a "click to start" button;
   - music and effects volume (the same two settings as the game's own
     settings screen, stored in the same place, so both always agree);
   - fullscreen on or off (browsers allow entering fullscreen only after
     a click, so the start click is the moment to do it);
   - the picture size: the largest whole-number zoom (default, sharp
     pixels) or stretched to fill the window (like the original's
     `stretch` launch word; not pixel-exact).
4. **How Bevy is used: left to me by the user ("you decide"); decided:
   Bevy as the host, the game in a plain Rust library.** Bevy is a game
   engine for Rust: it opens the window (in a browser, the canvas, the
   drawing area of the page), reads the mouse and keyboard, and draws
   with the graphics card. It also has its own way to organise a game's
   objects (an "entity component system", ECS) and its own sound player.
   The port uses Bevy for the window, the input and the drawing, and
   writes the game itself in `pp_core`, which knows nothing of Bevy.
   Why not Bevy for everything:
   - **Order.** The original updates its objects one after another in a
     fixed order, and that order decides the random draws and the drawing
     order (`port-requirements.md`, `screen-output.md`). An ECS runs its
     update steps in an order it chooses unless each is pinned, and walks
     its objects in its own storage order. Every pin would be one more
     place for a draw to slip out of step with the original.
   - **Testing.** `pp_core` can be tested against the Python reference
     scripts with a plain `cargo test`, in seconds, without a browser or a
     graphics card.
   - **Upgrades.** Bevy changes its interface with every release (0.20 is
     current). Keeping Bevy to the host keeps those changes to one part.
   - **Sound.** Bevy's sound player loads a whole file before playing,
     so it cannot stream a song; the port's own sound player (in the
     host, through the browser's Web Audio) is needed anyway.
   What this gives up: Bevy's own object system goes unused, and the
   download carries more of Bevy than the port needs (size measured in
   milestone 0). Not chosen either: no Bevy at all (drawing with WebGL
   by hand). It would make a smaller download, but Bevy is the project's
   stated goal and also gives a native window for quick tests.
5. **Tools for milestone 0.**
   - **Downloaded 2026-10-17 with the user's go-ahead:** Bevy 0.20.0 and
     the libraries it needs for the browser build (503 packages from
     crates.io, 40 MB downloaded, 304 MB unpacked with crates.io's
     index). They are in the project's own `.cargo-home/` (gitignored),
     not the usual `C:\Users\farha\.cargo`, so nothing is written outside
     the project (`CLAUDE.md` rule 3); every `cargo` command of the port
     sets `CARGO_HOME` to that folder. Features chosen: no defaults; the
     window, rendering, sprites, PNG and WebGL2 only (the final list is in
     `port/web/Cargo.toml`; meshes and input are not compiled in yet).
     The build folder is the gitignored `/target/`: 2.3 GB after
     milestone 0 (measured; the "several GB" first written here was an
     estimate).
   - **Installed 2026-10-17 with the user's go-ahead (milestone 0):**
     `wasm-bindgen-cli` 0.2.129 from
     crates.io (the version must equal the `wasm-bindgen` library that
     came with Bevy, 0.2.129). It turns the compiled WebAssembly (the
     browser's own machine-code format) into a file plus the JavaScript
     glue a page needs. Built from source by `cargo install` into
     `.cargo-home/bin`: a few minutes to build; three programs of 4 to 9 MB,
     of which the port uses `wasm-bindgen.exe`.
   - Optional, later: `wasm-opt` from the Binaryen project on GitHub
     (about 10 to 20 MB, estimated), which makes the WebAssembly file
     smaller. The measured size is 26 MB (`milestone-0.md`), so this is
     now a real question for the user; nothing is downloaded.
   - Not needed: `trunk` (a build helper): a short build script of our
     own does the same and shows what it does. Python's own web server
     cannot answer partial requests ("Range" requests, below), so the
     local server is a short Python script of our own, no download.
   - Already on this machine, not installed by this project: `ffmpeg`
     7.1.1 (through scoop), with Vorbis and Opus encoders. It can
     re-encode the songs without any download (the songs' row above).

## The architecture (2026-10-17, step 8; taken as accepted: the user answered its questions and asked when the first build can start)

### The parts

The port is a Rust "workspace" (one folder holding several Rust
libraries, called crates, built together) in `port/`, plus the page's own
files and the asset preparation:

| Part | Folder | What it is | Knows about |
|---|---|---|---|
| The game core | `port/core` (crate `pp_core`) | All of the game: the random generators, the data file readers, travelers, the booth's rules, the desk, speech, the border scene, the night, news, screens, buttons, text and page layout, pictures and their operations, the game-side audio layer (`app.aud`), saves as fact lists, screen changes. Each frame it takes the input and returns the finished 570 x 320 picture (it draws its own quads by software, decided 2026-10-18) and the sound commands | Nothing outside itself: no Bevy, no browser |
| The host | `port/web` (crate `pp_web`) | The Bevy app: the canvas and its fit to the window, the mouse and keys turned into the core's input, showing the core's picture, the sound player (32 sources, like `UnityPlatformAudio`), saves and settings in browser storage, loading the packs | Bevy, the browser (through Rust's `web-sys` bindings) |
| The page | `port/www` | `index.html`, the loader script (the start screen: load progress, "click to start", the player's options) and the service worker (below). Our own, small, plain JavaScript | The browser |
| Asset preparation | `scripts/build_assets/` (Python) | Turns this machine's game files into the packs the page loads: pictures, fonts, data files with the English pack applied (decision 3 above), effects and songs in the browser's formats, and a list of every file with its content fingerprint. Builds on the extraction scripts that already work (`scripts/extract`, `scripts/unity`, `locpack.py`) | The game files |

The output of the build (the WebAssembly, the page, the packs) goes into
`build/`, which holds game assets and is **added to `.gitignore`** before
anything is written there (rule 1).

Why the asset preparation stays in Python: the extraction (the archive's
decryption, UnityPy, the FMOD decoder) already works and is checked in
Python; it runs once on this machine, not in the browser. The game
reads the data files at run time from the packs, so no game text or
picture is written into the Rust code.

### One frame

1. The host collects the input since the last frame (the left mouse
   button, the pointer in game pixels, the keys the game reads;
   `input-handling.md`).
2. The host runs the core's fixed step of 1/60 s as many times as real
   time asks (decision 1 above; the browser calls the page once per
   screen refresh, which can be 60, 144 or another rate). The speaker's
   real-time clock gets the real elapsed time, uncapped
   (`audio-layer.md`).
3. The core builds the quad list in drawing order (layers lowest first,
   then the order visuals were added) and draws it into one 570 x 320
   picture cleared to black, with nearest-pixel reads and ordinary alpha
   blending (`screen-output.md`, "For the port"; `port/core/src/raster.rs`,
   decided 2026-10-18; the first draft had the host do this on the
   graphics card). It also returns the sound commands (start, stop,
   volume, pause).
4. The host copies the picture to the graphics card and shows it at a
   whole-number zoom on black.
5. The host carries out the sound commands and reports each sound's
   position back for the next frame (the music's beat comes from the
   song's position; `audio-layer.md`).

### How exactness is checked

- The core is tested natively (`cargo test`, no browser) against the
  Python reference scripts, which already match the running game for
  days 1 to 4 of one seed (`comparing-with-the-game.md`). The reference
  writes its results (travelers, draws, layouts, previews) into a
  gitignored folder; the Rust tests read them. A check that compares a
  quad list or a picture can compare pixel by pixel with the reference's
  previews (`text.py`, `pages.py`, `nightpics.py`, `host.py`).
- Exactness rules: `port-requirements.md`.
- The look and feel: the milestones below, in the browser.

### Loading and caching

Terms: a **service worker** is a small script the browser keeps for a web
address; it sits between the page and the network and can answer the
page's requests from the browser's own storage. **Cache Storage** is
that storage (files kept by the browser for the address). A **Range
request** asks for part of a file; a browser's sound player uses them to
play a file while it downloads. A **content fingerprint** is a short code
computed from a file's bytes, put in its name, so a changed file gets a
new name and an old copy is never mistaken for it.

Sizes (measured on this machine, before any browser conversion): the
pictures, fonts and data are 3.2 MB as the game stores them (`Art.dat`);
the three songs are 6.5 MB as the game stores them (Vorbis, 1.7 to
2.8 MB each); the 108 effects are 21 MB as WAV, smaller once compressed
(their compressed size depends on the format decision). The WebAssembly's
size was measured in milestone 0: 26.3 MB as built (5.4 MB compressed
with gzip), after the 37 MB of debugging names were removed from a 63.5
MB first build (`milestone-0.md`).

What the page loads:

1. **The start pack**, before the first screen: the page, the
   WebAssembly, all pictures, fonts and data, and the effects the title
   and menu screens use. The start screen shows the progress meanwhile.
2. **The rest of the effects**, in the background while the player is on
   the title screen or the intro. The first day waits for them only if
   they have not arrived (expected never, on a normal connection; not
   tested).
3. **The songs**, streamed and kept from **one download**: on the first
   visit the browser's own sound player asks for the song and the service
   worker fetches the whole file from the network once. As the data
   arrives the service worker splits it in two: one copy goes on to the
   sound player, which starts playing on the first part, and the other is
   written into Cache Storage. When the download ends, the kept copy is
   complete. If it is cut off (the tab closed mid-download), the partial
   copy is thrown away and the next visit streams the song again. The
   song is played into the same volume control as the effects. On later
   visits the service worker answers the song's requests, partial ones
   included, from storage.
   (The first draft of this file had the service worker download each song
   a second time, in the background, instead of keeping what was
   streamed. The user asked why; corrected 2026-10-17. The draft's reason
   was caution: a sound player asks for parts of a file, and on a first
   visit the service worker answers with the whole file as one stream.
   Chrome, Edge and Firefox are expected to accept that, since the port
   only plays a song from its start; not tested. If one of them refuses,
   the second download is the fallback.)

What is kept, and for how long:

- Every file the page loads (the page, the WebAssembly, the packs, the
  songs) is kept by the service worker. On a later visit the page starts
  from storage without asking the network for any of it, except one
  small check for a new version.
- Each build writes a file list with fingerprints. When a new build is
  put up, the service worker of a returning player sees the new list,
  downloads only the changed files in the background, and switches to
  them on the next visit; the old copies are then deleted.
- The page asks the browser to keep its storage ("persistent storage").
  A browser may still clear it (low disk space, the player clearing site
  data, a private window). Then the page simply loads from the network
  again, like a first visit.
- Saves and settings are kept separately from the cache (decided above:
  the browser's local storage), so clearing or updating the cache does
  not touch them.
- A service worker only runs on `https://` addresses and on
  `http://localhost`. Testing from another device at this machine's
  network address (`http://192.168...`) would run without it.

Risks, to be checked in milestone 2 (not tested):

- Whether each browser's sound player accepts the whole-file answer on a
  first visit (item 3 above). Checked with the developer tools' network
  panel: one request per song, and the song in Cache Storage afterwards.
- A song loop needs the song's start again. On a first visit the loop
  comes after the whole song has played, so after the download has ended
  (`Theme` is 2 MB and 104 s long), and the service worker answers it
  from storage.
- A song loop in the browser's sound player may have a short gap at the
  loop point. If it is audible: once a song is in storage, decode it in
  full and loop it without a gap.
- The music's beat follows the song's reported position. On a slow first
  visit the song can pause to wait for data; the title's rise then waits
  with it, which is the same rule the original follows.

## Milestones (2026-10-17, step 8; taken as accepted, as above)

Each milestone ends with a build you open in the browser at
`http://localhost:<port>` and try. Each has its own doc section, its
`MODLOG.md` entry and, when asked, its own commit. After each, I give
the command to run and a list of what you should see. A milestone is not
started before the previous one is accepted by you.

For trying later parts of the game without playing up to them, the page
takes test settings in its address, for development only: the master
seed (decided above), and a jump to a given day with the facts the
original's own debug jump fakes (`save-format.md`, "The debug jump to a
day").

| # | Name | What you can try | What it builds | Rests on |
|---|---|---|---|---|
| 0 | An empty page | The page opens on a black 570 x 320 picture at a whole-number zoom, with a test pattern and a frame counter; resizing the window keeps the zoom whole. Reload with the network switched off in the browser's developer tools: it still opens | The workspace, the build script, the local server, the service worker, the canvas fit, the fixed step | `screen-output.md` |
| 1 (split into 1a and 1b, 2026-10-18) | Pictures and text | **1a:** font test pages (every font id and every font sheet, 35 pages, arrow keys change page), identical to the Python reference. **1b:** a still of the title screen (logo and buttons, not clickable yet), the same pixels as the Python reference's preview of the same screen; the quit and version buttons are left out (quit is already decided against; the version text is unread) | The asset preparation, the start pack, the quad list drawn exactly, `app.vis` text and pictures | `text-drawing.md`, `vis-basics.md`, `screens.md` part 2, `fonts.md` |
| 2 | Sound | The start screen with its options and "click to start"; `Theme` plays at once on a first visit, while the developer tools show it still downloading; afterwards it is in Cache Storage, and an offline reload plays it. A test page plays any effect | The sound player, the effects, the song stream and background save, the volume rule | `audio.md`, `audio-layer.md` |
| 3 | The title screen alive | The game's own cursor; buttons with their pressed look and sounds; the title rising with the music; the settings and pause screens with working volumes; the intro pages; fades between screens | Input, buttons, `Menu`, screen changes, the settings file | `input-handling.md`, `buttons.md`, `screens.md` parts 1 to 5, `save-format.md` part 2 |
| 4 | The booth, no travelers | Day 1's screen: the booth, the desk and console, the border scene's still picture; dragging a passport and the rulebook, docking, the stamp bar, the clock; their sounds and the ambient loops | The desk, desk movement, the stamp bar, the booth's ambient | `booth-layout.md`, `desk-pictures.md`, `desk-movement.md`, `page-layout.md` |
| 5 | The first travelers | Day 1 played with the booth's rules: travelers come in, speak, hand papers; stamping, giving back, the citation slip. For a fixed seed the same travelers as the reference (and so as the game) | Traveler creation, the booth's state machine (read first), speech, judging | `traveler-creation.md` and its neighbours, `speech.md`, `player-actions.md`, `responses-and-events.md` |
| 6 | A whole day and night | The border scene's line walking and calling in; the day ending; the news, the night screen and its budget; saving; the load screen; the next day | The border scene's normal cycle, news, night, saves | `border-figures.md`, `border-scene.md`, `newspaper-picture.md`, `night.md`, `save-format.md` |
| 7 | The booth's later tools | The inspect mode, interrogation, fingerprints, searching, detaining, the bulletin, the drawer, the later papers | The rest of the booth | `inspect-mode.md`, `player-actions.md`, `fact-pictures.md` |
| 8 | The border's dangers | Attacks, the rifles, the bomb, the poison, the flash to the title, the shake | The rest of the border scene, screen effects | `border-shooting.md`, `screens.md` part 11 |
| 9 | Endings, credits, endless | The endings and their statistics page, the credits, the endless code box and the endless runs with their best scores | The remaining screens | `screens.md` parts 5 to 7, `endless-mode.md`, `ends-xml-format.md` |
| 10 | Checking against the original | The longer comparison run and the watch lists (both need your go-ahead to run the game) | Fixes only | `comparing-with-the-game.md`, `PROGRESS.md` kind 3 |

Milestones 4 and 5 are the largest; each may be split into smaller
ones when it is planned, so there is always something to try within a
session or two.
