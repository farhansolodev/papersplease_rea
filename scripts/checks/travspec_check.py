"""Checks of scripts/reference/travspec.py against the data files.

Usage: python -I travspec_check.py <reference dir> <data dir> stringliteral.json

Builds the first travelers of every story day for several master seeds and
reports anything the game's code would reject, plus a few counts.
"""
import collections
import json
import sys

sys.path.insert(0, sys.argv[1])
import travspec as T
from cyclers import FaceCycler
from seeds import Launch

C = collections.Counter
table, world, root = T.load(sys.argv[2])
code_strings = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}

days = [int(c) for c in table.col_ids[1:] if c.isdigit() and int(c) <= 31]
MASTERS = range(1, 13)

failures = []
none_values = C()
draws = collections.defaultdict(list)
genders = C()
fallbacks = C()
breaks = 0
made = 0
criminal_draws = C()
for master in MASTERS:
    launch = Launch(master)
    for day_number in days:
        face_cycler = FaceCycler(launch.face_cycler_seed)
        try:
            day = T.Day(table, day_number, launch.story_seed, face_cycler)
        except Exception as error:                      # noqa: BLE001
            failures.append(("day %d set-up" % day_number, repr(error)))
            continue
        rand = T.CountingRand(0)
        rand.__dict__.update(day.traveler_rand.__dict__)
        rand.count = 0
        context = T.TravelerContext(root, world, day.facts)
        for _ in range(len(day.traveler_ids) + 4):
            entry = day.next_traveler_id()
            before = rand.count
            try:
                spec = context.make_spec(entry, rand)
            except Exception as error:                  # noqa: BLE001
                failures.append((entry, repr(error)))
                continue
            made += 1
            if spec.id != entry:
                fallbacks[(entry, spec.id)] += 1
            draws[entry].append(rand.count - before)
            for key in ("nation", "purpose", "job", "district", "duration", "issuingCity", "gender"):
                if spec.vars.get(key) is None:
                    none_values[(entry, key)] += 1
            if "genderForced" not in spec.vars:
                genders[spec.vars["gender"]] += 1

print("-- building the first travelers of every day --")
print("  days:", len(days), "| master seeds:", len(MASTERS), "| specifications made:", made)
print("  failures:", failures[:8], "(%d in all)" % len(failures))
print("  entries that fell back to another:", dict(fallbacks))
print("  a detail left empty after filling in:", dict(none_values))
print("  gender when the script does not set it:", dict(genders))
spread = {entry: (min(v), max(v)) for entry, v in draws.items()}
print("  draws per specification: fewest", min(a for a, _ in spread.values()),
      "| most", max(b for _, b in spread.values()))
varying = sorted(entry for entry, (a, b) in spread.items() if a != b)
print("  entries whose number of draws varies:", len(varying), "of", len(spread), "|", varying[:10])

print("\n-- day set-up --")
with_face = [d for d in days if table.cell(d, "CRIMFACE")]
print("  days with a scripted criminal face (CRIMFACE):", {d: table.cell(d, "CRIMFACE") for d in with_face})
print("  every day makes 3 criminal faces; from the cycler:",
      dict(C(3 - (1 if d in with_face else 0) for d in days)))
ids = [i for d in days for i in T.split_and_trim(table.cell(d, "TRAVELERS"), "\n")] + \
      [table.cell(d, "FILL") for d in days]
print("  traveler ids named by Days.csv with no entry in Travelers.txt:",
      sorted({i for i in ids if i and root.find(i) is None}))
print("  days with no FILL:", [d for d in days if not table.cell(d, "FILL")])

print("\n-- conditions --")
lefts = C()
for entry in root.nodes:
    if entry.params[0] == "DEFAULT":
        continue
    stack = [entry]
    while stack:
        node = stack.pop()
        for child in node.nodes:
            if child.params[0] == "?":
                for i in range(1, len(child.params), 4):
                    lefts[child.params[i]] += 1
                stack.append(child)
facts = sorted(l for l in lefts if "/" in l)
print("  story and day facts read by script conditions:", len(facts))
print("  of those, not found as a whole string in the game's code:",
      [f for f in facts if f not in code_strings])
print("  'Game/Rules' appears in the code's strings:", "Game/Rules" in code_strings,
      "| 'Day/Rules':", "Day/Rules" in code_strings)

print("\n-- world --")
print("  nations:", len(world.nations), "| purposes:", [(p["id"], p["chance"], p["rule"]) for p in world.purposes])
print("  jobs:", len(world.jobs), "| districts:", len(world.districts), "| durations:", len(world.durations),
      "| autopapers:", len(world.autopapers))
