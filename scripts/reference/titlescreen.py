"""The title screen of milestone 1b (docs/milestone-1.md), as a still: the
resting state after the title has risen, with no button pressed. Built from
the code (docs/screens.md part 2, docs/buttons.md) and drawn with the same
quad rules as fontpage.py.

    python -I scripts/reference/titlescreen.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m1b` (gitignored).
It writes title.rgba (570 x 320 x 4 bytes, alpha 255), the same picture as
title.png and, enlarged 3 times, title_x3.png to look at.
port/core/src/title.rs builds the same quads and port/core/tests/title.rs
compares the two byte for byte.

What is on it, in the order the game draws it (TitleScreen constructor
0x180673be0, update 0x180676bc0, Menu, GameScreen.makePushButton):

- the screen's black fill (size taken as the whole screen; it changes no
  pixel on a screen cleared to black);
- the logo Title.png, x = floor(570 / 2 - width / 2), y = titleLogoTop 28
  (the container has risen to y 0; with no music the logo does not bob);
- STORY and ENDLESS: PushButton.png rows 0-18, the text in ui_large,
  colour 0x556855 made opaque, centred by Button.applyMode; the column by
  Menu.applyCenterY (below);
- the settings button: SettingsButton.png rows 0-28 at (10, 320 - 10 - 29);
- the credit: a 140 x 12 black picture with created_by in `regular`,
  colour 0x556855, at x = floor(570 / 2 - 140 / 2), y = 320 - 12 - 10.

Left out: the quit button (the user's decision), the version button (its
text, Platform.decoratedVersion, is not read).

Menu.applyCenterY, as read: the column's height h = min(320 - notch - 40,
sum of heights + (n - 1) x menuItemPaddingY); the gap between buttons is
floor((h - sum of heights) / n), divided by n, not n - 1; the first top is
(int)(centerY - h / 2). Desktop: h = min(280, 38 + 10) = 48, gap 5, first
top 236, so STORY at y 236 and ENDLESS at 260.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpage  # noqa: E402
import fonts  # noqa: E402
import text as textmod  # noqa: E402
from PIL import Image  # noqa: E402

W, H = fontpage.W, fontpage.H
PICTURES = ["Title.png", "PushButton.png", "SettingsButton.png"]

# Layout values, desktop (docs/booth-layout.md, docs/screens.md part 2).
TITLE_LOGO_TOP = 28
TITLE_MENU_CENTER_Y = 260
MENU_ITEM_PADDING_Y = 10
NOTCH_HEIGHT = 0
EDGE = 10                       # DAT_180a6ba58, the corner buttons' distance from the edges
PUSH_BAND = 19                  # makePushButton cuts PushButton.png into bands of 19 rows
SETTINGS_BAND = 29              # the title screen's addImageButton("settings", ..., 29)
CREDIT_W, CREDIT_H = 140, 12
GREEN = 0xFF556855              # 0x556855 made opaque (Button.applyMode adds alpha 255)


def text_items(assets):
    root = ET.parse(os.path.join(assets, "data", "Text.xml")).getroot()
    return {item.get("id"): item.find("t").text or "" for item in root.iter("item")}


class Title(fontpage.Page):
    def part(self, name, x, y, src):
        """A sprite of a piece (x, y, w, h) of a picture, drawn at (x, y)."""
        self.quads.append(fontpage.Quad(name, x, y, src[2], src[3], src, 0xFFFFFFFF))

    def button_text(self, font, string, bx, by, bw, bh, color):
        """Button.applyMode's text place for CENTER: the text's box at
        floor(bw / 2 - text width / 2), floor(bh / 2 - text height / 2)."""
        t = textmod.Text(font, string, align="CENTER", color=color)
        _, tw, th, _ = t.build()
        x = bx + int(_floor(bw * 0.5 - tw * 0.5))
        y = by + int(_floor(bh * 0.5 - th * 0.5))
        self.text(font, string, x, y, align="CENTER", color=color)


def _floor(v):
    return math.floor(v)


def menu_column(heights, center_y=TITLE_MENU_CENTER_Y):
    """Menu.applyCenterY: the top of each centre-column button."""
    total = sum(heights)
    h = min(float(H - NOTCH_HEIGHT - 40), float((len(heights) - 1) * MENU_ITEM_PADDING_Y) + total)
    gap = int(_floor((h - total) / len(heights)))
    y = int(center_y - h * 0.5)                       # (int): toward zero
    tops = []
    for bh in heights:
        tops.append(y)
        y += int(bh + gap)
    return tops


def build(lib, pictures, strings):
    page = Title(lib, pictures)
    page.fill(0, 0, W, H, 0xFF000000)
    logo_w, _ = pictures["Title.png"].size
    page.picture("Title.png", _floor(W * 0.5 - logo_w * 0.5), TITLE_LOGO_TOP)

    push_w = pictures["PushButton.png"].size[0]
    ui_large = lib.get("ui_large")
    labels = [strings["menu_story"], strings["menu_endless"]]
    x = _floor(W * 0.5 - push_w * 0.5)
    for label, y in zip(labels, menu_column([PUSH_BAND] * len(labels))):
        page.part("PushButton.png", x, y, (0, 0, push_w, PUSH_BAND))
        page.button_text(ui_large, label, x, y, push_w, PUSH_BAND, GREEN)

    settings_w = pictures["SettingsButton.png"].size[0]
    page.part("SettingsButton.png", EDGE, H - EDGE - SETTINGS_BAND, (0, 0, settings_w, SETTINGS_BAND))

    cx = _floor(W * 0.5 - CREDIT_W * 0.5)
    cy = H - CREDIT_H - EDGE
    page.fill(cx, cy, CREDIT_W, CREDIT_H, 0xFF000000)   # the black 140 x 12 picture
    page.button_text(lib.get("regular"), strings["created_by"], cx, cy, CREDIT_W, CREDIT_H, GREEN)
    return page.quads


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    pictures = {f: Image.open(os.path.join(assets, "fonts", f)) for f in fontpage.sheet_files(lib)}
    for name in PICTURES:
        pictures[name] = Image.open(os.path.join(assets, name))
    quads = build(lib, pictures, text_items(assets))
    data = fontpage.draw(quads, pictures)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "title.rgba"), "wb") as f:
        f.write(data)
    im = Image.frombytes("RGBA", (W, H), data).convert("RGB")
    im.save(os.path.join(out, "title.png"))
    im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(out, "title_x3.png"))
    print("%d quads -> %s" % (len(quads), os.path.join(out, "title.rgba")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
