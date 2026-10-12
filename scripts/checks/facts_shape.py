import sys, re, collections
import xml.etree.ElementTree as ET
raw = open(sys.argv[1], encoding="utf-8").read()
print("raw '&' not starting an entity:", len(re.findall(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", raw)), "| entities used:", dict(collections.Counter(re.findall(r"&(\w+|#\w+);", raw))))
print("raw '<' inside attribute values:", len(re.findall(r'="[^"]*<[^"]*"', raw)), "| comments:", raw.count("<!--"), "| CDATA:", raw.count("<![CDATA["))
fixed = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", raw)
root = ET.fromstring(fixed)
print("root:", root.tag, dict(root.attrib))
tags = collections.Counter(); attrs = collections.defaultdict(collections.Counter)
parents = collections.defaultdict(collections.Counter); text = collections.Counter()
def walk(e, parent):
    tags[e.tag] += 1; parents[e.tag][parent] += 1
    for a in e.attrib: attrs[e.tag][a] += 1
    if e.text and e.text.strip(): text[e.tag] += 1
    for c in e: walk(c, e.tag)
for c in root: walk(c, root.tag)
for t, n in tags.most_common():
    print(f"<{t}> x{n}  inside {dict(parents[t])}  text-bearing {text[t]}")
    print("     attrs:", ", ".join(f"{a}({c})" for a, c in attrs[t].most_common()))
