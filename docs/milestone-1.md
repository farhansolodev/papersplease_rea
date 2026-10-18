# Milestone 1: pictures and text

Split in two on 2026-10-18 (the user accepted the plan): **1a, the font test
pages** (built, below) and **1b, the title screen as a still** (built
2026-10-18, at the end of this doc). The plan is the milestone's row in `DESIGN.md` ("Milestones").

## 1a: the font test pages

Built 2026-10-18. The page loads a start pack, decodes the twelve font
sheets, lays text out with the game's own rules (`fonts.md`,
`text-drawing.md`), draws the quads by software and shows the 570 x 320
picture at a whole-number zoom, as milestone 0 did. **The pixels are
identical to the Python reference's pages**: that proves the port equals
the reference, not the game (nothing here was compared with the running
game).

### How to try it

From the project folder (the first command takes several minutes if the
Rust code changed; it also makes the start pack):

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080/?page=fonts` (the font pages were the
default page until 1b; now the title screen is). You should see:

- **35 pages.** The first 16 are one per font id, in `Fonts.xml` order
  (`tiny`, `small_harsh`, ..., `title_news`). The other 19 show each of
  the 12 font sheets, 570 x 320 at a time, row by row (a sheet that is
  592 x 576 takes four pages).
- **A text page** has a label (font id, file, line height, ascent, capital
  height, descent, space width, "page N of 35"), then samples: capital
  letters, small letters, digits and punctuation, a missing-letter
  example (the two boxes after "box"), a rounded and a plain background,
  half-transparent text over white (left); a paragraph wrapped at 270
  pixels with a long word cut with a hyphen, a centred and a right-aligned
  block, a text at a half-pixel position and a three-line text with
  3 pixels of line spacing (right).
- **Left and right arrow keys** go to the previous and next page (click
  the picture first if the keys do nothing). `&p=N` after `?page=fonts`
  opens page N, counting from 0 (`http://localhost:8080/?page=fonts&p=14`).
- `?page=testcard` is milestone 0's test card.
- On the page for `digits` (only `.` and `0` to `9`) every letter but the
  digits is a box: that is the game's rule for a missing letter.
- The "Fractional 0.5" line looks damaged (an "r" like a hyphen): see
  "Findings", below. It is expected.

### What was built

| Part | Where | Notes |
|---|---|---|
| Start pack builder | `scripts/build_assets/build_pack.py` | One file (`start.pack`, 2.0 MB) holding `data/Fonts.xml`, the 12 `.fnt` files, the 12 sheets (PNG kept as PNG) and `strings.json` (`wrap_hyphen`). Format in the script's header. Written to `build/` only. `build_web.py` calls it and gives it a fingerprinted name; `files.json` has a `pack` entry; the service worker stores it with the rest |
| Pack, pictures, XML | `port/core/src/pack.rs`, `picture.rs`, `xmlscan.rs` | The pack reader; PNG decoding (the `png` crate, already part of the build through Bevy, so no new download); a small reader for the flat XML the font files use |
| Fonts | `port/core/src/font.rs` | `.fnt` reading, measurements, `Font.split`, following `fonts.py` step by step |
| Text | `port/core/src/text.rs` | `Text.buildTiles`, following `text.py` |
| Drawing | `port/core/src/raster.rs` | Quads into the 570 x 320 picture: pixel coverage, nearest-pixel reads, the quad shader's blend, 8-bit rounding, all as `host.py` has them, in `f64` |
| Pages | `port/core/src/pages.rs` | The page definitions (the port's own test material) and the gallery of fonts and pictures |
| Host | `port/web/src/main.rs`, `port/www/index.html` | The loader fetches the pack and the address's settings and hands them over as `window.ppConfig`; the host reads it, shows the page, switches page on the arrow keys |
| Reference | `scripts/reference/fontpage.py` | The same 35 pages from `fonts.py`, `text.py` and `host.py`, written as raw pictures to `extracted/previews/m1/` (gitignored); about 3 minutes |

### Decisions

- **Software drawing in `pp_core`** (the user's decision on 2026-10-18; in
  `DESIGN.md`). The host only shows the picture.
- **All drawing arithmetic in `f64`, in the reference's order.** The game
  and the graphics card use single precision; where the two could differ
  (an exact tie at 8-bit rounding) was not found in these pages. Noted
  for the half-pixel case below.
- **PNG decoding in the core**, so `cargo test` loads the same pack the
  browser does.
- **The English language pack is not applied to the pack's strings, and
  does not need to be for `Text.xml`.** Only `wrap_hyphen` is in the pack.
  `locpack.py` (run 2026-10-18 on `en.zip`) lists the 23 texts the English
  pack changes: 18 in `Travelers.txt`, 2 in `Facts.xml`, 3 in
  `Endlesses.xml` and none in `Text.xml`. So the strings 1b needs
  (`menu_story`, `menu_endless`, `created_by`) can be taken from
  `Text.xml` as they are; applying the pack matters only when the
  traveler, facts and endless files go into a pack.
- **Quit and version:** the plan said these two buttons would be left out
  of the title still for now. The quit button was already decided against
  by the user on 2026-10-14 (`DESIGN.md`, "Decided by the user"); the
  version button stays out until `decoratedVersion` is read.

### What was measured

All on this machine, 2026-10-18.

| What | Value |
|---|---|
| WebAssembly | 26,389,052 bytes (5.47 MB gzip), 70 KB more than milestone 0's 26.32 MB |
| Start pack | 2,027,525 bytes (463 KB gzip) |
| JavaScript glue | 102 KB |
| `cargo test -p pp_core` | 44 unit tests (0.1 s) and the reference test over all 35 pages: 5.7 s in a debug build, 1.2 s in a release build (reading the files and decoding the sheets included) |
| The release build's time | not known: the log said 254 minutes, which cannot be right (the computer was suspended during it); milestone 0's was 5 min 25 s |
| Time to draw one page in the browser | **not measured** |

### What was checked, and how

- `cargo test -p pp_core` (needs the two gitignored inputs; without them
  `fontpage.rs` says "SKIPPED" and passes): 44 unit tests (the pack, XML
  reading, font measuring and line breaking, text layout, the drawing
  rules, the page parts, plus milestone 0's) and `tests/fontpage.rs`: **all
  35 pages the core draws are byte for byte the reference's**.
- `scripts/checks/web_offline_check.mjs` in headless Edge (passed once on
  the final script, after a first run that failed on the test's own
  mistake, see "Dead ends"): the milestone 0 checks as before, then
  `?page=fonts&p=4` at 570 x 320: **the whole canvas read back from the
  browser equals the reference's page 4, byte for byte**. The same for
  page 5 after pressing ArrowRight, page 4 after ArrowLeft, page 3 after
  another ArrowLeft, pages 16 and 34 (font sheet parts), and page 34 again
  after reloading with the network switched off (served by the service
  worker, the pack included).
- A look in the app's preview pane at page 14 (`title_thick`): it renders
  as the Python pictures do.

### Findings

- **A half-pixel position damages letters under the assumed card rule.**
  The "Fractional 0.5" line (x + 0.5, y + 0.5) comes out with wrong rows
  in some letters, because each pixel centre then maps exactly onto a
  boundary between two texels. Written up in `screen-output.md`, "Where a
  fractional position lands". If the game places any text at a half
  pixel, the real card's choice matters: compare in milestone 10. Not
  known whether the game does.
- **`Font.split` can loop for ever in the reference** when a word is as
  wide as the limit and not even one letter plus the hyphen fits.
  Written up in `fonts.md`. The port ends it by taking one letter; no
  game text is known to reach the case.
- **Two presses of the same key inside one frame count as one** (Bevy's
  `just_pressed`). The game's own input rules (`input-handling.md`) are a
  later milestone; this only affected the test.

### Fix after 1a: browser keys and right click (2026-10-18)

The user could not use browser shortcuts (F5, F12, Ctrl+R) or right-click
on the page. Cause, from Bevy 0.20.0's source: the window setting
`prevent_default_event_handling` was `true` (Bevy's default, which
milestone 0 had copied), and Bevy documents it as blocking exactly those
hotkeys; winit's web code calls `preventDefault` on the canvas's key,
wheel and context-menu events while it is set. Now `false`
(`port/web/src/main.rs`). Check 1c in `web_offline_check.mjs` sends F5,
F12, Ctrl+R and a context-menu event to the canvas and reads
`defaultPrevented`: all four `true` with the old setting (check failed),
all four `false` with the new one. The user tried the page after the fix
(2026-10-18).
For later: when the game takes keys (Space, arrows, Tab), the browser's
own action for them (scrolling, moving focus) may need stopping for those
keys only, in the page's script, not for all keys.

### Not tested

- Anything against the running game (the references are built from the
  documents; milestone 10).
- The drawing time in a real browser window, and a smooth frame rate. The
  page is drawn again only when the page changes, so nothing here would
  show a slow frame.
- Firefox, and Edge or Chrome as a visible window by hand.
- Whether the pack's PNG decoding gives exactly the pixels Haxe's PNG
  reader gives for the game (palette pictures, transparency): the
  reference reads the sheets with Pillow, the port with the `png` crate,
  and the two agree on all 12 font sheets (one of them, `Digits`, is a
  palette picture), but neither is the game's own reader.
- A service worker update to a new build (still as in milestone 0).

### Dead ends

- The browser check failed once at "page 3 after two ArrowLeft": the two
  key presses were sent too fast, and the host counted them as one. The
  check now waits for each page. (Not a port problem; see "Findings".)

## 1b: the title screen as a still

Built 2026-10-18. The page shows the title screen as it rests once the
title has risen: logo, STORY, ENDLESS, the settings button and the credit
line, nothing clickable yet. **Its pixels are identical to the new Python
reference's**, which is built from the code reading. Like 1a, that proves
the port equals the reference, not the game: nothing here was compared
with the running game.

### How to try it

```
python -I scripts/build_web.py
python -I scripts/serve.py 8080
```

Then open `http://localhost:8080` (the title is now the default page;
`?page=fonts` and `?page=testcard` still work). You should see, on black:

- the "PAPERS, PLEASE" logo with the eagle, centred, near the top;
- **STORY** and **ENDLESS** in grey-green, each over a dotted line,
  centred, one under the other low on the screen;
- a round wrench button in the bottom left corner;
- "created by Lucas Pope" in small letters, centred at the bottom.

Clicking does nothing yet, and there is no music or rising animation
(milestone 2 and later). The reference picture, enlarged three times, is
`extracted/previews/m1b/title_x3.png` (made by the reference script,
below; gitignored).

### What was built

| Part | Where | Notes |
|---|---|---|
| Reference | `scripts/reference/titlescreen.py` | Builds the screen's 36 quads from the code reading and draws them with `fontpage.py`'s rules; writes `extracted/previews/m1b/title.rgba`, `title.png` and `title_x3.png` (gitignored); about 2 seconds |
| Pack | `scripts/build_assets/build_pack.py` | Adds `pictures/Title.png`, `pictures/PushButton.png`, `pictures/SettingsButton.png` and the texts `menu_story`, `menu_endless`, `created_by` to `strings.json`; the pack is now 2,030,052 bytes (29 files) |
| Core | `port/core/src/title.rs`, `pages.rs`, `pack.rs` | The title's quads (`title::build`) and drawing (`title::draw`); the gallery now also loads the pack's `pictures/` and keeps `strings.json`; the pack can list its files |
| Host and page | `port/web/src/main.rs`, `port/www/index.html` | `?page=title`, the default, drawn once |
| Checks | `port/core/tests/title.rs`, `scripts/checks/web_offline_check.mjs` (step 1a) | The core's title against the reference, byte for byte, in `cargo test` and in headless Edge |

### Where everything sits (desktop, from the code)

All read from the `TitleScreen` constructor (`0x180673be0`), its `update`
(`0x180676bc0`), `Menu.addPushButton`, `Menu.addImageButton`,
`Menu.applyCenterY` and `GameScreen.makePushButton` in
`decompiled/all/play_screen.clean.c`; the button rules are in
`buttons.md`, the layout values in `booth-layout.md`.

| Thing | Picture | Place (x, y) | Text |
|---|---|---|---|
| Screen fill | white pixel, black | whole screen (size inferred; it changes no pixel) | |
| Logo | `Title.png`, 315 x 197 | (127, 28): floor(285 - 157.5), `titleLogoTop` | |
| STORY | `PushButton.png` rows 0-18 | (220, 236) | `ui_large`, 0xff556855, centred: floor(64.5 - width / 2), floor(9.5 - 20 / 2) = -1 |
| ENDLESS | the same | (220, 260) | the same |
| Settings | `SettingsButton.png` rows 0-28 | (10, 281): 10, 320 - 10 - 29 | |
| Credit | a 140 x 12 black picture | (215, 298): floor(285 - 70), 320 - 12 - 10 | `regular`, 0xff556855, centred in 140 x 12 |

At rest the container that holds all of this is at y 0 (`update` puts it
there when the music is not playing, and after the rise), and the logo at
`titleLogoTop` (with music it bobs 5 pixels lower once a bar; not shown).

**The gap between STORY and ENDLESS is 5 pixels, not 10.**
`Menu.applyCenterY` makes the column (n - 1) x `menuItemPaddingY` plus the
buttons' heights high (here 10 + 38 = 48), but then shares the spare room
out by the number of buttons, n, not n - 1: floor((48 - 38) / 2) = 5. The
first button's top is (int)(260 - 48 / 2) = 236, the second 236 + 19 + 5 =
260. Read from the decompiler's output only (not checked in the
instructions); a screenshot of the real title screen would settle it (the
two dotted lines would be 24 pixels apart, top to top).

The ui_large font's line is 20 pixels high, one more than the button's
19-row picture, so the button text's box starts one pixel above the
button.

### Decisions

- No quit button (decided by the user on 2026-10-14) and no version
  button (its text, `Platform.decoratedVersion`, is not read; the plan
  for 1b left it out).
- The drawing order is the order the game adds the visuals: the screen's
  fill, the logo (`TitleScreen.draw`, after the screen's own visuals),
  then the buttons, each picture before its text. Whether the game draws
  the logo before or after the container's buttons was not read; nothing
  on this screen overlaps, so the pixels are the same either way.

### What was measured

2026-10-18: WebAssembly 26,401,987 bytes (5.47 MB gzip), 12,936 bytes
more than after 1a; release build 1 min 43 s after the change.

### What was checked

- `cargo test -p pp_core`: 46 unit tests (two new ones for the menu
  column), the 35 font pages and the title, all pass; the title test
  printed "the title is identical to the reference" (it did not skip).
- `node scripts/checks/web_offline_check.mjs 8080` in headless Edge: the
  title read back from the canvas is identical to the reference; the
  font pages, the browser-keys check and the offline start still pass.
- A look in the app's browser pane at `http://localhost:8080`: the title
  screen as described above.

### Not tested

- Anything against the running game: the positions are from code reading
  only, and the 5-pixel gap above rests on the decompiler's output.
- Firefox. (The user tried 1b and the fix above on 2026-10-18; which
  browser was not recorded.)
- Whether the game's own PNG reader gives the same pixels for the three
  palette pictures (`Title.png`, `PushButton.png`, `SettingsButton.png`):
  the reference (Pillow) and the port (the `png` crate) agree, as for the
  font sheets in 1a.
