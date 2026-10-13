"""Cross-checks Languages.txt and Languages.png with each other and with the
language packs.

Usage: python -I languages_check.py <assets dir> [loc dir]      (needs Pillow)
<loc dir> is game\\PapersPlease_Data\\StreamingAssets\\loc in this project.
"""
import os
import sys

from PIL import Image

assets = sys.argv[1]
raw = open(os.path.join(assets, "data", "Languages.txt"), "rb").read()
codes = raw.decode("utf-8").split("\n")
problems = []
print("Languages.txt: %d bytes, carriage returns: %d, ends with a line break: %s" % (
    len(raw), raw.count(b"\r"), raw.endswith(b"\n")))
print("codes (%d): %s" % (len(codes), codes))
if any(c != c.strip() or not c for c in codes):
    problems.append("an empty or padded code (the game does not trim them)")
if len(set(codes)) != len(codes):
    problems.append("repeated code")

picture = Image.open(os.path.join(assets, "data", "Languages.png")).convert("RGBA")
width, height = picture.size
rows, left = divmod(height, len(codes))
print("Languages.png: %dx%d -> %d rows of %d pixels, %d pixels left over" % (width, height, len(codes), rows, left))
if left:
    problems.append("picture height is not a whole number of rows")
empty = []
for index, code in enumerate(codes):
    strip = picture.crop((0, index * rows, width, (index + 1) * rows))
    colours = strip.getcolors(maxcolors=100000)
    if len(colours) < 2:
        empty.append(code)
print("rows that are one flat colour (no name drawn):", empty or "none")
if empty:
    problems.append("empty row")

if len(sys.argv) > 2:
    packs = sorted(f[:-4] for f in os.listdir(sys.argv[2]) if f.endswith(".zip"))
    print("language packs: %d; codes without a pack: %s; packs without a code: %s" % (
        len(packs), sorted(set(codes) - set(packs)) or "none", sorted(set(packs) - set(codes)) or "none"))
    print("same order as sorted pack names:", codes == packs)
print("problems:", problems or "none")
