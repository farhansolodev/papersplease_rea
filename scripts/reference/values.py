"""Reference implementation of the helpers that make document values wrong.

Layer 5a of the traveler answer key (docs/value-helpers.md):
data.TravelerName (getFormatted, getRandomInvalidated, getRandomAlias),
data.Lang (the alias swap sets, makeAlias, makeTypo), data.Uppercaser,
data.FaceSpec.getInvalid, data.FingerprintCode.makeInvalid and
play.day.Traveler.invalidateIdNumber.

Run as a script to print examples and run the self-checks:

    python -I scripts/reference/values.py <data dir> [seed]

where <data dir> is extracted/art/assets/data.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cyclers import NameCycler  # noqa: E402
from haxemap import IntMap, StringMap  # noqa: E402
from person import make_fingerprints, make_random_id_number  # noqa: E402
from rand import Rand  # noqa: E402

BUILT_IN_SWAP_SETS = "aeiou,iuy,pgq,lj,ck,bh"
TYPO_NON_LETTERS = "-. "
PIECES = 20


def _split_and_trim(text, delimiter):
    return [piece.strip() for piece in text.split(delimiter) if piece.strip()]


def _item(rand, items):
    """ArrayUtil.getRandomItem: one draw; nothing (0 for numbers) past the end."""
    index = int(len(items) * rand.random())
    return items[index] if index < len(items) else None


class Uppercaser:
    """UpperCase.txt: one mapping per line, `0x<code point> <upper-case text>`."""

    def __init__(self, text):
        self.table = {}
        for line in text.split("\n"):
            parts = line.strip().split(" ")
            if len(parts) == 2:
                self.table[int(parts[0], 16)] = parts[1]

    def upper(self, text):
        return "".join(self.table.get(ord(ch), ch) for ch in text)


class Lang:
    """The parts of data.Lang that make aliases and typos."""

    def __init__(self, text_xml, uppercaser):
        match = re.search(r'<item id="env_typochars">\s*<t>(.*?)</t>', text_xml, re.S)
        joined = (match.group(1) if match else "") + "," + BUILT_IN_SWAP_SETS
        sets = _split_and_trim(joined, ",") + _split_and_trim(uppercaser.upper(joined), ",")
        table = StringMap()
        for letters in sets:
            ordered = sorted(letters)                  # by code point
            table.set("".join(ordered), ordered)
        self.swap_sets = list(table.values())          # the map's own (hash) order

    def make_alias(self, rand, word):
        """Change exactly one letter into a similar one."""
        chars = list(word)
        positions = IntMap()
        for index, ch in enumerate(chars):
            for swap_set in self.swap_sets:
                if ch in swap_set:
                    found = positions.get(index)
                    if found is None:
                        positions.set(index, [swap_set])
                    else:
                        found.append(swap_set)
        keys = list(positions.keys())                  # the map's own order, often not left to right
        if keys:
            index = _item(rand, keys) or 0
            swap_set = _item(rand, positions.get(index))
            original = chars[index]
            while True:
                letter = _item(rand, swap_set)
                if letter != original:
                    break
            alias = "".join(chars[:index] + [letter] + chars[index + 1:])
            if alias != word:
                return alias
        return self.make_typo(rand, word)

    def make_typo(self, rand, word):
        """Remove one character, not next to a hyphen, full stop or space."""
        chars = list(word)

        def at(i):
            return chars[i] if 0 <= i < len(chars) else None

        index = 0
        for _ in range(10000):
            index = int(rand.random() * (((len(word) - 1) - 0.0001) - 1.0) + 1.0)
            if at(index) not in TYPO_NON_LETTERS_SET and at(index - 1) not in TYPO_NON_LETTERS_SET:
                break
        return "".join(chars[:index] + chars[index + 1:])


TYPO_NON_LETTERS_SET = set(TYPO_NON_LETTERS)


class TravelerName:
    def __init__(self, name_cycler, male, first="", last=""):
        self.name_cycler = name_cycler
        self.male = male
        self.first = first
        self.last = last

    def formatted(self, layout=None):
        layout = layout or ""
        if layout == "Last, First":
            return self.last + ", " + self.first
        if layout == "FIRST LAST":
            return (self.first + " " + self.last).upper()
        if layout == "LAST,/FIRST":
            return (self.last + ",\n" + self.first).upper()
        if layout == "FIRST/LAST":
            return (self.first + "\n" + self.last).upper()
        return self.first + " " + self.last

    def equals(self, other):
        return self.first == other.first and self.last == other.last

    def _invalidated_once(self, rand):
        r = rand.random()
        cycler, male = self.name_cycler, self.male
        if r < 0.5:
            first = cycler.get(male)[0]                # two separate names from the cycler
            last = cycler.get(male)[1]
        elif r < 0.75:
            first, last = cycler.get(male)[0], self.last
        else:
            first, last = self.first, cycler.get(male)[1]
        return TravelerName(cycler, male, first, last)

    def random_invalidated(self, rand):
        while True:
            name = self._invalidated_once(rand)
            if not name.equals(self):
                return name

    def random_alias(self, lang, rand):
        name = TravelerName(self.name_cycler, self.male, self.first, self.last)
        r = rand.random()
        if self.male:
            first_name = r < 0.5
        else:
            if r >= 0.666:
                name.last = self.name_cycler.get(False)[1]
                return name
            first_name = r < 0.333
        if first_name:
            name.first = lang.make_alias(rand, self.first)
        else:
            name.last = lang.make_alias(rand, self.last)
        return name


def face_get_invalid(spec, rand):
    """FaceSpec.getInvalid: every piece shifted by 1 to 18; four draws."""
    male, shoulders, head, eyes, nose_mouth, palette, flip = spec
    shift = lambda piece: (int((PIECES - 2) * rand.random() + 1.0) + piece) % PIECES
    nose_mouth = shift(nose_mouth)
    eyes = shift(eyes)
    shoulders = shift(shoulders)
    head = shift(head)
    return (male, shoulders, head, eyes, nose_mouth, palette, flip)


def fingerprints_make_invalid(rand, valid):
    """A new random code, then each finger redrawn while it equals the real one."""
    fingers = make_fingerprints(rand)
    for index in range(len(fingers)):
        while fingers[index] == valid[index]:
            fingers[index] = int(rand.random() * 10.0)
    return fingers


def invalidate_id_number(rand, number):
    """Replace one character of the number with the one from a new random number."""
    other = make_random_id_number(rand)
    char_at = lambda text, i: text[i] if 0 <= i < len(text) else ""
    while True:
        index = int(len(number) * rand.random())
        if char_at(other, index) != char_at(number, index):
            return number[:index] + char_at(other, index) + number[index + 1:]


class CountingRand(Rand):
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


def load(data_dir):
    read = lambda name: open(os.path.join(data_dir, name), encoding="utf-8", newline="").read()
    lang = Lang(read("Text.xml"), Uppercaser(read("UpperCase.txt")))
    return lang, read("NamesM.txt"), read("NamesF.txt")


def main():
    data_dir = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    lang, names_m, names_f = load(data_dir)
    print("alias swap sets, in the game's order:", ", ".join("".join(s) for s in lang.swap_sets))

    rand = CountingRand(seed)
    cycler = NameCycler(names_m, names_f, seed)
    name = TravelerName(cycler, True, *cycler.get(True))
    print("name:", name.formatted(), "|", repr(name.formatted("LAST,/FIRST")), "|", name.formatted("Last, First"))
    print("  wrong names:", ", ".join(name.random_invalidated(rand).formatted() for _ in range(4)))
    print("  aliases:    ", ", ".join(name.random_alias(lang, rand).formatted() for _ in range(4)))
    woman = TravelerName(cycler, False, *cycler.get(False))
    print("name:", woman.formatted())
    print("  aliases:    ", ", ".join(woman.random_alias(lang, rand).formatted() for _ in range(5)))
    print("typos of 'East Grestin':", ", ".join(lang.make_typo(rand, "East Grestin") for _ in range(5)))
    print("aliases of 'Paradizna':", ", ".join(lang.make_alias(rand, "Paradizna") for _ in range(5)))
    print("wrong face for M-3-7-12-1-2-0:", face_get_invalid((True, 3, 7, 12, 1, 2, False), rand))
    print("wrong fingerprints for 28379:", fingerprints_make_invalid(rand, [2, 8, 3, 7, 9]))
    print("altered id number for 3FSXH-5K873:", invalidate_id_number(rand, "3FSXH-5K873"))

    problems = []
    words = [line.split(" ")[i] for line in (names_m + names_f).split("\n")
             if len(line.split(" ")) == 2 for i in (0, 1)]
    alias_draws, typo_fallbacks = {}, 0
    for index, word in enumerate(words[:1500]):
        r = CountingRand(1000 + index)
        alias = lang.make_alias(r, word)
        differing = [i for i, (a, b) in enumerate(zip(word, alias)) if a != b]
        if len(alias) == len(word):
            if len(differing) != 1:
                problems.append("alias of %r changed %d letters" % (word, len(differing)))
            alias_draws[r.count] = alias_draws.get(r.count, 0) + 1
        elif len(alias) == len(word) - 1:
            typo_fallbacks += 1
        else:
            problems.append("alias of %r has a wrong length" % word)
        typo = lang.make_typo(CountingRand(index), word)
        if len(typo) != len(word) - 1 or (len(word) > 2 and typo[0] != word[0]):
            problems.append("typo of %r is %r" % (word, typo))
    print("checks over 1500 name parts: draws used by an alias:", dict(sorted(alias_draws.items())),
          "| names with no swappable letter (typo instead):", typo_fallbacks)
    for s in range(300):
        r = CountingRand(s)
        face = face_get_invalid((True, s % 20, (s * 3) % 20, (s * 7) % 20, (s * 11) % 20, 0, False), r)
        if r.count != 4 or any(not 0 <= p < 20 for p in face[1:5]) or \
                face[1] == s % 20 or face[2] == (s * 3) % 20 or face[3] == (s * 7) % 20 or face[4] == (s * 11) % 20:
            problems.append("wrong face keeps a piece or leaves 0..19")
        valid = make_fingerprints(CountingRand(s + 5000))
        if any(a == b for a, b in zip(fingerprints_make_invalid(CountingRand(s), valid), valid)):
            problems.append("wrong fingerprints keep a finger")
        number = make_random_id_number(CountingRand(s + 9000))
        altered = invalidate_id_number(CountingRand(s), number)
        if len(altered) != len(number) or sum(a != b for a, b in zip(altered, number)) != 1:
            problems.append("altered id number differs in other than one place")
        wrong = name.random_invalidated(CountingRand(s))
        if wrong.equals(name):
            problems.append("wrong name equals the real one")
    print("problems:", sorted(set(problems)) or "none")


if __name__ == "__main__":
    main()
