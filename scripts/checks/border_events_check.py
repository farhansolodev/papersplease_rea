"""Checks Paths.xml, Days.csv, Text.xml and Sounds.xml against what
play.day.border.Border does with them. See docs/border-scene.md.

Usage: python -I border_events_check.py <reference dir> <data dir>
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import paths as P
import travspec

data = sys.argv[2]
text = open(os.path.join(data, "Paths.xml"), encoding="utf-8").read()
root = ET.fromstring(text)
lib = P.PathLib(text)
problems = []

# What Border.person_onEvent reacts to (read from the code).
EXACT = ["detain-say-out", "end-chat", "watch-poisoning", "start-intro", "throw-grenade",
         "throw-grenade-underhand", "detain-guards-waiting-outside", "detain-entrant-waiting-outside",
         "bomber-alarm", "bomber-explode", "start-chat", "truck-planted-wall", "truck-blow-wall",
         "poisoned-right-send-guard", "poisoned-left-panic", "finish-poisoning", "finish-boss",
         "park-bike", "call-elisa", "pan-right", "trucke0-die", "trucke1-decide"]
PREFIXES = ["spawn-explosion", "tell"]
LINE_EVENTS = ["arrived-in-booth"]                    # handled by WaitingLine, not Border

# Figures Border creates with addPerson, by id.
PEOPLE = ["guard0", "guard1", "guard2", "guard3", "guard4", "runner", "truck", "leaving", "traffic",
          "bosscar", "enemy0", "enemy1", "bike0", "bike1"]

# Every path name Border asks for (read from the code), by who gets it.
CODE_PATHS = {
    "guard0": ["guard0-enter", "guard0-detainstart", "guard0-resiststart", "guard0-detainfinish", "guard0-panic"],
    "guard1": ["guard1-enter", "guard1-waitforchat", "guard1-detainstart", "guard1-resiststart",
               "guard1-detainfinish", "guard1-panic", "guard1-exitchat", "guard1-enterchat-timebomb",
               "guard1-enterchat-midday"],
    "guard2": ["guard2-enter", "guard2-runner", "truckg2-start", "g2ba-start", "g2br-start", "guard2-grenaded",
               "guard-afterattack-stand", "guard-afterattack-kneel"],
    "guard3": ["guard3-enter", "guard3-runner", "guard3-runnerkill", "truckg3-start", "g3ba-start", "g3br-start",
               "guard3-grenaded", "guard-right-poisoned", "guard-afterattack-stand", "guard-afterattack-kneel"],
    "guard4": ["guard4-enter", "guard4-enterchat", "guard4-exitchat", "guard4-elisa-reunite", "guard4-runner",
               "truckg4-start", "g4ba-start", "g4ba-startkill", "g4br-start", "guard4-grenaded",
               "guard-afterattack-stand", "guard-afterattack-kneel"],
    "runner": ["runforit", "runner-bikerunner-start"],
    "truck": ["truck-enter"],
    "leaving": ["leaving-free", "enter-right", "entrant-detainstart", "entrant-detainfinish", "exit-right-bomb",
                "boss-exit", "boss-enter", "exit-right-poisoned", "exit-left-poisoned", "exit-left-timebomber",
                "exit-left-killer", "exit-right-elisa", "exit-right", "exit-left", "exit-right-panic", "panic-2"],
    "traffic": ["traffic0-wait", "traffic1-wait", "traffic2-wait", "traffic3-wait", "traffic0", "traffic-stop"],
    "bosscar": ["bosscar-enter", "bosscar-exit"],
    "enemy": ["enemy-free", "trucke0-start", "trucke1-start", "enemy-bikeattack-start", "enemy0-bikerunner-start",
              "enemy1-bikerunner-start", "enemy-throw-grenade-underhand", "enemy-grenaded", "bike-parked"],
}

all_paths = lib._order
names = {}
last, since = "the start of the file", 0
for node, original in zip(all_paths, root.findall("path")):
    if original.get("id") is None:
        since += 1
        names[node.get("id")] = "(unnamed, %d after %s)" % (since, last)
    else:
        last, since = original.get("id"), 0
        names[node.get("id")] = original.get("id")

# 1. Every path the code names exists.
missing = sorted({p for group in CODE_PATHS.values() for p in group if not lib.has_path(p)})
print("path names in the Border code: %d, missing from Paths.xml: %s" % (
    len({p for group in CODE_PATHS.values() for p in group}), missing or "none"))
problems += ["missing path " + p for p in missing]

# 2. Every event in the data is one the code reacts to.
events = collections.Counter()
for node in all_paths:
    for kind in ("start", "end", "die"):
        if node.get(kind):
            events[node.get(kind)] += 1
handled, ignored = [], []
for event in sorted(events):
    if event in EXACT or event in LINE_EVENTS or any(event.startswith(p) for p in PREFIXES):
        handled.append(event)
    else:
        ignored.append(event)
print("different event texts in the data: %d; nothing reacts to: %s" % (len(events), ignored or "none"))
print("events the code reacts to that the data never sends:",
      sorted(e for e in EXACT + LINE_EVENTS if e not in events) or "none")
empty = [names[n.get("id")] for n in all_paths for k in ("start", "end", "die") if n.get(k) == ""]
print("paths with an empty event text:", empty or "none")

# 3. "tell <who> <path>" and "spawn-explosion <x> <y>".
for event in sorted(events):
    if event.startswith("tell"):
        parts = [p for p in (x.strip() for x in event.split(" "))]
        who, path = (parts + [None, None])[1:3]
        ok = who in PEOPLE and path is not None and lib.has_path(path)
        print("  %-34s who is a figure id: %s; path exists: %s" % (event, who in PEOPLE, path is not None and lib.has_path(path)))
        if not ok:
            problems.append("bad tell event: " + event)
    elif event.startswith("spawn-explosion"):
        rest = event[len("spawn-explosion "):]
        if not re.fullmatch(r"-?\d+(\.\d+)? -?\d+(\.\d+)?", rest):
            problems.append("spawn-explosion offset not two numbers: " + event)
        print("  %-34s offset: %s" % (event, rest))

# 4. Guards 0 and 1 swap "guardN" for "jailorN" on days with jailors: which paths have a twin.
def reachable(start_ids):
    seen, todo = [], list(start_ids)
    while todo:
        path_id = todo.pop(0)
        if path_id in seen or not lib.has_path(path_id):
            continue
        seen.append(path_id)
        nxt = lib.create_path(P.Rand(1) if hasattr(P, "Rand") else __import__("rand").Rand(1), path_id).next
        if nxt is not None:
            todo.append(nxt)
    return seen


for guard, prefix in (("guard0", "jailor0"), ("guard1", "jailor1")):
    twins, none = [], []
    for path_id in reachable(CODE_PATHS[guard]):
        if "-" not in names[path_id] and names[path_id].startswith("("):
            continue                                   # unnamed paths are only reached through next
        alternative = prefix + path_id[path_id.index("-"):]
        (twins if lib.has_path(alternative) else none).append(path_id)
    print("%s with jailors: %d reachable named paths have a %s- twin, %d do not: %s" % (
        guard, len(twins), prefix, len(none), none))

# 4b. Where the chains of the reused figures end (a "free" path means the figure can be used again).
def chain_end(path_id):
    seen = []
    while path_id is not None and lib.has_path(path_id) and path_id not in seen:
        seen.append(path_id)
        path_id = lib.create_path(__import__("rand").Rand(1), path_id).next
    return names[seen[-1]], len(seen), path_id is not None and path_id in seen


for group, free in (("leaving", "leaving-free"), ("enemy", "enemy-free")):
    ends = collections.OrderedDict()
    for path_id in CODE_PATHS[group]:
        if path_id != free:
            last_path, length, loops = chain_end(path_id)
            ends.setdefault("loops" if loops else last_path, []).append(path_id)
    print("%s paths, by where their chain of next ends:" % group)
    for end, starts in ends.items():
        print("    %-34s <- %s" % (end, ", ".join(starts)))

# 5. An end event whose handler gives the same figure a new path: endPath then
#    follows that NEW path's next at once.
SAME_FIGURE = {"trucke1-decide": "enemy-throw-grenade-underhand"}
for node in all_paths:
    end = node.get("end")
    target = SAME_FIGURE.get(end)
    if end and end.startswith("tell"):
        parts = end.split(" ")
        target = parts[2] if len(parts) > 2 else None
        target = target if node.get("id", "").startswith(parts[1]) else None
    if target and lib.has_path(target):
        nxt = lib.path_nodes[target].get("next")
        print("end event %r on %s gives the same figure %s, whose next is %r%s" % (
            end, names[node.get("id")], target, nxt,
            "" if nxt is None else "  <-- the new path would be replaced at once"))

# 6. Texts and sounds the Border code names.
texts = open(os.path.join(data, "Text.xml"), encoding="utf-8").read()
for key in ["border_announce0", "border_announce1", "border_announce2", "border_bomber", "border_comeback",
            "border_elisa", "border_guardout", "border_next"]:
    if not re.search(r'["\']%s["\']' % key, texts):
        problems.append("text %s not found in Text.xml" % key)
sounds = set(re.findall(r'<sound[^>]*\bid="([^"]+)"', open(os.path.join(data, "Sounds.xml"), encoding="utf-8").read()))
used = ["speech-out", "speech-bomber", "speech-announce", "border-alarm", "border-boom", "booth-boom",
        "grenade-roll", "border-truckwreck", "border-foghorn", "border-tranqshot", "border-gunshot"]
print("sounds named by Border that are not in Sounds.xml:", sorted(set(used) - sounds) or "none")
problems += ["sound %s missing" % s for s in sorted(set(used) - sounds)]

# 7. Attacks and guards per day.
table = travspec.DaysTable(open(os.path.join(data, "Days.csv"), encoding="utf-8-sig").read())
attacks = collections.OrderedDict()
for day in range(1, 32):
    attack = table.cell(day, "ATTACK")
    if attack:
        attacks[day] = attack
print("days with an attack:", dict(attacks))
print("guard cells per day:", {day: table.cell(day, "GUARDS") for day in range(1, 32) if table.cell(day, "GUARDS")})

print("problems:", problems or "none")
