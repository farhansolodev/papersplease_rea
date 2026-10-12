"""Cross-check of docs/faces.md against Faces.xml and the face sheet images.

Usage: python -I faces_check.py <reference dir> <faces dir> Faces.xml FacePalette.png

Needs the Pillow library (through scripts/reference/faces.py).
"""
import collections
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import faces as F

C = collections.Counter
faces_dir, faces_xml, palette_png = sys.argv[2:5]

READ = {"age", "bmi", "hairheight", "canbeconfusing", "head", "shoulders", "mouth", "eyes",
        "nhead", "nshoulders", "nmouth", "neyes"}
root = ET.parse(faces_xml).getroot()
sheets = root.findall("sheet")
attrs = C(a for s in sheets for f in s.findall("face") for a in f.attrib)
print("-- Faces.xml --")
print("  sheets:", [(s.get("id"), len(s.findall("face"))) for s in sheets])
print("  face attributes:", dict(attrs))
print("  attributes the loader does not read:", sorted(set(attrs) - READ))
print("  other elements:", sorted({e.tag for e in root.iter()} - {"faces", "sheet", "face"}))
confusing = C(w for s in sheets for f in s.findall("face") for w in (f.get("canbeconfusing") or "").split())
print("  canbeconfusing words:", dict(confusing))
ints = [(f.get("id"), a) for s in sheets for f in s.findall("face") for a in ("age", "bmi", "hairheight")
        if not (f.get(a) or "").lstrip("-").isdigit()]
print("  age/bmi/hairheight missing or not whole numbers:", ints)
hair = [int(f.get("hairheight")) for s in sheets for f in s.findall("face")]
print("  hairheight range:", min(hair), "to", max(hair))

print("\n-- sheet images --")
KEYS = {F.KEY_EYE0: "eye0", F.KEY_EYE1: "eye1", F.KEY_NOSEMOUTH0: "nosemouth0",
        F.KEY_NOSEMOUTH1: "nosemouth1", F.KEY_EYE_NOSEMOUTH: "eye+nosemouth",
        F.KEY_HEAD_AND_SHOULDERS: "head+shoulders", F.KEY_SHOULDERS: "shoulders",
        F.KEY_MARK: "mark", 0: "transparent"}
key_colors = C()
alphas = C()
sizes = C()
bad_marks = []
missing = []
cells = 0
for s in sheets:
    sid = s.get("id")
    paths = {suffix: os.path.join(faces_dir, "Sheet%s%s.png" % (sid, suffix)) for suffix in ("", "d", "p")}
    for suffix, path in paths.items():
        if not os.path.exists(path):
            missing.append(os.path.basename(path))
    if any(not os.path.exists(p) for p in paths.values()):
        continue
    images = {suffix: F.Image.load(path) for suffix, path in paths.items()}
    for image in images.values():
        sizes[(image.width, image.height)] += 1
        alphas.update(p >> 24 for p in image.px)
    for position in range(len(s.findall("face"))):
        cells += 1
        x, y = (position % 2) * F.PIECE_W, (position // 2) * F.PIECE_H
        cell = images["p"].crop(x, y, F.PIECE_W, F.PIECE_H)
        key_colors.update(KEYS.get(p, hex(p)) for p in cell.px)
        marks = sum(1 for p in cell.px if p == F.KEY_MARK)
        if marks != 7:
            bad_marks.append((sid, position, marks))
print("  missing files:", missing)
print("  image sizes:", dict(sizes), "| alpha values:", dict(alphas))
print("  faces checked:", cells, "| faces without exactly 7 marker dots:", bad_marks)
print("  key image colours (pixels):", dict(key_colors))
on_disk = sorted(n for n in os.listdir(faces_dir) if n.startswith("Sheet"))
named = {"Sheet%s%s.png" % (s.get("id"), x) for s in sheets for x in ("", "d", "p")}
print("  sheet files with no sheet in Faces.xml:", sorted(set(on_disk) - named))

print("\n-- marker order (reading order must give eyes, nose, mouth, chin, shoulders) --")
odd = []
right_first = []
for s in sheets:
    male = s.get("id").startswith("M")
    number = int(s.get("id")[1:])
    for position in range(len(s.findall("face"))):
        piece = F.FacePiece(faces_dir, male, number * 4 + position, False).make_head()
        if piece.eye0 is None:
            continue                      # no artwork at this position (reported above)
        ok = (piece.eye0[1] == piece.eye1[1] and piece.eye0[0] < piece.eye1[0]
              and piece.eye0[1] < piece.nose[1] < piece.mouth[1] < piece.chin[1] <= piece.shoulder0[1]
              and piece.shoulder0[0] != piece.shoulder1[0])
        if not ok:
            odd.append((s.get("id"), position))
        if piece.shoulder0[0] > piece.shoulder1[0]:
            right_first.append((s.get("id"), position, piece.shoulder0, piece.shoulder1))
print("  faces whose markers are not in that layout:", odd)
print("  faces whose first shoulder dot is the right-hand one:", right_first)

print("\n-- FacePalette.png --")
palette = F.Image.load(palette_png)
print("  size:", (palette.width, palette.height), "| palette rows:", palette.height // 10)
row0 = [palette.px[k * 10] for k in range(5)]
print("  row 0 swatches are the five face and clothes colours:",
      set(row0) == {F.FACE0, F.FACE1, F.FACE2, F.CLOTHES0, F.CLOTHES1},
      "| order:", [hex(c) for c in row0])
uniform = all(len({palette.px[(r * 10 + dy) * palette.width + k * 10 + dx]
                   for dy in range(10) for dx in range(10)}) == 1
              for r in range(palette.height // 10) for k in range(5))
print("  every 10x10 swatch is one flat colour:", uniform)
