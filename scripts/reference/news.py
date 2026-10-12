"""Reference implementation of the day's news: data.NewsArticleLib,
data.NewsArticle and play.day.DayNews (docs/news-txt-format.md).

It decides which headlines a day's newspaper carries and in what order, and
the "News0, News1, ..." names the bulletin uses for them. Drawing the
newspaper is not covered.

Run as a script to list every day's headlines for one master seed:

    python -I scripts/reference/news.py <master seed> <data dir>

where <data dir> is extracted/art/assets/data.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402
import travspec as T  # noqa: E402
from cyclers import make_shuffled  # noqa: E402
from rand import Rand  # noqa: E402
from seeds import Launch, day_seeds  # noqa: E402

FILLER_KINDS = ["WEATHER", "SPORTS", "POLITICS", "ENTERTAINMENT"]
WANTED_NEWS_IDS = 3


class Article:
    """One headline. `title` is a `*` line, `sub` a `-` line; the lines under
    it can add a subtitle (-), a picture (@), a fact name (=) and a stamp ($)."""

    def __init__(self, node):
        self.title = self.sub = self.image = self.stamp = self.fact_id = None
        if node.params[0] == "*":
            self.title = " ".join(node.params[1:])
        elif node.params[0] == "-":
            self.sub = " ".join(node.params[1:])
        for child in node.nodes:
            kind = child.params[0]
            if kind == "-":
                self.sub = " ".join(child.params[1:])
            elif kind == "@":
                self.image = child.params[1]
            elif kind == "=":
                self.fact_id = child.params[1]
            elif kind == "$":
                self.stamp = child.params[1]
        self.sort_score = ((1000 if self.fact_id is not None else 0)
                           + (100 if self.title is not None else 0)
                           + (10 if self.sub is not None else 0)
                           + (1 if self.image is not None else 0))

    @property
    def text_for_bulletin(self):
        return self.title if self.title is not None else self.sub


def compare_strings(a, b):
    """StringUtil.compareStrings: by character code; -1, 0 or 1."""
    return -1 if a < b else (1 if a > b else 0)


def compare(a, b):
    """NewsArticle.compare: higher score first; two named articles with the
    same score go by name."""
    if a.sort_score == b.sort_score and a.fact_id is not None and b.fact_id is not None:
        return compare_strings(a.fact_id, b.fact_id)
    return b.sort_score - a.sort_score


def haxe_sort(items, f):
    """Array.sort as compiled in this game: a quicksort around the middle
    item. It does not keep equal items in their original order."""
    def quicksort(lo, hi):
        while True:
            pivot = items[(lo + hi) >> 1]
            i, j = lo, hi
            while i <= j:
                while i < hi and int(f(items[i], pivot)) < 0:
                    i += 1
                while j > lo and int(f(items[j], pivot)) > 0:
                    j -= 1
                if j < i:
                    break
                items[i], items[j] = items[j], items[i]
                i += 1
                j -= 1
            if lo < j:
                quicksort(lo, j)
            if hi <= i:
                return
            lo = i

    if items:
        quicksort(0, len(items) - 1)


class NewsLib:
    def __init__(self, news_text):
        self.root = tabtree.parse(news_text)

    def get_articles(self, news_id):
        """New article objects each time; an unknown id gives none."""
        node = self.root.find(news_id)
        return [Article(child) for child in node.nodes] if node is not None else []


def traveler_news_path(day_id):
    """DayNews.getStorageFactPath: where a day's traveler-triggered news ids
    are kept in the saved story, separated by ';'."""
    return "Game/Day%dTravelerNews" % day_id


def add_traveler_news(story_facts, day_id, news_id):
    """Day.addTravelerNews (the `News id` command of a traveler script)."""
    path = traveler_news_path(day_id)
    ids = [i for i in story_facts.get(path, "").split(";")] if story_facts.get(path) else []
    if news_id not in ids:
        ids.append(news_id)
    story_facts[path] = ";".join(ids)


class DayNews:
    def __init__(self, lib, table, rand, story_facts, day_id):
        self.day_id = day_id
        ids = T.split_and_trim(table.cell(day_id, "NEWS"), "\n")
        stored = story_facts.get(traveler_news_path(day_id - 1))     # the day BEFORE
        ids = ids + (stored.split(";") if stored else [])
        self.news_ids = ids
        self.articles = []
        for news_id in ids:
            self.articles += lib.get_articles(news_id)
        haxe_sort(self.articles, compare)
        self.fillers = []
        missing = WANTED_NEWS_IDS - len(ids)
        if missing > 0:
            order = make_shuffled(rand, len(FILLER_KINDS))
            for i in range(missing):
                choices = lib.get_articles("RANDOM_" + FILLER_KINDS[order[i]])
                self.fillers.append(choices[int(len(choices) * rand.random())])
            haxe_sort(self.fillers, compare)
            self.articles += self.fillers
        self.fact_id_remap = {}
        defaults = 0
        for index, article in enumerate(self.articles):
            if article.fact_id is None:
                article.fact_id = "NewsDefault%d" % defaults
                defaults += 1
            self.fact_id_remap["News%d" % index] = article.fact_id


def load(data_dir):
    read = lambda name: open(os.path.join(data_dir, name), encoding="utf-8", newline="").read()
    table, _, _ = T.load(data_dir)
    return NewsLib(read("News.txt")), table


def main():
    master, data_dir = int(sys.argv[1]), sys.argv[2]
    lib, table = load(data_dir)
    launch = Launch(master)
    print("master seed %d; no traveler-triggered news" % master)
    for col in table.col_ids[1:]:
        if not col.isdigit() or int(col) > 31:
            continue
        day = int(col)
        news = DayNews(lib, table, Rand(day_seeds(day, launch.story_seed)["news"]), {}, day)
        print("day %2d  from Days.csv: %s" % (day, ", ".join(news.news_ids) or "-"))
        for index, article in enumerate(news.articles):
            extras = " ".join(filter(None, [
                article.image and "[picture %s]" % article.image,
                article.stamp and "[stamp %s]" % article.stamp]))
            print("    News%d = %-13s %s%s %s" % (
                index, article.fact_id, article.title or "",
                (" / " if article.title and article.sub else "") + (article.sub or ""), extras))


if __name__ == "__main__":
    main()
