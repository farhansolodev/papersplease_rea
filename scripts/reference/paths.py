"""Reference implementation of the border scene's paths and animations:
data.PathLib, data.Path and data.Anim (docs/paths-xml-format.md).

Run as a script to list the paths:

    python -I scripts/reference/paths.py <Paths.xml>
"""

import math
import re
import sys
import xml.etree.ElementTree as ET


def _float(text):
    match = re.match(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", text or "")
    return float(match.group(0)) if match else float("nan")


def _point(text):
    parts = text.split()
    return [_float(parts[0]), _float(parts[1])]


class Anim:
    def __init__(self, node):
        self.id = node.get("id")
        self.suffix_h = node.get("suffix")
        self.suffix_v = node.get("suffixv", self.suffix_h)
        self.loop = node.get("loop") == "true"
        self.fps_h = _float(node.get("fps"))
        self.fps_v = _float(node.get("fpsv")) if node.get("fpsv") is not None else self.fps_h
        self.sound = node.get("sound")
        self.death = node.get("death") == "true"
        self.offset = _point(node.get("offset")) if node.get("offset") is not None else [0.0, 0.0]


class Path:
    def __init__(self, rand, node, lib):
        self.id = node.get("id")
        self.next = node.get("next")
        self.move_speed = _float(node.get("speed")) if node.get("speed") is not None else 10.0
        self.end_event = node.get("end")
        self.start_event = node.get("start")
        self.die_event = node.get("die")
        self.snap = node.get("snap") == "true"
        self.delay = _float(node.get("delay")) if node.get("delay") is not None else 0.0
        self.hold = _float(node.get("hold")) if node.get("hold") is not None else 0.0
        self.sound = node.get("sound")
        self.warp = node.get("warp") == "true"
        self.face = node.get("face")
        if self.next == "NEXT":
            following = lib.next_path_node(node)
            if following is not None:
                self.next = following.get("id")
        anim_id = node.get("anim", "walk")
        if anim_id not in lib.anim_nodes:
            raise KeyError("no animation " + anim_id)
        self.anim = Anim(lib.anim_nodes[anim_id])
        self.points = []
        for p in node.findall("p"):
            point = _point(p.get("xy"))
            if p.get("randomize") is not None:
                spread = _point(p.get("randomize"))
                point[0] += (rand.random() - 0.5) * spread[0]
                point[1] += (rand.random() - 0.5) * spread[1]
            self.points.append(point)
        if self.snap and not self.points:
            raise ValueError("snap path without points: " + str(self.id))
        self.num_stops = 1
        self.length = sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))

    def on_path(self, dist):
        """The point `dist` along the path; past the end, the last point."""
        for a, b in zip(self.points, self.points[1:]):
            segment = math.dist(a, b)
            if dist < segment:
                t = dist / segment
                return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
            dist -= segment
        return list(self.points[-1])

    def dist_for_stop(self, stop):
        return min(1.0, stop / self.num_stops) * self.length


class PathLib:
    def __init__(self, xml_text):
        root = ET.fromstring(xml_text)
        self.path_nodes, self.anim_nodes = {}, {}
        self._order = []
        counter = 0
        for node in root:
            if node.tag == "path":
                if node.get("id") is None:
                    # The game gives it "auto-<number>". Which number was not
                    # recovered; nothing refers to these names in the data.
                    node.set("id", "auto-%d" % counter)
                    counter += 1
                self.path_nodes[node.get("id")] = node         # a repeated id replaces the earlier one
                self._order.append(node)
            elif node.tag == "anim":
                self.anim_nodes[node.get("id")] = node

    def next_path_node(self, node):
        index = self._order.index(node)
        return self._order[index + 1] if index + 1 < len(self._order) else None

    def has_path(self, path_id):
        return path_id in self.path_nodes

    def create_path(self, rand, path_id):
        if path_id not in self.path_nodes:
            raise KeyError("no path " + path_id)
        return Path(rand, self.path_nodes[path_id], self)


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rand import Rand
    lib = PathLib(open(sys.argv[1], encoding="utf-8").read())
    rand = Rand(1)
    for path_id in lib.path_nodes:
        path = lib.create_path(rand, path_id)
        print("%-28s points %2d length %7.1f speed %5.1f anim %-12s next %s" % (
            path.id, len(path.points), path.length, path.move_speed, path.anim.id, path.next))
