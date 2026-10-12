import sys, collections, csv
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
rows = {r[0].strip(): r[1:] for r in csv.reader(open(sys.argv[3], encoding="utf-8", newline=""))}
used = {x.strip() for c in rows["TRAVELERS"] + rows["FILL"] for x in c.split("\n") if x.strip()}
block_inc = C(); op_inc = C(); fallback = C(); events = C(); buttons = C(); say_ref = 0; say_text = 0; say_fact = 0
def ops(node):
    global say_ref, say_text, say_fact
    for ch in node.nodes:
        k = ch.params[0]
        if k == "INCLUDE": op_inc[ch.params[1]] += 1
        elif k == "@": buttons[ch.params[1]] += 1
        elif k == '"':
            if len(ch.params) == 2 and ch.params[1].startswith("$") and not ch.params[1].startswith("${"): say_ref += 1
            else:
                say_text += 1
                if any("${" in q for q in ch.params): say_fact += 1
        ops(ch)
def block(node):
    for ch in node.nodes:
        k = ch.params[0]
        if k == "INCLUDE": block_inc[ch.params[1]] += 1
        elif k == "=" and ch.params[1] == "fallback": fallback[" ".join(ch.params[2:])] += 1
        elif k == "?": block(ch)
        elif k == ">": events[ch.params[1]] += 1; ops(ch)
        elif k == "*": ops(ch)
for e in root.nodes:
    if e.params[0] != "DEFAULT": block(e)
ids = {e.params[0] for e in root.nodes}
print("entries included from inside a response:", dict(op_inc))
print("entries included at block level:", len(block_inc), "distinct, e.g.", dict(block_inc.most_common(6)))
reach = used | set(block_inc) | set(op_inc) | {v for f in fallback for v in f.split()} | {"DEFAULT"}
print("fallback targets:", dict(fallback))
print("entries never named by Days.csv, an INCLUDE or a fallback:", sorted(ids - reach))
print("response events:", len(events), "distinct;", dict(events.most_common(14)))
print("events containing '*' (treated as patterns):", [e for e in events if "*" in e])
print("buttons enabled by '@':", dict(buttons.most_common()))
print("speech lines: stock references", say_ref, "| written text", say_text, "| of which use ${fact}", say_fact)
