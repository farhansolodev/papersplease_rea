"""Reference implementation of Haxe's StringMap and IntMap as compiled into the game.

Both are open-addressing hash tables (the "khash" design). The order in which
they are walked is the bucket order, which depends on the hash function, the
table size and the history of inserts and removals. The game walks such tables
in several places where the order decides random draws (docs/haxe-maps.md).

Run as a script to print the .NET and Haxe hashes of some strings in the same
format as scripts/ghidra/EmulateStringHash.java, so the two can be compared:

    python -I scripts/reference/haxemap.py [string ...]
"""

import sys

MASK = 0xFFFFFFFF


def to_int32(value: int) -> int:
    value &= MASK
    return value - 0x100000000 if value & 0x80000000 else value


def dotnet_string_hash(text: str) -> int:
    """System.String.GetHashCode as compiled here (the non-randomised one).

    Works on UTF-16 code units and stops at the first NUL, like the original.
    """
    data = text.encode("utf-16-le")
    units = [data[i] | data[i + 1] << 8 for i in range(0, len(data), 2)] + [0]
    hash1 = hash2 = 5381
    i = 0
    while units[i] != 0:
        hash1 = ((hash1 * 33) ^ units[i]) & MASK
        if units[i + 1] == 0:
            break
        hash2 = ((hash2 * 33) ^ units[i + 1]) & MASK
        i += 2
    return to_int32(hash1 + hash2 * 1566083941)


def haxe_string_hash(text: str) -> int:
    """StringMap's hash: the .NET hash, mixed; 0 and 1 are reserved."""
    k = dotnet_string_hash(text)
    k = to_int32(k + 0x7ED55D16 + (k << 12))
    k = to_int32((k ^ 0xC761C23C) ^ (k >> 19))
    k = to_int32(k + 0x165667B1 + (k << 5))
    k = to_int32((k + 0xD3A2646C) ^ (k << 9))
    k = to_int32(k + 0xFD7046C5 + (k << 3))
    k = to_int32((k ^ 0xB55A4F09) ^ (k >> 16))
    if k & ~1 == 0:
        k = 2 if k == 0 else -1
    return k


def round_up(x: int) -> int:
    v = (x - 1) & MASK
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    return to_int32(v + 1)


class StringMap:
    """haxe.ds.StringMap. Bucket flags: 0 empty, 1 deleted, otherwise the hash."""

    HASH_UPPER = 0.77

    def __init__(self) -> None:
        self.hashes: list[int] = []
        self.keys_: list = []
        self.vals: list = []
        self.n_buckets = 0
        self.size = 0
        self.n_occupied = 0
        self.upper_bound = 0

    def lookup(self, key: str) -> int:
        if self.n_buckets == 0:
            return -1
        mask = self.n_buckets - 1
        h = haxe_string_hash(key)
        i = h & mask
        step = 0
        while True:
            flag = self.hashes[i]
            if flag == 0:
                return -1
            if flag != 1 and flag == h and self.keys_[i] == key:
                return i
            step += 1
            i = (i + step) & mask

    def set(self, key: str, value) -> None:
        if self.n_occupied >= self.upper_bound:
            if self.size * 2 < self.n_buckets:
                self.resize(self.n_buckets - 1)
            else:
                self.resize(self.n_buckets + 2)
        mask = self.n_buckets - 1 if self.n_buckets else 0
        h = haxe_string_hash(key)
        i = h & mask
        x = i
        if self.hashes[i] != 0:
            site = -1
            step = 0
            found = False
            while True:
                flag = self.hashes[i]
                if flag == 0:
                    break
                if flag == h and self.keys_[i] == key:
                    found = True
                    break
                if flag == 1 and site == -1:
                    site = i
                step += 1
                i = (i + step) & mask
            x = i if found or site == -1 else site
        flag = self.hashes[x]
        if flag == 0:
            self.keys_[x], self.vals[x], self.hashes[x] = key, value, h
            self.size += 1
            self.n_occupied += 1
        elif flag == 1:
            self.keys_[x], self.vals[x], self.hashes[x] = key, value, h
            self.size += 1
        else:
            self.vals[x] = value

    def resize(self, new_n_buckets: int) -> None:
        n = max(round_up(new_n_buckets), 4)
        upper = n * self.HASH_UPPER + 0.5
        if not self.size < upper:
            return
        new_hashes = [0] * n
        old_n = self.n_buckets
        if old_n < n:
            self.keys_ += [None] * (n - old_n)
            self.vals += [None] * (n - old_n)
        keys, vals, hashes = self.keys_, self.vals, self.hashes
        for j in range(old_n):
            h = hashes[j]
            if h & ~1 == 0:
                continue
            key, val = keys[j], vals[j]
            keys[j] = vals[j] = None
            hashes[j] = 1
            while True:
                step = 0
                i = h
                while True:
                    i &= n - 1
                    if new_hashes[i] == 0:
                        break
                    step += 1
                    i += step
                new_hashes[i] = h
                if i >= old_n:
                    break
                h2 = hashes[i]
                if h2 & ~1 == 0:
                    break
                key, keys[i] = keys[i], key
                val, vals[i] = vals[i], val
                hashes[i] = 1
                h = h2
            keys[i], vals[i] = key, val
        if n < old_n:
            del keys[n:]
            del vals[n:]
        self.hashes = new_hashes
        self.n_occupied = self.size
        self.n_buckets = n
        self.upper_bound = int(upper)

    def get(self, key: str):
        i = self.lookup(key)
        return None if i == -1 else self.vals[i]

    def exists(self, key: str) -> bool:
        return self.lookup(key) != -1

    def remove(self, key: str) -> bool:
        i = self.lookup(key)
        if i == -1:
            return False
        self.hashes[i] = 1
        self.keys_[i] = self.vals[i] = None
        self.size -= 1
        return True

    def keys(self):
        for i in range(self.n_buckets):
            if self.hashes[i] & ~1:
                yield self.keys_[i]

    def values(self):
        for i in range(self.n_buckets):
            if self.hashes[i] & ~1:
                yield self.vals[i]


LIVE, DELETED, EMPTY = 0, 1, 2


def _inc(key: int, mask: int) -> int:
    return ((key >> 3) ^ to_int32(key << 3) | 1) & mask


class IntMap:
    """haxe.ds.IntMap. The hash of a key is the key itself."""

    HASH_UPPER = 0.7

    def __init__(self) -> None:
        self.state: list[int] = []
        self.keys_: list[int] = []
        self.vals: list = []
        self.n_buckets = 0
        self.size = 0
        self.n_occupied = 0
        self.upper_bound = 0

    def lookup(self, key: int) -> int:
        """As compiled: probes until the key is found in a used bucket or the
        probe sequence returns to its start (it does not stop at an empty
        bucket)."""
        if self.n_buckets == 0:
            return -1
        mask = self.n_buckets - 1
        start = i = key & mask
        while True:
            if self.keys_[i] == key and self.state[i] != EMPTY:
                return i if self.state[i] == LIVE else -1
            i = (i + _inc(key, mask)) & mask
            if i == start:
                return -1

    def set(self, key: int, value) -> None:
        if self.n_occupied >= self.upper_bound:
            if self.size * 2 < self.n_buckets:
                self.resize(self.n_buckets - 1)
            else:
                self.resize(self.n_buckets + 1)
        mask = self.n_buckets - 1
        i = key & mask
        if self.state[i] != EMPTY:
            site = -1
            flag = 0
            while True:
                if self.keys_[i] == key:
                    break
                flag = self.state[i]
                if flag == EMPTY:
                    break
                if site == -1 and flag == DELETED:
                    site = i
                i = (i + _inc(key, mask)) & mask
            if site != -1 and self.state[i] == EMPTY:
                i = site
        state = self.state[i]
        if state == EMPTY:
            self.keys_[i], self.vals[i], self.state[i] = key, value, LIVE
            self.size += 1
            self.n_occupied += 1
        elif state == DELETED:
            self.keys_[i], self.vals[i], self.state[i] = key, value, LIVE
            self.size += 1
        else:
            self.vals[i] = value

    def resize(self, new_n_buckets: int) -> None:
        n = max(round_up(new_n_buckets), 4)
        upper = n * self.HASH_UPPER + 0.5
        if not self.size < upper:
            return
        new_state = [EMPTY] * n
        old_n = self.n_buckets
        if old_n < n:
            self.keys_ += [0] * (n - old_n)
            self.vals += [None] * (n - old_n)
        keys, vals, state = self.keys_, self.vals, self.state
        for j in range(old_n):
            if state[j] != LIVE:
                continue
            key, val = keys[j], vals[j]
            vals[j] = None
            state[j] = DELETED
            while True:
                i = key
                while True:
                    i &= n - 1
                    if new_state[i] == EMPTY:
                        break
                    i += _inc(key, n - 1)
                new_state[i] = LIVE
                if i >= old_n or state[i] != LIVE:
                    break
                key, keys[i] = keys[i], key
                val, vals[i] = vals[i], val
                state[i] = DELETED
            keys[i], vals[i] = key, val
        if n < old_n:
            del keys[n:]
            del vals[n:]
        self.state = new_state
        self.n_occupied = self.size
        self.n_buckets = n
        self.upper_bound = int(upper)

    def get(self, key: int):
        i = self.lookup(key)
        return None if i == -1 else self.vals[i]

    def remove(self, key: int) -> bool:
        i = self.lookup(key)
        if i == -1:
            return False
        self.state[i] = DELETED
        self.vals[i] = None
        self.size -= 1
        return True

    def keys(self):
        for i in range(self.n_buckets):
            if self.state[i] == LIVE:
                yield self.keys_[i]


DEFAULTS = ["", "a", "ab", "abc", "Passport/Name", "VaccineCert/VaccineDates",
            "VaccineCert/VaccineDrugs", "Traveler/Nationality", "M0:0", "aeiou",
            "Über ß", "Rules/RuleArstotzkaOnly"]


def main() -> None:
    for text in sys.argv[1:] or DEFAULTS:
        quoted = '"' + "".join(c if ord(c) < 128 else f"\\u{ord(c):04x}" for c in text) + '"'
        raw = dotnet_string_hash(text) & MASK
        mixed = haxe_string_hash(text) & MASK
        print(f"{quoted:<28} raw {raw:08x} haxe {mixed:08x}")


if __name__ == "__main__":
    main()
