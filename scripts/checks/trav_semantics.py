import sys, collections
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
BLOCK = {"=", "+", "-", "?", "INCLUDE", "(", "MANUALPAPERS", "BREAK", "*", ">"}
OPS = {'"', "!", "-", "+", "=", "?", "@", "\\", "^", "INCLUDE"}
unknown_block = C(); op_other = C(); eq_names = C(); eq_shapes = C(); cond_bad = []; x_bad = []; group_children = C()
block_counts = C(); op_counts = C(); rand100 = 0; glue = C(); ops_used = C(); eq_op_shapes = C(); lhs_kinds = C()
def cond(params, start, where):
    global rand100
    n = len(params) - start
    if n < 3 or (n - 3) % 4: cond_bad.append((where, params))
    for i in range(start, len(params), 4):
        lhs = params[i]; ops_used[params[i + 1] if i + 1 < len(params) else "?"] += 1
        if lhs == "RANDOM100": rand100 += 1; lhs_kinds["RANDOM100"] += 1
        elif "/" in lhs: lhs_kinds[lhs.split("/")[0] + "/"] += 1
        else: lhs_kinds["variable"] += 1
        if i + 3 < len(params): glue[params[i + 3]] += 1
def ops(node, top):
    for ch in node.nodes:
        k = ch.params[0]; op_counts[k if k in OPS else "(other)"] += 1
        if k not in OPS: op_other[" ".join(ch.params[:2])] += 1
        if k == "=": eq_op_shapes[len(ch.params)] += 1
        if k == "?": cond(ch.params, 1, top)
        ops(ch, top)
def block(node, top):
    for ch in node.nodes:
        k = ch.params[0]; block_counts[k if k in BLOCK else "(unknown)"] += 1
        if k not in BLOCK: unknown_block[k] += 1
        elif k == "=":
            eq_names[ch.params[1]] += 1
            eq_shapes["with x children" if ch.nodes else ("no value" if len(ch.params) < 3 else ("one value" if len(ch.params) == 3 else "several values"))] += 1
            for x in ch.nodes:
                try: ok = x.params[0] == "x" and float(x.params[1]) != 0
                except Exception: ok = False
                if not ok: x_bad.append(x.params)
        elif k == "?": cond(ch.params, 1, top); block(ch, top)
        elif k in (">", "*"): ops(ch, top)
        elif k == "(":
            for g in ch.nodes: group_children["pattern" if "*" in g.params[0] else "plain path"] += 1
for entry in root.nodes: block(entry, entry.params[0])
print("block-level lines by kind:", dict(block_counts.most_common()))
print("unknown block-level kinds (would raise an error in the game):", dict(unknown_block))
print("lines inside responses and custom errors by kind:", dict(op_counts.most_common()))
print("  the '(other)' ones:", dict(op_other.most_common(12)))
print("'=' at block level:", dict(eq_shapes), "| invalid 'x' children:", x_bad[:3])
print("'=' inside responses, token counts:", dict(sorted(eq_op_shapes.items())))
known = "nation purpose job district duration issuingCity contrabandTypes special forceDeny slow canDetain leaveDir want face gender name idNumber genderForced fallback MANUALPAPERS error preventAdditionalError".split()
print("'=' names that are TravelerSpec properties:", {k: v for k, v in eq_names.most_common() if k in known})
print("'=' names that are not:", {k: v for k, v in eq_names.most_common() if k not in known})
print("conditions with a token count the evaluator would reject:", cond_bad[:3], "| RANDOM100 uses:", rand100)
print("comparison operators used:", dict(ops_used.most_common()), "| joiners:", dict(glue))
print("left-hand sides:", dict(lhs_kinds.most_common()))
