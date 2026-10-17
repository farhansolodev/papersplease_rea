"""Extract the game's sounds and songs (docs/audio.md).

Usage: .venv\\Scripts\\python -I audio_extract.py <PapersPlease_Data dir> <out dir>
(<PapersPlease_Data dir> = game\\PapersPlease_Data, the project's copy;
<out dir> = extracted\\audio. Needs UnityPy and the FMOD library that
UnityPy's fmod_toolkit brings along, both in the project's .venv.)

The scene's HostUnity object holds two lists of the same length: the file
names the game asks for (audioPaths, "stamp-down.wav", "Theme.ogg") and
the AudioClip each name stands for (audioClips). Each clip's bytes sit in
sharedassets0.resource as an FMOD sound bank (FSB5) with one sound in it:
IMA ADPCM for the effects, Vorbis for the songs. FMOD (the sound engine
Unity is built on) decodes each one to 16-bit PCM, written as a WAV file.

Writes:
  <out>/<name>.wav       one per audioPaths entry, named by that entry
                         with its extension made .wav (the songs' ".ogg"
                         becomes ".wav": the content is decoded PCM)
  <out>/audio_index.json one row per entry, in HostUnity's order: the
                         name the game asks for, the file written, the
                         clip, its stored format and what FMOD gave
and prints a summary.
"""
import ctypes
import json
import os
import struct
import sys

import UnityPy
from UnityPy.helpers.ResourceReader import get_resource_data
from fmod_toolkit.fmod import get_pyfmodex_system_instance, pyfmodex

data_dir, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

FSB5_CODECS = {1: "PCM8", 2: "PCM16", 7: "IMAADPCM", 11: "MPEG", 15: "VORBIS"}
UNITY_FORMATS = {0: "PCM", 1: "Vorbis", 2: "ADPCM", 3: "MP3"}  # AudioCompressionFormat
UNITY_LOAD = {0: "DecompressOnLoad", 1: "CompressedInMemory", 2: "Streaming"}

FILES = ("level0", "globalgamemanagers.assets", "sharedassets0.assets")
envs = {n: UnityPy.load(os.path.join(data_dir, n)) for n in FILES}
sf = {n: next(iter(e.files.values())) for n, e in envs.items()}
shared = sf["sharedassets0.assets"]


def ext_name(file_id):
    """The file a PPtr of level0 with this file id points into."""
    return "level0" if file_id == 0 else os.path.basename(sf["level0"].externals[file_id - 1].path)


# ---- HostUnity's two lists -------------------------------------------------
# Field order from dumps/il2cppdumper/dump.cs (the same decoding as
# scene_dump.py): six object references, audioPaths, audioClips, two more.
host = None
for o in sf["level0"].objects.values():
    if o.type.name != "MonoBehaviour":
        continue
    raw = o.get_raw_data()
    sfid, spid = struct.unpack_from("<iq", raw, 16)
    script = ext_name(sfid)
    if sf[script].objects[spid].read().m_ClassName == "HostUnity":
        host = raw
assert host is not None, "no HostUnity object in level0"

pos = 32 + ((struct.unpack_from("<i", host, 28)[0] + 3) & ~3)  # past m_Name
pos += 6 * 12                                                    # six PPtrs
n = struct.unpack_from("<i", host, pos)[0]
pos += 4
paths = []
for _ in range(n):
    ln = struct.unpack_from("<i", host, pos)[0]
    paths.append(host[pos + 4:pos + 4 + ln].decode("utf-8"))
    pos += 4 + ((ln + 3) & ~3)
m = struct.unpack_from("<i", host, pos)[0]
pos += 4
clips = []
for i in range(m):
    fid, pid = struct.unpack_from("<iq", host, pos + 12 * i)
    clips.append((ext_name(fid), pid))
pos += 12 * m
assert pos + 2 * 12 == len(host), "HostUnity: unexpected size"
assert n == m, "audioPaths %d, audioClips %d" % (n, m)
assert len(set(paths)) == n, "a repeated audio path"

# ---- decode every clip ---------------------------------------------------
system, lock = get_pyfmodex_system_instance(2, pyfmodex.flags.INIT_FLAGS.NORMAL)
PCM16 = pyfmodex.enums.SOUND_FORMAT.PCM16
rows = []
for path, (cfile, cpid) in zip(paths, clips):
    assert cfile == "sharedassets0.assets", (path, cfile)
    o = shared.objects[cpid]
    t = o.read_typetree()
    r = t["m_Resource"]
    data = get_resource_data(r["m_Source"], o.assets_file, r["m_Offset"], r["m_Size"])

    # The bank's header (FSB5 version 1): one sound, its codec, and the
    # sound's packed header word (channels, rate index, sample count).
    magic, ver, nsub, shdr, names, dsize, codec = struct.unpack_from("<4sIIIIII", data, 0)
    assert magic == b"FSB5" and ver == 1 and nsub == 1, (path, magic, ver, nsub)
    word = struct.unpack_from("<Q", data, 0x3C)[0]
    fsb_channels = ((word >> 5) & 1) + 1
    fsb_samples = word >> 34

    snd = system.create_sound(
        bytes(data), pyfmodex.flags.MODE.OPENMEMORY,
        exinfo=pyfmodex.structure_declarations.CREATESOUNDEXINFO(
            length=len(data), numchannels=t["m_Channels"], defaultfrequency=t["m_Frequency"]))
    assert snd.num_subsounds == 1, path
    sub = snd.get_subsound(0)
    fmt = sub.format
    rate = int(sub.default_frequency)
    samples = sub.get_length(pyfmodex.enums.TIMEUNIT.PCM)
    nbytes = sub.get_length(pyfmodex.enums.TIMEUNIT.PCMBYTES)
    assert fmt.format == PCM16 and fmt.bits == 16, (path, fmt.format)
    assert nbytes == samples * fmt.channels * 2, path
    pcm = bytearray()
    locked = sub.lock(0, nbytes)
    for ptr, size in locked:
        if ptr:
            pcm += ctypes.string_at(ptr, size.value)
    sub.unlock(*locked)
    sub.release()
    snd.release()
    assert len(pcm) == nbytes, (path, len(pcm), nbytes)

    stem = os.path.splitext(path)[0]
    fname = stem + ".wav"
    with open(os.path.join(out, fname), "wb") as fh:
        fh.write(b"RIFF" + struct.pack("<I", 36 + nbytes) + b"WAVE")
        fh.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, fmt.channels, rate,
                                        rate * fmt.channels * 2, fmt.channels * 2, 16))
        fh.write(b"data" + struct.pack("<I", nbytes))
        fh.write(pcm)

    rows.append({
        "path": path, "file": fname, "clip": t["m_Name"], "clip_path_id": cpid,
        "unity_format": UNITY_FORMATS.get(t["m_CompressionFormat"], t["m_CompressionFormat"]),
        "unity_load": UNITY_LOAD.get(t["m_LoadType"], t["m_LoadType"]),
        "unity_channels": t["m_Channels"], "unity_rate": t["m_Frequency"],
        "unity_length": t["m_Length"], "unity_preload": t["m_PreloadAudioData"],
        "stored_file": r["m_Source"], "stored_offset": r["m_Offset"], "stored_bytes": r["m_Size"],
        "fsb_data_start": 0x3C + shdr + names, "fsb_data_bytes": dsize, "fsb_codec": FSB5_CODECS.get(codec, codec),
        "fsb_channels": fsb_channels, "fsb_samples": fsb_samples,
        "channels": fmt.channels, "rate": rate, "samples": samples,
    })

with open(os.path.join(out, "audio_index.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)

# ---- summary --------------------------------------------------------------
kinds = {}
for row in rows:
    k = (row["fsb_codec"], row["channels"], row["rate"])
    kinds[k] = kinds.get(k, 0) + 1
print("%d entries in HostUnity's lists, %d files written to %s" % (len(rows), len(rows), out))
for (codec, ch, rate), c in sorted(kinds.items()):
    print("   %-9s %d channel(s) %5d Hz: %d" % (codec, ch, rate, c))
print("stored %d bytes; written %d bytes of PCM"
      % (sum(r["stored_bytes"] for r in rows), sum(r["samples"] * r["channels"] * 2 for r in rows)))
print("longest: " + ", ".join("%s %.1f s" % (r["path"], r["samples"] / r["rate"])
                             for r in sorted(rows, key=lambda r: -r["samples"])[:4]))
print("names that differ from their clip's name: %s"
      % ([(r["path"], r["clip"]) for r in rows if os.path.splitext(r["path"])[0] != r["clip"]] or "none"))
