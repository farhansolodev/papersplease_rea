"""Reference for drawing text: app.vis.Text (docs/text-drawing.md).

A Text is a font, a string and a few settings. Laying it out ("building its
tiles") breaks the string into lines with Font.split (fonts.py), then gives
every letter that has a picture one tile: a piece of the font sheet and the
place, relative to the text's position, where it is pasted. Its width and
height follow from the lines, the font's line height and the settings.

    python -I scripts/reference/text.py <assets dir> <font id> <text> [options]

Options: --width N (fixed width, 0 = break only at line breaks),
--multi (keep every line), --align LEFT|CENTER|RIGHT, --pad X Y,
--spacing N (line spacing), --color AARRGGBB, --bg AARRGGBB (background),
--rounded (background with its corner pixels cut), --png out.png [--scale N].
"\\n" in the text is a line break.

Prints the size and every tile. --png draws a preview (needs Pillow): the
letters in the text colour where the font sheet is opaque (every sheet here
is white with alpha 0 or 255, and the game's tint multiplies each channel
by colour / 255, read in Image.paste, docs/fact-pictures.md, so the pixels
are the same); the background and missing-letter boxes as filled
rectangles (the game stretches a 1 x 1 white picture as a quad, drawn by
Image.render, not read).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fonts  # noqa: E402

SPACE = 32             # Font.kSpaceCharCode
ALPHA_THRESH = 0.001   # Quad.kAlphaThresh: a tile with a smaller alpha is not drawn


class Tile:
    def __init__(self, kind, char, page, src, dst, color):
        self.kind = kind      # "letter", "box" (a letter the font lacks) or "background"
        self.char = char      # the character, or None for a background tile
        self.page = page      # font sheet index for a letter, None for the white 1 x 1 picture
        self.src = src        # (x, y, w, h) on the picture
        self.dst = dst        # (x, y, w, h) relative to the text's position
        self.color = color    # 0xAARRGGBB


class Text:
    def __init__(self, font, text="", fixed_width=0, multi_line=False, align="LEFT",
                 padding_x=0, padding_y=0, line_spacing=0, color=0,
                 background=0, rounded=False):
        # The constructor sets none of these but the font, so a new Text has
        # colour 0 (fully transparent: it draws nothing) and is one line.
        self.font, self.text = font, text
        self.fixed_width, self.multi_line, self.align = fixed_width, multi_line, align
        self.padding_x, self.padding_y, self.line_spacing = padding_x, padding_y, line_spacing
        self.color, self.background, self.rounded = color, background, rounded

    def will_draw(self, visible=True):
        """Text.willDraw (visible, not empty, colour alpha not 0). No game code
        calls it; what hides a transparent letter is Quad.make's alpha test."""
        return visible and bool(self.text) and (self.color >> 24) != 0

    def build(self):
        """Text.buildTiles. Returns (tiles, width, height, hyphenated)."""
        font = self.font
        if not self.text:
            return [], 0, 0, False
        lines, hyphenated, widest, _ = font.split(self.text, self.fixed_width, self.multi_line)
        r = 1 if self.rounded else 0
        tiles = []
        y = self.padding_y
        for line, line_width in lines:
            x = self.padding_x
            if self.align == "CENTER":
                x += int((widest - line_width) / 2)       # never negative, so rounded down
            elif self.align == "RIGHT":
                x += widest - line_width
            x += r
            for ch in line:                               # the game walks code points
                code = ord(ch)
                letter = font.letters.get(code)
                if letter is None:
                    if code != SPACE:                     # a box in the text colour
                        tiles.append(Tile("box", ch, None, (0, 0, 1, 1),
                                          (x + font.space_width - 1, y, font.space_width, font.cap_height),
                                          self.color))
                    x += font.space_width
                    continue
                if code != SPACE:
                    lx, ly, lw, lh = letter.rect
                    tiles.append(Tile("letter", ch, letter.page, letter.rect,
                                      (x + letter.offset[0], y + letter.offset[1], lw, lh), self.color))
                x += letter.advance
            y += font.line_height + self.line_spacing
        width = widest + 2 * self.padding_x
        height = font.line_height * len(lines) + self.line_spacing * max(0, len(lines) - 1) \
            + 2 * self.padding_y
        if self.background >> 24:
            back = [Tile("background", None, None, (0, 0, 1, 1), (r, 0, width - r, height), self.background)]
            if self.rounded:
                back.append(Tile("background", None, None, (0, 0, 1, 1), (0, 1, r, height - 2), self.background))
                back.append(Tile("background", None, None, (0, 0, 1, 1), (width, 1, r, height - 2), self.background))
            tiles = back + tiles                          # the background tiles come first
        return tiles, width + r, height, hyphenated

    # Text.get_baselineY / capY / bottomY, as offsets from the position's y.
    def baseline(self):
        return self.font.ascent

    def cap_top(self):
        return self.font.ascent - self.font.cap_height


def paste_position(pos, dst):
    """Visual.renderToImage pastes an unstretched tile at pos + dst; Image.paste
    turns each coordinate into a whole pixel by cutting toward zero."""
    return int(pos[0] + dst[0]), int(pos[1] + dst[1])


def render(text, assets_dir, scale=1, margin=4, backdrop=True):
    """A picture of the text, its position at (margin, margin). With backdrop,
    on grey with the text's box outlined in magenta; without, transparent."""
    from PIL import Image, ImageDraw
    tiles, width, height, _ = text.build()
    sheets = [Image.open(os.path.join(assets_dir, "fonts", f)).convert("RGBA") for f in text.font.page_files]
    image = Image.new("RGBA", (width + 2 * margin, height + 2 * margin), (128, 128, 128, 255 if backdrop else 0))
    if backdrop:
        ImageDraw.Draw(image).rectangle((margin, margin, margin + width - 1, margin + height - 1),
                                        outline=(255, 0, 255, 255))

    def rgba(c):
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24)

    for tile in tiles:
        if (tile.color >> 24) / 255 < ALPHA_THRESH:       # Quad.make skips the tile
            continue
        x, y = paste_position((margin, margin), tile.dst)
        if tile.page is None:
            w, h = tile.dst[2], tile.dst[3]
            if w > 0 and h > 0:
                image.alpha_composite(Image.new("RGBA", (int(w), int(h)), rgba(tile.color)), (x, y))
            continue
        sx, sy, w, h = tile.src
        if w <= 0 or h <= 0:
            continue
        piece = sheets[tile.page].crop((sx, sy, sx + w, sy + h))
        coloured = Image.new("RGBA", piece.size, rgba(tile.color))
        coloured.putalpha(Image.eval(piece.getchannel("A"), lambda a: a * (tile.color >> 24) // 255))
        image.alpha_composite(coloured, (x, y))
    if scale != 1:
        image = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
    return image


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    assets, font_id, string = argv[1], argv[2], argv[3].replace("\\n", "\n")
    args = argv[4:]
    options = {"color": 0xffffffff}
    png, scale = None, 4
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--width":
            options["fixed_width"] = int(args[i + 1]); i += 1
        elif a == "--multi":
            options["multi_line"] = True
        elif a == "--align":
            options["align"] = args[i + 1].upper(); i += 1
        elif a == "--pad":
            options["padding_x"], options["padding_y"] = int(args[i + 1]), int(args[i + 2]); i += 2
        elif a == "--spacing":
            options["line_spacing"] = int(args[i + 1]); i += 1
        elif a == "--color":
            options["color"] = int(args[i + 1], 16); i += 1
        elif a == "--bg":
            options["background"] = int(args[i + 1], 16); i += 1
        elif a == "--rounded":
            options["rounded"] = True
        elif a == "--png":
            png = args[i + 1]; i += 1
        elif a == "--scale":
            scale = int(args[i + 1]); i += 1
        else:
            raise SystemExit("unknown option " + a)
        i += 1
    font = fonts.FontLib(assets).get(font_id)
    text = Text(font, string, **options)
    tiles, width, height, hyphenated = text.build()
    print("font %s: line %d, ascent %d, cap %d, space %d" % (
        font_id, font.line_height, font.ascent, font.cap_height, font.space_width))
    print("size %d x %d, hyphenated %s, %d tiles; baseline at +%d, capitals' top at +%d" % (
        width, height, hyphenated, len(tiles), text.baseline(), text.cap_top()))
    for t in tiles:
        print("  %-10s %-4r page %-4s src %-18s dst %s" % (
            t.kind, t.char, t.page, t.src, tuple(int(v) for v in t.dst)))
    if png:
        render(text, assets, scale).save(png)
        print("preview written to", png)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
