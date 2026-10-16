"""Checks of the desk item's movement (docs/desk-movement.md) with
scripts/reference/deskmove.py, the desktop layout and Papers.xml.

Usage: python -I desk_movement_check.py <reference dir> <assets dir>

1. Every paper's reveal: the kind, where the paper starts and stops, and
   how many 1/60 s frames the reveal takes (closed sizes untilted).
2. The docked papers: their dock home against their closed picture's size;
   the path back home from three places, and that it lands.
3. The clamps: random drops on the desk, the counter and the wall, and
   how much of the paper stays in reach.
4. A fall to the counter's floor and a throw on the desk.
5. The give test and the drop's placement rules on a few cursor points.
Needs Pillow (picture sizes).
"""
import collections
import os
import random
import sys
import xml.etree.ElementTree as ET

from PIL import Image

sys.path.insert(0, sys.argv[1])
import deskmove as M  # noqa: E402
import layout as LAYOUT  # noqa: E402

L = LAYOUT.DESKTOP
assets = sys.argv[2]
pic_dir = os.path.join(assets, "assets", "papers")
problems = []
DT = 1.0 / 60.0


def size(name):
    path = os.path.join(pic_dir, name)
    if not os.path.exists(path):
        return None
    return Image.open(path).size


def closed_size(p):
    """Untilted closed size (desk-pictures.md): as it is for dock or mount papers,
    otherwise halved to even sizes, (w+1)//2*2 by (h+2)//2*2 of the half picture."""
    w, h = size(p["outer"])
    if p.get("dock") == "true" or p.get("mount"):
        return w, h
    hw, hh = -(-w // 2), -(-h // 2)          # Image.transformed rounds sizes up
    return (hw + 1) // 2 * 2, (hh + 2) // 2 * 2


def reveal_of(p):
    r = p.get("reveal")
    if r is None:
        return ("DOCKED",) if p.get("dock") == "true" else ("FROMSLOT",)
    if r.startswith("ondesk"):
        x, y = r.split(":")[1].split(",")
        return ("ONDESK", int(x), int(y))
    return ({"printbottom": "PRINTBOTTOM", "spitfromright": "SPITFROMRIGHT",
             "infiler": "INFILER", "printtop": "PRINTTOP"}.get(r, "FROMSLOT"),)


root = ET.parse(os.path.join(assets, "assets", "data", "Papers.xml")).getroot()
papers = [dict(n.attrib, _pages=[pg.get("image") for pg in n.findall("page")])
          for n in root.findall("paper")]

# 1. reveals
print("1. Reveals")
kinds = collections.Counter()
for p in papers:
    rv = reveal_of(p)
    kinds[rv[0]] += 1
    outer = closed_size(p)
    page = size(p["_pages"][0]) if p["_pages"] and p["_pages"][0] else None
    inner = page or outer
    dock = L["dockPoints"].get(p["id"].lower()) if p.get("dock") == "true" else None
    filer = M.Filer()
    item = M.DeskItem(outer, inner, filer_size=(175, 80), dock=dock, reveal=rv,
                      mount=size(p["mount"]) if p.get("mount") else None, filer=filer)
    filer.items.append(item)
    item.start_reveal(mount_pos=(10, 10))
    start = tuple(item.pos)
    frames = 0
    while item.state == M.REVEALING and frames < 2000:
        item.update(DT)
        frames += 1
    if item.state != M.NORMAL:
        problems.append("%s did not finish its reveal" % p["id"])
    if rv[0] in ("PRINTBOTTOM", "SPITFROMRIGHT", "PRINTTOP", "FROMSLOT") or p["id"] in (
            "Bulletin", "FamilyPhoto", "Rules"):
        print("   %-18s %-14s closed %-9s page %-9s start %-14s end %-14s %3d frames %s" % (
            p["id"], rv[0], "%dx%d" % outer, "%dx%d" % inner, start, tuple(item.pos), frames,
            item.placement))
    if item.placement == M.INNER:
        if not (L["desk"][0] - inner[0] < item.pos[0] < L["desk"][0] + L["desk"][2]):
            problems.append("%s ends off the desk" % p["id"])
print("   kinds:", dict(kinds))

# 2. docks
print("2. Docks")
for p in papers:
    if p.get("dock") != "true":
        continue
    key = p["id"].lower()
    dock = L["dockPoints"][key]
    cs = closed_size(p)
    same = tuple(dock["home"][2:]) == tuple(cs)
    print("   %-11s home %s, closed picture %dx%d: %s" % (
        key, dock["home"], cs[0], cs[1], "same size" if same else "DIFFERENT"))
    if not same:
        problems.append("dock %s home size differs from the closed picture" % key)
    for start in ((5, 5), (150, 120), (60, 140)):
        item = M.DeskItem(cs, cs, dock=dock, reveal=("DOCKED",))
        item.start_reveal()
        item.update(DT)
        item.pos = [float(start[0]), float(start[1])]
        frames, landed = 0, False
        while frames < 600:
            item.events = []
            item.update(DT)
            frames += 1
            if "sound drop" in item.events:
                landed = True
                break
        ok = landed and tuple(item.pos) == tuple(dock["home"][:2])
        print("      from %-10s home after %3d frames, landed: %s" % (start, frames, ok))
        if not ok:
            problems.append("dock %s from %s did not land at home" % (key, start))

# 3. clamps
print("3. Clamps")
rng = random.Random(5)
for placement, sz in ((M.INNER, (100, 140)), (M.INNER, (40, 20)), (M.OUTER, (30, 42)),
                      (M.MOUNT, (60, 50))):
    item = M.DeskItem(sz, sz, mount=sz)
    item.placement = placement
    xs, ys = [], []
    for _ in range(2000):
        item.pos = [rng.uniform(-400, 900), rng.uniform(-400, 600)]
        item.clamp()
        xs.append(item.pos[0])
        ys.append(item.pos[1])
    print("   %-5s %-9s x %7.1f..%-7.1f y %7.1f..%-7.1f" % (
        placement, "%dx%d" % sz, min(xs), max(xs), min(ys), max(ys)))
    if placement == M.INNER:
        mx, my = min(70, sz[0]), min(30, sz[1])
        r = L["boothInnerClamp"]
        if min(xs) != r[0] - sz[0] + mx or max(xs) != r[0] + r[2] - mx:
            problems.append("inner clamp x range")
        if min(ys) != r[1] - sz[1] + my or max(ys) != r[1] + r[3] - my:
            problems.append("inner clamp y range")

# 4. fall and throw
print("4. A fall and a throw")
item = M.DeskItem((30, 42), (60, 80))
item.state = M.NORMAL
item.placement = M.OUTER
item.pos = [80.0, 10.0]
frames = 0
while frames < 200:
    item.events = []
    item.update(DT)
    frames += 1
    if "sound drop" in item.events:
        break
print("   closed passport dropped at y 10 lands at y %s after %d frames" % (item.pos[1], frames))
if item.pos[1] != L["outerFloorMidY"] - 21:
    problems.append("fall end")
item = M.DeskItem((30, 42), (60, 80))
item.state = M.NORMAL
item.placement = M.INNER
item.pos = [300.0, 50.0]
item.touch.vel = [600.0, 0.0]
frames = 0
while item.touch.has_vel() and frames < 600:
    item.update(DT)
    frames += 1
print("   page thrown at 600 px/s slides to x %s in %d frames" % (item.pos[0], frames))

# 5. drag placement and the give test
print("5. Drag placement")
filer = M.Filer()
item = M.DeskItem((30, 42), (60, 80), filer_size=(175, 80), filer_type="CANFILER", filer=filer)
filer.items.append(item)
item.giveable = lambda it: M.GIVE_YES_NOW
item.state = M.NORMAL
item.placement = M.INNER
item.pos = [300.0, 60.0]
item.start_drag((310.0, 70.0))
for mouse in ((300.0, 60.0), (150.0, 60.0), (90.0, 30.0), (90.0, 130.0), (250.0, 214.0),
              (179.0, 214.0), (400.0, 214.0)):
    item.drag_to(mouse)
    print("   cursor %-14s -> %-5s at %-14s give icon %s" % (
        mouse, item.placement, tuple(item.pos), item.give_icon))
item.drag_to((90.0, 30.0))
out = item.end_drag()
print("   released over the give area:", out)
if "GIVING" not in out:
    problems.append("release over the give area did not give")

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
