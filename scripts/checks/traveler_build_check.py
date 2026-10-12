"""Cross-check of docs/traveler-build.md against the real data files.

Usage: python -I traveler_build_check.py <reference dir> Travelers.txt Errors.txt NamesM.txt NamesF.txt Bodies.xml Faces.xml
"""
import sys, re, collections
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import tabtree

READ_BY_TRAVELER = ["nation", "purpose", "job", "district", "duration", "issuingCity",
                    "contrabandTypes", "special", "forceDeny", "slow", "canDetain", "leaveDir",
                    "want", "face", "gender", "genderForced", "name", "idNumber"]

trav = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
values = collections.defaultdict(collections.Counter)
for _, node in tabtree.walk(trav):
    p = node.params or []
    if len(p) >= 2 and p[0] == "=":
        values[p[1]][" ".join(p[2:])] += 1

print("-- '=' variables the Traveler constructor reads, with their values in Travelers.txt --")
for name in READ_BY_TRAVELER:
    vals = values.get(name, collections.Counter())
    shown = dict(list(vals.most_common())[:6])
    print(f"  {name:16} uses={sum(vals.values()):3}  distinct={len(vals):3}  e.g. {shown}")

print("\n-- shapes --")
faces = [v for v in values.get("face", {})]
print("face values:", len(faces), "| part counts:", dict(collections.Counter(len(v.split('-')) for v in faces)),
      "| with '*':", sum('*' in v for v in faces))
names = [v for v in values.get("name", {})]
print("name values:", len(names), "| part counts after split('-'):", dict(collections.Counter(len(v.split('-')) for v in names)),
      "| empty first part:", sum(v.split('-')[0] == '' for v in names))
ids = [v for v in values.get("idNumber", {})]
print("idNumber values:", ids)
idre = re.compile(r"^[0-9A-HJ-NP-X]{5}-[0-9A-HJ-NP-X]{5}$")
print("  match the random format (5 chars, '-', 5 chars, no I/O/Y/Z):", sum(bool(idre.match(v)) for v in ids), "of", len(ids))
for flag in ("forceDeny", "slow", "canDetain", "genderForced"):
    print(f"{flag} values:", dict(values.get(flag, {})))

print("\n-- Errors.txt ids the constructor looks for --")
err = tabtree.parse(open(sys.argv[3], encoding="utf-8", newline="").read())
tabtree.expand_params(err)
eids = [n.params[0] for n in err.nodes if n.params and not n.params[0].startswith("*")]
for pat in ("Traveler-ConfusingGender", "Traveler-Criminal", "Bulletin-Criminal"):
    print(f"  containing {pat!r}:", [e for e in eids if pat in e])

print("\n-- name lists --")
for path in (sys.argv[4], sys.argv[5]):
    raw = open(path, encoding="utf-8", newline="").read()
    lines = raw.split("\n")
    bad = [l for l in lines if len(l.split(" ")) != 2]
    print(f"  {path.split(chr(92))[-1]}: entries after split on newline = {len(lines)}, "
          f"not exactly two words = {len(bad)} -> {bad[:5]}")

print("\n-- Bodies.xml contraband types --")
bodies = ET.parse(sys.argv[6]).getroot()
types = [c.get("type") for c in bodies.iter("contra")]
print("  <contra> elements:", len(types), "| by type:", dict(collections.Counter(types)))
print("  pick list for a random non-bomb type has", sum(t != "bomb" for t in types), "entries (duplicates kept)")

print("\n-- Faces.xml --")
faces_root = ET.parse(sys.argv[7]).getroot()
sheets = faces_root.findall("sheet")
print("  sheets:", [s.get("id") for s in sheets], "| faces per sheet:", sorted({len(s.findall('face')) for s in sheets}))
cc = collections.Counter()
for s in sheets:
    for f in s.findall("face"):
        words = set((f.get("canbeconfusing") or "").split())
        cc[("M" if s.get("id").startswith("M") else "F", words >= {"head", "eyes", "mouth"})] += 1
print("  faces whose canbeconfusing has head+eyes+mouth, by gender:", dict(cc))
