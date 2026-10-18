# Milestone 0: an empty page

Built 2026-10-17. The first browser build of the port: a Bevy window in a
browser canvas showing a 570 x 320 test card at the largest whole-number
zoom, a fixed 1/60 s step, a service worker that keeps the build for
offline use, and the build and server scripts. No game content. The plan
is the milestone's row in `DESIGN.md` ("Milestones").

## How to try it

Two commands, in this order, from the project folder. The first builds
(the first build takes about 5 minutes and uses about 2.3 GB in `target/`;
later builds reuse it):

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080` in Chrome, Edge and Firefox. You should see:

- A black window with a framed test card in the middle: a one-pixel white
  frame on all four edges, a faint grid, a grey ramp (16 steps), colour
  bars, a flat grey patch beside a one-pixel black and white checker, two
  groups of one-pixel lines, and a yellow square moving one pixel per
  step along a track near the bottom.
- Two numbers at the top left: **white = fixed steps** run so far,
  **yellow = pictures drawn**. On a 60 Hz screen they climb together; on
  144 Hz the yellow one climbs about 2.4 times faster.
- Resizing the window: the picture stays a whole-number multiple of 570 x
  320 (every game pixel the same square block), centred, black around it.
  Below 570 x 320 it is cropped, not shrunk.
- Reload once, then switch the network off in the developer tools
  (Network tab, "Offline") and reload: it still opens.

Stop the server with Ctrl+C. To start over with no service worker or
stored files, open `http://localhost:8080/?nosw` (removes both, then
reloads without registering; open the plain address after to register
again). `python -I scripts/build_web.py --no-cargo` repackages without
compiling; `--debug-names` keeps function names in the WebAssembly.

## What was built

| Part | Where | Notes |
|---|---|---|
| Workspace | `port/Cargo.toml`, `port/.cargo/config.toml` | Crates `pp_core` and `pp_web`; one build folder, `target/` at the project root. Release profile tuned for size (`opt-level "s"`, thin LTO, `panic = "abort"`) |
| Core | `port/core/src/` | `screen.rs`: 570 x 320 and `fit()`, the largest whole-number zoom for a window, centred, in physical pixels. `stepper.rs`: the fixed step. `testcard.rs`: the test card and a 3 x 5 digit font of the port's own. 15 tests (`cargo test -p pp_core`) |
| Host | `port/web/src/main.rs` | Bevy 0.20 with only the window, rendering, sprite, PNG and WebGL2 features. The test card is written into one 570 x 320 sRGB texture each frame and shown on one sprite with nearest-pixel reads |
| Page | `port/www/index.html`, `port/www/sw.js` | Plain JavaScript loader and service worker |
| Build | `scripts/build_web.py` | cargo, `wasm-bindgen` (name section removed), fingerprints, `files.json`, the build code baked into `sw.js` |
| Server | `scripts/serve.py` | Listens on 127.0.0.1 only; answers Range requests; WebAssembly type; fingerprinted files `immutable`, the rest `no-cache` |
| Check | `scripts/checks/web_offline_check.mjs` | Drives headless Edge or Chrome (throwaway profile in `build/`): picture size and place, pixel values, resizes, service worker, offline start |

### Decisions made while building

- **The frame counter is drawn as blocks** by the port's own 3 x 5 font in
  `pp_core`, not with Bevy's text. Bevy's text feature is not compiled
  in, so the download is smaller, and the pixels are ours.
- **The zoom is computed in physical pixels** (what the screen really
  shows), not the browser's scaled ones. On a screen scaled to 200 % the
  canvas is twice the window's CSS size, and a game pixel is still an
  exact block.
- **The step is capped at 0.1 s of real time per frame** (6 steps), as the
  original caps a frame at 0.1 s (`border-view.md`, "The frame rate").
  The accumulator counts integers, so it never drifts. With the browser
  calling at 60 Hz the step count can wobble by one between frames
  (0 or 2 steps in a frame); nothing smooths that. Not looked at over a
  long run.
- **One cache per build, served as a whole.** The worker serves the page,
  files.json and every file from its own build's cache, so a page and its
  files always agree. A new build changes `sw.js` (the build code), the
  browser installs the new worker in the background, copies unchanged
  fingerprinted files from the old cache and downloads the rest, and it
  starts serving on the next visit after every tab of the old one is
  closed. The old cache is then deleted.
- **A sRGB texture.** The card's bytes are stored as an sRGB texture; the
  graphics card decodes on reading and Bevy's output encodes again.

## What was measured

All on this machine, 2026-10-17.

| What | Value |
|---|---|
| Release build, first time (about 400 crates) | 5 min 25 s |
| `target/` after it (release build for the browser, plus the core's native test build) | 2.3 GB (the earlier "several GB" was an estimate) |
| `.cargo-home/` | about 410 MB (was 304 MB; the difference is mostly the wasm-bindgen CLI's own libraries) |
| WebAssembly, first build | 63.5 MB: 22 MB code, 3.8 MB data, **37 MB name section** (function names for debugging) |
| WebAssembly, names removed (`--remove-name-section`) | **26.3 MB**; 5.4 MB with gzip (level 9). The local server sends it uncompressed |
| JavaScript glue | 102 KB (14.6 KB gzip) |
| Page and service worker | 2.8 KB each |
| Frame time of the page's own code in the preview pane | 6 to 7 ms per frame (testcard drawn on the CPU, 570 x 320, with the upload), at a 1444 x 1458 canvas |

Not yet tried to make the WebAssembly smaller: `wasm-opt` (a download),
`opt-level "z"`, fewer Bevy features, a smaller card drawn without the
CPU copy. DESIGN.md's size note (milestone 2 loads this as part of the
start pack) now reads 26 MB; it matters for a first visit only, and the
service worker keeps it afterwards.

## What was checked, and how

By `scripts/checks/web_offline_check.mjs` (headless Edge 3 runs out of
3 on the final script; page at 1400 x 900, scale 1):

- Picture 1140 x 640 (zoom 2) at (130, 130): the centred position.
- Pixel values read back from the canvas: grey patch 128, ramp step 7
  = 119, red 255,0,0: no colour change between the card's bytes and the
  canvas.
- Resized to 1800 x 1000 (zoom 3 at 45, 20), 1000 x 700 (zoom 1 at 215,
  190), 1200 x 1500 (zoom 2 at 30, 430), 1710 x 960 (zoom 3 at 0, 0): the
  zoom and place each time matched `pp_core::screen::fit`.
- A first visit installs the service worker, which stores `index.html`,
  `files.json`, the glue and the WebAssembly; after a reload with the
  network switched off (Chrome's own offline setting) the page starts and
  draws the same picture.
- `cargo test -p pp_core`: 15 passed.

In the app's preview pane (a Chromium-based browser pane): the page
renders the card correctly at the physical-pixel zoom (scale 2: canvas
1444 x 1458, picture 1140 x 640, zoom 2) with the same exact pixel
values. The pane does not allow service workers, and it drew only about 1
frame a second (its own page of nothing but a frame counter got 61 a
second), so no frame rate was measured there.

## Not tested

- **The frame rate and the step's evenness on a real screen.** Nothing
  here ran at 60 Hz in a visible window. Watch the yellow square: it
  should move smoothly, and white and yellow numbers should climb
  together at 60 Hz.
- **Firefox, and Edge or Chrome as a visible window.** The check ran
  headless Edge (the same engine as Chrome). Firefox was not run at all.
- **A service worker update** (put up a second build, visit again): the
  code is written (copy unchanged files, delete the old cache on
  activation) but never run.
- **The first-visit double fetch.** On a first visit the page and the
  worker's install both ask for the big files. The server marks the
  fingerprinted files `immutable`, so the second request should come from
  the browser's own cache; the server's log shows the number of requests
  if you want to look.
- **Any browser on another device** (no service worker on a plain
  `http://192.168...` address; DESIGN.md, "Answered before milestone 0").
- **Native `cargo run` of the host** (not tried; the host is a plain Bevy
  app and may work).
- **The WebAssembly holds this machine's folder names** (874 occurrences
  of the user name in file paths, from panic messages). `build/` is
  gitignored and the files stay on the local server; to remove them for
  any other use, pass Rust's `--remap-path-prefix`. Not done.

## Dead ends, and things that looked wrong

- The first offline test runs failed after the resize steps were added.
  The cause was the test, not the port: headless browsers can count the
  page as not visible, and then `requestAnimationFrame` never fires. Fixed
  in the check with `Emulation.setFocusEmulationEnabled` and
  `Page.bringToFront` (3 of 3 runs passed afterwards; 3 of 3 had failed
  before with the same port build). The same page ran at 1 frame a second
  in the app's preview pane for a similar reason (the pane throttles), so
  the frame rate is a question for a real window.
- `cargo check --offline` failed once with "failed to download
  accesskit_consumer 0.38.0". The throwaway manifest that fetched Bevy on
  2026-10-17 is gone, so its exact features are unknown; the final ones are
  in `port/web/Cargo.toml`. The cause was not found: a following `cargo
  fetch` printed nothing and the number of stored crate files did not
  change (448 before and after), and every later build, run online,
  worked. Whether any Bevy crate was downloaded in this step is therefore
  not known; the folder grew from 304 MB to about 410 MB, which the
  wasm-bindgen CLI's libraries (installed this step) account for at least
  in part.
