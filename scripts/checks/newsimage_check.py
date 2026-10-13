"""Checks of the newspaper layout pictures and scripts/reference/newsimage.py.

Usage: python -I newsimage_check.py <reference dir> <assets dir>

<assets dir> is extracted/art/assets. Needs Pillow.
"""
import collections
import os
import sys

sys.path.insert(0, sys.argv[1])
import news as N
import newsimage as NI
from PIL import Image
from rand import Rand
from seeds import Launch, day_seeds

C = collections.Counter
assets = sys.argv[2]
problems = []


class Counting(Rand):
    count = 0

    def next_int(self):
        self.count += 1
        return Rand.next_int(self)

    def next_float(self):
        return self.next_int() / 2147483647.0

    random = next_float


def check_layouts(subdir, label):
    print("-- layout pictures, %s --" % label)
    for index in range(6):
        path = os.path.join(assets, subdir, "NewsLayout%d.png" % index)
        image = Image.open(path).convert("RGBA")
        layout = NI.Layout(assets, index, subdir)
        px = image.load()
        colours = C((px[x, y][0] << 16 | px[x, y][1] << 8 | px[x, y][2])
                    for y in range(image.height) for x in range(image.width))
        known = {c for _, c in NI.RECT_COLOURS} | {0}
        if set(colours) - known:
            problems.append("%s layout %d: other colours %s" % (label, index, set(colours) - known))
        cells = [[None] * layout.num_cols for _ in range(layout.num_lines)]
        for (name, colour), rect in zip(NI.RECT_COLOURS, layout.rects):
            # is the colour a solid rectangle, on whole columns?
            x, y, w, h = NI.colour_bounds(image, colour)
            if colours[colour] != (w + 1) * (h + 1):
                problems.append("%s layout %d: %s is not a solid rectangle" % (label, index, name))
            if x % 10 or (w + 1) % 10:
                problems.append("%s layout %d: %s is not on whole columns" % (label, index, name))
            if rect.x + rect.w > layout.num_cols or rect.y + rect.h > layout.num_lines:
                problems.append("%s layout %d: %s leaves the page" % (label, index, name))
            for line in range(rect.y, rect.y + rect.h):
                for col in range(rect.x, rect.x + rect.w):
                    if cells[line][col]:
                        problems.append("%s layout %d: %s overlaps %s" % (label, index, name, cells[line][col]))
                    cells[line][col] = name
        areas = [r.w * r.h for r in layout.rects]
        if areas[0] != max(areas) or areas.count(max(areas)) != 1:
            problems.append("%s layout %d: the first rectangle is not the single largest" % (label, index))
        print("  %d: %dx%d -> %d cols, %d lines, back %s" % (
            index, image.width, image.height, layout.num_cols, layout.num_lines, layout.back_image))
        for rect, area in zip(layout.rects, areas):
            print("       %-40s area %2d  pixels: left %3d top %3d width %3d height %3d" % (
                rect, area, rect.left, rect.top, rect.width, rect.full_height))


check_layouts("", "desktop")
check_layouts(os.path.join("layout", "phone"), "phone")

print("\n-- back pictures --")
for name, cols, lines in (("News.png", 4, 26), (os.path.join("layout", "phone", "NewsTall.png"), 3, 40)):
    image = Image.open(os.path.join(assets, name))
    need = (cols * NI.COL_STEP + NI.ARTICLE_X, lines * NI.LINE_STEP + NI.ARTICLE_Y)
    print("  %s: %dx%d; the grid reaches x %d, y %d" % (name, image.width, image.height, need[0], need[1]))
    if need[0] > image.width or need[1] > image.height:
        problems.append("%s: the grid does not fit" % name)

print("\n-- the days (no traveler news) --")
lib, table = N.load(os.path.join(assets, "data"))
marks = []
total_draws = C()
slot_kinds = C()
extra_draws = C()
most_articles = 0
for master in range(200):
    launch = Launch(master)
    launch.load_save()
    for day in range(1, 32):
        rand = Counting(day_seeds(day, launch.story_seed)["news"])
        day_news = N.DayNews(lib, table, rand, {}, day)
        before = rand.count
        plan = NI.Plan(NI.Layout(assets, day), day_news.articles, rand)
        marks.append(len(plan.marks))
        most_articles = max(most_articles, len(day_news.articles))
        if plan.dropped:
            problems.append("day %d: more articles than rectangles" % day)
        extra = sum(d for _, _, _, d in plan.slots)
        if rand.count - before != len(plan.marks) + 1 + extra:
            problems.append("day %d: draw count does not add up" % day)
        extra_draws[extra] += 1
        for position, (_, _, kind, _) in enumerate(plan.slots):
            slot_kinds[(position, kind)] += 1
        for x, y in plan.marks:
            if not (23 <= x < 23 + 3 * NI.COL_STEP + 60 and 56 <= y < 56 + 26 * 6):
                problems.append("a word mark outside the page: %s" % ((x, y),))
print("  200 master seeds x 31 days")
print("  word marks per newspaper: min %d, max %d, mean %.1f (one more draw than marks)" % (
    min(marks), max(marks), sum(marks) / len(marks)))
print("  most articles on one day:", most_articles)
print("  draws after the word marks (stamps and faces):", dict(sorted(extra_draws.items())))
for position in range(5):
    print("  rectangle %d (%s):" % (position, NI.RECT_COLOURS[position][0]),
          {k[1]: v for k, v in sorted(slot_kinds.items()) if k[0] == position})

print("\n-- pictures and stamps in News.txt --")
for entry in lib.root.nodes:
    for article in lib.get_articles(entry.params[0]):
        if article.image or article.stamp:
            if not article.title:
                problems.append("%s: a picture or stamp without a title" % entry.params[0])
            parts = len(article.image[5:].split("-")) if article.image else 0
            print("  %-24s image %-20s stamp %-18s face parts given: %s" % (
                entry.params[0], article.image, article.stamp, parts or "-"))
            if article.image and not article.image.startswith("Face:"):
                problems.append("%s: a picture that is not a Face" % entry.params[0])

print("\nproblems:", sorted(set(problems)) or "none")
