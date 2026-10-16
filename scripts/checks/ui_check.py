"""Checks of the rest of play.ui (docs/ui-parts.md) with scripts/reference/ui.py.

Usage: python -I ui_check.py <reference dir> <assets dir>

1. DiagramLine: on several polylines, every dot is more than one pixel from
   the one before (a dotted line) and the corners are rounded.
2. DottedLine: the lit pixels are every other pixel, from an even position.
3. The speech bubble picture and its stretched middle; for every line of
   Speeches.txt as written (placeholders not filled in), whether the bubble
   wraps it (wider than 160 pixels in small_tight) and how long it stays.
4. The bubble's opening and closing over time.
5. KineticScroll: a drag past the end, the rubber band and the spring back.
Needs Pillow for the picture size.
"""
import collections
import os
import sys

from PIL import Image

sys.path.insert(0, sys.argv[1])
import fonts  # noqa: E402
import tabtree  # noqa: E402
import ui as U  # noqa: E402

assets = sys.argv[2]
problems = []

# 1. DiagramLine
print("1. DiagramLine")
for pts in ([(10, 10), (60, 10)], [(10, 10), (60, 10), (60, 40)], [(5, 5), (40, 30), (90, 30), (90, 90)],
            [(0, 0), (3, 0), (3, 3)]):
    dots = U.build_dots(pts)
    bad = sum(1 for a, b in zip(dots, dots[1:]) if abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1)
    print("   %-40s %3d dots, %d too close" % (pts, len(dots), bad))
    if bad:
        problems.append("dots too close on %s" % (pts,))
half = U.visible_dots(U.build_dots([(10, 10), (60, 10)]), 0.5)
print("   visibleT 0.5 of the first line shows %d dots" % len(half))

# 2. DottedLine
print("2. DottedLine")
for p0, p1 in (((0, 5), (10, 5)), ((3, 5), (70, 5)), ((4, 0), (4, 15))):
    px = U.dotted_pixels(p0, p1)
    ok = all((x if p0[1] == p1[1] else y) % 2 == 0 for x, y in px)
    print("   %s to %s: %d pixels, all even: %s" % (p0, p1, len(px), ok))
    if not ok:
        problems.append("dotted line parity %s" % (p0,))

# 3. the bubble and the speech lines
print("3. Speech bubble")
pic = Image.open(os.path.join(assets, "assets", "SpeechBubble.png"))
print("   %s %dx%d, stretched middle %s" % (U.BUBBLE_PICTURE, pic.width, pic.height, U.BUBBLE_MIDDLE))
mx, my, mw, mh = U.BUBBLE_MIDDLE
if mx + mw > pic.width or my + mh > pic.height:
    problems.append("bubble middle outside the picture")
font = fonts.FontLib(os.path.join(assets, "assets")).get("small_tight")
text = open(os.path.join(assets, "assets", "data", "Speeches.txt"), encoding="utf-8").read()
lines = []
for entry in tabtree.parse(text).nodes:
    for child in entry.nodes:
        words = [w for w in child.params if not w.startswith("=") and not w.startswith("?")]
        if words:
            lines.append(" ".join(words))
wraps = [l for l in lines if U.bubble_wrap_width(font.text_width(l)) == 120]
longest = max(lines, key=lambda l: font.text_width(l))
print("   %d lines; %d wider than 160 pixels (wrapped at 120); widest %d px: %r" % (
    len(lines), len(wraps), font.text_width(longest), longest[:60]))
durations = collections.Counter(int(U.bubble_duration(l)) for l in lines)
print("   time shown (whole seconds, 0.1 s a character):", dict(sorted(durations.items())))

# 4. reveal
print("4. Opening (0.75 s) and closing (0.5 s), centred bubble")
for opening, total in ((True, 0.75), (False, 0.5)):
    row = []
    for k in range(0, 9):
        t = k / 8.0
        line, width, bounce = U.bubble_reveal_parts(t if opening else 1 - t, opening, True)
        row.append("%.2fs l%.1f w%.1f b%.1f" % (t * total, line, width, bounce))
    print("   %s: %s" % ("open" if opening else "close", "; ".join(row)))

# 5. scroll
print("5. KineticScroll (range 0..200)")
k = U.KineticScroll()
s = 0.0
for f, touch in enumerate((100, 90, 70, 50, 40)):
    s = k.drag(f, touch, s, 0.0, 200.0)
print("   dragged left by 60 from the start: scroll %.1f" % s)
k = U.KineticScroll()
s = 0.0
for f, touch in enumerate((100, 110, 130, 150)):
    s = k.drag(f, touch, s, 0.0, 200.0)
print("   dragged right by 50 at the start (past the end): scroll %.1f (rubber band)" % s)
for f in range(4, 60):
    s = k.update(f + 1, s, 0.0, 200.0, 1 / 60.0)
print("   after letting go, one second later: scroll %.1f" % s)
if s != 0.0:
    problems.append("spring back did not reach the end")

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
