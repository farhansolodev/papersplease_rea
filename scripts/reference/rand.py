"""Reference implementation of the game's random number generator, app.Rand.

The mixing step is the published "sfc32" generator. The seeding (three fixed
constants, the seed in the counter, 15 discarded outputs) is the game's own.
See docs/rand.md.

Run as a script to print values in the same format as
scripts/ghidra/EmulateRand.java, so the two can be compared:

    python -I scripts/reference/rand.py <count> <seed>...
"""

import sys

MASK = 0xFFFFFFFF


class Rand:
    def __init__(self, seed: int) -> None:
        self.a = 0x36AEF51A
        self.b = 0x21D4B3EB
        self.c = 0xF2517ABF
        self.d = seed & MASK
        for _ in range(15):
            self.next_int()

    def next_int(self) -> int:
        """Next value, 0 to 2**31 - 1 inclusive."""
        result = (self.a + self.b + self.d) & MASK
        self.d = (self.d + 1) & MASK
        self.a = self.b ^ (self.b >> 9)
        self.b = (self.c * 9) & MASK
        self.c = (((self.c << 21) | (self.c >> 11)) + result) & MASK
        return result & 0x7FFFFFFF

    def next_float(self) -> float:
        """Next value, 0.0 to 1.0 inclusive. Note: 1.0 is possible."""
        return self.next_int() / 2147483647.0

    # The game's random() is the same as nextFloat().
    random = next_float

    def state(self) -> tuple[int, int, int, int]:
        return self.a, self.b, self.c, self.d


def main() -> None:
    count = int(sys.argv[1])
    for text in sys.argv[2:]:
        seed = int(text)
        rand = Rand(seed)
        state = " ".join(f"{value:08x}" for value in rand.state())
        values = " ".join(str(rand.next_int()) for _ in range(count))
        print(f"seed {seed} state {state} | {values}")


if __name__ == "__main__":
    main()
