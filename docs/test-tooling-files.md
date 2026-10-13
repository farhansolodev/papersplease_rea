# The two test-tooling data files: TestScenarios.xml and Auto.txt

Studied on 2026-10-14. Neither file is used in normal play. They are the
developer's test aids, shipped with the game. They are worth knowing because
`Auto.txt` is in effect **a tested recipe for reaching every ending**, which
the port can reuse as a test plan.

Check: `scripts/checks/testfiles_check.py`.

Read in full: the `data.TestScenarioLib` and `data.TestScenario`
constructors. Read in part: `test.auto.AutoRouteSet` and `AutoRoute`
(constructors and `getTabNode`, only for the file's structure). The test
player itself is described in `comparing-with-the-game.md`. **Not studied:**
where a test scenario is started from, and how the test player carries out
each action word.

## TestScenarios.xml

A list of starting situations for trying one part of the game directly.

    <scenarios>
        <scenario id="day-18" day="18" cleargamefacts="true">
            <fact path="Game/PrisonGuard" val="4"/>
            ...

| Attribute of `<scenario>` | Meaning |
|---|---|
| `id` | name |
| `cleargamefacts` | `true`: start from an empty saved story (inferred from the name `clearStoryFacts`) |
| `day` | start at this day; missing means none (-1) |
| `night` | start at the night after this day; missing means none (-1) |
| `traveler` | start at this traveler; missing means none |

Each `<fact path="..." val="...">` child sets one saved fact first.

The library is loaded with the other data (`Db.testScenarioLib`) but which
code starts a scenario was not looked for. `Game.applyScreenChange` has
"skip to day" and "skip to traveler" jumps (`comparing-with-the-game.md`)
that such a scenario would fit.

Cross-check (`testfiles_check.py`): 12 scenarios; every attribute is one the
loader reads; 3 start at a day, 4 at a night, 5 at a traveler; they set 16
`Game/` facts and 24 `Night/` facts. One names the traveler `BOSS`, which is
not an entry of `Travelers.txt` (there are `BOSS0`, `BOSS1`, `BOSS2`...), so
that scenario is probably out of date.

## Auto.txt

The script of the test player: which routes exist and what to do on each.
An indented tree (`tab-tree-format.md`). Lines starting with `#` are
comments.

### The route list

The block named `@` lists the routes:

    story 1 in-debt
    endless 100 timed course1

`story <number> <name>`: play the story to the ending `<name>`.
`endless <number> <style> <course>`: play one endless game. The number is
what `routes` in `auto.plan` refers to.

### The instruction blocks

Every other top-level block is a set of instructions:

    <block name> [<base block>]
        <traveler id or special name>
            <action> ...

- `default` applies to every route.
- A route uses the block with its own name. A second word on the block's
  first line names a **base block** it builds on (`base-ignore-ezic`,
  `base-help-ezic`).
- Inside a block, each entry is a traveler's script id, or `*` for any
  traveler, or a special name the test player understands: `NIGHT` (every
  night), `NIGHT_<day>`, `ATTACK_<day>`, `HANG_ON_WALL`, and one
  `CONFISCATE_...` name.
- Under an entry come the actions. At the booth: `interrogate`,
  `stamp APPROVED|DENIED|WRONG`, `give <paper>`, `giveall`,
  `giveallexcept <paper>`, `confiscate`, `detain`, `click <paper> <mark>`,
  `poison`, `hold`, `wait`, `snipe`. At night: a budget line's label in
  quotes followed by `YES`, `EVEN` or `ODD` (tick it always, or on even or
  odd days; inferred from the words).

The order in which the blocks are consulted (the route's own, its base,
`default`, and `*`) was read only roughly and is not written down here.

Cross-check (`testfiles_check.py`):

- 33 routes: 21 story, 12 endless (the three styles times four courses).
- Every story route has a block of its own. 20 of the 21 names are endings
  in `Ends.xml`, and **every ending in `Ends.xml` has a route**. The 21st,
  `all-tokens`, is not an ending (it collects the tokens).
- 7 blocks build on a base; both bases exist.
- 48 entries are traveler ids and one is `*`. Eight names are not entries of
  `Travelers.txt`: the special names above. The words `NIGHT`, `NIGHT_`,
  `ATTACK_`, `HANG_ON_WALL`, `EVEN`, `ODD` and `WRONG` are all among the
  strings of the test player's code.

## Not known / not tested

- See "Not studied" at the top.
- Route 1 and part of route 20 have been run (`comparing-with-the-game.md`);
  the other routes have not.
