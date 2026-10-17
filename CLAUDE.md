# Papers, Please browser port

Sanity check: if I ask for the code word, answer "Jeremy Renner".

## Goal

Port my own copy of Papers, Please to run in the browser:

1. Decompile the local game to understand its logic and data formats.
2. Rewrite the game in Rust with Bevy, compiled to WebAssembly.
3. Extract the assets and convert them to formats the browser build can load.

## Hard rules, never break these

1. **Never commit game assets, decompiled code, dumps or extracted game files.**
   They are copyrighted and stay on this machine in the gitignored folders
   (`game/`, `extracted/`, `dumps/`, `decompiled/`). Only my own Rust code,
   tooling and notes get committed, and nothing from the game goes on a public
   host.
2. **Do not run `git commit` unless I asked.** Stage nothing beyond what the
   current task requires.
3. **Do not touch anything outside this project folder** unless I explicitly
   name the path. The game install is read-only: copy files into this project
   before working on them.
4. **Single-player and offline only.** If something touches online play,
   anti-cheat or DRM, stop and tell me.
5. **Never put credentials in the repo or in any file you can read.**
6. **Tell me before downloading any tool**, with its name, source and size.

## Target

- Install: `C:\GOG Games\PapersPlease` (GOG, Windows x64, about 90 MB), game
  version 1.4.11.124 (63294).
- Unity 2020.3.34, IL2CPP build. There are no managed C# assemblies.
  - `GameAssembly.dll` (13.8 MB): all game logic, compiled to native code.
  - `PapersPlease_Data\il2cpp_data\Metadata\global-metadata.dat`: the type,
    method and string names needed to make sense of `GameAssembly.dll`.
  - `UnityPlayer.dll`: the stock engine. Not a reverse-engineering target.
  - `PapersPlease_Data\sharedassets0.assets`, `sharedassets0.resource`,
    `globalgamemanagers.assets(.resS)`, `level0`, `Resources\`,
    `StreamingAssets\`: the assets.

## Start here in a new session

1. Read `docs/PROGRESS.md` first: it has the current state, the ordered next
   steps, what is stuck, the open questions and the list of docs. Then
   `docs/ghidra-workflow.md` for the commands and how to read decompiled
   output.
2. Before any work, tell me which model the step needs, so I can switch while
   the session is still short (you cannot switch it yourself). Opus for
   decompilation and reverse-engineering reasoning, or a step that mixes that
   with routine work. Sonnet for doc updates, routine helper scripts and
   checks. If unsure, say Opus.
3. Give me the plan for the step and wait (see "Plan first" below).

## Tooling state

- REA 6.4.0 is registered for Claude Code, with the `reverse-engineer-anything`
  skill installed. Use the connected server's actual tool list, not assumptions.
  REA has no Unity IL2CPP-specific command, so name recovery and asset
  extraction will need other tools.
- Node 24.21. JDK 21 at
  `C:\Users\farha\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.6.7-hotspot`
  (`JAVA_HOME` points there).
- Ghidra 12.1.4 is installed at `C:\tools\ghidra_12.1.4_PUBLIC`
  (`GHIDRA_INSTALL_DIR` is set, and both paths are saved in the REA
  registration). `rea doctor --provider ghidra` passes. Hopper cannot be
  installed on Windows, so Ghidra is the only native engine, and REA's Windows
  Ghidra support is experimental and read-only.
- Il2CppDumper 6.7.46 is installed at `C:\tools\Il2CppDumper-6.7.46`. Its
  output for this game is in `dumps/il2cppdumper/`; see
  `docs/il2cpp-name-recovery.md`.
- REA's Ghidra requests time out on `GameAssembly.dll` (the record is at the
  end of `docs/ghidra-workflow.md`), so that DLL is analysed by running
  Ghidra's `analyzeHeadless` directly. The analysed project is saved in
  `decompiled/ghidra/`; scripts are in `scripts/ghidra/`.
- In Claude Code's PowerShell tool, `JAVA_HOME` resolves to
  `C:\Program Files\Eclipse Adoptium\jre-21.0.4.7-hotspot` (a JRE), not the
  JDK above. Ghidra runs fine regardless; call `javap` and `jar` by their
  full JDK path.
- Python 3.12 is installed and used for the helper scripts (run with
  `python -I`). Pillow 11.1.0 is installed for it; the face scripts
  (`scripts/reference/faces.py` and everything built on it) need it.
  numpy 2.4.6 is also installed for it (found 2026-10-17, not installed
  by this project); `scripts/checks/music_beat_check.py` needs it.
- UnityPy 1.25.4 (reads Unity's asset files) is installed only in the
  project's gitignored `.venv/` (2026-10-17); run scripts that need it
  with `.venv\Scripts\python -I`. It came with `fmod_toolkit` 0.1.3 and
  its FMOD library (`fmod.dll`), which decodes the game's sounds
  (`docs/audio.md`). Shader byte code is disassembled with
  Windows' own `D3DCompiler_47.dll`. See `docs/screen-output.md`, "The
  Unity files".
- Rust 1.99 and the `wasm32-unknown-unknown` target are installed (checked
  2026-10-12). `trunk`, `wasm-pack` and `wasm-bindgen` are not installed, and
  Bevy has not been set up or tried.
- Write docs and multi-line scripts with the file tools, not shell
  here-documents: quotes in the text have broken those repeatedly.
- Setup references, only if a problem comes up:
  - https://github.com/morluto/rea/blob/main/docs/installation.md
  - https://github.com/morluto/rea/blob/main/docs/windows-ghidra-p0.md

## How to work

- **Plan first.** Before doing a task, tell me what you are going to do, which
  files will change and how I can check the result, then wait for my go-ahead.
  Reading files to work out the plan is fine without asking. Editing or
  creating files, running scripts or Ghidra, and any git command wait for the
  go-ahead. A plain question gets a direct answer, with no plan step.
- **Recover IL2CPP names first.** Raw `GameAssembly.dll` without the names from
  `global-metadata.dat` is not worth analysing.
- **Search the whole decompile first.** All of the game's own code is
  decompiled in `decompiled/all/`. Start every question with a search
  there, and read whole classes rather than single functions.
- **Reimplement from understanding.** Do not transliterate decompiler output
  into Rust.
- **Correct over fast.** Read whole functions and confirm against the real
  data file. Never present a name match as a finding. Read the comments in
  data files (XML parsers drop them). Before calling anything unused or left
  over, search the other data files and the code's strings. Say what was
  observed and mark the rest as inferred; do not explain why something is the
  way it is without evidence. (On 2026-10-12, three name-based guesses about
  `Days.csv` and a "cut content" claim about the `journalist` purpose were
  all wrong.) The study method is in `docs/ghidra-workflow.md`.
- **One thing at a time.** Get one thing working, then write down how it works.
  Do not bundle unrelated changes; I want to be able to revert a single step.
  Each step gets its doc, its `MODLOG.md` entry and, when I ask for a commit,
  its own commit.
- **Keep older docs true.** When a step shows that something written earlier
  is out of date or wrong, fix that sentence in the same step. Two cases: a
  note that something is not studied, not checked or unknown, which the step
  has now answered; and an earlier finding, inference or guess that the step
  shows was wrong. Change the sentence itself, saying what is now known and
  which doc holds it; a note added at the end of the doc is not enough. For
  a statement that was wrong, also say that it was corrected and when, and
  check whether another doc, a reference script or a check was built on it:
  fix those too, or list them as needing a fix. Before finishing a step,
  search `docs/` for the step's main names (classes, functions, file names)
  to find such sentences, and list the docs corrected in the step's
  `MODLOG.md` entry. When a run of the game confirms something, do the same
  for "not compared with the running game" lines, and say how strong the
  evidence is.
- **Running the original game needs my go-ahead, each launch.**
- **Ask before large refactors.** If you think the architecture is wrong, say
  so and explain, then wait for me.
- **Verify with evidence.** For the original game you cannot see the screen, so
  rely on logs, numbers and dumped data. For the browser build, run it and look.
- **Tell me how to test it.** After every change, give the exact command to run
  and what I should see. "Done" without a test procedure is not done.
- **Explain in plain language.** I am not the programmer here. Explain a term
  the first time you use it.

## Honesty

- If something is not tested, write "not tested". Never imply you verified
  something you didn't.
- If you are not sure, say so. A confident wrong answer costs me hours.
- Do not call something confirmed on thin evidence: say how many real
  alternatives each matching result had.
- Record failures alongside successes, so a dead end is not repeated.
- If you cannot solve something after two real attempts, stop. Write the stuck
  report in the step's doc under a "Dead ends" heading: the goal, what works
  (tested), the current problem, the evidence, what was tried, and ideas not
  tried yet. Add a short entry under "Currently stuck" in `docs/PROGRESS.md`
  that points to it. When the problem is solved, remove that entry and keep
  the report, marked resolved.

## What each file is for

Each kind of information lives in one place. Do not repeat it in another.

| File | Its only job | When to update |
|---|---|---|
| `CLAUDE.md` (this file) | The rules for how to work, plus the goal, the target and the tooling state | When I give a new standing rule, or the tooling changes |
| `docs/PROGRESS.md` | Where the project stands: current state, next steps, what is stuck, open questions, the list of docs | At the end of every step, without being asked: the next session starts from it |
| `MODLOG.md` | Diary: what was changed and how it was tested | After every change, newest first, in the format at the top of that file |
| `docs/<topic>.md` | What was learned about one topic (a format, a game rule, a class layout), including its dead ends | When something is confirmed, not on every change; and when a later step answers one of its open notes or shows one of its statements was wrong |
| `docs/DESIGN.md` | How the port works (not written yet) | When the architecture changes |

- Rules live only in this file. When I give a new standing rule, propose the
  edit here. Do not save it as a Claude memory note and do not copy it into
  `docs/PROGRESS.md`.
- `MODLOG.md` is long. Read its newest entries when needed, not the whole
  file.
