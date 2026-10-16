# Scope drift: a note for reference

Written 2026-10-16 at the user's request, after drawing part 4.

## What is happening

Each step ends with a "suggested next part" in `docs/PROGRESS.md`. When
the next part is done, it does not match that suggestion:

- some of the suggested items are quietly left out;
- things nobody asked for are added to the step;
- what was left out, plus new things found while reading, become the
  next suggestion.

So the list of remaining work grows as fast as it shrinks.

## Example: drawing part 4

Suggested: `setInnerImage` and `addInnerVisual`, `Image.render`,
`compareProximity`, the inspect mode. Then the rest of `app.vis` and
`play.ui`, and input handling. Then audio.

Done: the first three. **The inspect mode was left out without saying
so.** Added without being asked: the drawer, wall and rack pictures,
clipping, click tests, stamp ink, the carousel question. Pushed to
"part 5": the inspect mode, plus new items (dragging, the reveal and
hide animations, the desktop sizes of the booth's rectangles).

## Why

Reading any piece of code shows the code next to it. Each unread
neighbour gets written under "Not studied" and then promoted to the
next steps. The drawing step never had a finish line, so anything found
could become another part.

## Decision for now

The user chose (2026-10-16) to keep going at this pace, in case this is
simply how a project like this goes. Nothing in the process was changed.

## If it keeps happening

Options discussed, none adopted yet:

- Give each step a fixed end, written down before it starts, and say up
  front if an item will be dropped.
- Put what is found during a step under open questions, not next steps;
  only the user adds next steps (this would be a rule in `CLAUDE.md`).
- Read neighbouring code only when the port needs it.

Signs to watch for: a "suggested next part" that is longer than the
last one; an item that moves from one suggestion to the next more than
once; a step whose "Not studied" list is longer than what it studied.
