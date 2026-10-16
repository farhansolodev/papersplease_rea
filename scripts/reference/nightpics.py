"""Reference for the family pictures of the night screen, desktop layout:
play.night.FamilyVisuals and FamilyVisualsDim (docs/night-pictures.md).

Given the family and the night's facts, lists every picture the game places
(which file, which piece of it, where) and every text, in the order the
game adds them. Positions are the ones the code gives each picture's
position field. A text's position is the top left corner of its box
(app.vis.Text, docs/text-drawing.md); how a picture is drawn from its
position is not read (taken as its top left corner).

    python -I scripts/reference/nightpics.py <assets dir> list   <night.json | demo>
    python -I scripts/reference/nightpics.py <assets dir> render <night.json | demo> <out.png>

render draws the pictures and the texts (needs Pillow; texts through
text.py) on a 570 x 320 grey screen, so their places can be compared with
a screenshot.

night.json holds:
    {"members": [{"name": "Wife", "emotions": ["COLD", "SICK"]}, ...],
     "apartment": "C8", "tokens": ["Impor"], "upgrades": ["INSPECT_HOTKEY"],
     "haveFamilyPassports": 1, "numEscapePassports": 0}
"members" lists every member of Family.members, dead ones too, in the
family's order; "emotions" are names from EMOTIONS (nights.Member.emotions
gives them). "tokens" is Night/TokenIds followed by the day's token ids.
"""

import json
import os
import sys

# The screen (Layout, desktop block).
SCREEN_W, SCREEN_H = 570, 320

# FamilyVisualsDim with no footer scale given: scale 1.
TOKEN_SIZE = 29
APARTMENT_W, APARTMENT_H = 40, 30
UPGRADE_W, UPGRADE_H = 45, 15
PASSPORT_W, PASSPORT_H = 30, 40
STATUS_ICON = 30
MOOD_PADDING_X = -2

# The positions the LANDSCAPE branch of the constructor sets.
APARTMENT_POS = (int(520 - APARTMENT_W * 0.5), 9)          # (500, 9)
FAMILY_STEP = (0, STATUS_ICON + 13)                         # (0, 43)
FAMILY_CENTER_X = 520
TOKENS_POS0 = (25, 60)
TOKENS_STEP = (0, TOKEN_SIZE + 2)                           # (0, 31)
UPGRADES_POS0 = (69, 205)
UPGRADES_STEP = (0, UPGRADE_H + 3)                          # (0, 18)
PASSPORT_POS = (76, 158)

NAME_COLOR = 0xff556855                  # kFamilyStatusColor
OBRISTAN_COLOR = 0xff8a0c0c              # kObristantFamilyStatusColor

# Emotions.png: one 30 x 30 piece per emotion, top to bottom, in the order
# of the Emotion enum; get_emotionFlags sets bit (index) for each.
EMOTIONS = ["HAPPY", "OK", "SAD", "COLD", "SICK", "VERYSICK", "DEAD", "HUNGRY"]
# FamilyVisuals.imageTokenIds: the pieces of Tokens.png, top to bottom.
IMAGE_TOKEN_IDS = ["Empty", "Obristan", "UnitedFed", "Republia", "Antegria", "Impor", "Kolechia", "Arstotzka"]
# The pieces of Upgrades.png, top to bottom (the array the constructor builds).
UPGRADE_PIECES = [None, "INSPECT_HOTKEY", "STAMPBAR_HOTKEY", "RULEBOOK_TABS", "INSPECT_DOUBLECLICK",
                  "BOOTH_MULTITOUCH"]
# StoryState.kValidUpgradesDesktop, in its order.
VALID_UPGRADES_DESKTOP = ["INSPECT_HOTKEY", "STAMPBAR_HOTKEY", "RULEBOOK_TABS", "INSPECT_DOUBLECLICK"]
APARTMENT_PIECE = {"C5": 3, "C6": 2, "C7": 1}        # anything else: piece 0 ("8 CLASS")

DEMO = {
    "members": [{"name": "Wife", "emotions": ["SICK"]},
                {"name": "Son", "emotions": ["COLD", "SICK"]},
                {"name": "Mother-in-law", "emotions": ["COLD", "SICK", "HUNGRY"]},
                {"name": "Uncle", "emotions": ["OK"]}],
    "apartment": "C8", "tokens": [], "upgrades": [],
    "haveFamilyPassports": 1, "numEscapePassports": 0,
}


def floor(x):
    return int(x // 1)


def tokens_order(assets_dir):
    """Facts.xml <misc tokenOrder="...">, split on spaces. (Facts.xml is not
    well-formed XML, so the attribute is found by pattern.)"""
    import re
    text = open(os.path.join(assets_dir, "data", "Facts.xml"), encoding="utf-8").read()
    return [t for t in re.search(r'tokenOrder="([^"]*)"', text).group(1).split(" ") if t.strip()]


def layout(night, token_order, font=None):
    """Returns the items in the order the game adds them to its list.
    A picture: ("pic", file, (x, y, w, h) piece or None for the whole file,
    scale, x, y). A text: ("text", text, colour, x, y)."""
    items = []

    piece = APARTMENT_PIECE.get(night.get("apartment"), 0)
    items.append(("pic", "ApartmentClass.png", (piece * APARTMENT_W, 0, APARTMENT_W, APARTMENT_H), 1,
                  APARTMENT_POS[0], APARTMENT_POS[1]))

    members = night["members"]
    center0_y = floor(SCREEN_H * 0.5 - ((len(members) - 1) * FAMILY_STEP[1] + STATUS_ICON) * 0.5)
    for index, member in enumerate(members):
        cx = index * FAMILY_STEP[0] + FAMILY_CENTER_X
        cy = index * FAMILY_STEP[1] + center0_y
        shown = sorted(set(member["emotions"]), key=EMOTIONS.index)       # bit order
        count = len(shown)
        width = MOOD_PADDING_X * (count - 1) + STATUS_ICON * count
        height = STATUS_ICON
        step_x = (width - STATUS_ICON) / (count - 1) if count >= 2 else 0
        step_y = (height - STATUS_ICON) / (count - 1) if count >= 2 else 0
        for j, emotion in enumerate(shown):
            items.append(("pic", "Emotions.png", (0, EMOTIONS.index(emotion) * STATUS_ICON, STATUS_ICON, STATUS_ICON),
                          1, floor(j * step_x + (cx - width * 0.5)), floor(j * step_y + (cy - height * 0.5))))
        name = member["name"]
        text_w = font.text_width(name) if font else 0
        text_y = floor(STATUS_ICON * 0.5 + cy) - (font.ascent if font else 0) + (font.cap_height if font else 0)
        items.append(("text", name, NAME_COLOR, floor(cx - text_w * 0.5), text_y))

    # Tokens: a place for each name of tokenOrder, a piece for each name of
    # imageTokenIds. Empty places get the "Empty" piece and come first.
    placed = {}
    for token in night.get("tokens", []):
        if token not in IMAGE_TOKEN_IDS:
            continue
        if token in token_order:
            slot = token_order.index(token)
            placed[slot] = token                       # a later duplicate lands on the same place
    for slot in range(7):
        if slot not in placed:
            items.append(("pic", "Tokens.png", (0, 0, TOKEN_SIZE, TOKEN_SIZE), 1,
                          slot * TOKENS_STEP[0] + TOKENS_POS0[0], slot * TOKENS_STEP[1] + TOKENS_POS0[1]))
    for token in night.get("tokens", []):
        if token in IMAGE_TOKEN_IDS and token in token_order:
            slot = token_order.index(token)
            frame = IMAGE_TOKEN_IDS.index(token)
            items.append(("pic", "Tokens.png", (0, frame * TOKEN_SIZE, TOKEN_SIZE, TOKEN_SIZE), 1,
                          slot * TOKENS_STEP[0] + TOKENS_POS0[0], slot * TOKENS_STEP[1] + TOKENS_POS0[1]))

    # Passports.
    have_family = night.get("haveFamilyPassports", 1)
    if have_family == 1:
        alive = sum(1 for m in members if "DEAD" not in m["emotions"])
        count = alive + 1
    else:
        count = night.get("numEscapePassports", 0)
    if count != 0:
        name = "papers/PassportOuterArstotzka.png" if have_family == 1 else "papers/PassportOuterObristan.png"
        items.append(("pic", name, None, 0.5, PASSPORT_POS[0], PASSPORT_POS[1]))
        text = "x%d" % count
        text_h = font.line_height if font else 0          # one line, no padding: Text.height is the line height
        items.append(("text", text, NAME_COLOR if have_family == 1 else OBRISTAN_COLOR,
                      PASSPORT_POS[0] + PASSPORT_W + 1, PASSPORT_POS[1] + PASSPORT_H - text_h))
    else:
        items.append(("pic", "NightPassportFrame.png", None, 1, PASSPORT_POS[0], PASSPORT_POS[1]))

    # Upgrades: one place per upgrade this platform offers.
    held = set(night.get("upgrades", []))
    for i, upgrade in enumerate(VALID_UPGRADES_DESKTOP):
        frame = UPGRADE_PIECES.index(upgrade) if upgrade in held else 0
        items.append(("pic", "Upgrades.png", (0, frame * UPGRADE_H, UPGRADE_W, UPGRADE_H), 1,
                      floor(i * UPGRADES_STEP[0] + UPGRADES_POS0[0]), floor(i * UPGRADES_STEP[1] + UPGRADES_POS0[1])))
    return items


def load_night(arg):
    if arg == "demo":
        return DEMO
    with open(arg, encoding="utf-8") as f:
        return json.load(f)


def main():
    assets_dir, command, night_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fonts
    font = fonts.FontLib(assets_dir).get("regular")
    items = layout(load_night(night_arg), tokens_order(assets_dir), font)
    if command == "list":
        for item in items:
            if item[0] == "pic":
                _, name, piece, scale, x, y = item
                print("picture %-36s piece %-18s scale %-4s at %4d, %4d" % (name, piece, scale, x, y))
            else:
                _, text, colour, x, y = item
                print("text    %-36r colour %08x                at %4d, %4d" % (text, colour, x, y))
    elif command == "render":
        from PIL import Image
        import text as T
        screen = Image.new("RGBA", (SCREEN_W, SCREEN_H), (40, 40, 40, 255))
        for item in items:
            if item[0] == "pic":
                _, name, piece, scale, x, y = item
                picture = Image.open(os.path.join(assets_dir, name)).convert("RGBA")
                if piece:
                    px, py, pw, ph = piece
                    picture = picture.crop((px, py, px + pw, py + ph))
                if scale != 1:
                    # Image.transformed, as the game halves the covers (factpics.py)
                    import factpics as FP
                    source = FP.F.Image(picture.width, picture.height)
                    source.px = [(a << 24) | (r << 16) | (g << 8) | b for r, g, b, a in picture.getdata()]
                    small = FP.transformed(source, 0.0, scale)
                    picture = Image.new("RGBA", (small.width, small.height))
                    picture.putdata([((c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24) for c in small.px])
                screen.alpha_composite(picture, (x, y))
            else:
                _, string, colour, x, y = item
                label = T.Text(font, string, multi_line=True, align="CENTER", color=colour)
                screen.alpha_composite(T.render(label, assets_dir, margin=0, backdrop=False), (x, y))
        screen.save(sys.argv[4])
        print("wrote", sys.argv[4])
    else:
        sys.exit("unknown command: " + command)


if __name__ == "__main__":
    main()
