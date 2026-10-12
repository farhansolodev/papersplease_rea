"""Reference implementation of the game's face and name cyclers.

app.ArrayUtil.makeShuffled and getShuffledWithMaxSeparation,
app.ShuffledSequence, data.FaceCycler and data.NameCycler. See
docs/traveler-build.md ("The face cycler", "Shuffled sequences", "The name")
and docs/run-and-seeds.md for where the seed comes from.

Run as a script to print what a launch with the given master seed hands out
first, and to run the self-checks:

    python -I scripts/reference/cyclers.py <master seed> NamesM.txt NamesF.txt [count]
"""

import os
import sys

# python -I does not put this folder on the import path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rand import Rand  # noqa: E402

RESHUFFLE_COUNT_MAX = 4      # ShuffledSequence.kReshuffleCountMax
NUM_PALETTES = 6             # FaceSpec.kNumPalettes
NUM_SHEETS_MALE = 5          # FaceSpec.kNumSheetsMale
NUM_SHEETS_FEMALE = 5        # FaceSpec.kNumSheetsFemale
FACES_PER_SHEET = 4          # FaceSpec.kNumFacesPerSheet


def make_shuffled(rand, count):
    """0..count-1 in shuffled order; `count` draws."""
    array = list(range(count))
    for i in range(count):
        n = count - i
        r = rand.random()
        j = int(r * n)
        last = array[n - 1]
        if j < len(array):
            array[n - 1] = array[j]
            array[j] = last
        else:
            # Only when r is exactly 1.0 on the first step: reading past the
            # end of a Haxe array gives nothing (0 as a number) and writing
            # there makes the array one longer. Not checked in this build.
            array[n - 1] = 0
            array.append(last)
    return array


def shuffled_with_max_separation(array, rand):
    """A new order of `array` in which an item cannot come back soon after
    its place in the old order; one draw per item."""
    out = []
    n = len(array)
    separation = int(n * 0.5 - 1.0)
    for i in range(n):
        reach = int(min(float(n), float(n - separation + i)))
        candidates = [array[k] for k in range(reach) if array[k] not in out]
        r = rand.random()
        j = int(len(candidates) * r)
        out.append(candidates[j] if j < len(candidates) else 0)   # past the end: r exactly 1.0
    return out


class ShuffledSequence:
    """Hands out 0..count-1 in a shuffled order, then starts again."""

    def __init__(self, count, seed, reshuffle_on_loop=False, cur=0, reshuffle_count=0):
        self.seed = seed
        self.reshuffle_on_loop = reshuffle_on_loop
        self.cur = cur
        self.reshuffle_count = reshuffle_count
        self.array = make_shuffled(Rand(seed), count)
        if reshuffle_on_loop:
            for k in range(reshuffle_count):
                self.array = shuffled_with_max_separation(self.array, Rand(seed + 1 + k))

    def next(self):
        if self.cur >= len(self.array):
            self.cur = 0
            if self.reshuffle_on_loop:
                if self.reshuffle_count < RESHUFFLE_COUNT_MAX - 1:
                    self.reshuffle_count += 1
                    self.array = shuffled_with_max_separation(
                        self.array, Rand(self.seed + self.reshuffle_count))
                else:
                    self.reshuffle_count = 0
                    self.array = make_shuffled(Rand(self.seed), len(self.array))
        value = self.array[self.cur]
        self.cur += 1
        return value


class FaceCycler:
    """Which face pieces, palette and mirror flag the next random face gets."""

    def __init__(self, seed):
        self.rand = Rand(seed)
        self.pieces_m = self._make_pieces(NUM_SHEETS_MALE, seed + 1)
        self.pieces_f = self._make_pieces(NUM_SHEETS_FEMALE, seed + 2)
        self.palettes = ShuffledSequence(NUM_PALETTES, seed + 3, True)

    @staticmethod
    def _make_pieces(sheets, seed):
        return [ShuffledSequence(FACES_PER_SHEET * sheets, seed + k, True) for k in range(4)]

    def next(self, male):
        """Returns (male, shoulders, head, eyes, nose_mouth, palette, flip)."""
        pieces = self.pieces_m if male else self.pieces_f
        shoulders, head, eyes, nose_mouth = (sequence.next() for sequence in pieces)
        palette = self.palettes.next()
        flip = self.rand.random() > 0.5
        return male, shoulders, head, eyes, nose_mouth, palette, flip


def spec_text(spec):
    male, shoulders, head, eyes, nose_mouth, palette, flip = spec
    return "%s-%d-%d-%d-%d-%d-%d" % ("M" if male else "F", shoulders, head, eyes, nose_mouth,
                                     palette, 1 if flip else 0)


class NameCycler:
    """Hands out first and last names. A fresh one, with no saved position."""

    def __init__(self, names_m_text, names_f_text, seed):
        self.lines_m = names_m_text.split("\n")
        self.lines_f = names_f_text.split("\n")
        self.names_m = ShuffledSequence(len(self.lines_m), seed)
        self.names_f = ShuffledSequence(len(self.lines_f), seed + 1)

    def get(self, male):
        lines = self.lines_m if male else self.lines_f
        sequence = self.names_m if male else self.names_f
        for _ in range(1000):
            words = lines[sequence.next()].split(" ")
            if len(words) == 2:
                return words[0], words[1]      # the game saves the position here
        return "First", "Last"


def _checks(master, names_m_text, names_f_text):
    problems = []
    # Every pass of a sequence hands out each number exactly once.
    for reshuffle in (False, True):
        sequence = ShuffledSequence(20, master + 1, reshuffle)
        passes = [[sequence.next() for _ in range(20)] for _ in range(9)]
        if any(sorted(p) != list(range(20)) for p in passes):
            problems.append("a pass is not a permutation (reshuffle=%s)" % reshuffle)
        if not reshuffle and any(p != passes[0] for p in passes):
            problems.append("a basic sequence changed between passes")
        if reshuffle:
            if passes[4] != passes[0] or passes[5] != passes[1] or passes[8] != passes[0]:
                problems.append("a reshuffling sequence does not repeat every four passes")
            if passes[1] == passes[0]:
                problems.append("a reshuffling sequence did not reshuffle")
            # Across a reshuffle an item returns no sooner than this many steps later.
            gaps = []
            for a, b in zip(passes, passes[1:4]):
                gaps += [20 - a.index(v) + b.index(v) for v in range(20)]
            print("  reshuffling sequence of 20: shortest gap before an item returns:", min(gaps))
    # The overlapping seeds: male heads and female shoulders share seed + 2, and so on.
    cycler = FaceCycler(master)
    males = [cycler.next(True) for _ in range(20)]
    cycler = FaceCycler(master)
    females = [cycler.next(False) for _ in range(20)]
    if [m[2] for m in males] != [f[1] for f in females]:
        problems.append("male heads and female shoulders differ (they share a seed)")
    if [m[3] for m in males] != [f[2] for f in females] or [m[4] for m in males] != [f[3] for f in females]:
        problems.append("male eyes/female heads or male nose-mouth/female eyes differ")
    if [m[3] for m in males[:6]] and ShuffledSequence(NUM_PALETTES, master + 3, True).array != \
            FaceCycler(master).palettes.array:
        problems.append("palette sequence seed")
    names = NameCycler(names_m_text, names_f_text, master)
    seen = [names.get(True) for _ in range(len(names.lines_m) - 1)]
    if len(set(seen)) != len(seen):
        problems.append("a male name repeated within one pass")
    print("  name lists: %d male and %d female entries; carriage returns in the files: %s" % (
        len(names.lines_m), len(names.lines_f), "\r" in names_m_text or "\r" in names_f_text))
    print("  problems:", problems or "none")


def main():
    master = int(sys.argv[1])
    names_m_text = open(sys.argv[2], encoding="utf-8", newline="").read()
    names_f_text = open(sys.argv[3], encoding="utf-8", newline="").read()
    count = int(sys.argv[4]) if len(sys.argv) > 4 else 8

    faces = FaceCycler(master)
    print("master seed %d" % master)
    print("first %d faces if every traveler is male:  " % count,
          " ".join(spec_text(faces.next(True)) for _ in range(count)))
    faces = FaceCycler(master)
    print("first %d faces if every traveler is female:" % count,
          " ".join(spec_text(faces.next(False)) for _ in range(count)))
    names = NameCycler(names_m_text, names_f_text, master)
    print("first %d male names:  " % count, ", ".join(" ".join(names.get(True)) for _ in range(count)))
    print("first %d female names:" % count, ", ".join(" ".join(names.get(False)) for _ in range(count)))
    print("checks:")
    _checks(master, names_m_text, names_f_text)


if __name__ == "__main__":
    main()
