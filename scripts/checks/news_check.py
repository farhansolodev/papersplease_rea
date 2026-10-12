"""Checks of News.txt and scripts/reference/news.py against the data files.

Usage: python -I news_check.py <reference dir> <assets dir>

<assets dir> is extracted/art/assets.
"""
import collections
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import news as N
import tabtree
import travspec as T
from rand import Rand
from seeds import Launch, day_seeds

C = collections.Counter
assets = sys.argv[2]
data = os.path.join(assets, "data")
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
problems = []

lib, table = N.load(data)
entries = lib.root.nodes
ids = [e.params[0] for e in entries]
print("-- News.txt --")
print("  entries:", len(ids), "| repeated ids:", [i for i, n in C(ids).items() if n > 1] or "none")
print("  entries with more than one word on the id line:", [e.params for e in entries if len(e.params) > 1] or "none")
kinds = C()
depth_kinds = C()
for e in entries:
    for depth, node in tabtree.walk(e):
        depth_kinds[(depth, node.params[0])] += 1
        if depth > 1:
            problems.append("a line nested deeper than an article's detail: %r" % node.params)
print("  article lines by first sign:", {k[1]: v for k, v in depth_kinds.items() if k[0] == 0})
print("  detail lines by first sign:", {k[1]: v for k, v in depth_kinds.items() if k[0] == 1})
for (depth, sign), count in depth_kinds.items():
    if (depth == 0 and sign not in "*-") or (depth == 1 and sign not in "-@=$"):
        problems.append("a sign the code ignores: %r at depth %d" % (sign, depth))
articles = [(e.params[0], a) for e in entries for a in lib.get_articles(e.params[0])]
print("  articles:", len(articles), "| by score:", dict(sorted(C(a.sort_score for _, a in articles).items())))
print("  entries by number of articles:", dict(sorted(C(len(e.nodes) for e in entries).items())))
neither = [i for i, a in articles if a.title is None and a.sub is None]
print("  articles with neither a title nor a subtitle:", neither or "none")
detail_words = C(len(n.params) for e in entries for d, n in tabtree.walk(e) if d == 1 and n.params[0] in "@=$")
print("  words on @, = and $ lines (sign included):", dict(detail_words))

print("\n-- pictures, stamps and fact names --")
facts_xml = read("Facts.xml")
for news_id, a in articles:
    if a.image is not None:
        ok = re.fullmatch(r"Face:[MF](-\d+){4}", a.image) is not None
        print("  picture %-18s on %-22s %s" % (a.image, news_id, "" if ok else "UNEXPECTED FORM"))
        if not ok:
            problems.append("picture value of an unexpected form: " + a.image)
stamps = C(a.stamp for _, a in articles if a.stamp is not None)
for stamp, count in stamps.items():
    exists = os.path.exists(os.path.join(assets, stamp))
    print("  stamp %s on %d articles, file present: %s" % (stamp, count, exists))
    if not exists:
        problems.append("stamp file missing: " + stamp)
travelers_text = read("Travelers.txt")
for news_id, a in articles:
    if a.fact_id is not None:
        print("  fact name %-8s on %-22s defined in Facts.xml: %-5s uses of Bulletin/%s in Travelers.txt: %d" % (
            a.fact_id, news_id, ('id="%s"' % a.fact_id) in facts_xml, a.fact_id,
            travelers_text.count("Bulletin/" + a.fact_id)))
print("  Bulletin news facts in Facts.xml:", sorted(set(re.findall(r'id="(News\w*)"', facts_xml))))

print("\n-- who names each entry --")
day_ids = {}
for col in table.col_ids[1:]:
    for news_id in T.split_and_trim(table.cell(col, "NEWS"), "\n"):
        day_ids.setdefault(news_id, []).append(col)
traveler_ids = C(m.group(1) for m in re.finditer(r"^\s*@\s+News\s+(\S+)", tabtree.strip_block_comments(travelers_text), re.M)
                 if "#" not in m.group(0))
print("  named in Days.csv: %d | named by `News` commands in Travelers.txt: %d" % (len(day_ids), len(traveler_ids)))
for name in list(day_ids) + list(traveler_ids):
    if name not in ids:
        problems.append("news id with no entry in News.txt: " + name)
both = sorted(set(day_ids) & set(traveler_ids))
print("  named by both:", both or "none")
fillers = ["RANDOM_" + k for k in N.FILLER_KINDS]
unused = [i for i in ids if i not in day_ids and i not in traveler_ids and i not in fillers]
print("  entries nothing names:", unused or "none")
print("  filler entries and their choices:", {f: len(lib.get_articles(f)) for f in fillers})
for f in fillers:
    if not lib.get_articles(f):
        problems.append("filler entry with no article: " + f)

print("\n-- the sort --")
r = Rand(7)
unstable = 0
for trial in range(2000):
    items = [(int(r.random() * 4), k) for k in range(int(r.random() * 9) + 1)]
    out = list(items)
    N.haxe_sort(out, lambda a, b: b[0] - a[0])
    if sorted(out) != sorted(items) or any(out[k][0] < out[k + 1][0] for k in range(len(out) - 1)):
        problems.append("the sort lost an item or left the list out of order")
    unstable += out != sorted(items, key=lambda x: -x[0])
print("  2000 random lists: all end up highest score first; %d of them not in a stable sort's order" % unstable)
pair = ["first", "second"]
N.haxe_sort(pair, lambda a, b: 0)
print("  two equal items [first, second] come out as:", pair)

print("\n-- every story day, 200 master seeds, no traveler news --")
days = [int(c) for c in table.col_ids[1:] if c.isdigit() and int(c) <= 31]
shape = C()
filler_seen = C()
draws = C()
first_headline = collections.defaultdict(C)


class Counting(Rand):
    def __init__(self, seed):
        self.count = 0
        super().__init__(seed)
        self.count = 0

    def next_int(self):
        self.count += 1
        return super().next_int()

    def next_float(self):
        return self.next_int() / 2147483647.0

    random = next_float


for master in range(1, 201):
    launch = Launch(master)
    for day in days:
        rand = Counting(day_seeds(day, launch.story_seed)["news"])
        news = N.DayNews(lib, table, rand, {}, day)
        shape[(len(news.news_ids), len(news.articles) - len(news.fillers), len(news.fillers))] += 1
        draws[(len(news.fillers), rand.count)] += 1
        for a in news.fillers:
            filler_seen[a.text_for_bulletin] += 1
        first_headline[day][news.articles[0].text_for_bulletin] += 1
        scores = [a.sort_score for a in news.articles[:len(news.articles) - len(news.fillers)]]
        if scores != sorted(scores, reverse=True):
            problems.append("day %d: articles not highest score first" % day)
        if sorted(news.fact_id_remap) != ["News%d" % i for i in range(len(news.articles))]:
            problems.append("day %d: remap names are not News0.." % day)
        if len(set(news.fact_id_remap.values())) != len(news.articles):
            problems.append("day %d: two articles share a fact name" % day)
print("  (ids, their articles, fillers) -> day-seeds:", dict(sorted(shape.items())))
print("  (fillers, draws from the news generator):", dict(sorted(draws.items())))
print("  fillers chosen:", dict(filler_seen))
print("  most articles on one day:", max(k[1] + k[2] for k in shape))
changing = {d: dict(c) for d, c in first_headline.items() if len(c) > 1}
print("  days whose first article depends on the seed:", changing or "none")
swapped = [d for d in days
           if len(lib.get_articles(table.cell(d, "NEWS").strip())) == 2
           and N.DayNews(lib, table, Rand(1), {}, d).articles[0].title
           != lib.get_articles(table.cell(d, "NEWS").strip())[0].title]
print("  days whose two articles come out in the opposite order to News.txt:", swapped)

print("\n-- traveler news --")
facts = {}
N.add_traveler_news(facts, 5, "KILLERATHLETE_DETAINED")
N.add_traveler_news(facts, 5, "KILLERATHLETE_DETAINED")
N.add_traveler_news(facts, 5, "GENERIC_BOMBER")
print("  stored after three commands on day 5 (one repeated):", facts)
for day in (5, 6, 7):
    news = N.DayNews(lib, table, Rand(1), facts, day)
    print("  day %d ids: %s -> %s" % (day, news.news_ids, [a.text_for_bulletin for a in news.articles]))
if N.DayNews(lib, table, Rand(1), facts, 6).news_ids != ["WORKPERMIT_FIRST", "KILLERATHLETE_DETAINED", "GENERIC_BOMBER"]:
    problems.append("traveler news of day 5 did not reach day 6")

print("\nproblems:", sorted(set(problems)) or "none")
