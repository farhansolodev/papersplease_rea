"""Cross-check of docs/speech.md against the real data files.

Usage: python -I speech_check.py <reference dir> Speeches.txt Travelers.txt Errors.txt Facts.xml
"""
import sys, re, collections
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import tabtree

C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())

responses = {}
dupes = []
says = []
for node in root.nodes:
    p = node.params
    rid = p[0]
    if rid in responses:
        dupes.append(rid)
    fact = p[1] if len(p) > 1 else None
    entry = []
    for child in node.nodes:
        q = list(child.params)
        when = expr = None
        i = 0
        if q[0].startswith("="):
            when = q[0][1:]; i = 1
        if i < len(q) and q[i].startswith("?"):
            expr = q[i][1:]; i += 1
        text = " ".join(q[i:])
        entry.append((when, expr, text))
        says.append((rid, fact, when, expr, text, len(child.nodes)))
    responses[rid] = (fact, entry, len(p))
print("responses:", len(root.nodes), "| distinct ids:", len(responses), "| repeated ids (later one wins):", dupes)
print("response header shapes (token count):", dict(C(v[2] for v in responses.values())))
print("responses with a fact path:", sum(1 for v in responses.values() if v[0]))
print("say lines:", len(says), "| with =when:", sum(1 for s in says if s[2] is not None),
      "| with ?expression:", sum(1 for s in says if s[3] is not None),
      "| say lines that have children (ignored):", sum(1 for s in says if s[5]))
print("say lines whose text is empty:", [(s[0], s[2]) for s in says if not s[4]][:5])
print("responses with no say lines:", [k for k, v in responses.items() if not v[1]][:10])

texts = [s[4] for s in says]
print("\n-- features inside say texts --")
print("  ';' alternatives:", sum(";" in t for t in texts), "| starts '@':", sum(t.startswith("@") for t in texts),
      "| ends '~':", sum(t.endswith("~") for t in texts))
print("  [m]:", sum("[m]" in t for t in texts), "[f]:", sum("[f]" in t for t in texts), "[x]:", sum("[x]" in t for t in texts))
print("  ${path}:", sum("${" in t for t in texts), "e.g.", sorted({m for t in texts for m in re.findall(r"\$\{(.*?)\}", t)})[:8])
refs = [w[1:] for t in texts for w in t.split(" ") if w.startswith("$") and not w.startswith("${")]
print("  $id references:", len(refs), "| not a response id:", sorted(set(r for r in refs if r not in responses)))
exprs = [s[3] for s in says if s[3]]
print("  expressions:", dict(C(exprs).most_common(8)), "| using RANDOM100:", sum("RANDOM100" in e for e in exprs))

facts = ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", open(sys.argv[5], encoding="utf-8").read()))
paths = set()
for d in facts.findall("paper"):
    for f in d.findall("fact"):
        paths.add(d.get("id") + ("/" + f.get("id") if f.get("id") else ""))
fps = sorted({v[0] for v in responses.values() if v[0]})
print("\n-- response fact paths --")
print("  distinct:", len(fps), "| not a Facts.xml path (and not Day/Game/Night):",
      [f for f in fps if f not in paths and not f.startswith(("Day/", "Game/", "Night/")) and "[NATIONS]" not in f])

print("\n-- who uses which speech --")
trav = tabtree.parse(open(sys.argv[3], encoding="utf-8", newline="").read())
lines = [" ".join(n.params[1:]) for _, n in tabtree.walk(trav) if n.params and n.params[0] == '"']
def resolve(text):
    rid = text[1:] if text.startswith("$") and not text.startswith("${") else text
    return rid in responses
dollar = [l for l in lines if l.startswith("$")]
print("  Travelers.txt say lines:", len(lines), "| starting '$':", len(dollar),
      "| '$' lines not found:", [l for l in dollar if not resolve(l)],
      "| other lines that are response ids:", sum(1 for l in lines if not l.startswith("$") and resolve(l)))
err = tabtree.parse(open(sys.argv[4], encoding="utf-8", newline="").read())
tabtree.expand_params(err)
elines = []
for top in err.nodes:
    if top.params[0].startswith("*"):
        continue  # template definitions; their uses are already expanded
    elines += [" ".join(n.params[1:]) for _, n in tabtree.walk(top) if n.params and n.params[0] == '"']
print("  Errors.txt say lines:", len(elines), "| distinct:", len(set(elines)),
      "| not a response id:", sorted({l for l in elines if not resolve(l)})[:10])
used = {l[1:] if l.startswith("$") else l for l in lines + elines} | set(refs)
unnamed = [k for k in responses if k not in used]
print("  responses never named by Travelers.txt, Errors.txt or another say line:", len(unnamed))
facts_text = open(sys.argv[5], encoding="utf-8").read()
import json, os
lit_path = os.path.join(os.path.dirname(sys.argv[1]), "..", "dumps", "il2cppdumper", "stringliteral.json")
code = {l["value"] for l in json.load(open(lit_path, encoding="utf-8"))} if os.path.exists(lit_path) else set()
for k in unnamed:
    print(f"    {k:26} in Facts.xml: {k in facts_text}  a code string: {k in code}")
bracket = [l for l in lines if re.search(r"(.+?)\[([^\]]{3,})\]", l) and not resolve(l)]
print("  literal Travelers.txt lines with a [fact path] suffix:", len(bracket), bracket[:3])
print("    with text after the ']' (dropped by the game):",
      [l for l in bracket if re.search(r"(.+?)\[([^\]]{3,})\](.+)", l)])
lit = [l for l in lines if not resolve(l)]
print("\n-- features inside literal Travelers.txt lines --")
print("  ';':", sum(";" in t for t in lit), "| '@' first:", sum(t.startswith("@") for t in lit),
      "| '~' last:", sum(t.endswith("~") for t in lit), "| [m]:", sum("[m]" in t for t in lit),
      "| [f]:", sum("[f]" in t for t in lit), "| [x]:", sum("[x]" in t for t in lit),
      "| ${:", sum("${" in t for t in lit), "| '$' inside:", sum("$" in t[1:] for t in lit))
print("  examples:", [t for t in lit if ";" in t][:2], [t for t in lit if t.endswith("~")][:2],
      [t for t in lit if "${" in t][:2], [t for t in lit if "[m]" in t or "[f]" in t][:2])
