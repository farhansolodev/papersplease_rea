"""Looks at the three data files the game's code never asks for by name:
Threads.txt, TravelerGraph.txt and Version.txt.

Usage: python -I notes_files_check.py <data dir> <stringliteral.json>
"""
import collections
import json
import os
import re
import sys

data = sys.argv[1]
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
literals = {entry["value"] for entry in json.load(open(sys.argv[2], encoding="utf-8"))}

for name in ("Threads.txt", "TravelerGraph.txt", "Version.txt"):
    hits = sorted(v for v in literals if name.lower() in v.lower())
    print("%s: %d bytes; code strings containing the name: %s" % (
        name, os.path.getsize(os.path.join(data, name)), hits or "none"))

print("\nVersion.txt says: %r" % read("Version.txt").strip())

travelers = set(re.findall(r"^([A-Z0-9_]+)\b", read("Travelers.txt"), re.M))
news = set(re.findall(r"^([A-Z0-9_]+)\b", read("News.txt"), re.M))

threads = read("Threads.txt")
marks = collections.Counter()
known = collections.Counter()
for word in re.findall(r"[@^\[*#]?[A-Za-z0-9_/\-]+\]?", threads):
    if word.startswith("@"):
        marks["@ (news)"] += 1
        known["@ in News.txt" if word[1:] in news else "@ not in News.txt"] += 1
    elif word.startswith("^"):
        marks["^"] += 1
    elif word.startswith("["):
        marks["[...]"] += 1
    elif word.startswith(("*", "#")):
        marks["section " + word[0]] += 1
    elif re.fullmatch(r"[A-Z0-9_]+", word):
        marks["plain upper-case word"] += 1
        known["plain word is a traveler id" if word in travelers else "plain word is not a traveler id"] += 1
print("\nThreads.txt: %d lines; kinds of word: %s" % (threads.count("\n") + 1, dict(marks)))
print("  ", dict(known))

graph = read("TravelerGraph.txt")
first_words = collections.Counter(line.strip().split(" ")[0] for line in graph.split("\n") if line.strip())
print("\nTravelerGraph.txt: %d lines" % (graph.count("\n") + 1))
print("   most common first words:", dict(first_words.most_common(12)))
graphs = re.findall(r"^Graph (\S+)", graph, re.M)
print("   'Graph' blocks: %d; named after a traveler id: %d" % (len(graphs), sum(1 for g in graphs if g in travelers)))
arrows = re.findall(r"^\s*> (\S+)", graph, re.M)
print("   '>' lines: %d; naming a traveler id: %d" % (len(arrows), sum(1 for a in arrows if a in travelers)))
