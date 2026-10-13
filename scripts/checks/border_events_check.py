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

# 7b. Leave directions set by traveler scripts: one the code names, or else a path id.
DIRECTIONS = ["left", "right", "right-bomb", "right-poisoned", "left-poisoned", "left-killer", "left-timebomber",
              "right-boss", "right-guard", "left-guard", "right-elisa"]
travelers = open(os.path.join(data, "Travelers.txt"), encoding="utf-8").read()
for value in sorted(set(re.findall(r"=\s*leaveDir\s+(\S+)", travelers))):
    kind = "named by the code" if value in DIRECTIONS else ("used as a path id; that path exists: %s" % lib.has_path(value))
    print("leaveDir %-16s %s" % (value, kind))
    if value not in DIRECTIONS and not lib.has_path(value):
        problems.append("leaveDir %s is neither a known direction nor a path" % value)

# 8. Shooting (docs/border-shooting.md).
anim_nodes = {a.get("id"): a for a in root.findall("anim")}
for path_id in ("shot", "tranq", "bike-explode", "enemy-grenaded"):
    if not lib.has_path(path_id):
        problems.append("missing path " + path_id)
        continue
    node = lib.path_nodes[path_id]
    anim = anim_nodes[node.get("anim", "walk")]
    print("path %-15s animation %-12s death: %-5s points: %d  next: %s  start: %s" % (
        path_id, anim.get("id"), anim.get("death", "false"), len(node.findall("p")), node.get("next"), node.get("start")))
    if anim.get("death") != "true":
        problems.append("%s does not use a death animation, so the figure would not count as dead" % path_id)
shoot_sounds = ["border-tranqshot", "border-gunshot", "rifle-unlock", "rifle-keyinsert", "rifle-cock",
                "button-drop", "booth-intro", "grenade-roll", "booth-boom", "border-boom"]
print("shooting sounds not in Sounds.xml:", sorted(set(shoot_sounds) - sounds) or "none")
problems += ["sound %s missing" % s for s in sorted(set(shoot_sounds) - sounds)]
papers = open(os.path.join(data, "Papers.xml"), encoding="utf-8").read()
for key in ("KeyTranq", "KeyKill"):
    if not re.search(r'<paper id="%s"' % key, papers):
        problems.append("paper %s not in Papers.xml" % key)
ends = open(os.path.join(data, "Ends.xml"), encoding="utf-8").read()
end_ids = ["killed-innocent", "tranqed-innocent", "killed-guard", "tranqed-guard", "killed-target", "tranqed-target"]
print("endings named by the border scene that are not in Ends.xml:",
      [e for e in end_ids if not re.search(r'["\']%s["\']' % e, ends)] or "none")
problems += ["ending %s missing" % e for e in end_ids if not re.search(r'["\']%s["\']' % e, ends)]
no_sniping = [day for day in attacks if "SNIPING" not in table.accumulated(day, "FEATURES")]
print("attack days where the player cannot shoot (no SNIPING feature):", no_sniping or "none")
print("days where the tranquilliser key is handed out by the PAPERS row:",
      [day for day in range(1, 32) if "KeyTranq" in table.cell(day, "PAPERS")])
try:
    from PIL import Image
    holes = Image.open(os.path.join(os.path.dirname(data), "BulletHoles.png"))
    print("BulletHoles.png: %d x %d (the code cuts 4 pieces of 8 x 8 from its top row)" % holes.size)
    if holes.size[0] < 32 or holes.size[1] < 8:
        problems.append("BulletHoles.png is smaller than 32 x 8")
except Exception as error:                                  # noqa: BLE001
    print("BulletHoles.png not checked:", error)

# 9. The view, the cameras and the endless scoreboard (docs/border-view.md).
def lerp_scale(value, in_min, in_max, out_min, out_max):    # app.Num.lerpScale
    value = max(min(value, in_max), in_min)
    return (value - in_min) / (in_max - in_min) * (out_max - out_min) + out_min

# Desktop layout values, read from the Layout constructor's instructions.
BORDER_W, BORDER_H, PIXEL_W, SCOREBOARD_W = 570, 103, 570, 180
pan_max = max(0, BORDER_W - PIXEL_W)
print("desktop: scene %d x %d, window %d wide, so the view can move by %d" % (BORDER_W, BORDER_H, PIXEL_W, pan_max))
print("bounce off an edge at speed 0 / 200 / 400+: %s pixels over %s seconds" % (
    [lerp_scale(v, 0, 400, 4, 10) for v in (0, 200, 400)], [round(lerp_scale(v, 0, 400, 0.2, 0.4), 2) for v in (0, 200, 400)]))
print("runner scene, view offset at runner x = 185 / 250 / 320:",
      [round(lerp_scale(x, 185, 320, 0, 50), 1) for x in (185, 250, 320)])
shown, countdown = [], 2.0                                  # FlashingScore: 7 flashes in 2 seconds
while countdown > 0:
    countdown -= 1 / 60
    if countdown > 0:
        which = 1 if (countdown / 2.0 * 7 * 0.5) % 1.0 >= 0.5 else 0
        if not shown or shown[-1] != which:
            shown.append(which)
print("a flash shows text", " ".join(str(w) for w in shown), "then the real value (%d stretches)" % len(shown))
if len(shown) != 7 or shown[0] != 0 or shown[-1] != 0:
    problems.append("the flash model does not give 7 stretches starting and ending on the flash text")
assets = os.path.dirname(data)
view_sounds = ["border-pan", "border-foghorn"]
problems += ["sound %s missing" % s for s in view_sounds if s not in sounds]
fonts = open(os.path.join(data, "Fonts.xml"), encoding="utf-8").read()
if not re.search(r'<font id="fixed"', fonts):
    problems.append("font 'fixed' (the scoreboard's) is not in Fonts.xml")
endlesses = open(os.path.join(data, "Endlesses.xml"), encoding="utf-8").read()
pictures = ["EndlessScore.png", "BorderCamNoise.png", "BorderCamPalette.png"] + sorted(set(re.findall(r'icon="([^"]+)"', endlesses)))
missing = [name for name in pictures if not os.path.exists(os.path.join(assets, name))]
print("pictures named by the scoreboard and cameras that are missing:", missing or "none")
problems += ["picture %s missing" % name for name in missing]
try:
    from PIL import Image
    sizes = {name: Image.open(os.path.join(assets, name)).size for name in pictures if name not in missing}
    print("picture sizes:", sizes)
    if sizes.get("EndlessScore.png", (SCOREBOARD_W, 0))[0] != SCOREBOARD_W:
        problems.append("EndlessScore.png is not %d wide (Layout.kEndlessScoreboardWidth)" % SCOREBOARD_W)
    if sizes.get("BorderCamPalette.png", (31, 1))[0] < 31:
        problems.append("BorderCamPalette.png is narrower than 31 (the code reads pixels 0, 10, 20 and 30)")
    palette = Image.open(os.path.join(assets, "BorderCamPalette.png")).convert("RGBA")
    print("camera colours (pixels 0, 10, 20, 30 of the top row):", [palette.getpixel((x, 0))[:3] for x in (0, 10, 20, 30)])
except Exception as error:                                  # noqa: BLE001
    print("picture sizes not checked:", error)

print("problems:", problems or "none")
