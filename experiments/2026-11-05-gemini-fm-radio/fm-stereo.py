#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""F6: is an FM recording stereo?

Reads 16-bit stereo WAV files and prints, for each: the RMS of the left and
right channels and of their mean (M) and half-difference (S), S relative to M
in dB, and the share of samples where left and right are equal. Forced mono
should give S = 0 and every sample equal; a stereo broadcast gives a clearly
nonzero S. Prints levels only, nothing of the content.
"""
import math
import sys
import wave
from array import array


def analyse(path):
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 2 or w.getsampwidth() != 2:
            return f"{path}: not 16-bit stereo"
        rate = w.getframerate()
        data = array("h", w.readframes(w.getnframes()))
    if sys.byteorder != "little":
        data.byteswap()
    left, right = data[0::2], data[1::2]
    n = len(left)
    if not n:
        return f"{path}: empty"
    sl = sr = sm = ss = 0.0
    equal = 0
    for a, b in zip(left, right):
        sl += a * a
        sr += b * b
        m = (a + b) / 2
        s = (a - b) / 2
        sm += m * m
        ss += s * s
        equal += a == b
    rms = [math.sqrt(x / n) for x in (sl, sr, sm, ss)]
    full = 32768.0
    db = [20 * math.log10(x / full) if x else float("-inf") for x in rms]
    side = 20 * math.log10(rms[3] / rms[2]) if rms[3] and rms[2] else float("-inf")
    return (f"{path}: {n / rate:.1f} s at {rate} Hz; RMS dBFS L {db[0]:.1f} R {db[1]:.1f} "
            f"M {db[2]:.1f} S {db[3]:.1f}; S/M {side:.1f} dB; "
            f"L=R in {100 * equal / n:.2f}% of samples")


for arg in sys.argv[1:]:
    print(analyse(arg))
