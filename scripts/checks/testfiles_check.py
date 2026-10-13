"""Cross-checks the two test-tooling data files, TestScenarios.xml and Auto.txt.

Usage: python -I testfiles_check.py <reference dir> <data dir>
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import tabtree

data = sys.argv[2]
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
problems = []

# ---------------------------------------------------------------- TestScenarios.xml
root = ET.fromstring(read("TestScenarios.xml"))
scenarios = root.findall("scenario")
attrs = collections.Counter(a for s in scenarios for a in s.attrib)
print("TestScenarios.xml: %d scenarios, attributes %s" % (len(scenarios), dict(attrs)))
unread = set(attrs) - {"id", "cleargamefacts", "day", "night", "traveler"}
fact_attrs = {a for s in scenarios for f in s.findall("fact") for a in f.attrib}
print("  attributes the loader does not read: %s; <fact> attributes: %s" % (sorted(unread) or "none", sorted(fact_attrs)))
starts = collections.Counter(tuple(k for k in ("day", "night", "traveler") if s.get(k) is not None) for s in scenarios)
print("  what a scenario starts at:", {"+".join(k) or "nothing": v for k, v in starts.items()})
prefixes = collections.Counter(f.get("path").split("/")[0] for s in scenarios for f in s.findall("fact"))
print("  fact stores set:", dict(prefixes))
traveler_ids = set(re.findall(r"^([A-Z0-9_]+)\b", read("Travelers.txt"), re.M))
missing = sorted({s.get("traveler") for s in scenarios if s.get("traveler")} - traveler_ids)
print("  travelers named but not in Travelers.txt:", missing or "none")
if unread:
    problems.append("scenario attribute not read")

# ---------------------------------------------------------------- Auto.txt
tree = tabtree.parse(read("Auto.txt"))
tops = {n.params[0]: n for n in tree.nodes}
routes = tops["@"].nodes
kinds = collections.Counter(r.params[0] for r in routes)
print("Auto.txt: %d routes %s; other top-level blocks: %d" % (len(routes), dict(kinds), len(tree.nodes) - 1))
endings = set(re.findall(r'<end[^>]*\bid="([^"]+)"', read("Ends.xml")))
story = [r for r in routes if r.params[0] == "story"]
no_block = [r.params[2] for r in story if r.params[2] not in tops]
no_ending = [r.params[2] for r in story if r.params[2] not in endings]
print("  story routes: %d; without a block of their own: %s; whose name is not an ending in Ends.xml: %s" % (
    len(story), no_block or "none", no_ending or "none"))
print("  endings in Ends.xml with no story route:", sorted(endings - {r.params[2] for r in story}) or "none")
bases = collections.Counter(n.params[1] for n in tree.nodes if len(n.params) > 1)
print("  blocks that build on another block:", dict(bases), "| unknown base:",
      sorted(b for b in bases if b not in tops) or "none")
entries = collections.Counter()
actions = collections.Counter()
unknown_travelers = set()
for block in tree.nodes[1:]:
    for entry in block.nodes:
        name = entry.params[0]
        if name == "*":
            entries["* (any traveler)"] += 1
        elif re.fullmatch(r"[A-Z0-9_]+", name):
            entries["a traveler id"] += 1
            if name not in traveler_ids:
                unknown_travelers.add(name)
        else:
            entries["other: " + name] += 1
        for action in entry.nodes:
            actions[action.params[0]] += 1
print("  entries inside blocks:", dict(entries))
print("  traveler ids not in Travelers.txt:", sorted(unknown_travelers) or "none")
print("  action words under entries:", dict(actions))
endless = [r for r in routes if r.params[0] == "endless"]
print("  endless routes: %s" % sorted({(r.params[2], r.params[3]) for r in endless}))
print("problems:", problems or "none")
