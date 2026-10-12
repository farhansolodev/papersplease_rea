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
  version v1.4.11.124 (63294).
- Unity 2020.3.34, IL2CPP build. There are no managed C# assemblies.
  - `GameAssembly.dll` (13.8 MB): all game logic, compiled to native code.
  - `PapersPlease_Data\il2cpp_data\Metadata\global-metadata.dat`: the type,
    method and string names needed to make sense of `GameAssembly.dll`.
  - `UnityPlayer.dll`: the stock engine. Not a reverse-engineering target.
  - `PapersPlease_Data\sharedassets0.assets`, `sharedassets0.resource`,
    `globalgamemanagers.assets(.resS)`, `level0`, `Resources\`,
    `StreamingAssets\`: the assets.

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
- REA's Ghidra requests time out on `GameAssembly.dll` (see `STATUS.md`), so
  that DLL is analysed by running Ghidra's `analyzeHeadless` directly.
- Rust, Bevy and the wasm toolchain have not been checked or set up yet.
- Setup references, only if a problem comes up:
  - https://github.com/morluto/rea/blob/main/docs/installation.md
  - https://github.com/morluto/rea/blob/main/docs/windows-ghidra-p0.md

## How to work

- **Recover IL2CPP names first.** Raw `GameAssembly.dll` without the names from
  `global-metadata.dat` is not worth analysing.
- **Reimplement from understanding.** Do not transliterate decompiler output
  into Rust.
- **One thing at a time.** Get one thing working, then write down how it works.
  Do not bundle unrelated changes; I want to be able to revert a single step.
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
- Record failures alongside successes, so a dead end is not repeated.
- If you cannot solve something after two real attempts, stop and write
  `STATUS.md`: the goal, what works (tested), the current problem, the evidence,
  what was tried, and ideas not tried yet.

## Files to keep updated

- `MODLOG.md`: add an entry after every change, newest first, in the format at
  the top of that file.
- `docs/`: confirmed findings (formats, game rules, class layouts) and
  `docs/DESIGN.md` for how the port works. Update when something is confirmed
  or the architecture changes, not on every change.
