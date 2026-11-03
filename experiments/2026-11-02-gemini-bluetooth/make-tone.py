#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A 30 s, 44.1 kHz stereo test file: 5 s left at 440 Hz, 5 s right at 660 Hz,
then 20 s of notes on both channels, -20 dBFS. Usage: make-tone.py OUTPUT.wav"""
import math
import struct
import sys
import wave

RATE = 44100
LEVEL = 0.1 * 32767


def tone(frequency, seconds, left, right):
    out = bytearray()
    for i in range(int(RATE * seconds)):
        fade = min(1.0, i / 441, (RATE * seconds - i) / 441)
        s = LEVEL * fade * math.sin(2 * math.pi * frequency * i / RATE)
        out += struct.pack("<hh", int(s * left), int(s * right))
    return out


data = tone(440, 5, 1, 0) + tone(660, 5, 0, 1)
for n in range(40):
    data += tone(262 * 2 ** ((0, 4, 7, 12)[n % 4] / 12), 0.5, 1, 1)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(bytes(data))
