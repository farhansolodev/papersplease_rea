"""The newspaper picture: layout rectangles, which article goes where, and
the random draws made while it is composed.

Reference for play.day.LayoutImage and play.day.DayNewsImage.make
(docs/newspaper-picture.md). Text fitting (title font or regular font, whether
the subtitle fits, where each text goes) is modelled by fit(), with text.py.
The stamp's exact position is not computed (its size after turning is not
known); the number of draws is.

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
TEXT_DROP = 2                              # kTextDrop: the first text's capitals start 2 below the top
SUBTITLE_GAP = 4                           # a constant in make: the subtitle's capitals 4 below the title

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


def round_to_nearest_line(p):
    """DayNewsImage.roundToNearestLine: always rounds UP to whole lines of 6."""
    return math.ceil(p / LINE_STEP) * LINE_STEP


class Fit:
    """How one article's text is set in its rectangle (make, step 4)."""

    def __init__(self, kind, texts, text_bottom, top):
        self.kind = kind                # "empty box", "subtitle only", "title",
        #                                 "title in regular" or "nothing shown"
        self.texts = texts              # [(role, Text, x, y)] that are drawn
        self.text_bottom = text_bottom
        self.content_height = round_to_nearest_line(text_bottom + 1 - top)

    @property
    def subtitle_shown(self):
        return any(role == "subtitle" for role, _, _, _ in self.texts)


def fit(rect, article, font_lib):
    """Sets an article's title and subtitle in a rectangle as make() does.
    font_lib is a fonts.FontLib. Returns a Fit."""
    from text import Text
    left, top, width = rect.left, rect.top, rect.width
    title_font, regular = font_lib.get("title_news"), font_lib.get("regular")
    black = 0xFF000000

    def first_text(font, string):
        # centred in the rectangle, wrapped to width - 2, capitals 2 below the top
        t = Text(font, string, fixed_width=width - 2, multi_line=True, align="CENTER", color=black)
        _, w, h, hyphenated = t.build()
        x = math.floor(left + width * 0.5 - w * 0.5)
        y = math.floor(top + TEXT_DROP) - font.ascent + font.cap_height
        return t, x, y, h, hyphenated

    if article is None or not (article.title or article.sub):
        return Fit("empty box", [], top + rect.h * LINE_STEP - 1, top)
    if not article.title:
        t, x, y, h, _ = first_text(regular, article.sub)
        return Fit("subtitle only", [("subtitle", t, x, y)], y + h, top)
    t, x, y, h, hyphenated = first_text(title_font, article.title)
    if hyphenated or h / LINE_STEP > rect.h:
        # set again in the regular font; the subtitle is never shown then
        t, x, y, h, _ = first_text(regular, article.title)
        if h / LINE_STEP <= rect.h:
            return Fit("title in regular", [("title", t, x, y)], y + h, top)
        return Fit("nothing shown", [], top, top)
    texts, bottom = [("title", t, x, y)], y + h
    if article.sub:
        # left aligned (no alignment set) at the rectangle's left edge
        s = Text(regular, article.sub, fixed_width=width - 2, multi_line=True, color=black)
        _, _, sh, _ = s.build()
        sy = math.floor(y + h + SUBTITLE_GAP) - regular.ascent + regular.cap_height
        if (sy + sh - top) / LINE_STEP <= rect.h:
            texts.append(("subtitle", s, left, sy))
            bottom = sy + sh
    return Fit("title", texts, bottom, top)


def face_draws(spec_text):
    """Draws for a 'Face:' picture: one per missing part in FaceSpec.fromString
    (7 parts in all), then one in Face.getDocImage."""
    return (7 - len(spec_text.split("-"))) + 1


class Plan:
    """What make() does for one day, as far as it is modelled."""

    def __init__(self, layout, articles, rand, font_lib=None):
        self.layout = layout
        self.marks = word_breaks(rand, layout)
        self.slots = []
        self.fits = []                               # one Fit per slot, if font_lib is given
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
            if font_lib is not None:
                self.fits.append(fit(rect, article, font_lib))
        self.dropped = articles[len(layout.rects):]


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fonts
    import news as N
    from rand import Rand
    from seeds import Launch, day_seeds

    master, assets = int(sys.argv[1]), sys.argv[2]
    days = [int(d) for d in sys.argv[3:]] or list(range(1, 32))
    lib, table = N.load(os.path.join(assets, "data"))
    font_lib = fonts.FontLib(assets)
    launch = Launch(master)
    launch.load_save()          # a new game uses the second story seed
    for day in days:
        rand = Rand(day_seeds(day, launch.story_seed)["news"])
        day_news = N.DayNews(lib, table, rand, {}, day)
        plan = Plan(Layout(assets, day), day_news.articles, rand, font_lib)
        print("day %d: NewsLayout%d, %d word marks" % (day, plan.layout.index, len(plan.marks)))
        for (rect, article, _, draws), fitted in zip(plan.slots, plan.fits):
            text = article.text_for_bulletin if article else "-"
            lost = " (subtitle not shown)" if article and article.title and article.sub \
                and not fitted.subtitle_shown else ""
            print("   %-38s %-16s draws %d  %s%s" % (rect, fitted.kind, draws, text, lost))


if __name__ == "__main__":
    main()
