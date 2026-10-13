# Three data files the game does not read

Looked at on 2026-10-14: `Threads.txt`, `TravelerGraph.txt` and
`Version.txt` sit in the game's data folder, but the game's code never loads
them. They look like the developer's own notes and build leftovers. The port
does not need them; `Threads.txt` is still a handy overview of the story.

Check: `scripts/checks/notes_files_check.py`.

## Why "not read" is a safe statement

- None of the three names appears among the code's strings.
- Data files are always asked for by a whole name: all 30 strings that start
  with `assets/data/` are complete file names, and there is no bare
  `assets/data/` or `.txt` string from which a name could be glued together.
  (The only folder prefixes that exist on their own are `assets/`,
  `assets/achievements/`, `assets/faces/`, `assets/fonts/`, `assets/intro/`
  and `assets/papers/`.)

What this does not rule out: a name built letter by letter, which would be
very unusual. Not tested by running the game without the files.

## Version.txt

One line: `1.4.11.124`, the game's version (the same number as the
installed game, see `CLAUDE.md`). Where the game gets the version it shows
on screen was not looked up; it is not from this file.

## Threads.txt

179 lines, an indented outline of the story's threads: which event leads to
which. The marks, as far as they can be read from the content (**inferred,
nothing in the code explains them**):

- a plain upper-case word is a traveler script (90 of the 121 such words are
  entries of `Travelers.txt`; the other 31 are not, so the notes are partly
  out of date or use other names);
- `@NAME` is a news article: all 35 are entries of `News.txt`;
- `[...]` is a feature or rule being introduced (`[WorkPermit]`,
  `[SEARCH/NoContraBand/SearchKolechia]`);
- `^NAME` looks like a border event (`^RUNNER`, `^TRUCK`, `^BIKE0`);
- `#` and `*` start sections (`#FEATURES`, `*STUFF`).

## TravelerGraph.txt

231 lines. It describes, as indented trees, the possible orders of a
traveler's responses at the booth (`Intro-Replace`, `Approved`, `Denied`,
`Detain-After`, `Give-<paper>`...; these are the response names of
`responses-and-events.md`), first for general "process" patterns and then in
six `Graph <name>` blocks for particular story lines (`KID_KILLER`, ...).
Lines starting with `>` name the next traveler script (38 of the 62 are
entries of `Travelers.txt`), and lines starting with `=` name a saved fact
and a value. It reads like the input of a tool that draws or checks these
flows; no such tool is in the game.

## Not known

- Whether an earlier build read any of these.
- The exact meaning of every mark; it does not matter for the port.
