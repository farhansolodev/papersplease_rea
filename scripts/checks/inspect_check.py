"""Checks of the inspect mode (docs/inspect-mode.md) with
scripts/reference/inspectmode.py, Papers.xml, Text.xml and the layout.

Usage: python -I inspect_check.py <reference dir> <assets dir>

1. Papers.xml: for every paper, how many marks give a fact the inspect mode
   can select (inspectable, no link, a fact id, after the proxy), and which
   papers cannot be inspected at all.
2. The four things in the booth that can be selected, with their rectangles.
3. Text.xml has the six texts the inspect mode shows.
4. The selection rules on hand-made cases.
5. The diagram's timeline over its 2 seconds.
6. The side the diagram's label takes for a few pairs of rectangles.
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import inspectmode as I  # noqa: E402
import layout as LAYOUT  # noqa: E402

L = LAYOUT.DESKTOP
assets = sys.argv[2]
data = os.path.join(assets, "assets", "data")
problems = []


def truth(v, default):
    if v is None:
        return default
    return v == "true"


# 1. marks
print("1. Inspectable marks per paper")
root = ET.parse(os.path.join(data, "Papers.xml")).getroot()
total = 0
not_inspectable = []
for paper in root.findall("paper"):
    pid = paper.get("id")
    paper_insp = truth(paper.get("inspectable"), True)
    if not paper_insp:
        not_inspectable.append(pid)
    count = 0
    for page in paper.findall("page"):
        page_insp = truth(page.get("inspectable"), paper_insp)
        for m in page.findall("mark"):
            insp = truth(m.get("inspectable"), page_insp)
            text, image, emblem = m.get("text"), m.get("image"), m.get("emblem")
            fact = None
            if text is not None and text.startswith("$"):
                fact = text[1:]
            elif image is not None and image.startswith("$"):
                fact = image[1:]
            elif emblem is not None:
                fact = "Emblem/" + emblem
            if m.get("proxy"):
                fact = m.get("proxy")
            mark = {"fact": fact, "inspectable": insp, "link": m.get("link")}
            path = I.fact_path_for_mark(pid, mark)
            if path != pid and paper_insp:
                count += 1
    total += count
    print("   %-18s %3d" % (pid, count))
print("   marks in all: %d; papers that cannot be inspected (%d): %s" % (
    total, len(not_inspectable), " ".join(not_inspectable)))

# 2. booth things
print("2. Booth things (booth coordinates)")
for path, name in I.BOOTH_INSPECTABLES:
    r = L[name]
    print("   %-14s %s" % (path, r))
    if r is None:
        problems.append("no rectangle for %s" % path)

# 3. texts
print("3. Texts")
text_root = ET.parse(os.path.join(data, "Text.xml")).getroot()
ids = {item.get("id"): "".join(t.text or "" for t in item.findall("t")) for item in text_root.iter("item")}
for key in ("booth_highlight", "booth_interrogate", "booth_discrepancy", "booth_matching",
            "booth_nocorrelation", "booth_cleared"):
    if key not in ids:
        problems.append("missing text %s" % key)
    print("   %-20s %r" % (key, ids.get(key)))
for rel, cleared in (("NONE", False), ("AGREE", False), ("AGREE", True), ("DISAGREE", False)):
    print("   relationship %-8s cleared %-5s -> %s" % (rel, cleared, I.relationship_text_id(rel, cleared)))

# 4. selection
print("4. Selection")
s = I.Selection()
P = I.Inspectable
cases = [
    (P("Passport/Name", None), "inspect-highlight", ["Passport/Name", None]),
    (P("Passport/Name", None), "inspect-unhighlight", [None, None]),
    (P("Passport/Name", None), "inspect-highlight", ["Passport/Name", None]),
    (P("EntryPermit/Name", None), "inspect-highlight", ["Passport/Name", "EntryPermit/Name"]),
    (P("Booth/Face", None), "inspect-highlight", ["Booth/Face", "EntryPermit/Name"]),
    (P("Rules/Seal", None), "inspect-highlight", ["Booth/Face", "Rules/Seal"]),
    (P("Rules", None), "inspect-highlight", ["Booth/Face", "Rules"]),
    (P("Rules", None, selectable=False), None, ["Booth/Face", "Rules"]),
]
for item, sound, expect in cases:
    got = s.select(item)
    slots = [x.fact_path if x else None for x in s.slots]
    ok = got == sound and slots == expect
    print("   %-18s %-20s %s %s" % (item.fact_path, got, slots, "" if ok else "UNEXPECTED"))
    if not ok:
        problems.append("selection case %s" % item.fact_path)
for is_open in (False, True):
    for selectable in (False, True):
        print("   double click, open %-5s selectable %-5s -> %s" % (
            is_open, selectable, I.quick_inspect(is_open, selectable)))

# 5. diagram
print("5. Diagram timeline (2 s)")
for k in range(0, 21, 2):
    t = k / 20.0
    p = I.diagram_parts(t)
    print("   %.1f s  lines %.2f %.2f  line2 %.2f  text %-5s  button %.2f" % (
        t * 2, p["line0"], p["line1"], p["line2"], p["text"], p["button"]))
blinks = 0
prev = False
for k in range(2001):
    v = I.diagram_parts(k / 2000.0)["text"]
    if v and not prev:
        blinks += 1
    prev = v
print("   the text appears %d times (blinks) before staying" % blinks)
if blinks != 3:
    problems.append("expected three appearances of the text")

# 6. sides
print("6. Diagram label side")
for r0, r1 in (((200, 20, 60, 8), (400, 150, 60, 8)),
               ((200, 20, 60, 8), (210, 150, 60, 8)),
               ((200, 100, 60, 8), (230, 110, 60, 8)),
               ((10, 10, 60, 8), (100, 190, 60, 8)),
               ((450, 60, 100, 8), (460, 70, 100, 8))):
    print("   %s %s -> %s" % (r0, r1, I.join_side(r0, r1, 60, 22)))

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
