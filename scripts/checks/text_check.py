"""Checks of Text.xml against what data.Lang reads and what asks for its ids.

Usage: python -I text_check.py <data dir> <stringliteral.json>
"""
import collections
import json
import os
import re
import sys

C = collections.Counter
data = sys.argv[1]
literals = [entry["value"] for entry in json.load(open(sys.argv[2], encoding="utf-8"))]
code_strings = set(literals)
problems = []

raw = open(os.path.join(data, "Text.xml"), encoding="utf-8", newline="").read()
print("-- Text.xml --")
print("  bytes:", len(raw.encode("utf-8")), "| carriage returns:", raw.count("\r"), "| comments:", raw.count("<!--"))
print("  tags:", dict(C(re.findall(r"<(\w+)", raw))), "| attributes:", dict(C(re.findall(r'\s(\w+)="', raw))))
items = re.findall(r'<item id="([^"]*)">(.*?)</item>', raw, re.S)
if len(items) != raw.count("<item"):
    problems.append("an <item> that the simple pattern here does not match")
shapes = C(re.sub(r"<t>.*?</t>", "<t>..</t>", body, flags=re.S).strip() for _, body in items)
print("  what an <item> holds:", dict(shapes))
ids = [i for i, _ in items]
print("  items:", len(ids), "| repeated ids (the first one wins):", [i for i, c in C(ids).items() if c > 1] or "none")

HTML = {"\\n": "\n", "<br>": "\n", "<br/>": "\n", "&amp;": "&", "&lt;": "<", "&gt;": ">"}


def clean(text):
    """Lang.loadFromXml: drop leading white space, then Lang.cleanHtml."""
    text = text.lstrip()
    for old, new in HTML.items():
        text = text.replace(old, new)
    return text


texts = {}
for item_id, body in items:
    inner = re.search(r"<t>(.*?)</t>", body, re.S).group(1)
    texts.setdefault(item_id, clean(inner))
used = C()
for _, body in items:
    for old in HTML:
        used[old] += body.count(old)
print("  replacements made on loading:", {k: v for k, v in used.items() if v})
others = C(re.findall(r"&\w+;", "".join(b for _, b in items)))
print("  other &...; sequences left as they are:", dict(others) or "none")
overlap = [i for i, b in items if "&amp;lt;" in b or "&amp;gt;" in b or "&amp;amp;" in b]
print("  entries where the order of the replacements would matter:", overlap or "none")
print("  entries with a real line break inside:", sum("\n" in b for _, b in items),
      "| starting with white space before cleaning:", sum(re.search(r"<t>\s", b) is not None for _, b in items),
      "| ending with white space:", sum(re.search(r"\s</t>", b) is not None for _, b in items))
print("  empty entries:", [i for i, t in texts.items() if t == ""] or "none")

print("\n-- placeholders --")
numbered = {i: sorted(set(re.findall(r"\$\d", t))) for i, t in texts.items() if re.search(r"\$\d", t)}
named = {i: sorted(set(re.findall(r"\$[a-z]\w*", t))) for i, t in texts.items() if re.search(r"\$[a-z]", t)}
print("  entries with $0..$9: %d | highest number used: %s" % (
    len(numbered), max(p for ps in numbered.values() for p in ps)))
print("  entries with named placeholders:", named)
gaps = [i for i, ps in numbered.items() if ps != ["$%d" % n for n in range(len(ps))]]
print("  numbered entries that skip a number:", gaps or "none")

print("\n-- the long date --")
month_ids = ["month_%d" % n for n in range(1, 13)]
day_ids = ["day_%d" % n for n in range(1, 32)]
print("  date_verbose:", repr(texts.get("date_verbose")), "| month_1..12 present:", all(m in texts for m in month_ids),
      "| day_1..31 present:", all(d in texts for d in day_ids), "| month_0 present:", "month_0" in texts)
for needed in ["date_verbose"] + month_ids + day_ids:
    if needed not in texts:
        problems.append("missing: " + needed)
print("  example, 23 November 1982:", texts["date_verbose"].replace("$month", texts["month_11"])
      .replace("$day", texts["day_23"]).replace("$year", "1982"))

print("\n-- who asks for each id --")
prefixes = sorted({s for s in code_strings if s.endswith("_") and any(i.startswith(s) and i != s for i in ids)})
other_files = ""
for name in sorted(os.listdir(data)):
    if name not in ("Text.xml",) and name.lower().endswith((".xml", ".txt", ".csv")):
        other_files += open(os.path.join(data, name), encoding="utf-8", errors="replace").read()
by = C()
unasked = []
for item_id in texts:
    if item_id in code_strings:
        by["the whole id is in the code"] += 1
    elif any(item_id.startswith(p) for p in prefixes):
        by["a prefix of it is in the code (the rest is built)"] += 1
    elif re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(item_id), other_files):
        by["named in another data file"] += 1
    else:
        unasked.append(item_id)
print("  ", dict(by))
print("  prefixes in the code that ids are built from:", prefixes)
print("  ids nothing found asks for:", unasked or "none")
asked_missing = sorted(s for s in code_strings if re.fullmatch(r"(budget|family|menu|citation|env|booth|night|confirm|load|stats|title|settings|endless)_[a-z0-9_]+", s)
                       and s not in texts and not s.endswith("_"))
print("  code strings that look like text ids but are not in Text.xml:", asked_missing or "none")

print("\nproblems:", sorted(set(problems)) or "none")
