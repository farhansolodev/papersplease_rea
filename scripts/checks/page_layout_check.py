"""Checks of the page pictures against Papers.xml and scripts/reference/pages.py
(docs/page-layout.md).

Usage: python -I page_layout_check.py <reference dir> <assets dir>

1. For every page: marks without `pos` per side, against the pixels of each
   candidate marker colour (opaque black, red, blue) in the page picture.
2. Lays out every page (fact marks get their fact name as text, every page
   exists, the rulebook tabs upgrade on) and lists literal texts that leave
   the page picture.
Needs Pillow.
"""
import collections
import os
import sys

sys.path.insert(0, sys.argv[1])
import fonts
import pages as P
from PIL import Image

assets = sys.argv[2]
papers = P.load(assets)
font_lib = fonts.FontLib(assets)
problems = []
C = collections.Counter

CANDIDATES = {"black": (0, 0, 0, 255), "red": (255, 0, 0, 255), "blue": (0, 0, 255, 255)}

print("-- 1. marker pixels against marks without pos --")
pages_seen = set()
totals = C()
side1_pages = []
extra_black = []
for paper in papers:
    for index, page in enumerate(paper.pages):
        if page.image in pages_seen and False:
            continue
        path = os.path.join(assets, "papers", page.image)
        if not os.path.exists(path):
            problems.append("%s page %d: picture %s missing" % (paper.id, index, page.image))
            continue
        image = Image.open(path).convert("RGBA")
        counts = C(image.getdata())
        found = {name: counts[rgba] for name, rgba in CANDIDATES.items()}
        label = "%s%s page %d (%s)" % (paper.id, " " + paper.nation if paper.nation else "", index, page.image)
        # a seal mark takes a pixel too, but places itself by its emblemrect
        need = C(m.side for m in page.marks if m.pos is None)
        users = C(m.side for m in page.marks if m.pos is None and m.type != "EMBLEM")
        totals["pages"] += 1
        totals["marks without pos, side 0"] += need[0]
        totals["marks without pos, side 1"] += need[1]
        order = [m.type for m in page.marks if m.pos is None and m.side == 0]
        if "EMBLEM" in order and order[order.index("EMBLEM"):].count("EMBLEM") != len(order) - order.index("EMBLEM"):
            problems.append(label + ": a seal mark comes before a mark that needs its pixel")
        if "EMBLEM" in order:
            totals["pages whose seal mark is the last mark without pos"] += 1
        if users[0] > found["black"]:
            problems.append("%s: %d side-0 marks need a pixel, only %d black pixels" % (label, users[0], found["black"]))
        elif found["black"] > need[0]:
            extra_black.append((label, need[0], found["black"]))
        if need[1]:
            side1_pages.append((paper.id, index, page.image, need[1], found["red"], found["blue"]))
        elif found["red"] or found["blue"]:
            totals["pages with red or blue pixels but no side-1 mark"] += 1
        if set(m.side for m in page.marks) - {0, 1}:
            problems.append("%s page %d: a side other than 0 and 1" % (paper.id, index))
print("  ", dict(totals))
print("  pages with side-1 marks (paper, page, picture, marks, red pixels, blue pixels):")
for row in side1_pages:
    print("    %-16s %d %-28s %2d  red %2d  blue %2d" % row)
red_ok = all(r[3] == r[4] for r in side1_pages)
blue_ok = all(r[3] == r[5] for r in side1_pages)
print("  side 1 matches red on every page: %s; blue: %s" % (red_ok, blue_ok))
print("  pages with more black pixels than marks without pos (all are painted over):")
for row in extra_black:
    print("    %-48s marks %2d  black pixels %2d" % row)
if not red_ok:
    problems.append("side-1 marks do not match the red pixels")

print("\n-- 2. every page laid out (fact marks show their fact name) --")
outside = []
kinds = C()
for paper in papers:
    for index, page in enumerate(paper.pages):
        path = os.path.join(assets, "papers", page.image)
        if not os.path.exists(path):
            continue
        image = Image.open(path).convert("RGBA")
        placed = P.layout(paper, index, image, font_lib, has_rulebook_tabs=True,
                          image_size=P.literal_image_size(assets))
        for v in placed:
            kinds[v.kind] += 1
            if v.kind == "text" and v.mark.fact_id() is None:
                w, h = v.size
                if v.x < 0 or v.y < 0 or v.x + w > image.width or v.y + h > image.height:
                    outside.append("%s%s page %d %s %r at %d,%d size %dx%d in %dx%d" % (
                        paper.id, " " + paper.nation if paper.nation else "", index, v.name,
                        v.text.text, v.x, v.y, w, h, image.width, image.height))
        left = [C(Image.open(path).convert("RGBA").getdata())[c] for c in P.MARKER_RGBA]
        after = C(image.getdata())
        if any(after[c] for c in P.MARKER_RGBA) and any(left):
            totals["pages with marker pixels left after painting"] += 1
print("  visuals by kind:", dict(kinds))
print("  literal texts that reach outside the page picture:", len(outside))
for line in outside:
    print("    " + line)

print("\nproblems:", problems or "none")
