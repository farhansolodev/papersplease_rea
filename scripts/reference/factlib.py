"""Reference model of Facts.xml as the game holds it: data.FactLib.

Layer 5b (first part) of the traveler answer key: the documents and their
facts after expansion, the copy of a document's facts in the order the game
walks it (a Haxe StringMap's order), the links by which one fact's value
makes another invalid, the localization table, and the expiration-date
rule. See docs/facts-xml-format.md, docs/papers-on-desk.md and
docs/haxe-maps.md.

Run as a script to print a summary and run the self-checks:

    python -I scripts/reference/factlib.py <data dir>

where <data dir> is extracted/art/assets/data.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdate  # noqa: E402
from haxemap import StringMap  # noqa: E402
from rand import Rand  # noqa: E402

DEFAULT_RANGE = (10.0, 30.0)


def parse_int(text):
    match = re.match(r"\s*[-+]?\d+", text or "")
    return int(match.group(0)) if match else 0


class FactDef:
    def __init__(self, doc, node, override_id=None, override_val=None):
        self.id = override_id if override_id is not None else node.get("id")
        self.val = override_val if override_val is not None else (node.get("val") or "")
        self.val_loc = node.get("loc") if node.get("loc") is not None else self.val
        self.path = doc.id + ("/" + self.id if self.id else "")
        self.editable = node.get("editable") == "true"
        self.format = node.get("format")
        self.prefix = node.get("prefix") or ""
        self.notice_errors = (node.get("noticeerrors") == "true"
                              if node.get("noticeerrors") is not None else doc.notice_errors)
        self.range = DEFAULT_RANGE
        if node.get("range") is not None:
            low, high = node.get("range").split()[:2]
            self.range = (float(low), float(high))
        # Attribute names are case-sensitive: the misspelled `whennot` is not read.
        self.invalidates = [(i.get("path"), i.get("when"), i.get("whenNot"), i.get("nation"))
                            for i in node.findall("invalidate")]
        self.cites = ([(node.get("cite"), None)] if node.get("cite") is not None else []) + \
                     [(c.get("val"), c.get("when")) for c in node.findall("cite")]

    def invalidates_path(self, current_value, nation, other_path):
        for path, when, when_not, for_nation in self.invalidates:
            if (path == other_path and (for_nation is None or for_nation == nation)
                    and (when is None or when == current_value)
                    and (when_not is None or when_not != current_value)):
                return True
        return False


class DocDef:
    def __init__(self, lib, node):
        self.id = node.get("id")
        self.stay = node.get("stay")
        self.multi = node.get("multi") == "true"
        self.notice_errors = node.get("noticeerrors") is None or node.get("noticeerrors") == "true"
        self.money = parse_int(node.get("money")) if node.get("money") is not None else 0
        self.say_trade = node.get("saytrade")
        self.fact_defs = []
        for fact in node.findall("fact"):
            self._add_fact_defs(lib, fact)
        self.clear_confusion_paths = [c.get("path") for c in node.findall("clearconfusion")]

    def _add_fact_defs(self, lib, node):
        fact_id = node.get("id")
        value = node.get("val") or ""
        if "[NATIONS]" in fact_id:
            for name, cities in lib.nations:
                localized = "\n".join(lib.localized(city) for city in cities)
                text = value.replace("[ISSUINGCITIES]", localized).replace("[NATIONS]", name)
                self.fact_defs.append(FactDef(self, node, fact_id.replace("[NATIONS]", name), text))
        elif "[DISTRICTS]" in value:
            localized = "\n".join(lib.localized(district) for district in lib.districts)
            self.fact_defs.append(FactDef(self, node, fact_id, value.replace("[DISTRICTS]", localized)))
        else:
            self.fact_defs.append(FactDef(self, node))

    def generate_expiration_date(self, rand, now, duration_months):
        """One draw if the document has an ExpirationDate fact, none otherwise."""
        for definition in self.fact_defs:
            if definition.id == "ExpirationDate":
                low, high = definition.range
                if duration_months != 0.0 and high > 700.0:
                    low = max(low, duration_months * 31.0 + 5.0)
                    high = max(low + 60.0, high)
                return gdate.after_days(now, rand.random() * (high - low) + low)
        return now


class Fact:
    def __init__(self, path, text, localized=None, date=None, name=None):
        self.path = path
        self.text = text
        self.localized = localized
        self.date = date
        self.name = name

    def is_set(self):
        return bool(self.text)


class FactLib:
    def __init__(self, facts_xml_text):
        root = ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", facts_xml_text))
        self.nations = [(n.get("name"), n.get("cities").split(";")) for n in root.find("nations")]
        self.districts = [d.get("val") for d in root.find("districts")]
        self.vaccines = [v.get("val") for v in root.find("vaccines")]
        self.durations = [(d.get("val"), d.get("text"), d.get("purposes")) for d in root.find("durations")]
        self.locs = {l.get("id"): l.get("val") for l in root.find("locs")}
        self.misc = dict(root.find("misc").attrib)
        self.confiscations = {c.get("id"): c.attrib for c in root.find("confiscations")}
        self.docs = {}
        self.fact_defs = {}
        for node in root.findall("paper"):
            doc = DocDef(self, node)
            self.docs[doc.id] = doc
            for definition in doc.fact_defs:
                self.fact_defs[definition.path] = definition
        self.persist_paper_ids = [d.id for d in self.docs.values() if d.stay in ("day", "game")]

    def localized(self, text):
        return self.locs.get(text, text)

    def get_facts(self, paper_id):
        """A fresh copy of a document's facts, as the game's table: walking
        it (keys() or values()) gives the game's order, not file order."""
        table = StringMap()
        doc = self.docs.get(paper_id)
        for definition in (doc.fact_defs if doc else []):
            table.set(definition.path, Fact(definition.path, definition.val, definition.val_loc))
        return table

    def is_multi_paper(self, paper_id):
        return paper_id in self.docs and self.docs[paper_id].multi

    def paper_money(self, paper_id):
        return self.docs[paper_id].money if paper_id in self.docs else 0

    def paper_stay(self, paper_id):
        return self.docs[paper_id].stay if paper_id in self.docs else None

    def clear_confusion_paths(self, paper_id):
        return self.docs[paper_id].clear_confusion_paths if paper_id in self.docs else []

    def generate_paper_expiration_date(self, paper_id, rand, now, duration_months):
        doc = self.docs.get(paper_id)
        return doc.generate_expiration_date(rand, now, duration_months) if doc else now

    def fact_invalidates_path(self, path, value, nation, other_path):
        definition = self.fact_defs.get(path)
        return definition.invalidates_path(value, nation, other_path) if definition else False

    def should_notice_error(self, path):
        definition = self.fact_defs.get(path)
        return definition.notice_errors if definition else False


def main():
    data_dir = sys.argv[1]
    lib = FactLib(open(os.path.join(data_dir, "Facts.xml"), encoding="utf-8").read())
    facts = [d for doc in lib.docs.values() for d in doc.fact_defs]
    print("documents: %d | facts after expansion: %d | with a written value: %d | empty: %d" % (
        len(lib.docs), len(facts), sum(1 for f in facts if f.val), sum(1 for f in facts if not f.val)))
    print("documents that stay: %d | stackable: %s" % (
        len(lib.persist_paper_ids), sorted(d.id for d in lib.docs.values() if d.multi)))
    different = []
    for doc in lib.docs.values():
        file_order = [f.path for f in doc.fact_defs]
        if list(lib.get_facts(doc.id).keys()) != file_order:
            different.append(doc.id)
    print("documents whose facts are walked in a different order than written: %d" % len(different))
    short = lambda key: key.split("/", 1)[1] if "/" in key else "(the document itself)"
    print("  VaccineCert order:", [short(k) for k in lib.get_facts("VaccineCert").keys()])
    print("  Passport order:   ", [short(k) for k in lib.get_facts("Passport").keys()])
    ranges = {f.path: f.range for f in facts if f.id == "ExpirationDate"}
    print("expiration-date ranges in days:", ranges)
    now = gdate.from_ymd(1982, 10, 23)
    for paper, months in (("Passport", 0.0), ("EntryPermit", 2.0), ("WorkPermit", 6.0), ("Rules", 0.0)):
        days = [round(lib.generate_paper_expiration_date(paper, Rand(seed), now, months) - now)
                for seed in range(400)]
        print("  %-11s duration %3.1f months: expires %d to %d days from today" % (
            paper, months, min(days), max(days)))
    links = [(f.path,) + link for f in facts for link in f.invalidates]
    print("invalidate links: %d | with a `when`: %d | with `whenNot`: %d | to a path that is not a fact: %s" % (
        len(links), sum(1 for l in links if l[2] is not None), sum(1 for l in links if l[3] is not None),
        [l[1] for l in links if l[1] not in lib.fact_defs]))
    print("example: Traveler/Nationality 'Kolechia' invalidates Rules/RuleArstotzkaOnly:",
          lib.fact_invalidates_path("Traveler/Nationality", "Kolechia", None, "Rules/RuleArstotzkaOnly"))
    expanded = sorted(f.path for f in facts if any(n in f.path for n, _ in lib.nations))[:4]
    print("expanded per nation, first few:", expanded)
    problems = []
    if len(lib.docs) != 63 or len(facts) != 203:
        problems.append("expected 63 documents and 203 facts")
    order = [short(k) for k in lib.get_facts("VaccineCert").keys()]
    if order.index("VaccineDates") > order.index("VaccineDrugs"):
        problems.append("VaccineCert: dates should be walked before drugs")
    if any(doc.fact_defs for doc in lib.docs.values() if doc.multi):
        problems.append("a stackable document has facts")
    print("problems:", problems or "none")


if __name__ == "__main__":
    main()
