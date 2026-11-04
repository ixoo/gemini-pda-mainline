#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A 30 s, 44.1 kHz stereo music-like file to compare codecs: plucked chords panned
across the field, bass, kick and bright hi-hats, whose noise bursts lossy coding finds
hard. The same seed gives the same file. Usage: make-music.py OUTPUT.wav"""
import math
import random
import struct
import sys
import wave

RATE = 44100
SECONDS = 30
BEAT = RATE // 2
CHORDS = ((0, 4, 7, 11), (9, 12, 16, 19), (5, 9, 12, 16), (7, 11, 14, 17))
left = [0.0] * (RATE * SECONDS)
right = [0.0] * (RATE * SECONDS)
random.seed(6797)


def add(start, samples, pan):
    for i, s in enumerate(samples, start):
        if i >= len(left):
            break
        left[i] += s * math.cos(pan * math.pi / 2)
        right[i] += s * math.sin(pan * math.pi / 2)


def pluck(frequency, seconds, level):
    return [level * math.exp(-4 * i / (RATE * seconds))
            * sum(math.sin(2 * math.pi * frequency * h * i / RATE) / h ** 1.5 for h in range(1, 8))
            for i in range(int(RATE * seconds))]


def hat(level):
    samples, last = [], 0.0
    for i in range(RATE // 12):
        noise = random.uniform(-1, 1)
        samples.append(level * (noise - last) * math.exp(-40 * i / RATE))
        last = noise
    return samples


kick = [0.5 * math.exp(-18 * i / RATE) * math.sin(2 * math.pi * (50 + 80 * math.exp(-40 * i / RATE)) * i / RATE)
        for i in range(RATE // 4)]
for beat in range(SECONDS * 2):
    chord = CHORDS[beat // 8 % 4]
    root = 220 * 2 ** (chord[0] / 12)
    start = beat * BEAT
    note = 220 * 2 ** (chord[beat % 4] / 12)
    add(start, pluck(note, 1.2, 0.12), (beat % 8) / 7)
    add(start, pluck(note * 2, 0.8, 0.05), 1 - (beat % 8) / 7)
    if beat % 2 == 0:
        add(start, kick, 0.5)
        add(start, pluck(root / 4, 1.0, 0.2), 0.5)
    add(start, hat(0.12), 0.3)
    add(start + BEAT // 2, hat(0.08), 0.7)

peak = max(max(map(abs, left)), max(map(abs, right)))
scale = 0.5 * 32767 / peak
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(b"".join(struct.pack("<hh", int(a * scale), int(b * scale)) for a, b in zip(left, right)))
