"""Reference for laying out one document page: data.Page.getInnerImageAndMarkPositions
and the play.day.PaperInnerVisuals constructor (docs/page-layout.md).

A page is a picture plus marks (Papers.xml). Each mark gets a position, either
its `pos` (or a random point between `pos` and `pos2`), or the next marker
pixel of its side in the page picture: opaque black for side 0, a second
marker colour for side 1 (see MARKER). Marker pixels are painted over with the
pixel before them. Then each mark becomes a text, a picture or a seal, placed
by its alignment and flow.

    python -I scripts/reference/pages.py <assets dir> <paper id> [page index] [options]

Options: --nation N (which Passport), --values "k=v;k=v" (fact values; others
show their fact name; a picture fact's value is a file in assets/papers),
--mask "id id" (the paper's PageMask text), --upgrade (the rulebook tabs
upgrade), --face SPEC (a face for the document and criminal photos, e.g.
M-3-7-12-1-2-0), --prints CODE (fingerprints, e.g. 31415), --seed N (their
draws), --png out.png [--scale N].

Fact pictures come from factpics.py (BoothEnv.getImage) where the preview
knows the value (see picture_source); the others are left out, as the game
leaves out a mark with no picture. Not modelled: what a fact's text is
(BoothEnv.getLocalizedText, given here by --values), the search photo,
a seal mark's picture, the Transcript's page count, the rules and news
fact renames.
"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fonts  # noqa: E402
from text import Text  # noqa: E402

# the two marker colours, as the game's 32-bit pixel value; see MARKER_RGBA
MARKER_SIDE0 = 0xFF000000
MARKER_SIDE1 = 0xFFFF0000
# the same as (r, g, b, a) in the PNG; which of red or blue side 1 is was
# settled against the page pictures (scripts/checks/page_layout_check.py)
MARKER_RGBA = {(0, 0, 0, 255): 0, (255, 0, 0, 255): 1}
SMALL_FIELD = 55            # a constant in the constructor (touch padding, phone and tablet only)
LINK_BUTTON_PADDING = 1     # paddingX and paddingY of a text with a link
INHERITED = ("align", "flow", "font", "textcolor", "backcolor", "wrap", "flowpad",
             "side", "scale", "emblemrect", "inspectable")


def parse_point(text):
    parts = (text or "").split(" ")
    try:
        return (float(parts[0]), float(parts[1])) if len(parts) == 2 else (0.0, 0.0)
    except ValueError:
        return (0.0, 0.0)


def parse_rect(text):
    parts = (text or "").split(" ")
    try:
        return tuple(float(p) for p in parts) if len(parts) == 4 else (0.0, 0.0, 100.0, 100.0)
    except ValueError:
        return (0.0, 0.0, 100.0, 100.0)


def parse_color(text):
    return int(text, 16) | 0xFF000000 if text else 0


class Mark:
    def __init__(self, attrs):
        a = attrs.get
        if a("text") is not None:
            self.type, self.text, self.image = "TEXT", a("text"), None
        elif a("image") is not None:
            self.type, self.text, self.image = "IMAGE", None, a("image")
        elif a("emblem") is not None:
            self.type, self.text, self.image = "EMBLEM", None, None
        else:
            self.type = None
        self.emblem = a("emblem")
        self.align = (a("align") or "left").upper()
        self.flow = (a("flow") or "none").upper()
        self.font = a("font") or "regular"
        self.text_color = parse_color(a("textcolor"))
        self.back_color = 0 if a("backcolor") in (None, "0") else parse_color(a("backcolor"))
        self.wrap = int(a("wrap") or 0)
        self.flow_pad = int(a("flowpad") or 0)
        self.side = int(a("side") or 0)
        self.scale = float(a("scale") or 1.0)
        self.emblem_rect = parse_rect(a("emblemrect"))
        self.link = a("link")
        self.pos = parse_point(a("pos")) if a("pos") is not None else None
        self.pos2 = parse_point(a("pos2")) if a("pos2") is not None else None
        self.clip_height = int(a("clipheight") or 0)

    def fact_id(self):
        """Mark.getFactId (the proxy is not used for drawing)."""
        if self.type == "TEXT" and self.text.startswith("$"):
            return self.text[1:]
        if self.type == "IMAGE" and self.image.startswith("$"):
            return self.image[1:]
        if self.type == "EMBLEM":
            return "Emblem/" + self.emblem
        return None

    def random_force_pos(self, rand):
        """Mark.getRandomForcePos: pos as it is, or a whole-pixel point between pos and pos2."""
        if self.pos2 is None or rand is None:
            return self.pos
        rx, ry = rand.random(), rand.random()
        x = (self.pos2[0] - self.pos[0]) * rx + self.pos[0]
        y = (self.pos2[1] - self.pos[1]) * ry + self.pos[1]
        return (float(int(x // 1)), float(int(y // 1)))


class Page:
    def __init__(self, node, defaults):
        attrs = dict(defaults)
        attrs.update({k: v for k, v in node.attrib.items()})
        self.id = node.get("id") or "none"
        self.image = node.get("image")
        page_defaults = {k: attrs[k] for k in INHERITED if k in attrs}
        self.marks = []
        for m in node.findall("mark"):
            mark_attrs = dict(page_defaults)
            mark_attrs.update(m.attrib)
            mark = Mark(mark_attrs)
            if mark.type is not None:
                self.marks.append(mark)


class PaperDef:
    def __init__(self, node):
        self.id, self.nation = node.get("id"), node.get("nation") or ""
        defaults = {k: v for k, v in node.attrib.items() if k in INHERITED}
        self.pages = [Page(p, defaults) for p in node.findall("page")]


def load(assets_dir):
    root = ET.parse(os.path.join(assets_dir, "data", "Papers.xml")).getroot()
    return [PaperDef(p) for p in root.findall("paper")]


def mark_positions(page, image, rand=None):
    """Page.getInnerImageAndMarkPositions. `image` is a Pillow RGBA picture,
    changed in place (marker pixels painted over). Returns one (x, y) per mark."""
    positions = []
    waiting = {0: [], 1: []}
    for index, mark in enumerate(page.marks):
        if mark.pos is None:
            positions.append((0.0, 0.0))
            waiting[mark.side].append(index)
        else:
            positions.append(mark.random_force_pos(rand))
    px = image.load()
    previous = (0, 0, 0, 0)          # the pixel read before; 0 before the first
    for y in range(image.height):
        for x in range(image.width):
            pixel = px[x, y]
            side = MARKER_RGBA.get(pixel)
            if side is not None:
                if waiting[side]:
                    positions[waiting[side].pop(0)] = (float(x), float(y))
                px[x, y] = previous
            previous = pixel
    return positions


class Nav:
    """PaperNav: which pages exist, from the paper's PageMask text."""

    def __init__(self, paper, page_mask="", transcript_pages=None):
        self.paper, self.mask, self.transcript_pages = paper, page_mask or "", transcript_pages

    def has_page(self, index):
        if self.paper.id == "Transcript" and self.transcript_pages is not None \
                and index >= self.transcript_pages:
            return False
        if not self.mask:
            return True
        return index < len(self.paper.pages) and self.paper.pages[index].id in self.mask   # a substring test

    def has_page_from_id(self, page_id):
        return page_id in self.mask if self.mask else True

    def next_index(self, index):
        while True:
            index += 1
            if index >= len(self.paper.pages):
                return -1
            if self.has_page(index):
                return index

    def prev_index(self, index):
        found = -1
        for i in range(index):
            if self.has_page(i):
                found = i
        return found

    def existing_page_id(self, link):
        for part in link.split(","):
            if self.has_page_from_id(part):
                return part
        return None


class Placed:
    def __init__(self, index, kind, mark, x, y, text=None, size=None, clip=None, picture=None):
        self.index, self.kind, self.mark = index, kind, mark
        self.x, self.y, self.text, self.size, self.clip = x, y, text, size, clip
        self.picture = picture        # a factpics (faces.Image) picture, when known
        self.name = "MARK#%d" % index


def layout(paper, page_index, image, font_lib, value_text=None, nav=None, rand=None,
           has_rulebook_tabs=False, touch_target_expand=0, image_size=None, image_for=None):
    """PaperInnerVisuals: the visuals of one page, in mark order.
    value_text(fact_id) gives a fact mark's text (BoothEnv.getLocalizedText);
    image_for(mark) a mark's picture (see picture_source), or image_size(mark)
    only its size; None leaves the mark out."""
    page = paper.pages[page_index]
    nav = nav or Nav(paper)
    value_text = value_text or (lambda fact_id: fact_id)
    positions = mark_positions(page, image, rand)
    placed = []
    right = bottom = 0.0                       # the last text's or picture's right and bottom edges
    for index, mark in enumerate(page.marks):
        px, py = positions[index]
        if mark.link == "#next":
            if nav.next_index(page_index) < 0:
                continue
        elif mark.link == "#prev":
            if nav.prev_index(page_index) < 0:
                continue
        elif mark.link is not None and nav.existing_page_id(mark.link) is None:
            continue
        fact = mark.fact_id()
        visual = None
        if mark.type == "TEXT":
            string = value_text(fact) if fact is not None else mark.text
            if not string:
                continue
            string = string.replace("\\n", "\n")
            font = font_lib.get(mark.font)
            t = Text(font, color=mark.text_color, align=mark.align)
            if mark.flow == "DOWN":
                x, y = px, mark.flow_pad + bottom
            elif mark.flow == "RIGHT":
                x, y = mark.flow_pad + right, py + 1 - font.ascent
            else:
                x, y = px, py + 1 - font.ascent
            if mark.link is None:
                if mark.back_color:
                    t.background, t.padding_x = mark.back_color, 1
            else:                              # a button: colours swapped, rounded box
                t.background, t.rounded = mark.text_color, True
                t.color = mark.back_color
                t.padding_x = t.padding_y = LINK_BUTTON_PADDING
            if mark.wrap:
                t.multi_line, t.fixed_width = True, mark.wrap
            if string[:1] == "@":              # "@text": letters and box colours swapped
                t.background, t.color = t.color, t.background
                string = string[1:]
            t.text = string
            if touch_target_expand > 0 and fact is not None and t.build()[1] < SMALL_FIELD:
                n = 1
                while SMALL_FIELD - t.build()[1] > font.space_width * n:
                    n += 1
                if mark.align == "CENTER":
                    string = " " * (n // 2) + string + " " * (n // 2)
                elif mark.align == "RIGHT":
                    string = " " * n + string
                else:
                    string = string + " " * n
                t.text = string
            _, w, h, _ = t.build()
            if mark.align == "CENTER":
                x = float(int((x - w * 0.5) // 1))
            elif mark.align == "RIGHT":
                x = float(int((x - w) // 1))
            right, bottom = x + w, y + h
            visual = Placed(index, "text", mark, x, y, text=t, size=(w, h))
        elif mark.type == "IMAGE":
            if mark.image.startswith("RulesTab") and not has_rulebook_tabs:
                continue
            picture = image_for(mark) if image_for else None
            if picture is not None:
                size = (picture.width, picture.height)
            else:
                size = image_size(mark) if image_size else None
            if size is None:
                continue                       # no picture: the mark is left out
            x, y = px, py
            if mark.flow == "DOWN":
                y = mark.flow_pad + bottom
            elif mark.flow == "RIGHT":
                x = mark.flow_pad + right
            w, h = size
            if mark.align == "CENTER":
                x = float(int((x - w * 0.5) // 1))
            elif mark.align == "RIGHT":
                x = float(int((x - w) // 1))
            right, bottom = x + w, y + h
            visual = Placed(index, "image", mark, x, y, size=size, picture=picture)
        elif mark.type == "EMBLEM":
            # drawn only when the seal's status is VALID or INCORRECT; the picture
            # and its place inside emblem_rect take three draws (not modelled here)
            visual = Placed(index, "emblem", mark, mark.emblem_rect[0], mark.emblem_rect[1],
                            size=mark.emblem_rect[2:])
        if visual is not None:
            if mark.clip_height:
                visual.clip = (0, 0, 100000, mark.clip_height)
            placed.append(visual)
    return placed


def literal_image_size(assets_dir):
    """image_size for the layout check: the size of a literal picture
    (picture_source with no fact values); fact-valued pictures are None."""
    source = picture_source(assets_dir, None)

    def size(mark):
        picture = source(mark)
        return (picture.width, picture.height) if picture is not None else None
    return size


def picture_source(assets_dir, paper_id, values=None, face_spec=None, prints=None, seed=1):
    """image_for for the preview (factpics.py, docs/fact-pictures.md).
    Literal pictures: Mark.getImage (BLANK:WxH, or the file scaled by `scale`).
    Fact pictures, as BoothEnv.getImage makes them, only where the preview
    knows the value: a picture file named by --values or by Facts.xml, the
    rulebook's seal sheets, the bulletin seal; a document or criminal photo
    with --face SPEC; fingerprints and the thumbprint with --prints CODE.
    The random draws come from a generator of their own (`seed`), not the
    booth's."""
    import re
    import factpics as FP
    import faces as F
    from rand import Rand
    data = os.path.join(assets_dir, "data")
    values = values or {}
    rand = Rand(seed)
    state = {}

    def facts():
        if "lib" not in state:
            import factlib
            state["lib"] = factlib.FactLib(open(os.path.join(data, "Facts.xml"), encoding="utf-8").read())
        return state["lib"]

    def doc_face():
        if "face" not in state:
            lib = F.FaceLib(os.path.join(data, "Faces.xml"), os.path.join(assets_dir, "FacePalette.png"))
            state["face"] = F.Face(os.path.join(assets_dir, "faces"), lib, F.FaceSpec(face_spec), for_doc=True)
        return state["face"]

    def source(mark):
        name = mark.image
        if not name.startswith("$"):
            if name.startswith("BLANK:"):
                m = re.match(r"BLANK:(\d+)x(\d+)", name)
                return F.Image(*((int(m.group(1)), int(m.group(2))) if m else (10, 10)))
            path = os.path.join(assets_dir, "papers", name)
            if not os.path.exists(path):
                return None
            picture = FP.load(path)
            return FP.transformed(picture, 0.0, mark.scale) if mark.scale != 1.0 else picture
        fact = name[1:]
        text, back = mark.text_color & 0xFFFFFF, mark.back_color & 0xFFFFFF
        if fact == "Face":
            if face_spec is None:
                return None
            mirrored = paper_id != "Passport"
            return FP.doc_image(doc_face(), rand, mark.scale, mirrored, mirrored, text, back)
        if paper_id == "Photo":
            return None                    # the search photo needs a traveler: not previewed
        if fact in ("Fingerprints", "Thumbprint"):
            if prints is None:
                return None
            code = FP.fingerprint_code(rand, prints)
            picture = FP.fingerprint_image(assets_dir, code, rand, text, fact == "Fingerprints")
        elif fact.startswith("Criminal"):
            if face_spec is None:
                return None
            picture = FP.doc_image(doc_face(), rand, 1.0, False, True, text, back)
        elif fact in ("SealsMoa", "SealsMol"):
            emblem = "MinistryOfAdmission" if fact == "SealsMoa" else "MinistryOfLabor"
            picture = FP.valid_seals_image(FP.Emblems(assets_dir), emblem, back)
        else:
            value = values.get(fact)
            if value is None:
                definition = facts().fact_defs.get("%s/%s" % (paper_id, fact))
                value = definition.val if definition is not None else ""
            if not value:
                return None
            if value == "BulletinEmblem":
                picture = FP.bulletin_emblem_image(FP.Emblems(assets_dir))
            else:
                path = os.path.join(assets_dir, "papers", value)
                if not os.path.exists(path):
                    return None
                picture = FP.load(path)
        return FP.scaled(picture, mark.scale)
    return source


def render(placed, image, assets_dir, scale=1):
    """A preview: the page picture (marker pixels already painted over), the
    texts drawn with text.py, literal pictures pasted, seals outlined."""
    from PIL import Image, ImageDraw
    import text as T
    out = image.copy()
    draw = ImageDraw.Draw(out)
    for v in placed:
        if v.kind == "text":
            piece = T.render(v.text, assets_dir, margin=0, backdrop=False)
            if v.clip:
                piece = piece.crop((0, 0, piece.width, min(piece.height, v.clip[3])))
            out.alpha_composite(piece, (int(v.x), int(v.y)))
        elif v.kind == "image":
            if v.picture is not None:
                p = v.picture
                piece = Image.new("RGBA", (p.width, p.height))
                piece.putdata([((c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24) for c in p.px])
                if v.clip:
                    piece = piece.crop((0, 0, piece.width, min(piece.height, v.clip[3])))
                out.alpha_composite(piece, (int(v.x), int(v.y)))
            else:
                x, y = int(v.x), int(v.y)
                draw.rectangle((x, y, x + v.size[0] - 1, y + v.size[1] - 1), outline=(255, 0, 255, 255))
        else:
            x, y, w, h = v.mark.emblem_rect
            draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 0, 255, 255))
    if scale != 1:
        out = out.resize((out.width * scale, out.height * scale), Image.NEAREST)
    return out


def main(argv):
    from PIL import Image
    if len(argv) < 3:
        print(__doc__)
        return 1
    assets, paper_id = argv[1], argv[2]
    args = argv[3:]
    page_index = int(args.pop(0)) if args and args[0].isdigit() else 0
    nation, values, mask, upgrade, png, scale = "", {}, "", False, None, 3
    face_spec, prints, seed = None, None, 1
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--nation":
            nation = args[i + 1]; i += 1
        elif a == "--values":
            values = dict(kv.split("=", 1) for kv in args[i + 1].split(";") if "=" in kv); i += 1
        elif a == "--mask":
            mask = args[i + 1]; i += 1
        elif a == "--upgrade":
            upgrade = True
        elif a == "--png":
            png = args[i + 1]; i += 1
        elif a == "--scale":
            scale = int(args[i + 1]); i += 1
        elif a == "--face":
            face_spec = args[i + 1]; i += 1
        elif a == "--prints":
            prints = args[i + 1]; i += 1
        elif a == "--seed":
            seed = int(args[i + 1]); i += 1
        else:
            raise SystemExit("unknown option " + a)
        i += 1
    papers = [p for p in load(assets) if p.id == paper_id and (not nation or p.nation == nation)]
    if not papers:
        raise SystemExit("no paper " + paper_id)
    paper = papers[0]
    page = paper.pages[page_index]
    image = Image.open(os.path.join(assets, "papers", page.image)).convert("RGBA")
    placed = layout(paper, page_index, image, fonts.FontLib(assets),
                    value_text=lambda f: values.get(f, f), nav=Nav(paper, mask),
                    has_rulebook_tabs=upgrade,
                    image_for=picture_source(assets, paper.id, values, face_spec, prints, seed))
    print("%s%s page %d (%s), picture %s %dx%d, %d marks, %d drawn" % (
        paper.id, " " + paper.nation if paper.nation else "", page_index, page.id, page.image,
        image.width, image.height, len(page.marks), len(placed)))
    for v in placed:
        m = v.mark
        what = repr(v.text.text) if v.kind == "text" else (m.image or m.emblem)
        print("  %-8s %-6s at %6.1f %6.1f  size %-10s %s%s" % (
            v.name, v.kind, v.x, v.y, "%dx%d" % tuple(v.size) if v.size else "?", what,
            "  clip %d" % m.clip_height if m.clip_height else ""))
    if png:
        render(placed, image, assets, scale).save(png)
        print("preview written to", png)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
