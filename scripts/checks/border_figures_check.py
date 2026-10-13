"""Checks Paths.xml and Days.csv against what the border figures
(play.day.border.Person) and the waiting line (WaitingLine) need.
See docs/border-figures.md.

Usage: python -I border_figures_check.py <reference dir> <data dir>
"""
import collections
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import paths as P
import travspec
from rand import Rand

data = sys.argv[2]
text = open(os.path.join(data, "Paths.xml"), encoding="utf-8").read()
root = ET.fromstring(text)
lib = P.PathLib(text)
problems = []


class CountingRand:
    def __init__(self):
        self.rand, self.draws = Rand(1), 0

    def random(self):
        self.draws += 1
        return self.rand.random()


def draws_for(path_id):
    counter = CountingRand()
    lib.create_path(counter, path_id)
    return counter.draws


# 1. The paths the waiting line asks for by name.
LINE_PATHS = (["waiting-line", "enter-left", "panic-poisoned"]
              + ["%s-%d" % (family, n) for family in ("disperse", "panic", "rush") for n in range(3)])
missing = [p for p in LINE_PATHS if not lib.has_path(p)]
print("paths the waiting line names: %d, missing: %s" % (len(LINE_PATHS), missing or "none"))
problems += ["missing path " + p for p in missing]
for family in ("disperse", "panic", "rush"):
    extra = [i for i in lib.path_nodes if i.startswith(family + "-") and i[len(family) + 1:].isdigit()
             and int(i[len(family) + 1:]) > 2]
    if extra:
        problems.append("%s has numbered paths the code can never pick: %s" % (family, extra))
print("random draws when one of them is created:",
      ", ".join("%s %d" % (p, draws_for(p)) for p in LINE_PATHS if lib.has_path(p)))
if draws_for("waiting-line") != 12:
    problems.append("waiting-line no longer costs 12 draws")

enter = lib.path_nodes["enter-left"]
with_event = [n.get("id") for n in root.findall("path") if n.get("end") == "arrived-in-booth"]
print("paths whose end event is arrived-in-booth:", with_event)
if with_event != ["enter-left"] or enter.get("next") is not None:
    problems.append("enter-left is not the only path ending in arrived-in-booth, or it has a next")

# 2. The target figure swaps the part before the first "-" for "target".
swaps = {}
for path_id in LINE_PATHS:
    alternative = "target" + path_id[path_id.index("-"):]
    if lib.has_path(alternative):
        swaps[path_id] = alternative
print("alternative paths for the target figure:", swaps or "none")
if swaps != {"waiting-line": "target-line"}:
    problems.append("the target figure's alternative paths changed")
if lib.has_path("target-line"):
    print("  target-line draws: %d; points: %d (waiting-line: %d)" % (
        draws_for("target-line"), len(lib.path_nodes["target-line"].findall("p")),
        len(lib.path_nodes["waiting-line"].findall("p"))))

# 3. Attributes the figure code relies on.
all_paths = lib._order          # the library's own nodes: unnamed paths have an id here
labels, last_named, since = {}, "the start of the file", 0
for node, original in zip(all_paths, root.findall("path")):
    if original.get("id") is None:
        since += 1
        labels[node.get("id")] = "(unnamed, %d after %s)" % (since, last_named)
    else:
        last_named, since = original.get("id"), 0
        labels[node.get("id")] = original.get("id")


def label(node):
    return labels[node.get("id")]


anims ={a.get("id"): P.Anim(a) for a in root.findall("anim")}
no_point_warp = [label(n) for n in all_paths if n.get("warp") == "true" and not n.findall("p")]
no_point_snap = [label(n) for n in all_paths if n.get("snap") == "true" and not n.findall("p")]
print("warp paths: %d, without points: %s" % (
    sum(1 for n in all_paths if n.get("warp") == "true"), no_point_warp or "none"))
print("snap paths: %d, without points: %s" % (
    sum(1 for n in all_paths if n.get("snap") == "true"), no_point_snap or "none"))
both = [label(n) for n in all_paths if n.get("warp") == "true" and n.get("snap") == "true"]
print("paths with both snap and warp (warp would be ignored):", both or "none")
problems += ["warp path without points: %s" % i for i in no_point_warp]
faces = collections.Counter(n.get("face") for n in all_paths if n.get("face") is not None)
print("face values:", dict(faces))
if set(faces) - {"left", "right"}:
    problems.append("a face value other than left or right (the code would treat it as right)")
still_h = [a.id for a in anims.values() if a.fps_h == 0 and a.fps_v != 0]
print("animations that are still sideways but not up and down (would never play):", still_h or "none")
print("animations whose strip ending is -Idle (the figure's own idle strip is used instead):",
      [a.id for a in anims.values() if a.suffix_h == "-Idle"])
print("animations marked as a death:", [a.id for a in anims.values() if a.death])

# 4. How each path can come to its end.
ways = collections.Counter()
never = []
zero_length_warp = []
for node in all_paths:
    anim = anims[node.get("anim", "walk")]
    points = node.findall("p")
    stops = anim.fps_h != 0 and not anim.loop
    hold = node.get("hold") is not None and P._float(node.get("hold")) > 0
    walks = bool(points) and node.get("snap") != "true"       # a snap path places the figure and never moves it
    reasons = (["arrives"] if walks else []) + (["animation finishes"] if stops else []) + (["hold runs out"] if hold else [])
    ways[" or ".join(reasons) or "never by itself"] += 1
    if not reasons:
        never.append(node)
    if node.get("warp") == "true" and points:
        path = lib.create_path(CountingRand(), node.get("id"))
        if len(points) > 1 and P.math.dist(path.points[0], path.points[1]) == 0:
            zero_length_warp.append(label(node))
print("how a path can end:")
for way, count in ways.most_common():
    print("  %4d  %s" % (count, way))
print("paths that never end by themselves:", [label(n) for n in never])
for node in never:
    if node.get("next") is not None or node.get("end") is not None:
        problems.append("path %s never ends but has a next or an end event" % label(node))
print("warp paths whose first two points are the same spot (direction cannot be worked out):",
      zero_length_warp or "none")

# 5. The waiting line's length per day.
table = travspec.DaysTable(open(os.path.join(data, "Days.csv"), encoding="utf-8-sig").read())
lengths = collections.Counter()
for day in range(1, 32):
    length = travspec.parse_int(table.cell(day, "LINE")) if table.cell(day, "LINE") else 0
    lengths[length] += 1
    if length < 3:
        problems.append("day %d: a line of %d cannot work (stops = people - 2)" % (day, length))
    if "BORDER_TARGET" in table.accumulated(day, "FEATURES"):
        print("day %d has BORDER_TARGET: line of %d, the target is person number %d (counting from 0, from the back)" % (
            day, length, length // 4))
print("line lengths on days 1 to 31 (length: days):", dict(sorted(lengths.items(), reverse=True)))
print("draws to build a line of 100 without a target: %d (15 per person: 1 strip speed, 12 path, 2 idle)" % (
    100 * (1 + draws_for("waiting-line") + 2)))

print("problems:", problems or "none")
