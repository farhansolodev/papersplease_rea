# Buttons (`play.ui.Button`)

Studied on 2026-10-16 (part 9 of the screens step; buttons are used on
every screen, in the booth and in the border scene, so they have their own
doc). Code reading, a Ghidra dump of two constructors' instructions, and a
check of the button pictures in the extracted archive
(`scripts/checks/button_pictures_check.py`, below). **Nothing here has
been compared with the running game.**

Terms used below:

- **Look** (the code calls it a *mode*, class `play.ui.Mode`): one way a
  button can appear. A look has a name, a normal picture, a pressed
  picture, an optional text with its two colours and its alignment, and
  optional extra pictures drawn on top ("overlays"). A button holds a list
  of looks and shows one of them at a time.
- **Pressed**: the state while the mouse button (or the button's shortcut
  key) is held down on the button. The button then shows its current
  look's pressed picture and pressed text colour.
- **Click**: what happens when the press ends over the button. The
  button's `whenClick` function runs.
- **Piece of a picture** (`PartData`): a rectangle cut out of a picture.
  Most button pictures hold several looks stacked top to bottom (bands of
  rows) or side by side (columns).

## What was read

All in `decompiled/all/` unless named:

- `play.ui.Button`: the constructor `0x1806a4860` (all its defaults),
  `addMode` `0x1806a6530`, `applyMode` `0x1806a6610`, `cycleMode`, `draw`
  `0x1806a6c20`, `findMode`, `get_modeName`, `set_modeName` `0x1806a7470`,
  `get_hasBackButtonId`, `width`, `height`, `react` `0x1806a7160`,
  `setAsBackButton`, `setImageClip`, `setReactMargin`, `setVisualsLayer`,
  `set_scale`, `get_enabled`, `set_enabled` (in `app_ent.clean.c`). That
  is every method of the class except the reflection helpers.
- `play.ui.Mode`: constructor, `addOverlay`, `apply`, `get_hasText`,
  `setText`, `setTextNormalColor`, `setTextPressingColor`; `setTextAlign`
  by its slot. All of it.
- `play.ui.ButtonHelper`: constructor, `react` `0x1806a3d60`,
  `setReactMargin`. All of it. (`react` was first read in part 4 for the
  shortcut key; read again in full here for the mouse.)
- `play.ui.ButtonReactResult`: its class setup (all it has).
- `play.ui.HoverButton`: constructor `0x1809eb520` (also as instructions,
  `decompiled/part9_run1.txt`), class setup, `draw`, `react`, `update`.
- `play.day.booth.DropButton`: constructor `0x1807ab110`, its two small
  functions, `get_dropped`, `set_dropped`, `set_dropT`, `autoIsAnimating`,
  `update`.
- `app.ent.Input`: `getPointerOver` `0x1804af0f0`,
  `getPointerOverEvenIfCaptured`, the start of `getIntersectsMaskedArea`;
  `app.ent.Pointer`: `captureUntilNextFrameEnd`, `isCapturing`; the
  layouts of `Pointer` and `Cursor` (from the class dump).
- `app.Num.smoothstep`; the start of `app.Interp.get` (enough to see that
  `BOUNCEBACK` is a curve of its own, not its shape).
- `SettingRow.makeModeImages` `0x18086c630` again, now with the picture
  functions named.
- `Res.getImage`, and the loop of the `Res` constructor `0x180775820` that
  loads the archive's files; `Platform.resOverrideDir`.
- Every place that makes a button, for its pictures, looks and colours
  (the list is in "Every button the game makes"). For the screens these
  were read in earlier parts; here only their button calls were read again.
- The `Border` constructor's instructions around the booth button
  (`decompiled/part9_run1.txt`), and the writes of two `Layout` fields in
  `decompiled/layout_ctor_asm.txt`.

Constants read with `read_doubles.py`: 0.5 (`0x180a36c30`), 2.0
(`0x180a36c40`), 1.0 (`0x180a36c38`), 3.0 (`0x180a36c48`), 6.0
(`0x180a36c60`), 0.25 (`0x180a36c28`), 0.1 (`0x180a36c18`), -1.0
(`0x180a6d6c0`).

**How numbered calls were named.** The decompiler often shows a call
through an object's method table as a number (for example `+ 0x2c8`). The
method table starts at offset `0x138` of the class data and each entry is
`0x10` long, so the number gives the slot: `(0x2c8 - 0x138) / 0x10 = 25`.
The slot numbers are in the class dump. Checked on calls whose name the
decompiler did show (`Mode.setText` is slot 25 and shows as `+ 0x2c8`).
This is how `Image.copy` (38), `fill` (28), `paste` (29), `clone` (41),
`flipV` (37), the `Mode` setters and `Mode.apply` (30) were named below.

## A button in short

A button is an entity (`Ent`) that owns one background picture, one text,
and a list of looks. It shows the current look: the look's normal picture,
or its pressed picture while it is pressed, with the look's text on top in
the matching colour, then the look's overlays. It reacts to the mouse
(press over it, let go over it) and, if it has one, to a shortcut key
(only Escape is ever used, which makes it a "back button", `screens.md`
part 4). A click calls the button's `whenClick` function with the button.

There is **no disabled look**. A button that does not take input is drawn
exactly as before. A hidden button is neither drawn nor clicked.

## A new button

`Button(parent, font, pressSound, clickSound)`; any of the last three may
be left out:

| Field | Starts as |
|---|---|
| font | `ui_large` (the game stops with "Font not found: ..." if the font does not exist) |
| sound when pressed | `button-down` |
| sound when clicked | `button-up` |
| shortcut key | -1 (none); `setAsBackButton` sets 5, Escape |
| scale | 1 |
| shown (`buttonVisible`) | yes |
| background picture | an empty picture holder (no picture yet) |
| text | an empty text in the font |
| looks | none; no current look |
| margins around the click area | 0 on all four sides |

## Looks

**Adding a look.** `addMode(name, normalPicture, pressedPicture)` makes a
look and adds it at the end of the list. If no pressed picture is given,
the pressed picture is the normal one (the button then looks the same
when pressed). A new look has no text, white text in both states
(`0xffffffff`) and centred text. **The first look added becomes the
current look at once** and is applied.

The look's setters return the look, so the code chains them:
`setText`, `setTextNormalColor`, `setTextPressingColor`, `setTextAlign`,
`addOverlay`, and `apply` (which makes this look the current one, by its
name).

**Choosing a look.**

- `modeName = name` makes the first look with that name current and
  applies it. If there is none, nothing changes.
- `findMode(name)` returns the first look with that name, or nothing.
- `cycleMode()` makes the next look in the list current, going back to
  the first after the last. No code that calls it was found in the
  whole-game decompile.
- `modeName` (reading) is the current look's name, or an empty text if
  there is none.

**Applying a look** (`applyMode`). This runs when a look is first added,
when the current look changes, and when the button goes from not pressed
to pressed or back. It does not run every frame.

1. The text becomes the look's text, with the look's alignment.
2. The background picture becomes the look's pressed picture if the
   button is pressed, otherwise its normal picture.
3. If the look has a text that is not empty:
   - the text colour becomes the look's pressed colour if pressed,
     otherwise its normal colour, **always fully opaque** (the code adds
     an alpha of 255 to the colour). So a pressed colour given as 0 is
     black;
   - the text's left edge, inside the button: 2 if the background has no
     picture or the alignment is LEFT; `floor(picture width x 0.5 - text
     width x 0.5)` if CENTER; `picture width - text width - 2` if RIGHT
     (not rounded down);
   - the text's top: `floor(picture height x 0.5 - text height x 0.5)`.
     A button's text is one line with no padding, so its height is the
     font's line height and its width the text's width (`app.vis.Text`,
     read on 2026-10-16, `text-drawing.md`; this said it was not read).

   If the text is empty, the colour and position are left as they were;
   nothing is drawn for an empty text anyway.

So a look's text does not move when the button is pressed; only the
picture and the colour change.

**Size.** A button's width and height are those of its background picture
if it has one, otherwise those of its text. (For a picture made larger by
`scale`, what the picture holder answers was not read.)

## Drawing

Each frame, if the button is shown, at the button's position on screen:
the background picture (if it has one and is visible), then the text (if
not empty and visible), then each overlay of the current look (if
visible), in the order they were added. Each goes to its own drawing
layer; `setVisualsLayer(layer)` sets the layer of the background, the
text and the overlays of every look at once.

Overlays belong to a look, not to the pressed state: a look's overlays
are drawn the same whether the button is pressed or not, and they change
only when another look becomes current. (The load screen and the endless
screen use them, below.)

## How a button reacts

Each frame the button gets input (`Button.react`), if it is shown:

1. The click area is the button's rectangle on screen, widened by the
   four margins (`setReactMargin(left, right, top, bottom)`).
2. **The shortcut key**, if the button has one and the click area is not
   under a blocked area of the screen (part 4 of `screens.md`, unchanged):
   - while the key is down: the button is pressed; `button-down` (or the
     button's own press sound) plays on the first frame only; **the mouse
     is not looked at that frame**;
   - on the frame the key goes up, if the button was pressed: not pressed
     any more, the click sound plays, and the button is clicked;
   - otherwise go on to the mouse.
3. **The mouse.** The game looks for pointer 0 (the mouse):
   - first, a pointer that this button has "taken" (see below), wherever
     it is now, unless it is over a blocked area;
   - otherwise a pointer that no entity has taken, inside the click area,
     not over a blocked area; one whose button is down is preferred.

   With no such pointer, the button is not pressed. With one:
   - if the pointer is inside the click area and no other entity has set
     the cursor this frame, **the cursor becomes the hand**;
   - if the button has not taken the pointer and the mouse button went
     down this frame: the press sound plays and the button **takes** the
     pointer (`captureUntilNextFrameEnd`: other entities then ignore it;
     the hold lasts until the end of the next frame and is renewed every
     frame while the mouse button is held);
   - if the button has the pointer: it is pressed while the mouse button
     is down **and** the pointer is inside the click area. When the mouse
     button goes up, the button is clicked only if it was pressed on the
     frame before and the pointer is still inside: then the click sound
     plays. While the mouse button stays down the hold is renewed.
4. If the button was clicked, `whenClick(button)` runs.
5. If pressed changed this frame, the look is applied again (picture and
   text colour).

What the player sees, by the code: press on a button and it shows
pressed, with the press sound. Slide off while holding: it shows normal
again, but stays "taken"; slide back on: pressed again. Let go over it:
click, with the click sound. Let go elsewhere: nothing, no sound. Pressing
outside and sliding onto a button does not press it (the mouse button
did not go down over it).

**Taking input on and off.** `enabled` is the entity switch 4 ("takes
input", `screens.md` part 1). Turned off, the button gets no input at all
and looks the same.

**The result kinds** `ButtonReactResult` (`NONE`, `JUSTPRESS`,
`PRESSING`, `CLICK`) are made by the class setup and used by nothing in
the whole-game decompile (searched by name; `ButtonHelper.react` returns
only yes or no). Not needed for the port.

`get_hasBackButtonId` answers whether the id is `back` or `cancel`. No
code that calls it by name was found. (The menu and the confirm box test
those ids themselves, `screens.md` parts 2 and 3.)

## Other settings

- `scale = s`: sets the background picture's horizontal and vertical
  scale. The text is not scaled. Only the border's booth button uses it
  (its value `borderScale` is 1.0 on desktop, `border-view.md`).
- `setImageClip(rectangle)`: the background and the text are drawn only
  inside the rectangle. Used by the two kinds below.
- `setReactMargin`: only the border's booth button calls it (below).

## Every button the game makes

From a search of the whole decompile for every place that makes a
`Button` or one of its two kinds. The last column says where the button
itself is described. "Bands of n" means the picture is cut into bands of
n rows from the top. Colours are written without the alpha; a pressed
colour of 0 shows as black.

| Made by | Picture and cut | Looks | Text, normal / pressed colour | On desktop | Described in |
|---|---|---|---|---|---|
| `GameScreen.makePushButton`, the standard wide button (also through `Menu.addPushButton`) | `PushButton.png` or `PushButtonRed.png`, 129 x 38: band 1 (rows 0-18) normal, a dotted outline; band 2 (rows 19-37) pressed, filled | `normal` | the given text and alignment (CENTER if none); `0x556855` (red: `0xcc2e2e`) / black | yes | `screens.md` parts 1, 2 |
| `Menu.addImageButton(id, picture, rows, font)` | bands of `rows`: band 1 normal, band 2 pressed; with `rows` 0 the whole picture for both | `normal` | none, unless the caller adds one | yes | `screens.md` part 2 |
| Title: `quit`, `settings` | `QuitButton.png` (bands of 17), `SettingsButton.png` (bands of 29), through `addImageButton` | `normal` | none | quit: only if the platform can exit; the user decided on no quit option | `screens.md` part 2 |
| Title: `version` | `VersionButton.png`, bands of 12, through `addImageButton` with font `regular` | `normal` | the version text; `0x3b483b` / black | the title's `version` button, still open for the port | `screens.md` part 2 |
| Title: `credit` | made at run time: normal a 140 x 12 bar filled opaque black, pressed the same bar filled `0x556855` | `normal` | `created_by`, font `regular`; `0x556855` / black (so pressing swaps the two colours) | yes | `screens.md` part 2 |
| `GameScreen.addMediaButtons`: `web`, `twitter` | `WebpageButton.png`, `TwitterButton.png`, bands of 11 | `normal` | none | left out by the user's decision | `screens.md` part 4 |
| `GameScreen.enablePause`: `pause` | `PauseButton.png` or `PauseButtonBlack.png`, bands of 19 | `normal` | none | **no** (only when the layout's `showPauseButton` is set, the portrait layouts) | `screens.md` part 1 |
| `SettingRow`: tick box, minus, plus, device | made at run time (`makeModeImages`, below) | tick box `off`, `on`; minus and plus `normal`; device `phone`, `tablet` | none | tick box, minus, plus: yes | `screens.md` part 4 |
| `SettingRow`: language, rating | made at run time | | | left out by the user's decision | `screens.md` part 4 |
| `LoadScreen`: delete button | `LoadDelete.png`, 29 x 75, bands of 25: band 1 normal, band 2 pressed (for both looks), band 3 the deleting look (red) | `normal`, `deleting` | none | yes | `screens.md` part 3 |
| `LoadButton`: a save, the root (`new-root`) | `LoadButtonNew.png` and pictures made at run time | `normal`, and `deleting` for a save, whose overlay is `LoadButtonDel.png` | none | yes | `screens.md` part 3 |
| `EndlessScreen`: style and course buttons | `EndlessStyleButton.png` (bands of 80), `EndlessCourseButton.png` (bands of 60) | `normal`, with the icon and texts as overlays | none (texts are overlays) | yes | `screens.md` part 7 |
| `EndlessScreen`: `leaderboards` | `LeaderboardsButton.png`, bands of 33 | `normal` | none | left out by the user's decision | `screens.md` part 7 |
| `NightScreen`: sleep button | (`screens.md` part 1) | `normal`; `BudgetEnt.updateBudgetTotal` sets its text again after every balance: the budget's rename if it has one, else `budget_sleep` | | yes | `screens.md` part 1 |
| `UnstashOverlay`: `stash-resume` | `UnstashButton.png`, 149 x 78, halves | `normal` | `menu_resume`; `0x85a4b1` / black | **no** (desktop never restores a stash, `save-format.md` part 2) | `save-format.md` part 2 |
| `PlatformChangeConfirm`: `phone`, `tablet`, `cancel` | `PlatformChangeButton.png` (cut not read); CANCEL is a standard push button and the back button | `normal` | | not studied | `screens.md` part 4 |
| `Border`: the booth button `outer-booth` | `OuterBooth.png`, 56 x 76; normal from the top, highlight from row 38, each as high as the space between the button and the scene's bottom: 103 - 65 = **38 rows** on desktop | `normal`, `highlight`; **no pressed picture** (pressed looks like normal) | none | yes | `border-scene.md` (when it blinks) |
| `StampBar`: the denial-reason button `drop-denialreason` | a `DropButton` (below), `ReasonButton.png` | `normal`, `flash` | none | yes | below |
| `Carousel`: give, hang, confiscate | `HoverButton`s (below) | `normal` | `carousel_give`, `carousel_hang`, `carousel_confiscate` | **no** (below) | below |
| `CriminalPosterPin` | `CriminalPosterPinButton.png`, 140 x 45, four columns of 35 | `wait` (column 1), `0` (column 2), `1` (column 3); column 4 is the pressed picture of all three | none | **no** (below) | below |
| `LangChooser` | | | | left out by the user's decision | |

Not in this list: the border's rifle buttons (`RifleButton`) are not
`Button`s; they are their own entity (`border-shooting.md`).

The booth button's two settings that the decompiler dropped, read from
the instructions (`decompiled/part9_run1.txt`, around `0x180439354`):
`setReactMargin` gets the layout value `borderOuterBoothButtonReactMargin`
for left, right and top, and 0 for the bottom. That value is written once
in the `Layout` constructor, **6**, at `0x18049940b`, next to the first of
the three writes of `borderOuterBoothButton`; the desktop block (the third,
which writes the button's position at `0x18049d290`) does not write it, so
**on desktop the margins are 0**. (This was inferred from the missing
write; running the constructor in the emulator on 2026-10-16 gives 0,
`booth-layout.md`.) The button also starts with input off
(switch 4 cleared); `border-scene.md` says when it is turned on.

### The settings rows' pictures (`makeModeImages`)

Already described in `screens.md` part 4; the picture functions are now
named, which makes two points exact. The normal picture: a box filled
opaque black, with a white dot on every border pixel whose x + y is even
(so the corners at (0, 0) are white and the dots stay in step around the
box). The pressed picture is a copy (`clone`) of it with the inside, 2
pixels in from each edge, filled white (`fill`). The icon is then pasted
(`paste`, mode `BLEND`) at ((box width - icon width) x 0.5, (box height -
icon height) x 0.5) on both; whether `paste` rounds those halves was not
read. The device button's two looks are the upper and lower halves of
`SettingButtonPlatform.png` (34 x 50), cut with `copy`.

## The two kinds built on a button

### The sliding button of the stamp bar (`DropButton`)

The stamp bar makes one, `drop-denialreason`, from `ReasonButton.png`
(72 x 90), with the default font and sounds. The picture is cut into
three bands of 30 rows: band 1 is the `normal` look's picture, band 2 the
`flash` look's, and band 3 the pressed picture of both. The button is
clipped to its top 30 rows.

It slides down from behind a line (`topY`) and back up, run by the game's
state machine (`app.Stater`, `border-scene.md`) with two states:

- `off`: over 0.5 s, `dropT` goes to 0. The button starts here at once.
- `on`: over 0.5 s, `dropT` goes to 1. On entering, the sound
  `button-drop` plays. While in it, every frame: the look is `flash` when
  (time in the state, modulo 0.5 s) is over 0.25 s, otherwise `normal`.
  So **it blinks: 0.25 s normal, 0.25 s flash**, for as long as it is
  down.

Both blends use the curve `BOUNCEBACK(0.1, 1)` (`app.InterpType`); its
shape was not read (it looks like an overshoot and settle). For a given
`dropT`: the button is shown and takes input only while `dropT` is above
0; its top is at `topY - height + height x dropT`; and the part above
`topY` is cut off. `dropped` reads as "the state is `on`"; setting it
goes to `on` or `off`. Who drops it and what a click does are in the stamp
bar's code (`StampBar`, `DropRemote`), not read here.

### The hover buttons of the phone's carousel (`HoverButton`)

Only the phone and tablet build these (next section). In short, for
completeness: font `ui_regular`, press sound `hover-down`, click sound
`hover-up` only if asked for; `HoverButton.png` (120 x 48), top half
normal and bottom half pressed; text `0xe0e9c7` / `0x191212`. Three kinds:
a plain button, or one with an arrow (`HoverArrow.png`, 50 x 32: left
half the arrow, right half its highlight) above or below it, the
down-pointing one flipped. The arrow is centred horizontally; its top is
at the button's height - 6 for the kind `ARROWUP` and at 6 - the arrow's
height for `ARROWDOWN` (from the instructions; the decompiler mixed the
two branches). The button opens from its middle: a value moves 6 per
second towards 1 while shown (towards minus a given delay while hidden),
the button is drawn while the value is above 0, clipped to a centred
width of `width x smoothstep(value)`, and takes input only when the value
is exactly 1. A 20-pixel band of the arrow's highlight sweeps across the
arrow twice a second. The carousel makes three: give, hang, confiscate.

## Pictures only phones have

`HoverButton.png`, `HoverArrow.png` and `CriminalPosterPinButton.png` are
**not** in the archive's main folder; they are only in
`assets/layout/phone/`. On desktop the game never loads the layout
folders at all (read for this step from the `Res` constructor; the rule
is in `art-dat-format.md`, "The layout folders are for phones and tablets
only"). So on desktop `assets/HoverButton.png` and
`assets/CriminalPosterPinButton.png` do not exist, and asking for them
would stop the game ("Res asset not found", `language-pack.md`; `en.zip`
has neither). **Inferred:** a desktop booth makes neither the carousel's
hover buttons nor the criminal-poster pin. (The carousel makes its hover
buttons only when the layout has a `carousel` rectangle. Whether a
desktop booth has a `Carousel` at all was open here; settled on
2026-10-16 in `desk-pictures.md`: the `Booth` constructor makes one only
for the shape `PORTRAIT_THIN`, so a desktop booth has none, and which
`Layout` block writes `carousel` no longer matters for desktop.)

`scripts/checks/button_pictures_check.py` confirms the three are absent
from the main folder.

## For the port

- One button type with: a list of looks (name, normal picture, pressed
  picture, text, two text colours, alignment, overlays), the current
  look, a pressed flag, a click function, an optional shortcut key,
  margins, shown and takes-input switches. A look is applied only when it
  changes or the pressed flag changes.
- Pressed text is drawn fully opaque; a pressed colour of 0 is black.
- The mouse rules above, including "the press must start on the button"
  and "let go outside: no click, no sound", and the hand cursor over a
  button. The shortcut key is used only for Escape (back buttons).
- No disabled look.
- On desktop: no pause button, no resume overlay, no carousel buttons,
  no criminal-poster pin; the stamp bar's sliding button and the booth
  button are needed. The pictures the port needs are all in the main
  folder; the `layout/` folders can be left out of a desktop port's
  assets.
- The pictures and the cuts are checked by the script below; for the
  port's own asset step it lists, in one place, which pictures are cut
  how.

## Checks

```
python -I scripts\checks\button_pictures_check.py extracted\art\assets
```

Prints each button picture with its size and cut, and `problems: 0`:
all 20 pictures are where the code asks for them and divide exactly into
the cuts the code makes (17 in the main folder, 3 only in the phone
folder and absent from the main one). A look at four of them, enlarged,
agreed with the reading: `PushButton.png` has a dotted outline on top
and a filled band below; `LoadDelete.png` has an outline, a filled and a
red band; `ReasonButton.png` has three bands of the same button with the
lamps in different states; `OuterBooth.png` has the booth plain and with
a ring.

## Not studied

- (`app.vis.Text`'s width and height were listed here; read on
  2026-10-16, `text-drawing.md`: one line's height is the font's line
  height, its width the text's width.)
- What a scaled picture answers for its width (`Sprite.width`). (Whether
  `Image.paste` rounds half-pixel positions was listed here: it cuts them
  toward zero, `text-drawing.md`. A button on screen is drawn as quads,
  which the game code does not round; what the Unity side does with them
  was not read.)
- The shape of the `BOUNCEBACK` curve (`app.Interp.get`, case 6).
- When the stamp bar drops its button and what the click does
  (`StampBar`, `DropRemote`); the criminal-poster pin's behaviour beyond
  its looks (phone only, by the inference above).
- `PlatformChangeButton.png`'s cut and the `LoadButtonNew.png` pictures
  of the root button (`newNormalImage`, `newPressedImage`).
- Which block of the `Layout` constructor writes `carousel` (no longer
  needed for desktop: a desktop booth makes no carousel,
  `desk-pictures.md`).

## Things to watch in the game

Each takes a few seconds on any screen with a standard button (the title
screen's STORY, for example):

1. Pressing a button: it fills (the lower band of `PushButton.png`) and
   its text turns black; the press sound plays on the press, not on the
   release.
2. Holding, sliding off: the button goes back to the outline; sliding
   back on: filled again.
3. Letting go outside the button: nothing happens and no sound plays.
4. Pressing outside a button and sliding onto it while holding: it does
   not fill, and letting go there does not click it.
5. The cursor becomes a hand over a button.
6. In the booth, when the stamp bar's reason button is down: it blinks
   about twice a second (0.25 s per look).
