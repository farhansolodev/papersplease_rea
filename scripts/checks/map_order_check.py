"""Applies the reference StringMap/IntMap (scripts/reference/haxemap.py) to the
places where the game's hash order decides random draws. Backs docs/haxe-maps.md.

Usage: python -I map_order_check.py <reference dir> Facts.xml Text.xml NamesM.txt NamesF.txt
"""
import sys, re
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
from haxemap import StringMap, IntMap

AMP = r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)"
facts = ET.fromstring(re.sub(AMP, "&amp;", open(sys.argv[2], encoding="utf-8").read()))
nations = [n.get("name") for n in facts.find("nations").findall("nation")]

# 1. Order in which a document's empty facts are generated when it is put on
#    the desk: a fresh StringMap filled with the document's fact paths in file
#    order (after [NATIONS] expansion), then walked.
DRAWS = {"AccessNations", "Description", "VaccineDates", "VaccineDrugs"}
differs = 0
print("-- generation order of empty facts, documents where it differs from file order --")
for doc in facts.findall("paper"):
    did = doc.get("id")
    paths, empty = [], set()
    for f in doc.findall("fact"):
        fid = f.get("id") or ""
        ids = [fid.replace("[NATIONS]", n) for n in nations] if "[NATIONS]" in fid else [fid]
        for one in ids:
            path = did + ("/" + one if one else "")
            paths.append(path)
            if not f.get("val"):
                empty.add(path)
    table = StringMap()
    for p in paths:
        table.set(p, p)
    walked = [p for p in table.keys() if p in empty]
    written = [p for p in dict.fromkeys(paths) if p in empty]
    if walked != written:
        differs += 1
        if any(p.split("/")[-1] in DRAWS for p in walked) or did == "VaccineCert":
            print(f"  {did}: walked {walked}")
print(f"  documents whose generation order differs from file order: {differs}")

# 2. The alias swap sets for the English text, in the order the game keeps them.
text = ET.parse(sys.argv[3]).getroot()
typochars = next(i.find("t").text for i in text.iter("item") if i.get("id") == "env_typochars")
joined = typochars + "," + "aeiou,iuy,pgq,lj,ck,bh"
def split_trim(s):
    return [p.strip() for p in s.split(",") if p.strip()]
sets = split_trim(joined) + split_trim(joined.upper())  # UpperCase.txt matches .upper() for ASCII
table = StringMap()
for s in sets:
    key = "".join(sorted(s))
    table.set(key, key)
swap_sets = list(table.values())
print("\n-- alias swap sets (English), in the game's order --")
print(" ", swap_sets)

# 3. Alias positions: an IntMap filled with the positions that have a swap set,
#    in increasing order, then walked.
def positions_order(name):
    m = IntMap()
    for i, ch in enumerate(name):
        if any(ch in s for s in swap_sets):
            m.set(i, True)
    return list(m.keys())
total = not_ascending = 0
example = None
for path in sys.argv[4:6]:
    for line in open(path, encoding="utf-8", newline="").read().split("\n"):
        for word in line.split(" "):
            if not word:
                continue
            total += 1
            order = positions_order(word)
            if order != sorted(order):
                not_ascending += 1
                example = example or (word, order)
print("\n-- alias positions --")
print(f"  name parts checked: {total}; walked in an order other than left to right: {not_ascending}")
print(f"  example: {example}")

# 4. Self-test of the reference tables: random sets and removes must keep the
#    same contents as a Python dict (this checks consistency, not the order).
import random
rng = random.Random(1)
ok = True
for trial in range(200):
    sm, im, ds, di = StringMap(), IntMap(), {}, {}
    for step in range(rng.randrange(1, 300)):
        k = rng.randrange(0, 60)
        if rng.random() < 0.7:
            sm.set(f"k{k}", step); ds[f"k{k}"] = step
            im.set(k * 7 - 100, step); di[k * 7 - 100] = step
        else:
            assert sm.remove(f"k{k}") == (f"k{k}" in ds); ds.pop(f"k{k}", None)
            assert im.remove(k * 7 - 100) == (k * 7 - 100 in di); di.pop(k * 7 - 100, None)
    ok &= sorted(sm.keys()) == sorted(ds) and all(sm.get(k) == v for k, v in ds.items())
    ok &= sorted(im.keys()) == sorted(di) and all(im.get(k) == v for k, v in di.items())
    ok &= sm.size == len(ds) and im.size == len(di)
print("\n-- self-test (200 random runs of sets and removes) --")
print("  contents always match a Python dict:", ok)
