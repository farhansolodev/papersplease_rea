"""The settings screen of milestone 3b (docs/milestone-3.md), as a still:
what the title's settings button opens, on desktop, in English, with the
Language row left out (the user's decision: English only). Built from the
code (docs/screens.md part 4) and drawn with the same quad rules as
fontpage.py.

    python -I scripts/reference/settingsscreen.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m3b` (gitignored).
It writes two pictures (570 x 320 x 4 bytes, alpha 255), each also as a PNG
and, enlarged 3 times, as _x3.png to look at:

- settings_a.rgba: the settings a new player has (fullscreen off, nudity on,
  as a desktop game starts; easy mode off; the first date format; both
  volumes 1.0);
- settings_b.rgba: fullscreen on, nudity off, easy mode on with its tip
  showing (as in the 3 seconds after the click), the third date format,
  music 0.3 (a bar 13.8 pixels long) and sound 0.7.

port/core/src/settings_screen.rs builds the same quads and
port/core/tests/settings_screen.rs compares the two byte for byte.

What is on it, in the order the game draws it (SettingsScreen constructor
0x180715910, GameScreen.addHeader, SettingsMenu constructor 0x180710150,
SettingRow, SettingDim, Menu.addPushButton):

- the header: ScreenHeader.png centred at y = gameScreenHeaderY 13, then the
  title `menu_settings` in title_tall, white on a black box with 8 pixels of
  padding left and right, centred, its middle on the picture's bottom edge
  (y = floor(13 + 54 - height / 2));
- the settings list, at x = floor(570 / 2 - its width / 2) and y centred
  between the header's bottom and DONE's top; its rows one under the other,
  19 pixels apart (the last row's 4 pixels of padding not counted). Each row
  draws its own pictures (label, volume bar, date text, easy tip) and then
  its buttons:
  - the label at (0, cap height - ascent) = (0, -4);
  - a tick box, or minus, at the button column (180, -1); plus at
    (180 + 15 + 4, -1);
  - the volume bar: white 50 x 16 at (126, -1), black 48 x 14 at (127, 0),
    the level white (46 x volume) x 12 at (128, 1), not drawn under 1 pixel;
  - the date format's example ("1982-1-23" ...) ending at x 176;
  - the easy tip `menu_easytip` at (210, -4) on the Easy Mode row, shown only
    for 3 seconds after easy mode is switched on;
- DONE: PushButton.png rows 0-18 with `menu_done` in ui_large, colour
  0x556855, centred left to right, its column centred on
  standardFooterButtonY 290 (so at y 280).

The buttons' pictures are made when the screen is built
(SettingRow.makeModeImages): a black box 15 x 15 (taller if the icon needs
it) with a dotted white border (a dot where x + y is even), the icon pasted
in the middle with BLEND; the pressed picture is the same with the inside
(2 pixels in) filled white before the icon. The tick box's "on" icon has no
inner padding, the others 2.

Left out: the Language row (the user's decision), the `web` and `twitter`
buttons (the user's decision), the Vibration and Device rows (not made on
desktop) and the version text (not on desktop).
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factpics as FP  # noqa: E402
import fontpage  # noqa: E402
import fonts  # noqa: E402
import text as textmod  # noqa: E402
import titlescreen  # noqa: E402
from faces import Image as PxImage  # noqa: E402
from PIL import Image  # noqa: E402

W, H = fontpage.W, fontpage.H

# Layout values, desktop (docs/screens.md part 4, docs/booth-layout.md).
HEADER_Y = 13                   # gameScreenHeaderY
FOOTER_Y = 290                  # standardFooterButtonY
BUTTON_W = BUTTON_H = 15        # settingsButtonSize
PADDING = 4                     # settingsPadding
BUTTON_X = 180                  # settingsButtonX
ROW_H = PADDING + BUTTON_H      # SettingDim.rowHeight
BAR_W = BUTTON_W * 50 // 15     # SettingDim.barWidth
TIP_DX = 30                     # the easy tip sits 30 right of the button column
HEADER_PAD = 8                  # the header title's paddingX
PUSH_BAND = titlescreen.PUSH_BAND
GREEN = titlescreen.GREEN
WHITE = 0xFFFFFFFF
BLACK = 0xFF000000

# play.Settings' date formats: the third string of each is what the row shows.
DATE_EXAMPLES = ["1982-1-23", "23-1-1982", "1-23-1982"]

ICONS = ["SettingButtonOn.png", "SettingButtonOff.png", "SettingButtonPlus.png", "SettingButtonMinus.png"]
PICTURES = ["ScreenHeader.png", "PushButton.png"] + ICONS


class Settings:
    def __init__(self, fullscreen=False, nudity=True, easy_mode=False, date_format=0,
                 music=1.0, sound=1.0, tip=False):
        self.fullscreen, self.nudity, self.easy_mode = fullscreen, nudity, easy_mode
        self.date_format, self.music, self.sound, self.tip = date_format, music, sound, tip


def make_mode_images(icon, internal_padding=2):
    """SettingRow.makeModeImages for one column: [normal, pressed]."""
    w = BUTTON_W
    h = max(BUTTON_H, icon.height + 2 + internal_padding * 2)
    normal = FP.fill(PxImage(w, h), BLACK)
    for x in range(w):
        if x % 2 == 0:
            normal.px[x] = WHITE
        if (x & 1) == ((h - 1) & 1):
            normal.px[w * (h - 1) + x] = WHITE
    for y in range(h):
        if y % 2 == 0:
            normal.px[w * y] = WHITE
        if ((w - 1) & 1) == (y & 1):
            normal.px[w * y + w - 1] = WHITE
    pressed = FP.copy(normal)
    FP.fill(pressed, WHITE, (2, 2, pressed.width - 4, pressed.height - 4))
    FP.paste(normal, icon, (normal.width - icon.width) * 0.5, (normal.height - icon.height) * 0.5, mode=FP.BLEND)
    FP.paste(pressed, icon, (pressed.width - icon.width) * 0.5, (pressed.height - icon.height) * 0.5, mode=FP.BLEND)
    return [normal, pressed]


def to_pil(image):
    out = Image.new("RGBA", (image.width, image.height))
    out.putdata([((p >> 16) & 255, (p >> 8) & 255, p & 255, p >> 24) for p in image.px])
    return out


def button_pictures(assets):
    """The made pictures by name ("on", "off", "plus", "minus", each with
    "-pressed"), as PIL pictures for fontpage.draw."""
    load = lambda f: PxImage.load(os.path.join(assets, f))  # noqa: E731
    made = {}
    for name, file, pad in [("on", "SettingButtonOn.png", 0), ("off", "SettingButtonOff.png", 2),
                            ("plus", "SettingButtonPlus.png", 2), ("minus", "SettingButtonMinus.png", 2)]:
        normal, pressed = make_mode_images(load(file), pad)
        made["made:" + name] = to_pil(normal)
        made["made:" + name + "-pressed"] = to_pil(pressed)
    return made


class Row:
    """A SettingRow: its pictures (texts and fills, in order) and its
    buttons, in row coordinates."""

    def __init__(self, title_font, label):
        self.font = title_font
        self.label_y = title_font.cap_height - title_font.ascent
        self.visuals = [("text", label, 0, self.label_y)]
        self.buttons = []
        self.height = ROW_H

    def button_y(self):
        return int(math.floor(self.font.ascent * 0.5 - BUTTON_H * 0.5)) - 1

    def add_checkbox(self, on):
        self.buttons.append(("made:on" if on else "made:off", BUTTON_X, self.button_y()))

    def add_plus_minus(self):
        self.buttons.append(("made:minus", BUTTON_X, self.button_y()))
        self.buttons.append(("made:plus", BUTTON_X + BUTTON_W + PADDING, self.button_y()))

    def add_volume_bar(self, volume):
        x = BUTTON_X - PADDING - BAR_W
        self.visuals.append(("fill", WHITE, x, -1.0, BAR_W, self.font.ascent))
        self.visuals.append(("fill", BLACK, x + 1.0, 0.0, BAR_W - 2.0, self.font.ascent - 2.0))
        level = (BAR_W - 2.0 - 2.0) * volume            # volumePercMaxWidth x volumePerc
        if level >= 1.0:
            self.visuals.append(("fill", WHITE, x + 2.0, 1.0, level, self.font.ascent - 4.0))

    def add_text(self, string, x):
        self.visuals.append(("text", string, x, self.label_y))

    def text_width(self, string):
        return textmod.Text(self.font, string).build()[1]

    def visual_width(self, v):
        return self.text_width(v[1]) if v[0] == "text" else v[4]

    def width(self):
        right = 0.0
        for v in self.visuals:
            right = max(right, v[2] + self.visual_width(v))
        for _, x, _ in self.buttons:
            right = max(right, x + BUTTON_W)
        return right

    def split_if_needed(self):
        """splitOntoTwoLinesIfNecessary: everything but the label moves a row
        down when the label reaches to within the padding of it."""
        left = 1e300
        for v in self.visuals[1:]:
            left = min(left, v[2])
        for _, x, _ in self.buttons:
            left = min(left, x)
        if self.text_width(self.visuals[0][1]) + 0 < left - PADDING:
            return
        self.visuals = [self.visuals[0]] + [v[:3] + (v[3] + ROW_H,) + v[4:] for v in self.visuals[1:]]
        self.buttons = [(b[0], b[1], b[2] + ROW_H) for b in self.buttons]
        self.height += ROW_H


def text_items(assets):
    root = ET.parse(os.path.join(assets, "data", "Text.xml")).getroot()
    return {item.get("id"): item.find("t").text or "" for item in root.iter("item")}


def build(lib, pictures, strings, settings):
    page = titlescreen.Title(lib, pictures)
    title_tall = lib.get("title_tall")

    # The header (GameScreen.addHeader).
    header_w, header_h = pictures["ScreenHeader.png"].size
    page.picture("ScreenHeader.png", int(math.floor(W * 0.5 - header_w * 0.5)), HEADER_Y)
    title = textmod.Text(title_tall, strings["menu_settings"], color=WHITE, background=BLACK, padding_x=HEADER_PAD)
    _, tw, th, _ = title.build()
    tx = int(math.floor(W * 0.5 - tw * 0.5))
    ty = int(math.floor((header_h + HEADER_Y) - th * 0.5)) + 0.0
    page.text(title_tall, strings["menu_settings"], tx, ty, color=WHITE, background=BLACK, padding_x=HEADER_PAD)
    header_bottom = ty + th

    # The rows (SettingsMenu, the Title form on desktop, without Language).
    rows = []
    for label, kind in [("menu_fullscreen", "fullscreen"), ("menu_nudity", "nudity"), ("menu_easy", "easy"),
                        ("menu_dateformat", "date"), ("menu_music", "music"), ("menu_sound", "sound")]:
        row = Row(title_tall, strings[label])
        if kind in ("fullscreen", "nudity", "easy"):
            row.add_checkbox({"fullscreen": settings.fullscreen, "nudity": settings.nudity,
                              "easy": settings.easy_mode}[kind])
        elif kind == "date":
            row.add_plus_minus()
            example = DATE_EXAMPLES[settings.date_format]
            row.add_text(example, BUTTON_X - PADDING - row.text_width(example))
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
    total_h = y - PADDING
    if settings.tip:     # added to the Easy Mode row after the rows are stacked
        rows[2].add_text(strings["menu_easytip"], BUTTON_X + TIP_DX)

    done_y = titlescreen.menu_column([PUSH_BAND], FOOTER_Y)[0]
    mx = int(math.floor(W * 0.5 - total_w * 0.5))
    my = int(math.floor((done_y - header_bottom) * 0.5 + header_bottom - total_h * 0.5))

    for row, top in zip(rows, tops):
        ox, oy = mx, my + top
        for v in row.visuals:
            if v[0] == "text":
                page.text(title_tall, v[1], ox + v[2], oy + v[3], color=WHITE)
            else:
                page.fill(ox + v[2], oy + v[3], v[4], v[5], v[1])
        for name, x, by in row.buttons:
            w, h = pictures[name].size
            page.part(name, ox + x, oy + by, (0, 0, w, h))

    # DONE (Menu.addPushButton: centred, its column centred on 290).
    push_w = pictures["PushButton.png"].size[0]
    x = int(math.floor(W * 0.5 - push_w * 0.5))
    page.part("PushButton.png", x, done_y, (0, 0, push_w, PUSH_BAND))
    page.button_text(lib.get("ui_large"), strings["menu_done"], x, done_y, push_w, PUSH_BAND, GREEN)
    return page.quads


CASES = {
    "settings_a": Settings(),
    "settings_b": Settings(fullscreen=True, nudity=False, easy_mode=True, date_format=2,
                           music=0.3, sound=0.7, tip=True),
}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    pictures = {f: Image.open(os.path.join(assets, "fonts", f)) for f in fontpage.sheet_files(lib)}
    for name in PICTURES:
        pictures[name] = Image.open(os.path.join(assets, name))
    pictures.update(button_pictures(assets))
    strings = text_items(assets)
    os.makedirs(out, exist_ok=True)
    for name, settings in CASES.items():
        quads = build(lib, pictures, strings, settings)
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
