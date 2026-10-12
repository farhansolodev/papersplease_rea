import sys, re, collections
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
papers = root.findall("paper"); C = collections.Counter
def vals(elems, attr): return dict(C(e.get(attr) for e in elems if e.get(attr) is not None))
pages = [pg for p in papers for pg in p]; marks = [m for pg in pages for m in pg]
print("children of <paper> other than page:", C(c.tag for p in papers for c in p if c.tag != "page"))
print("children of <page> other than mark:", C(c.tag for pg in pages for c in pg if c.tag != "mark"))
ids = C(p.get("id") for p in papers)
print("paper ids:", len(ids), "duplicated:", {k: [(q.get("nation")) for q in papers if q.get("id") == k] for k, n in ids.items() if n > 1})
print("nation values:", vals(papers, "nation"))
print("reveal values:", vals(papers, "reveal"))
for a in ("fromtraveler","stampable","inspectable","rotate","oddshape","dock","canpinch","canconfiscate"):
    print(f"paper {a}:", vals(papers, a))
snd = {s.get("id") for s in root.findall("sounds")}
print("sounds ids:", sorted(snd), "| paper sounds refs missing:", sorted({p.get("sounds") for p in papers if p.get("sounds")} - snd), "| 'paper' default exists:", "paper" in snd)
print("trade:", vals(papers, "trade"), "| mount count:", sum(1 for p in papers if p.get("mount")))
print("mark align:", vals(marks, "align"), "| page align:", vals(pages, "align"), "| paper align:", vals(papers, "align"))
print("mark flow:", vals(marks, "flow"))
print("mark side:", vals(marks, "side"), "| inspectable:", vals(marks, "inspectable"))
kinds = C(("text" if m.get("text") is not None else "image" if m.get("image") is not None else "emblem" if m.get("emblem") is not None else "NONE") for m in marks)
print("mark kinds:", dict(kinds), "| with both text and image:", sum(1 for m in marks if m.get("text") is not None and m.get("image") is not None))
print("text starting with $:", sum(1 for m in marks if (m.get("text") or "").startswith("$")), "of", kinds["text"], "| image starting with $:", sum(1 for m in marks if m.get("text") is None and (m.get("image") or "").startswith("$")), "of", kinds["image"])
pt = re.compile(r"^-?\d+(\.\d+)? -?\d+(\.\d+)?$")
for name, elems, attr in (("mark pos", marks, "pos"), ("mark pos2", marks, "pos2"), ("mark stamplinksize", marks, "stamplinksize"), ("paper visacenter", papers, "visacenter"), ("ink datepos", root.findall("ink"), "datepos")):
    v = [e.get(attr) for e in elems if e.get(attr) is not None]
    print(f"{name}: {len(v)} values, not 'number number': {[x for x in v if not pt.match(x)][:5]}")
er = [m.get("emblemrect") for m in marks if m.get("emblemrect")]
print("emblemrect not 4 numbers:", [x for x in er if len(x.split()) != 4])
col = [e.get(a) for e in papers + pages + marks + root.findall("ink") for a in ("textcolor","backcolor","datecolor") if e.get(a) is not None]
print("colour formats:", dict(C("0x-hex" if re.match(r"^0x[0-9A-Fa-f]{6}$", c) else "zero" if c == "0" else "other:" + c for c in col)))
print("unused attrs -> fontlinespacing on:", [p.get("id") for p in papers if p.get("fontlinespacing")], "| format values:", vals(marks, "format"), "| section values:", vals(marks, "section"))
car = root.find("carousel"); known = set(ids)
gp = [x.strip() for g in car.findall("group") for x in g.get("papers").split(",")]
print("carousel groups:", [(g.get("id"), len(g.get("papers").split(",")), g.get("tight")) for g in car.findall("group")])
print("group paper ids not defined as papers:", sorted(set(gp) - known))
print("forceorder:", [(f.get("id"), f.get("val")) for f in car.findall("forceorder")])
print("pages per paper:", dict(sorted(C(len(list(p)) for p in papers).items())), "| page ids:", dict(C(pg.get("id") for pg in pages)))
