import csv, sys, re, collections
rows = list(csv.reader(open(sys.argv[1], encoding="utf-8", newline="")))
print("rows:", len(rows), "columns:", sorted(set(len(r) for r in rows)))
print("header:", rows[0])
for r in rows:
    cells = r[1:]
    filled = [c for c in cells if c.strip()]
    items = [x for c in filled for x in c.split("\n") if x.strip()]
    prefixes = collections.Counter(x[0] for x in items if x[0] in "+-!?*@#")
    sample = items[0][:40] if items else ""
    print(f"{r[0]!r:22} filled {len(filled):2}/{len(cells)}  items {len(items):3}  prefixes {dict(prefixes)}  e.g. {sample!r}")
