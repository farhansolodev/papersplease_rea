r"""Does MusicBeat's tempo table fit a song? Compares where the table puts
the beats with where the recording's notes start.

Usage: python -I music_beat_check.py <reference dir> <audio dir>
(<audio dir> = extracted\audio, from scripts\unity\audio_extract.py).
Needs numpy (the system Python has it; the project's .venv does not).

Method: an onset strength curve (spectral flux: how much the spectrum
grows from one 5.8 ms step to the next, with the slow trend removed),
then the mean strength at a grid of beat times (the best of three
neighbouring steps). The table's grid is tried with a time shift of
-0.3..+0.3 s and a tempo scale of 0.90..1.10; steady-tempo grids of
90..130 beats a minute with any shift are the comparison. A table that
belongs to the song should score far above every steady grid, and best
at scale 1. This is a measurement of the recording, not game code.
"""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, sys.argv[1])
import aud  # noqa: E402

problems = []
N, HOP = 2048, 256


def onset_curve(path):
    w = wave.open(path)
    rate, n = w.getframerate(), w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, w.getnchannels()).astype(np.float64).mean(axis=1)
    frames = (len(x) - N) // HOP
    window = np.hanning(N)
    spec = np.log1p(np.abs(np.array([np.fft.rfft(x[i * HOP:i * HOP + N] * window)
                                     for i in range(frames)])) / 100.0)
    flux = np.concatenate([[0.0], np.maximum(0.0, np.diff(spec, axis=0)).sum(axis=1)])
    flux = np.maximum(flux - np.convolve(flux, np.ones(43) / 43, mode="same"), 0.0)
    return flux / flux.mean(), rate / HOP, n / rate, (N / 2) / rate


def first_sound(path, level=100):
    w = wave.open(path)
    x = np.abs(np.frombuffer(w.readframes(w.getframerate()), dtype="<i2").astype(int))
    return np.argmax(x > level) / w.getnchannels() / w.getframerate()


def table_beats():
    mb = aud.MusicBeat()
    return np.array([mb.get_time(float(b)) for b in range(192)])


beats = table_beats()
results = {}
for song in ("Theme", "Victory", "Death"):
    path = os.path.join(sys.argv[2], song + ".wav")
    flux, fps, dur, centre = onset_curve(path)

    def score(times):
        times = times[(times > 0.05) & (times < dur - 0.1)]
        idx = np.round((times - centre) * fps).astype(int)
        idx = idx[(idx >= 1) & (idx < len(flux) - 1)]
        return float(np.mean([flux[i - 1:i + 2].max() for i in idx]))

    table = max((score(beats * s + d), round(s, 3), round(d, 2))
                for s in np.arange(0.90, 1.1001, 0.005) for d in np.arange(-0.3, 0.3001, 0.01))
    steady = max((max(score(np.arange(0.0, dur, 60.0 / bpm) + d) for d in np.arange(0.0, 60.0 / bpm, 0.01)), bpm)
                 for bpm in np.arange(90.0, 130.01, 2.5))
    results[song] = (table, steady)
    print("%-8s %6.2f s, first sound at %.3f s | table: best %.2f at scale %.3f, shift %+.2f s | "
          "best steady grid: %.2f at %.1f bpm" % (song, dur, first_sound(path), table[0], table[1], table[2],
                                                 steady[0], steady[1]))

theme_table, theme_steady = results["Theme"]
if not (theme_table[1] == 1.0 and theme_table[0] > 2 * theme_steady[0]):
    problems.append("the table does not stand out on Theme")
for song in ("Victory", "Death"):
    table, steady = results[song]
    if table[0] > 2 * steady[0]:
        problems.append("the table also fits " + song)

print("\nproblems:", "none" if not problems else "")
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
