"""Reference implementation of how a language pack changes the game's files:
data.loc.Pack (load, makeEnKey, cleanHtml, localize) and the 27 extractors of
data.loc.Extractors.init (docs/language-pack.md).

Run as a script to compare a pack with the extracted archive and list every
text the pack changes in the data files:

    python -I scripts/reference/locpack.py <assets dir> <pack.zip>

for example `extracted/art/assets` and
`game/PapersPlease_Data/StreamingAssets/loc/en.zip`. For en.zip the expected
result is in docs/language-pack.md: 2,102 pieces found, 8 not found, 23
texts changed.

Not modelled: data.CsvTable itself (Python's csv reader, with every cell
trimmed, as docs/days-csv-format.md says); Haxe's XML reader (a lenient
clean-up before Python's, as the checks do); TabEntry.set_text (a changed
text is reported, not written back).
"""

import csv
import io
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402

# Pack's class setup: the two patterns of makeEnKey, and cleanHtml's table
# (a Haxe StringMap; the replacements do not overlap, so order is not needed).
KEY_STRIP_MARKUP = re.compile(r"(?:\\n)|(?:<[^>]*>)|(?:&[^;]*;)", re.I)
KEY_STRIP_OTHER = re.compile(r"[^A-Za-z0-9@]")
CLEAN_HTML = [("\\n", "\n"), ("<br>", "\n"), ("<br/>", "\n"),
              ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")]


def make_en_key(text):
    """CRC-32 of the text without markup, spaces and punctuation."""
    text = KEY_STRIP_OTHER.sub("", KEY_STRIP_MARKUP.sub("", text))
    return zlib.crc32(text.encode("utf-8"))


def clean_html(text):
    for old, new in CLEAN_HTML:
        text = text.replace(old, new)
    return text


def read_csv(text):
    """Rows of cells, each trimmed (data.CsvTable trims every cell)."""
    return [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(text))]


class Pack:
    """Pack.load: the files by their game name, and the text table."""

    def __init__(self, zip_path):
        self.files = {}
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                if info.compress_type != zipfile.ZIP_STORED:
                    raise ValueError("This language pack has compressed entries, which are not supported.")
                name = info.filename
                if name.startswith("/"):
                    name = name[1:]
                if name.startswith("./"):
                    name = name[2:]
                self.files["assets/" + name] = z.read(info.filename)
        if "assets/data/Loc.csv" not in self.files:
            raise ValueError("Loc.csv not found.")
        if "assets/data/LocVersion.txt" not in self.files:
            raise ValueError("Unknown language pack version.")
        self.version = int(self.files["assets/data/LocVersion.txt"].decode("utf-8").strip() or 0)
        self.strings = {}
        for row in read_csv(self.files["assets/data/Loc.csv"].decode("utf-8")):
            self.strings.setdefault(row[0], {})[make_en_key(row[1])] = clean_html(row[2])
        del self.files["assets/data/Loc.csv"]

    def localize(self, context, text):
        """Pack.localize: the new text, or None when nothing is replaced."""
        if not text:
            return None
        table = self.strings.get(context)
        if table is None:
            return None
        return table.get(make_en_key(text))


# ---------------------------------------------------------------- extractors
# Each yields (context, text) for every piece of text the game would offer
# to the pack.

def tab_pieces(text, prefix, match):
    """TabExtractor.run / runSubs: every line below each top-level entry."""
    def walk(node, context):
        for child in node.nodes:
            span = match(child.params)
            if span is not None:
                yield context, " ".join(child.params[span[0]:span[1]])
            if child.nodes:
                yield from walk(child, context)

    for top in tabtree.parse(text).nodes:
        yield from walk(top, prefix + top.params[0])


def match_speech(p):  # Extractors_init_32
    i = 1 if p[0].startswith("=") or p[0].startswith("?") else 0
    if p[i].startswith("?"):
        i += 1
    if len(p) == i + 1 and p[i].startswith("$"):
        return None
    return i, len(p)


def match_traveler(p):  # Extractors_init_40: spoken lines
    if p[0] != '"' or (len(p) == 2 and p[1].startswith("$")):
        return None
    return 1, len(p)


def match_note(p):  # Extractors_init_52: an end below 0 means the line's length
    if p[0] == "=" and len(p) > 1 and p[1] == "EzicNote/Message":
        return 2, len(p)
    return None


def match_news(p):  # Extractors_init_57: headline and subtitle
    return (1, len(p)) if p[0] in ("*", "-") else None


def match_night(p):  # Extractors_init_64: spoken lines and budget lines
    if p[0] == '"':
        return 1, len(p)
    if p[0] == ">" and p[1] not in ("YES", "NO"):
        return 1, (p.index("|", 1) if "|" in p[1:] else len(p))
    return None


def read_xml(text):
    """A lenient clean-up so Python's strict reader accepts the game's files:
    comments made of dashes are removed and a bare & is kept as text."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", text))


def xml_select(xml, path):  # XmlExtractor.select
    if "/" not in path:
        return [xml] if path == "" else xml.findall(path)
    head, rest = path.split("/", 1)
    return [found for child in xml.findall(head) for found in xml_select(child, rest)]


def xml_attrs(xml, path, accept):  # XmlExtractor.runChildren
    if "/" not in path:
        value = xml.get(path)
        if value is not None and (accept is None or accept(value)):
            yield value
        return
    head, rest = path.split("/", 1)
    for child in xml.findall(head):
        yield from xml_attrs(child, rest, accept)


def xml_pieces(text, prefix, root_path, attr_path, accept=None):  # XmlExtractor.run
    for element in xml_select(read_xml(text), root_path):
        for value in xml_attrs(element, attr_path, accept):
            yield prefix + element.get("id", ""), value


def ignore_dollar_signs(value):
    return "$" not in value


def not_rule_picture(value):  # Extractors_init_96
    return "[" not in value and ".png" not in value


def csv_pieces(text, prefix, two_pages):  # CsvExtractor.run
    rows = read_csv(text)
    by_name = {row[0]: row for row in rows}

    def cell(name, col):
        row = by_name.get(name, [])
        return row[col] if col < len(row) else ""

    for col, day in enumerate(rows[0]):
        if col == 0 or not day:
            continue
        if cell("BULLETIN0", col) == "":
            continue
        yield prefix + day + "A", cell("BULLETIN0", col)
        if two_pages:
            yield prefix + day + "B", cell("BULLETIN1", col)


def extractors():
    """(file name, function from the file's text to its pieces), in the
    order of Extractors.init."""
    xml = [
        ("Facts.xml", "facts", "", "locs/loc/val", None),
        ("Facts.xml", "facts", "", "paper/fact/cite", None),
        ("Facts.xml", "facts", "", "paper/fact/cite/val", None),
        ("Facts.xml", "facts", "", "paper/cite", None),
        ("Facts.xml", "facts", "", "paper/fact/val", not_rule_picture),
        ("Facts.xml", "facts", "", "confiscations/confiscation/desc", None),
        ("Facts.xml", "facts", "", "confiscations/confiscation/error", None),
        ("Papers.xml", "paper:", "paper", "page/mark/text", ignore_dollar_signs),
        ("Ends.xml", "end:", "end", "page/text", ignore_dollar_signs),
        ("Intro.xml", "intro", "", "page/text", ignore_dollar_signs),
    ] + [("Faces.xml", "face:", "sheet/face", a, None)
         for a in ("head", "eyes", "mouth", "nhead", "neyes", "nmouth")] + [
        ("Endlesses.xml", "endless:", "style", "name", None),
        ("Endlesses.xml", "endless:", "style", "desc", None),
        ("Endlesses.xml", "endless:", "style", "bulletin", None),
        ("Endlesses.xml", "endless:", "course", "name", None),
    ]
    yield from [
        ("Speeches.txt", lambda t: tab_pieces(t, "speech:", match_speech)),
        ("Travelers.txt", lambda t: tab_pieces(t, "traveler:", match_traveler)),
        ("Travelers.txt", lambda t: tab_pieces(t, "note:", match_note)),
        ("News.txt", lambda t: tab_pieces(t, "news:", match_news)),
        ("Nights.txt", lambda t: tab_pieces(t, "night:", match_night)),
    ]
    for name, prefix, root_path, attr_path, accept in xml:
        yield name, (lambda t, p=prefix, r=root_path, a=attr_path, f=accept:
                     xml_pieces(t, p, r, a, f))
    yield "Days.csv", lambda t: csv_pieces(t, "bulletin:", True)
    yield "Endless.csv", lambda t: csv_pieces(t, "bullend:", False)


def apply(pack, data_dir):
    """Run every extractor over the data files. Returns (found, not_found,
    changes, used_contexts); a change is (context, file, old text, new text)."""
    found, not_found, changes, used = 0, [], [], set()
    for name, pieces in extractors():
        with open(os.path.join(data_dir, name), encoding="utf-8") as f:
            text = f.read()
        for context, old in pieces(text):
            if not old:
                continue
            new = pack.localize(context, old)
            if new is None:
                not_found.append((context, name, old))
                continue
            found += 1
            used.add(context)
            if new != old:
                changes.append((context, name, old, new))
    return found, not_found, changes, used


def compare_files(pack, assets_dir):
    """The pack's files against the extracted archive: (same, differ, only in
    the pack)."""
    same, differ, only = [], [], []
    for name, data in sorted(pack.files.items()):
        path = os.path.join(assets_dir, name[len("assets/"):])
        if not os.path.exists(path):
            only.append(name)
        elif open(path, "rb").read() == data:
            same.append(name)
        else:
            differ.append(name)
    return same, differ, only


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    assets_dir, zip_path = sys.argv[1], sys.argv[2]
    pack = Pack(zip_path)
    same, differ, only = compare_files(pack, assets_dir)
    print(f"pack files (without Loc.csv): {len(pack.files)}; version {pack.version}")
    print(f"  same as the archive: {len(same)}; different: {len(differ)}; only in the pack: {len(only)}")
    for name in differ:
        print("  different:", name)
    for name in only:
        print("  only in the pack:", name)

    found, not_found, changes, used = apply(pack, os.path.join(assets_dir, "data"))
    contexts = [c for c in pack.strings if c != "CONTEXT"]
    print(f"pieces found: {found}; not found: {len(not_found)}")
    for context, name, old in not_found:
        print(f"  not found: {context} ({name}) {old[:60]!r}")
    print(f"contexts used: {len(used)} of {len(contexts)}")
    print(f"texts changed: {len(changes)}")
    for context, name, old, new in changes:
        print(f"  {context} ({name})")
        print(f"    before: {old!r}")
        print(f"    after:  {new!r}")


if __name__ == "__main__":
    main()
