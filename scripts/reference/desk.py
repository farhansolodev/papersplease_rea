"""Reference implementation of the random draws made when a paper is drawn on
the desk: BoothEngine.addNewEnvPapers, the play.day.booth.Paper constructor
and the first page drawn by play.day.PaperInnerVisuals
(docs/desk-drawing-draws.md).

These draws come from the booth's own generator, the one that also picks
errors and document values, so they must be counted for the booth to stay in
step with the game. Only the number and order of the draws is modelled, not
the pictures.

The fingerprint and thumbprint pictures' draws are counted too
(docs/fact-pictures.md): a fresh random code that the fact's text then
overwrites (five draws plus redraws), then one draw per finger shown.

Not modelled: pages drawn again later (turning a page, following a link;
the contraband draw sits on the search photo's second page), a document
photo whose value is neither VALID nor a full face specification
(FaceSpec.fromString draws for each missing or '*' part; the generated
values were not checked for those), a picture fact with no fact at all
(no picture, no draw).
"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from person import make_fingerprints  # noqa: E402


class Mark:
    def __init__(self, node):
        self.has_range = node.get("pos") is not None and node.get("pos2") is not None
        image = node.get("image") or ""
        self.image_fact = image[1:] if image.startswith("$") else None
        self.emblem = node.get("emblem")


class PaperDrawDef:
    def __init__(self, node):
        self.rotate = node.get("rotate", "true") != "false"
        page = node.find("page")
        self.first_page = [Mark(m) for m in page.findall("mark")] if page is not None else []


class Desk:
    """The papers that have a picture on the desk, for one booth."""

    def __init__(self, papers_xml_text, booth):
        self.defs = {}
        for node in ET.fromstring(papers_xml_text).iter("paper"):
            self.defs.setdefault(node.get("id"), PaperDrawDef(node))    # first definition wins (not checked)
        self.booth = booth
        self.shown = []
        self.show_new_papers()                # the day's own papers: rulebook, transcript, bulletin, ...

    def shown_ids(self):
        """BoothEnv.getPaperIdWithIndexes: existing, visible papers, sorted."""
        booth = self.booth
        ids = [key for key in booth.paper_infos
               if booth.find_invalid_fact_path(key + "/Exists") is None
               and booth.value_text(key + "/Visible") != "NO"]
        return sorted(ids)

    def show_new_papers(self):
        """BoothEngine.addNewEnvPapers. The game runs it after every batch of
        operations and every event. Returns the ids newly drawn."""
        current = self.shown_ids()
        self.shown = [key for key in self.shown if key in self.booth.paper_infos]
        added = []
        for key in current:
            if key not in self.shown:
                definition = self.defs.get(key.split("_")[0])
                if definition is None:
                    continue                  # fact-only "papers" (Traveler, Speech, Booth) have no picture
                self.shown.append(key)
                added.append(key)
                self._draw(key, definition)
        return added

    def new_traveler(self):
        """Call right after Booth.make_new_traveler: only the papers that stay
        for the day or the game keep their picture; the new traveler's papers
        are then drawn."""
        keep = self.booth.env.lib.persist_paper_ids
        self.shown = [key for key in self.shown if key.split("_")[0] in keep]
        return self.show_new_papers()

    def _draw(self, key, definition):
        rand = self.booth.rand
        if definition.rotate:
            rand.random()                     # the tilt of the closed paper
        for mark in definition.first_page:    # Page.getInnerImageAndMarkPositions
            if mark.has_range:
                rand.random()
                rand.random()
        for mark in definition.first_page:    # PaperInnerVisuals, mark by mark
            if mark.image_fact == "Face":
                rand.random()                 # Face.getDocImage: a small vertical shift
            elif mark.image_fact is not None and mark.image_fact.startswith("Criminal"):
                if self.booth.value_text("%s/%s" % (key, mark.image_fact)) != "":
                    rand.random()
            elif mark.image_fact in ("Fingerprints", "Thumbprint"):
                make_fingerprints(rand)       # FingerprintCode.fromString: a random code first
                for _ in range(5 if mark.image_fact == "Fingerprints" else 1):
                    rand.random()             # FingerprintCode.getImage: one per finger shown
            if mark.emblem is not None:
                status = self.booth.value_text("%s/Emblem/%s" % (key, mark.emblem))
                if status in ("VALID", "INVALID"):
                    rand.random()             # which seal picture
                    rand.random()             # its x position
                    rand.random()             # its y position
