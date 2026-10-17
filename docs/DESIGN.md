# Design decisions for the port

**Status (2026-10-17): only the decisions list is written.** The architecture
(how the Rust and Bevy code is laid out) is not written yet; it comes in step 8
(`PROGRESS.md`). This file started from the sorting of the open questions
(step 7); every item here is from that sorting, and the open-question list in
`PROGRESS.md` points here for the `C` kind.

A decision is **decided** (the user said so, with the date), **suggested** (my
default, not confirmed: say yes, or change it) or **open**.

## Decided by the user

| Decision | Date | Detail |
|---|---|---|
| English only: no Language row, no language chooser, no age rating | 2026-10-16 | `screens.md` part 7; English still loads its own pack (`language-pack.md`) |
| No leaderboards. The local best score per course and style is kept | 2026-10-16 | `screens.md` part 7 |
| The settings screen's `web` and `twitter` buttons are left out | 2026-10-14 | `screens.md` part 4 |
| No quit option: neither the pause screen's QUIT nor the title's quit button | 2026-10-14 | `screens.md` part 4 |

## Needed before the first Rust code

These change how the first code is written, so they come first.

1. **Frame time.** The original steps by real elapsed time, capped at 0.1 s a
   frame, at 60 frames a second on most screens (65 on the others, never above
   70). A few things move by frame (the credits). Its test player uses a fixed
   1/20 s. (`border-view.md`, "The frame rate".)
   *Suggested:* a fixed step of 1/60 s, with the browser's frame timer feeding
   it, and per-frame quantities kept as in the original.
2. **The random sequence.** In the original, redrawing a page repeats its
   random draws, so which pages the player looks at can change later travelers
   (`desk-drawing-draws.md`); the border scene's generator draws follow real
   time (standing figures draw every 2 to 4 seconds, an attack starts after
   `6 + 4 x r` seconds; `border-figures.md`, `border-scene.md`).
   *Suggested:* copy the **booth side exactly** (traveler creation, desk draws,
   speech): the reference matches the game on it and it is the method for
   checking the port. For the **border scene** copy the draw order and the
   delays, but not the dependence on real time (that follows from decision 1).
3. **The English pack** (`language-pack.md`). *Suggested:* apply it once, when
   the assets are prepared (`scripts/reference/locpack.py` already does it),
   not at run time. Either way the 23 changed texts and the picture that is
   only in the pack must come out.

## Can wait until the feature is built

| Decision | Suggested | Where from |
|---|---|---|
| How the browser build gets the songs (62 MB as WAV) | Rebuild the stored Vorbis data into `.ogg` files without re-encoding, or re-encode; both need a tool download (your go-ahead, `CLAUDE.md` rule 6). The effects are 21 MB as WAV | `audio.md` |
| The ambient loop that plays at full level at a day's start, until first faded in (by the code; not heard) | Keep it, since it is what the code does. Hear it in the game first if you want to be sure | `audio-layer.md` |
| How the canvas fits the browser window, and its size in a window | Whole-number zoom with black bars, as the original's Pixel Perfect Camera is documented to do; a window of 570 x 320 doubled while the double stays under two thirds of the screen | `screen-output.md` |
| How the port picks its master seed | A random one at start, settable (for example from the page address) so a test can fix it | `run-and-seeds.md` |
| The credits' speed | 30 pixels a second, 120 while the button is held, by time | `screens.md` part 6 |
| The credits screen's `web` and `twitter` buttons | Leave out, like the settings screen's | `screens.md` part 6 |
| The title's `version` button (opens the developer's update page) | Leave out | `screens.md` part 2 |
| Fullscreen follows the window both ways; in a browser Escape also leaves fullscreen | Decide when the settings screen is built | `screens.md` part 4 |
| Key O (saves a screenshot to the documents folder) | Leave out | `screens.md` part 4 |
| The endless screen's hidden "clear achievements" box and `presskit_prep` | Leave out | `screens.md` part 7 |
| The host's second ("phantom") cursor | Leave out: the game's picture covers it, it shows only over full-screen black bars | `screen-output.md` |
| The forced layout (`platover`) | Leave out: nothing reads it in this build | `screens.md` part 4 |
| `Citation` message clip: the code takes the page's clip, so a long message is not cut at 36 pixels | Keep what the code does | `desk-pictures.md` |
| Fingerprint picture's alpha-1 background; seal sheet's one-pixel drop | Keep what the code does | `fact-pictures.md` |
| The desktop original loses the current day when the game is closed (a stash is written but never read back). A tab closes easily | Copy the original first; add day-resume later if wanted. If added, note that a restore builds a new `Day` with no generator put back (`save-format.md` part 2) | `save-format.md` |
| How the port stores saves | The browser's local storage, in the port's own format keeping the save tree; reading the original's encrypted files only if you want to import real saves. A save shows its real date, so the browser clock is used | `save-format.md` |
