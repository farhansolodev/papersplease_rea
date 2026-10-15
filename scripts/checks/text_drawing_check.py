"""Checks for docs/text-drawing.md: which characters of the English data a
font lacks (app.vis.Text draws such a character as a box in the text
colour), and whether every font sheet is plain white with alpha 0 or 255
(what the preview in scripts/reference/text.py relies on).

Usage: python -I text_drawing_check.py <reference dir> <assets dir>
"""
import html
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import fonts as F  # noqa: E402
from PIL import Image  # noqa: E402

assets = sys.argv[2]
data_dir = os.path.join(assets, "data")
lib = F.FontLib(assets)
problems = []

# Every character of Text.xml's texts, after the escapes the file uses.
raw = open(os.path.join(data_dir, "Text.xml"), encoding="utf-8").read()
text_chars = set()
for body in re.findall(r"<t>(.*?)</t>", raw, re.S):
    body = body.replace("\\n", "\n").replace("<br>", "\n").replace("<br/>", "\n")
    text_chars |= set(html.unescape(body))
text_chars -= {"\n", "\r"}

# Every character of each data file (markup included).
file_chars = {}
for name in sorted(os.listdir(data_dir)):
    path = os.path.join(data_dir, name)
    if os.path.isfile(path) and name.rsplit(".", 1)[-1] in ("xml", "txt", "csv"):
        file_chars[name] = set(open(path, encoding="utf-8", errors="replace").read()) - {"\n", "\r", "\t", "﻿"}

print("characters in Text.xml texts:", len(text_chars))
print("%-20s %-34s %s" % ("font id", "Text.xml characters missing", "data files with characters missing (count)"))
for font_id, font in lib.defs.items():
    have = set(chr(c) for c in font.letters)
    miss_text = "".join(sorted(text_chars - have))
    if len(miss_text) > 30:
        miss_text = miss_text[:30] + "... (%d)" % len(miss_text)
    files = ["%s %d" % (name, len(chars - have)) for name, chars in file_chars.items() if chars - have]
    print("%-20s %-34s %s" % (font_id, ascii(miss_text), ", ".join(files) if len(files) <= 3
                              else "%d files" % len(files)))

print("-- font sheets --")
for file_name in sorted(set(f for font in lib.defs.values() for f in font.page_files)):
    image = Image.open(os.path.join(assets, "fonts", file_name)).convert("RGBA")
    colours = set(image.getdata())
    odd = [c for c in colours if c[3] not in (0, 255) or (c[3] == 255 and c[:3] != (255, 255, 255))]
    print("  %-40s %4d x %-4d %d colours%s" % (file_name, image.width, image.height, len(colours),
                                             "" if not odd else ", not plain white: %r" % odd[:4]))
    if odd:
        problems.append(file_name + " is not plain white with alpha 0 or 255")
print("problems:", problems or "none")
