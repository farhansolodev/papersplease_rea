"""Cross-checks Fonts.xml and the .fnt files against what the loader reads.

Usage: python -I fonts_check.py <reference dir> <assets dir>
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import fonts as F

assets = sys.argv[2]
fonts_dir = os.path.join(assets, "fonts")
problems = []

xml_text = open(os.path.join(assets, "data", "Fonts.xml"), encoding="utf-8").read()
root = ET.fromstring(xml_text)
print("Fonts.xml: %d fonts, tags %s, attributes %s" % (
    len(root.findall("font")), sorted({e.tag for e in root.iter()}),
    sorted({a for e in root.iter() for a in e.attrib})))
ids = [n.get("id") for n in root.findall("font")]
if len(ids) != len(set(ids)):
    problems.append("duplicate font id")
used = {n.get("file") for n in root.findall("font")}
present = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(fonts_dir, "*.fnt"))}
print("font files used: %d, present: %d, used but missing: %s, present but unused: %s" % (
    len(used), len(present), sorted(used - present) or "none", sorted(present - used) or "none"))
if used - present:
    problems.append("missing font file")

tags, attrs = set(), set()
for name in sorted(present):
    node = ET.parse(os.path.join(fonts_dir, name + ".fnt")).getroot()
    tags |= {e.tag for e in node.iter()}
    attrs |= {e.tag + "." + a for e in node.iter() for a in e.attrib}
    codes, long_names, id_differs, repeats = set(), 0, 0, 0
    for char in node.iter("char"):
        text = F.NAMED_LETTERS.get(char.get("letter"), char.get("letter"))
        long_names += len(text) != 1
        id_differs += ord(text[0]) != int(char.get("id"))
        repeats += ord(text[0]) in codes
        codes.add(ord(text[0]))
    pages = [p.get("file") for p in node.iter("page")]
    missing = [p for p in pages if not os.path.exists(os.path.join(fonts_dir, p))]
    print("  %-34s letters %4d (count attribute %s), sheets %d, letter names longer than one character %d, "
          "letter differs from id %d, repeated %d, has 0 %s, has A %s" % (
              name, len(codes), node.find("chars").get("count"), len(pages), long_names, id_differs, repeats,
              ord("0") in codes, ord("A") in codes))
    if missing or long_names or id_differs or repeats:
        problems.append(name)
print(".fnt tags:", sorted(tags))
print(".fnt attributes:", sorted(attrs))

lib = F.FontLib(assets)
print("measurements (line height, ascent, capital height, descent, space width, widest advance):")
for font_id, font in lib.defs.items():
    print("  %-20s %3d %3d %3d %3d %3d %3d" % (font_id, font.line_height, font.ascent, font.cap_height,
                                             font.descent, font.space_width, font.advance_max))
font = lib.get("regular")
sample = "Glory to Arstotzka. Cause no trouble. Supercalifragilisticexpialidocious"
for width in (0, 60, 30):
    lines, hyphenated, widest, letters = font.split(sample, width)
    print("split at %d: %s hyphenated=%s widest=%d letters=%d" % (width, [l for l, _ in lines], hyphenated, widest, letters))
    if width and widest >= max(width, font.advance_max):
        problems.append("a line is too wide")
    if "".join(l for l, _ in lines).replace(" ", "").replace("-", "") != sample.replace(" ", "").replace("-", ""):
        problems.append("split lost text")
print("problems:", problems or "none")
