"""Checks of Sounds.xml against what data.SoundDef reads and what asks for sounds.

Usage: python -I sounds_check.py <reference dir> <data dir> <stringliteral.json>
"""
import collections
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
from cyclers import ShuffledSequence
from rand import Rand

C = collections.Counter
data = sys.argv[2]
code_strings = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}
problems = []

raw = open(os.path.join(data, "Sounds.xml"), encoding="utf-8", newline="").read()
root = ET.fromstring(raw)
sounds = root.findall("sound")
print("-- Sounds.xml --")
print("  tags:", dict(C(e.tag for e in root.iter())), "| comments:", raw.count("<!--"))
print("  attributes:", dict(C(a for s in sounds for a in s.attrib)))
for attribute in {a for s in sounds for a in s.attrib} - {"id", "file", "loop", "vol", "fade", "room"}:
    problems.append("attribute the code does not read: " + attribute)
ids = [s.get("id") for s in sounds]
repeats = [i for i, c in C(ids).items() if c > 1]
print("  sounds:", len(ids), "| repeated ids (the game stops on one):", repeats or "none")
problems += ["repeated id: " + i for i in repeats]


class Def:
    """data.SoundDef."""

    def __init__(self, rand, node):
        self.id = node.get("id")
        self.files = node.get("file").split(" ") if node.get("file") is not None else [self.id + ".wav"]
        self.loop = node.get("loop") == "true"
        self.vol = float(node.get("vol")) if node.get("vol") is not None else 1.0
        self.has_fade = node.get("fade") is not None
        self.fade = float(node.get("fade")) if self.has_fade else 3.0
        self.room = node.get("room")
        self.rand = rand
        # More than two recordings: a shuffled order over THREE of them,
        # whatever their number.
        self.sequence = ShuffledSequence(3, rand.next_int()) if len(self.files) > 2 else None

    def filename(self):
        if len(self.files) == 1:
            return self.files[0]
        if self.sequence is None:
            return self.files[int(len(self.files) * self.rand.random())]
        return self.files[self.sequence.next()]


rand = Rand(23)
defs = [Def(rand, s) for s in sounds]
print("  looping:", [d.id for d in defs if d.loop], "| with a fade:", {d.id: d.fade for d in defs if d.has_fade},
      "| tied to a room:", {d.id: d.room for d in defs if d.room})
print("  loop values:", dict(C(s.get("loop") for s in sounds if s.get("loop") is not None)))
print("  volumes other than 1:", len([d for d in defs if d.vol != 1.0]),
      "| lowest %.3f (%s)" % min((d.vol, d.id) for d in defs))
for s in sounds:
    for name in ("vol", "fade"):
        if s.get(name) is not None and not re.fullmatch(r"\d+(\.\d+)?", s.get(name)):
            problems.append("%s is not a plain number: %s" % (name, s.get(name)))
by_count = C(len(d.files) for d in defs)
print("  sounds by number of recordings:", dict(sorted(by_count.items())))
borrowed = {d.id: d.files for d in defs if len(d.files) == 1 and d.files[0] != d.id + ".wav"}
print("  sounds that use another sound's recording:", borrowed)
all_files = sorted({f for d in defs for f in d.files})
print("  distinct recordings named:", len(all_files), "| not ending in .wav:", [f for f in all_files if not f.endswith(".wav")] or "none")
shared = {f: [d.id for d in defs if f in d.files] for f in all_files}
print("  recordings used by more than one sound:", {f: who for f, who in shared.items() if len(who) > 1})

print("\n-- which recording plays --")
for d in defs:
    if len(d.files) > 1:
        played = [d.filename() for _ in range(600)]
        counts = C(played)
        never = [f for f in d.files if f not in counts]
        repeats_in_a_row = sum(played[i] == played[i + 1] for i in range(len(played) - 1))
        print("  %-16s %d recordings | never played: %s | same one twice running: %d of 599" % (
            d.id, len(d.files), never or "none", repeats_in_a_row))
        if len(d.files) <= 3 and never:
            problems.append(d.id + ": a recording never plays")

print("\n-- who asks for each sound --")
others = ""
for name in sorted(os.listdir(data)):
    if name != "Sounds.xml" and name.lower().endswith((".xml", ".txt", ".csv")):
        others += open(os.path.join(data, name), encoding="utf-8", errors="replace").read()
by = C()
unasked = []
prefixes = sorted({s for s in code_strings if s.endswith("-") and any(i.startswith(s) for i in ids)})
for sound_id in ids:
    if sound_id in code_strings:
        by["the whole id is in the code"] += 1
    elif re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(sound_id), others):
        by["named in another data file"] += 1
    elif any(sound_id.startswith(p) for p in prefixes):
        by["a prefix of it is in the code"] += 1
    else:
        unasked.append(sound_id)
print("  ", dict(by), "| prefixes:", prefixes)
print("  sounds nothing found asks for:", unasked or "none")
in_data = sorted({m for m in re.findall(r'sound="([^"]+)"', others)})
print("  sound= values in other data files:", in_data, "| all defined:", all(m in ids for m in in_data))
problems += ["sound named in a data file but not defined: " + m for m in in_data if m not in ids]

print("\nproblems:", sorted(set(problems)) or "none")
