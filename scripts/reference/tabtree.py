"""Reference implementation of the game's indented-tree text parser.

This is data.TabParser + data.Node.consume + app.StringUtil.splitQuoted, as
used for Travelers.txt and other tab-indented data files. See
docs/tab-tree-format.md.

Run as a script to print a summary of a file:

    python -I scripts/reference/tabtree.py extracted/art/assets/data/Travelers.txt
"""

import re
import sys

TOKEN = re.compile(r'(?:"((?:[^"\\]|\\.)*)")|(?:([^\s]+))')
SPEECH_START = re.compile(r'^\s*"\s+')


class Node:
    def __init__(self) -> None:
        self.params: list[str] | None = None
        self.nodes: list["Node"] = []

    def find(self, first_param: str) -> "Node | None":
        """First child whose first parameter equals the given text."""
        for node in self.nodes:
            if node.params[0] == first_param:
                return node
        return None


def split_quoted(text: str) -> list[str]:
    """Split into tokens: a "double quoted" run, or a run without spaces."""
    tokens = []
    while text:
        match = TOKEN.search(text)
        if not match:
            break
        tokens.append(match.group(1) if match.group(1) is not None else match.group(2))
        text = text[match.end():]
    return tokens


def strip_block_comments(text: str) -> str:
    position = 0
    while True:
        position = text.find("#*", position)
        if position < 0:
            return text
        end = text.find("*#", position)
        if end < 0:
            raise ValueError("Unclosed block comment: " + text[position:position + 30] + "...")
        text = text[:position] + text[end + 2:]


def consume(node: Node, lines: list[str], line_index: int, tab_indent: int) -> int:
    """Fill `node` from `lines`, starting at `line_index`. Returns lines used."""
    if tab_indent < 0:
        node.params = []
    used = 0
    while line_index + used < len(lines):
        line = lines[line_index + used]
        comment = line.find("#")
        if comment >= 0:
            line = line[:comment]
        if not line.strip():
            used += 1
            continue

        if node.params is None:
            # The node's own line.
            speech = SPEECH_START.match(line)
            if speech:
                node.params = ['"'] + split_quoted(line[speech.end():])
            else:
                node.params = split_quoted(line)
            used += 1
            continue

        indent = len(line) - len(line.lstrip("\t"))
        if indent == tab_indent + 1:
            child = Node()
            used += consume(child, lines, line_index + used, indent)
            node.nodes.append(child)
        elif indent <= tab_indent + 1:
            return used
        else:
            raise ValueError(f"Invalid indent on line {line_index + used} ({indent})")
    return used


def parse(text: str) -> Node:
    root = Node()
    consume(root, strip_block_comments(text).split("\n"), 0, -1)
    return root


def walk(node: Node, depth: int = 0):
    for child in node.nodes:
        yield depth, child
        yield from walk(child, depth + 1)


def main() -> None:
    with open(sys.argv[1], encoding="utf-8", newline="") as f:
        root = parse(f.read())
    nodes = list(walk(root))
    print(f"top-level nodes: {len(root.nodes)}, all nodes: {len(nodes)}, "
          f"deepest level: {max(depth for depth, _ in nodes)}")
    kinds: dict[str, int] = {}
    for depth, node in nodes:
        first = node.params[0] if node.params else "(empty)"
        kind = "name" if depth == 0 else (first if not first[0].isalnum() else "word")
        kinds[kind] = kinds.get(kind, 0) + 1
    for kind, count in sorted(kinds.items(), key=lambda item: -item[1]):
        print(f"  {count:5}  {kind}")


if __name__ == "__main__":
    main()
