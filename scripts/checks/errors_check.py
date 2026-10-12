import sys, re, collections
import xml.etree.ElementTree as ET
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
before = sum(1 for _, n in tabtree.walk(root))
uses = sum(1 for _, n in tabtree.walk(root) if any(q.startswith("$") and len(q) >= 3 for q in n.params))
tabtree.expand_params(root)
after = sum(1 for _, n in tabtree.walk(root))
left = [n.params for _, n in tabtree.walk(root) if any(q.startswith("$") and len(q) >= 3 for q in n.params)]
print(f"nodes before expansion {before}, template uses {uses}, nodes after {after}, '$' words left: {left[:3]}")
templates = [n for n in root.nodes if n.params[0].startswith("*")]
errors = [n for n in root.nodes if not n.params[0].startswith("*")]
always = [n for n in errors if n.params[0].startswith("ALWAYS")]
print("templates:", len(templates), "| errors:", len(errors), "| always:", len(always), "| random:", len(errors) - len(always))
ids = C(n.params[0] for n in errors)
print("duplicate error ids:", [k for k, v in ids.items() if v > 1])
groups = C((n.params[1] if len(n.params) > 1 else n.params[0]) for n in errors if n not in always)
print("groups among random errors:", len(groups), "| largest:", groups.most_common(5), "| groups with one error:", sum(1 for v in groups.values() if v == 1))
tags = C(t for n in errors for t in re.findall(r"<[^>]*>", n.params[0]))
print("tags:", dict(tags.most_common()))
OPS = {'"', "!", "-", "+", "=", "?", "@", "\\", "^", "INCLUDE"}
kinds = C(); other = C(); req1 = C(); req_lhs = C(); req_ops = C(); req_bad = []; nested_req = 0; inval = C(); events = C(); says = set(); buttons = C()
def walk_ops(node, depth, eid):
    global nested_req
    for ch in node.nodes:
        k = ch.params[0]; kinds[(min(depth, 2), k if k in OPS else "(group)")] += 1
        if k == "\\":
            if depth > 1: nested_req += 1
            toks = ch.params[1:]
            if len(toks) == 1: req1[toks[0]] += 1
            elif len(toks) >= 3 and (len(toks) - 3) % 4 == 0:
                for i in range(0, len(toks), 4):
                    req_lhs[toks[i]] += 1; req_ops[toks[i + 1]] += 1
            else: req_bad.append((eid, toks))
        elif k == "!": inval[ch.params[1]] += 1
        elif k == '"': says.add(" ".join(ch.params[1:]))
        elif k == "@": buttons[" ".join(ch.params[1:])] += 1
        elif k not in OPS: events[" ".join(ch.params[1:]) if k == ">" else " ".join(ch.params)] += 1
        walk_ops(ch, depth + 1, eid)
for e in errors: walk_ops(e, 1, e.params[0])
print("lines directly under an error:", {k: v for (d, k), v in kinds.items() if d == 1})
print("lines deeper:", {k: v for (d, k), v in kinds.items() if d == 2})
print("requirements below the first level (ignored by the matching code):", nested_req)
print("paper requirements:", dict(req1.most_common()))
print("condition left sides:", dict(req_lhs.most_common()), "| operators:", dict(req_ops.most_common()), "| malformed:", req_bad[:3])
raw = open(sys.argv[3], encoding="utf-8").read()
facts = ET.fromstring(re.sub(r"&(?!amp;)", "&amp;", raw))
nations = [n.get("name") for n in facts.find("nations")]
paths = set()
for d in facts.findall("paper"):
    for f in d.findall("fact"):
        for i in ([f.get("id").replace("[NATIONS]", n) for n in nations] if "[NATIONS]" in f.get("id") else [f.get("id")]):
            paths.add(d.get("id") + ("/" + i if i else ""))
print("facts invalidated:", len(inval), "distinct paths | not a known fact path:", sorted(k for k in inval if k not in paths)[:12])
docs = {d.get("id") for d in facts.findall("paper")}
print("paper requirements that are not a document in Facts.xml:", sorted(set(req1) - docs))
print("named groups (events):", dict(events.most_common()))
print("buttons:", dict(buttons.most_common()), "| distinct speech ids:", len(says), "| with spaces:", sum(1 for s in says if " " in s))
print("example expanded entry:")
e = [n for n in errors if n.params[0].startswith("Passport-Hidden")][0]
def show(n, ind=0):
    print("   " + "  " * ind + " ".join(n.params))
    for c in n.nodes: show(c, ind + 1)
show(e)
