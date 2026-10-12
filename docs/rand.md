# app.Rand: the game's random number generator

Studied on 2026-10-12. All nine of the class's own methods were decompiled
and read in full, and the result was checked by running the game's real
machine code in an emulator (see "How it was verified").

Reference implementation: `scripts/reference/rand.py`.

## What it is

A small formula that turns a starting number (the seed) into a fixed, endless
sequence of numbers. The same seed always gives the same sequence.

The mixing step is a published generator called **sfc32** ("small fast
chaotic", by Chris Doty-Humphrey). The way it is started is the game's own.

## State

Four 32-bit whole numbers: `a`, `b`, `c` and a counter `d`.

## Starting it from a seed

```
a = 0x36AEF51A
b = 0x21D4B3EB
c = 0xF2517ABF
d = seed
then produce and throw away 15 numbers
```

## Producing a number: `nextInt()`

All arithmetic wraps around at 32 bits.

```
result = a + b + d
d = d + 1
a = b XOR (b shifted right by 9)
b = c * 9
c = (c rotated left by 21) + result
return result with its top bit cleared      (0 to 2,147,483,647)
```

## Producing a fraction: `nextFloat()` and `random()`

```
nextFloat() = nextInt() / 2147483647.0
random()    = nextFloat()
```

**The result can be exactly 1.0.** The divisor is 2^31 - 1, not 2^31, so the
largest whole number gives 1.0. This happens about once in two billion
draws. Code that turns a fraction into a list position with
`floor(length * r)` therefore has to cope with getting `length` itself; the
game's "pick one from a list" returns nothing in that case rather than
failing. A port that assumed the fraction is always below 1.0 would differ
from the original at that point, or crash.

## Saving and restoring

`getState()` copies the four numbers into an `app.RandState` object;
`setState()` copies them back; `fromState()` makes a new generator from a
saved state. So a generator can be frozen and resumed mid-sequence. Where
this is used (probably the mid-day "stash") is not studied.

## Is this the only source of randomness?

Yes, **with one exception at start-up**:

- **Correction (2026-10-13).** The first check looked only for direct calls
  to `System.Random`'s `Next`, `NextDouble` and `Sample`, and found none.
  That missed calls made through an object's method table. The `Game`
  constructor makes one: when no seed is given (the normal Windows start),
  it takes the game's **master seed** from Haxe's `Math.random()`, which is
  `System.Random.NextDouble()` on a generator seeded from the system's
  tick count. See `run-and-seeds.md`. Every other random number in the game
  comes from `app.Rand` generators derived from that master seed.
- Nothing else in the game was found calling the Haxe library's
  `Std.random` or `Math.random`.
- No class derives from `app.Rand`, so every call lands in the code above.
- The system clock is read by the save header (a timestamp), the frame-rate
  counter, `app.Clock.getSystemTime`, the test automation and the online
  leaderboard code. None of those are random-number sources themselves.

Seventeen places create a generator: the `Day` constructor (four per day,
see `docs/days-csv-format.md`), `play.Bootstrap`, `BoothEnv`,
`CriminalPoster`, `TakeBursts`, `BorderCam`, `ScreenShake`, `PullChain`,
`LoadScreen.loadButton_onClick`, `ShuffledSequence`, `SoundDefLib` and
`FaceCycler`. `BoothEnv` uses the day seed minus `0x7FFFF000` and shares that
generator with its error maker (`traveler-creation.md`). `FaceCycler` and
`ShuffledSequence` derive several generators from one seed, some of them
overlapping; the name cycler's position is saved with the game
(`traveler-build.md`). `play.Bootstrap` makes the story-seed and
endless-seed generators and gives the face and name cyclers the master
seed; the whole chain is in `run-and-seeds.md`. **What seed each of the
remaining sites uses** (`CriminalPoster`, `TakeBursts`, `BorderCam`,
`ScreenShake`, `PullChain`, `LoadScreen`, `SoundDefLib`) **is not
studied.**

## How it was verified

`scripts/ghidra/EmulateRand.java` runs the game's own constructor and
`nextInt` machine code in Ghidra's emulator, using a fake object in scratch
memory. Its output was compared with `scripts/reference/rand.py` for seven
seeds (0, 1, 4146, -1, 2147483647, -2147483648, 123456789): the four state
numbers after construction, and the next 20 outputs. All seven lines were
identical.

```powershell
C:\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat decompiled\ghidra PapersPlease `
  -process GameAssembly.dll -noanalysis -readOnly -scriptPath scripts\ghidra `
  -postScript EmulateRand.java 20 0 1 4146 -1 2147483647 -2147483648 123456789
python -I scripts\reference\rand.py 20 0 1 4146 -1 2147483647 -2147483648 123456789
```

Limits of this check:

- It was not compared against the running game. The emulator executes the
  same instructions the game does, but both the emulator and the decompiler
  are parts of Ghidra, so a mistake in Ghidra's model of an instruction would
  not be caught. These are common instructions, so that is unlikely.
- The division in `nextFloat` was not emulated. The divisor was read
  directly from the DLL's data.
- That `random()` forwards to `nextFloat()` comes from the method slot
  numbers in the recovered metadata (slot 26), not from running it.
