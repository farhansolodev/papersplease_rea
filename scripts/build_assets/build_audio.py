"""Builds the sound files of the browser build (milestone 2, docs/milestone-2.md).

    python -I scripts/build_assets/build_audio.py      # writes build/assets/

Two outputs, both game assets, so both stay in build/ (gitignored, CLAUDE.md
rule 1):

- effects.pack: the 108 effects as the game stores them (IMA ADPCM, FMOD's
  block layout, docs/audio.md), cut out of sharedassets0.resource with no
  change. The port decodes them itself (port/core/src/adpcm.rs). Same pack
  format as the start pack (build_pack.py); one file per effect, named by
  the game's own name ("effects/stamp-down.wav"), holding

      channels u16, rate u32, samples u32 (per channel), the ADPCM blocks

- songs/<Song>.ogg: the three songs re-encoded from extracted/audio/<Song>.wav
  to Ogg Vorbis by ffmpeg (already on this machine; no download). Lossy: the
  game's own Vorbis data cannot be put into an .ogg file without a tool
  that is not installed (docs/DESIGN.md, the songs' row). Encoded again
  only when the WAV or the settings change (a note next to each file).

Inputs (all gitignored, made by earlier steps): game/PapersPlease_Data/
sharedassets0.resource (the copy of the game in this project) and
extracted/audio/ (scripts/unity/audio_extract.py: the WAV files and
audio_index.json).
"""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESOURCE = os.path.join(ROOT, "game", "PapersPlease_Data", "sharedassets0.resource")
AUDIO = os.path.join(ROOT, "extracted", "audio")
OUT = os.path.join(ROOT, "build", "assets")
# ffmpeg's Vorbis quality scale runs -1 to 10; 6 is about 190 kbit/s for
# stereo 44.1 kHz. The game stores its songs at about 160 kbit/s.
SONG_ARGS = ["-c:a", "libvorbis", "-q:a", "6", "-map_metadata", "-1"]


def index():
    with open(os.path.join(AUDIO, "audio_index.json"), encoding="utf-8") as f:
        return json.load(f)


def effects_pack():
    """The effects pack's bytes."""
    stored = open(RESOURCE, "rb").read()
    entries = []
    for r in index():
        if r["fsb_codec"] != "IMAADPCM":
            continue
        start = r["stored_offset"] + r["fsb_data_start"]
        blocks = stored[start:start + r["fsb_data_bytes"]]
        # Whole blocks of 36 bytes per channel, enough for every sample.
        need = -(-r["samples"] // 64) * 36 * r["channels"]
        if len(blocks) < need:
            sys.exit(f"{r['path']}: {len(blocks)} bytes stored, {need} needed")
        head = struct.pack("<HII", r["channels"], r["rate"], r["samples"])
        entries.append(("effects/" + r["path"], head + blocks))
    if len(entries) != 108:
        sys.exit(f"expected 108 effects, found {len(entries)}")
    head = b"PPK1" + struct.pack("<I", len(entries))
    table, data, offset = b"", b"", 0
    for name, blob in entries:
        raw = name.encode("utf-8")
        table += struct.pack("<H", len(raw)) + raw + struct.pack("<II", offset, len(blob))
        data += blob
        offset += len(blob)
    return head + table + data


def song_names():
    return sorted(os.path.splitext(r["path"])[0] for r in index() if r["fsb_codec"] == "VORBIS")


def songs():
    """Encodes the songs where needed; returns {"Theme.ogg": path, ...}."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg is not on the PATH (docs/milestone-2.md)")
    folder = os.path.join(OUT, "songs")
    os.makedirs(folder, exist_ok=True)
    out = {}
    for song in song_names():
        wav = os.path.join(AUDIO, song + ".wav")
        ogg = os.path.join(folder, song + ".ogg")
        note = ogg + ".source"
        source = hashlib.sha256(open(wav, "rb").read()).hexdigest() + " " + " ".join(SONG_ARGS)
        if not (os.path.exists(ogg) and os.path.exists(note) and open(note).read() == source):
            print(f"+ ffmpeg {song}.wav -> {song}.ogg", flush=True)
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", wav,
                            *SONG_ARGS, ogg], check=True)
            with open(note, "w") as f:
                f.write(source)
        out[song + ".ogg"] = ogg
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    pack = effects_pack()
    with open(os.path.join(OUT, "effects.pack"), "wb") as f:
        f.write(pack)
    print(f"effects.pack: {len(pack):,} bytes")
    for name, path in songs().items():
        print(f"songs/{name}: {os.path.getsize(path):,} bytes")


if __name__ == "__main__":
    main()
