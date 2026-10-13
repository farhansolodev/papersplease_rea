"""Checks of Ends.xml and Intro.xml against what the code reads.

Usage: python -I ends_check.py <reference dir> <assets dir> <stringliteral.json>

<assets dir> is extracted/art/assets. Also models which pages of an ending are
shown (the `when` test of play.screen.Intro).
"""
import collections
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import travspec as T

C = collections.Counter
assets = sys.argv[2]
data = os.path.join(assets, "data")
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
code_strings = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}
problems = []


def parse(text):
    """The comments in Ends.xml are rows of dashes, which a strict XML reader
    rejects; they are removed first."""
    return ET.fromstring(re.sub(r"<!--.*?-->", "", text, flags=re.S))


raw = read("Ends.xml")
print("-- Ends.xml --")
print("  comments:", len(re.findall(r"<!--.*?-->", raw, flags=re.S)),
      "| of them not just dashes:", [c for c in re.findall(r"<!--(.*?)-->", raw, flags=re.S) if c.strip("- \t\r\n")])
try:
    ET.fromstring(raw)
    print("  a strict XML reader accepts the file as it is")
except ET.ParseError as e:
    print("  a strict XML reader rejects the file as it is:", e)
root = parse(raw)
ends = root.findall("end")
print("  top-level tags:", dict(C(child.tag for child in root)))
print("  <end> attributes:", dict(C(a for e in ends for a in e.attrib)))
pages = [(e.get("id"), p) for e in ends for p in e.findall("page")]
print("  <page> attributes:", dict(C(a for _, p in pages for a in p.attrib)))
print("  tags under <end>:", dict(C(child.tag for e in ends for child in e)))
for attribute in {a for e in ends for a in e.attrib} - {"id", "music", "num", "achieve", "pages", "gocredits"}:
    problems.append("<end> attribute the code does not read: " + attribute)
for attribute in {a for _, p in pages for a in p.attrib} - {"image", "text", "color", "sound", "when"}:
    problems.append("<page> attribute the code does not read: " + attribute)

ids = [e.get("id") for e in ends]
nums = [T.parse_int(e.get("num")) for e in ends]
print("  endings:", len(ends), "| repeated ids:", [i for i, c in C(ids).items() if c > 1] or "none",
      "| numbers:", "1 to %d, each once" % len(ends) if sorted(nums) == list(range(1, len(ends) + 1)) else nums)
if sorted(nums) != list(range(1, len(ends) + 1)):
    problems.append("ending numbers are not 1..n")
print("  music:", dict(C(e.get("music") for e in ends)), "| go to credits:", [e.get("id") for e in ends if e.get("gocredits") == "true"])
print("  gocredits values:", dict(C(e.get("gocredits") for e in ends if e.get("gocredits") is not None)))
print("  with an achievement:", len([e for e in ends if e.get("achieve")]))
for e in ends:
    target = e.get("pages")
    if target is not None:
        print("  %s borrows the pages of %s (own pages: %d)" % (e.get("id"), target, len(e.findall("page"))))
        if target not in ids:
            problems.append("pages= names a missing ending: " + target)
print("  pages per ending:", {e.get("id"): len(e.findall("page")) for e in ends})

print("\n-- pictures, sounds, colours, text --")
intro_dir = os.path.join(assets, "intro")
images = C(p.get("image") for _, p in pages)
fact_images = [i for i in images if i.startswith("$")]
missing = [i for i in images if not i.startswith("$") and not os.path.exists(os.path.join(intro_dir, i))]
print("  distinct pictures: %d | taken from a fact: %s | files missing from assets/intro: %s" % (
    len(images), fact_images, missing or "none"))
problems += ["picture missing: " + i for i in missing]
for n in range(1, 7):
    if not os.path.exists(os.path.join(intro_dir, "Passport%d.png" % n)):
        problems.append("Passport%d.png missing (needed by End/FamilyPassportsImage)" % n)
print("  Passport1.png to Passport6.png present:", all(
    os.path.exists(os.path.join(intro_dir, "Passport%d.png" % n)) for n in range(1, 7)))
sounds = C(p.get("sound") for _, p in pages if p.get("sound") is not None)
sounds_xml = read("Sounds.xml")
print("  sounds:", dict(sounds), "| defined in Sounds.xml:", {s: ('id="%s"' % s) in sounds_xml for s in sounds})
print("  music ids defined in Sounds.xml:", {m: ('id="%s"' % m) in sounds_xml for m in {e.get("music") for e in ends}})
colors = C(p.get("color") for _, p in pages if p.get("color") is not None)
print("  colours:", dict(colors))
for color in colors:
    if not re.fullmatch(r"0x[0-9a-fA-F]{6}", color):
        problems.append("colour not in 0xRRGGBB form: " + color)
fact_texts = C(p.get("text") for _, p in pages if (p.get("text") or "").startswith("$"))
print("  texts taken from a fact:", dict(fact_texts))
for name in list(fact_texts) + fact_images:
    if name[1:] not in code_strings:
        problems.append("fact named by a page but not set by the code: " + name)
print("  pages with no text attribute:", sum(p.get("text") is None for _, p in pages),
      "| with empty text:", sum(p.get("text") == "" for _, p in pages),
      "| containing &quote;:", sum("&quote;" in (p.get("text") or "") for _, p in pages))

print("\n-- conditions (when) --")
whens = C(p.get("when") for _, p in pages if p.get("when") is not None)
print("  ", dict(whens))
for when in whens:
    tokens = when.split(" ")
    if len(tokens) != 3 or tokens[1] not in ("==", "!=", "has", "!has", "<", "<=", ">", ">="):
        problems.append("condition the tester would misread: " + when)
    if tokens[0] not in code_strings:
        problems.append("condition on a fact the code does not set: " + tokens[0])


def shown_pages(end_id, facts):
    """EndLib.getEndPages plus the page player's rule: a page with a `when`
    that is false is skipped."""
    node = next(e for e in ends if e.get("id") == end_id)
    if node.get("pages") is not None:
        node = next(e for e in ends if e.get("id") == node.get("pages"))
    out = []
    for page in node.findall("page"):
        when = page.get("when")
        if when is None or T.test_with_glue(when.split(" "), 0, lambda left: facts.get(left, "")):
            out.append(page)
    return out


for end_id in ("escape", "flee"):
    counts = {}
    for taken in range(0, 6):
        facts = {"End/FamilyTakeCount": str(taken), "End/FamilyPassportsImage": "Passport%d.png" % (taken + 1)}
        shown = shown_pages(end_id, facts)
        counts[taken] = (len(shown), sum(p.get("sound") == "stamp-down" for p in shown))
    print("  %s: family members taken -> (pages shown, stamp sounds): %s" % (end_id, counts))
    if any(counts[t][1] != t + 1 for t in counts):
        problems.append(end_id + ": the number of stamp sounds is not one per person")

print("\n-- who asks for each ending --")
nights = read("Nights.txt")
travelers = read("Travelers.txt")
for end_id in ids:
    where = []
    if re.search(r"@\s+End\s+%s\s*$" % re.escape(end_id), nights, re.M):
        where.append("Nights.txt")
    if re.search(r"@\s+End\s+%s\s*$" % re.escape(end_id), travelers, re.M):
        where.append("Travelers.txt")
    if end_id in code_strings:
        where.append("the code")
    print("  %-40s %s" % (end_id, ", ".join(where) or "NOTHING FOUND"))
    if not where:
        problems.append("ending nothing asks for: " + end_id)
asked = set(re.findall(r"@\s+End\s+(\S+)", nights + "\n" + travelers))
for name in asked - set(ids):
    problems.append("ending asked for but not in Ends.xml: " + name)

print("\n-- Intro.xml --")
intro = parse(read("Intro.xml"))
intro_pages = intro.findall("page")
print("  root tag: %s | pages: %d | attributes: %s" % (intro.tag, len(intro_pages), dict(C(a for p in intro_pages for a in p.attrib))))
for page in intro_pages:
    if not os.path.exists(os.path.join(intro_dir, page.get("image"))):
        problems.append("intro picture missing: " + page.get("image"))

print("\nproblems:", sorted(set(problems)) or "none")
