"""Checks the button pictures against the way the code cuts them (buttons.md).

Usage: python -I button_pictures_check.py <assets dir>   (needs Pillow)

<assets dir> is extracted\\art\\assets. For each picture the code turns into
button looks, it checks that the picture is where the code asks for it and
that the cut divides it exactly: rows of a given height stacked top to
bottom, or equal columns side by side. It also checks that the pictures the
code asks for only on phones are absent from the main folder: on desktop the
game never loads the layout folders (buttons.md, "Pictures only phones
have"), so a desktop build could not find them.
"""
import os
import sys

from PIL import Image

assets = os.path.join(sys.argv[1], "")
problems = []

# (picture, folder, cut, size of one piece, number of pieces, who cuts it)
# cut "rows": pieces are full-width bands of the given height, top first.
# cut "cols": pieces are full-height columns, left first.
PICTURES = [
    ("PushButton.png", "", "rows", 19, 2, "GameScreen.makePushButton"),
    ("PushButtonRed.png", "", "rows", 19, 2, "GameScreen.makePushButton"),
    ("PauseButton.png", "", "rows", 19, 2, "GameScreen.enablePause"),
    ("PauseButtonBlack.png", "", "rows", 19, 2, "GameScreen.enablePause"),
    ("QuitButton.png", "", "rows", 17, 2, "TitleScreen (addImageButton)"),
    ("SettingsButton.png", "", "rows", 29, 2, "TitleScreen (addImageButton)"),
    ("VersionButton.png", "", "rows", 12, 2, "TitleScreen (addImageButton)"),
    ("WebpageButton.png", "", "rows", 11, 2, "GameScreen.addMediaButtons"),
    ("TwitterButton.png", "", "rows", 11, 2, "GameScreen.addMediaButtons"),
    ("LeaderboardsButton.png", "", "rows", 33, 2, "EndlessScreen (addImageButton)"),
    ("EndlessStyleButton.png", "", "rows", 80, 2, "EndlessScreen"),
    ("EndlessCourseButton.png", "", "rows", 60, 2, "EndlessScreen"),
    ("LoadDelete.png", "", "rows", 25, 3, "LoadScreen (normal, pressed, deleting)"),
    ("UnstashButton.png", "", "rows", 39, 2, "UnstashOverlay"),
    ("SettingButtonPlatform.png", "", "rows", 25, 2, "SettingRow.addPlatformButton"),
    ("ReasonButton.png", "", "rows", 30, 3, "DropButton (normal, flash, pressed)"),
    ("OuterBooth.png", "", "rows", 38, 2, "Border (normal, highlight; 38 = 103 - 65 on desktop)"),
    ("HoverButton.png", "layout/phone/", "rows", None, 2, "HoverButton (halves)"),
    ("HoverArrow.png", "layout/phone/", "cols", None, 2, "HoverButton (back, front)"),
    ("CriminalPosterPinButton.png", "layout/phone/", "cols", None, 4,
     "CriminalPosterPin (wait, 0, 1, pressed)"),
]

for name, folder, cut, piece, count, who in PICTURES:
    path = assets + folder + name
    if not os.path.exists(path):
        problems.append("%s: not found in %s" % (name, folder or "the main folder"))
        continue
    width, height = Image.open(path).size
    total = height if cut == "rows" else width
    if piece is None:
        piece = total // count
    ok = piece * count == total
    print("%-28s %-14s %3d x %-3d  %d %s of %d  %s%s" % (
        name, folder or "main", width, height, count, cut, piece, who,
        "" if ok else "   <-- does not divide"))
    if not ok:
        problems.append("%s: %d %s of %d do not make %d" % (name, count, cut, piece, total))
    if folder and os.path.exists(assets + name):
        problems.append("%s: also in the main folder, so desktop could load it" % name)

print("problems: %d" % len(problems))
for p in problems:
    print("  " + p)
