"""Cross-checks Paths.xml against what data.PathLib, data.Path and data.Anim read.

Usage: python -I paths_check.py <reference dir> <data dir> [stringliteral.json]
"""
import collections
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import paths as P
from rand import Rand

data = sys.argv[2]
text = open(os.path.join(data, "Paths.xml"), encoding="utf-8").read()
root = ET.fromstring(text)
problems = []

READ = {"path": {"id", "next", "speed", "end", "start", "die", "snap", "delay", "hold", "sound", "warp", "face", "anim"},
        "anim": {"id", "suffix", "suffixv", "loop", "fps", "fpsv", "sound", "death", "offset"},
        "p": {"xy", "randomize"}}
top = collections.Counter(node.tag for node in root)
print("root <%s>, children: %s" % (root.tag, dict(top)))
for tag in READ:
    seen = collections.Counter(a for node in root.iter(tag) for a in node.attrib)
    unread = sorted(set(seen) - READ[tag])
    print("  <%s> attributes: %s; not read by the code: %s" % (tag, dict(seen), unread or "none"))
    if unread:
        problems.append("unread attribute on " + tag)
nested = [n for n in root.iter("path") if n not in list(root)]
print("paths nested inside other elements:", len(nested))
print("comments in the file:", len(re.findall(r"<!--", text)))

lib = P.PathLib(text)
named = [n for n in root.findall("path") if n.get("id") is not None]
ids = [n.get("id") for n in named]
repeats = [i for i, c in collections.Counter(ids).items() if c > 1]
print("paths: %d, with their own id: %d, unnamed: %d, repeated ids: %s" % (
    len(root.findall("path")), len(named), len(root.findall("path")) - len(named), repeats or "none"))
print("animations: %d, repeated ids: %s" % (
    len(root.findall("anim")),
    [i for i, c in collections.Counter(n.get("id") for n in root.findall("anim")).items() if c > 1] or "none"))

rand = Rand(1)
nexts = collections.Counter()
bad_next, no_points, events, sounds, faces = [], 0, collections.Counter(), set(), collections.Counter()
draws = 0
for path_id in lib.path_nodes:
    node = lib.path_nodes[path_id]
    try:
        path = lib.create_path(rand, path_id)
    except Exception as error:                       # noqa: BLE001
        problems.append("%s: %s" % (path_id, error))
        continue
    raw_next = node.get("next")
    nexts["NEXT" if raw_next == "NEXT" else ("none" if raw_next is None else "named")] += 1
    if raw_next == "NEXT" and path.next == "NEXT":
        bad_next.append(path_id + " (NEXT with nothing after it)")
    elif path.next is not None and not lib.has_path(path.next):
        bad_next.append("%s -> %s" % (path_id, path.next))
    no_points += not path.points
    draws += 2 * sum(1 for p in node.findall("p") if p.get("randomize") is not None)
    for kind, value in (("start", path.start_event), ("end", path.end_event), ("die", path.die_event)):
        if value:
            events[value] += 1
    if path.sound:
        sounds.add(path.sound)
    if path.face:
        faces[path.face] += 1
    if path.points and path.length > 0:
        end = path.on_path(path.length + 1)
        if end != path.points[-1] or path.on_path(0) != path.points[0]:
            problems.append("on_path ends wrong for " + path_id)
print("next: %s; targets that are not a path id: %s" % (dict(nexts), bad_next or "none"))
print("paths without points: %d; points with a random spread: %d (two draws each)" % (no_points, draws // 2))
print("animation use by paths:", dict(collections.Counter(n.get("anim", "walk (default)") for n in root.findall("path"))))
print("face values:", dict(faces))
print("events (%d different): %s" % (len(events), ", ".join(sorted(events))))
for anim in root.findall("anim"):
    if anim.get("sound"):
        sounds.add(anim.get("sound"))
sound_ids = set(re.findall(r'<sound[^>]*\bid="([^"]+)"', open(os.path.join(data, "Sounds.xml"), encoding="utf-8").read()))
print("sounds named: %s; not in Sounds.xml: %s" % (sorted(sounds), sorted(sounds - sound_ids) or "none"))
if bad_next:
    print("  (see the doc: these are checked against the code's own strings)")
if len(sys.argv) > 3:
    literals = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}
    print("events whose first word is not among the code's strings:",
          sorted(e for e in events if e.split(" ")[0] not in literals) or "none")
    print("events with extra words:", sorted(e for e in events if " " in e))
    print("path ids not among the code's strings: %d of %d" % (
        sum(1 for i in ids if i not in literals), len(ids)))
    print("next targets that are not a path id but are a code string:",
          sorted({b.split(" -> ")[1] for b in bad_next if " -> " in b and b.split(" -> ")[1] in literals}) or "none")
print("problems:", problems or "none")
