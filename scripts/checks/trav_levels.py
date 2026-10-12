import sys, collections
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
BLOCK = {"=", "+", "-", "?", "INCLUDE", "(", "MANUALPAPERS", "BREAK", "*", ">"}
block_lhs = C(); op_lhs = C(); stray = C(); typo = []; block_ops = C(); op_ops = C(); default_shape = C()
def lhs_kind(l): return "RANDOM100" if l == "RANDOM100" else (l.split("/")[0] + "/" if "/" in l else "variable")
def conds(params, into, opsinto, where):
    for i in range(1, len(params), 4):
        into[lhs_kind(params[i])] += 1; opsinto[params[i + 1]] += 1
        if params[i + 1] not in ("==", "!=", "<", "<=", ">", ">=", "has", "!has"): typo.append((where, " ".join(params)))
def ops(node, top):
    for ch in node.nodes:
        if ch.params[0] == "?": conds(ch.params, op_lhs, op_ops, top)
        ops(ch, top)
def block(node, top, path):
    for ch in node.nodes:
        k = ch.params[0]
        if k not in BLOCK: stray[(top, path, k)] += 1
        elif k == "?": conds(ch.params, block_lhs, block_ops, top); block(ch, top, path + " > ?")
        elif k in (">", "*"): ops(ch, top)
for entry in root.nodes:
    if entry.params[0] == "DEFAULT":
        def shape(n, depth):
            for ch in n.nodes:
                default_shape[(depth, ch.params[0])] += 1; shape(ch, depth + 1)
        shape(entry, 1)
    block(entry, entry.params[0], entry.params[0])
print("stray lines at block level:", dict(stray))
print("conditions evaluated when the traveler is created: left sides", dict(block_lhs.most_common()), "| operators", dict(block_ops.most_common()))
print("conditions inside responses: left sides", dict(op_lhs.most_common()), "| operators", dict(op_ops.most_common()))
print("comparisons with an operator the evaluator does not know:", typo)
print("shape of DEFAULT by depth:", {f"{d}:{k}": v for (d, k), v in sorted(default_shape.items())})
