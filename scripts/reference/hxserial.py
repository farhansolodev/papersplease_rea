"""Read text written by Haxe's general serializer (haxe.Serializer).

The game's `stash` store entry is written this way (docs/save-format.md,
part 2). This reader covers the codes seen in a real stash plus a few
neighbours; it is not a full implementation. Unknown codes raise an error
instead of being skipped.

The text is a run of values, each starting with a one-letter code:

    n null      t true      f false     z the number 0
    i<digits>   a whole number          d<digits>  a number with a fraction
    y<len>:<text>   a string, URL-encoded, <len> counted after encoding
    R<n>            the n-th string seen so far (strings are not repeated)
    c<name><field><value>...g   an object of a class: field name, value, ...
    o<field><value>...g         an object without a class
    w<enum><constructor>:<n><args>   an enum value, written by name
    j<enum>:<index>:<n><args>        an enum value, written by number
    l...h  a list     a...h  an array (u<n> inside means n nulls)
    b<key><value>...h  a map with text keys
    q:<key><value>...h a map with number keys
    r<n>   the n-th object seen so far

Values come back as plain Python: dict for an object (its class under the
key "__class"), list for a list or array, dict for a map, and
("enum", enum name, constructor, arguments) for an enum value.
"""

from urllib.parse import unquote

NUMBER_CHARS = "0123456789+-.eE"


class Reader:
    def __init__(self, text: str):
        self.s = text
        self.p = 0
        self.strings = []
        self.objects = []

    def _digits(self) -> int:
        start = self.p
        while self.p < len(self.s) and (self.s[self.p].isdigit()
                                        or self.s[self.p] == "-"):
            self.p += 1
        return int(self.s[start:self.p])

    def _expect(self, ch: str) -> None:
        if self.s[self.p] != ch:
            raise ValueError(f"expected {ch!r} at {self.p}")
        self.p += 1

    def _pairs_until(self, end: str, into: dict) -> dict:
        while self.s[self.p] != end:
            key = self.read()
            into[key] = self.read()
        self.p += 1
        return into

    def read(self):
        code = self.s[self.p]
        self.p += 1
        if code == "n":
            return None
        if code == "t":
            return True
        if code == "f":
            return False
        if code == "z":
            return 0
        if code == "i":
            return self._digits()
        if code == "d":
            start = self.p
            while self.p < len(self.s) and self.s[self.p] in NUMBER_CHARS:
                self.p += 1
            return float(self.s[start:self.p])
        if code == "y":
            length = self._digits()
            self._expect(":")
            value = unquote(self.s[self.p:self.p + length])
            self.p += length
            self.strings.append(value)
            return value
        if code == "R":
            return self.strings[self._digits()]
        if code == "r":
            return self.objects[self._digits()]
        if code == "c":
            obj = {"__class": self.read()}
            self.objects.append(obj)
            return self._pairs_until("g", obj)
        if code == "o":
            obj = {}
            self.objects.append(obj)
            return self._pairs_until("g", obj)
        if code in "wj":
            enum_name = self.read()
            if code == "w":
                constructor = self.read()
            else:
                self._expect(":")
                constructor = self._digits()
            self._expect(":")
            count = self._digits()
            args = [self.read() for _ in range(count)]
            value = ("enum", enum_name, constructor, args)
            self.objects.append(value)
            return value
        if code in "la":
            items = []
            self.objects.append(items)
            while self.s[self.p] != "h":
                if self.s[self.p] == "u":
                    self.p += 1
                    items.extend([None] * self._digits())
                else:
                    items.append(self.read())
            self.p += 1
            return items
        if code == "b":
            mapping = {}
            self.objects.append(mapping)
            return self._pairs_until("h", mapping)
        if code == "q":
            mapping = {}
            self.objects.append(mapping)
            while self.s[self.p] == ":":
                self.p += 1
                key = self._digits()
                mapping[key] = self.read()
            self._expect("h")
            return mapping
        raise ValueError(f"unknown code {code!r} at {self.p - 1}")


def unserialize(text: str):
    """The first value in `text`, and how many characters it used."""
    reader = Reader(text)
    value = reader.read()
    return value, reader.p


def fact_texts(fact_set: dict) -> dict:
    """A serialized data.FactSet -> {fact path: its text}."""
    out = {}
    for path, fact in fact_set["facts"].items():
        value = fact.get("value")
        out[path] = None if value is None else value.get("text")
    return out
