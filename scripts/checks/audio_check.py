"""Checks of the extracted sounds (docs/audio.md) against the stored
clips, the data files and the Unity mixer.

Usage: python -I audio_check.py <reference dir> <audio dir> <sharedassets0.resource>
                                <data dir> <unity dump dir>
(<audio dir> = extracted\\audio, written by scripts/unity/audio_extract.py;
<unity dump dir> = extracted\\unity, written by scene_dump.py; pure Python)

1. The index: 111 names, one file each, WAV headers, lengths against
   Unity's clip settings and the FMOD bank header.
2. An independent IMA ADPCM decoder, run on the stored bytes, gives the
   same samples as FMOD for every effect.
3. Sounds.xml: every recording it names exists; which stored ones are
   never named; the songs against Ends.xml and the code's song names.
4. No file is silent.
5. The mixer: groups, the snapshot, the exposed volume parameters; and
   host.category_attenuation_db and host.AudioHost.
"""
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, sys.argv[1])
import host as H  # noqa: E402

audio, resource, data, dump = sys.argv[2:6]
problems = []


def expect(name, got, want):
    ok = got == want
    print("   %-62s %s%s" % (name, got, "" if ok else "   (wanted %s)" % (want,)))
    if not ok:
        problems.append(name)


rows = json.load(open(os.path.join(audio, "audio_index.json"), encoding="utf-8"))

# ---- 1. the index ------------------------------------------------------------
print("1. The index")
paths = [r["path"] for r in rows]
expect("entries", len(rows), 111)
expect("repeated names", len(paths) - len(set(paths)), 0)
expect("names ending .wav / .ogg / other",
       (sum(p.endswith(".wav") for p in paths), sum(p.endswith(".ogg") for p in paths),
        sum(not p.endswith((".wav", ".ogg")) for p in paths)), (108, 3, 0))
expect(".wav names stored as IMA ADPCM",
       all(r["fsb_codec"] == "IMAADPCM" and r["unity_format"] == "ADPCM"
           for r in rows if r["path"].endswith(".wav")), True)
expect(".ogg names stored as Vorbis",
       all(r["fsb_codec"] == "VORBIS" and r["unity_format"] == "Vorbis"
           for r in rows if r["path"].endswith(".ogg")), True)
expect("load type of every clip", sorted({r["unity_load"] for r in rows}), ["DecompressOnLoad"])
expect("clips whose name is not the file name's stem",
       [r["path"] for r in rows if os.path.splitext(r["path"])[0] != r["clip"]], [])
pieces = sorted((r["stored_offset"], r["stored_bytes"]) for r in rows)
expect("stored pieces cover sharedassets0.resource end to end, once",
       all(a[0] + a[1] == b[0] for a, b in zip(pieces, pieces[1:]))
       and pieces[0][0] == 0 and pieces[-1][0] + pieces[-1][1] == os.path.getsize(resource)
       and all(r["stored_file"] == "sharedassets0.resource" for r in rows), True)

bad_header, bad_len = [], []
pcm = {}
for r in rows:
    raw = open(os.path.join(audio, r["file"]), "rb").read()
    riff, size, wave, fmt, fsize, tag, ch, rate, brate, align, bits, dtag, dsize = \
        struct.unpack_from("<4sI4s4sIHHIIHH4sI", raw, 0)
    if (riff, wave, fmt, fsize, tag, bits, dtag) != (b"RIFF", b"WAVE", b"fmt ", 16, 1, 16, b"data") \
            or size != len(raw) - 8 or dsize != len(raw) - 44 or (ch, rate) != (r["channels"], r["rate"]) \
            or brate != rate * ch * 2 or align != ch * 2:
        bad_header.append(r["file"])
    n = dsize // (2 * ch)
    # Unity's m_Length is a float of samples / rate.
    if n != r["samples"] or n != r["fsb_samples"] or ch != r["unity_channels"] or ch != r["fsb_channels"] \
            or rate != r["unity_rate"] or abs(n / rate - r["unity_length"]) > 1.0 / rate:
        bad_len.append(r["file"])
    pcm[r["path"]] = raw[44:]
expect("WAV files with a wrong header", bad_header, [])
expect("files whose length, channels or rate disagree", bad_len, [])
print("   rates and channels: %s" % sorted({(r["rate"], r["channels"]) for r in rows}))

# ---- 2. an independent IMA ADPCM decode ------------------------------------
print("2. IMA ADPCM, decoded here, against FMOD's output")
STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55,
         60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337,
         371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552,
         1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
         7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385,
         24623, 27086, 29794, 32767]
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8] * 2


def ima_decode(block_data, channels, samples):
    """The standard IMA ADPCM step, in FMOD's FSB5 block layout: per
    channel a 36-byte block, 4 header bytes (sample, step index, unused)
    and 32 bytes of 4-bit codes, low half first. In a stereo block the two
    headers come first, then the codes in 4-byte turns. The header sample
    is the block's first sample; 63 codes follow, and the 64th code of a
    block is never used. Returns the samples interleaved."""
    out = [[] for _ in range(channels)]
    block = 36 * channels
    pos = 0
    while len(out[0]) < samples:
        b = block_data[pos:pos + block]
        pos += block
        for c in range(channels):
            pred, idx = struct.unpack_from("<hB", b, 4 * c)
            codes = []
            for g in range(8):
                start = 4 * channels + 4 * (g * channels + c)
                for byte in b[start:start + 4]:
                    codes += [byte & 15, byte >> 4]
            o = out[c]
            o.append(pred)
            for code in codes[:63]:
                s = STEPS[idx]
                d = s >> 3
                if code & 1:
                    d += s >> 2
                if code & 2:
                    d += s >> 1
                if code & 4:
                    d += s
                pred = max(-32768, min(32767, pred - d if code & 8 else pred + d))
                idx = max(0, min(88, idx + INDEX[code]))
                o.append(pred)
    return [out[c][i] for i in range(samples) for c in range(channels)]


stored = open(resource, "rb").read()
differ = []
checked = 0
for r in rows:
    if r["fsb_codec"] != "IMAADPCM":
        continue
    start = r["stored_offset"] + r["fsb_data_start"]
    mine = ima_decode(stored[start:start + r["fsb_data_bytes"]], r["channels"], r["samples"])
    theirs = list(struct.unpack("<%dh" % (len(pcm[r["path"]]) // 2), pcm[r["path"]]))
    checked += 1
    if mine != theirs:
        differ.append(r["path"])
expect("effects decoded", checked, 108)
expect("effects whose samples differ from FMOD's", differ, [])

# ---- 3. the data files ---------------------------------------------------------
print("3. Sounds.xml, Ends.xml and the songs")
sounds = ET.parse(os.path.join(data, "Sounds.xml")).getroot().findall("sound")
named = []
for s in sounds:
    named += s.get("file").split(" ") if s.get("file") is not None else [s.get("id") + ".wav"]
named_set = set(named)
expect("recordings named by Sounds.xml (distinct)", len(named_set), 108)
expect("named recordings with no stored clip", sorted(named_set - set(paths)), [])
expect("stored .wav clips that Sounds.xml never names",
       sorted(p for p in paths if p.endswith(".wav") and p not in named_set), [])
fourth = [s.get("file").split(" ")[3] for s in sounds
          if s.get("file") is not None and len(s.get("file").split(" ")) > 3]
expect("4th recordings (stored, never played)", fourth, ["text-reveal3.wav", "chain-jingle3.wav"])
# Ends.xml has comments of dashes ("<!------>") that strict XML rejects,
# so its music attributes are found by pattern.
ends = open(os.path.join(data, "Ends.xml"), encoding="utf-8").read()
end_music = sorted(set(re.findall(r'<end [^>]* music="([^"]*)"', ends)))
print("   music named by Ends.xml: %s" % end_music)
songs = sorted(os.path.splitext(p)[0] for p in paths if p.endswith(".ogg"))
expect("songs stored", songs, ["Death", "Theme", "Victory"])
# "Theme" and "Victory" are set as songId by screen constructors (docs/audio.md).
expect("songs asked for (Ends.xml music + Theme + Victory) all stored",
       sorted(set(end_music) | {"Theme", "Victory"}) == songs, True)

# ---- 4. not silent -------------------------------------------------------------
print("4. Levels")
peaks = {}
for p, b in pcm.items():
    v = struct.unpack("<%dh" % (len(b) // 2), b)
    peaks[p] = max(max(v), -min(v))
expect("silent files", [p for p, k in peaks.items() if k == 0], [])
q = sorted(peaks.items(), key=lambda kv: kv[1])
print("   quietest peaks: %s; files reaching full scale: %d"
      % (", ".join("%s %d" % kv for kv in q[:3]), sum(1 for k in peaks.values() if k >= 32767)))

# ---- 5. the mixer and the host ------------------------------------------------
print("5. The mixer and the host's rules")
mixer = json.load(open(os.path.join(dump, "objects", "sharedassets0.assets_120_AudioMixerController.json"),
                       encoding="utf-8"))
mc = mixer["m_MixerConstant"]
group_names = bytes(mc["groupNameBuffer"]).split(b"\0")[:3]
expect("mixer groups", [g.decode() for g in group_names], ["Master", "Effects", "Music"])
expect("group parents", [g["parentConstantIndex"] for g in mc["groups"]], [-1, 0, 0])
expect("effects on any group", mc["effects"], [])
expect("snapshot values (volume dB, pitch per group)", mc["snapshots"][0]["values"],
       [0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
expect("exposed parameters are CRC32 of EffectsAtten, MusicAtten",
       mc["exposedParameterNames"], [zlib.crc32(b"EffectsAtten"), zlib.crc32(b"MusicAtten")])
expect("... and set the volume of Effects (2) and Music (4)", mc["exposedParameterIndices"], [2, 4])
expect("attenuation for volume 1, 0.5, 0, 2 (dB, rounded)",
       [round(H.category_attenuation_db(v), 4) for v in (1, 0.5, 0, 2)], [0.0, -6.0206, -80.0, 0.0])
host = H.AudioHost(paths)
started = [host.start(i, "effects", "stamp-down.wav", False, 1.0) for i in range(33)]
expect("33 sounds at once: how many start", sum(started), 32)
expect("an unknown name plays nothing", host.start(99, "effects", "nothing.wav", False, 1.0), False)
host.update({0, 1})
expect("two finished sounds free two sources", host.start(100, "music", "Theme.ogg", True, 1.0)
       and host.start(101, "effects", "button-up.wav", False, 1.0)
       and not host.start(102, "effects", "button-up.wav", False, 1.0), True)
host.update({100})
expect("a looping sound is not freed when its end is reported", 100 in host.playing, True)

print()
print("problems: %s" % (", ".join(problems) if problems else "none"))
