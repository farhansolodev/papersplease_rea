import sys, re, collections
import xml.etree.ElementTree as ET
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read()); tabtree.expand_params(root)
raw = open(sys.argv[3], encoding="utf-8").read()
facts = ET.fromstring(re.sub(r"&(?!amp;)", "&amp;", raw))
nations = [n.get("name") for n in facts.find("nations")]
paths = set()
for d in facts.findall("paper"):
    for f in d.findall("fact"):
        for i in ([f.get("id").replace("[NATIONS]", n) for n in nations] if "[NATIONS]" in f.get("id") else [f.get("id")]):
            paths.add(d.get("id") + ("/" + i if i else ""))
errors = [n for n in root.nodes if not n.params[0].startswith("*")]
inval = C(ch.params[1] for e in errors for ch in e.nodes if ch.params[0] == "!")
tilde = [k for k in inval if k.startswith("~")]
print("invalidated paths:", len(inval), "| starting with ~:", len(tilde), "| ~ paths known once ~ is removed:", sum(1 for k in tilde if k[1:] in paths))
print("other unknown paths:", sorted(k for k in inval if not k.startswith("~") and k not in paths))
print("first characters of invalidated paths:", dict(C(k[0] if not k[0].isalnum() else "letter" for k in inval)))
eq = [(e.params[0], ch.params[1:]) for e in errors for ch in e.nodes if ch.params[0] == "="]
print("'=' lines directly under an error:", eq)
print("errors with no '!' line:", [e.params[0] for e in errors if not any(ch.params[0] == "!" for ch in e.nodes)])
print("errors with no requirement:", [e.params[0] for e in errors if not any(ch.params[0] == "\\" for ch in e.nodes)][:10])
print("<rare> in any id:", sum(1 for e in errors if "<rare>" in e.params[0]), "| ids with tags, by first tag:", dict(C((re.findall(r"<[^>]*>", e.params[0]) or ["(none)"])[0] for e in errors)))
print("ids without any tag:", [e.params[0] for e in errors if "<" not in e.params[0]])
trav = tabtree.parse(open(sys.argv[4], encoding="utf-8", newline="").read())
pats = C()
for _, n in tabtree.walk(trav):
    if n.params[0] == "=" and len(n.params) > 2 and n.params[1] == "error":
        for v in n.params[2:]: pats[v.rsplit(":", 1)[0] if re.search(r":[\d.]+$", v) else v] += 1
    if n.params[0] == "x" : pass
print("distinct values given to 'error' in Travelers.txt:", len(pats), "| most common:", pats.most_common(12))
ids = [e.params[0] for e in errors if not e.params[0].startswith("ALWAYS")]
nomatch = [p for p in pats if not any(re.search(p, i, re.I) for i in ids)]
print("'error' values that match no error id as a pattern:", nomatch)
