"""Reference implementation of building the person: the play.day.Traveler
constructor (docs/traveler-build.md). Layer 2 of the traveler answer key.

It takes a traveler specification's variables and the booth's random
generator and produces the face, name, id number, fingerprints, height,
weight and birth date, drawing random numbers in the game's order.

Not modelled here (other layers): evaluating the traveler script that
produces the variables, choosing the error, and generating document values.
Picking a criminal from the day's list is passed in as a function; booth.py
supplies it.

Run as a script for a demonstration:

    python -I scripts/reference/person.py <master seed> <day> <count> <assets dir>

where <assets dir> is extracted/art/assets. The demonstration builds people
one after another from the day's booth generator. In the game other steps
draw from that generator between two people, so **these are not the
travelers the game would produce for that seed**; it only exercises the code.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces as F  # noqa: E402
import gdate  # noqa: E402
from cyclers import FaceCycler, NameCycler, NUM_PALETTES  # noqa: E402
from rand import Rand  # noqa: E402
from seeds import Launch, day_seeds  # noqa: E402

ID_ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWX"
RANDOM_PIECES = 20            # FaceSpec.kPieceMaxMale / kPieceMaxFemale


def pick(rand, items):
    """ArrayUtil.getRandomItem: one draw; nothing if the draw is exactly 1.0."""
    index = int(len(items) * rand.random())
    return items[index] if index < len(items) else None


def parse_int(text):
    """Std.parseInt, as far as these values need it: 0 when not a number."""
    try:
        return int(text)
    except ValueError:
        return 0


def face_spec_from_string(rand, text):
    """FaceSpec.fromString: one draw for each part that is missing or '*'."""
    parts = text.split("-")

    def given(index):
        return index < len(parts) and parts[index] != "*"

    male = parts[0] == "M" if given(0) else rand.random() > 0.5
    pieces = [parse_int(parts[i]) if given(i) else int(RANDOM_PIECES * rand.random())
              for i in range(1, 5)]
    palette = parse_int(parts[5]) if given(5) else int(NUM_PALETTES * rand.random())
    flip = bool(parse_int(parts[6]) & 1) if given(6) else rand.random() > 0.5
    return (male, pieces[0], pieces[1], pieces[2], pieces[3], palette, flip)


def spec_text(spec):
    male, shoulders, head, eyes, nose_mouth, palette, flip = spec
    return "%s-%d-%d-%d-%d-%d-%d" % ("M" if male else "F", shoulders, head, eyes, nose_mouth,
                                     palette, 1 if flip else 0)


class FaceMeta:
    """FaceLib.getMetadata: the four pieces' Faces.xml records combined."""

    def __init__(self, lib, spec):
        male, shoulders, head, eyes, nose_mouth = spec[:5]
        m_shoulders = lib.face_meta(male, shoulders)
        m_head = lib.face_meta(male, head)
        m_eyes = lib.face_meta(male, eyes)
        m_nose_mouth = lib.face_meta(male, nose_mouth)
        age = lambda m: float(parse_int(m.get("age", "")))
        bmi = lambda m: float(parse_int(m.get("bmi", "")))
        self.age = age(m_eyes) * 0.5 + age(m_head) * 0.3 + age(m_nose_mouth) * 0.2
        self.bmi = int(bmi(m_head) * 0.8 + bmi(m_shoulders) * 0.2)
        self.hair_height = parse_int(m_head.get("hairheight", ""))
        self.ok_for_confusing_gender = (
            "head" in m_head.get("canbeconfusing", "")
            and "eyes" in m_eyes.get("canbeconfusing", "")
            and "mouth" in m_nose_mouth.get("canbeconfusing", ""))


def make_random_id_number(rand):
    """Ten draws. A draw of exactly 1.0 gives no character."""
    chars = [ID_ALPHABET[i] if i < len(ID_ALPHABET) else ""
             for i in (int(len(ID_ALPHABET) * rand.random()) for _ in range(10))]
    return "".join(chars[:5]) + "-" + "".join(chars[5:])


def make_fingerprints(rand):
    fingers = [int(rand.random() * 10.0) for _ in range(5)]
    while fingers[1] == fingers[2]:
        fingers[2] = int(rand.random() * 10.0)
    while fingers[3] == fingers[4]:
        fingers[4] = int(rand.random() * 10.0)
    return fingers


def lerp_scale(value, in_min, in_max, out_min, out_max):
    """app.Num.lerpScale: clamp, then a straight line between the ends."""
    clamped = max(min(value, in_max), in_min)
    return ((clamped - in_min) / (in_max - in_min)) * (out_max - out_min) + out_min


def weight_for(bmi, height_m, male):
    base = int(float(bmi) * height_m * height_m)
    if male:
        factor = lerp_scale(float(base), 60.0, 100.0, 1.3, 1.0)
    else:
        factor = lerp_scale(float(base), 40.0, 100.0, 1.0, 0.8)
    return int(float(base) * factor)


def day_date(day):
    """Day 1 of the story is 23 November 1982 (month numbers start at 0)."""
    return gdate.after_days(gdate.from_ymd(1982, 10, 23), float(day - 1))


class Person:
    pass


def build_person(variables, rand, face_cycler, name_cycler, lib, faces_dir, contra_types,
                 error_id=None, pick_criminal=None):
    """The Traveler constructor.

    variables: the specification's variables (text values, absent when unset).
    error_id: the id of the error chosen for this traveler, if any (the
        specification's custom error, when it has one).
    pick_criminal: for a Traveler-Criminal error, a function (rand, male) that
        returns (criminal index, face) or None (Criminal.selectRandom; it may
        draw once). Called at the point the game calls it.
    """
    p = Person()
    p.criminal_index = None
    p.draws_before = getattr(rand, "count", None)
    p.num_vaccines = 3 if rand.random() <= 0.5 else 2
    p.contraband_types = variables.get("contrabandTypes")
    if p.contraband_types is None:
        p.contraband_types = pick(rand, contra_types)

    spec = None
    if variables.get("face") is not None:
        spec = face_spec_from_string(rand, variables["face"])
    p.male = variables.get("gender") == "M"

    confusing = False
    name_other_gender = False
    p.error_id = error_id
    if error_id and "Traveler-ConfusingGender" in error_id:
        confusing = True
        name_other_gender = rand.random() > 0.5
    elif error_id and "Traveler-Criminal" in error_id:
        found = pick_criminal(rand, p.male) if pick_criminal else None
        if found is None:
            p.error_id = None                 # no criminal found: the traveler gets no error
        else:
            p.criminal_index, spec = found
            p.male = spec[0]
            p.error_id = "Bulletin-Criminal%d" % p.criminal_index

    if spec is None:
        if confusing:
            while True:
                spec = face_cycler.next(not p.male)
                if FaceMeta(lib, spec).ok_for_confusing_gender:
                    break
        else:
            spec = face_cycler.next(p.male)
    p.face_spec = spec
    p.meta = FaceMeta(lib, spec)
    face = F.Face(faces_dir, lib, F.FaceSpec(spec_text(spec)))
    p.face = face

    name_male = (not p.male) if name_other_gender else p.male
    p.name_male = name_male
    p.first, p.last = name_cycler.get(name_male)
    if variables.get("name") is not None:
        parts = variables["name"].split("-")
        if parts[0]:
            p.first = parts[0]
        if len(parts) > 1 and parts[1]:
            p.last = parts[1]

    p.id_number = variables.get("idNumber")
    if p.id_number is None:
        p.id_number = make_random_id_number(rand)
    p.fingerprints = make_fingerprints(rand)
    p.height_m = face.height_in_meters - rand.random() * 0.1
    p.height_cm = int(math.floor(p.height_m * 100.0 + 0.5))      # Haxe Math.round
    p.weight = weight_for(p.meta.bmi, p.height_m, p.male)
    return p


def birth_date(person, today):
    return gdate.after_years(today, -person.meta.age)


class CountingRand(Rand):
    """A generator that counts its draws, for showing how many each step took."""

    def __init__(self, seed):
        self.count = 0
        super().__init__(seed)
        self.count = 0

    def next_int(self):
        self.count += 1
        return super().next_int()

    def next_float(self):
        return self.next_int() / 2147483647.0

    random = next_float


def load_contra_types(bodies_xml):
    return [c.get("type") for c in ET.parse(bodies_xml).getroot().iter("contra")
            if c.get("type") != "bomb"]


def main():
    master, day, count = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    assets = sys.argv[4]
    data = os.path.join(assets, "data")
    faces_dir = os.path.join(assets, "faces")
    lib = F.FaceLib(os.path.join(data, "Faces.xml"), os.path.join(assets, "FacePalette.png"))
    contra_types = load_contra_types(os.path.join(data, "Bodies.xml"))
    read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()

    launch = Launch(master)
    booth = CountingRand(day_seeds(day, launch.story_seed)["booth"])
    face_cycler = FaceCycler(launch.face_cycler_seed)
    name_cycler = NameCycler(read("NamesM.txt"), read("NamesF.txt"), launch.name_cycler_seeds[0])
    today = day_date(day)
    print("master %d, day %d (%s), contraband types to pick from: %d" % (
        master, day, gdate.format_date(today, "%Y.%m.%d"), len(contra_types)))
    print("NOT what the game would produce: the draws of the other layers are missing.")
    for index in range(count):
        variables = {"gender": "M" if index % 2 == 0 else "F"}
        before = booth.count
        person = build_person(variables, booth, face_cycler, name_cycler, lib, faces_dir, contra_types)
        print("%s %-22s face %-16s id %s  prints %s  %d cm %d kg  born %s  vaccines %d  contraband %s  (%d draws)" % (
            "M" if person.male else "F", person.first + " " + person.last, spec_text(person.face_spec),
            person.id_number, "".join(map(str, person.fingerprints)), person.height_cm, person.weight,
            gdate.format_date(birth_date(person, today), "%Y.%m.%d"), person.num_vaccines,
            person.contraband_types, booth.count - before))


if __name__ == "__main__":
    main()
