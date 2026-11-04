#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round trip through bt-voice: speech-band tones come back, the wrong bit order does
come back noisier, and invalid records stay quiet. Usage: test-bt-voice.py PATH_TO_BT_VOICE"""
import math
import struct
import subprocess
import sys

tool = sys.argv[1]
RATE = 8000


def run(args, data):
    return subprocess.run([tool] + args, input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)


def tone(frequency, level, seconds=2.0):
    n = int(RATE * seconds)
    return [level * 32767 * math.sin(2 * math.pi * frequency * i / RATE) for i in range(n)]


def pack(samples):
    return struct.pack("<%dh" % len(samples), *[int(s) for s in samples])


def unpack(data):
    return struct.unpack("<%dh" % (len(data) // 2), data)


def snr(reference, output):
    """dB, at the best delay and gain, skipping the settling time."""
    best = -99.0
    a = reference[2000:10000]
    power_a = sum(x * x for x in a)
    for delay in range(0, 64):
        b = output[2000 + delay:10000 + delay]
        if len(b) < len(a):
            break
        cross = sum(x * y for x, y in zip(a, b))
        power_b = sum(y * y for y in b)
        if power_b == 0:
            continue
        gain = cross / power_a
        noise = sum((y - gain * x) ** 2 for x, y in zip(a, b))
        best = max(best, 10 * math.log10(gain * gain * power_a / max(noise, 1e-9)))
    return best


for frequency, level, minimum in ((300, 0.1, 15), (440, 0.1, 15), (1000, 0.1, 15), (1000, 0.5, 10), (2000, 0.1, 8)):
    # 1 kHz at half scale needs a slope of 1600 per bit, beyond delta max: the spec's limit.
    samples = tone(frequency, level)
    coded = run(["encode"], pack(samples)).stdout
    assert len(coded) == len(samples)
    got = unpack(run(["decode", "--raw"], coded).stdout)
    value = snr(samples, got)
    print("%5d Hz %.2f: %.1f dB" % (frequency, level, value))
    assert value >= minimum, value

samples = tone(440, 0.1)
coded = run(["encode"], pack(samples)).stdout
# A swapped byte only shuffles eight bits within 125 us, so a low tone survives, noisier.
right = snr(samples, unpack(run(["decode", "--raw"], coded).stdout))
wrong = snr(samples, unpack(run(["decode", "--raw", "--msb"], coded).stdout))
print("right bit order %.1f dB, wrong %.1f dB" % (right, wrong))
assert wrong <= right - 8
coded = run(["encode", "--msb"], pack(samples)).stdout
assert snr(samples, unpack(run(["decode", "--raw", "--msb"], coded).stdout)) >= right - 1

# Capture records: a valid word decodes, an invalid record holds the signal down.
coded = run(["encode"], pack(samples)).stdout
records = b"".join(coded[i:i + 30] + b"\x01\x00" for i in range(0, len(coded) - 29, 30))
result = run(["decode"], records)
assert b"invalid=0" in result.stderr
assert snr(samples, unpack(result.stdout)) >= 15
silent = run(["decode"], (b"\xff" * 30 + b"\x00\x00") * 400)
assert b"valid=0 invalid=400" in silent.stderr
assert max(abs(x) for x in unpack(silent.stdout)[100:]) < 200
print("bt-voice: round trip, bit order and validity pass")
