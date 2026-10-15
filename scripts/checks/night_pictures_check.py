"""Checks the night screen's family pictures against the way the code cuts
them (night-pictures.md).

Usage: python -I night_pictures_check.py <assets dir>   (needs Pillow)

<assets dir> is extracted\\art\\assets. For each picture FamilyVisuals uses
it checks that the file is there and that it divides exactly into the
pieces the code cuts, of the size FamilyVisualsDim gives them: rows stacked
top to bottom, or columns side by side. For the passport covers, which the
code halves (Image.transformed with scale 0.5), it checks that half the
cover is the passport size. It also checks the token names: every name of
Facts.xml's tokenOrder must be one of the pieces of Tokens.png.
"""
import os
import re
import sys

from PIL import Image

assets = sys.argv[1]
problems = []

# (picture, cut, piece width, piece height, pieces, what the pieces are)
PICTURES = [
    ("ApartmentClass.png", "cols", 40, 30, 4, "8, 7, 6, 5 CLASS (C8 or other, C7, C6, C5)"),
    ("Emotions.png", "rows", 30, 30, 8, "HAPPY OK SAD COLD SICK VERYSICK DEAD HUNGRY"),
    ("Tokens.png", "rows", 29, 29, 8, "Empty, then the 7 nations of imageTokenIds"),
    ("Upgrades.png", "rows", 45, 15, 6, "empty, then 5 upgrades"),
    ("NightPassportFrame.png", "rows", 30, 40, 1, "no passports"),
]
for name, cut, pw, ph, count, what in PICTURES:
    path = os.path.join(assets, name)
    if not os.path.exists(path):
        problems.append(name + ": not found")
        continue
    w, h = Image.open(path).size
    want = (pw, ph * count) if cut == "rows" else (pw * count, ph)
    ok = (w, h) == want
    print("%-26s %3d x %-3d  %d %s of %d x %d  %s%s" % (name, w, h, count, cut, pw, ph, what,
                                                       "" if ok else "   <-- expected %d x %d" % want))
    if not ok:
        problems.append("%s: %d x %d, expected %d x %d" % (name, w, h, want[0], want[1]))

for name in ("papers/PassportOuterArstotzka.png", "papers/PassportOuterObristan.png"):
    path = os.path.join(assets, name)
    if not os.path.exists(path):
        problems.append(name + ": not found")
        continue
    w, h = Image.open(path).size
    ok = (w * 0.5, h * 0.5) == (30, 40)
    print("%-34s %3d x %-3d  halved: %g x %g%s" % (name, w, h, w * 0.5, h * 0.5,
                                                   "" if ok else "   <-- expected 30 x 40"))
    if not ok:
        problems.append("%s: half is not 30 x 40" % name)

IMAGE_TOKEN_IDS = ["Empty", "Obristan", "UnitedFed", "Republia", "Antegria", "Impor", "Kolechia", "Arstotzka"]
facts = open(os.path.join(assets, "data", "Facts.xml"), encoding="utf-8").read()
order = [t for t in re.search(r'tokenOrder="([^"]*)"', facts).group(1).split(" ") if t.strip()]
print("tokenOrder: %s (%d names)" % (" ".join(order), len(order)))
if len(order) != 7:
    problems.append("tokenOrder has %d names; the code draws 7 places" % len(order))
for token in order:
    if token not in IMAGE_TOKEN_IDS:
        problems.append("tokenOrder name %s has no piece in Tokens.png" % token)

print("%d problems" % len(problems))
for problem in problems:
    print("  " + problem)
