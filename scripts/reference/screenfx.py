"""Reference for the screen shake and the screen flash:
play.screen.ScreenShake and play.screen.ScreenFlash (docs/screens.md, part 11).

ScreenShake: every screen owns one, with its own generator seeded
0x6500065. While a shake runs, each update draws one random() and moves
the screen by a whole-pixel offset in that direction:

    amount = (1 - min(elapsed, duration) / duration) ** 1.5 * magnitude
    angle  = random() * 2 * pi
    x = floor(cos(angle) * amount), y = floor(sin(angle) * amount)

The update where amount falls below 0.001 draws nothing, ends the shake
and puts the screen back at (0, 0).

ScreenFlash: the white flash of a "flash to the title" and the black fade
cover. flash(t) gives (black alpha, white alpha) t seconds into the flash.

    python -I scripts/reference/screenfx.py shake  <fps> <start:duration:magnitude>...
    python -I scripts/reference/screenfx.py poison [fps]
    python -I scripts/reference/screenfx.py flash  <duration> [fps]

`shake` lists, frame by frame, the offset of a screen made at time 0 that
gets the given shakes (times in seconds). `poison` is the booth's poisoned
state (shakes at 0, 2 and 4 s; the flash starts at 6 s, when the screen
stops being updated, so the offset of the last frame before 6 s stays on
screen). Assumed, not read: a shake started in a frame is already applied
by that frame's update, and frame k is k / fps seconds after the screen
was made. Python's cos, sin
and pow are not the game's own (MSVC's); a difference could only show
where a product lands exactly on a whole number.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rand import Rand  # noqa: E402

SHAKE_SEED = 0x6500065   # 105,906,277; a new generator per screen
SHAKE_POWER = 1.5
SHAKE_STOP = 0.001
FLASH_FADE = 2.0         # Game's second argument to startFlash
CLOCK_BASE = 100.0       # stands in for the game clock's time when the screen is made

# The booth's "poisoned" state (Booth constructor): (time, duration, magnitude).
POISON_SHAKES = [(0.0, 0.5, 2.0), (2.0, 1.0, 2.0), (4.0, 6.0, 3.0)]
POISON_FLASH_AT = 6.0
POISON_FLASH = 3.0
# The other two users.
BORDER_EXPLOSION_SHAKE = (1.0, 2.0)   # Border.spawnExplosion
BOMB_FLASH = 0.1                      # Booth.timeBombExplode, grenade on the booth


class ScreenShake:
    def __init__(self) -> None:
        self.rand = Rand(SHAKE_SEED)
        self.start_time = 0.0
        self.duration = 0.0
        self.magnitude = 0.0
        self.pos = (0, 0)

    def start(self, now: float, duration: float, magnitude: float) -> None:
        # A new shake replaces a running one.
        self.duration = duration
        self.magnitude = magnitude
        self.start_time = now

    def update(self, now: float) -> None:
        # The game tests the start time against 0, so a shake started at
        # clock time exactly 0 would never run.
        if self.start_time == 0.0:
            return
        elapsed = min(now - self.start_time, self.duration)
        elapsed = max(elapsed, 0.0)
        amount = math.pow(1.0 - elapsed / self.duration, SHAKE_POWER) * self.magnitude
        if amount < SHAKE_STOP:
            self.start_time = 0.0
            self.pos = (0, 0)
            return
        angle = self.rand.random() * 2.0 * math.pi
        self.pos = (int(math.floor(math.cos(angle) * amount)),
                    int(math.floor(math.sin(angle) * amount)))


def flash(t: float, duration: float, fade: float = FLASH_FADE) -> tuple[float, float]:
    """(black alpha, white alpha) t seconds after the flash started.
    Before it, the black cover is at whatever the fade left (0 while playing)."""
    after = max(0.0, min(1.0, (t - duration) / fade))
    if after > 0.0:
        return 1.0, 1.0 - after
    return 0.0, min(1.0, t / duration)


def run_shakes(fps: float, starts: list[tuple[float, float, float]],
               freeze_at: float | None = None) -> tuple[list[tuple[float, int, int]], int]:
    """Frame by frame (time, x, y) for frames at k / fps, k = 0, 1, ...,
    and the number of random draws. Times are seconds since the screen was
    made; the game's clock is not 0 then (CLOCK_BASE stands in for it)."""
    shaker = ScreenShake()
    pending = sorted(starts)
    last = max(s + d for s, d, _ in starts) + 0.25
    rows = []
    draws = 0
    k = 0
    while True:
        t = k / fps
        if t > last + 1e-9:
            break
        if freeze_at is not None and t >= freeze_at - 1e-9:
            break
        while pending and pending[0][0] <= t + 1e-9:
            _, duration, magnitude = pending.pop(0)
            shaker.start(CLOCK_BASE + t, duration, magnitude)
        before = shaker.rand.state()
        shaker.update(CLOCK_BASE + t)
        if shaker.rand.state() != before:
            draws += 1
        rows.append((t, shaker.pos[0], shaker.pos[1]))
        k += 1
    return rows, draws


def print_rows(rows: list[tuple[float, int, int]]) -> None:
    previous = None
    for t, x, y in rows:
        if (x, y) != previous or (x, y) != (0, 0):
            print(f"{t:7.3f}  x {x:+d}  y {y:+d}")
        previous = (x, y)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "shake":
        fps = float(sys.argv[2])
        starts = []
        for text in sys.argv[3:]:
            s, d, m = (float(v) for v in text.split(":"))
            starts.append((s, d, m))
        rows, draws = run_shakes(fps, starts)
        print_rows(rows)
        print(f"random draws: {draws}")
    elif mode == "poison":
        fps = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
        rows, draws = run_shakes(fps, POISON_SHAKES, freeze_at=POISON_FLASH_AT)
        print_rows(rows)
        t, x, y = rows[-1]
        print(f"frozen from {POISON_FLASH_AT:.3f} at x {x:+d} y {y:+d}; "
              f"flash {POISON_FLASH} s + fade {FLASH_FADE} s, title at "
              f"{POISON_FLASH_AT + POISON_FLASH + FLASH_FADE:.3f}")
        print(f"random draws: {draws}")
    elif mode == "flash":
        duration = float(sys.argv[2])
        fps = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
        steps = int(round((duration + FLASH_FADE) * fps))
        for k in range(steps + 1):
            t = k / fps
            black, white = flash(t, duration)
            print(f"{t:6.3f}  black {black:.3f}  white {white:.3f}")
        print(f"title at {duration + FLASH_FADE:.3f} s")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
