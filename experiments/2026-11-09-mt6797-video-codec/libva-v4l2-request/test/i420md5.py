# SPDX-License-Identifier: GPL-3.0-or-later
# Compare I420 frames on stdin with an ffmpeg framemd5 file.
import hashlib, sys
# usage: i420md5.py W H FRAMEMD5 < frames.i420
w, h, ref = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
fs = w * h + 2 * (w // 2) * (h // 2)
refs = [l.split(',')[-1].strip() for l in open(ref) if l[0].isdigit()]
data = sys.stdin.buffer.read()
n = len(data) // fs
got = [hashlib.md5(data[i * fs:(i + 1) * fs]).hexdigest() for i in range(n)]
ok = sum(1 for a, b in zip(got, refs) if a == b)
print(f"{n} frames, {ok}/{len(refs)} match the framemd5")
sys.exit(0 if ok == len(refs) == n else 1)
