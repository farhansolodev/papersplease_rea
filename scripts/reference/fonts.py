"""Reference implementation of the fonts: data.FontLib, data.FontDef and
app.vis.Font (docs/fonts.md). It reads Fonts.xml and the .fnt files, works
out each font's measurements, measures text and breaks it into lines.

Run as a script to list the fonts:

    python -I scripts/reference/fonts.py <assets dir>
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

NAMED_LETTERS = {"space": " ", "&#13;": "\r", "&#10;": "\n", "&gt;": ">", "&lt;": "<",
                 "&quot;": '"', "&amp;": "&"}


class Letter:
    def __init__(self, code, text, page, rect, offset, advance):
        self.code, self.text, self.page = code, text, page
        self.rect = rect                  # x, y, width, height on the sheet
        self.offset = offset              # [x, y] where to draw, relative to the pen
        self.advance = advance


def _int(text):
    """Haxe's Std.parseInt as used here: a missing or bad number counts as 0."""
    match = re.match(r"\s*([+-]?\d+)", text or "")
    return int(match.group(1)) if match else 0


class Font:
    def __init__(self, fonts_dir, name, force_line_height=0, hyphen="-"):
        self.name = name
        root = ET.parse(os.path.join(fonts_dir, name + ".fnt")).getroot()
        self.page_files = [page.get("file") for page in root.find("pages").findall("page")]
        self.letters = {}
        self.line_height = 0
        self.advance_max = 0
        self.space_width = 0
        self.ascent = 0
        self.cap_height = 0
        reference = None
        top = 10000
        for node in root.find("chars").findall("char"):
            text = node.get("letter")
            text = NAMED_LETTERS.get(text, text)
            letter = Letter(ord(text[0]), text, _int(node.get("page")),
                            (_int(node.get("x")), _int(node.get("y")), _int(node.get("width")), _int(node.get("height"))),
                            [_int(node.get("xoffset")), _int(node.get("yoffset"))], _int(node.get("xadvance")))
            self.letters[letter.code] = letter            # a later letter with the same code replaces
            if text in ("0", "A"):                        # the letter measurements are taken from
                reference = letter
            self.line_height = max(self.line_height, letter.rect[3])
            self.advance_max = max(self.advance_max, letter.advance)
            top = min(top, letter.offset[1])
            if text == " ":
                self.space_width = letter.advance
        for letter in self.letters.values():              # move everything up to the highest letter
            letter.offset[1] -= top
        if reference is not None:
            self.ascent = reference.offset[1] + reference.rect[3]
            self.cap_height = reference.rect[3]
        if force_line_height != 0:
            self.line_height = force_line_height
        self.hyphen = "" if hyphen == "NONE" else hyphen
        self.hyphen_width = self.text_width(self.hyphen)

    @property
    def descent(self):
        return self.line_height - self.ascent

    def text_width(self, text):
        """Sum of the advances; characters the font lacks count as 0."""
        return sum(self.letters[ord(c)].advance for c in text if ord(c) in self.letters)

    def split(self, text, max_width, multi_line=True):
        """Breaks text into lines. Returns (lines as (text, width), hyphenated,
        widest line, number of non-space characters)."""
        lines = []
        hyphenated = False

        def flush(line):
            line = line.rstrip()
            lines.append((line, self.text_width(line)))

        if max_width == 0:
            for part in text.split("\n"):
                part = part.strip()
                lines.append((part, self.text_width(part)))
        else:
            max_width = max(max_width, self.advance_max)
            current, width = "", 0
            for paragraph in text.split("\n"):
                words = paragraph.split(" ")
                while words:
                    word = words[0]
                    word_width = self.text_width(word)
                    if word_width + width < max_width:
                        current += word + " "
                        width += self.space_width + word_width
                        words.pop(0)
                        if words:
                            continue
                    elif word_width >= max_width:             # longer than a whole line: cut it
                        count = 0
                        while count < len(word):
                            if self.text_width(word[:count + 1]) + width + self.hyphen_width >= max_width:
                                break
                            count += 1
                        if count > 0:
                            head, words[0] = word[:count], word[count:]
                            current += head if head[-1:] == self.hyphen else head + self.hyphen
                            hyphenated = True
                    flush(current)
                    current, width = "", 0
            if current.rstrip():
                flush(current)
        if not multi_line and len(lines) > 1:
            lines = lines[:1]
        return (lines, hyphenated, max([w for _, w in lines], default=0),
                sum(1 for line, _ in lines for c in line if c != " "))


class FontLib:
    def __init__(self, assets_dir, hyphen="-"):
        text = open(os.path.join(assets_dir, "data", "Fonts.xml"), encoding="utf-8").read()
        self.defs = {}
        for node in ET.fromstring(text).findall("font"):
            force = _int(node.get("lineheight")) if node.get("lineheight") is not None else 0
            self.defs[node.get("id")] = Font(os.path.join(assets_dir, "fonts"), node.get("file"), force, hyphen)

    def get(self, font_id):
        if font_id not in self.defs:
            raise KeyError("Font not found: " + font_id)
        return self.defs[font_id]


if __name__ == "__main__":
    lib = FontLib(sys.argv[1])
    print("%-20s %-34s %5s %5s %5s %5s %5s %5s %s" % (
        "id", "file", "line", "asc", "cap", "desc", "space", "maxw", "letters"))
    for font_id, font in lib.defs.items():
        print("%-20s %-34s %5d %5d %5d %5d %5d %5d %d" % (
            font_id, font.name, font.line_height, font.ascent, font.cap_height, font.descent,
            font.space_width, font.advance_max, len(font.letters)))
