import sys, csv, collections
sys.path.insert(0, sys.argv[1])
import tabtree
C = collections.Counter
raw = open(sys.argv[2], encoding="utf-8", newline="").read()
print("line endings: CRLF" if "\r\n" in raw else "line endings: LF", "| block comments:", raw.count("#*"), "| lines inside them:", sum(raw[a:raw.find("*#", a)].count("\n") for a in [i for i in range(len(raw)) if raw.startswith("#*", i)]))
root = tabtree.parse(raw)
ids = [n.params[0] for n in root.nodes]
print("top-level ids:", len(ids), "distinct:", len(set(ids)), "| duplicated:", [k for k, v in C(ids).items() if v > 1][:10])
print("top-level nodes with more than one parameter:", [(n.params) for n in root.nodes if len(n.params) > 1][:8])
rows = {r[0].strip(): r[1:] for r in csv.reader(open(sys.argv[3], encoding="utf-8", newline=""))}
used = [x.strip() for c in rows["TRAVELERS"] + rows["FILL"] for x in c.split("\n") if x.strip()]
print("traveler ids used by Days.csv:", len(used), "distinct:", len(set(used)), "| not defined in Travelers.txt:", sorted(set(used) - set(ids)))
print("defined but not used by Days.csv:", len(set(ids) - set(used)), "e.g.", sorted(set(ids) - set(used))[:14])
inc = [n.params for _, n in tabtree.walk(root) if n.params and n.params[0] == "INCLUDE"]
print("INCLUDE lines:", len(inc), "| targets not defined:", sorted({p[1] for p in inc if len(p) > 1 and p[1] not in ids}), "| with other than 2 parameters:", [p for p in inc if len(p) != 2][:5])
words = C(n.params[0] for d, n in tabtree.walk(root) if d > 0 and n.params and n.params[0][0].isalnum())
print("word-led lines below the top level:", dict(words.most_common(12)))
print("parameter counts for '=' lines:", dict(sorted(C(len(n.params) for _, n in tabtree.walk(root) if n.params[0] == "=").items())))
print("parameter counts for '?' lines:", dict(sorted(C(len(n.params) for _, n in tabtree.walk(root) if n.params[0] == "?").items())))
print("'>' second parameter values:", len({n.params[1] for _, n in tabtree.walk(root) if n.params[0] == ">"}), "distinct")
print("tokens that were written in quotes:", sum(1 for _, n in tabtree.walk(root) for p in n.params if " " in p))
