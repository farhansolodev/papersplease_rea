"""Reference implementation of how the game derives its seeds.

From the launch's master seed to the story seeds and each story day's
generator seeds. See docs/run-and-seeds.md, docs/days-csv-format.md and
docs/traveler-creation.md. All arithmetic wraps at 32 bits, as in the game.

Run as a script:

    python -I scripts/reference/seeds.py <master seed> <number of loads> <day>...

It prints the story seeds (the first is drawn at start-up, one more per
loaded save) and, for each given day, the seeds of its generators under the
first story seed.
"""

import os
import sys

# python -I does not put this folder on the import path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rand import Rand  # noqa: E402

MASK = 0xFFFFFFFF


def to_int32(value: int) -> int:
    value &= MASK
    return value - 0x100000000 if value & 0x80000000 else value


class Launch:
    """What play.Bootstrap derives from the master seed."""

    def __init__(self, master: int) -> None:
        self.master = to_int32(master)
        self.endless_seed_gen = Rand(self.master + 26)
        self.story_seed_gen = Rand(self.master + 73)
        self.face_cycler_seed = self.master
        self.name_cycler_seeds = (self.master, to_int32(self.master + 1))
        # setLanguage at the end of the constructor creates the day run.
        self.story_seed = self.story_seed_gen.next_int()

    def load_save(self) -> int:
        """Loading a save draws a new story seed (advanceStorySeed)."""
        self.story_seed = self.story_seed_gen.next_int()
        return self.story_seed


def day_seeds(day: int, story_seed: int) -> dict[str, int]:
    seed = to_int32(day * 50 + story_seed)
    return {
        "day": seed,
        "news": to_int32(seed + 0x1000),
        "border": to_int32(seed + 0x2000),
        "night": to_int32(seed + 0x3000),
        "traveler": to_int32(seed + 0x4000),
        "booth": to_int32(seed - 0x7FFFF000),
    }


def main() -> None:
    master = int(sys.argv[1])
    loads = int(sys.argv[2])
    days = [int(text) for text in sys.argv[3:]]
    launch = Launch(master)
    first = launch.story_seed
    stories = [first] + [launch.load_save() for _ in range(loads)]
    print(f"master {launch.master}: story seeds {stories}")
    for day in days:
        seeds = " ".join(f"{name}={value}" for name, value in day_seeds(day, first).items())
        print(f"day {day}: {seeds}")


if __name__ == "__main__":
    main()
