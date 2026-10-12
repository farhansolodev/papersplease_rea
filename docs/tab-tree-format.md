# The indented-tree text format

Studied on 2026-10-12. This is the generic reader behind `Travelers.txt`.
Functions read in full: `Res.getTabParser`, `Res.getText`, `Res.toAsset`,
`data.TabParser` constructor and `expandParams`, `data.Node` constructor,
`consume`, `getTabIndent`, `findNode`, `expandParams`, `getExpanded`,
`app.StringUtil.splitQuoted`, `splitAndTrim` and `compareStrings`.

Reference implementation: `scripts/reference/tabtree.py`.

Everything here is confirmed in the code unless marked otherwise.

## What it produces

A tree of nodes. Each node has a list of text parameters (the words on its
line) and a list of child nodes (the lines indented one level beneath it).

## How a file becomes a tree

1. **Text.** Every asset that is not a `.png` is kept as text.
2. **Block comments.** Everything from `#*` to the next `*#` is deleted,
   repeatedly, before anything else. An unclosed `#*` is an error.
3. **Lines.** The text is split at line-feed characters.
4. **Line comments.** A line is cut at its first `#`, wherever it is, even
   inside quotes. So `#` can never appear in data.
5. **Blank lines** (after the cut) are skipped.
6. **Indentation** is the number of leading **tab** characters. Spaces do
   not count. A line indented exactly one more than a node is that node's
   child. A line indented two or more deeper than its parent is an error
   ("Invalid indent on line").
7. **Parameters.** The line is split into tokens: a run of characters with
   no whitespace, or a `"double quoted"` run, which may contain spaces. A
   backslash inside quotes protects the next character, but the backslash is
   kept in the token.
8. **Speech lines.** If a line starts with a `"` followed by whitespace, its
   first parameter is `"` and the rest of the line is split as in step 7.
   The opening quote does not start a quoted token.

The root node has no parameters; its children are the unindented lines.

## Lookups

- `findNode(text)`: the first child whose first parameter equals `text`.
- `TravelerLib.getAllTravelerIds`: the first parameter of every top-level
  node, sorted by plain character order (`compareStrings`).

## Templates

The reader has a template feature (`Node.expandParams`, `getExpanded`):

- A node whose parameters include one starting with `$` (three characters or
  longer) is replaced by a copy of the top-level node named `*` plus the rest
  of that word. In the copy, `$1`, `$2`, ... become the parameters that
  followed (**numbered from 1**; confirmed from the raw instructions), and a
  parameter of the form `*name` or `*name:variant` becomes `name`.
- The copy's parameters replace the `$` word and everything after it; its
  children are placed before the node's own children. Only the first `$`
  word on a line is handled. Children are then expanded the same way.

Expansion is a separate step that the loader has to ask for:

- **`Errors.txt` uses it.** `ErrorLib` calls `expandParams` (through a
  method table, which is why a search for direct callers found none). See
  `errors-txt-format.md`.
- **`Travelers.txt` does not.** `TravelerLib` never asks for it. That file
  has speech lines such as `" $ask-purpose` with no matching `*ask-purpose`
  node, which would raise "Node not found" if it were expanded.

## Language packs

`Res.getTabParser` passes the finished tree to the active language pack
(`locPack.localizeTab`) when there is one. What that changes is not studied.

## Checks

Run on the real `Travelers.txt`:

- The reference reader parses the whole file without error: 185 top-level
  nodes, 2,974 nodes in all, deepest level 6. The file's deepest indent is 6
  tabs and no line starts with a space.
- One block comment, 12 lines long, is removed.
- All 142 distinct traveler ids named in `Days.csv` (`TRAVELERS` and `FILL`
  rows, 287 uses) exist as top-level nodes.
- All 113 `INCLUDE` lines name an existing top-level node.

Run on the real `Errors.txt` with template expansion: 768 nodes become 981,
all 82 template uses are replaced, and no `$` reference is left.

The reference reader has not been compared with the game's own output,
because the tree only exists inside the running game.

```powershell
python -I scripts\reference\tabtree.py extracted\art\assets\data\Travelers.txt
```
