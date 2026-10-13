"""Cross-checks BorderAnim.xml (a picture atlas) with its sheet and with the
animations of Paths.xml.

Usage: python -I borderanim_check.py <assets dir>      (needs Pillow)
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image

assets = sys.argv[1]
root = ET.parse(os.path.join(assets, "data", "BorderAnim.xml")).getroot()
problems = []
print("root <%s> %s; children: %s" % (root.tag, dict(root.attrib), dict(collections.Counter(n.tag for n in root))))
print("attributes:", dict(collections.Counter(a for n in root for a in n.attrib)))

sheet = Image.open(os.path.join(assets, "BorderAnim.png"))
print("sheet BorderAnim.png: %dx%d" % sheet.size)
entries = [(n.get("name"), int(n.get("x")), int(n.get("y")), int(n.get("width")), int(n.get("height"))) for n in root]
names = [e[0] for e in entries]
repeats = [n for n, c in collections.Counter(names).items() if c > 1]
outside = [e[0] for e in entries if e[1] < 0 or e[2] < 0 or e[1] + e[3] > sheet.size[0] or e[2] + e[4] > sheet.size[1]]
overlap = 0
for i, a in enumerate(entries):
    for b in entries[i + 1:]:
        if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
            overlap += 1
print("pictures: %d, repeated names: %s, outside the sheet: %s, overlapping pairs: %d" % (
    len(entries), repeats or "none", outside or "none", overlap))
if repeats or outside or overlap:
    problems.append("atlas layout")
print("names in sorted order already:", names == sorted(names))

# Sequences: the game collects every name that STARTS WITH a prefix, in file order.
stems = collections.OrderedDict()
for name, x, y, w, h in entries:
    match = re.match(r"^(.*)[- ](\d+)$", name)          # "Boom-03" and "Enemy-WalkH 2"
    stem = match.group(1) if match else name
    stems.setdefault(stem, []).append((name, w, h))
numbered = {s: f for s, f in stems.items() if len(f) > 1 or re.search(r"[- ]\d+$", f[0][0])}
print("picture groups (name without its frame number): %d; with numbered frames: %d; single pictures: %d" % (
    len(stems), len(numbered), len(stems) - len(numbered)))
styles = collections.Counter("dash, from 00" if "-%02d" % 0 in f[0][0][-3:] else "space, from 1" for f in numbered.values())
print("numbering styles:", dict(styles))
bad_numbers = []
for stem, frames in numbered.items():
    numbers = [int(re.search(r"[- ](\d+)$", n).group(1)) for n, _, _ in frames]
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))) or numbers[0] not in (0, 1):
        bad_numbers.append(stem)
print("groups whose frame numbers do not run upward in file order:", bad_numbers or "none")
print("frames per group:", dict(sorted(collections.Counter(len(f) for f in numbered.values()).items())))
mixed = [s for s, f in stems.items() if len({(w, h) for _, w, h in f}) > 1]
print("groups whose frames differ in size:", mixed or "none")
shadow = sorted((a, b) for a in stems for b in stems if a != b and b.startswith(a))
print("groups whose name is the start of another group's name (a prefix search would mix them): %d" % len(shadow))
for a, b in shadow[:12]:
    print("   %s / %s" % (a, b))

# The animations of Paths.xml name suffixes; the figure's own name comes first.
paths = ET.parse(os.path.join(assets, "data", "Paths.xml")).getroot()
suffixes = collections.OrderedDict()
for anim in paths.findall("anim"):
    for key in ("suffix", "suffixv"):
        if anim.get(key):
            suffixes.setdefault(anim.get(key), anim.get("id"))
figures = collections.OrderedDict()
unmatched = set(stems)
for suffix in suffixes:
    for stem in stems:
        if stem.endswith(suffix):
            figures.setdefault(stem[:-len(suffix)], []).append(suffix)
            unmatched.discard(stem)
print("animation suffixes in Paths.xml: %d; with no picture group ending in them: %s" % (
    len(suffixes), [s for s in suffixes if not any(st.endswith(s) for st in stems)] or "none"))
print("figure names found this way: %s" % ", ".join("%s(%d)" % (f, len(s)) for f, s in figures.items()))
print("picture groups not explained by any animation suffix: %s" % (sorted(unmatched) or "none"))
print("problems:", problems or "none")
