#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize a sensors-imu.sh CSV: one line per second in the device frame.

Device frame, the screen's: X toward its right edge, Y toward its top, Z out of
it toward the user.
Accel in m/s^2, gyro in deg/s. The matrix applied is the one the file records.
"""
import math
import sys

header = {}
rows = []
for line in open(sys.argv[1]):
    line = line.strip()
    if line.startswith("#"):
        parts = line[1:].split(None, 1)
        header[parts[0]] = parts[1] if len(parts) > 1 else ""
    elif line and not line.startswith("t,"):
        rows.append([float(v) for v in line.split(",")])

accel_scale = float(header["accel_scale"])
gyro_scale = float(header["anglvel_scale"])


def matrix(text):
    return [[float(v) for v in row.split(",")] for row in text.split(";")]


ma = mg = matrix(header["matrix"])


def apply(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


samples = []
for r in rows:
    a = [v * accel_scale for v in apply(ma, r[1:4])]
    g = [math.degrees(v * gyro_scale) for v in apply(mg, r[4:7])]
    samples.append((r[0], a, g))

print(f"samples {len(samples)} over {samples[-1][0] - samples[0][0]:.1f} s, "
      f"accel raw scale {accel_scale}, gyro raw scale {gyro_scale}")
print("  sec    ax     ay     az    |a|     gx     gy     gz")
t0 = samples[0][0]
buckets = {}
for t, a, g in samples:
    buckets.setdefault(int(t - t0), []).append((a, g))
for sec in sorted(buckets):
    b = buckets[sec]
    a = [sum(x[0][i] for x in b) / len(b) for i in range(3)]
    g = [sum(x[1][i] for x in b) / len(b) for i in range(3)]
    print(f"{sec:5d} {a[0]:6.2f} {a[1]:6.2f} {a[2]:6.2f} {math.hypot(*a):6.2f} "
          f"{g[0]:6.1f} {g[1]:6.1f} {g[2]:6.1f}")

n = len(samples)
for name, idx in (("accel", 1), ("gyro", 2)):
    mean = [sum(s[idx][i] for s in samples) / n for i in range(3)]
    sd = [math.sqrt(sum((s[idx][i] - mean[i]) ** 2 for s in samples) / n) for i in range(3)]
    print(name, "mean", [round(v, 3) for v in mean], "sd", [round(v, 3) for v in sd])
