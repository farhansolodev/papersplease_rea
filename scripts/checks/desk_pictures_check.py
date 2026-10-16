"""Checks of the desk pictures (docs/desk-pictures.md) against Papers.xml, the
pictures and scripts/reference/deskpics.py.

Usage: python -I desk_pictures_check.py <reference dir> <assets dir>

1. Every paper: its closed picture exists; which way it is made (turned and
   halved, or as it is because of dock or mount); its size untilted and the
   largest size over the whole tilt range; its wall picture exists.
2. The drawer: the envelope and the give icon exist; for every
   confiscatable paper, where the strip of its closed picture comes from.
3. Odd-shaped papers: how many pixels of each page picture the odd-shape
   test refuses (alpha 8 or less), and the same count for the other papers.
4. Stampable papers with more than one page (the ink layer stays when a
   page is turned).
5. The one mark with clipheight, which the desk item's clip replaces.
6. compareProximity: symmetry over random rectangle pairs, and the nested,
   same-rectangle and same-column cases.
Needs Pillow.
"""
import collections
import math
import os
import random
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import deskpics as D  # noqa: E402
import factpics as FP  # noqa: E402

assets = sys.argv[2]
problems = []
root = ET.parse(os.path.join(assets, "assets", "data", "Papers.xml")).getroot()
paper_nodes = root.findall("paper")
pic_dir = os.path.join(assets, "assets", "papers")


def load(name):
    path = os.path.join(pic_dir, name)
    if not os.path.exists(path):
        problems.append("missing picture %s" % name)
        return None
    return FP.load(path)


# 1. closed pictures
print("1. Closed pictures (outer), wall pictures (mount)")
kinds = collections.Counter()
for node in paper_nodes:
    p = dict(node.attrib)
    outer = load(p["outer"])
    if outer is None:
        continue
    turned = D.outer_is_turned(p)
    if not turned:
        kind = "as it is (%s)" % ("dock" if p.get("dock") == "true" else "mount")
        size0 = (outer.width, outer.height)
        biggest = size0
    elif p.get("rotate") == "false":
        kind = "halved, not tilted"
        o = D.outer_picture(assets, p, 0.0)
        size0 = biggest = (o.width, o.height)
    else:
        kind = "tilted and halved"
        o = D.outer_picture(assets, p, D.tilt_angle(0.5))
        size0 = (o.width, o.height)
        biggest = size0
        for k in range(0, 61, 5):            # every 5 degrees from -30 to +30
            o = D.outer_picture(assets, p, math.radians(k - 30))
            biggest = (max(biggest[0], o.width), max(biggest[1], o.height))
    kinds[kind] += 1
    mount = ""
    if p.get("mount"):
        m = load(p["mount"])
        if m is not None:
            mount = "mount %s %d x %d" % (p["mount"], m.width, m.height)
    print("  %-16s %-26s %-19s %3d x %3d  up to %3d x %3d  %s" % (
        p["id"] + ("/" + p["nation"] if p.get("nation") else ""), p["outer"], kind,
        size0[0], size0[1], biggest[0], biggest[1], mount))
for k, n in sorted(kinds.items()):
    print("  %3d papers: %s" % (n, k))

# 2. drawer
print("2. Drawer (filer) and give icon")
env_path = os.path.join(assets, D.FILER_ENVELOPE)
icon_path = os.path.join(assets, D.GIVE_ICON)
for path in (env_path, icon_path):
    if not os.path.exists(path):
        problems.append("missing %s" % path)
envelope = FP.load(env_path) if os.path.exists(env_path) else None
icon = FP.load(icon_path) if os.path.exists(icon_path) else None
if envelope is not None:
    print("  envelope %d x %d" % (envelope.width, envelope.height))
if icon is not None:
    print("  give icon %d x %d" % (icon.width, icon.height))
if envelope is not None:
    seen = set()
    for node in paper_nodes:
        p = dict(node.attrib)
        if p.get("canconfiscate") != "true" or p["outer"] in seen:
            continue
        seen.add(p["outer"])
        outer = load(p["outer"])
        rect, at = D.filer_strip_rect(outer, envelope)
        note = ""
        if outer.width - D.FILER_STRIP_W < D.FILER_STRIP_MIN_X:
            note = "  (narrower than 40: the strip starts at 10)"
        print("  %-26s %3d x %3d: strip x %g, %d x %g, at (%g, %g)%s" % (
            p["outer"], outer.width, outer.height, rect[0], rect[2], rect[3], at[0], at[1], note))
        if icon is not None:
            o = D.outer_picture(assets, p, D.tilt_angle(0.5))
            print("    give icon at %s over the %d-wide closed picture" %
                  (D.give_icon_place(o.width, icon.width, icon.height), o.width))

# 3. odd shapes
print("3. Pixels the odd-shape test refuses (alpha <= 8): every page of an")
print("   odd-shaped paper, and the first page of the others that have some")
no_effect = []
for node in paper_nodes:
    p = dict(node.attrib)
    odd = p.get("oddshape") == "true"
    pages = node.findall("page") if odd else node.findall("page")[:1]
    for page in pages:
        img = load(page.get("image"))
        if img is None:
            continue
        refused = sum(1 for px in img.px if (px >> 24) <= D.ODD_SHAPE_ALPHA)
        if odd or refused:
            print("  %-16s %-5s %-28s %6d of %6d" % (
                p["id"], "odd" if odd else "plain", page.get("image"), refused, len(img.px)))
        if odd and refused == 0:
            no_effect.append("%s %s" % (p["id"], page.get("image")))
print("  odd-shaped pages where the test refuses nothing (a note, not a problem): %s"
      % (", ".join(no_effect) or "none"))

# 4. stampable papers with several pages
print("4. Stampable papers with more than one page")
for node in paper_nodes:
    p = dict(node.attrib)
    pages = node.findall("page")
    if p.get("stampable") == "true":
        print("  %-16s fromtraveler=%-5s pages %d" % (
            p["id"], p.get("fromtraveler", "false"), len(pages)))

# 5. clipheight
print("5. Marks with clipheight")
for node in paper_nodes:
    for page in node.findall("page"):
        for mark in page.findall("mark"):
            if mark.get("clipheight"):
                print("  %s %s: %s clipheight %s" % (
                    node.get("id"), page.get("image"), mark.get("text") or mark.get("image"),
                    mark.get("clipheight")))

# 6. compareProximity
print("6. compareProximity")
rng = random.Random(1)
asym = 0
for _ in range(20000):
    ra = (rng.randint(0, 40), rng.randint(0, 40), rng.randint(1, 60), rng.randint(1, 30))
    rb = (rng.randint(0, 40), rng.randint(0, 40), rng.randint(1, 60), rng.randint(1, 30))
    p = (rng.uniform(0, 80), rng.uniform(0, 60))
    if D.compare_proximity(p, ra, rb) != -D.compare_proximity(p, rb, ra):
        asym += 1
print("  random pairs where swapping the two does not swap the answer: %d of 20000" % asym)
if asym:
    problems.append("compareProximity not symmetric in %d cases" % asym)
cases = [
    ("nested: the inner wins", (5, 5), (0, 0, 40, 20), (2, 2, 10, 8), 1),
    ("same rectangle", (5, 5), (0, 0, 10, 10), (0, 0, 10, 10), 0),
    ("same column, narrow beats wide", (3, 12), (0, 0, 60, 10), (0, 10, 10, 10), None),
]
for label, p, ra, rb, want in cases:
    got = D.compare_proximity(p, ra, rb)
    print("  %-34s %s %s at %s -> %d" % (label, ra, rb, p, got))
    if want is not None and got != want:
        problems.append("compareProximity %s: %d, expected %d" % (label, got, want))

print()
print("problems: %s" % ("none" if not problems else len(problems)))
for p in problems:
    print("  " + p)
