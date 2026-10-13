"""Checks of Emblems.xml and Bodies.xml against the code's rules and the pictures.

Usage: python -I emblems_bodies_check.py <reference dir> <assets dir> <stringliteral.json>

<assets dir> is extracted/art/assets. Needs Pillow (for picture sizes).
"""
import collections
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image

sys.path.insert(0, sys.argv[1])
from rand import Rand

C = collections.Counter
assets = sys.argv[2]
data = os.path.join(assets, "data")
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
code_strings = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}
problems = []

# ---------------------------------------------------------------- emblems
root = ET.fromstring(read("Emblems.xml").split("?>", 1)[1])
emblems = root.findall("emblem")
print("-- Emblems.xml --")
print("  <emblem> attributes:", dict(C(a for e in emblems for a in e.attrib)),
      "| <nation> attributes:", dict(C(a for e in emblems for n in e.findall("nation") for a in n.attrib)))
read_by_code = {"id", "file", "count", "valid", "size"}
for attribute in {a for e in emblems for a in e.attrib}:
    if attribute not in read_by_code:
        print("  attribute the loader does not read: %s (the word is %s the code's strings)" % (
            attribute, "among" if attribute in code_strings else "NOT among"))

sets = []            # (id, nation, count, valid, (w, h), file): EmblemLib's list
for e in emblems:
    size = tuple(int(v) for v in e.get("size").split(" "))
    if e.get("file") is not None:
        sets.append((e.get("id"), None, int(e.get("count")), int(e.get("valid")), size, e.get("file")))
    else:
        for n in e.findall("nation"):
            sets.append((e.get("id"), n.get("id"), int(e.get("count")), int(e.get("valid")), size, n.get("file")))
print("  emblem sets built:", len(sets))
for emblem_id, nation, count, valid, (w, h), file in sets:
    path = os.path.join(assets, file)
    if not os.path.exists(path):
        problems.append("emblem sheet missing: " + file)
        continue
    sheet = Image.open(path)
    columns = sheet.width // w
    cells = columns * (sheet.height // h)
    print("  %-20s %-10s sheet %dx%d, cells %dx%d -> %d per row, %d cells; count %d, valid %d" % (
        emblem_id, nation or "-", sheet.width, sheet.height, w, h, columns, cells, count, valid))
    if cells < count or valid > count or sheet.width % w or sheet.height % h:
        problems.append("emblem sheet does not fit its count: " + file)


def emblem_cell(rand, count, valid, want_valid):
    """EmblemLib.getEmblemImage: which cell of the sheet (one draw)."""
    r = rand.random()
    return int(valid * r) if want_valid else int((count - valid) * r + valid)


rand = Rand(1)
seen = C()
for emblem_id, nation, count, valid, size, file in sets[:3]:
    good = C(emblem_cell(rand, count, valid, True) for _ in range(3000))
    bad = C(emblem_cell(rand, count, valid, False) for _ in range(3000))
    print("  %s%s: valid picks use cells %s, invalid picks use cells %s" % (
        emblem_id, "/" + nation if nation else "", sorted(good), sorted(bad)))
    if max(good) >= valid or min(bad) < valid or max(bad) >= count:
        problems.append("emblem cell out of its range: " + emblem_id)
facts = read("Facts.xml")
used = sorted(set(re.findall(r'Emblem/(\w+)', facts + read("Papers.xml") + read("Errors.txt"))))
print("  emblem ids named in Facts.xml, Papers.xml, Errors.txt:", used,
      "| all defined:", all(u in {s[0] for s in sets} for u in used))
nations_xml = set(re.findall(r'<nation id="([^"]+)"', facts))
print("  nations with a diplomatic emblem:", sorted(s[1] for s in sets if s[1]),
      "| nations in Facts.xml without one:", sorted(nations_xml - {s[1] for s in sets if s[1]}))

# ---------------------------------------------------------------- bodies
root = ET.fromstring(read("Bodies.xml"))
print("\n-- Bodies.xml --")
print("  tags:", dict(C(e.tag for e in root.iter())))
locs = {l.get("id"): tuple(int(v) for v in l.get("rect").split(" ")) for l in root.findall("loc")}
contras = root.findall("contra")
print("  attributes: loc", dict(C(a for l in root.findall("loc") for a in l.attrib)),
      "| contra", dict(C(a for c in contras for a in c.attrib)),
      "| offset", dict(C(a for c in contras for o in c.findall("offset") for a in o.attrib)))
print("  places:", locs)
print("  contraband by type:", dict(C(c.get("type") for c in contras)), "| by place:", dict(C(c.get("loc") for c in contras)))
faces = os.path.join(assets, "faces")
body_ids = ["F0", "F1", "F2", "M0", "M1", "M2"]
sizes = {}
for body in body_ids:
    for suffix in ("", "c"):
        path = os.path.join(faces, "Body%s%s.png" % (body, suffix))
        if not os.path.exists(path):
            problems.append("body picture missing: " + os.path.basename(path))
        else:
            sizes[body + suffix] = Image.open(path).size
print("  body pictures (unclothed and clothed) present for:", body_ids, "| sizes:", sorted(set(sizes.values())))
offsets_for = C(o.get("body") for c in contras for o in c.findall("offset"))
print("  offsets given per body:", dict(sorted(offsets_for.items())),
      "| bodies with none (offset 0 0 is used):", [b for b in body_ids if b not in offsets_for])
outside = []
for c in contras:
    if c.get("loc") not in locs:
        problems.append("contraband names a missing place: " + c.get("loc"))
        continue
    path = os.path.join(faces, c.get("file"))
    if not os.path.exists(path):
        problems.append("contraband picture missing: " + c.get("file"))
        continue
    width, height = Image.open(path).size
    x, y, w, h = locs[c.get("loc")]
    given = {o.get("body"): tuple(int(v) for v in o.get("val").split(" ")) for o in c.findall("offset")}
    for body in body_ids:
        ox, oy = given.get(body, (0, 0))
        # The piece is cut from the contraband picture at the place moved
        # back by the offset, and pasted on the body at the place itself.
        cx, cy = x - ox, y - oy
        if cx < 0 or cy < 0 or cx + w > width or cy + h > height:
            outside.append((c.get("file"), body, (cx, cy, w, h), (width, height)))
print("  contraband picture sizes:", sorted({Image.open(os.path.join(faces, c.get("file"))).size for c in contras}))
print("  cut-outs reaching outside the contraband picture:", outside or "none")


def body_id(male, bmi):
    return ("M" if male else "F") + ("0" if bmi < 21 else "2" if bmi > 24 else "1")


print("  body for body-mass 18, 21, 24, 25:", [body_id(True, b) for b in (18, 21, 24, 25)])
files = [c.get("file") for c in contras]
wanted = sorted(set(re.findall(r"contrabandTypes\s+(\S+)", read("Travelers.txt"))))
print("  contrabandTypes values in Travelers.txt:", wanted)
for want in wanted:
    if want.startswith("$"):
        matches = [f for f in files if want[1:] in f]
    else:
        matches = [c.get("file") for c in contras if c.get("type") in want]
    print("    %-12s matches %s" % (want, matches))
    if not matches:
        problems.append("contrabandTypes value that matches nothing: " + want)
non_bomb = [c.get("type") for c in contras if c.get("type") != "bomb"]
print("  list the random non-bomb type is drawn from:", dict(C(non_bomb)))

print("\nproblems:", sorted(set(problems)) or "none")
