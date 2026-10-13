"""Checks of Endlesses.xml and Endless.csv, and a model of endless scoring.

Usage: python -I endless_check.py <reference dir> <assets dir>

<assets dir> is extracted/art/assets.
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import travspec as T
from person import lerp_scale

C = collections.Counter
assets = sys.argv[2]
data = os.path.join(assets, "data")
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
problems = []

root = ET.fromstring(read("Endlesses.xml"))
styles, courses = root.findall("style"), root.findall("course")
print("-- Endlesses.xml --")
print("  tags:", dict(C(e.tag for e in root.iter())))
print("  <style> attributes:", dict(C(a for s in styles for a in s.attrib)))
print("  <course> attributes:", dict(C(a for c in courses for a in c.attrib)))
actions = [(s.get("id"), a) for s in styles for a in s if a.tag != "score"]
print("  action tags:", dict(C(a.tag for _, a in actions)), "| their attributes:", dict(C(k for _, a in actions for k in a.attrib)))
scales = [(s.get("id"), a) for s in styles for a in s if a.tag == "score"]
print("  <score> (scale) attributes:", dict(C(k for _, a in scales for k in a.attrib)), "on", [i for i, _ in scales])
for name, have, known in (("style", {a for s in styles for a in s.attrib},
                           {"id", "name", "desc", "icon", "button", "leaderboard", "reportscoremax", "time", "bulletin"}),
                          ("course", {a for c in courses for a in c.attrib}, {"id", "name", "day", "button", "leaderboard"}),
                          ("action", {k for _, a in actions for k in a.attrib}, {"score", "time", "delta", "end"}),
                          ("score", {k for _, a in scales for k in a.attrib}, {"scale0", "scale1", "time0", "time1"})):
    for attribute in have - known:
        problems.append("<%s> attribute the code does not read: %s" % (name, attribute))
missing = [f for f in [s.get("button") for s in styles] + [s.get("icon") for s in styles] + [c.get("button") for c in courses]
           if not os.path.exists(os.path.join(assets, f))]
print("  button and icon pictures missing from the extracted assets:", missing or "none")


def parse_signed(text):
    """Action.parseSigned."""
    if text.startswith("+"):
        return T.parse_int(text[1:])
    if text.startswith("-"):
        return -T.parse_int(text[1:])
    return T.parse_int(text)


class Style:
    def __init__(self, node):
        self.id = node.get("id")
        self.time_limit = float(node.get("time")) if node.get("time") is not None else 0.0
        self.report_max = node.get("reportscoremax") == "true"
        scale = node.find("score")
        get = lambda key, default: float(scale.get(key)) if scale is not None and scale.get(key) is not None else default
        self.scale0, self.scale1 = get("scale0", 1.0), get("scale1", 1.0)
        self.time0, self.time1 = get("time0", 0.0), get("time1", 1.0)
        self.actions = {}
        for child in node:
            if child.tag != "score":
                self.actions[child.tag] = (parse_signed(child.get("score", "0")), parse_signed(child.get("time", "0")),
                                           parse_signed(child.get("delta", "0")), child.get("end") == "true")

    def scale(self, time):
        return int(lerp_scale(time, self.time0, self.time1, self.scale0, self.scale1))


class Endless:
    """play.day.Endless: the score and clock of one endless run."""

    def __init__(self, style):
        self.style, self.time, self.score, self.score_max = style, 0.0, 0, 0
        self.counts, self.ending = C(), False

    def advance(self, seconds):
        self.time += seconds
        if self.style.time_limit != 0.0 and self.time > self.style.time_limit:
            self.ending = True

    def handle(self, action_id):
        if self.ending or action_id not in self.style.actions:
            return
        score, time, delta, end = self.style.actions[action_id]
        before = self.counts[action_id]
        self.counts[action_id] += 1
        if score != 0:
            self.score += self.style.scale(self.time) * score + before * delta
            self.score_max = max(self.score, self.score_max)
            if self.score < 0:
                self.ending = True
        if time != 0:
            self.time -= time
        if end:
            self.ending = True

    @property
    def reported(self):
        return self.score_max if self.style.report_max else self.score


library = {s.get("id"): Style(s) for s in styles}
print("\n-- the styles as the code holds them --")
for style in library.values():
    print("  %-11s time limit %-5s report highest: %-5s scale %s..%s over %s..%s s | actions (score, time, delta, end): %s" % (
        style.id, style.time_limit, style.report_max, style.scale0, style.scale1, style.time0, style.time1, style.actions))
if set(library) != {"timed", "perfection", "endurance"}:
    problems.append("unexpected set of styles")

print("\n-- scoring model --")
run = Endless(library["timed"])
for _ in range(20):
    run.advance(20)
    run.handle("process")
run.handle("mistake")
after_mistake = run.time
run.handle("detain")
print("  timed: 20 travelers in 400 s -> score %d; a citation moves the clock from 400 to %.0f s; a detention then to %.0f s and score %d" % (
    20, after_mistake, run.time, run.score))
if after_mistake != 430 or run.time != 425 or run.score != 21:
    problems.append("timed model")
run.advance(200)
print("    past 600 s the run is ending:", run.ending)
points = []
for minute in range(0, 12):
    run = Endless(library["perfection"])
    run.advance(minute * 60 + 30)
    run.handle("process")
    points.append(run.score)
print("  perfection: points for one traveler in minute 1..12:", points)
if points[:10] != [10, 9, 8, 7, 6, 5, 4, 3, 2, 1] or points[-1] != 1:
    problems.append("perfection points per minute")
run = Endless(library["perfection"])
run.handle("mistake")
print("    a citation ends the run:", run.ending)
run = Endless(library["endurance"])
costs = []
for _ in range(30):
    run.handle("process")
for _ in range(4):
    before = run.score
    run.handle("mistake")
    costs.append(before - run.score)
print("  endurance: after 30 travelers, four citations cost %s -> score %d, reported %d, ending %s" % (
    costs, run.score, run.reported, run.ending))
if costs != [5, 10, 15, 20] or run.reported != 30 or not run.ending:
    problems.append("endurance model")

print("\n-- Endless.csv --")
endless = T.DaysTable(read("Endless.csv"))
days = T.DaysTable(read("Days.csv"))
print("  columns:", [c for c in endless.col_ids[1:] if c], "| rows:", len(endless.rows))
print("  rows not in Days.csv:", sorted(set(endless.rows) - set(days.rows)) or "none",
      "| Days.csv rows not here:", sorted(set(days.rows) - set(endless.rows)) or "none")
for course in courses:
    day = course.get("day")
    if day not in endless.col_ids:
        problems.append("course day not a column of Endless.csv: " + day)
        continue
    rules = endless.accumulated(day, "RULES")
    features = endless.accumulated(day, "FEATURES")
    print("  %s (column %s): %d rules, features %s" % (course.get("id"), day, len(rules), features))
    print("      rules:", rules)
    print("      shown as:", endless.cell(day, "DESC").replace("\n", ", "), "| filler traveler:", endless.cell(day, "FILL"),
          "| line length:", endless.cell(day, "LINE"), "| duration:", endless.cell(day, "DURATION"))
facts = read("Facts.xml")
for rule in {r for c in courses for r in endless.accumulated(c.get("day"), "RULES")}:
    if rule not in facts:
        problems.append("rule not in Facts.xml: " + rule)
travelers = read("Travelers.txt")
for fill in {endless.cell(c.get("day"), "FILL") for c in courses}:
    if not re.search(r"^%s\s*$" % re.escape(fill), travelers, re.M):
        problems.append("filler traveler entry missing: " + fill)

print("\nproblems:", sorted(set(problems)) or "none")
