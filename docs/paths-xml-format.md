# Paths.xml: paths and animations of the border scene

Studied on 2026-10-14. `Paths.xml` describes how the little figures in the
top view (the queue, the entrant, guards, the truck, the motorbikes...) move:
**paths** (lists of points to walk along, chained one after another) and
**animations** (which picture strip to play and how fast).

Reference script: `scripts/reference/paths.py`. Check:
`scripts/checks/paths_check.py`.

Functions read in full: `data.PathLib` (constructor, `createPath`,
`hasPath`), the `data.Path` constructor and its `_getOnPath`, `getOnPath`,
`fillFromOnPath`, `getDistForStop`, `get_firstPoint`, `get_hasPoints`; the
`data.Anim` constructor; `app.XmlUtil.getNextSibling`. **Not studied:** the
code that uses them (`play.day.border.Border`, `Person`, `WaitingLine`): how
a figure follows a path over time, what each event does, how `hold`, `delay`,
`warp`, `snap` and `face` are applied. Their meanings below are from the
names and the data, marked as inferred.

## The file

The root `<border>` has two kinds of children, in any order: `<anim>` and
`<path>`. Other children are ignored. The library keeps the raw elements in
two tables by id; a path or animation object is only built when asked for.

A `<path>` without an `id` is given one of the form `auto-<number>` when the
file is loaded. (Which number was not recovered from the code. Nothing in
the data refers to those names; unnamed paths are only reached through
`next="NEXT"`.)

### `<anim>`

| Attribute | Default | Meaning |
|---|---|---|
| `id` | required | name used by `anim="..."` on a path |
| `suffix` | required | ending of the picture-strip name for moving sideways (the figure's own name comes first; inferred) |
| `suffixv` | same as `suffix` | the strip for moving up or down |
| `loop` | false | `true` repeats the animation |
| `fps` | required | pictures per second, sideways; 0 is used for a still pose |
| `fpsv` | same as `fps` | pictures per second, up or down |
| `sound` | none | a sound id from `Sounds.xml` |
| `death` | false | `true` marks a dying animation (inferred from the name) |
| `offset` | `0 0` | two numbers, a shift of the picture |

### `<path>`

| Attribute | Default | Meaning |
|---|---|---|
| `id` | automatic | name |
| `next` | none | the path to continue with. The word **`NEXT`** means the next `<path>` element in the file; if there is none, the word stays as it is |
| `speed` | 10 | movement speed |
| `anim` | `walk` | animation id; an unknown one is an error |
| `start`, `end`, `die` | none | event names sent at those moments (inferred: start of the path, its end, the figure's death) |
| `snap` | false | `true` requires at least one point (an error otherwise). Inferred: jump to the first point instead of walking there |
| `delay`, `hold` | 0 | waiting times (inferred: before starting, and after arriving) |
| `sound` | none | a sound id |
| `warp` | false | (meaning not studied) |
| `face` | none | `left` or `right` in the data (inferred: which way the figure looks) |

Children `<p>`: the points, in order.

| Attribute | Meaning |
|---|---|
| `xy` | two numbers, the point |
| `randomize` | optional, two numbers `rx ry`: the point is moved by a random amount, **two draws**: `x += (r1 - 0.5) * rx`, then `y += (r2 - 0.5) * ry` |

The random generator is handed in by whoever creates the path. A path is
built afresh each time it is asked for, so a randomized path differs each
time. Which generator the border scene uses was not followed up here; it is
**not** the booth's own generator unless the border passes that one in
(`desk-drawing-draws.md` lists who uses the booth's).

## What a path object offers

- **Length**: the sum of the straight distances between consecutive points.
- **Point at a distance** (`getOnPath(dist)`): walk along the segments; past
  the end it is the last point.
- **Number of stops** is always set to 1 here, and `getDistForStop(stop)` is
  `min(1, stop / stops) * length`. (Something else may change the number of
  stops later, for the waiting line; not followed up.)
- First point, and whether it has points at all. **A path may have no
  points**: 151 of the 309 do. Those only play an animation, wait, or send
  an event.

## Cross-check with the file

`paths_check.py` (run 2026-10-14):

- Root `<border>` with 39 `<anim>` and 309 `<path>` children and nothing
  else; no path is nested in another. The file has 24 comments (one spans
  several lines and hides a block of paths).
- Every attribute in the file is one the code reads: 13 on `<path>`, 9 on
  `<anim>`, 2 on `<p>`.
- 191 paths have their own id (none repeated), 118 are unnamed.
- `next`: 202 use `NEXT` and each has a path after it; 27 name a path, and
  all 27 exist; 80 have none.
- All 40 animation names used by paths exist (83 paths use the default
  `walk`).
- 15 points have a random spread (the waiting line's six points among them).
- 36 different event texts. Some carry extra words, for example
  `tell guard2 shot` and `spawn-explosion 5 -20`; the first word of every
  one is among the code's strings. What they do is in the border code.
- 5 sound ids are named; all exist in `Sounds.xml`.
- 112 of the 191 path ids are not whole strings in the code. So the code
  must build path names from parts (the data has families such as
  `disperse-0`, `disperse-1`, `disperse-2`); how is in the border code.
- The reference builds all 309 paths without error.

## Not known / not tested

- Everything about following a path over time (see the top).
- Nothing here was compared with the running game.
