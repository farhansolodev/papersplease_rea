"""Cross-checks Credits.txt against what play.screen.CreditList does with it.

Usage: python -I credits_check.py <reference dir> <assets dir>
"""
import collections
import os
import sys

sys.path.insert(0, sys.argv[1])
import tabtree

assets = sys.argv[2]
text = open(os.path.join(assets, "data", "Credits.txt"), encoding="utf-8", newline="").read()
languages = [l.strip() for l in open(os.path.join(assets, "data", "Languages.txt"), encoding="utf-8").read().split("\n") if l.strip()]
root = tabtree.parse(text)
problems = []

STYLE = {"$": "finale", "-": "small", "/": "team", "+": "role"}
kinds = collections.Counter()
conditions = collections.Counter()
images, depths = [], collections.Counter()
lines = []                                    # what the list would show, in order


def add(node, depth, available):
    words = list(node.params)
    if words and words[0] == "?":
        words.pop(0)
        condition = words.pop(0) if words else ""
        conditions[condition] += 1
        if condition.startswith("have-lang-"):
            code = condition[len("have-lang-"):]
            if code not in languages:
                problems.append("unknown language code " + code)
            if code not in available:
                return
        else:
            problems.append("condition the code does not know: " + condition)
    first = words[0] if words else ""
    if first == "[OFFSCREEN]":
        kinds["[OFFSCREEN]"] += 1
        lines.append("(jump below the screen)")
    elif first == "[SPACE]":
        kinds["[SPACE]"] += 1
        lines.append("(gap)")
    elif first == "[IMAGE]":
        kinds["[IMAGE]"] += 1
        images.append(words[1])
        lines.append("(picture %s)" % words[1])
    elif words:
        style = STYLE.get(first, "name")
        kinds[style] += 1
        shown = " ".join(words[1:] if first in STYLE else words)
        lines.append("%-6s %s" % (style, shown))
        if first.startswith("[") or (len(first) == 1 and not first.isalnum() and first not in STYLE):
            problems.append("looks like an unknown marker: " + first)
    depths[depth] += 1
    for child in node.nodes:
        add(child, depth + 1, available)


add(root, 0, languages)
print("lines by kind (all languages available):", dict(kinds))
print("nodes by depth:", dict(sorted(depths.items())))
print("conditions:", dict(conditions))
print("pictures:", images, "missing:", [i for i in images if not os.path.exists(os.path.join(assets, i))] or "none")
all_lines = len(lines)
lines.clear()
kinds.clear()
add(root, 0, ["en"])
print("lines shown with every language: %d; with only English: %d" % (all_lines, len(lines)))
print("first lines:")
for line in lines[:8]:
    print("   " + line)
print("Languages.txt codes:", languages)
print("problems:", sorted(set(problems)) or "none")
