# Haxe's StringMap and IntMap: the order of a lookup table

Studied on 2026-10-13. The game keeps many things in Haxe's lookup tables
(`haxe.ds.StringMap` for text keys, `haxe.ds.IntMap` for number keys). Walking
such a table gives its entries in an order that depends on the keys' hashes
and the table's history, not on the order they were added. In three places
found so far that order decides which random draw goes where:

- the order in which a paper's empty facts are generated (`papers-on-desk.md`);
- the order of the alias letter groups (`value-helpers.md`);
- the order of the letter positions an alias can change (`value-helpers.md`).

Functions read in full: `StringMap` (`set`, `lookup`, `resize`, `get`,
`exists`, `remove`, `keys`, `iterator`, `clear`, constructor), its key and
value iterators; `IntMap` (static setup, constructor, `set`, `lookup`,
`resize`, `remove`, `keys`, `getInc`, `roundUp`, `flagsSize`, `hash`), its
key iterator; `System.String.GetHashCode`; `StringUtil.splitAndTrim`; the
swap-set sort comparison in `Lang.buildAliasSwapSets`. The two load factors
and the swap-set insert were read from the raw instructions.

Everything here is confirmed in the code unless marked otherwise.

## The text hash

**`System.String.GetHashCode`** in this build is the fixed (not randomised)
.NET hash. It reads the text as UTF-16 units and stops at the first NUL:

```
h1 = h2 = 5381
for each pair of units (a, b):
    h1 = (h1 * 33) xor a
    if there is no b: stop
    h2 = (h2 * 33) xor b
result = h1 + h2 * 1566083941        (32-bit wrap-around)
```

**Haxe's mixing** turns that into the table's hash, in six steps, all 32-bit:

```
k = k + 0x7ED55D16 + (k << 12)
k = (k xor 0xC761C23C) xor (k >> 19)
k = k + 0x165667B1 + (k << 5)
k = (k + 0xD3A2646C) xor (k << 9)
k = k + 0xFD7046C5 + (k << 3)
k = (k xor 0xB55A4F09) xor (k >> 16)
```

(`>>` keeps the sign.) A result of 0 becomes 2 and a result of 1 becomes −1,
because 0 and 1 mark empty and deleted buckets.

**Checked against the game's machine code.** `scripts/ghidra/EmulateStringHash.java`
runs the real `StringMap.lookup` and `String.GetHashCode` in Ghidra's
emulator and reads both hashes. For 12 test strings (empty, one to three
letters, fact paths, a face key, non-English letters) both values equal
`scripts/reference/haxemap.py`'s exactly.

## StringMap

Three arrays of the same size (a power of two): one with each bucket's hash
(0 = empty, 1 = deleted), one of keys, one of values.

- **Finding a bucket**: start at `hash & (size − 1)`; on a collision try the
  next bucket at distance 1, then 2, then 3 further (`i = i + step`, step
  growing by one each time).
- **Adding** (`set`): walk the probe sequence until the key or an empty
  bucket; if a deleted bucket was passed, reuse the first one. An empty
  bucket counts as newly "occupied"; a reused deleted one does not.
- **Removing**: mark the bucket deleted (hash 1) and clear key and value.
  The occupied count is not reduced, so removals bring the next resize
  closer.
- **Growing** (`resize`): before adding, if occupied ≥ limit. The new size
  is `size − 1` if fewer than half the buckets hold entries, otherwise
  `size + 2`, rounded up to a power of two, at least 4. The limit is
  `int(new size × 0.77 + 0.5)`. If the number of entries is not below that
  limit, nothing is done. Otherwise every entry is moved to its place in the
  new layout **in place**, in bucket order, displacing (and then moving)
  entries that have not moved yet.
- **Walking** (`keys`, values): buckets 0, 1, 2, ... skipping empty and
  deleted ones.

The first `set` on a new table makes it 4 buckets with a limit of 3.

## IntMap

Same idea, with differences:

- The hash of a number is the number itself.
- Probing uses a fixed step per key: `((k >> 3) xor (k << 3)) | 1`, masked.
- Each bucket has two flag bits (empty, deleted) instead of a stored hash.
- Load factor 0.7 instead of 0.77; growing adds 1 instead of 2 before
  rounding up.
- `lookup` keeps probing past empty buckets until it finds the key or comes
  back to where it started. That only changes speed, not results.

## Results for the game's data

Script: `scripts/checks/map_order_check.py`.

- **Fact generation order.** For 19 documents the walk order of their empty
  facts differs from file order. For `VaccineCert` it is: `VaccineDates`,
  (the document itself), `Name`, `IdNumber`, `Exists`, `VaccineDrugs`,
  `Visible`. So **the vaccine dates are generated before the vaccine
  drugs**.
- **Alias letter groups (English)**, in the game's order:
  `CK, IUY, JL, aeiou, jl, bh, GPQ, BH, gpq, AEIOU, iuy, ck`.
- **Alias positions.** Of 5,278 first and last names in the name lists,
  1,237 have their candidate positions walked in an order other than left to
  right. Example: in `Kristof` the candidates are positions 0, 2 and 5, and
  they are walked as 0, 5, 2.
- **Self-test**: 200 random runs of adds and removes; the reference tables
  always held the same entries as a Python dictionary. This checks
  consistency, not order.

## Notes for the port

- Use `scripts/reference/haxemap.py` as the model. Wherever the original
  walks a `StringMap` or `IntMap` and the order changes an outcome, the port
  must build the same table the same way (same keys, same order of adds and
  removes) and walk it, or precompute the resulting order.
- Places known so far: fact generation per paper, alias groups, alias
  positions. Other walks seen (carrying facts between travelers, saving
  staying papers, expanding `*` fact-group patterns, placeholder maps) have
  not been shown to change a random draw.

## Not checked

- The table logic (`set`, `resize`, walking) was checked by reading and by
  the self-test, not in the emulator: running `set` there would need the
  game's memory allocator. The hash itself was checked in the emulator.
- Nothing here has been compared with the running game.
