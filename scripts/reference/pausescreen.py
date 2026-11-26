"""The pause screen of milestone 4b (docs/milestone-4.md), as stills: what
Escape opens over the day screen on desktop, in English, without QUIT (the
user's decision), and the confirm box its MAIN MENU button opens. Built
from the code (docs/screens.md parts 3 and 4: PauseScreen constructor
0x1808035e0, menu_onClick, showConfirm; Confirm constructor 0x18093beb0,
show 0x18093d4f0, draw; Frame.buildTiles) and drawn with the same quad
rules as fontpage.py.

    python -I scripts/reference/pausescreen.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m4b`
(gitignored). It writes two pictures (570 x 320 x 4 bytes, alpha 255),
each also as a PNG and, enlarged 3 times, as _x3.png to look at:

- pause_a.rgba: the pause screen with the settings a new player has;
- pause_b.rgba: the same with MAIN MENU clicked: the confirm box open.

port/core/src/pause.rs draws the same and port/core/tests/pause.rs
compares the two byte for byte.

What is on it, in the order drawn (the day screen under it is hidden):

- the header (as the settings screen's) with `menu_paused`;
- RESUME and MAIN MENU: standard buttons (PushButton.png rows 0-18, text
  in ui_large, 0x556855), centred left to right, their column centred on
  y = 320 x 270 / 320 = 270 by the menu helper: tops 246 and 270 (two
  buttons 19 high, the 10 of padding shared out per button: 5);
- the settings list in its Pause form (Fullscreen, Nudity, Music, Sound),
  centred left to right, and up and down between the header's bottom and
  RESUME's top;
- with the confirm box (Confirm.show with an empty message and two
  options): a fill over the whole screen, black at alpha 0.5 (a float,
  not a byte); ConfirmBox.png (244 x 192) as a nine-slice frame with
  borders of 10, 244 wide and 2 x 19 + 20 + 2 x 20 = 98 high (no message:
  the gap between buttons doubled to 20, the padding 20 above and below),
  at x = floor(285 - 122) = 163, y = floor(160 - 49) = 111; the buttons
  centred in it, the first at y = 111 + 98 - 58 - 20 = 131, the next 39
  lower: MAIN MENU red (PushButtonRed.png, text 0xcc2e2e), then CANCEL.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpage  # noqa: E402
import fonts  # noqa: E402
import settingsscreen as SS  # noqa: E402
import text as textmod  # noqa: E402
import titlescreen  # noqa: E402
import vis  # noqa: E402
from PIL import Image  # noqa: E402

W, H = fontpage.W, fontpage.H
MENU_CENTER_Y = H * 270 // 320
RED = 0xFFCC2E2E
CONFIRM_GAP, CONFIRM_BUTTON_H = 10.0, 19.0      # Confirm's statics
CONFIRM_PADDING = (15.0, 20.0)                   # Layout.confirmBoxPadding, desktop
FRAME_BORDER = 10

PICTURES = SS.PICTURES + ["PushButtonRed.png", "ConfirmBox.png"]


def push_button(page, lib, pictures, strings, text_id, x, y, red=False):
    name = "PushButtonRed.png" if red else "PushButton.png"
    w = pictures[name].size[0]
    page.part(name, x, y, (0, 0, w, SS.PUSH_BAND))
    page.button_text(lib.get("ui_large"), strings[text_id], x, y, w, SS.PUSH_BAND, RED if red else SS.GREEN)


def build(lib, pictures, strings, settings, confirm):
    page = titlescreen.Title(lib, pictures)
    title_tall = lib.get("title_tall")

    # The header (GameScreen.addHeader).
    header_w, header_h = pictures["ScreenHeader.png"].size
    page.picture("ScreenHeader.png", int(math.floor(W * 0.5 - header_w * 0.5)), SS.HEADER_Y)
    title = textmod.Text(title_tall, strings["menu_paused"], color=SS.WHITE, background=SS.BLACK,
                         padding_x=SS.HEADER_PAD)
    _, tw, th, _ = title.build()
    tx = int(math.floor(W * 0.5 - tw * 0.5))
    ty = int(math.floor((header_h + SS.HEADER_Y) - th * 0.5)) + 0.0
    page.text(title_tall, strings["menu_paused"], tx, ty, color=SS.WHITE, background=SS.BLACK,
              padding_x=SS.HEADER_PAD)
    header_bottom = ty + th

    # The menu: RESUME, MAIN MENU (no QUIT).
    push_w = pictures["PushButton.png"].size[0]
    bx = int(math.floor(W * 0.5 - push_w * 0.5))
    resume_y, main_y = titlescreen.menu_column([SS.PUSH_BAND, SS.PUSH_BAND], MENU_CENTER_Y)

    # The settings list, Pause form.
    rows = []
    for label, kind in [("menu_fullscreen", "fullscreen"), ("menu_nudity", "nudity"),
                        ("menu_music", "music"), ("menu_sound", "sound")]:
        row = SS.Row(title_tall, strings[label])
        if kind in ("fullscreen", "nudity"):
            row.add_checkbox(settings.fullscreen if kind == "fullscreen" else settings.nudity)
        else:
            row.add_volume_bar(settings.music if kind == "music" else settings.sound)
            row.add_plus_minus()
        rows.append(row)
    total_w, y = 0.0, 0.0
    tops = []
    for row in rows:
        row.split_if_needed()
        total_w = max(total_w, row.width())
        tops.append(y)
        y += row.height
    total_h = y - SS.PADDING
    mx = int(math.floor(W * 0.5 - total_w * 0.5))
    my = int(math.floor((resume_y - header_bottom) * 0.5 + header_bottom - total_h * 0.5))

    # Drawn in the order made: the menu's buttons, then the list.
    push_button(page, lib, pictures, strings, "menu_resume", bx, resume_y)
    push_button(page, lib, pictures, strings, "menu_mainmenu", bx, main_y)
    for row, top in zip(rows, tops):
        ox, oy = mx, my + top
        for v in row.visuals:
            if v[0] == "text":
                page.text(title_tall, v[1], ox + v[2], oy + v[3], color=SS.WHITE)
            else:
                page.fill(ox + v[2], oy + v[3], v[4], v[5], v[1])
        for name, x, by in row.buttons:
            w, h = pictures[name].size
            page.part(name, ox + x, oy + by, (0, 0, w, h))

    if confirm:
        # Confirm.draw: the back fill (ColorData 0, 0, 0, 0.5 as floats).
        page.quads.append(fontpage.Quad(fontpage.WHITE, 0, 0, W, H, (0, 0, 1, 1), (0.0, 0.0, 0.0, 0.5)))
        dw, dh = pictures["ConfirmBox.png"].size
        fx = int(math.floor(W * 0.5 - dw * 0.5))
        gap = CONFIRM_GAP + CONFIRM_GAP                # no message
        buttons_h = 2 * CONFIRM_BUTTON_H + 1 * gap
        height = buttons_h + (CONFIRM_PADDING[1] + CONFIRM_PADDING[1])
        fy = int(math.floor(H * 0.5 - height * 0.5))
        scale9 = (FRAME_BORDER, FRAME_BORDER, dw - 2 * FRAME_BORDER, dh - 2 * FRAME_BORDER)
        for src, dst in vis.frame_tiles((dw, dh), scale9, (dw, height)):
            page.quads.append(fontpage.Quad("ConfirmBox.png", fx + dst[0], fy + dst[1], dst[2], dst[3], src,
                                            0xFFFFFFFF))
        by = ((height + fy) - buttons_h) - CONFIRM_PADDING[1]
        red_w = pictures["PushButtonRed.png"].size[0]
        for text_id, red in [("menu_mainmenu", True), ("confirm_cancel", False)]:
            w = red_w if red else push_w
            x = int(math.floor(dw * 0.5 - w * 0.5)) + fx
            push_button(page, lib, pictures, strings, text_id, x, by, red)
            by = by + gap + CONFIRM_BUTTON_H
    return page.quads


CASES = {"pause_a": False, "pause_b": True}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    pictures = {f: Image.open(os.path.join(assets, "fonts", f)) for f in fontpage.sheet_files(lib)}
    for name in PICTURES:
        pictures[name] = Image.open(os.path.join(assets, name))
    pictures.update(SS.button_pictures(assets))
    strings = SS.text_items(assets)
    os.makedirs(out, exist_ok=True)
    for name, confirm in CASES.items():
        quads = build(lib, pictures, strings, SS.Settings(), confirm)
        data = fontpage.draw(quads, pictures)
        with open(os.path.join(out, name + ".rgba"), "wb") as f:
            f.write(data)
        im = Image.frombytes("RGBA", (W, H), data).convert("RGB")
        im.save(os.path.join(out, name + ".png"))
        im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(out, name + "_x3.png"))
        print("%s: %d quads -> %s" % (name, len(quads), os.path.join(out, name + ".rgba")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
