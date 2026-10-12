import sys, re, collections
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
tags = C(); shapes = C(); second = C(); child_kinds = C(); req_shapes = C(); req_first = C()
for n in root.nodes:
    name = n.params[0]
    for t in re.findall(r"<([^>]*)>", name): tags[t] += 1
    shapes[len(n.params)] += 1
    if len(n.params) > 1: second[n.params[1]] += 1
    for ch in n.nodes:
        child_kinds[ch.params[0]] += 1
        if ch.params[0] == "\\":
            req_shapes[len(ch.params) - 1] += 1; req_first[ch.params[1] if len(ch.params) == 2 else "(condition)"] += 1
print("entries:", len(root.nodes), "| parameter counts:", dict(shapes), "| distinct second tokens:", len(second))
print("tags:", dict(tags.most_common()))
print("names with no tag:", sum(1 for n in root.nodes if "<" not in n.params[0]), "e.g.", [n.params[0] for n in root.nodes if "<" not in n.params[0]][:8])
print("direct children by kind:", dict(child_kinds.most_common()))
print("requirement lines by number of words:", dict(sorted(req_shapes.items())), "| single-word requirements:", dict(req_first.most_common(14)))
print("first six entries:", [" ".join(n.params) for n in root.nodes[:6]])
