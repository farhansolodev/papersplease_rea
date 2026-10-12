import sys, re, json, collections
import xml.etree.ElementTree as ET
C = collections.Counter
raw = open(sys.argv[1], encoding="utf-8").read()
root = ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", raw))
papers_xml = ET.parse(sys.argv[2]).getroot()
lits = {x["value"] for x in json.load(open(sys.argv[3], encoding="utf-8"))}
docs = root.findall("paper"); facts = [f for d in docs for f in d.findall("fact")]
inv = [i for f in facts for i in f.findall("invalidate")]; cites = [c for f in facts for c in f.findall("cite")]
def vals(elems, attr): return dict(C(e.get(attr) for e in elems if e.get(attr) is not None))
print("element holding '&&':", [(e.tag, a) for e in root.iter() for a, v in e.attrib.items() if "&&" in v])
print("children of <paper>:", dict(C(c.tag for d in docs for c in d)), "| children of <fact>:", dict(C(c.tag for f in facts for c in f)))
print("doc stay:", vals(docs, "stay"), "| multi:", vals(docs, "multi"), "| noticeerrors:", vals(docs, "noticeerrors"), "| money:", vals(docs, "money"))
print("doc with 'cite' attr (code reads 'desc' instead):", [d.get("id") for d in docs if d.get("cite") is not None], "| with 'desc':", sum(1 for d in docs if d.get("desc")))
pid = {p.get("id") for p in papers_xml.findall("paper")}; did = [d.get("id") for d in docs]
print("doc ids:", len(did), "distinct", len(set(did)), "| docs that are not papers in Papers.xml:", sorted(set(did) - pid))
print("papers in Papers.xml with no doc here:", sorted(pid - set(did)))
print("fact ids with [NATIONS]:", sum(1 for f in facts if "[NATIONS]" in f.get("id")), "| vals with [ISSUINGCITIES]:", sum(1 for f in facts if "[ISSUINGCITIES]" in (f.get("val") or "")), "| with [DISTRICTS]:", sum(1 for f in facts if "[DISTRICTS]" in (f.get("val") or "")), "| [NATIONS] in val but not id:", sum(1 for f in facts if "[NATIONS]" in (f.get("val") or "") and "[NATIONS]" not in f.get("id")))
print("fact id empty:", sum(1 for f in facts if f.get("id") == ""), "| fact val multi-line:", sum(1 for f in facts if "\n" in (f.get("val") or "")), "| editable:", vals(facts, "editable"), "| noticeerrors:", vals(facts, "noticeerrors"))
print("fact format values:", vals(facts, "format"))
print("fact range values:", vals(facts, "range"))
print("fact 'cite' attr count:", sum(1 for f in facts if f.get("cite") is not None), "| <cite> when starting with '*':", sum(1 for c in cites if c.get("when", "").startswith("*")), "of", len(cites), "| sample when:", sorted({c.get("when") for c in cites})[:8])
print("invalidate: with when", sum(1 for i in inv if i.get("when") is not None), "| with whennot (lowercase, not read):", [(i.get("path"), i.get("whennot")) for i in inv if i.get("whennot") is not None], "| distinct when values:", len({i.get("when") for i in inv}), "| when containing operators:", sum(1 for i in inv if re.search(r"==|&&|\|\|", i.get("when") or "")))
fpaths = set()
nations = [n.get("name") for n in root.find("nations")]
for d in docs:
    for f in d.findall("fact"):
        ids = [f.get("id").replace("[NATIONS]", n) for n in nations] if "[NATIONS]" in f.get("id") else [f.get("id")]
        for i in ids: fpaths.add(d.get("id") + ("/" + i if i else ""))
print("expanded fact paths:", len(fpaths))
ip = [i.get("path") for i in inv]
print("invalidate paths not matching a fact path:", sorted({x for x in ip if x not in fpaths})[:12])
grp = root.find("groups"); gpaths = [x for g in grp for x in g]
print("groups:", len(list(grp)), "| paths with '*':", sum(1 for x in gpaths if "*" in x.get("val")), "| with [NATION]:", sum(1 for x in gpaths if "[NATION]" in x.get("val")), "| group ids with [NATION]:", sum(1 for g in grp if "[NATION]" in g.get("id")))
plain = [x.get("val") for x in gpaths if "*" not in x.get("val") and "[NATION]" not in x.get("val")]
print("plain group paths not matching a fact path:", sorted({x for x in plain if x not in fpaths})[:12])
print("nations:", nations, "| citizen values (attribute never read):", vals(root.find("nations"), "citizen"))
pur = list(root.find("purposes"))
print("purposes:", [(x.get("val"), x.get("chance"), x.get("rule"), x.get("chooseforinvalid"), len(x.get("nations").split())) for x in pur])
print("autopapers:", [(x.get("id"), x.get("rule"), x.get("purposes")) for x in root.find("autopapers")])
print("durations:", [(x.get("val"), x.get("purposes")) for x in root.find("durations")])
print("counts: jobs", len(list(root.find("jobs"))), "districts", len(list(root.find("districts"))), "vaccines", len(list(root.find("vaccines"))), "locs", len(list(root.find("locs"))))
rb = list(root.find("rulebook")); rules_pages = {pg.get("id") for p in papers_xml.findall("paper") if p.get("id") == "Rules" for pg in p}
print("rulebook pages:", [(x.get("id"), x.get("rule"), x.get("confiscation")) for x in rb])
print("rulebook page ids not a page of the Rules paper:", sorted({x.get("id") for x in rb} - rules_pages), "| Rules pages not in rulebook:", sorted(rules_pages - {x.get("id") for x in rb}))
print("confiscations:", [x.get("id") for x in root.find("confiscations")])
misc = root.find("misc")
print("misc attrs and whether the name exists as a string in the code:", {a: (a in lits) for a in misc.attrib})
print("loc section values (attribute never read):", vals(root.find("locs"), "section"))
