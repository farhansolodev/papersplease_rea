"""The newspaper picture: layout rectangles, which article goes where, and
the random draws made while it is composed.

Reference for play.day.LayoutImage and play.day.DayNewsImage.make
(docs/newspaper-picture.md). Text fitting (title font or regular font, whether
the subtitle fits) is NOT modelled, so text positions and the stamp's exact
position are not computed; the number of draws is.

Usage: python -I newsimage.py <master seed> <assets dir> [day ...]
Needs Pillow.
"""
import math
import os
import sys

from PIL import Image

# play.day.DayNewsImage static values
ARTICLE_X = 13
ARTICLE_Y = 56
COL_WIDTH = 80
COL_PADDING_X = 5
LINE_HEIGHT = 5
LINE_PADDING_Y = 1
COL_STEP = COL_WIDTH + COL_PADDING_X       # 85, used as one number in the code
LINE_STEP = LINE_HEIGHT + LINE_PADDING_Y   # 6
WORD_RUN = 60                              # length of one "line" in the word-break walk

# play.day.LayoutImage: the colours looked for, in this order
RECT_COLOURS = [("red", 0xFF0000), ("green", 0x00FF00), ("blue", 0x0000FF),
                ("yellow", 0xFFFF00), ("magenta", 0xFF00FF)]
LAYOUT_COL_WIDTH = 10


class Rect:
    def __init__(self, name, x, y, w, h):
        self.name, self.x, self.y, self.w, self.h = name, x, y, w, h

    # pixel values used by DayNewsImage.make
    left = property(lambda self: self.x * COL_STEP + ARTICLE_X)
    top = property(lambda self: self.y * LINE_STEP + ARTICLE_Y)
    width = property(lambda self: self.w * COL_STEP - 5)
    full_height = property(lambda self: self.h * LINE_STEP)

    def __repr__(self):
        return "%s(col %d, line %d, %d cols, %d lines)" % (self.name, self.x, self.y, self.w, self.h)


def colour_bounds(image, colour):
    """LayoutImage.getColorBoundsRect: w and h are max - min, NOT a count."""
    px = image.load()
    xs, ys = [], []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = px[x, y][:3]
            if (r << 16 | g << 8 | b) == colour:
                xs.append(x)
                ys.append(y)
    if not xs:
        return 10000, 10000, -20000, -20000
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


class Layout:
    def __init__(self, assets_dir, day_id, subdir=""):
        self.index = int(math.fmod(day_id, 6))
        image = Image.open(os.path.join(assets_dir, subdir, "NewsLayout%d.png" % self.index)).convert("RGBA")
        self.rects = []
        for name, colour in RECT_COLOURS:
            x, y, w, h = colour_bounds(image, colour)
            x = math.floor(x / LAYOUT_COL_WIDTH + 0.5)
            w = math.floor(w / LAYOUT_COL_WIDTH + 0.5)
            self.rects.append(Rect(name, x, y, w, h))
        self.num_cols = image.width // 10
        self.num_lines = image.height
        self.back_image = "NewsTall.png" if self.num_cols == 3 else "News.png"


def word_breaks(rand, layout):
    """The small marks drawn over the background before the articles.
    Returns their (x, y) positions. Draws once more than it returns."""
    marks = []
    pos = 0
    while True:
        pos += int((rand.random() * 0.5 + 0.3) * WORD_RUN)
        line = pos // WORD_RUN
        col = line // layout.num_lines
        if col >= layout.num_cols:
            return marks
        marks.append((col * COL_STEP + 23 + pos % WORD_RUN, (line % layout.num_lines) * LINE_STEP + ARTICLE_Y))


def face_draws(spec_text):
    """Draws for a 'Face:' picture: one per missing part in FaceSpec.fromString
    (7 parts in all), then one in Face.getDocImage."""
    return (7 - len(spec_text.split("-"))) + 1


class Plan:
    """What make() does for one day, as far as it is modelled."""

    def __init__(self, layout, articles, rand):
        self.layout = layout
        self.marks = word_breaks(rand, layout)
        self.slots = []
        for index, rect in enumerate(layout.rects):
            article = articles[index] if index < len(articles) else None
            kind = "empty box"
            draws = 0
            if article is not None and (article.title or article.sub):
                kind = "title" if article.title else "subtitle only"
                if article.title and article.stamp:
                    draws += 3                       # rotation, x, y
                if article.image and article.image.startswith("Face:"):
                    draws += face_draws(article.image[len("Face:"):])
            for _ in range(draws):
                rand.random()
            self.slots.append((rect, article, kind, draws))
        self.dropped = articles[len(layout.rects):]


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import news as N
    from rand import Rand
    from seeds import Launch, day_seeds

    master, assets = int(sys.argv[1]), sys.argv[2]
    days = [int(d) for d in sys.argv[3:]] or list(range(1, 32))
    lib, table = N.load(os.path.join(assets, "data"))
    launch = Launch(master)
    launch.load_save()          # a new game uses the second story seed
    for day in days:
        rand = Rand(day_seeds(day, launch.story_seed)["news"])
        day_news = N.DayNews(lib, table, rand, {}, day)
        plan = Plan(Layout(assets, day), day_news.articles, rand)
        print("day %d: NewsLayout%d, %d word marks" % (day, plan.layout.index, len(plan.marks)))
        for rect, article, kind, draws in plan.slots:
            text = article.text_for_bulletin if article else "-"
            print("   %-38s %-13s draws %d  %s" % (rect, kind, draws, text))


if __name__ == "__main__":
    main()
