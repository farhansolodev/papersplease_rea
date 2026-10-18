"""Builds the browser version into build/web/ (gitignored).

    python -I scripts/build_web.py            # full build
    python -I scripts/build_web.py --no-cargo # redo only the packaging
    python -I scripts/build_web.py --debug-names  # keep function names

Steps: cargo builds the WebAssembly (release); wasm-bindgen turns it into a
file plus the JavaScript glue the page needs; every built file gets its
content fingerprint in its name; the page and service worker are copied
from port/www; files.json lists everything. The build code (a short hash of
the file list and fingerprints) is baked into sw.js, so a new build makes
the browser install a new service worker.

Needs wasm-bindgen-cli in .cargo-home/bin (docs/milestone-0.md).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build_assets"))
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
    files["index.html"] = (PORT / "www" / "index.html").read_bytes()

    # The build code covers every file the page loads, by name and content.
    listing = sorted((n, fingerprint(d)) for n, d in files.items())
    build = fingerprint(json.dumps(listing).encode())

    manifest = {
        "build": build,
        "app_js": app_js,
        "app_wasm": app_wasm,
        "pack": start_pack,
        "fingerprinted": fingerprinted,
        "files": ["index.html", "files.json", *fingerprinted],
    }
    files["files.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    sw = (PORT / "www" / "sw.js").read_text(encoding="utf-8")
    if "__BUILD__" not in sw:
        sys.exit("sw.js lost its __BUILD__ marker")
    files["sw.js"] = sw.replace("__BUILD__", build).encode()

    for name, data in files.items():
        (OUT / name).write_bytes(data)
    shutil.rmtree(glue)

    print(f"\nbuild {build} in {OUT}")
    import gzip
    for name in (app_wasm, start_pack, app_js, "index.html", "sw.js"):
        raw = len(files[name])
        packed = len(gzip.compress(files[name], 9))
        print(f"  {name:<28} {raw:>10,} bytes   gzip {packed:>10,}")


if __name__ == "__main__":
    main()
