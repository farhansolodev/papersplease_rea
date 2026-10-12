"""Cross-check of docs/papers-on-desk.md against the real data files.

Usage: python -I papers_on_desk_check.py <reference dir> Facts.xml Papers.xml Days.csv Errors.txt
"""
import sys, re, csv, collections
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import tabtree

AMP = r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)"
facts = ET.fromstring(re.sub(AMP, "&amp;", open(sys.argv[2], encoding="utf-8").read()))
papers = ET.fromstring(open(sys.argv[3], encoding="utf-8").read())

# Fact ids whose VALID value makes random draws (docs/fact-values.md).
DRAWS_WHEN_VALID = {"AccessNations", "Description", "VaccineDates", "VaccineDrugs"}
# Fact ids whose value needs a traveler to exist.
NEEDS_TRAVELER = {"BirthDate", "Name", "IssuingCity", "Nation", "IdNumber", "Gender", "Face",
                  "Description", "Fingerprints", "Thumbprint", "Height", "Weight", "Duration",
                  "Purpose", "Job", "District", "Nationality", "Contraband", "VaccineDates",
                  "VaccineDrugs", "WorkEndDate"}

docs = facts.findall("paper")
print("documents:", len(docs))

def flag(name, pred):
    ids = [d.get("id") for d in docs if pred(d)]
    print(f"{name}: {len(ids)} -> {ids}")

flag("multi", lambda d: d.get("multi") == "true")
flag("money", lambda d: d.get("money") is not None)
print("  money values:", {d.get("id"): d.get("money") for d in docs if d.get("money")})
print("achieve (count only):", sum(1 for d in docs if d.get("achieve")))
flag("id starts with Token", lambda d: d.get("id").startswith("Token"))
print("stay:", dict(collections.Counter(d.get("stay") for d in docs)))

all_paths = set()
for d in docs:
    for f in d.findall("fact"):
        fid = f.get("id")
        all_paths.add(d.get("id") + ("/" + fid if fid else ""))

print("\n-- values generated when a document is added (facts with empty val) --")
preset = generated = 0
for d in docs:
    for f in d.findall("fact"):
        if f.get("val"): preset += 1
        else: generated += 1
print("facts with a written value:", preset, "| facts generated on add:", generated)

print("\n-- documents with two or more facts that draw when generated valid (order matters) --")
for d in docs:
    ids = [f.get("id") for f in d.findall("fact") if not f.get("val") and f.get("id") in DRAWS_WHEN_VALID]
    if len(ids) >= 2:
        print(f"  {d.get('id'):24} {ids}")

print("\n-- staying documents: do they draw random numbers or need a traveler when added? --")
for stay in ("game", "day"):
    for d in docs:
        if d.get("stay") != stay: continue
        ids = [f.get("id") for f in d.findall("fact") if not f.get("val")]
        exp = any(f.get("id") == "ExpirationDate" for f in d.findall("fact"))
        draws = sorted(set(ids) & DRAWS_WHEN_VALID) + (["<expiration date>"] if exp else [])
        needs = sorted(set(ids) & NEEDS_TRAVELER)
        emblem = [i for i in ids if i.startswith("Emblem")]
        if draws or needs:
            print(f"  {stay:4} {d.get('id'):24} draws={draws} needs-traveler={needs}")
    print(f"  ({stay}: {sum(1 for d in docs if d.get('stay') == stay)} documents checked)")

print("\n-- multi documents: facts --")
for d in docs:
    if d.get("multi") == "true":
        print(f"  {d.get('id'):24} stay={d.get('stay')} facts={[f.get('id') for f in d.findall('fact')]}")

print("\n-- clearconfusion --")
tilde = set()
root = tabtree.parse(open(sys.argv[5], encoding="utf-8", newline="").read())
tabtree.expand_params(root)
for _, node in tabtree.walk(root):
    for param in node.params or []:
        if param.startswith("~"): tilde.add(param[1:])
cc = [(d.get("id"), c.get("path")) for d in docs for c in d.findall("clearconfusion")]
print("entries:", len(cc), "| on documents:", sorted({p for p, _ in cc}))
print("paths that are not real facts:", sorted({p for _, p in cc if p not in all_paths}))
print("distinct paths cleared:", len({p for _, p in cc}), "| distinct ~ paths in Errors.txt:", len(tilde))
print("cleared but never made confusing:", sorted({p for _, p in cc} - tilde))
print("made confusing but never cleared:", sorted(tilde - {p for _, p in cc}))
print("cleared by a document other than their own:", sum(1 for d, p in cc if p.split('/')[0] != d), "of", len(cc))

print("\n-- Bulletin --")
bul_facts = [f.get("id") for d in docs if d.get("id") == "Bulletin" for f in d.findall("fact")]
print("Bulletin facts in Facts.xml:", bul_facts)
bul = [p for p in papers.iter("paper") if p.get("id") == "Bulletin"]
page_ids = [pg.get("id") for pg in bul[0].findall("page")] if bul else []
print("Bulletin pages in Papers.xml:", page_ids)
refs = collections.Counter()
for pg in (bul[0].findall("page") if bul else []):
    for m in pg.iter("mark"):
        for a in ("text", "image"):
            v = m.get(a) or ""
            if v.startswith("$"): refs[v[1:]] += 1
print("fact references on Bulletin pages:", dict(refs))
def pronoun(s):
    out, up = "", True
    for ch in s:
        out += ch.upper() if up else ch
        up = ch == " "
    return out
want = {"PageNumber" + pronoun(p) for p in page_ids}
print("PageNumber<Page> facts missing from Facts.xml:", sorted(want - set(bul_facts)))
print("PageNumber facts in Facts.xml with no page:", sorted({f for f in bul_facts if f.startswith('PageNumber')} - want))

rows = list(csv.reader(open(sys.argv[4], encoding="utf-8", newline="")))
byname = {r[0].strip(): r[1:] for r in rows if r}
b0, b1, bp = byname.get("BULLETIN0", []), byname.get("BULLETIN1", []), byname.get("BPAGES", [])
n = max(len(b0), len(b1))
notice_counts = collections.Counter()
for i in range(n):
    a = b0[i].strip() if i < len(b0) else ""
    b = b1[i].strip() if i < len(b1) else ""
    notice_counts[(1 if a else 0) + (1 if b else 0)] += 1
print("days by number of notice pages:", dict(notice_counts))
extra = sorted({w for c in bp for w in c.split()})
print("BPAGES ids:", extra, "| not pages of the Bulletin paper:", sorted(set(extra) - set(page_ids)))
print("days whose text has [PAGESNOTE]:", sum(1 for c in b0 + b1 if "[PAGESNOTE]" in c))
