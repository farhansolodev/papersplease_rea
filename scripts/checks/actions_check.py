"""Cross-check of docs/player-actions.md against the data files.

Usage: python -I actions_check.py <reference dir> Travelers.txt Errors.txt Papers.xml Facts.xml
       Text.xml Speeches.txt

Prints counts. It also runs a small model of the stamp-result rules and the
penalty formula as described in the doc, so they can be compared with the
port later.
"""
import collections
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
import tabtree

C = collections.Counter


def read(path):
    return open(path, encoding="utf-8", newline="").read()


def lenient_xml(path):
    """Facts.xml holds a raw '&&'; escape stray ampersands before parsing."""
    return ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", read(path)))


travelers = tabtree.parse(read(sys.argv[2]))
errors = tabtree.parse(read(sys.argv[3]))
tabtree.expand_params(errors)
papers = ET.parse(sys.argv[4]).getroot()
facts = lenient_xml(sys.argv[5])
text = read(sys.argv[6])
speeches = tabtree.parse(read(sys.argv[7]))

paper_ids = {p.get("id") for p in papers.findall("paper")}

# ---------------------------------------------------------------- stamp results
APPROVED, DENIED, REASONED = 2, 4, 8


def stamp_set(flags, kind):
    if kind == APPROVED:
        return flags if flags & DENIED else flags | APPROVED
    if kind == DENIED:
        return (flags & ~APPROVED) | DENIED
    if kind == REASONED:
        return flags | REASONED
    return flags


def stamp_combine(a, b):
    out = 0
    if (a | b) & REASONED:
        out = stamp_set(out, REASONED)
    if (a | b) & DENIED:
        return stamp_set(out, DENIED)
    if (a | b) & APPROVED:
        return stamp_set(out, APPROVED)
    return out


def stamp_text(flags):
    return "".join(n for bit, n in ((2, "APPROVED"), (4, "DENIED"), (8, "REASONED")) if flags & bit)


print("-- stamp results (model of the documented rules) --")
print("  approve then deny:", stamp_text(stamp_set(stamp_set(0, APPROVED), DENIED)),
      "| deny then approve:", stamp_text(stamp_set(stamp_set(0, DENIED), APPROVED)),
      "| deny then reason:", stamp_text(stamp_set(stamp_set(0, DENIED), REASONED)))
print("  combine approved + denied:", stamp_text(stamp_combine(APPROVED, DENIED)),
      "| approved + reasoned:", stamp_text(stamp_combine(APPROVED, REASONED)),
      "| nothing + nothing:", repr(stamp_text(stamp_combine(0, 0))))

print("\n-- penalties for the 1st to 8th citation of a day --")
costs = []
for before in range(8):
    costs.append("warning" if before == 0 else "last warning" if before == 1
                 else int(max(1.0, before - 2) * 5.0))
print(" ", costs)

# ---------------------------------------------------------------- response names
FIXED = {"Approved", "ApprovedDenied", "Denied", "Detain-After", "Detain-Before", "Detain-Replace",
         "Enable-Detain", "Enable-Fingerprint", "Enable-Search", "Impatient", "Interrogate",
         "Interrogate-After", "Interrogate-Before", "Interrogate-Replace", "Intro", "Intro-After",
         "Intro-Before", "Intro-Replace", "Leave", "Poisoned", "Search-After", "Search-Before",
         "Search-Replace", "ShutterClose", "TimeBomb-Disarmed", "TimeBomb-Opened"}
names = C()
wants = C()
rejects = C()
nofiler = C()
for entry in travelers.nodes:
    for _, n in tabtree.walk(entry):
        p = n.params or []
        if len(p) > 1 and p[0] == ">":
            names[" ".join(p[1:])] += 1
        if len(p) > 2 and p[0] == "@":
            {"Want": wants, "Reject": rejects, "NoFiler": nofiler}.get(p[1], C())[" ".join(p[2:])] += 1


def explain(name):
    if name in FIXED:
        return "fixed"
    for prefix in ("Give-", "Confiscated-", "Unconfiscated-", "LinkClicked-"):
        if name.startswith(prefix):
            return prefix
    if re.fullmatch(r"Interrogate-.+-(Before|Replace|After)", name):
        return "Interrogate-<button>-"
    return None


kinds = C()
unexplained = []
for name, count in names.items():
    kind = explain(name)
    kinds[kind] += 1
    if kind is None:
        unexplained.append(name)
print("\n-- response names in Travelers.txt --")
print("  distinct:", len(names), "| by how the code builds them:", dict(kinds))
print("  not explained:", sorted(unexplained))
print("  fixed names the code asks for that no traveler defines:", sorted(FIXED - set(names)))


def target_kind(target):
    """What a Give-/Want pattern can refer to."""
    if target in paper_ids:
        return "paper id"
    if "*" in target:
        try:
            hits = [p for p in paper_ids if re.search(target, p)]
        except re.error:
            return "bad pattern"
        if hits:
            return "pattern matching %d paper ids" % len(hits)
        if re.match(r"[A-Z]+-[A-Z]+-[A-Z]+", target):
            return "confiscated id (PAPER-FIRST-LAST...)"
        return "pattern matching nothing"
    return "unknown"


gives = {n[len("Give-"):]: c for n, c in names.items() if n.startswith("Give-")}
print("\n-- Give-<id> targets --")
print(" ", dict(C(target_kind(t) for t in gives)))
print("  unknown:", sorted(t for t in gives if target_kind(t) in ("unknown", "pattern matching nothing")))

print("\n-- @ Want / Reject / NoFiler --")
print("  Want:", sum(wants.values()), "lines,", len(wants), "distinct:",
      dict(C(target_kind(t) for t in wants)))
print("  Want targets that are not a paper or pattern:",
      sorted(t for t in wants if target_kind(t) in ("unknown", "pattern matching nothing")))
print("  Reject:", dict(rejects), "| NoFiler:", dict(nofiler))
def overlap(a, b):
    """True when two ids or patterns can name the same paper."""
    return a == b or ("*" in a and re.search(a, b)) or ("*" in b and re.search(b, a))


print("  Give targets no Want pattern covers (given back by the ordinary rules instead):",
      sorted(g for g in gives if not any(overlap(g, w) for w in wants)))

links = C((p.get("id"), m.get("link")) for p in papers.findall("paper") for m in p.iter("mark")
          if (m.get("link") or "").startswith("#custom"))
print("\n-- custom links in Papers.xml --")
print(" ", dict(links), "| LinkClicked names:", sorted(n for n in names if n.startswith("LinkClicked-")))

# ---------------------------------------------------------------- interrogation
error_nodes = [n for n in errors.nodes if not n.params[0].startswith("*")]


def interrogates(node):
    """All '> Interrogate' groups at any depth under a node."""
    return [n for _, n in tabtree.walk(node) if n.params[:2] == [">", "Interrogate"]]


inval_with = inval_without = 0
buttons = C()
other_groups = C()
for e in error_nodes:
    for _, n in tabtree.walk(e):
        if n.params and n.params[0] == "!":
            found = interrogates(n)
            if found:
                inval_with += 1
                for _, b in tabtree.walk(found[0]):
                    if b.params and b.params[0] == "@":
                        buttons[" ".join(b.params[1:])] += 1
            else:
                inval_without += 1
        if n.params and n.params[0] == ">" and n.params[1:] != ["Interrogate"]:
            other_groups[" ".join(n.params[1:])] += 1
print("\n-- Errors.txt (templates expanded) --")
print("  invalidate lines with an Interrogate response:", inval_with, "| without:", inval_without)
print("  @ commands inside those responses:", dict(buttons))
print("  other named groups in errors:", dict(other_groups))
used = sorted(n for n in names if explain(n) == "Interrogate-<button>-")
print("  Interrogate-<button>-... names in Travelers.txt:", used,
      "| buttons they need:", sorted({n.split("-")[1] for n in used} - set(buttons)) or "all present")

# ---------------------------------------------------------------- things the code names
print("\n-- papers, facts, text and speech the code names --")
for pid in ("IdentityRecord", "FingerprintsBlank", "Fingerprints", "Photo", "SeizureSlip",
            "FilerEnvelope", "Citation", "Poison", "TimeBomb", "Passport"):
    if pid not in paper_ids:
        print("  MISSING paper:", pid)
print("  papers with a trade:", {p.get("id"): p.get("trade") for p in papers.findall("paper") if p.get("trade")})
docs = {d.get("id"): d for d in facts.findall("paper")}
print("  docs with saytrade:", {i: d.get("saytrade") for i, d in docs.items() if d.get("saytrade")})
fact_paths = {i + "/" + f.get("id") for i, d in docs.items() for f in d.findall("fact")}
need = ["TimeBomb/Screw%d" % i for i in range(4)] + ["TimeBomb/Wire%d" % i for i in range(4)] + \
       ["Poison/Powder1", "Poison/Powder2", "FilerEnvelope/Title", "Citation/Message", "Citation/Penalty"]
print("  fact paths the code sets that have no <fact> definition:", [p for p in need if p not in fact_paths])
print("  docs of those papers exist:", {i: i in docs for i in ("FilerEnvelope", "Citation")})
can_filer = sorted(p.get("id") for p in papers.findall("paper") if p.get("canconfiscate") == "true")
print("  papers with canconfiscate (filer type CANFILER):", can_filer)
quiet_docs = [i for i, d in docs.items() if d.get("noticeerrors") == "false"]
quiet_facts = [i + "/" + f.get("id") for i, d in docs.items() for f in d.findall("fact")
               if f.get("noticeerrors") == "false"]
print("  errors not noticed: docs", quiet_docs, "| facts", quiet_facts)
for key in ("citation_warning", "citation_lastwarning", "citation_penalty", "env_clearforentry"):
    if 'id="%s"' % key not in text:
        print("  MISSING text entry:", key)
speech_ids = {n.params[0] for n in speeches.nodes}
print("  speech ids missing:", [s for s in ("ask-detain", "detain", "ask-search", "trade-fingerprints")
                                if s not in speech_ids])

groups = facts.find("groups")
paths = [p for g in groups.findall("group") for p in g.findall("path")]
print("\n-- fact groups in Facts.xml --")
print("  groups:", len(groups.findall("group")), "| paths:", len(paths),
      "| with a proxy:", sum(1 for p in paths if p.get("proxy")))
