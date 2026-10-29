"""Builds the browser version into build/web/ (gitignored).

    python -I scripts/build_web.py            # full build
    python -I scripts/build_web.py --no-cargo # redo only the packaging
    python -I scripts/build_web.py --debug-names  # keep function names

Steps: cargo builds the WebAssembly (release); wasm-bindgen turns it into a
file plus the JavaScript glue the page needs; the start pack, the effects
pack and the songs are made (build_assets/); every built file gets its
content fingerprint in its name; the page, its sound player and the service
worker are copied from port/www; files.json lists everything. The build
code (a short hash of the file list and fingerprints) is baked into sw.js,
so a new build makes the browser install a new service worker.

The songs go into songs/ and are listed apart ("songs" in files.json): the
service worker keeps them when they first play, not when it installs
(docs/milestone-2.md).

Needs wasm-bindgen-cli in .cargo-home/bin (docs/milestone-0.md) and ffmpeg
on the PATH for the songs (docs/milestone-2.md).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build_assets"))
import build_audio  # noqa: E402
import build_pack  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CARGO_HOME = ROOT / ".cargo-home"
PORT = ROOT / "port"
OUT = ROOT / "build" / "web"
TARGET = "wasm32-unknown-unknown"
WASM_IN = ROOT / "target" / TARGET / "release" / "pp_web.wasm"
BINDGEN = CARGO_HOME / "bin" / "wasm-bindgen.exe"


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def main():
    env = dict(os.environ, CARGO_HOME=str(CARGO_HOME))
    if "--no-cargo" not in sys.argv:
        run(["cargo", "build", "--release", "--target", TARGET, "-p", "pp_web"],
            cwd=PORT, env=env)
    if not WASM_IN.exists():
        sys.exit(f"missing {WASM_IN}: run without --no-cargo first")
    if not BINDGEN.exists():
        sys.exit(f"missing {BINDGEN}: see docs/milestone-0.md")

    glue = ROOT / "build" / "_bindgen"
    for d in (glue, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    # The name section (function names, for debugging) was 37 of 63 MB in
    # the first build, so it is dropped unless --debug-names is given.
    strip = [] if "--debug-names" in sys.argv else \
        ["--remove-name-section", "--remove-producers-section"]
    run([BINDGEN, "--target", "web", "--no-typescript", *strip,
         "--out-dir", glue, "--out-name", "pp_web", WASM_IN])

    # name -> bytes, in the order they are listed.
    files = {}
    fingerprinted = []

    def add_fingerprinted(src: Path, stem: str, ext: str) -> str:
        data = src.read_bytes()
        name = f"{stem}.{fingerprint(data)}.{ext}"
        files[name] = data
        fingerprinted.append(name)
        return name

    app_js = add_fingerprinted(glue / "pp_web.js", "pp_web", "js")
    app_wasm = add_fingerprinted(glue / "pp_web_bg.wasm", "pp_web_bg", "wasm")
    pack = glue / "start.pack"
    pack.write_bytes(build_pack.build())
    start_pack = add_fingerprinted(pack, "start", "pack")
    effects = glue / "effects.pack"
    effects.write_bytes(build_audio.effects_pack())
    effects_pack = add_fingerprinted(effects, "effects", "pack")
    songs = {}
    for name, src in build_audio.songs().items():
        data = Path(src).read_bytes()
        stem = Path(name).stem
        songs[name] = f"songs/{stem}.{fingerprint(data)}.ogg"
        files[songs[name]] = data
    files["index.html"] = (PORT / "www" / "index.html").read_bytes()
    files["audio.js"] = (PORT / "www" / "audio.js").read_bytes()

    # The build code covers every file the page loads, by name and content,
    # and the service worker's own text (before the code is put into it).
    sw = (PORT / "www" / "sw.js").read_text(encoding="utf-8")
    listing = sorted((n, fingerprint(d)) for n, d in files.items())
    listing.append(("sw.js", fingerprint(sw.encode())))
    build = fingerprint(json.dumps(listing).encode())

    manifest = {
        "build": build,
        "app_js": app_js,
        "app_wasm": app_wasm,
        "pack": start_pack,
        "effects": effects_pack,
        "songs": songs,
        "fingerprinted": fingerprinted,
        "files": ["index.html", "audio.js", "files.json", *fingerprinted],
    }
    files["files.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    if "__BUILD__" not in sw:
        sys.exit("sw.js lost its __BUILD__ marker")
    files["sw.js"] = sw.replace("__BUILD__", build).encode()

    for name, data in files.items():
        (OUT / name).parent.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_bytes(data)
    shutil.rmtree(glue)

    print(f"\nbuild {build} in {OUT}")
    import gzip
    for name in (app_wasm, start_pack, effects_pack, *songs.values(), app_js, "index.html", "audio.js", "sw.js"):
        raw = len(files[name])
        packed = len(gzip.compress(files[name], 9))
        print(f"  {name:<28} {raw:>10,} bytes   gzip {packed:>10,}")


if __name__ == "__main__":
    main()
