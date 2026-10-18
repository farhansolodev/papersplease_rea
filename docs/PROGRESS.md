# Where the project stands

**Read this first in a new session.** Last updated 2026-10-18, after
step 11, milestone 1b, the title screen as a still (`milestone-1.md`);
before it step 10, milestone 1a, the font test pages; before it
step 9, milestone 0 (`milestone-0.md`) and step 8, the architecture and
milestones in `DESIGN.md`. The user asked
the same day for three things, now in `DESIGN.md` as decided: the build
goes in milestones, each a browser build to try; the audio is streamed on
a first visit and kept in the browser; the game is kept in the browser so
a later visit loads fast. The design: a game core in plain Rust
(`pp_core`), Bevy as a thin host (my choice, left to me by the user),
asset preparation in Python, a service worker for the caching (each song
downloaded once, split between the player and the cache), and 11
milestones (0 to 10). The user then answered the five questions before
milestone 0 (`DESIGN.md`, "Answered before milestone 0"): served from the
user's own local web server, Chrome, Edge and Firefox, a start screen with
player options, Bevy left to me, and the go-ahead for Bevy's download.
**Bevy 0.20.0 is downloaded** (503 packages, into the project's
gitignored `.cargo-home/`).

**Update, later the same day (step 9): milestone 0, an empty page, is
built** (`milestone-0.md`; the user gave the go-ahead for the plan and
the `wasm-bindgen-cli` download), and the user tried it in their
browsers and said it looks right.

**Update 2026-10-18 (step 10): milestone 1a, the font test pages, is
built** (`milestone-1.md`). The user decided: the quads are drawn by
software in `pp_core`, milestone 1 is split into 1a (fonts) and 1b (the
title screen as a still). The core now reads the start pack, decodes
pictures, lays out text and draws quads; 35 pages are identical to the
new Python reference (`scripts/reference/fontpage.py`), in `cargo test`
and in headless Edge. Details in step 10 below.

**Update 2026-10-18 (step 11): milestone 1b, the title screen as a still,
is built** (`milestone-1.md`, "1b"), with the user's go-ahead. Before it,
a fix the user asked for: the page no longer blocks the browser's
shortcuts and right click (`milestone-1.md`, "Fix after 1a"). The title's
pixels are identical to a new Python reference (`titlescreen.py`), in
`cargo test` and in headless Edge; nothing compared with the game. A
finding: two menu buttons sit 5 pixels apart, not 10 (`screens.md`,
"The menu helper"; decompiler output only). The user tried 1b and the
fix the same day. Next: the plan for milestone 2. Details in step 11 below.

Before it the same day,
step 7, the sorting of the open questions: 151 items into five kinds
(answered and closed, need the game, the user's decision, will not matter,
could bite), the list below cut to four parts, and a new `docs/DESIGN.md`
with the decisions only. Nothing was run and no code read. The same day
the user accepted every suggested default in `DESIGN.md`, among them the
three "needed before the first Rust code" (a fixed 1/60 s step; booth draws
copied exactly; the English pack applied once at asset preparation). Two
stay open there: the songs' format (a tool download needs its own
go-ahead) and fullscreen in a browser. Next: step 8, writing the rest of
`DESIGN.md` (the architecture).

Before it the same day, step 6b, the game-side audio layer `app.aud` (`audio-layer.md`; code
reading of all of `app.aud` and its callers, two Ghidra runs, a
reference script `aud.py`, a check, and a measurement of the songs'
note starts; nothing listened to in the game). Main findings: one
speaker and one music player for the run, on a real-time clock with no
cap; fades are straight lines over the sound's `fade`; **an instant
volume change never reaches the host**, so at the start of a day one of
the booth's two ambient loops plays at full level until it is first
faded in (by the code; inferred to be the booth's hum); the booth
re-asks for its ambient volumes every frame, which turns their fades
into a smooth approach (4.6 s); a screen change fades every effect out
(songs untouched) and drops one-shots for the rest of that frame; the
pause screen pauses effects only, **so a song plays on under it** (this
corrects `save-format.md` and `screens.md`, which said all sound); a
song change fades the old one out over 4 s and starts the new one from
its beginning; the beat is a fixed tempo table (100 to 125 bpm) that
**fits `Theme`** in a measurement of the recording, so **the title's
rise takes about 23.6 s**. The only sound with a room (`car-driveby`)
is dropped while a traveler is in the booth.

Before it the same day, step 6, the audio (`audio.md`; the clips read with UnityPy and decoded
with the FMOD library that came with it, a second decoder of my own for
the effects, code reading of the host's sound player, one Ghidra run; an
extraction script and a check; nothing listened to in the game). Main
findings: all sounds are 111 clips in `sharedassets0.resource` (and
nothing else is in it), named by the file names the game asks for; the
108 effects are IMA ADPCM, the 3 songs (`Theme`, `Death`, `Victory`)
Vorbis; all 111 are now WAV files in `extracted/audio/` (80 MB), and two
independent decoders agree sample for sample on every effect; every
recording `Sounds.xml` names is there; the host plays at most 32 sounds
at once and drops the rest silently; the mixer does nothing but the two
volume settings, applied as setting squared in decibels (so 0 is
−80 dB, not silent). Open: how to ship the songs to a browser (62 MB as
WAV; a tool download either way) and the game-side audio layer (done
since, step 6b above)
`app.aud` (fading, the music's beat).

Before it the same day, step 5b, the Unity scene and shader files (`screen-output.md`, "The
Unity files" and "The quad shader"; read with UnityPy 1.25.4, newly
installed in the project's `.venv/`, the shaders disassembled with
Windows' own `D3DCompiler_47.dll`; a dump script, a reference function
and a check; not run in the game). Main findings: the quad shader
multiplies the picture by the quad's colour and mixes by **ordinary
alpha blending**; the project is in **gamma colour space**, so the mix is
on the stored values (by Unity's documentation); the screen quad is a
plain copy and the bars are black; the Pixel Perfect Camera has 100
pixels per unit; the window is resizable; the **phantom cursor is
behind the game's picture**, so it is never seen over it (only over
full-screen black bars); the grey "paused" screen shader is never used.
Everything step 5 had left open in the Unity files is answered.

Before it the same day,
the last part of the drawing step, the Unity side (`screen-output.md`;
code reading, a reference script `host.py` and a check; not run in the
game). **The drawing step is done.** Main findings: layers are drawn
lowest number first, and inside a layer in the order the visuals were
added; the Unity host keeps that order exactly (no grouping by picture);
everything is drawn into one 570 x 320 picture cleared to black, with
nearest-pixel reads; quads are not rounded, so where a fractional one
lands is the graphics card's rule; a picture is sent to the graphics card
again when its change counter moves; a window is 570 x 320 doubled while
the double stays under two thirds of the monitor (1140 x 640 on
1920 x 1080); the host's `phantomCursor` shows `CursorPhantom.png`,
which is exactly the arrow's white edge, placed on the drawn arrow.
Not in the code, so left open then: the quad shader's blending, the
colour space, the full-screen fit and whether the phantom cursor is
visible (answered by step 5b above, except the full-screen fit, which is
the Pixel Perfect Camera package's documented behaviour, not tested).

Before it, on 2026-10-16,
input handling (`input-handling.md`; code reading, a reference script
`inputs.py` and a check; not run in the game). Main findings: on desktop
only the mouse's left button counts, as one pointer in whole game
pixels; the topmost part under the mouse answers first and blocks its
rectangle for the frame, and the first cursor set wins; a part that
takes the pointer keeps it to the end of the next frame; a double click
is under 0.2 s and under 2 pixels; the game draws its own cursor (arrow,
hand, or the rifle's 47 x 47 scope at the border).

Before it the same day, part 7 of the drawing step: the rest of `play.ui` (`ui-parts.md`; code
reading, a reference script `ui.py` and a check; not run in the game).
Main findings: the diagram lines (inspect mode, screen rules) are
**dotted**, single pixels two apart, with rounded corners; the speech
bubble wraps a line at 120 pixels only when it is wider than 160 and
stays 0.1 s per character, with a small bounce when it opens; the
drag helper has a rubber band and a spring back; the achievement popup
comes from the platform's social service (out of scope).

Before it the same day, part 6 of the drawing step: the rest of `app.vis` (`vis-basics.md`;
code reading, a whole-decompile search for callers, a reference script
`vis.py` and a check over the data files; not run in the game). Main
findings: a picture's pixel is 0xAARRGGBB held as bytes B, G, R, A;
colours convert by 255, cut toward zero; a plain box is one white pixel
stretched; `Frame` is a nine-slice picture; atlas chips are drawn in y
order; a point in the data must be exactly "x y" with one space (all 625
values in the data are); many helpers (the MMPX enlarger, rainbow
colours, `Point.random`, picture flips) are never called by the game.

Before it the same day, part 5b of the drawing step: the inspect mode (`inspect-mode.md`; code
reading with the instructions of part 5a's Ghidra run, a reference
script `inspectmode.py` and a check; not run in the game). Main
findings: two selection slots, a third mark replaces the older one; a
mark's fact path comes from the mark's fact after its proxy and the day's
renames; the paper itself can be marked only if it does not dock and
`Facts.xml` knows it; four booth things can be marked (counter, face,
clock, weight); 16 papers cannot be inspected; the label's text is one
of four by the pair's relationship; the diagram runs 2 seconds (lines,
three appearances of the label, then the interrogate button, shown only
for a disagreement with `Interrogate` responses, and pressable once every
2 seconds); the mode is disabled for the rest of the day once the booth
is busy with the border scene.

Before it the same day, part 5a of the drawing step: how a paper moves on the desk
(`desk-movement.md`; code reading, three Ghidra runs for what the
decompiler dropped, a reference script `deskmove.py` and a check over
every paper; not run in the game). Main findings: a paper from the slot
falls at 350 pixels a second onto the counter (a passport in 9 frames);
printed papers wait 3 seconds, then print line by line in 20-pixel
steps; an open page always keeps at least 70 x 30 pixels on the desk;
the give icon needs the cursor and the paper's bottom inside the give
area while the traveler may take the paper; closed papers fall with
3,000 pixels a second squared; the rulebook, bulletin and transcript rise,
slide and drop back into their dock, whose places have exactly the
closed pictures' sizes; the sound `toTop` plays when a paper that is
already on top is picked up (checked in the instructions).

Before it the same day, the desktop layout step (`booth-layout.md`): the game's own `Layout`
constructor was **run in Ghidra's emulator** for the desktop platform,
which gives all 98 fields of the layout, among them the booth's
rectangles that part 4 left open. The run reproduces all 35 values
read by hand from the instructions in earlier steps. Main values (booth
coordinates; the booth is the 570 x 217 area under the border scene,
from screen y 103): the traveler's window x 0..178, y 0..107; the counter
below it; the desk x 178..570; open pages are cut 2 pixels right of the
desk's edge (x 180); the give area x 39..139, y 0..107; closed papers
fall until their middle is at y 145; the rulebook, bulletin and
transcript dock at three places on the console. New: `EmulateLayout.java`,
`layout_dump.py`, `layout.py` (the values), `layout_check.py`. Not run in
the game.

Before it the same day, part 4 of the drawing step: a paper's pictures
on the desk (`desk-pictures.md`). It was code reading, with one Ghidra
run for the instructions, a reference script `deskpics.py` and a check
over every paper in `Papers.xml`. It was not run in the game. Main
findings:

- A desktop booth has **no carousel** (the booth makes one only for the
  phone layout). This settles an open question of `buttons.md` and
  `screens.md`: the desktop stamp bar is a `StampBar`.
- A closed paper is its picture turned by up to 30° either way and
  **halved**, with a grey-green shadow at (−1, 2); docked and hung papers
  keep theirs as it is (but still make the tilt draw).
- On the desk a page's visuals take the page's clip, so the `Citation`'s
  36-pixel `clipheight` has no effect there (by the code).
- `compareProximity` (which mark the cursor picks) and `Image.render`
  are read in full.

Before it the same day, part 3 of the drawing step: the fact pictures of
a page (`fact-pictures.md`; code reading, one Ghidra run, a reference
script `factpics.py` now used by `pages.py`, a check of every picture
fact in `Papers.xml`; not run in the game). Main findings:

- Every paper except `Passport` shows its photo mirrored and recoloured.
- A fingerprint picture costs a random code's draws plus one draw per
  finger. `desk.py` now counts them; the logs cannot test it.
- `Image.paste`, `tint` and `transformed` are read.

It also corrected `text-drawing.md` (a stretched tile goes through
`Image.render`, not `Image.draw`), `emblems-and-bodies.md` (nothing
pastes the contraband on the body) and `nightpics.py` (it halved the
passport cover with other pixels than the game). Before it the same day,
part 2 of the drawing step: how a document page is laid out
(`page-layout.md`; code reading, two Ghidra runs for the instructions, a
reference script `pages.py` that lays a page out and draws a preview, a
check of all 120 page pictures; not run in the game). Main finding: a
mark without `pos` takes its place from a marker pixel in the page
picture (black for side 0, red for side 1), and every such pixel is
painted over, the tokens' black details included. Before it the same
day: which real newspaper headlines lose their subtitle or fall back to
the regular font, worked out with `text.py` (`newspaper-picture.md`,
"Which real headlines are cut"; `newsimage.py` now lays the texts out).
Before that, part 1 of the drawing step: how a text is laid out and drawn
(`text-drawing.md`; code reading, three Ghidra runs for the instructions,
a reference script `text.py` that lays a text out and draws a preview, a
check of the fonts against the English texts; not run in the game). It
also corrected `fonts.py` (the width of a one-line text). Before it the
same day, part 11 of the screens: the day screen, the wait screen, the screen
shake, the screen flash and the news magnifier (`screens.md` part 11;
code reading, one Ghidra run for what the decompiler dropped, a
reference script `screenfx.py`; not run in the game). It closes the
screens step. Before it the same day, part 10: the night screen's family
pictures (`night-pictures.md`; code reading, one constructor checked in
its instructions, a check of the six pictures and a reference script
that renders them; not run in the game, but it agrees with the
description of the user's night-3 screenshot). Before that, part 9: buttons (`buttons.md`; code reading, two
constructors read as instructions, and a check of the button pictures;
not run in the game). It also found that desktop never loads the
archive's `layout/` folders (`art-dat-format.md`). Before that, part 8: how a language
pack is loaded and what the English pack changes
(`language-pack.md`; code reading and a comparison of the files, not run
in the game). Before that the same day: the user decided the port is
English only, with no language chooser and no age rating. Earlier that
day, the screens, part 7: the endless code box and the endless screen, with the
local best score per course and style (`screens.md`; code reading, then
watched by the user in the real game in a separate save folder: all
matched, and the files it wrote confirm the stored choice and the local
best score).
Earlier the same day a whole-game search showed nothing but the news
screen uses the day's news generator (`newspaper-picture.md`). Before
that 2026-10-15, in the
eleventh session (after the screens, part 6: the credits screen, and the
game's frame rate; parts 1 to 5, in the ninth and tenth sessions, were
the base of a screen, the night screen, the title screen, the menu
helper, the load screen, the confirm box, the pause screen, the settings
screen, and the intro and ending screens with their page player; all
code reading, plus one screenshot of the real night screen that
confirmed the budget's line order). Also on 2026-10-15: the older
per-topic decompiles were removed from `decompiled/`, which now holds
only `all/`, `ghidra/`, 16 library-function files and the `.txt`
listings (see "Things that exist only on this machine").
`MODLOG.md` has the step-by-step history; this file is
the current state, what to do next and what is still open. It is updated at
the end of every step. The rules for how to work are in `CLAUDE.md`, not
here.

## One-paragraph summary

The game is Haxe compiled to C# and then to native code by Unity IL2CPP.
Names, data layouts and typed signatures are recovered and loaded into a
saved Ghidra project, so any function can be decompiled by name, and
since the tenth session **all of the game's own code is decompiled once**
into `decompiled/all/` (6,856 functions), so any question can start with
a search. The
content archive (`Art.dat`) is decrypted and unpacked: 614 images, fonts and
plain-text data files. The 111 sounds and songs, stored elsewhere, are
decoded to WAV (`audio.md`), and the game's own sound layer (fades,
song changes, the music's beat) is read (`audio-layer.md`). The game is strongly data-driven. **Every data file
now has a write-up.** Traced from the code: the seed chain from launch to
each day; how a traveler is chosen, built and given documents with right or
deliberately wrong values; how errors are chosen and applied; speech; the
booth's events, the player's actions and how mistakes are judged; faces;
the day's headlines and the newspaper picture; the night (family, budget, endings by debt or death);
endings, text, sounds, seals, bodies, endless mode, fonts, the border
scene's paths and pictures, how its figures follow a path, how the
waiting line works, and what runs the scene (its states, the 36 path events,
the four attack scenes, shooting and its six endings, how the day ends
there, the view, the endless scoreboard), credits, languages, the save
files (the encrypted store, the tree of saves, what one save holds; a real
save folder decrypts and matches), and how the game moves between screens
(19 kinds of request, one place that builds each screen, loads and saves),
with the "stash", a resume snapshot that the desktop game writes but never
reads back (seen in a test with the real game), and the first of the
screens: the night screen (lines start ticked, a click flips one, the
budget is balanced after every click, the appearing animation, the sleep
button), the title screen (its buttons, the title rising with the
music), the load screen (the save tree as a grid of at most 5 tracks,
continuing, starting anew, deleting), and the pause and settings screens
(Escape pauses; the list of settings they share; a changed setting is
applied and saved on the next frame; every key the game reads, and every
other use of Escape, which is always a screen's "back button"), and the
intro and the endings (one page player: a 1-second wipe from the right,
then the caption types on, then NEXT; the ending fades to its statistics
page over 2 + 2 + 2 seconds and records the ending in `EndBits`), and the
credits screen (the first credit held for 4 seconds, then the list
scrolls 0.5 pixel a frame, 4 times that while the mouse button is held,
and loops; the game runs at 60 frames a second on most screens), and the
endless screens (the code box: code 62131, five blinks over 3 seconds;
the endless screen: style and course rows, the choice kept in the
settings, a result box after a run, and the player's best score per
course kept locally even without leaderboards), and the language pack
(English is loaded as a pack too: every file lookup tries `en.zip` first,
and its table fixes 3 typos, shows `Gender` as `Sex` and adds line breaks
to 16 texts; one bulletin picture exists only in the pack), and the
buttons (a button has looks, each with a normal and a pressed picture,
usually two bands of one picture, and a text whose colour changes when
pressed; the press must start on the button and a click is the release
over it; every button the game makes is listed with its picture and
cut), and the night screen's family pictures (fixed desktop positions:
a row of status badges and the name per member on the right, the
apartment class top right, seven token places, the passports with their
count and four upgrade places on the left; no random draws), and the
last screens (the day screen holds the booth and the border scene and,
on desktop, no tutorial; every screen has its own shaker, which moves the
whole screen by whole pixels with its own fixed-seed generator; a "flash
to the title" turns the screen white, then black, then shows the title,
after a time bomb, a grenade on the booth or touching poison), and how a
text is drawn (the line breaker's lines, one piece of the font sheet per
letter, a filled box for a letter the font lacks; the size is the widest
line and the number of lines times the line height, plus padding; a
text's position is the top left corner of its box; on screen each letter
becomes a quad, and a letter with no colour set is skipped), and how a
document page is laid out (marks without a position take it from marker
pixels in the page picture, black or red by side, which are then painted
over; texts sit one pixel above their base line, can flow down or right
from the last one, links become rounded buttons, seals are drawn at half
opacity), and which newspaper headlines are cut (on the plain days, two
lose their subtitle; traveler news adds more, and one title falls back
to the small font because "Breakthrough" is one pixel too wide), and the
fact pictures of a page (the document photo, mirrored and recoloured on
every paper but the passport; the search photo's head, body and
contraband; fingerprints cut to the outline of a random print; the
bulletin's criminal photos; the rulebook's seal sheets; pictures named by
a fact's value; and the picture operations paste, tint and scaling). The desktop
layout turned out to have no panning, no camera screens and no slow motion:
those exist only in the phone and tablet layouts. A Python reference builds
complete travelers from a master seed, and **it now matches the running
game**: the game's own test player was run with a fixed seed, and for the 36
travelers of days 1 to 4 the reference gives the same entry, nationality,
purpose, papers and errors as the game's log. The night model also
reproduces four hand-played nights exactly, from the facts in real saves.
No Rust code exists yet.

## How far along

Rough estimate: **about 40% of the work**, low confidence. Estimated total:
100 to 200 hours of sessions.

| Stage | Share | State |
|---|---|---|
| 1. Tools to read the code | 3% | Done |
| 2. Getting assets out | 5% | Mostly done: images, fonts, data; the English language pack compared with the archive (`language-pack.md`; other packs not needed); the audio, as WAV (`audio.md`, 2026-10-17). Not done: a scripted `Art.dat` cut-out; the browser formats (the songs are too big as WAV, a decision for `DESIGN.md`) |
| 3. Understanding the data files | 12% | Done: all 31 files in the data folder are written up (`data-files.md`). The 3 that the game does not read are noted as such |
| 4. Understanding the game logic | 30% | Roughly 80%. Done: the traveler pipeline (with a Python reference that matches the game), speech, booth events, player actions, judging, faces, news selection, the night's rules, the newspaper picture, endless-mode rules, the whole border scene in four parts (figures and the waiting line, `Border` itself, shooting, the view with the cameras and the endless scoreboard), saves in two parts (the store, the save tree, one save's content, settings and statistics files; screen changes and the stash). The screens, parts 1 to 7: the base of a screen, the night screen, the title screen, the menu helper, the load screen, the confirm box, the pause screen, the settings screen, the intro and ending screens with their page player, the credits screen, the endless code box and the endless screen (`screens.md`); the frame rate (`border-view.md`); part 8, how a language pack is loaded and what the English one changes (`language-pack.md`); part 9, buttons (`buttons.md`); part 10, the night screen's family pictures (`night-pictures.md`); part 11, the day screen, the wait screen, the screen shake, the screen flash and the news magnifier (`screens.md`). Left out by the user's decision: the language chooser and the age rating. Step 5, drawing, part 1: how a text is laid out and drawn (`text-drawing.md`); part 2: how a document page is laid out (`page-layout.md`); the newspaper's headlines run through the text layout (`newspaper-picture.md`); part 3: the fact pictures of a page and the picture operations they use (`fact-pictures.md`); part 4: a paper's pictures on the desk, clipping, drawing order, clicking, picking a mark, stamp ink, `Image.render` (`desk-pictures.md`). Every desktop layout value, from the `Layout` constructor run in the emulator (`booth-layout.md`). Part 5a: how a paper moves (reveals, hides, dragging, the clamps, the give area, the dock points, the drawer; `desk-movement.md`). Part 5b: the inspect mode (`inspect-mode.md`). Part 6: the rest of `app.vis` (`vis-basics.md`). Part 7: the rest of `play.ui` (`ui-parts.md`). Input handling (`input-handling.md`). The Unity side of drawing (`screen-output.md`), which ends the drawing step; step 5b, the Unity scene and shader files, read with UnityPy (`screen-output.md`, "The Unity files"). Step 6b, the game-side audio layer (`audio-layer.md`) |
| 5. Building the browser game in Rust | 40% | Started: **milestone 0 built and tried by the user** (`milestone-0.md`, 2026-10-17): a Bevy window in the browser showing a test card at a whole-number zoom, the fixed step, the service worker, the build and server scripts. **Milestone 1a built** (`milestone-1.md`, 2026-10-18): the start pack, fonts, text layout, software drawing of quads, 35 font test pages identical to the Python reference. **Milestone 1b built** (2026-10-18): the title screen as a still, identical to its Python reference; tried by the user. The architecture and milestones are in `DESIGN.md` (step 8). Bevy 0.20.0 and `wasm-bindgen-cli` 0.2.129 are in `.cargo-home/`; `trunk` and `wasm-pack` are not used. Milestones 2 to 10 not started |
| 6. Comparing with the original | 10% | Started and working: a repeatable method exists and days 1 to 4 of one seed match; a real save folder gives a second method (see "Verification") |

## What is documented

| Doc | Covers |
|---|---|
| `il2cpp-name-recovery.md` | Il2CppDumper run and checks |
| `ghidra-workflow.md` | Commands, scripts, how to read decompiled output, the emulator, the study method |
| `art-dat-format.md` | The encrypted archive |
| `data-files.md` | Index of every data file, its loader and its write-up |
| `port-requirements.md` | Exactness rules the Rust port must follow |
| `milestone-0.md` | Milestone 0, an empty page: how to try it, what was built, what was measured (WebAssembly 26 MB, `target/` 2.3 GB), what was checked, what is not tested, dead ends |
| `milestone-1.md` | Milestone 1a, the font test pages, and 1b, the title screen as a still (with where everything on it sits and the 5-pixel menu gap); the fix for blocked browser keys: how to try each, what was built, the decisions, measurements, checks, findings (half-pixel positions, a line-breaker edge), what is not tested |
| `DESIGN.md` | The port's decisions: decided by the user, suggested defaults, the three needed before the first Rust code, the five answered before milestone 0 (hosting, browsers, start screen, Bevy as a thin host, downloads); the architecture (core, host, page, asset preparation; one frame; exactness checks; loading and caching) and the 11 milestones (step 8) |
| **Base** | |
| `rand.md` | The random generator, checked against the machine code |
| `run-and-seeds.md` | Start-up: the master seed, story seeds (a new game uses the second one), cyclers, command-line words, the debug log switches |
| `tab-tree-format.md` | The indented-tree reader and templates |
| `haxe-maps.md` | Haxe's `StringMap` and `IntMap`: hash, layout, walking order |
| **Travelers and the booth** | |
| `days-csv-format.md` | `Days.csv` |
| `papers-xml-format.md` | `Papers.xml` (layout and drawing not studied) |
| `facts-xml-format.md` | `Facts.xml`, plus random-pick procedures |
| `travelers-txt-format.md` | Traveler scripts |
| `errors-txt-format.md` | `Errors.txt` and error selection |
| `traveler-creation.md` | The sequence that creates a traveler |
| `traveler-build.md` | Building the person: face, name, id, fingerprints, height, weight, criminals |
| `operations-and-fact-validity.md` | Running an operation; invalid facts |
| `fact-values.md` | How each document value is generated |
| `value-helpers.md` | Wrong names, aliases, typos, wrong faces and fingerprints, dates |
| `papers-on-desk.md` | Adding and removing papers, staying papers, the bulletin |
| `desk-drawing-draws.md` | **The random draws made when a paper is drawn on the desk** (tilt, photo, seal, fingerprints). Needed to stay in step with the game |
| `speech.md` | `Speeches.txt` and how say lines become speech (each stock line draws) |
| `responses-and-events.md` | The booth's events, responses, conditions, operation queue, button commands, citations |
| `player-actions.md` | Stamping, giving and confiscating, the filer, interrogation, fingerprint / search / detain, poison and bomb, judging, penalties |
| `faces.md` | `Faces.xml`, face sheets, how a face picture is composed |
| `emblems-and-bodies.md` | `Emblems.xml` (seals) and `Bodies.xml` (body types, contraband) |
| **Around the day** | |
| `news-txt-format.md` | `News.txt`, which headlines a day gets and in what order |
| `newspaper-picture.md` | The newspaper picture: the six layout pictures, which article goes in which rectangle, what is drawn, its random draws; the news screen; which real headlines lose their subtitle or fall back to the regular font (worked out with `text.py`) |
| `nights-txt-format.md` | `Nights.txt`: scheduled events, budget lines, the calendar |
| `night.md` | The night itself: family members, the budget, illness, hunger, cold, the debt and death endings |
| `save-format.md` | **Saves, part 1**: the save folder and its `.sav` files, the encryption, the tree of saves (`headers`), what one save holds (the story facts as XML), saving / loading / deleting, `StoryState`, the settings and statistics files, the debug jump's faked facts, and the comparison with a real save folder. **Part 2**: the 19 requests a part of the game can make (`GameTransition`), how a screen change is queued and built (`Game.queueScreenChange`, `applyScreenChange`), the game's own five states (fade, pause), and the stash: when it is written, deleted and read, what it holds, how it is restored |
| `screens.md` | **The screens, part 1**: the switches every on-screen object carries (active, takes input, is updated), what every screen is built on (`GameScreen`), and the night screen: what it builds and in what order, tall or short budget lines, ticking, when the budget is balanced and what the player sees, the appearing animation and its timings, the sleep button, the family sentences (`Family.buildMessage`). **Part 2**: the title screen (its buttons and what each does, the title rising in 20 steps with the music, the logo bobbing), the menu helper `Menu`, and the desktop values of eight layout fields. **Part 3**: the load screen (the grid of save buttons, how saves are put on up to 5 tracks, what a click does, the summary box, deleting) and the confirm box `Confirm`. **Part 4**: which key pauses (Escape) and the game's 11 key numbers, the pause screen, the settings screen, the settings list both share (its rows in each form, what each click does, how a row is laid out), who writes the settings file (`Game.applySettings`), that nothing in the build reads `platover`, the header helper, and seven more desktop layout values (one of them corrects part 2). **Part 5**: the page player of the intro and the endings (the wipe, the typing caption, NEXT, hurrying a page from page 2 of the intro), the intro screen, the ending screen (its steps, the statistics text, the 2 + 2 + 2-second fade, the button), `EndBits` and the load screen's ending marks, restoring an ending stash. **Part 6**: the credits screen (who opens it, which languages are available, where the list sits, the 4-second hold at the first view, the scroll by frame and the fast scroll while the mouse button is held, the loop, the buttons). **Part 7**: the endless code box (`UnlockConfirm`: the keys, the check, the blinking, the code 62131), the endless screen (its two rows, selecting and the stored choice with its fallback, the selection line, PLAY and BACK, the score under each course and the local best score kept in the statistics, the result box after a run, the hidden clear-achievements box and press-kit helper; where it touches leaderboards, left out by the user's decision). **Part 11**: the day screen (`DayScreen`: booth, border, a tutorial on phones only), the wait screen (phones and tablets), the screen shake (one per screen, seed `0x6500065`, the formula, who shakes), the screen flash and fade cover (`ScreenFlash`, the flash to the title and its three users), the news magnifier (never on desktop) and `Layout.getFitScale`. Each part ends with a list of things to watch in the game |
| `ends-xml-format.md` | `Ends.xml` and `Intro.xml`: the 20 endings and the intro slides |
| `endless-mode.md` | `Endlesses.xml`, `Endless.csv`: styles, courses, scoring (the endless screen is in `screens.md`, part 7) |
| `text-xml-format.md` | `Text.xml`: texts, placeholders, the long date |
| `sounds-xml-format.md` | `Sounds.xml`: which recording plays, song names |
| `audio.md` | **Step 6**: where the sounds are (111 clips in `sharedassets0.resource`, keyed by the file names the game asks for), their stored formats (IMA ADPCM effects with the block layout, Vorbis songs), the extraction to WAV and how far it is exact, the host's sound player (`UnityPlatformAudio`: 32 sources, start, stop, pausing, the volume in decibels), the mixer, which screens ask for which song, the check, the port's song-format decision |
| `audio-layer.md` | **Step 6b**: the game-side audio layer `app.aud`: one speaker and one music player, the speaker's real-time clock; playing an effect (unknown id, room, the ignore switch, the recording picked only when it plays) and a song; a sound's volume, straight-line fades, the 0.01 jump, stopping (an instant volume change never reaches the host); who stops, pauses, ignores (screen change: effects fade out; pause: effects only); the booth's two ambient loops and the room; song changes (`Music`); the beat table (`MusicBeat`) and its fit to `Theme`; the title's rise in seconds; vibration (none on desktop) |
| `fonts.md` | `Fonts.xml` and the `.fnt` files: measurements, text width, line breaking |
| `text-drawing.md` | **Drawing, part 1**: `app.vis.Text`: its settings, how it is laid out (lines, alignment, padding, line spacing, the background and its cut corners, the box for a missing letter), its size, where its position puts it, how it is drawn on screen (quads, the 0.001 alpha test) and into a picture (`Image.paste` cuts positions toward zero), letters revealed one by one, which code sets padding, spacing or a background |
| `page-layout.md` | **Drawing, part 2**: `PaperInnerVisuals`: who builds a page, the page picture and its marker pixels (black side 0, red side 1, painted over), the positions, which marks a link leaves out (`PaperNav` and the page mask), text marks (flow, the base line, boxes, link buttons, wrap, touch padding), picture marks, seal marks (half opacity), clipping; finding marks and pages |
| `fact-pictures.md` | **Drawing, part 3**: `BoothEnv.getImage`, the picture a fact shows: the document photo (`Face.getDocImage`; mirrored and recoloured except on `Passport`), the search photo's head, body and contraband, fingerprints and the thumbprint, the bulletin's criminal photos, the rulebook's seal sheets, the bulletin seal, pictures named by the value (where each value comes from), the final scaling; the picture operations (`draw`, `transformed`, `paste` with its modes and tint, `copy`, `fill`, `replace`, `tint`, `Math.round`); every random draw; who reads the Nudity setting |
| `desk-pictures.md` | **Drawing, part 4**: a paper's pictures on the desk (`DeskItem`, made by `Paper`): the closed picture (tilt up to 30°, halved, shadow; docked and hung papers as they are), the open page (`setPage`, `setInnerImage`, `addInnerVisual`), the drawer envelope, the wall picture, the phone-only rack; a desktop booth has no carousel; clipping and which rectangle each sprite is cut to; drawing order and layers; clicking and the odd-shape test; picking the mark under the cursor (`getInnerVisualAt`, `compareProximity` in full); stamp ink; `Image.render` |
| `desk-movement.md` | **Drawing, part 5a**: how a paper moves (`DeskItem`): the reveal chosen by the `Paper` constructor and every reveal animation with its timing and sounds (from the slot, printed from the bottom or top, spat from the right, the instant ones), the hide animations and who hides papers, dragging (which placement the cursor gives, offsets, the clamps), dropping (the drawer, the wall's saved place, giving, clicks and links), the give test, falling, sliding (the drag velocity), the dock points' drag clamp and return path, the drawing order, the drawer (`Filer`: size, states, slots) |
| `input-handling.md` | **Input handling**: one frame's order; the mouse to game pixels; a pointer's frame (down, just down and up, held and unheld place, taking, double click); `getPointerOver` and `getPointerJustDown`; blocked areas and who sets them; keys and pointers masked until release; the cursor kinds, the drawn cursor and where each picture sits; the rifle scope cursor |
| `ui-parts.md` | **Drawing, part 7**: the rest of `play.ui`: the dotted `DiagramLine` (dots, rounded corners, how much shows), `DottedLine`, the speech bubble (look, wrapping, place, time on screen, opening and closing), `KineticScroll` (rubber band, coasting), the rest of `RevealTextEnt`, the achievement popup in outline |
| `screen-output.md` | **The Unity side of drawing** (the last part): the drawing order (layers lowest first, then the order visuals were added), the host's frame, the 570 x 320 screen picture and how it is fitted to the window (window size, full screen, the command-line words), how quads are batched, texture coordinates, pictures on the graphics card and the change counter, where a fractional position lands (the graphics card's rule, assumed), the quad shader (colour multiplied in, ordinary alpha blending, gamma colour space), the phantom cursor (behind the picture, so hidden over it), and the Unity files (step 5b: the scene, materials, shaders, Pixel Perfect Camera and project settings, read with UnityPy) |
| `vis-basics.md` | **Drawing, part 6**: the rest of `app.vis`: pictures in memory (0xAARRGGBB, byte order, change counter, `white1x1`), colours, `Fill`, the nine-slice `Frame`, the atlas of chips and its y order, `Point.parse` and `Rect.parse` with the data check, the geometry helpers the game uses, and the helpers it never calls |
| `inspect-mode.md` | **Drawing, part 5b**: the inspect mode (`InspectUi`): opening and closing (button, Space, double click), its states and timings, the reveal of the hint and buttons, the overlay, the surround lines and the initial scan; what can be marked (papers topmost first, marks to fact paths, the paper itself, the booth's four things); the two selection slots; the pair's text; the diagram's timeline and label side; the interrogate button; when the mode is disabled |
| `booth-layout.md` | **Every desktop value of `Layout`**, from the game's constructor run in Ghidra's emulator: the booth's rectangles (window, counter, console, desk, clips, clamps, give area, slot, counter edge, floor line), the dock points of the rulebook, bulletin and transcript, the inspect rectangles, and all other fields; how the run was made and checked (35 values read by hand earlier all match) |
| `paths-xml-format.md` | `Paths.xml`: paths and animations of the figures in the top view |
| `borderanim-xml-format.md` | `BorderAnim.xml`: the picture atlas and how an animation finds its frames |
| `border-figures.md` | **The border scene, part 1**: which random generator it uses, how a figure follows a path frame by frame (what `hold`, `delay`, `snap`, `warp`, `face` and the event attributes do), the waiting line (building, moving up, the ring of reused figures, dispersing, panic) and its random draws |
| `border-scene.md` | **The border scene, part 2**: the figures `Border` owns, its 12 states, the normal call-in cycle, what happens when a traveler leaves or is detained, when and how the four attacks run, what each of the 36 path events does, explosions, how the day ends, saving, every random draw |
| `border-shooting.md` | **The border scene, part 3**: when the player can shoot, the two rifles and their keys, what a shot does and whom it hits, the attack result and its six endings, bullet holes, the grenade's flight, slow motion and which clock runs what, the test player's aiming helpers |
| `border-view.md` | **The border scene, part 4**: the three screen layouts and their border values (desktop: no panning, no cameras, no slow motion; hit box 8 x 18), how the view slides and follows a figure, the camera screens, the endless scoreboard and its flashing texts, the game's clock and frame time, and the frame rate (60 frames a second when the screen's refresh matches, otherwise 65; added 2026-10-15) |
| `credits-txt-format.md` | `Credits.txt` and the layout of the credits list |
| `languages-list.md` | `Languages.txt`, `Languages.png` |
| `language-pack.md` | **Part 8**: how a language pack (`StreamingAssets/loc/<code>.zip`) is loaded, which language starts, how the pack's table replaces text in the data files (the 27 extractors), what is in `en.zip`, and the 23 texts the English pack changes. English only, by the user's decision |
| `buttons.md` | **Part 9**: `play.ui.Button` and its looks (`Mode`): the normal and pressed pictures, the text, its colours and where it sits, drawing, how the mouse and the shortcut key press and click a button, the hand cursor, every button the game makes with its picture and cut, the stamp bar's sliding `DropButton`, the phone-only `HoverButton`, and which button pictures exist only for phones |
| `night-pictures.md` | **Part 10**: the night screen's family pictures (`FamilyVisuals`): the status badges and name of each member, the apartment class, the token column (`tokenOrder`, `imageTokenIds`), the passports and their count, the upgrade places (desktop's four upgrades); their desktop positions and picture pieces; the reference `nightpics.py` |
| `test-tooling-files.md` | `TestScenarios.xml`, `Auto.txt` (a recipe for reaching every ending) |
| `unused-data-files.md` | `Threads.txt`, `TravelerGraph.txt`, `Version.txt`: not read by the game |
| **Checking against the original** | |
| `comparing-with-the-game.md` | The game's test player: the `auto.plan` file, how to run it with a fixed seed, the log it writes, and the results of the runs so far |

## Currently stuck

Nothing.

Two earlier problems are solved. Their records are kept with their topics,
so the dead ends are not repeated: REA's Ghidra requests timing out (end of
`ghidra-workflow.md`), and the booth's random numbers falling out of step
with the game (end of `comparing-with-the-game.md`).

## Next steps, in order

(Done in the fourth session: the booth layer of the reference; every
remaining data file; the night's rules; the method for comparing with the
running game and the first two runs; finding and fixing why the reference's
error picks left the game's. Done in the fifth: the newspaper picture. Done
in the sixth: the whole border scene, parts 1 to 4. Done in the seventh:
saves, part 1. Done in the eighth: saves, part 2. Done in the ninth: the
screens, parts 1 to 3. Done in the tenth: the screens, parts 4 and 5.
Done in the eleventh: the screens, part 6. Done on 2026-10-16: the
screens, part 7; part 8, the language pack; part 9, buttons; part 10,
the night screen's family pictures; part 11, the last screens.)

1. **A longer comparison run of the game**: **postponed by the user on
   2026-10-14** ("skip for now"). Do not start it without being asked; it
   also needs the go-ahead for each launch. What it would test: later days
   and a second seed, for what days 1 to 4 never exercised. The list is at
   the end of `desk-drawing-draws.md`: pages
   drawn again when turned, the fingerprint / thumbprint / contraband
   pictures, the identity record, a hidden paper shown later, invalid seals,
   criminal photos on the bulletin. It would also test documents that only
   appear later (work pass, id card, access permit, vaccine certificate...).
   A full route takes about 40 seconds per day.
2. **The border scene**: **done**, in four parts (`border-figures.md`,
   `border-scene.md`, `border-shooting.md`, `border-view.md`). The 314
   functions read are in `decompiled/all/` (311 in
   `play_day_border.clean.c`, 3 in `play_day_booth.clean.c`); a condensed
   copy of `Border` can be made with `condense_decompile.py` and a name
   filter. (They were read in older copies, removed on 2026-10-15 as
   duplicates.)
3. **Saves**: **done**, in two parts (`save-format.md`). Part 2 was code
   reading, and its main claim was then tested in the real game on
   2026-10-14: after the first traveler of day 1 had left and the window
   was closed, `stash.sav` was in the folder; the next launch showed the
   title screen and left the file alone; a click on "Story" deleted it,
   and the screen that opened offered only a new game (the unfinished day
   was lost). The stash's content matches the description (`stash_check.py`,
   `0 problems`).
4. **The screens: done** on 2026-10-16, in 11 parts. Parts 1 to 7 and
   11 are in `screens.md`, parts 8 to 10 in their own docs (below). In
   `screens.md`:
   the base of a screen (`GameScreen`, the entity switches), the night
   screen, the title screen, the menu helper `Menu`, the load screen, the
   confirm box `Confirm`, the pause screen, the settings screen and the
   settings list they share, the page player of the intro and the
   endings, the intro screen, the ending screen, the credits screen, the
   endless code box `UnlockConfirm` and the endless screen.
   (The language chooser and the rating screen were suggested as part 8;
   the user decided on 2026-10-16 to leave both out of the port, so
   they will not be studied. Part 8 became how the English language
   pack is loaded: **done** on 2026-10-16, `language-pack.md`. Part 9,
   buttons: **done** on 2026-10-16, `buttons.md`. Part 10, the night
   screen's family pictures: **done** on 2026-10-16,
   `night-pictures.md`. Part 11, **done** on 2026-10-16 in
   `screens.md`: `DayScreen`, `WaitScreen`, `ScreenShake` with
   `GameScreen.shake`, `ScreenFlash`, `NewsScreenMagnifier`.) Not read in
   `play.screen`, both small: `ScrollPassthroughEnt` (7 functions, made
   by the `LoadScreen` constructor) and `ReactPassthroughEnt` (7; no
   code making it was found by name). Left out: `LangChooser`,
   `RatingScreen`, `RatingPopup` (the user's decision);
   `UnstashOverlay` and `PlatformChangeConfirm` are phone and tablet
   only by the earlier reading (`save-format.md`, `screens.md` part 4).
   All of `play.screen` is decompiled in
   `decompiled/all/play_screen.clean.c` (466 functions, with a condensed
   copy `play_screen.short.c`; parts 1 to 5 were read in an older copy,
   removed on 2026-10-15 as a duplicate);
   read so far:
   `NightScreen`, `TitleScreen`, `Menu`,
   `LoadScreen` and its helpers (the constructor for its parts only, not
   its positions), most of `Confirm` and `GameScreen`, `PauseScreen`,
   `SettingsScreen`, `SettingsMenu`, `SettingRow`, `SettingDim`,
   `Intro`, `IntroScreen`, `EndScreen`, `CreditScreen`, `CreditList`,
   `UnlockConfirm`, `EndlessScreen` (its desktop branch in detail),
   `DayScreen`, `WaitScreen`, `ScreenShake`, `ScreenFlash`,
   `NewsScreenMagnifier`. How a
   screen is asked for and built is in `save-format.md`, part 2.
   The user's screenshot of a night screen (2026-10-14) confirmed the
   order of the budget lines for one night (`screens.md`, part 1). A
   second look, at a night with no one sick, would test a different
   line count; the other items of that list need a live screen.
5. **Drawing**: part 1, how a text is laid out and drawn
   (`app.vis.Text`), **done** on 2026-10-16, `text-drawing.md`. Part 2,
   how a document page is laid out (`PaperInnerVisuals`), **done** on
   2026-10-16, `page-layout.md`. The newspaper's fallback rules run on
   real headlines: **done** on 2026-10-16 (`newspaper-picture.md`).
   Part 3, the fact pictures of a page (`BoothEnv.getImage`) and the
   picture operations they use (`paste` with its modes and tint, `copy`,
   `fill`, `replace`, `tint`, `transformed`), **done** on 2026-10-16,
   `fact-pictures.md`.
   Part 4, a paper's pictures on the desk (`DeskItem`: its pictures,
   clipping, drawing, clicking, picking a mark with `compareProximity`,
   stamp ink) and `Image.render`, **done** on 2026-10-16,
   `desk-pictures.md`.
   The desktop values of the layout's booth rectangles: **done** on
   2026-10-16 by running the `Layout` constructor in the emulator,
   `booth-layout.md` (done before part 5, which needs them).
   Part 5a, the desk item's movement: **done** on 2026-10-16,
   `desk-movement.md`. Part 5b, the inspect mode: **done** on
   2026-10-16, `inspect-mode.md`. Part 6, the rest of `app.vis`:
   **done** on 2026-10-16, `vis-basics.md`. Part 7, the rest of
   `play.ui`: **done** on 2026-10-16, `ui-parts.md`. Input handling:
   **done** on 2026-10-16, `input-handling.md`. (This said on 2026-10-16
   that the search photo was also left; that was wrong, corrected on
   2026-10-17: its pictures were read in part 3, `fact-pictures.md`, "The
   search photo", and how it prints onto the desk in part 5a,
   `desk-movement.md`, `PRINTTOP`. The sentence was copied from an old
   note in `text-drawing.md`, corrected the same day.)
   The Unity side, how the game's draw list reaches the screen:
   **done** on 2026-10-17, `screen-output.md`. **The drawing step is
   done.** It answered: the drawing order inside a layer (the order the
   visuals were added) and between layers (lowest number first); who
   reads the change counter (the host, re-sending the picture); how the
   570 x 320 picture is fitted to the window; what the `phantomCursor`
   shows. Left then, because they are not in the code but in the
   Unity scene and shader files: how the quad shader combines the colour
   and blends, the colour space, the full-screen fit, whether the
   phantom cursor is visible; answered in step 5b (below). Where a
   fractional position lands is the graphics card's rule (assumed, the
   usual one).
5b. **The Unity scene and shader settings: done** on 2026-10-17
   (`screen-output.md`, "The Unity files", "The quad shader", "The
   host's second cursor"). Read with UnityPy 1.25.4 (installed with the
   user's approval into `.venv/`, about 13 MB with its libraries) by
   `scripts/unity/scene_dump.py`; the shader programs disassembled with
   Windows' `D3DCompiler_47.dll`; checked by
   `scripts/checks/unity_scene_check.py` (`0 problems`). Answers: colour
   multiplied in and ordinary alpha blending; gamma colour space; the
   screen quad a plain copy on black; 100 pixels per unit, upscale
   render texture off; the window resizable; the phantom cursor hidden
   behind the picture. Not from the files: the Pixel Perfect Camera's
   full-screen and resized-window fit (its documentation), the
   graphics card's rounding.
6. **Audio extraction: done** on 2026-10-17 (`audio.md`). It was in
   `sharedassets0.resource`, as guessed (now checked: 111 clips, nothing
   else). `scripts/unity/audio_extract.py` writes 111 WAV files and an
   index into `extracted/audio/`; `scripts/checks/audio_check.py`
   (`0 problems`) checks them against the stored data (a second ADPCM
   decoder agrees on all 108 effects), `Sounds.xml`, `Ends.xml` and the
   mixer. The host's sound player is read and in `host.py`. Left: the
   songs' browser format (a decision, and a tool download, below) and
   `app.aud` (step 6b, done since). (The language zips in `StreamingAssets/loc/`
   were also here: only `en.zip` is needed, and it is a plain zip that
   Python reads; compared with the archive on 2026-10-16,
   `language-pack.md`.)
6b. **The game-side audio layer: done** on 2026-10-17
   (`audio-layer.md`). All of `app.aud` in
   `decompiled/all/app_aud.clean.c` read, with `app.Num.lerpScale`,
   `app.Clock` and every caller found by name; two Ghidra runs
   (`decompiled/aud_run1.txt`, `aud_run2.txt`) for dropped arguments and
   the volume setter; the reference `scripts/reference/aud.py`; checked
   by `scripts/checks/aud_check.py` (`problems: none`) and, for the beat
   table against the recordings, `scripts/checks/music_beat_check.py`
   (`problems: none`; needs numpy). Answers: `Speaker` (rooms, the
   ignore switch, pause and resume of effects only, stop all with its
   effects-only default), `SpeakerSound` (straight-line fades, the 0.01
   jump, stopping at 0.001), `Music` (the same song plays on, a change
   fades the old one out over 4 s), `MusicBeat` (a tempo table that fits
   `Theme`; the title's rise takes about 23.6 s, `screens.md` part 2).
   Corrected: "all sound" paused and stopped in `save-format.md` and
   `screens.md`. Not from the code: which booth state a day starts in,
   so which ambient loop is heard at full level at first.
7. **Sort the open questions: done** on 2026-10-17 (added 2026-10-14 at
   the user's request). All 151 items were put in one of five kinds (28
   answered and closed, 41 need the game, 21 are the user's decisions, 40
   will not matter for a desktop port, 35 could bite during the build;
   some items were split, so 165 lines in all; the sheet was a scratch
   file, not kept). The result is the shorter list below, in four parts
   (the answered ones are gone), and `docs/DESIGN.md`, which then held
   only the decisions list (the architecture followed in step 8). No code was read and nothing was run: an item
   that could bite got "assume this, settle it when building that part",
   not an answer. The few answered on the way: the game's log has nothing
   of the border scene but the test player's `BusyWithBorder` queue lines;
   a desktop PC's `canVibrate` is false (`audio-layer.md`).
8. **Design the Rust port: done** (2026-10-17). The three decisions
   "needed before the first Rust code" in `DESIGN.md` are decided (frame
   time, the random sequence, the English pack). The architecture and the
   milestones are written in `DESIGN.md`, with the user's three requests
   of the same day (milestones to try, streamed and kept audio, a game
   kept in the browser) and the user's answers to the five questions
   before milestone 0. Bevy 0.20.0 is downloaded into `.cargo-home/`.
   Each milestone is planned
   and accepted on its own. Still open in `DESIGN.md`: the songs' and
   effects' format (before milestone 2) and fullscreen (milestone 3).
   The first thing to read when the booth is built is
   its state machine (`decompiled/booth_ctor_asm.txt`; first item under
   "Could bite during the build"). `Auto.txt` can serve as a test plan: it
   lists what to do to reach each ending.
9. **Milestone 0, an empty page: built and tried by the user**
   (2026-10-17, `milestone-0.md`). The workspace (`port/`), the test card,
   the fixed step, the service worker, `scripts/build_web.py`,
   `scripts/serve.py` and a browser check. Checked in headless Edge
   (picture size and place, exact pixel values, four window sizes, offline
   start); **not tested**: the frame rate and a smooth step in a real
   window, Firefox, a service worker update, a second device. Next:
   the user tries it (two commands in `milestone-0.md`), then the plan for
   **milestone 1, pictures and text**. The WebAssembly is 26 MB (5.4 MB
   gzip), larger than hoped: no smaller-build work was done yet.

10. **Milestone 1a, the font test pages: built and tried by the
   user** (2026-10-18, `milestone-1.md`). New: the start pack builder
   (`scripts/build_assets/`), the Python reference
   (`scripts/reference/fontpage.py`), in `pp_core` the pack reader, PNG
   decoding, fonts, text layout and the software drawing, the 35 pages,
   and the host showing them (arrow keys change page). Checked: 44 unit
   tests and a test of all 35 pages against the reference (byte for
   byte), and headless Edge reading the canvas back (6 page views and the
   offline start, all identical). **Not tested**: against the running
   game, the drawing time in a real browser, Firefox. Findings: a half-pixel
   position damages letters under the assumed card rule
   (`screen-output.md`); the reference's line breaker can loop for ever at
   one edge (`fonts.md`). Next: the user tries 1a (two commands in
   `milestone-1.md`), then the plan for **1b, the title screen as a
   still** (done since, step 11).

11. **Milestone 1b, the title screen as a still: built and tried by
   the user** (2026-10-18, `milestone-1.md`, "1b"). Before it, the
   fix for the page swallowing F5, F12, Ctrl+R and right click (Bevy's
   `prevent_default_event_handling`, now off; a check for it in the
   browser check). New: `scripts/reference/titlescreen.py`, the title's
   pictures and texts in the start pack, `port/core/src/title.rs`, the
   host's `?page=title` (now the default), `port/core/tests/title.rs`,
   a title step in the browser check. Checked: 46 unit tests, the title
   byte for byte in `cargo test` and in headless Edge, a look in the
   app's browser pane. **Not tested**: against the running game (a
   screenshot of the real title would test the 5-pixel menu gap),
   Firefox. The user tried it, with the fix, on 2026-10-18 (which
   browser was not recorded). Next: the plan for **milestone 2** (`DESIGN.md`, "Milestones").

Small jobs that fit anywhere:

- `scripts/reference/booth.py` and `news.py`, when run by hand as scripts,
  still use the **first** story seed. A new game uses the second
  (`run-and-seeds.md`); `compare_with_log.py` already does this correctly.
- `booth.py` does not call `desk.py` or `speech.py` itself; only
  `compare_with_log.py` chains them. A single "play a day" reference that
  owns all three would be tidier.
- `scripts/checks/booth_check.py` was not re-run after `desk.py` was added
  (`booth.py` itself was not changed).
- **Out-of-date "not studied" notes** were swept on 2026-10-14 (36 fixes in
  18 docs, `MODLOG.md`). Left as they are because the records do not say
  which parts the comparison runs exercised: the line "Nothing here has
  been compared with the running game" in `papers-on-desk.md`,
  `operations-and-fact-validity.md`, `value-helpers.md` and `haxe-maps.md`.
  The sweep only looked for "not known" notes answered later; the docs were
  not re-read in full.

## Open questions and unconfirmed items

Sorted on 2026-10-17 (step 7) from the older list of 151 items. The older
list was grouped by session; this one is grouped by what has to happen next.
Every item says why it is still open and where the detail is. Items that were
answered are gone from here (their answers are in the docs named in
`MODLOG.md`, step 7). Kinds:

1. **Could bite during the build**: not known yet, and the port may need it.
   Each says what the port assumes meanwhile and when to settle it.
2. **The user's decision**: in `DESIGN.md`, not repeated here. All decided
   on 2026-10-17 except the songs' format and fullscreen in a browser.
3. **Needs the game to run**: one watch list per doc, below; none blocks the
   build.
4. **Will not matter for a desktop port**: left as they are, with the reason.

(The fifth kind, answered by a step already done, has no list: those items
were closed and the docs that still said "open" were fixed.)

### 1. Could bite during the build

Read these in the order of the port's build. The first two matter most.

- **The booth's own state machine** (`empty`, `entering`, `intro`,
  `busy-with-border`, `detaining`...) is known only where `Border` touches it.
  The decompiler times out on the `Booth` constructor, where the states are
  set up; its instructions are in `decompiled/booth_ctor_asm.txt` and list the
  state names and callbacks in order. It also decides which ambient loop is
  heard at a day's start and which six states select the street noise
  (`audio-layer.md`). *Settle first when the booth is built.* Assume nothing;
  read it.
- **Who sends the scene to `waiting-to-fade-to-night` on a day that ends by
  the clock** (`border-scene.md`). *Settle when the day's end is built.*
- **What `canDetain`, `forceDeny`, `slow` and `special` do in play** beyond
  what `responses-and-events.md` shows; what the day's token list and
  `Bulletin/PageMask` are for; which classes besides `BoothEnv` call
  `addPaper`. *Settle when the booth's rules are ported.*
- **`Auto.txt`**: the order in which instruction blocks are consulted, and how
  each action is carried out (`test-tooling-files.md`). Needed for the
  milestones' test plan (`DESIGN.md`).
- **Whether there is exactly one `BoothEngine` per day** (one "recent error
  groups" memory). Assume yes (the comparison runs agree).
- **`Facts.xml` `<cite when="*bomb">`**: whether the `*` is stripped before
  the "contains" test. One entry. Assume it is stripped; check when the bomb is
  ported.
- **A saved name-cycler position** is not modelled in the reference. Settle
  when loading a game is built (the names must go on where they were).
- **Other users of the random generators**: `Day.borderRand` outside the
  border classes (`border-figures.md`); the seeds of 6 minor generators
  (`rand.md`); other callers of `Array.sort`, an unstable quicksort (known
  users: the news list, the night's budget, the save tree's children). Assume
  none touches the booth's sequence; the comparison run would show it.
- **The data slips the port must reproduce**: `ask-forgery-asylumgrant` reads
  a fact that does not exist (`speech.md`); `=!` in `EZIC_DIPLO` makes a group
  that never runs (`responses-and-events.md`); the 4th recording of a sound
  with more than three never plays (`sounds-xml-format.md`).
- **Border scene**: what the rifle key paper does after unlocking, and whether
  an unlocked rifle stays unlocked on later days (`border-shooting.md`);
  `Endless.csv` leaves `LINE` blank in four columns (`endless-mode.md`).
- **News**: who sets `Day.whenAddNews`; whether endless mode has news and a
  bulletin (by the code an endless day is queued straight as the day screen).
  `news-txt-format.md`.
- **Endless scoring**: a Perfection run with one traveler and one citation
  scored 0 (seen in the statistics file); inferred: the citation ended the
  run before the traveler's points were added; the order of the two actions
  was not read (`endless-mode.md`). `StringUtil.formatTime` (the result
  box's time) is not read.
- **Load screen**: positions not read (heading, ending marks, day headers,
  drag hints) and the line between a save and its parent
  (`LoadButton.drawConnectingLine`); the summary box builds that day's news
  with a generator seeded 0, so its headline need not be the day's real first
  one; when "the saved day is not later than the parent's day" applies
  (`save-format.md`); the save button's date and time use the browser's clock.
- **The night's messages**: `DayLib.getNightMessages` asks `Days.csv` for a
  cell `NIGHTMSG` that the file does not have; what the table reader returns
  for a missing name was not read. Assume no messages (the reference passes
  none; `night.md`, `screens.md` part 1).
- **Screens**: the stamp bar's `BOUNCEBACK` curve, when the bar drops its
  sliding button, and what its click does (`buttons.md`); the flash's size
  (game or window pixels), the order inside one frame of a state's timed
  functions and the screen's update, and what `setPaperPoisoned`'s argument
  means when the poison is touched (`screens.md` part 11); what the "instant"
  option of `Stater.go` changes; how the endless descriptions' line breaks
  (from the English pack) come out; the credits list's height (about 2,272,
  not recomputed).
- **Drawing**: `BoothEngine.applyUpdatedSettings` (what the nudity setting
  redraws); whether anything reads the alpha-1 pixels of a fingerprint
  picture; the sprite origin (a quad's top left sits at the given pixel,
  `screen-output.md`; the night preview takes it that way, so probably
  answered: confirm when the first sprite is drawn); which pixels a
  fractional quad covers (assumed: the nearest pixel, a half rounding down;
  a WebGL draw into a 570 x 320 picture should match; not tested).
- **Line breaking** (`Font.split`): reconstructed from scrambled decompiler
  output; checked against the English texts (`text-drawing.md`), edge cases
  untested.

### 2. The user's decision

All of these are in `DESIGN.md` (decided, suggested or open), with a
suggested default for each. Three come before the first Rust code: frame
time, how exactly to copy the random sequence, and when to apply the English
pack. Not repeated here.

### 3. Needs the game to run

Collected so the user can watch them in one go, or the longer comparison run
(step 1 of "Next steps", postponed by the user) can cover them. **Nothing
below blocks the build.** The watch lists are at the end of each doc (items
and time are in the doc):

| Doc | Items | What |
|---|---|---|
| `audio-layer.md` | 6 | a song under the pause screen, `Theme` fading into the day, both ambient loops at a day's start, the cross-fade when a traveler comes in, `Theme` going on to the load screen, the title's 24-second rise |
| `audio.md` | 5 | the title's song, an ending's song, the never-played 4th recordings, a volume of 0, the very quiet breathing-in sound; also whether sounds pause when the window loses focus (no caller of `SetPauseForAppLostFocus` found; the port assumes no pause) |
| `screen-output.md` | 5 | window size, full-screen fit, the phantom cursor over bars, a half-opacity seal's colours, resizing |
| `input-handling.md` | 5 | the game's cursor and the hand, no cursor before the first move, the double click, the rifle's scope, the right button |
| `desk-pictures.md` | 6 | closed paper size, tilt and shadow; docked papers untilted; the drawer envelope; the drag shadow; clicks through see-through pixels; a long citation message |
| `fact-pictures.md` | 6 | the id card's mirrored photo, the criminal photos' size, the seal sheet's one-pixel drop and others |
| `text-drawing.md` | 3 + 3 | the settings header box, the intro caption's lines, a typing caption; and the surprising ones: a missing letter's box, the rounded background's extra pixel, a one-line text as wide as the widest line |
| `screens.md` part 11 | 4 | no tutorial on day 1, the border explosion's shake, the time bomb's flash, the poison touch; and a flash to the title freezing a running shake |
| `night-pictures.md` | 7 + 1 | a token, an upgrade, a death, five members, the Obristan passports; a member with four badges would run 7 pixels past the right edge |
| `buttons.md` | 6 | the pressed look, sliding off and back, letting go outside, a press that starts outside, the hand cursor, the stamp bar's blinking reason button; no hover buttons in a desktop booth; the border button's click margin |
| `language-pack.md` | 2 | `WATCH_GIVER0` says "All Arstotzkans are same."; `KID_KILLER2` says "Damn it."; `Gender` shows as `Sex` |
| `screens.md` part 7 | 3 | the title's buttons through the code box; a worse second endless run leaves the best score; how the result box writes the time |
| `screens.md` part 6 | list | the credits screen |
| `screens.md` part 5 | list | the intro and endings, whether the first picture wipes in, the second click on NEXT restarting the fade |
| `screens.md` part 4 | list | the pause and settings screens |
| `screens.md` part 1 and 2 | lists | the night screen's moving parts (a tick that cannot be afforded, the sleep button while appearing, the orders of budget lines for none, one and two sick members, penalties and bribes), the title screen |
| `screens.md` part 3 | list | the load screen (a copy of `extracted/saverun` shows most of it) |
| `save-format.md` | - | deleting a save; whether the first number in `names.sav` is the launch's master seed (a hand-played game's first travelers could then be predicted) |
| `border-scene.md` / `border-view.md` | - | `trucke1-decide` (the second attacker skips his throwing animation, one of three ways); no panning, no cameras, no slow motion on desktop (day 2 has the first attack) |
| `borderanim-xml-format.md` | - | five animation prefixes that also collect another group's frames |
| `newspaper-picture.md` | - | nothing in it compared with the game; the stamp's angle (used as radians?) |
| `night.md` | - | penalties, bribes, attacks, the scheduled events and the endings were not exercised |
| `comparing-with-the-game.md` | - | the reference matches one seed, days 1 to 4 (36 travelers) plus day 1 of a second route. The fingerprint, thumbprint and contraband draws (`desk.py`) come after the last pick the log can show, so they are untested; the same for the inference that `BoothEnv.auto...` serve only the test player. A longer run covers these |

### 4. Will not matter for a desktop port

Left as they are, with the reason. Do not spend time on them.

- **Phone, tablet and platform code**: the input mode becoming touch and the
  phone swipes; `Tutor`; `wantPlatformKind`; the tablet and phone layouts and
  upgrade pictures; `PlatformChangeButton.png`'s cut and the root save
  button's two pictures; `DURATION_SLOW`; an invalid stash's error at
  start-up; the update-check buttons (`newversion`); the platform side of
  `play.AlltimeStats` (achievements, leaderboards; rule 4).
- **Out by the user's decisions**: other languages (the alias swap sets,
  `[m]`/`[f]` gender switches, characters above 255 in saves, the Language
  row), the age rating, the quit option, leaderboards.
- **Never called or never reached**: `willDraw`; `ButtonReactResult`,
  `Button.cycleMode`, `get_hasBackButtonId`; `Error.requiredPaperIds`; the
  pause screen's `credit` id; the stamp ink layer's first size (every
  stampable paper has one page); a frame with no valid quad; entity switches
  8 and 16 (no name; the port makes its own); the unused data files, 20
  traveler entries nothing refers to, six speech responses named nowhere,
  `DIPLOMAT_FIRST`, who uses `TabParser.expandParams` besides `ErrorLib` (the
  port reads the data its own way), whether DONE stops the credits' fast scroll,
  which platform the frame settings in `HostUnity.CreateGame` are for, facts without definitions (`FilerEnvelope/Title`,
  `Citation/Message`, `Citation/Penalty`); the test scenarios' start,
  the test player's audit pictures and frame capture (`comparing-with-the-game.md`
  "Dead ends"); `Paths.xml` automatic path numbers.
- **Cannot show or be told apart in a port**: the graphics card's blend
  rounding; Unity's samples against FMOD's (the port decodes the WAV files
  from `extracted/audio/`); the quiet `traveler-breathein`; face sheet `M6`'s
  one face and `F1:0`'s dot order; a wrong `Purpose` for an Arstotzkan (the
  data never asks); `Game/Visitor<n>`, `Game/Stat/Day`; who changes the
  clock's global speed (desktop has no slow motion, so 1); the first night 3 of
  the hand-played game (what was clicked cannot be read from a save; the
  rules are not in doubt).
- **Predictions that only test the reading**: on the first title screen,
  Escape to skip the rising title should also quit when the key is let go
  (the port has no quit).
- **Tooling**: two Ghidra analysis errors and 36 functions without a typed
  signature (`ghidra-workflow.md`); neither has mattered.

## Verification against the original

The stated problem: the original's screen cannot be seen, so the port is
checked with numbers and logs.

- **A screenshot from the user (works, since 2026-10-14).** A picture the
  user pastes into the session can be read and measured. One night-screen
  picture confirmed the order of eight budget lines and four horizontal
  positions to about a pixel (`screens.md`, part 1, "Compared with a
  screenshot"). The scale was taken from a picture of known width in the
  shot. Pictures are not kept in the project.

- **The game's own test player (works, the main method).** The game ships
  with an automated player. A file `auto.plan` in the save folder switches
  it on, fixes the master seed and turns on the detailed log; the command
  line word `savedir <folder>` moves the save folder into this project, and
  the test player keeps its saves in memory, so real saves are untouched.
  Full instructions and the log format: `comparing-with-the-game.md`.

      game\PapersPlease.exe savedir C:\Users\farha\dev\papersplease_rea\extracted\autorun

  The log lands in `%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\Player.log`
  (Unity's own folder, outside the project); copies of the runs so far are
  in the gitignored `extracted/autorun/`. **Each launch needs the user's
  go-ahead.**
- **Comparing a log with the reference**:

      python -I scripts\checks\compare_with_log.py scripts\reference extracted\art\assets extracted\autorun\Player.route20.seed12345.log 12345

  Result so far: route 20, seed 12345, days 1 to 4: 36 of 36 travelers match
  on entry, nationality, duration, purpose, papers, error, always-errors and
  additional error. Route 1, day 1: 8 of 8. Without the desk draws 30 of 36;
  without the spoken lines 32 of 36.
- What that confirms: the seed chain; reading traveler scripts; the person,
  document values, error choice and additional error (by their draw
  counts); the desk draws; the spoken-line draws. What the log cannot show:
  names, faces, id numbers and document values directly (they are only
  confirmed through the draw counts).
- **Emulator** (works): run self-contained pieces of the real code in
  Ghidra's emulator. Used for `app.Rand` (`EmulateRand.java`) and the
  string hash (`EmulateStringHash.java`).
- **Reference scripts checked against the code or the calendar**: `rand.py`
  (emulator), `gdate.py` (every day 1800 to 2200), `haxemap.py`.
- **Checks against the data files**: one script per data file in
  `scripts/checks/` (arguments in its `README.md`). These compare the files
  with what the code reads; they are not comparisons with the running game.
- **A real save folder (works, the second method).** Start the game with
  `savedir` pointing at an empty folder in the project and play by hand;
  the folder then holds the saves, settings, statistics and name position
  as encrypted text files (`save-format.md`). The folder from 2026-10-14 is
  `extracted/saverun/` (gitignored).

      python -I scripts\reference\savefile.py extracted\saverun dumps\il2cppdumper\stringliteral.json
      python -I scripts\checks\save_check.py scripts\reference extracted\saverun dumps\il2cppdumper\stringliteral.json
      python -I scripts\checks\save_night_check.py scripts\reference extracted\art\assets\data extracted\saverun dumps\il2cppdumper\stringliteral.json

  Result so far: all 8 files decrypt and re-encrypt to the same text; the
  save tree (four saves, one branch) and each save agree with the code
  reading (`0 problems`); the night model reproduces the night before each
  of the four saves with exactly one of 24, 56, 288 and 352 possibilities,
  three with nothing bought and one with everything bought. A stash from a second folder (`extracted/stash_sample`, a day-1 stash
  after one traveler) is read and compared with the description by

      python -I scripts\checks\stash_check.py scripts\reference extracted\stash_sample dumps\il2cppdumper\stringliteral.json extracted\art\assets\data

  (`0 problems`). What a save can show: the story facts after
  each night (family, money, statistics, staying papers, script flags). What
  it cannot: the story seed is not saved, so it gives no randomness, and
  it does not record what the player did.

## Things that exist only on this machine

All gitignored. Nothing below is in git.

| Path | Size | What | How to recreate |
|---|---|---|---|
| `game/` | 90 MB | Copy of the GOG install | Copy `C:\GOG Games\PapersPlease` |
| `dumps/il2cppdumper/` | 31 MB | Names, layouts, string table | `il2cpp-name-recovery.md` |
| `decompiled/ghidra/` | about 590 MB | Analysed Ghidra project with names and types | `ghidra-workflow.md` steps 1 to 3 (about 20 minutes) |
| `decompiled/*.c`, `*.clean.c` (16 files), `decompiled/*.txt` (49 files) | about 4 MB | What is not in `decompiled/all/`. The `.c` files: library functions the game calls (Haxe's maps in `maps`, `Array.sort` in `news2`, `Lambda.has` in `paperhelpers2`, `Math.random` in `seedsrc`, `String.GetHashCode` in `strhash`, `Xml` and the XML parser in `xml`, three unnamed helpers in `border_misc` and `border_view2`; 41 functions in all), each with a cleaned copy. The `.txt` files: machine-code listings (among them `booth_ctor_asm.txt` and `layout_ctor_asm.txt`, the only readable form of the `Booth` and `Layout` constructors, on which the decompiler times out), string lists in machine-code order, and Ghidra logs with search results. The older decompiles of the game's own classes were removed on 2026-10-15: every function in them is in `decompiled/all/`, identical or better (`MODLOG.md`) | Step 4 of `ghidra-workflow.md`, with the addresses in each file's `// =====` lines; for a listing, `DumpAssembly.java` or `ListStringUses.java` with the address in its `MODLOG.md` entry |
| `extracted/checks/` | small | Test face pictures, the overview of all faces, the face height survey | `faces.py` (`show`, `overview`, `survey`) |
| `extracted/Art.dat` | 3 MB | Archive cut from `sharedassets0.assets` by hand | Offsets in `art-dat-format.md` |
| `extracted/art/` | 9 MB | The 614 unpacked files | `art-dat-format.md` commands |
| `extracted/endlessrun/` | small | The save folder of the endless-mode test of 2026-10-16 (`screens.md`, part 7): settings with endless unlocked, statistics with one best score, names | Run the game with `savedir` pointing at an empty folder, type the code 62131 on ENDLESS, play one run |
| `extracted/saverun/` | small | A real save folder: the user's hand-played game of 2026-10-14 (four saves with one branch, settings, statistics, name position) | Play again with `savedir` pointing at an empty folder (`save-format.md`); the same game cannot be recreated |
| `extracted/stashrun/`, `extracted/stash_sample/` | small | The stash test of 2026-10-14: the test's save folder as it ended (no stash, it was deleted by the click on "Story"), and a copy taken after the first launch that still has `stash.sav` | Play again as described in `save-format.md` ("The stash test in the running game"); the same stash cannot be recreated |
| `decompiled/booth_ctor_asm.txt` | about 0.5 MB | Read for part 2 of `save-format.md`: the instructions of the `Booth` constructor and of `HostUnity.CreateGame`. (The stash, `GameTransition` and `play.screen` functions read for that part are in `decompiled/all/`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1801b9100` and `0x1809e7b00` |
| `decompiled/titlescreen_update_asm.txt`, `loadscreen_strings.txt` | small | For `screens.md`, parts 2 and 3: the instructions of `TitleScreen.update`, and the strings of three load-screen functions in machine-code order | `DumpAssembly.java 0x180676bc0`; `ListStringUses.java` with `0x1806f4810`, `0x1806ee2e0` and `0x18093d4f0` |
| `decompiled/all/` | about 44 MB | **The whole game decompiled once** (2026-10-14): every function of the game's own classes (6,856 of 6,858; not the social service and Steam), one file per part with a cleaned copy, the address lists in `lists/`, two Ghidra logs, and `booth_react.short.c`. Search here first for "who else does this?" | `ghidra-workflow.md`, "The whole game, decompiled once": `game_function_lists.py`, then `DecompileFunctions.java` with `@` list files (about 19 minutes), then `clean_decompile.py` on each file |
| `decompiled/drawing5_run1.txt` to `drawing5_run3.txt` | under 1 MB each | For `desk-movement.md` (and part 5b): the instructions of the `Filer` and `InspectUi` constructors, `InspectUi.updateOverlay`, `Paper.set_mountPos` and `get_mountPos`, `DeskItem.animateReveal`, `startCustomDrag` and `FUN_180131040`; the strings of `updateOverlay`, the `InspectUi` constructor, `InspectUiDiagram.set` and its constructor | `DumpAssembly.java 0x180873270 0x18061c9e0 0x1804bedb0 0x1804b58b0` with `ListStringUses.java 0x1804bedb0 0x1804b58b0 0x1808ea280 0x1808e8910`; then `DumpAssembly.java 0x180454d60 0x18061b880 0x180131040`; then `DumpAssembly.java 0x18045cbc0` |
| `decompiled/layout_emulation_run1.txt` | about 1 MB | For `booth-layout.md`: the log of the `EmulateLayout.java` run (every stub call and the finished objects' memory), which `layout_dump.py` and `layout_check.py` read | Step 4 of `ghidra-workflow.md` with `-postScript EmulateLayout.java`, output redirected to the file (about a minute) |
| `decompiled/drawing4_run1.txt` | under 1 MB | For `desk-pictures.md`: the instructions of `DeskItem.updateClipRects`, `PaperDef.generateRotatedOuterImage` and `PaperInnerVisuals.compareProximity`, and the string list of the `Paper` constructor | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x18045dfe0 0x180612010 0x180615fe0` and `ListStringUses.java 0x180616b80`, output redirected to the file |
| `decompiled/drawing3_run1.txt` | under 1 MB | For `fact-pictures.md`: the instructions of `System.Math.Cos` and `Sin`, `Math.round`, `EmblemLib.getValidImage`, `FingerprintCode.getImage`, `BoothEnv.getImage` and `Image.transformed` | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1803c21e0 0x1803c2430 0x1808a84d0 0x1807b5540 0x180878e10 0x180477970 0x1809f95e0`, output redirected to the file |
| `extracted/previews/factpics/` | small | Previews from `factpics.py` and `pages.py` (fact pictures, pages with them, the night screen), made from the game's art | `factpics.py <assets> extracted/previews/factpics`; `pages.py ... --png` |
| `extracted/previews/deskpics/` | small | Previews from `deskpics.py` (closed papers at three tilts, a wall plaque, a passport in the drawer envelope, a drag shadow), made from the game's art | `deskpics.py extracted/art extracted/previews/deskpics` |
| `decompiled/step5_run1.txt` to `step5_run3.txt` | under 1 MB | For `text-drawing.md`: the instructions of `Text.buildTiles` and `Visual.renderToImage`, of `Image.paste`, and of `Font.split` | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x18066ef30 0x1807d4480`, then `0x1809f5f80`, then `0x18087f080`, output redirected to the file |
| `decompiled/part11_run1.txt` | under 1 MB | For `screens.md`, part 11: the instructions of `System.Math.Cos` and `Sin` (which helper is which), `ScreenShake.update`, `Game.createStater` (the fade targets) and the function that ends the flash to the title | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1803c21e0 0x1803c2430 0x1808635e0 0x18058a9e0 0x18058a580`, output redirected to the file |
| `decompiled/part10_run1.txt` | under 1 MB | For `night-pictures.md`: the instructions of the `FamilyVisuals` constructor (the name field, the alignment, the passport halving, the count's gap, the empty-token test) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x18074cdc0`, output redirected to the file |
| `decompiled/part9_run1.txt` | under 1 MB | For `buttons.md`: the instructions of the `Border` constructor (the booth button's click margins) and of the `HoverButton` constructor (the arrow's position) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x180437070 0x1809eb520` |
| `decompiled/part7_run1.txt` | under 1 MB | For `screens.md`, part 7: the instructions of the `UnlockConfirm` and `EndlessScreen` constructors, `EndlessScreen.refreshScoreTexts`, `ScoreEntry.isBetterThan` and `ScoreEntry.toString` | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1806859c0 0x1807c1390 0x1807c6fc0 0x1808608d0 0x180860900` |
| `decompiled/part5_run1.txt` | under 1 MB | For `screens.md`, part 5: the instructions of the `EndScreen` constructor and the strings of the `Intro` and `EndScreen` constructors in machine-code order | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1807b9800`; `ListStringUses.java` with `0x1808fae90` and `0x1807b9800` |
| `decompiled/settingsmenu_music_asm.txt`, `part4_run1.txt` to `part4_run3.txt` | small | For `screens.md`, part 4: the instructions of `SettingsMenu.musicButton_whenClick`, and the Ghidra output of three runs (string lists of four functions in machine-code order, three caller searches). (The key, `InputWrapper` and `HostUnity.Update` functions read for that part are in `decompiled/all/top.clean.c` and `app_ent.clean.c`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x180714b30`; `ListStringUses.java` with `0x180710150`, `0x180869f50`, `0x18086a9b0`, `0x1808035e0`; `FindReferences.java` with `0x18086FAF0`, `0x180870B30`, `0x1804AA120`, `0x180870210` |
| `decompiled/budgetent_ctor_asm.txt`, `budgetent_ctor_strings.txt`, `asm_family_buildmessage.txt` | small | For `screens.md`, part 1: the instructions of the `BudgetEnt` constructor and of `Family.buildMessage`; the `BudgetEnt` constructor's strings in machine-code order. (The `play.night`, `RevealTextEnt` and `GameScreen` functions read for that part are in `decompiled/all/`) | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1806c2a70` and `0x180757930`; `ListStringUses.java 0x1806c2a70` |
| `.venv/` | about 53 MB | Python virtual environment with UnityPy 1.25.4 and its libraries (installed 2026-10-17 for step 5b) | `python -m venv .venv`, then `.venv\Scripts\python -m pip install --only-binary=:all: --no-binary=tpk_ar UnityPy==1.25.4` (`tpk_ar` has no pre-built package; it is built from its 10 KB source) |
| `extracted/audio/` | about 80 MB | Step 6's extraction: the 111 sounds and songs as 16-bit WAV, named by the game's file names (songs `.ogg` made `.wav`), and `audio_index.json` | `.venv\Scripts\python -I scripts\unity\audio_extract.py game\PapersPlease_Data extracted\audio` (about 5 seconds) |
| `decompiled/audio_run1.txt` | small | For `audio.md`: the instructions of `UnityPlatformAudio.setCategoryVolume` and of the `log10` it calls | Step 4 of `ghidra-workflow.md`: `DumpAssembly.java 0x1809a7c10 0x180131510`, output redirected to the file |
| `decompiled/aud_run1.txt`, `aud_run2.txt` | small | For `audio-layer.md`: who uses the two ambient sound names (the `Booth` constructor), the instructions of `Game.applyScreenChange` and `Booth.update` (run 1); of `SpeakerSound.setVolume`, `SpeakerSound.update`, `Speaker.play`, `MusicBeat.getBeat` (run 2) | Step 4 of `ghidra-workflow.md`: run 1 `FindReferences.java 0x180C5E4A8 0x180C5EC50` then `DumpAssembly.java 0x180587a40 0x1801ca450`; run 2 `DumpAssembly.java 0x180720e10 0x180721010 0x1807229d0 0x1806ce650`; output redirected to the file |
| `extracted/unity/` | under 1 MB | Step 5b's dump of the Unity files: every scene, material and settings object as JSON, the four shaders' programs disassembled, `summary.txt` | `.venv\Scripts\python -I scripts\unity\scene_dump.py game\PapersPlease_Data extracted\unity` |
| `extracted/autorun/` | 2 MB | The test player's folder: `auto.plan`, `auto.log`, copies of three `Player.log` runs, and scratch scripts from the fourth session (`show.sh` prints one decompiled function with the noise removed; `rand_uses2.py` lists functions matching a pattern; `log_step.py`; several experiments) | The logs: run the game as above (needs the go-ahead). The scratch scripts are conveniences, not needed |

Outside the project: `C:\tools\Il2CppDumper-6.7.46`, `C:\tools\ghidra_12.1.4_PUBLIC`,
and `C:\Users\farha\.claude\CLAUDE.md` (lists those tool paths for every
project).
Ghidra also keeps a small cache in `C:\Users\farha\AppData\Local\ghidra\`.
Running the game writes Unity's `Player.log` under
`%USERPROFILE%\AppData\LocalLow\3909\PapersPlease\`.

## Scripts

| Folder | What |
|---|---|
| `scripts/ghidra/` | `game_function_lists.py` (address lists of all the game's own functions, for the whole-game decompile); Ghidra scripts (names, types, decompile with `@` list files, references, static writes, string uses, assembly dump, the two emulator checks, and `EmulateLayout.java`, which runs the whole `Layout` constructor), `clean_decompile.py`, `condense_decompile.py` (a shorter view of a cleaned file, for long classes), and `read_doubles.py` (reads the number constants the decompiler shows only as addresses) |
| `scripts/extract/` | `decrypt_art.py`, `unpack_art.py` |
| `scripts/unity/` | `scene_dump.py`: dumps the Unity scene, materials, shaders (disassembled) and project settings with UnityPy (`screen-output.md`, "The Unity files"); `audio_extract.py`: decodes the 111 sounds and songs to WAV with FMOD (`audio.md`). Run both with `.venv\Scripts\python` |
| `scripts/reference/` | Reference implementations. Base: `rand.py`, `tabtree.py`, `seeds.py`, `gdate.py`, `haxemap.py`. Traveler answer key, in layers: `cyclers.py`, `faces.py` (needs Pillow), `person.py`, `travspec.py`, `errormaker.py`, `values.py`, `factlib.py`, `booth.py` (everything chained), plus what happens between travelers: `desk.py` (draws when papers are drawn) and `speech.py` (spoken lines). Others: `news.py` (headlines), `newsimage.py` (newspaper layout and draws; needs Pillow), `nights.py` (night events, budget, the family), `fonts.py`, `paths.py`, `savefile.py` (reads and decrypts a save folder; can also encrypt), `hxserial.py` (reads the text of Haxe's general serializer, as far as a stash needs), `locpack.py` (applies a language pack to the data files and lists what changes; `language-pack.md`), `nightpics.py` (the night screen's family pictures: every picture and text with its desktop position; renders the pictures and texts; needs Pillow to render; `night-pictures.md`), `screenfx.py` (the screen shake frame by frame and the flash to the title; `screens.md` part 11), `text.py` (`app.vis.Text`: lays a text out tile by tile, gives its size, draws a preview with Pillow; `text-drawing.md`), `pages.py` (lays a document page out and draws a preview; `page-layout.md`), `factpics.py` (the fact pictures and the picture operations; `fact-pictures.md`), `deskpics.py` (a paper's pictures on the desk, clipping, picking a mark, stamp ink, `Image.render`; `desk-pictures.md`), `deskmove.py` (how a paper moves, frame by frame; `desk-movement.md`), `inspectmode.py` (the inspect mode's rules; `inspect-mode.md`), `vis.py` (colours, point and rectangle text, nine-slice frames, atlas tiles; `vis-basics.md`), `ui.py` (dotted lines, the speech bubble, the drag helper; `ui-parts.md`), `inputs.py` (the mouse, pointers, blocked areas, keys, the cursor's place; `input-handling.md`), `host.py` (the drawing order, the quad batcher, the texture table, the window size, the phantom cursor's place, the assumed pixel rule, the quad shader's colour and blending as `quad_pixel`; `screen-output.md`; and the sound player and the category volume in decibels, `audio.md`), `aud.py` (the game-side audio layer: the speaker, a sound's fades, songs, the beat table, `Sounds.xml` as the speaker reads it, and a stand-in host that keeps time; `audio-layer.md`), `layout.py` (every desktop `Layout` value) and `layout_dump.py` (decodes an `EmulateLayout.java` run; `booth-layout.md`) |
| `scripts/checks/` | Checks against the real data files, `compare_with_log.py` against the running game's log, `save_check.py` and `save_night_check.py` against a real save folder, `stash_check.py` against a real stash, `button_pictures_check.py` against the button pictures, `night_pictures_check.py` against the night screen's family pictures, `text_drawing_check.py` (fonts against the English texts, the font sheets' colours), `page_layout_check.py` (marker pixels of every page picture), `fact_pictures_check.py` (every picture fact, its files and sizes) `desk_pictures_check.py` (every paper's desk pictures) `ui_check.py` (dotted lines, the bubble and the speech lines, the drag helper), `input_check.py` (pointer and key sequences, the cursor pictures), `host_check.py` (the drawing order, batching, the texture table, window sizes, the phantom cursor picture and place), `unity_scene_check.py` (the Unity scene, shaders and settings against step 5b's dump, and `host.quad_pixel`), `audio_check.py` (the extracted sounds against the stored data with a second ADPCM decoder, `Sounds.xml`, `Ends.xml`, the mixer, the host's sound rules), `aud_check.py` (`aud.py`: the beat table, the title's rise, song changes, the ambient loops, rooms, the ignore switch, pausing and stopping), `music_beat_check.py` (the beat table against the songs' note starts; needs numpy), `vis_check.py` (points and rectangles in the data files, colours, frames), `inspect_check.py` (marks per paper, booth things, texts, selection, the diagram), `desk_movement_check.py` (every paper's reveal, the docks, clamps, a fall, a throw, the drag placement) and `layout_check.py` (the emulated layout against `layout.py` and 35 values read by hand); see its `README.md` for each script's arguments |
