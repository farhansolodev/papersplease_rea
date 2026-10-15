"""Which real newspaper headlines fall back to the regular font, lose their
subtitle or are not shown at all (newsimage.fit, which lays the texts out
with text.py; docs/newspaper-picture.md).

Usage: python -I news_fit_check.py <reference dir> <assets dir> [master seeds]

Three parts:
1. Every article of News.txt in every rectangle of the six desktop layouts.
2. The real days 1 to 31 with no traveler news, over the given number of
   master seeds (default 200): which article lands where, and what happens.
3. Traveler news: each id named by a `News` command, added to the paper of
   the day after each day whose TRAVELERS cell names the entry holding the
   command (alone, and with every other traveler id of the same day).
Needs Pillow.
"""
import collections
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import fonts
import news as N
import newsimage as NI
import tabtree
from rand import Rand
from seeds import Launch, day_seeds

assets = sys.argv[2]
seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 200
data = os.path.join(assets, "data")
font_lib = fonts.FontLib(assets)
lib, table = N.load(data)
layouts = [NI.Layout(assets, i) for i in range(6)]
problems = []


def label(article):
    if article.title and article.sub:
        return "%s / %s" % (article.title, article.sub)
    return article.title or article.sub


def outcome(f, article):
    """A short word for what happened, or None when the article is shown whole."""
    if f.kind in ("title in regular", "nothing shown"):
        return f.kind + (" (subtitle lost)" if article.sub else "")
    if f.kind == "title" and article.sub and not f.subtitle_shown:
        return "subtitle lost"
    return None


# ---- 1. every article, every rectangle ----
print("-- 1. every article of News.txt in every rectangle of the six layouts --")
articles = []
for node in lib.root.nodes:
    for a in lib.get_articles(node.params[0]):
        articles.append((node.params[0], a))
sizes = sorted({(r.w, r.h) for lay in layouts for r in lay.rects})
print("  %d articles; rectangle sizes (columns, lines): %s" % (len(articles), sizes))
by_size = collections.defaultdict(list)
for news_id, a in articles:
    for w, h in sizes:
        rect = NI.Rect("x", 0, 0, w, h)
        f = NI.fit(rect, a, font_lib)
        what = outcome(f, a)
        if what:
            by_size[(news_id, label(a))].append("%dx%d %s" % (w, h, what))
        # the code's own checks, repeated on the result
        for role, t, x, y in f.texts:
            _, tw, th, _ = t.build()
            if role == "title" and f.kind == "title" and th / 6 > h:
                problems.append("title taller than its rectangle kept in title_news")
print("  articles that are not shown whole in at least one size (size: what happens):")
for (news_id, text), notes in sorted(by_size.items()):
    print("    %-26s %s" % (news_id, text))
    print("        " + "; ".join(notes))

# ---- 2. the real days, no traveler news ----
print("\n-- 2. days 1 to 31, %d master seeds, no traveler news --" % seeds)
seen = collections.Counter()
days = [int(c) for c in table.col_ids[1:] if c.isdigit() and int(c) <= 31]


def run_day(day, story_seed, facts, counter, tag=""):
    rand = Rand(day_seeds(day, story_seed)["news"])
    day_news = N.DayNews(lib, table, rand, facts, day)
    plan = NI.Plan(NI.Layout(assets, day), day_news.articles, rand, font_lib)
    for index, ((rect, article, _, _), f) in enumerate(zip(plan.slots, plan.fits)):
        if article is None:
            continue
        counter[(day, tag, index, rect.w, rect.h, label(article), f.kind,
                 outcome(f, article) or "shown whole")] += 1


for master in range(1, seeds + 1):
    launch = Launch(master)
    launch.load_save()
    for day in days:
        run_day(day, launch.story_seed, {}, seen)
whole = collections.Counter()
for (day, _, index, w, h, text, kind, what), n in sorted(seen.items()):
    whole[what] += n
    if what != "shown whole":
        print("  day %2d  rectangle %d (%dx%d)  %-15s %s  [%d of %d seeds]" % (
            day, index, w, h, what, text, n, seeds))
print("  outcomes over all placements:", dict(whole))
always = sorted({(d, t) for (d, _, _, _, _, t, _, w) in seen if w == "shown whole"} &
                {(d, t) for (d, _, _, _, _, t, _, w) in seen if w != "shown whole"})
print("  (day, article) shown whole on some seeds and not on others:", always or "none")

# ---- 3. traveler news ----
print("\n-- 3. traveler news (the paper of the day after) --")
travelers = open(os.path.join(data, "Travelers.txt"), encoding="utf-8", newline="").read()
travelers = tabtree.strip_block_comments(travelers)
owner, by_entry, includes = None, collections.defaultdict(list), collections.defaultdict(set)
for line in travelers.split("\n"):
    if line.lstrip().startswith("#"):
        continue
    if re.match(r"^[A-Za-z0-9_]", line):
        owner = line.split()[0]
    m = re.match(r"^\s*@\s+News\s+(\S+)", line)
    if m and m.group(1) not in by_entry[owner]:
        by_entry[owner].append(m.group(1))
    m = re.match(r"^\s*INCLUDE\s+(\S+)", line)
    if m:
        includes[owner].add(m.group(1))


def reach(entry, seen_entries=None):
    """The entry and every entry it INCLUDEs, all the way down."""
    seen_entries = seen_entries if seen_entries is not None else set()
    if entry not in seen_entries:
        seen_entries.add(entry)
        for e in includes[entry]:
            reach(e, seen_entries)
    return seen_entries


# day -> {entry with News commands: its ids}; an entry is reached from a name in
# the day's TRAVELERS or FILL cell, directly or through INCLUDE
on_day = collections.defaultdict(dict)
for d in days:
    names = N.T.split_and_trim(table.cell(d, "TRAVELERS"), "\n") + N.T.split_and_trim(table.cell(d, "FILL"), "\n")
    for name in names:
        for entry in reach(name):
            if by_entry.get(entry):
                on_day[d][entry] = by_entry[entry]
for entry, ids in by_entry.items():
    if ids:
        hits = [d for d in days if entry in on_day[d]]
        print("  %-22s %s  reached on days %s" % (entry, ids, hits or "none"))
# every combination of at most one id per entry on the same day (one entry's
# ids are alternatives, chosen by the player's decision)
combos = {}
for d, entries in on_day.items():
    if d + 1 > 31:
        continue
    choices = [[None] + ids for ids in entries.values()]
    found = [[]]
    for options in choices:
        found = [c + [o] for c in found for o in options]
    combos[d] = [[i for i in c if i] for c in found if any(c)]
trav_seen = collections.Counter()
for master in range(1, seeds + 1):
    launch = Launch(master)
    launch.load_save()
    for d, lists in sorted(combos.items()):
        for ids in lists:
            facts = {}
            for i in ids:
                N.add_traveler_news(facts, d, i)
            run_day(d + 1, launch.story_seed, facts, trav_seen, "+" + "+".join(ids))
trav_whole = collections.Counter()
for (day, tag, index, w, h, text, kind, what), n in sorted(trav_seen.items()):
    trav_whole[what] += n
    if what != "shown whole":
        print("  day %2d %-50s rectangle %d (%dx%d)  %-15s %s  [%d of %d seeds]" % (
            day, tag, index, w, h, what, text, n, seeds))
print("  outcomes over all placements:", dict(trav_whole))

print("\nproblems:", sorted(set(problems)) or "none")
