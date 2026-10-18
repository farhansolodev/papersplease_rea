"""The font test pages of milestone 1a (docs/milestone-1.md), drawn the way
the game draws: text laid out by text.py, turned into quads, the quads
drawn in order into a 570 x 320 picture by host.py's pixel rules.

    python -I scripts/reference/fontpage.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m1` (gitignored).
It writes page_000.rgba ... (570 x 320 x 4 bytes, alpha 255) and pages.json
(the page names). port/core/src/pages.rs builds the same pages and
port/core/tests/fontpage.rs compares them byte for byte.

The pages are the port's own test material, not game screens:

- one text page per font id in Fonts.xml order: samples of letters, digits,
  a missing letter, wrapping with a cut word, three alignments, a rounded and
  a plain background, half-transparent text, a half-pixel position, line
  spacing;
- then each font sheet, 570 x 320 at a time (row by row), drawn as one quad
  that runs off the screen.

What is assumed, not from the game: which pixels a fractional quad covers,
the texel a pixel reads, and the 8-bit rounding (host.py: covered_pixels,
texel_at, to_byte).
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fonts  # noqa: E402
import host  # noqa: E402
import text as textmod  # noqa: E402
from PIL import Image  # noqa: E402

W, H = host.GAME_W, host.GAME_H
WHITE = "white"          # the 1 x 1 white picture (Image.white1x1)


class Quad:
    def __init__(self, image, x, y, w, h, src, color):
        self.image, self.src, self.color = image, src, color
        self.x0, self.y0 = x, y
        self.x1, self.y1 = x + w, y + h


class Page:
    def __init__(self, lib, sheets):
        self.lib, self.sheets, self.quads = lib, sheets, []

    def fill(self, x, y, w, h, color):
        self.quads.append(Quad(WHITE, x, y, w, h, (0, 0, 1, 1), color))

    def picture(self, name, x, y, color=0xFFFFFFFF):
        w, h = self.sheets[name].size
        self.quads.append(Quad(name, x, y, w, h, (0, 0, w, h), color))

    def text(self, font, string, x, y, **options):
        """Draws a Text at (x, y) and returns its height."""
        options.setdefault("color", 0xFFFFFFFF)
        t = textmod.Text(font, string, **options)
        tiles, width, height, _ = t.build()
        for tile in tiles:
            w, h = tile.dst[2], tile.dst[3]
            if tile.page is None:
                self.quads.append(Quad(WHITE, x + tile.dst[0], y + tile.dst[1], w, h, (0, 0, 1, 1), tile.color))
            else:
                self.quads.append(Quad(font.page_files[tile.page], x + tile.dst[0], y + tile.dst[1],
                                       w, h, tile.src, tile.color))
        return height


def font_ids(lib):
    return list(lib.defs)


def sheet_files(lib):
    """The font sheets, once each, in the order of first use in Fonts.xml."""
    seen = []
    for font in lib.defs.values():
        for f in font.page_files:
            if f not in seen:
                seen.append(f)
    return seen


def sheet_parts(size):
    cols, rows = math.ceil(size[0] / W), math.ceil(size[1] / H)
    return [((p % cols) * W, (p // cols) * H) for p in range(cols * rows)]


def page_list(lib, sheets):
    pages = [("text", i) for i in font_ids(lib)]
    for f in sheet_files(lib):
        for n, _ in enumerate(sheet_parts(sheets[f].size)):
            pages.append(("sheet", f, n))
    return pages


def build_page(lib, sheets, index):
    pages = page_list(lib, sheets)
    kind = pages[index]
    page = Page(lib, sheets)
    regular = lib.get("regular")
    label_tail = "  page %d of %d" % (index + 1, len(pages))
    if kind[0] == "text":
        font = lib.get(kind[1])
        page.fill(0, 0, W, H, 0xFF202830)
        page.text(regular, "%s / %s: line %d ascent %d cap %d descent %d space %d%s" % (
            kind[1], font.name, font.line_height, font.ascent, font.cap_height, font.descent,
            font.space_width, label_tail), 4, 4)
        y = 20
        y += page.text(font, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 4, y) + 4
        y += page.text(font, "abcdefghijklmnopqrstuvwxyz", 4, y, color=0xFFB0FFB0) + 4
        y += page.text(font, "0123456789 .,:;!?'\"-+=()[]/%&#@*$", 4, y, color=0xFFB0B0FF) + 4
        y += page.text(font, "box ☺ § end", 4, y) + 4
        y += page.text(font, "Rounded", 4, y, padding_x=3, padding_y=2, background=0xFF3355AA, rounded=True) + 4
        y += page.text(font, "Plain box", 4, y, padding_x=2, padding_y=1, background=0xFF883333) + 4
        page.fill(4, y, 150, font.line_height, 0xFFFFFFFF)       # half-transparent text on white
        y += page.text(font, "Half alpha", 4, y, color=0x80FF4020) + 4
        y = 20
        paragraph = ("The quick brown fox jumps over the lazy dog. "
                     "Pneumonoultramicroscopicsilicovolcanoconiosis is a very long word that gets cut with a hyphen.")
        y += page.text(font, paragraph, 290, y, fixed_width=270, multi_line=True, color=0xFFFFCC33) + 4
        y += page.text(font, "Centred text\nwraps and\ncentres each line within the widest line", 290, y,
                       fixed_width=270, multi_line=True, align="CENTER", color=0xFFCCFFFF) + 4
        y += page.text(font, "Right aligned line one\nand a much longer second line", 290, y,
                       fixed_width=270, multi_line=True, align="RIGHT", color=0xFFFFCCCC) + 4
        y += page.text(font, "Fractional 0.5", 290.5, y + 0.5) + 4
        y += page.text(font, "one\ntwo\nthree", 290, y, multi_line=True, line_spacing=3) + 4
    else:
        name, n = kind[1], kind[2]
        size = sheets[name].size
        ox, oy = sheet_parts(size)[n]
        page.fill(0, 0, W, H, 0xFF303848)
        page.picture(name, -ox, -oy, 0xFFFFFFFF)
        page.text(regular, "%s  %d x %d  part %d of %d%s" % (
            name, size[0], size[1], n + 1, len(sheet_parts(size)), label_tail), 0, 0,
            padding_x=2, padding_y=1, background=0xC0000000)
    return page.quads


def draw(quads, sheets):
    """The quads, in order, into a 570 x 320 RGBA picture cleared to opaque black."""
    screen = bytearray(b"\x00\x00\x00\xff" * (W * H))
    white = Image.new("RGBA", (1, 1), (255, 255, 255, 255))
    pictures = {name: im.convert("RGBA") for name, im in sheets.items()}
    pictures[WHITE] = white
    pixels = {name: im.load() for name, im in pictures.items()}
    for q in quads:
        if (q.color >> 24) / 255 < host.ALPHA_THRESH:
            continue
        colour = [((q.color >> 16) & 255) / 255.0, ((q.color >> 8) & 255) / 255.0,
                  (q.color & 255) / 255.0, (q.color >> 24) / 255.0]
        iw, ih = pictures[q.image].size
        sx, sy, sw, sh = q.src
        u0, u1, v0, v1 = sx / iw, (sx + sw) / iw, sy / ih, (sy + sh) / ih
        xs = [x for x in host.covered_pixels(q.x0, q.x1) if 0 <= x < W]
        ys = [y for y in host.covered_pixels(q.y0, q.y1) if 0 <= y < H]
        for y in ys:
            ty = host.texel_at(y, q.y0, q.y1, v0, v1, ih)
            for x in xs:
                tx = host.texel_at(x, q.x0, q.x1, u0, u1, iw)
                i = (y * W + x) * 4
                new = host.quad_pixel(pixels[q.image][tx, ty], colour, screen[i:i + 3])
                screen[i], screen[i + 1], screen[i + 2] = new
    return bytes(screen)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    sheets = {f: Image.open(os.path.join(assets, "fonts", f)) for f in sheet_files(lib)}
    os.makedirs(out, exist_ok=True)
    pages = page_list(lib, sheets)
    for i, kind in enumerate(pages):
        data = draw(build_page(lib, sheets, i), sheets)
        with open(os.path.join(out, "page_%03d.rgba" % i), "wb") as f:
            f.write(data)
        print("page %3d %s" % (i, kind), flush=True)
    with open(os.path.join(out, "pages.json"), "w") as f:
        json.dump([list(p) for p in pages], f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
