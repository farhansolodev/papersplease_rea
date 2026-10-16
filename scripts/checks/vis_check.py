"""Checks of the rest of app.vis (docs/vis-basics.md) with scripts/reference/vis.py.

Usage: python -I vis_check.py <reference dir> <assets dir>

1. Every attribute in the data files that the game reads as a point
   (Point.parse) or a rectangle (Rect.parse): how many values, and any that
   the game's split rules would refuse (and so replace by the default).
2. Colours: the 0xAARRGGBB to float and back round trip, on every value of
   each channel.
3. A nine-slice frame's tiles add up to its outer size.
"""
import collections
import glob
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import vis as V  # noqa: E402

assets = sys.argv[2]
data = os.path.join(assets, "assets", "data")
problems = []

POINTS = ("pos", "pos2", "visacenter", "datepos", "offset", "size", "stamplinksize", "xy",
          "range", "randomize")
RECTS = ("emblemrect", "rect")

# 1. text forms
print("1. Points and rectangles in the data files")
counts = collections.Counter()
for path in sorted(glob.glob(os.path.join(data, "*.xml"))):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        print("   %s: not well-formed XML, skipped (read by the game's own parser)" % os.path.basename(path))
        continue
    name = os.path.basename(path)
    for el in root.iter():
        for attr, value in el.attrib.items():
            if attr in POINTS:
                counts[(name, attr)] += 1
                if len(value.split(" ")) != 2:
                    problems.append("%s %s=%r: not two parts split on one space" % (name, attr, value))
                elif any(v != v for v in V.parse_point(value)):
                    problems.append("%s %s=%r: not a number" % (name, attr, value))
            elif attr in RECTS:
                counts[(name, attr)] += 1
                parts = [p for p in value.split(" ") if p.strip()]
                if len(parts) != 4:
                    problems.append("%s %s=%r: not four parts" % (name, attr, value))
for (name, attr), n in sorted(counts.items()):
    print("   %-18s %-14s %5d" % (name, attr, n))
print("   (pos and pos2 in Papers.xml are read by data.Mark; the other names may")
print("   be read as plain text in some files: a refusal below is only a lead)")

# 2. colours
print("2. Colour round trip")
bad = 0
for v in range(256):
    for shift in (0, 8, 16, 24):
        u = (v << shift) | (0xFF000000 if shift != 24 else 0)
        if V.to_uint(*V.from_uint(u)) != u:
            bad += 1
print("   values that do not come back: %d of 1024" % bad)
if bad:
    problems.append("colour round trip")

# 3. frames
print("3. Nine-slice frame")
for image, s9, outer in (((9, 9), (3, 3, 3, 3), (40, 20)), ((21, 15), (5, 4, 11, 7), (100, 64))):
    tiles = V.frame_tiles(image, s9, outer)
    area = sum(d[2] * d[3] for _, d in tiles)
    ok = area == outer[0] * outer[1]
    print("   image %s, middle %s, outer %s: %d tiles, area %s" % (image, s9, outer, len(tiles), "ok" if ok else "WRONG"))
    if not ok:
        problems.append("frame tiles")

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
