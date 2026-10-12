"""Reference implementation of how the game builds a face picture.

This follows data.FacePiece, data.Face, data.FaceLib and app.vis.Image.draw
as described in docs/faces.md. It needs the Pillow library to read PNGs.

Show one face (the spec is M|F-shoulders-head-eyes-noseMouth-palette-flip):

    python -I scripts/reference/faces.py show <faces dir> <Faces.xml> <FacePalette.png> M-3-7-12-1-2-0
           [--doc] [--png out.png]

Survey the pixel heights of every head and shoulders pairing:

    python -I scripts/reference/faces.py survey <faces dir> <Faces.xml> <FacePalette.png>

Draw every face as originally drawn, labelled with its piece number:

    python -I scripts/reference/faces.py overview <faces dir> <Faces.xml> <FacePalette.png> out.png

Images written by show and overview are built from the game's art: keep
them in a gitignored folder.
"""

import math
import struct
import sys
import xml.etree.ElementTree as ET

from PIL import Image as PilImage

PIECE_W, PIECE_H = 150, 120          # FaceSpec.kSizeInSheetX / Y
FACES_PER_SHEET = 4

FACE0, FACE1, FACE2 = 0xFF3D5043, 0xFF848A6B, 0xFFDED6AC
CLOTHES0, CLOTHES1 = 0xFF551B18, 0xFF892C27
DOC_DARK, DOC_LIGHT = 0xFF574848, 0xFFA29490

KEY_EYE0, KEY_EYE1 = 0xFF008000, 0xFF00FF00
KEY_NOSEMOUTH0, KEY_NOSEMOUTH1 = 0xFF000080, 0xFF0000FF
KEY_EYE_NOSEMOUTH = 0xFF00FFFF
KEY_HEAD_AND_SHOULDERS = 0xFFFF0000
KEY_SHOULDERS = 0xFF000000
KEY_MARK = 0xFFFFFFFF

MARK_NONE, MARK_EYE, MARK_NOSE, MARK_MOUTH, MARK_CHIN, MARK_SHOULDER = range(6)

HEAD_COLOR = 0x3D5043                 # Face.kHeadColor (alpha ignored)
HEIGHT_MIN_METERS = 1.0               # Face.kHeightMetersMin
METERS_PER_PIXEL = struct.unpack("<d", struct.pack("<Q", 0x3F829E4129E4129F))[0]
HEAD_SCALE_MAX = 1.05


class Image:
    """Pixels are 32-bit numbers 0xAARRGGBB, row by row."""

    def __init__(self, width, height, fill=0):
        self.width = width
        self.height = height
        self.px = [fill] * (width * height)

    @staticmethod
    def load(path):
        source = PilImage.open(path).convert("RGBA")
        image = Image(source.width, source.height)
        image.px = [(a << 24) | (r << 16) | (g << 8) | b for r, g, b, a in source.getdata()]
        return image

    def crop(self, x, y, width, height):
        out = Image(width, height)
        for row in range(height):
            start = (y + row) * self.width + x
            out.px[row * width:(row + 1) * width] = self.px[start:start + width]
        return out

    def save(self, path):
        out = PilImage.new("RGBA", (self.width, self.height))
        out.putdata([((p >> 16) & 255, (p >> 8) & 255, p & 255, p >> 24) for p in self.px])
        out.save(path)

    def draw(self, source, affine):
        """app.vis.Image.draw: copy `source` through `affine`, no blending."""
        a = affine
        w, h = float(source.width), float(source.height)
        x00 = a.m00 * 0.0 + a.m01 * 0.0 + a.m02
        y00 = a.m10 * 0.0 + a.m11 * 0.0 + a.m12
        xw0 = a.m01 * 0.0 + a.m00 * w + a.m02
        yw0 = a.m11 * 0.0 + a.m10 * w + a.m12
        ywh = a.m11 * h + a.m10 * w + a.m12
        x0h = a.m00 * 0.0 + a.m01 * h + a.m02
        xwh = a.m01 * h + a.m00 * w + a.m02
        y0h = a.m11 * h + a.m10 * 0.0 + a.m12
        left = max(0, int(min(x00, xw0, xwh, x0h)))
        right = min(self.width, int(max(x00, xw0, xwh, x0h) + 1.0))
        top = max(0, int(min(y00, yw0, ywh, y0h)))
        bottom = min(self.height, int(max(y00, yw0, ywh, y0h) + 1.0))
        if not (left < right and top < bottom):
            return self
        inverse = a.copy().invert()
        for y in range(top, bottom):
            for x in range(left, right):
                sx, sy = inverse.transform(float(x), float(y))
                sx = int(sx)                      # truncates toward zero, as the game does
                if 0 <= sx < source.width:
                    sy = int(sy)
                    if 0 <= sy < source.height:
                        pixel = source.px[sy * source.width + sx]
                        if (pixel >> 24) > 0x7F:
                            self.px[y * self.width + x] = pixel
        return self


class Affine:
    """A 2x3 matrix. Each operation is applied after the ones before it."""

    def __init__(self):
        self.m00, self.m01, self.m02 = 1.0, 0.0, 0.0
        self.m10, self.m11, self.m12 = 0.0, 1.0, 0.0

    def copy(self):
        out = Affine()
        out.m00, out.m01, out.m02 = self.m00, self.m01, self.m02
        out.m10, out.m11, out.m12 = self.m10, self.m11, self.m12
        return out

    def _then(self, a00, a01, a02, a10, a11, a12):
        m00, m01, m02, m10, m11, m12 = self.m00, self.m01, self.m02, self.m10, self.m11, self.m12
        self.m00 = a00 * m00 + a01 * m10
        self.m01 = a00 * m01 + a01 * m11
        self.m02 = a00 * m02 + a01 * m12 + a02
        self.m10 = a10 * m00 + a11 * m10
        self.m11 = a10 * m01 + a11 * m11
        self.m12 = a10 * m02 + a11 * m12 + a12
        return self

    def translate(self, tx, ty):
        return self._then(1.0, 0.0, tx, 0.0, 1.0, ty)

    def scale(self, sx, sy):
        return self._then(sx, 0.0, 0.0, 0.0, sy, 0.0)

    def invert(self):
        m00, m01, m02, m10, m11, m12 = self.m00, self.m01, self.m02, self.m10, self.m11, self.m12
        det = m00 * m11 - m01 * m10
        if det == 0.0:
            raise ValueError("Can't invert matrix (zero determinant)")
        d = 1.0 / det
        self.m00 = m11 * d
        self.m01 = -m01 * d
        self.m10 = -m10 * d
        self.m02 = (m12 * m01 - m02 * m11) * d
        self.m11 = m00 * d
        self.m12 = -(m12 * m00 - m02 * m10) * d
        return self

    def transform(self, x, y):
        return y * self.m01 + x * self.m00 + self.m02, x * self.m10 + y * self.m11 + self.m12


class FacePiece:
    """One face cut from a sheet, to be turned into one of the four pieces."""

    def __init__(self, faces_dir, male, face_index, for_doc):
        self.for_doc = for_doc
        if for_doc:
            self.face0, self.face1, self.face2 = DOC_DARK, DOC_LIGHT, DOC_LIGHT
            self.clothes0, self.clothes1 = DOC_DARK, DOC_LIGHT
            self.clear_color = DOC_LIGHT
        else:
            self.face0, self.face1, self.face2 = FACE0, FACE1, FACE2
            self.clothes0, self.clothes1 = CLOTHES0, CLOTHES1
            self.clear_color = 0
        self.width, self.height = PIECE_W, PIECE_H
        position = face_index % FACES_PER_SHEET
        x, y = (position % 2) * PIECE_W, (position // 2) * PIECE_H
        name = "Sheet" + ("M" if male else "F") + str(face_index // FACES_PER_SHEET)
        colors = Image.load("%s/%s%s.png" % (faces_dir, name, "d" if for_doc else ""))
        keys = Image.load("%s/%sp.png" % (faces_dir, name))
        self.image = colors.crop(x, y, PIECE_W, PIECE_H)
        self.keys = keys.crop(x, y, PIECE_W, PIECE_H)
        self.eye0 = self.eye1 = self.nose = self.mouth = self.chin = None
        self.shoulder0 = self.shoulder1 = None

    def add_mark(self, i):
        """White dots in the key image, in reading order: two eyes, nose,
        mouth, chin, two shoulders."""
        point = [float(i % self.width), float(i // self.width)]
        if self.eye0 is None:
            self.eye0 = point
            return MARK_EYE
        if self.eye1 is None:
            self.eye1 = point
            return MARK_EYE
        if self.nose is None:
            self.nose = point
            return MARK_NOSE
        if self.mouth is None:
            self.mouth = point
            return MARK_MOUTH
        if self.chin is None:
            self.chin = point
            return MARK_CHIN
        if self.shoulder0 is None:
            self.shoulder0 = point
            return MARK_SHOULDER
        if self.shoulder1 is None:
            self.shoulder1 = point
            return MARK_SHOULDER
        return MARK_NONE

    def make_head(self):
        px = self.image.px
        for i, key in enumerate(self.keys.px):
            if key in (KEY_EYE0, KEY_NOSEMOUTH0):
                px[i] = self.face0
            elif key in (KEY_EYE1, KEY_NOSEMOUTH1, KEY_EYE_NOSEMOUTH):
                px[i] = self.face1
            elif key == KEY_MARK:
                mark = self.add_mark(i)
                if mark == MARK_SHOULDER:
                    px[i] = 0
                elif mark in (MARK_EYE, MARK_NOSE, MARK_MOUTH):
                    px[i] = self.face1
            elif key == KEY_SHOULDERS:
                px[i] = 0
        return self

    def _make_feature(self, keep_keys, keep_marks):
        px = self.image.px
        for i, key in enumerate(self.keys.px):
            if key == KEY_MARK:
                mark = self.add_mark(i)
                if not (mark in keep_marks and px[i] != self.face1):
                    px[i] = 0
            elif key in keep_keys:
                if px[i] == self.face1:
                    px[i] = 0
            else:
                px[i] = 0
        return self

    def make_eyes(self):
        return self._make_feature((KEY_EYE0, KEY_EYE1, KEY_EYE_NOSEMOUTH), (MARK_EYE,))

    def make_nose_mouth(self):
        return self._make_feature((KEY_NOSEMOUTH0, KEY_NOSEMOUTH1, KEY_EYE_NOSEMOUTH),
                                  (MARK_NOSE, MARK_MOUTH))

    def make_shoulders(self):
        px = self.image.px
        fill = self.face1 if self.for_doc else self.clothes0
        for i, key in enumerate(self.keys.px):
            if key == KEY_MARK:
                self.add_mark(i)
                px[i] = 0              # the game writes the fill colour, then clears it
            elif key in (KEY_EYE0, KEY_EYE1):
                px[i] = 0
            elif key in (KEY_HEAD_AND_SHOULDERS, KEY_NOSEMOUTH0, KEY_NOSEMOUTH1, KEY_EYE_NOSEMOUTH):
                px[i] = fill
            elif key != KEY_SHOULDERS:
                px[i] = 0
        return self

    def flip_on_x(self, center_x):
        center = float(int(math.floor(center_x)))
        width, px = self.image.width, self.image.px
        if center < width * 0.5:
            start, end = int(math.floor(center)), width
        else:
            start, end = 0, int(math.floor(center)) + 1
        for y in range(self.image.height):
            row = y * width
            for x in range(start, end):
                mirror = int(math.floor(-(x - center) + center))
                if 0 <= mirror < width:
                    px[row + x], px[row + mirror] = px[row + mirror], px[row + x]
                else:
                    px[row + x] = 0
        for point in (self.nose, self.mouth, self.eye0, self.eye1, self.chin,
                      self.shoulder0, self.shoulder1):
            point[0] = -(point[0] - center) + center
        self.eye0, self.eye1 = self.eye1, self.eye0


class FaceSpec:
    def __init__(self, text):
        parts = text.split("-")
        if len(parts) != 7:
            raise ValueError("a full face spec has 7 parts: M-shoulders-head-eyes-noseMouth-palette-flip")
        self.male = parts[0] == "M"
        self.shoulders, self.head, self.eyes, self.nose_mouth, self.palette = map(int, parts[1:6])
        self.flip = bool(int(parts[6]) & 1)


class FaceLib:
    def __init__(self, faces_xml, palette_png):
        self.meta = {}
        for sheet in ET.parse(faces_xml).getroot().findall("sheet"):
            for position, face in enumerate(sheet.findall("face")):
                self.meta[sheet.get("id") + ":" + str(position)] = face.attrib
        self.palette = Image.load(palette_png)

    def face_meta(self, male, face_index):
        key = ("M" if male else "F") + str(face_index // FACES_PER_SHEET) + ":" + \
              str(face_index % FACES_PER_SHEET)
        return self.meta[key]

    def hair_height(self, spec):
        return int(self.face_meta(spec.male, spec.head).get("hairheight", "0") or 0)

    def replace_colors(self, image, palette_index):
        """Swatches are 10 pixels apart: row 0 holds the colours to find,
        row palette_index * 10 the colours to put in their place."""
        pal = self.palette
        find = [pal.px[k * 10] for k in range(5)]
        row = palette_index * 10 * pal.width
        put = [pal.px[row + k * 10] for k in range(5)]
        for i, pixel in enumerate(image.px):
            for k in range(5):
                if pixel == find[k]:
                    image.px[i] = put[k]
                    break


class Face:
    def __init__(self, faces_dir, lib, spec, for_doc=False):
        self.spec = spec
        shoulders = FacePiece(faces_dir, spec.male, spec.shoulders, for_doc).make_shoulders()
        head = FacePiece(faces_dir, spec.male, spec.head, for_doc).make_head()
        eyes = FacePiece(faces_dir, spec.male, spec.eyes, for_doc).make_eyes()
        nose_mouth = FacePiece(faces_dir, spec.male, spec.nose_mouth, for_doc).make_nose_mouth()
        if spec.flip:
            shoulders.flip_on_x(shoulders.chin[0])
            head.flip_on_x(head.chin[0])
            eyes.flip_on_x((eyes.eye1[0] + eyes.eye0[0]) * 0.5)
            nose_mouth.flip_on_x((nose_mouth.eye1[0] + nose_mouth.eye0[0]) * 0.5)

        # Eyes onto the head: stretched sideways so the eye spacing matches.
        eye_scale = abs(head.eye0[0] - head.eye1[0]) / abs(eyes.eye0[0] - eyes.eye1[0])
        a = Affine().translate(-eyes.eye0[0], -eyes.eye0[1]).scale(eye_scale, 1.0)
        a.translate(head.eye0[0], head.eye0[1])
        head.image.draw(eyes.image, a)

        # Nose and mouth onto the head: stretched up and down, half way
        # towards the head's own nose-to-mouth distance.
        ratio = abs(head.nose[1] - head.mouth[1]) / abs(nose_mouth.nose[1] - nose_mouth.mouth[1])
        nm_scale = (1.0 - ratio) * 0.5 + ratio
        nm_mid = _mid(nose_mouth.nose, nose_mouth.mouth)
        head_mid = _mid(head.nose, head.mouth)
        b = Affine().translate(-nm_mid[0], -nm_mid[1]).scale(1.0, nm_scale)
        b.translate(head_mid[0], head_mid[1])
        head.image.draw(nose_mouth.image, b)

        self.image = Image(head.image.width, head.image.height, head.clear_color)

        # Shoulders and head are each stretched sideways half way towards
        # the other's shoulder width.
        head_width = abs(head.shoulder0[0] - head.shoulder1[0])
        shoulders_width = abs(shoulders.shoulder0[0] - shoulders.shoulder1[0])
        wide = head_width / shoulders_width
        narrow = shoulders_width / head_width
        self.head_scale = min(HEAD_SCALE_MAX, (1.0 - narrow) * 0.5 + narrow)
        self.shoulders_scale = (1.0 - wide) * 0.5 + wide
        s_mid = _mid(shoulders.shoulder0, shoulders.shoulder1)
        s = Affine().translate(-s_mid[0], -s_mid[1]).scale(self.shoulders_scale, 1.0)
        s.translate(s_mid[0], s_mid[1])
        self.image.draw(shoulders.image, s)

        # The head's chin goes where the shoulders' chin mark ended up.
        h = Affine().translate(-head.chin[0], -head.chin[1]).scale(self.head_scale, 1.0)
        h.translate(shoulders.chin[0], shoulders.chin[1])
        sx, sy = shoulders.chin
        hx, hy = head.chin
        dx = (sx * s.m00 + sy * s.m01 + s.m02) - (h.m01 * hy + h.m00 * hx + h.m02)
        dy = (sx * s.m10 + sy * s.m11 + s.m12) - (h.m11 * hy + h.m10 * hx + h.m12)
        h.translate(dx, dy)
        self.image.draw(head.image, h)
        self.head_only_image = Image(self.image.width, self.image.height, 0).draw(head.image, h)
        self.head_only_chin = (sy * s.m01 + sx * s.m00 + s.m02, sy * s.m11 + sx * s.m10 + s.m12)
        self.pieces = (shoulders, head, eyes, nose_mouth)

        self.height_in_pixels = 0
        self.top_row = None
        if for_doc:
            return
        hair = lib.hair_height(spec)
        width = self.image.width
        for y in range(self.image.height):
            row = self.image.px[y * width:(y + 1) * width]
            if any((p & 0xFFFFFF) == HEAD_COLOR for p in row):
                self.height_in_pixels = self.image.height - hair - y
                if self.top_row is None:
                    self.top_row = y
            if self.height_in_pixels != 0:
                break
        if spec.palette != 0:
            lib.replace_colors(self.image, spec.palette)

    @property
    def height_in_meters(self):
        return self.height_in_pixels * METERS_PER_PIXEL + HEIGHT_MIN_METERS


def _mid(p, q):
    return (q[0] - p[0]) * 0.5 + p[0], (q[1] - p[1]) * 0.5 + p[1]


def show(faces_dir, lib, text, for_doc, png):
    face = Face(faces_dir, lib, FaceSpec(text), for_doc)
    for name, piece in zip(("shoulders", "head", "eyes", "nose/mouth"), face.pieces):
        print("%-10s eyes %s %s  nose %s  mouth %s  chin %s  shoulders %s %s" % (
            name, piece.eye0, piece.eye1, piece.nose, piece.mouth, piece.chin,
            piece.shoulder0, piece.shoulder1))
    print("head scale %r, shoulders scale %r" % (face.head_scale, face.shoulders_scale))
    if not for_doc:
        print("top row with the head colour: %s, hair height: %d" % (face.top_row, lib.hair_height(face.spec)))
        print("height in pixels: %d, height in metres: %r" % (face.height_in_pixels, face.height_in_meters))
    if png:
        face.image.save(png)
        print("wrote", png)


def has_artwork(faces_dir, male, face_index):
    """False for a sheet position with no marker dots (nothing drawn there)."""
    return FacePiece(faces_dir, male, face_index, False).make_head().shoulder1 is not None


def survey(faces_dir, lib):
    for male in (True, False):
        gender = "M" if male else "F"
        sheets = sum(1 for key in lib.meta if key.startswith(gender)) // FACES_PER_SHEET
        pieces = [p for p in range(sheets * FACES_PER_SHEET) if has_artwork(faces_dir, male, p)]
        print("%s: pieces with artwork: %d (0 to %d)" % (gender, len(pieces), pieces[-1]))
        heights = {}
        for head in pieces:
            for shoulders in pieces:
                spec = FaceSpec("%s-%d-%d-%d-%d-0-0" % (gender, shoulders, head, head, head))
                heights[(head, shoulders)] = Face(faces_dir, lib, spec).height_in_pixels
        for label, limit in (("random faces (pieces 0 to 19)", 20), ("all pieces", len(pieces))):
            values = sorted(v for (h, s), v in heights.items() if h < limit and s < limit)
            print("  %s: %d pairings, pixel height %d to %d (%.3f m to %.3f m), zero heights: %d" % (
                label, len(values), values[0], values[-1],
                values[0] * METERS_PER_PIXEL + 1.0, values[-1] * METERS_PER_PIXEL + 1.0,
                sum(1 for v in values if v == 0)))
        for head in pieces:
            row = [heights[(head, s)] for s in pieces]
            print("  head %2d: %d to %d" % (head, min(row), max(row)))


def overview(faces_dir, lib, png, columns=9, zoom=2, label_height=22):
    """One picture of every face as drawn (all four pieces from the same
    face, base colours), labelled with its gender and piece number."""
    from PIL import ImageDraw

    cells = []
    for male in (True, False):
        gender = "M" if male else "F"
        sheets = sum(1 for key in lib.meta if key.startswith(gender)) // FACES_PER_SHEET
        for piece in range(sheets * FACES_PER_SHEET):
            if has_artwork(faces_dir, male, piece):
                face = Face(faces_dir, lib, FaceSpec("%s-%d-%d-%d-%d-0-0" % ((gender,) + (piece,) * 4)))
                cells.append(("%s %d   %.2f m" % (gender, piece, face.height_in_meters), face.image))
    cell_w, cell_h = PIECE_W * zoom, PIECE_H * zoom + label_height
    rows = (len(cells) + columns - 1) // columns
    sheet = PilImage.new("RGBA", (cell_w * columns, cell_h * rows), (96, 96, 96, 255))
    pen = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(cells):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        picture = PilImage.new("RGBA", (image.width, image.height))
        picture.putdata([((p >> 16) & 255, (p >> 8) & 255, p & 255, p >> 24) for p in image.px])
        sheet.alpha_composite(picture.resize((PIECE_W * zoom, PIECE_H * zoom), PilImage.NEAREST),
                              (x, y + label_height))
        pen.text((x + 6, y + 5), label, fill=(255, 255, 255, 255))
    sheet.save(png)
    print("wrote %s with %d faces" % (png, len(cells)))


def main():
    mode, faces_dir, faces_xml, palette_png = sys.argv[1:5]
    lib = FaceLib(faces_xml, palette_png)
    if mode == "show":
        rest = sys.argv[6:]
        png = rest[rest.index("--png") + 1] if "--png" in rest else None
        show(faces_dir, lib, sys.argv[5], "--doc" in rest, png)
    elif mode == "survey":
        survey(faces_dir, lib)
    elif mode == "overview":
        overview(faces_dir, lib, sys.argv[5])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
