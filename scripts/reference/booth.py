"""Reference implementation of the booth: play.day.BoothEnv.

Layer 5b (second part) and the chaining layer of the traveler answer key.
It puts papers on the desk (addPaper), generates each document value
(makeFactValue), marks facts wrong or right again (setFactInvalid,
setFactValid, the invalidate / validate / set-fact / add-paper lines of an
error) and runs the whole of makeNewTraveler on top of the earlier layers:
travspec.py (who comes next and their script), errormaker.py (which error),
person.py (the person), values.py (wrong-value helpers), factlib.py (the
documents' facts) and faces.py (the face picture, for the height).
See docs/traveler-creation.md, docs/papers-on-desk.md, docs/fact-values.md
and docs/operations-and-fact-validity.md.

Run as a script to list the first travelers of a day with their documents:

    python -I scripts/reference/booth.py <master seed> <day> <count> <assets dir> [--facts]

where <assets dir> is extracted/art/assets.
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import errormaker as E  # noqa: E402
import faces as F  # noqa: E402
import gdate  # noqa: E402
import person as P  # noqa: E402
import travspec as T  # noqa: E402
import values as V  # noqa: E402
from cyclers import FaceCycler, NameCycler, make_shuffled  # noqa: E402
from factlib import Fact, FactLib  # noqa: E402
from haxemap import StringMap  # noqa: E402
from rand import Rand  # noqa: E402
from seeds import Launch, day_seeds  # noqa: E402

DATE_FORMATS = (("%y.%m.%d", "%Y.%m.%d"), ("%d.%m.%y", "%d.%m.%Y"), ("%m.%d.%y", "%m.%d.%Y"))


class Env:
    """Everything loaded once from the data files."""

    def __init__(self, assets_dir):
        data = os.path.join(assets_dir, "data")
        read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
        facts_text = read("Facts.xml")
        self.lib = FactLib(facts_text)
        self.table, self.world, self.travelers = T.load(data)
        self.error_lib = E.ErrorLib(read("Errors.txt"))
        self.misc = self.lib.misc
        self.upper = V.Uppercaser(read("UpperCase.txt"))
        text_xml = read("Text.xml")
        self.lang = V.Lang(text_xml, self.upper)
        self.text = {m.group(1): m.group(2) for m in
                     re.finditer(r'<item id="([^"]+)">\s*<t>(.*?)</t>', text_xml, re.S)}
        self.names_m, self.names_f = read("NamesM.txt"), read("NamesF.txt")
        self.faces_dir = os.path.join(assets_dir, "faces")
        self.face_lib = F.FaceLib(os.path.join(data, "Faces.xml"),
                                  os.path.join(assets_dir, "FacePalette.png"))
        self.contra_types = P.load_contra_types(os.path.join(data, "Bodies.xml"))


class Value:
    def __init__(self, text, localized=None, date=None, name=None):
        self.text = text
        self.localized = localized
        self.date = date
        self.name = name


class PaperInfo:
    def __init__(self, paper_id, index, expiration):
        self.id = paper_id
        self.index = index
        self.id_with_index = paper_id if index == 0 else "%s_%d" % (paper_id, index)
        self.expiration = expiration


class Booth:
    """One day's booth. Its generator and its error maker last the day."""

    def __init__(self, env, day_number, story_seed, face_cycler, name_cycler,
                 story_facts=None, date_format_index=0):
        self.env = env
        self.day_number = day_number
        self.story_facts = dict(story_facts or {})
        self.day = T.Day(env.table, day_number, story_seed, face_cycler, self.story_facts)
        self.day_facts = self.day.facts
        self.today = P.day_date(day_number)
        self.features = [f for f in self.day_facts["Day/Features"].split(";") if f]
        self.harder = "HARDER" in self.features
        self.confiscation_id = env.table.cell(day_number, "CONFISCATE").replace("&amp;", "&") or None
        self.rand = P.CountingRand(day_seeds(day_number, story_seed)["booth"])
        self.error_maker = E.ErrorMaker(self.rand, env.error_lib)
        self.face_cycler = face_cycler
        self.name_cycler = name_cycler
        self.spec_context = T.TravelerContext(env.travelers, env.world, self.day_facts, self.story_facts)
        self.date_format = DATE_FORMATS[date_format_index if 0 <= date_format_index < 3 else 0]
        self.criminal_used = [False] * len(self.day.criminals)
        self.traveler = None
        self.paper_infos = {}
        self.facts = {}
        self.invalid_paths = []
        self.invalid_infos = {}
        self.invalid_order = 0
        self.confusing_paths = set()
        self.cleared_confusion_paths = []
        self.had_paper_ids = []
        self.applied_errors = []
        self.bribe_money = 0
        # The constructor's papers. None of them draws; the bulletin text,
        # the rulebook page mask and the upgrade marks are not modelled.
        for paper in ["Rules", "Transcript", "Bulletin"] + \
                T.split_and_trim(env.table.cell(day_number, "PAPERS"), "\n") + \
                [p for p in self.story_facts.get("Game/StayingPapers", "").split(";") if p]:
            self.add_paper(paper)

    # ------------------------------------------------------------ fact stores

    def get_value(self, path):
        if path.startswith("Day/"):
            return Fact(path, self.day_facts[path]) if path in self.day_facts else None
        if path.startswith("Game/") or path.startswith("Night/"):
            return Fact(path, self.story_facts[path]) if path in self.story_facts else None
        return self.facts.get(path)

    def value_text(self, path):
        fact = self.get_value(path)
        return fact.text if fact is not None and fact.text is not None else ""

    def set_fact_value(self, path, value):
        if path.startswith("Day/"):
            self.day_facts[path] = value.text
        elif path.startswith("Game/") or path.startswith("Night/"):
            self.story_facts[path] = value.text
        else:
            fact = self.facts.setdefault(path, Fact(path, ""))
            fact.text, fact.localized, fact.date, fact.name = (
                value.text, value.localized, value.date, value.name)

    # ------------------------------------------------------------ validity

    def find_invalid_fact_path(self, path):
        if self.traveler is None:
            return None
        for invalid in self.invalid_paths:
            if invalid == path:
                return invalid
            text = self.facts[invalid].text if invalid in self.facts else ""
            if self.env.lib.fact_invalidates_path(invalid, text or "", self.traveler.nationality, path):
                return invalid
        return None

    def set_fact_invalid(self, path, op=None):
        if self.find_invalid_fact_path(path) is not None:
            return
        fact = self.facts.setdefault(path, Fact(path, ""))
        value = self.make_fact_value(fact.path, False)
        fact.text, fact.localized, fact.date, fact.name = (
            value.text, value.localized, value.date, value.name)
        self.invalid_paths.append(path)
        self.invalid_infos[path] = (op, self.invalid_order)
        self.invalid_order += 1

    def set_fact_valid(self, path):
        if self.find_invalid_fact_path(path) is None:
            return
        fact = self.facts.get(path)
        if fact is None:
            return
        definition = self.env.lib.fact_defs.get(path)
        if definition is not None and definition.editable:
            value = self.make_fact_value(fact.path, True)
            fact.text, fact.localized, fact.date, fact.name = (
                value.text, value.localized, value.date, value.name)
        self.cleared_confusion_paths.append(path)
        if path in self.invalid_paths:
            self.invalid_paths.remove(path)
        self.invalid_infos.pop(path, None)

    # ------------------------------------------------------------ papers

    def next_multi_paper_index(self, paper_id):
        return max([info.index for info in self.paper_infos.values() if info.id == paper_id],
                   default=-1) + 1

    def add_paper(self, paper_id):
        lib = self.env.lib
        self.bribe_money += lib.paper_money(paper_id)
        if paper_id not in self.had_paper_ids:
            self.had_paper_ids.append(paper_id)
        if not lib.is_multi_paper(paper_id):
            if paper_id not in self.paper_infos:
                months = T.parse_float(self.traveler.duration) if self.traveler is not None else 0.0
                expiration = lib.generate_paper_expiration_date(paper_id, self.rand, self.today, months)
                self.paper_infos[paper_id] = PaperInfo(paper_id, 0, expiration)
                copy = lib.get_facts(paper_id)
                for fact in copy.values():                         # the table's own order
                    if not fact.text:
                        value = self.make_fact_value(
                            fact.path, self.find_invalid_fact_path(fact.path) is None)
                        fact.text, fact.localized, fact.date, fact.name = (
                            value.text, value.localized, value.date, value.name)
                for fact in copy.values():                         # existing paths keep their value
                    if fact.path not in self.facts:
                        self.facts[fact.path] = fact
        else:
            info = PaperInfo(paper_id, self.next_multi_paper_index(paper_id), 0.0)
            self.paper_infos[info.id_with_index] = info
        for path in lib.clear_confusion_paths(paper_id):
            if path in self.confusing_paths:
                self.set_fact_valid(path)

    def remove_paper(self, id_with_index):
        if id_with_index in self.paper_infos:
            del self.paper_infos[id_with_index]
            self.bribe_money -= self.env.lib.paper_money(id_with_index.split("_")[0])

    # ------------------------------------------------------------ one line of an error

    def apply_op(self, node):
        """The lines an error can carry at its top level. Requirements and
        named groups do nothing here; a say line is not modelled."""
        kind = node.params[0]
        if kind == "!":
            path = node.params[1]
            if path.startswith("~"):
                path = path[1:]
                self.set_fact_invalid(path, node)
                self.set_fact_value(path, self.make_fact_value(path, False, confusing=True))
                self.confusing_paths.add(path)
            else:
                self.set_fact_invalid(path, node)
        elif kind == "^":
            self.set_fact_valid(node.params[1])
        elif kind == "=":
            self._set_fact(node.params[1], node.params[2] if len(node.params) > 2 else "")
        elif kind == "+":
            self.add_paper(node.params[1])
        elif kind == "-":
            self.remove_paper(node.params[1])

    def _set_fact(self, path, word):
        if "/" not in word:
            if word.startswith("++") or word.startswith("--"):
                current = T.parse_int(self.value_text(path) or "0")
                amount = T.parse_int(word[2:])
                word = str(current + amount if word.startswith("++") else current - amount)
            self.set_fact_value(path, Value(word))
            return
        source = self.get_value(word)                    # copy from another fact
        definition = self.env.lib.fact_defs.get(path)
        prefix = definition.prefix if definition else ""
        if source is None:
            self.set_fact_value(path, Value(word))
        elif source.name is None:
            self.set_fact_value(path, Value(prefix + source.text))
        else:
            layout = definition.format if definition else None
            self.set_fact_value(path, Value(prefix + source.name.formatted(layout), name=source.name))

    # ------------------------------------------------------------ values

    def format_date(self, date, long=False):
        return gdate.format_date(date, self.date_format[1 if long else 0])

    def _random_access_nations(self, include_arstotzka, count):
        nations = self.env.world.nations
        order = make_shuffled(self.rand, len(nations))
        names = [nations[order[order[i]]][0] for i in range(len(nations))]   # the shuffle applied twice
        if not include_arstotzka:
            names.remove("Arstotzka")
        while len(names) > count:
            index = int(len(names) * self.rand.random())
            name = names[index] if index < len(names) else None
            if include_arstotzka and name == "Arstotzka":
                continue
            if name in names:
                names.remove(name)
        return names

    def _decorations(self, yes):
        """The face's "has" or "has not" description words, in the game's
        table order."""
        t = self.traveler
        male, shoulders, head, eyes, nose_mouth = t.face_spec[:5]
        table = StringMap()
        for key, piece in (("shoulders", shoulders), ("head", head), ("eyes", eyes), ("mouth", nose_mouth)):
            word = self.env.face_lib.face_meta(male, piece).get(key if yes else "n" + key)
            if word is not None:
                table.set(key, word)
        return list(table.values())

    def make_fact_value(self, path, valid, confusing=False):
        env, rand, t, today = self.env, self.rand, self.traveler, self.today
        lib, world, lang = env.lib, env.world, env.lang
        slash = path.find("/")
        paper = path[:slash] if slash >= 0 else path
        fact_id = path[slash + 1:] if slash >= 0 else ""

        if fact_id == "BirthDate":
            date = gdate.after_years(today, -t.meta.age)
            if not valid:
                shift = rand.random() * 1815.0 + 10.0
                if rand.random() < 0.5:
                    shift = -shift
                date = gdate.after_days(date, shift)
            return Value(self.format_date(date), date=date)
        if fact_id in ("Exists", "Visible"):
            return Value("YES" if valid else "NO")
        if fact_id == "ExpirationDate":
            if valid:
                date = self.paper_infos[paper].expiration     # the game also fails if the paper is not on the desk
            else:
                date = gdate.after_days(today, -(rand.random() * 29.0 + 1.0))
            return Value(self.format_date(date), date=date)
        if fact_id == "WorkEndDate":
            year, month, _ = gdate.split(today)
            duration = T.parse_float(t.duration)
            if valid:
                month = month + 1 + int(math.ceil(duration))
                if month > 11:
                    year, month = year + month // 12, month % 12
            else:
                month = int(math.floor(duration)) + month
                if month > 11:
                    year, month = year + month // 12, month % 12
                month -= int(rand.random() * 11.0 + 1.0)
                if month < 0:
                    back = (-month - 1) // 12 + 1
                    year, month = year - back, month + back * 12
            date = gdate.from_ymd(year, month, 1)
            return Value(self.format_date(date), date=date)
        if fact_id == "UseDate":
            date = today if valid else gdate.after_days(today, rand.random() * 29.0 + 1.0)
            return Value(self.format_date(date), date=date)
        if fact_id == "Name":
            name = t.name
            if not valid:
                if rand.random() >= 0.5:
                    name = name.random_invalidated(rand)
                else:
                    name = name.random_alias(lang, rand)
            definition = lib.fact_defs.get(path)
            return Value(name.formatted(definition.format if definition else None), name=name)
        if fact_id == "IssuingCity":
            city = t.issuing_city
            shown = lib.localized(city)
            if not valid:
                if rand.random() < 0.25:
                    city = lang.make_alias(rand, city)
                    shown = lang.make_alias(rand, shown)
                elif self.harder and rand.random() < 0.25:
                    city = lang.make_typo(rand, city)
                    shown = lang.make_typo(rand, shown)
                else:
                    while True:
                        nation = world.random_nationality(rand, None)
                        if nation != t.nationality:
                            break
                    city = world.random_issuing_city(rand, nation)
                    shown = lib.localized(city)
            return Value(city, shown)
        if fact_id == "Nation":
            nation = t.nationality
            if not valid:
                nation = world.random_nationality(rand, None)
                while nation == t.nationality:
                    nation = world.random_nationality(rand, None)
            return Value(nation.upper(), env.upper.upper(lib.localized(nation)))
        if fact_id == "AccessNations":
            count = int(rand.random() * 3.0 + 2.0)
            names = self._random_access_nations(valid, count)
            return Value(", ".join(names).upper(),
                         env.upper.upper(", ".join(lib.localized(n) for n in names)))
        if fact_id == "IdNumber":
            number = t.id_number
            if not valid:
                if self.harder and rand.random() < 0.5:
                    if rand.random() < 0.25:
                        number = lang.make_typo(rand, number)
                    else:
                        number = V.invalidate_id_number(rand, number)
                else:
                    number = P.make_random_id_number(rand)
            return Value(number)
        if fact_id == "Gender":
            male = t.male if (confusing or valid) else not t.male
            return Value("M" if male else "F",
                         env.text.get("env_lettermale" if male else "env_letterfemale"))
        if fact_id == "Face":
            if valid:
                return Value("VALID")
            return Value(P.spec_text(V.face_get_invalid(t.face_spec, rand)))
        if fact_id == "Description":
            word = V._item(rand, self._decorations(valid))
            return Value(env.upper.upper(word) if word is not None else "")
        if fact_id in ("Fingerprints", "Thumbprint"):
            fingers = t.fingerprints if valid else V.fingerprints_make_invalid(rand, t.fingerprints)
            return Value("".join(str(f) for f in fingers))
        if fact_id == "Alias":
            return Value(env.text.get("env_noalias", ""))
        if fact_id == "Height":
            cm = t.height_cm
            if not valid:
                change = int(P.lerp_scale(rand.random(), 0.0, 1.0, 10.0, 20.0))
                cm = cm + change if rand.random() > 0.5 else cm - change
            return Value("%dcm" % cm)
        if fact_id == "Weight":
            weight = t.weight
            if not valid:
                weight -= int(P.lerp_scale(rand.random(), 0.0, 1.0, 3.0, 5.0))
            return Value("%dkg" % weight)
        if fact_id == "Duration":
            duration = t.duration
            if not valid:
                duration = world.random_duration(rand, None)
                while duration == t.duration:
                    duration = world.random_duration(rand, None)
            shown = next((lib.localized(text) for value, text, _ in lib.durations if value == duration),
                         "UNKNOWN")
            return Value(str(duration), shown)
        if fact_id == "Purpose":
            purpose = t.purpose
            if not valid:
                while purpose == t.purpose:
                    purpose = world.random_purpose(rand, t.nationality,
                                                   self.day_facts.get("Day/Rules", ""), for_invalid=True)
            return Value(purpose, env.upper.upper(lib.localized(purpose)))
        if fact_id == "Job":
            return Value(t.job, lib.localized(t.job))
        if fact_id == "District":
            district = t.district
            shown = lib.localized(district)
            if not valid:
                if self.harder and rand.random() < 0.5:
                    district = lang.make_typo(rand, district)
                    shown = lang.make_typo(rand, shown)
                else:
                    district = lang.make_alias(rand, district)
                    shown = lang.make_alias(rand, shown)
            return Value(district, env.upper.upper(lib.localized("district").replace("$0", shown)))
        if fact_id == "Nationality":
            return Value(t.nationality, lib.localized(t.nationality))
        if fact_id == "Contraband":
            return Value(t.contraband_types)
        if fact_id == "NowDate":
            return Value(self.format_date(today), date=today)
        if fact_id == "VaccineDates":
            if valid:
                date = gdate.after_days(today, rand.random() * 700.484 - 730.484)
            else:
                date = gdate.after_days(today, rand.random() * 2191.452 - 3652.42)
            dates = []
            for _ in range(t.num_vaccines):
                dates.append(self.format_date(date, long=True))
                date = gdate.after_days(date, rand.random() + 1.0)
            return Value("\n".join(dates))
        if fact_id == "VaccineDrugs":
            drugs = ["POLIO"] if valid else []
            while len(drugs) < t.num_vaccines:
                drug = V._item(rand, lib.vaccines)
                if drug not in drugs and drug != "POLIO":
                    drugs.append(drug)
            order = make_shuffled(rand, len(drugs))
            drugs = [drugs[i] for i in order]
            return Value("\n".join(drugs), "\n".join(lib.localized(d) for d in drugs))
        if fact_id.startswith("Emblem"):
            if valid:
                return Value("VALID")
            return Value("INVALID" if rand.random() < 0.75 else "NONE")
        if fact_id.startswith("Criminal"):
            index = T.parse_int(fact_id[len("Criminal"):])
            return Value(str(index) if 0 <= index < len(self.day.criminals) else "")
        if paper in ("Bulletin", "Rules"):
            existing = self.get_value(path)
            if existing is not None:
                return Value(existing.text, existing.localized, existing.date, existing.name)
        return Value("")

    # ------------------------------------------------------------ a traveler

    def _pick_criminal(self, entry_id, gender_forced):
        def pick(rand, male):
            for index, (reserved_for, face) in enumerate(self.day.criminals):
                if reserved_for is not None and reserved_for == entry_id:
                    return index, face
            candidates = [index for index, (reserved_for, face) in enumerate(self.day.criminals)
                          if not self.criminal_used[index] and reserved_for is None
                          and (not gender_forced or face[0] == male)]
            if not candidates:
                return None
            index = V._item(rand, candidates)
            return (index, self.day.criminals[index][1]) if index is not None else None
        return pick

    def apply_error(self, error):
        if error is None:
            return
        self.applied_errors.append(error)
        for node in error.node.nodes:
            self.apply_op(node)

    def make_new_traveler(self):
        """BoothEnv.makeNewTraveler. Returns the traveler; the booth then
        holds their papers and facts."""
        env = self.env
        entry = self.day.next_traveler_id()
        spec = self.spec_context.make_spec(entry, self.day.traveler_rand)

        # Carry over what persists; reset the per-traveler state.
        keep = set(env.lib.persist_paper_ids)
        self.facts = {path: fact for path, fact in self.facts.items()
                      if path.split("/")[0] in keep and path.split("/")[0] != "Transcript"}
        self.paper_infos = {key: info for key, info in self.paper_infos.items() if info.id in keep}
        self.had_paper_ids = [info.id for info in self.paper_infos.values()]
        self.invalid_paths, self.invalid_infos, self.invalid_order = [], {}, 0
        self.confusing_paths, self.cleared_confusion_paths, self.applied_errors = set(), [], []

        draws_start = self.rand.count
        context = E.make_error_context(self.day_facts, spec, self.confiscation_id)
        error = E.first_error(spec, context, self.error_maker)
        if spec.custom_error_node is not None:
            custom = T.tabtree.Node()
            custom.params = spec.custom_error_node.params[1:]
            custom.nodes = spec.custom_error_node.nodes
            error = E.Error(custom)

        draws_before = self.rand.count
        person = P.build_person(
            spec.vars, self.rand, self.face_cycler, self.name_cycler, env.face_lib, env.faces_dir,
            env.contra_types, error.id if error else None,
            self._pick_criminal(spec.id, spec.vars.get("genderForced") == "YES"))
        if person.criminal_index is not None:
            self.criminal_used[person.criminal_index] = True
            error = env.error_lib.find(person.error_id)
        elif person.error_id is None:
            error = None

        v = spec.vars
        person.entry, person.spec, person.error = entry, spec, error
        person.nationality, person.purpose, person.duration = v.get("nation"), v.get("purpose"), v.get("duration")
        person.job, person.district, person.issuing_city = v.get("job"), v.get("district"), v.get("issuingCity")
        person.name = V.TravelerName(self.name_cycler, person.name_male, person.first, person.last)
        person.person_draws = self.rand.count - draws_before
        self.traveler = person

        for paper in ["Traveler", "Speech", "Booth"] + list(spec.initial_papers):
            self.add_paper(paper)
        self.apply_error(error)
        person.additional_error = E.additional_error(spec, error, context, self.error_maker,
                                                     self.rand, env.misc)
        self.apply_error(person.additional_error)
        person.always_errors = env.error_lib.always_errors_for_context(context)
        for extra in person.always_errors:
            self.apply_error(extra)
        person.total_draws = self.rand.count - draws_start
        return person


def describe(booth, person, with_facts):
    errors = [e.id for e in booth.applied_errors]
    print("%-20s %s %s %s, %s, %d cm %d kg, id %s, face %s" % (
        person.entry, "M" if person.male else "F", person.first, person.last, person.nationality,
        person.height_cm, person.weight, person.id_number, P.spec_text(person.face_spec)))
    print("    purpose %s, duration %s, papers: %s" % (
        person.purpose, person.duration, ", ".join(person.spec.initial_papers) or "none"))
    print("    errors: %s | wrong facts: %s" % (", ".join(errors) or "none",
                                                ", ".join(booth.invalid_paths) or "none"))
    if with_facts:
        for paper in person.spec.initial_papers:
            shown = ["%s=%s%s" % (path.split("/", 1)[1], repr(fact.text)[1:-1],
                                  "*" if booth.find_invalid_fact_path(path) else "")
                     for path, fact in booth.facts.items()
                     if path.startswith(paper + "/") and path.split("/", 1)[1] not in ("Exists", "Visible")]
            print("    %s: %s" % (paper, "; ".join(shown)))


def main():
    master, day_number, count = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    env = Env(sys.argv[4])
    launch = Launch(master)
    booth = Booth(env, day_number, launch.story_seed, FaceCycler(launch.face_cycler_seed),
                  NameCycler(env.names_m, env.names_f, launch.name_cycler_seeds[0]))
    print("master %d, day %d (%s), rules: %s" % (
        master, day_number, gdate.format_date(booth.today, "%Y.%m.%d"), booth.day_facts["Day/Rules"]))
    for _ in range(count):
        person = booth.make_new_traveler()
        describe(booth, person, "--facts" in sys.argv)


if __name__ == "__main__":
    main()
