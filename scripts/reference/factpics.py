"""Reference for the pictures a document shows for a fact: play.day.BoothEnv.getImage
and what it calls (docs/fact-pictures.md).

A picture mark whose name starts with `$` (Papers.xml) shows a fact. getImage
turns the fact into a picture: the document photo (Face.getDocImage), the
search photo's head, body and contraband, fingerprints and the thumbprint
(FingerprintCode.getImage), the bulletin's criminal photos, the rulebook's
sheet of valid seals (EmblemLib.getValidImage), the bulletin's seal, or a
picture file named by the fact's value. Then, for most of them, the picture
is scaled by the mark's `scale` (Image.transformed).

It also holds the picture operations those need, as read in app.vis.Image:
paste (three paste modes, plain or tinted), copy, fill, replace, tint and
transformed. Image.draw and the matrix are in faces.py.

    python -I scripts/reference/factpics.py <assets dir> <out dir> [--seed N] [--zoom N]

writes example pictures (a passport photo and the same face on an id card,
fingerprints, a thumbprint, a criminal photo, the search photo's head and
body, a contraband piece, the two seal sheets, the bulletin seal, a rulebook
passport cover at half size) as PNG files, each blown up --zoom times (4).
They are made from the game's art: keep <out dir> in a gitignored folder.

Not modelled: where the fact values come from (fact-values.md and the
others), what a FaceSpec or fingerprint value holds when it is invalid (they
are passed in), BodyLib.getContraband's pick (the chosen entry is passed in),
and how a picture is drawn on screen.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces as F  # noqa: E402
from faces import Affine, Image  # noqa: E402
from person import face_spec_from_string, spec_text  # noqa: E402

# Face's static values
DOC_W, DOC_H = 80, 96                 # kDocImageDefaultWidth / Height
PAL_PHOTO_FRONT, PAL_PHOTO_BACK = 7, 8  # kPalPhotoFront / Back (rows of FacePalette.png)
DOC_DARK, DOC_LIGHT = F.DOC_DARK, F.DOC_LIGHT
MISSING_FACE = 0xFFFF0000             # a document photo with no fact: a red box
# FingerprintCode's static values
PRINT_SIZE = 32                       # size of one print on FingerSworls.png
PRINT_IMAGE_H = 32                    # height of the made picture
PRINT_DEFAULT_CELL = 32               # the cell width when none is given
SCALE_EPSILON = 0.0001                # getImage scales when |scale - 1| is larger
VALID_SEAL_GAP = 12                   # getValidImage: the gap between the two columns
PHOTO_HEAD = 50                       # getPhotoHeadImage: the picture is 50 x 50
PHOTO_CHIN = (25.0, 42.0)             # ... with the chin here
BODY_H = 160                          # Traveler.getBodyImage: height of the cut

REPLACE, OVERLAY, BLEND = "REPLACE", "OVERLAY", "BLEND"   # app.vis.PasteMode


def math_round(x):
    """Haxe Math.round as compiled: the whole part, plus one if the rest is
    0.5 or more, minus one if it is below -0.5 (checked in the instructions)."""
    i = int(x)
    d = x - i
    if d >= 1.0 or -1.0 >= d:
        return i
    if d >= 0.5:
        return i + 1
    if -0.5 > d:
        return i - 1
    return i


# ------------------------------------------------------------- picture work

def fill(image, color, rect=None):
    """Image.fill: write the colour as it is over the (clipped) rectangle."""
    if rect is None:
        clip = _clip(image.width, image.height, 0, 0, image.width, image.height,
                     0, 0, image.width, image.height)
    else:
        x, y, w, h = (int(v) for v in rect)
        clip = _clip(image.width, image.height, x, y, w, h, 0, 0, w, h)
    if clip:
        dx, dy, sx0, sy0, sx1, sy1 = clip
        for row in range(sy1 - sy0):
            start = (dy + row) * image.width + dx
            image.px[start:start + (sx1 - sx0)] = [color] * (sx1 - sx0)
    return image


def replace(image, find, put):
    """Image.replace: every pixel exactly equal to `find` becomes `put`."""
    image.px = [put if p == find else p for p in image.px]
    return image


def tint(image, color):
    """Image.tint: each channel, alpha too, times the colour's / 255 (whole numbers)."""
    ca, cr, cg, cb = color >> 24, (color >> 16) & 255, (color >> 8) & 255, color & 255
    out = []
    for p in image.px:
        a = ((p >> 24) * ca) // 255
        r = (((p >> 16) & 255) * cr) // 255
        g = (((p >> 8) & 255) * cg) // 255
        b = ((p & 255) * cb) // 255
        out.append((a << 24) | (r << 16) | (g << 8) | b)
    image.px = out
    return image


def _clip(dst_w, dst_h, dx, dy, src_w, src_h, sx, sy, sw, sh):
    """app.vis.Clipper.clip. Returns (dx, dy, sx0, sy0, sx1, sy1) or None."""
    sx0, sy0 = max(sx, 0), max(sy, 0)
    sx1 = min(sw + sx, src_w)
    sy1 = min(sh + sy, src_h)
    if dx < 0:
        sx0 -= dx
        dx = 0
    if dy < 0:
        sy0 -= dy
        dy = 0
    if (sx1 - sx0) + dx > dst_w:
        sx1 = sx1 - ((sx1 - sx0) + dx) + dst_w
    if (sy1 - sy0) + dy > dst_h:
        sy1 = sy1 - ((sy1 - sy0) + dy) + dst_h
    if sx0 < sx1 and sy0 < sy1:
        return dx, dy, sx0, sy0, sx1, sy1
    return None


def paste(dst, src, x=0.0, y=0.0, rect=None, mode=REPLACE, tint_color=None):
    """Image.paste. The position is cut toward zero; `rect` (x, y, w, h) is the
    part of `src` to paste. tint_color None is ColorMode DEFAULT, otherwise TINT."""
    dx, dy = int(x), int(y)
    if rect is None:
        clip = _clip(dst.width, dst.height, dx, dy, src.width, src.height,
                     0, 0, src.width, src.height)
    else:
        rx, ry, rw, rh = (int(v) for v in rect)
        clip = _clip(dst.width, dst.height, dx, dy, src.width, src.height, rx, ry, rw, rh)
    if not clip:
        return dst
    dx, dy, sx0, sy0, sx1, sy1 = clip
    if tint_color is not None:
        ta, tr = tint_color >> 24, (tint_color >> 16) & 255
        tg, tb = (tint_color >> 8) & 255, tint_color & 255
    for row in range(sy1 - sy0):
        s_row = (sy0 + row) * src.width + sx0
        d_row = (dy + row) * dst.width + dx
        for col in range(sx1 - sx0):
            p = src.px[s_row + col]
            a = p >> 24
            if tint_color is not None:
                a = (a * ta) // 255
                p = ((a << 24) | (((((p >> 16) & 255) * tr) // 255) << 16)
                     | (((((p >> 8) & 255) * tg) // 255) << 8) | (((p & 255) * tb) // 255))
            i = d_row + col
            if mode == REPLACE:
                dst.px[i] = p
            elif mode == OVERLAY:
                if a > 0x7F:
                    dst.px[i] = p
            else:
                q = dst.px[i]
                keep = 255 - a
                r = (((q >> 16) & 255) * keep + ((p >> 16) & 255) * a) // 255
                g = (((q >> 8) & 255) * keep + ((p >> 8) & 255) * a) // 255
                b = ((q & 255) * keep + (p & 255) * a) // 255
                dst.px[i] = (max(q >> 24, a) << 24) | (r << 16) | (g << 8) | b
    return dst


def copy(image, rect=None):
    """Image.copy: a whole copy, or a new picture of the rectangle's size
    (whole parts) with that part pasted in (REPLACE)."""
    if rect is None:
        out = Image(image.width, image.height)
        out.px = list(image.px)
        return out
    out = Image(int(rect[2]), int(rect[3]))
    return paste(out, image, 0, 0, rect)


def transformed(image, rotation=0.0, scale=1.0):
    """Image.transformed: turned by `rotation` (radians) about its middle and
    scaled, into a new picture just big enough (sizes rounded up)."""
    a = Affine()
    a.translate(-image.width * 0.5, -image.height * 0.5)
    c, s = math.cos(rotation), math.sin(rotation)
    a._then(c, -s, 0.0, s, c, 0.0)
    a.scale(scale, scale)
    w, h = float(image.width), float(image.height)
    xs = [a.m02, a.m00 * w + a.m02, a.m01 * h + a.m02, a.m01 * h + a.m00 * w + a.m02]
    ys = [a.m12, a.m10 * w + a.m12, a.m11 * h + a.m12, a.m11 * h + a.m10 * w + a.m12]
    a.translate(-min(xs), -min(ys))
    out = Image(int(math.ceil(max(xs) - min(xs))), int(math.ceil(max(ys) - min(ys))))
    return out.draw(image, a)


def load(path):
    return Image.load(path)


# ------------------------------------------------------------- the pictures

def doc_image(face, rand, scale, flip_x, replace_colors, text_color=0, back_color=0):
    """Face.getDocImage: the document photo. One draw (how far down the face sits)."""
    w, h = math_round(DOC_W * scale), math_round(DOC_H * scale)
    out = Image(w, h, 0xFF000000)
    a = Affine().translate(-face.image.width * 0.5, -float(face.image.height))
    a.scale(-scale if flip_x else scale, scale)
    down = math_round(rand.random() * 3.0 + 3.0)
    a.translate(out.width * 0.5, float(int(math.floor(float(out.height))) + down))
    out.draw(face.image, a)
    if replace_colors:
        replace(out, DOC_DARK, text_color | 0xFF000000)
        replace(out, DOC_LIGHT, back_color | 0xFF000000)
    return out


def missing_doc_image(scale):
    """getImage with no Face fact: a red box (sizes cut down, not rounded)."""
    return Image(int(math.floor(DOC_W * scale)), int(math.floor(DOC_H * scale)), MISSING_FACE)


def photo_head_image(face, lib, front):
    """Face.getPhotoHeadImage: the head alone at half size (mirrored from the
    back), chin at (25, 42) of a 50 x 50 picture, in the photo colours."""
    head = face.head_only_image
    out = Image(PHOTO_HEAD, PHOTO_HEAD)
    a = Affine().translate(-head.width * 0.5, -head.height * 0.5)
    a.scale(0.5 if front else -0.5, 0.5)
    a.translate(PHOTO_HEAD * 0.5, PHOTO_HEAD * 0.5)
    cx, cy = a.transform(*face.head_only_chin)
    a.translate(PHOTO_CHIN[0] - cx, PHOTO_CHIN[1] - cy)
    out.draw(head, a)
    lib.replace_colors(out, PAL_PHOTO_FRONT if front else PAL_PHOTO_BACK)
    return out


def body_id(male, bmi):
    """BodyLib.getBodyId (emblems-and-bodies.md)."""
    return ("M" if male else "F") + ("0" if bmi < 21 else "2" if bmi > 24 else "1")


def body_image(assets, body, nude, front):
    """Traveler.getBodyImage: the left (front) or right (back) half of the
    200-wide body picture, 160 high; Body<id>.png when nude, else Body<id>c.png."""
    picture = load(os.path.join(assets, "faces", "Body%s%s.png" % (body, "" if nude else "c")))
    half = picture.width * 0.5
    return copy(picture, (0.0 if front else half, 0, half, BODY_H))


class Bodies:
    """Bodies.xml, as far as cutting a contraband piece needs it."""

    def __init__(self, assets):
        root = ET.parse(os.path.join(assets, "data", "Bodies.xml")).getroot()
        self.assets = assets
        self.locs = {l.get("id"): [float(v) for v in l.get("rect").split(" ")]
                     for l in root.findall("loc")}
        self.contras = root.findall("contra")

    def piece(self, entry, body):
        """BodyLib.getContraband after its pick: the cut piece and where it
        belongs on the body (Contraband.image, .pastePos)."""
        x, y, w, h = self.locs[entry.get("loc")]
        off = next((o.get("val") for o in entry.findall("offset") if o.get("body") == body), None)
        ox, oy = (float(v) for v in off.split(" ")) if off else (0.0, 0.0)
        picture = load(os.path.join(self.assets, "faces", entry.get("file")))
        cut = (x - ox, y - oy, w, h)
        return copy(picture, cut), (ox + cut[0], cut[1] + oy)


def fingerprint_image(assets, fingers, rand, color, all_fingers=True, cell=0):
    """FingerprintCode.getImage. `fingers` holds five numbers, -1 for none.
    One draw per finger shown, made before the finger is looked at."""
    sheet = load(os.path.join(assets, "FingerSworls.png"))
    blank = load(os.path.join(assets, "FingerSworlBlank.png"))
    count = len(fingers) if all_fingers else 1
    cell = cell or PRINT_DEFAULT_CELL
    out = Image(count * cell, PRINT_IMAGE_H)
    rgb = color & 0xFFFFFF
    for i in range(count):
        column = (i + 1) // 2 * PRINT_SIZE            # thumb, then two fingers per column
        print_y = PRINT_SIZE * fingers[i]
        mask_y = int(rand.random() * 10.0) * PRINT_SIZE
        left = i * cell
        if fingers[i] < 0:
            paste(out, blank, left, 0, (0, 0, blank.width, blank.height))
            continue
        width = min(out.width - left, PRINT_SIZE)
        for row in range(PRINT_SIZE):
            for col in range(width):
                ink = sheet.px[(print_y + row) * sheet.width + column + col] & 255      # blue
                mask = sheet.px[(mask_y + row) * sheet.width + column + col] >> 24     # alpha
                out.px[row * out.width + left + col] = (((mask - ink) & 255) << 24) | rgb
    return out


def fingerprint_code(rand, text):
    """FingerprintCode.fromString: a new random code (five draws plus
    redraws, traveler-build.md), then finger i from character i: '-' is -1,
    a digit is that digit, anything else 0."""
    from person import make_fingerprints
    fingers = make_fingerprints(rand)
    for i in range(5):
        ch = text[i] if i < len(text) else ""
        fingers[i] = -1 if ch == "-" else int(ch) if ch.isdigit() else 0
    return fingers


class Emblems:
    """Emblems.xml, as far as the seal sheets need it."""

    def __init__(self, assets):
        root = ET.parse(os.path.join(assets, "data", "Emblems.xml")).getroot()
        self.assets = assets
        self.sets = []
        for e in root.findall("emblem"):
            size = [float(v) for v in e.get("size").split(" ")]
            files = [(n.get("id"), n.get("file")) for n in e.findall("nation")] or [("", e.get("file"))]
            for nation, name in files:
                self.sets.append(dict(id=e.get("id"), nation=nation, file=name, size=size,
                                      count=int(e.get("count")), valid=int(e.get("valid"))))

    def grid(self, s):
        return load(os.path.join(self.assets, s["file"]))

    def translucent_grid(self, s):
        """The EmblemLib constructor: a copy of the sheet tinted 0x80000000
        (black, alpha halved)."""
        return tint(copy(self.grid(s)), 0x80000000)

    def first(self, emblem_id):
        return next(s for s in self.sets if s["id"] == emblem_id)

    def cell(self, s, n):
        """getEmblemImage with a given cell: no draw."""
        cw, ch = s["size"]
        grid = self.grid(s)
        columns = int(math.floor(grid.width / cw))
        return copy(grid, (n % columns * cw, n // columns * ch, cw, ch))


def valid_seals_image(emblems, emblem_id, back_color):
    """EmblemLib.getValidImage: the valid seals of a set as dark shapes on
    the back colour, two to a row."""
    s = emblems.first(emblem_id)
    cw, ch = s["size"]
    valid = s["valid"]
    rows = (valid + 1) // 2
    source = emblems.translucent_grid(s)
    columns = int(source.width / cw)
    out = fill(Image(int(cw + cw + VALID_SEAL_GAP), int((rows - 1) + rows * ch)), back_color | 0xFF000000)
    for i in range(valid):
        src = (int(math.floor(i % columns)) * cw, int(math.floor(i / columns)) * ch, cw, ch)
        side = int(math.floor(i % 2))
        x = side * cw + side * VALID_SEAL_GAP
        y = int(math.floor(i * 0.5)) * ch + int(math.floor(i / rows))
        paste(out, source, x, y, src, BLEND)
    return out


def bulletin_emblem_image(emblems):
    """The value BulletinEmblem: cell 0 of the Ministry of Admission's sheet
    (no draw), alpha halved."""
    return tint(copy(emblems.cell(emblems.first("MinistryOfAdmission"), 0)), 0x80FFFFFF)


def scaled(image, scale):
    """The end of getImage, for every branch except the photos."""
    if abs(scale - 1.0) > SCALE_EPSILON:
        return transformed(image, 0.0, scale)
    return image


# ------------------------------------------------------------- demonstration

def demo(assets, out_dir, seed=1, zoom=4):
    from rand import Rand
    rand = Rand(seed)
    lib = F.FaceLib(os.path.join(assets, "data", "Faces.xml"), os.path.join(assets, "FacePalette.png"))
    faces_dir = os.path.join(assets, "faces")
    spec = spec_text(face_spec_from_string(rand, "M-3-7-12-1-2-0"))
    doc_face = F.Face(faces_dir, lib, F.FaceSpec(spec), for_doc=True)
    face = F.Face(faces_dir, lib, F.FaceSpec(spec))
    emblems = Emblems(assets)
    bodies = Bodies(assets)
    entry = next(c for c in bodies.contras if c.get("file") == "Contra-Gun0.png")
    pictures = [
        ("passport_photo", doc_image(doc_face, rand, 0.5, False, False)),
        ("idcard_photo", doc_image(doc_face, rand, 0.4, True, True, 0x3D394D, 0xB29CCC)),
        ("missing_photo", missing_doc_image(0.5)),
        ("fingerprints", fingerprint_image(assets, fingerprint_code(rand, "31415"), rand, 0x202020)),
        ("fingerprints_one_missing", fingerprint_image(assets, fingerprint_code(rand, "3-415"), rand, 0x202020)),
        ("thumbprint", fingerprint_image(assets, fingerprint_code(rand, "7"), rand, 0x4E454F, False)),
        ("criminal", scaled(doc_image(doc_face, rand, 1.0, False, True, 0x565656, 0xA3A3A3), 0.4)),
        ("photo_head_front", photo_head_image(face, lib, True)),
        ("photo_head_back", photo_head_image(face, lib, False)),
        ("photo_body_front", body_image(assets, "M1", False, True)),
        ("photo_body_back", body_image(assets, "M1", False, False)),
        ("contraband_gun0_M1", bodies.piece(entry, "M1")[0]),
        ("seals_moa", valid_seals_image(emblems, "MinistryOfAdmission", 0xE4E6BD)),
        ("seals_mol", valid_seals_image(emblems, "MinistryOfLabor", 0xE4E6BD)),
        ("bulletin_emblem", bulletin_emblem_image(emblems)),
        ("rules_passport_cover", scaled(load(os.path.join(assets, "papers", "PassportOuterArstotzka.png")), 0.5)),
    ]
    os.makedirs(out_dir, exist_ok=True)
    for name, image in pictures:
        big = Image(image.width * zoom, image.height * zoom)
        for y in range(big.height):
            row = (y // zoom) * image.width
            big.px[y * big.width:(y + 1) * big.width] = [image.px[row + x // zoom] for x in range(big.width)]
        path = os.path.join(out_dir, name + ".png")
        big.save(path)
        print("%-26s %3d x %-3d  %s" % (name, image.width, image.height, path))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    seed, zoom = 1, 4
    if "--seed" in argv:
        seed = int(argv[argv.index("--seed") + 1])
    if "--zoom" in argv:
        zoom = int(argv[argv.index("--zoom") + 1])
    demo(argv[1], argv[2], seed, zoom)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
