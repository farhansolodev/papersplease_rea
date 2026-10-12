"""Checks of scripts/reference/person.py against docs/traveler-build.md and the data.

Usage: python -I person_check.py <reference dir> <assets dir> Travelers.txt

<assets dir> is extracted/art/assets. Needs the Pillow library.
"""
import collections
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import faces as F
import person as P
from cyclers import FaceCycler, NameCycler

assets = sys.argv[2]
data = os.path.join(assets, "data")
faces_dir = os.path.join(assets, "faces")
lib = F.FaceLib(os.path.join(data, "Faces.xml"), os.path.join(assets, "FacePalette.png"))
contra = P.load_contra_types(os.path.join(data, "Bodies.xml"))
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
names_m, names_f = read("NamesM.txt"), read("NamesF.txt")


def build(variables, seed=77, error_id=None, master=5):
    rand = P.CountingRand(seed)
    face_cycler, name_cycler = FaceCycler(master), NameCycler(names_m, names_f, master)
    person = P.build_person(variables, rand, face_cycler, name_cycler, lib, faces_dir, contra, error_id)
    return person, rand.count, face_cycler, name_cycler


def redraws(person_seed):
    """Fingerprint redraws for a seed: found by counting against the fixed part."""
    _, count, _, _ = build({"gender": "M"}, person_seed)
    return count - 18


print("-- number of draws from the booth's generator --")
seed = next(s for s in range(1, 200) if redraws(s) == 0)        # a seed with no fingerprint redraw
base = build({"gender": "M"}, seed)[1]
cases = [
    ("nothing scripted", {"gender": "M"}, None, 18),
    ("contrabandTypes given", {"gender": "M", "contrabandTypes": "gun"}, None, 17),
    ("idNumber given", {"gender": "M", "idNumber": "AAAAA-BBBBB"}, None, 8),
    ("face with all 7 parts", {"gender": "M", "face": "M-1-2-3-4-0-0"}, None, 18),
    ("face with 6 parts", {"gender": "M", "face": "M-1-2-3-4-0"}, None, 19),
    ("face with 5 parts", {"gender": "M", "face": "M-1-2-3-4"}, None, 20),
    ("confusing-gender error", {"gender": "M"}, "Traveler-ConfusingGender<generic>", 19),
    ("criminal error, no criminal found", {"gender": "M"}, "Traveler-Criminal<generic>", 18),
]
problems = []
for label, variables, error, expected in cases:
    # A different number of draws before the fingerprints changes them, so
    # allow for redraws: the count can only be the expected one or more.
    got = build(variables, seed, error)[1]
    flag = "" if got >= expected and (got == expected or label != "nothing scripted") else "  <-- CHECK"
    print("  %-34s expected %2d (plus any fingerprint redraws), got %2d%s" % (label, expected, got, flag))
    if flag:
        problems.append(label)

print("\n-- fingerprints over 2000 seeds --")
bad = 0
extra = collections.Counter()
for s in range(2000):
    prints = P.make_fingerprints(P.CountingRand(s))
    bad += prints[1] == prints[2] or prints[3] == prints[4]
    rand = P.CountingRand(s)
    P.make_fingerprints(rand)
    extra[rand.count - 5] += 1
print("  with finger 2 = finger 3 or finger 4 = finger 5:", bad, "| redraws needed:", dict(sorted(extra.items())))

print("\n-- names --")
plain, _, _, cycler_a = build({"gender": "M"}, seed)
scripted, _, _, cycler_b = build({"gender": "M", "name": "Jorji-Costava"}, seed)
half, _, _, _ = build({"gender": "M", "name": "-Costava"}, seed)
print("  cycler name:", plain.first, plain.last, "| scripted:", scripted.first, scripted.last,
      "| last name only:", half.first, half.last)
print("  the name cycler advanced the same with a scripted name:",
      cycler_a.get(True) == cycler_b.get(True))

print("\n-- confusing gender --")
person, _, face_cycler, _ = build({"gender": "M"}, seed, "Traveler-ConfusingGender<generic>")
print("  traveler male:", person.male, "| face:", P.spec_text(person.face_spec),
      "| face passes for the other gender:", person.meta.ok_for_confusing_gender,
      "| female faces taken from the cycler:", face_cycler.pieces_f[0].cur)
tries = collections.Counter()
for master in range(40):
    for male in (True, False):
        rand = P.CountingRand(seed)
        fc, nc = FaceCycler(master), NameCycler(names_m, names_f, master)
        P.build_person({"gender": "M" if male else "F"}, rand, fc, nc, lib, faces_dir, contra,
                       "Traveler-ConfusingGender<generic>")
        used = (fc.pieces_f if male else fc.pieces_m)[0].cur
        tries[("man with a woman's face" if male else "woman with a man's face", used)] += 1
print("  faces tried before one fits, over 40 master seeds:", dict(sorted(tries.items())))

print("\n-- weight factor --")
print("  men:   base 60 ->", P.lerp_scale(60.0, 60.0, 100.0, 1.3, 1.0), "| base 80 ->",
      round(P.lerp_scale(80.0, 60.0, 100.0, 1.3, 1.0), 6), "| base 100 ->", P.lerp_scale(100.0, 60.0, 100.0, 1.3, 1.0))
print("  women: base 40 ->", P.lerp_scale(40.0, 40.0, 100.0, 1.0, 0.8), "| base 100 ->",
      P.lerp_scale(100.0, 40.0, 100.0, 1.0, 0.8))

print("\n-- every scripted face in Travelers.txt can be built --")
values = sorted(set(re.findall(r"\b[Ff]ace\s+([MF]-[0-9*-]+)", open(sys.argv[3], encoding="utf-8").read())))
heights = []
failed = []
for value in values:
    try:
        spec = P.face_spec_from_string(P.CountingRand(1), value)
        face = F.Face(faces_dir, lib, F.FaceSpec(P.spec_text(spec)))
        heights.append((round(face.height_in_meters, 3), value))
    except Exception as error:                          # noqa: BLE001
        failed.append((value, repr(error)))
print("  scripted face values:", len(values), "| failed:", failed)
print("  by number of parts:", dict(collections.Counter(len(v.split("-")) for v in values)))
heights.sort()
print("  face heights: shortest", heights[:3], "| tallest", heights[-3:])
print("\nproblems:", problems or "none")
