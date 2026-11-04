#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""mSBC frames for the Gemini's Bluetooth voice path, using ffmpeg's SBC codec.

  bt-msbc.py encode IN.wav OUT.bin    4 s of silence frames, then 6 s of IN, 1333 frames
  bt-msbc.py decode IN.cvsd OUT.wav   the driver's capture records to 16 kHz mono

A 60-byte link frame is the H2 header (01, then 08 38 c8 f8 in turn), a 57-byte mSBC
frame and one pad byte. Capture arrives as 32-byte records, 30 bytes and a validity
word, so two records make a frame, from either record. A frame that is invalid or lost
decodes as silence, to keep the timing. Counts go to stderr.
"""

import os
import subprocess
import sys

FRAMES = 1333
SILENCE_FRAMES = 533
H2 = (0x08, 0x38, 0xc8, 0xf8)
# The silence frame in the kernel's mtk-btcvsd.c.
SILENCE = bytes.fromhex(
    "ad0000c500000000776db6dddb6db776db6dddb6db776db6dddb6db776db6"
    "dddb6db776db6dddb6db776db6dddb6db776db6dddb6db776db6c")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def encode(source, out):
    ffmpeg("-i", source, "-t", "6", "-ar", "16000", "-ac", "1", "-c:a", "sbc", "-msbc", "1",
           "-f", "sbc", out + ".sbc")
    with open(out + ".sbc", "rb") as f:
        coded = f.read()
    os.remove(out + ".sbc")
    frames = [SILENCE] * SILENCE_FRAMES
    frames += [coded[i:i + 57] for i in range(0, len(coded) - 56, 57)]
    frames = (frames + [SILENCE] * FRAMES)[:FRAMES]
    with open(out, "wb") as f:
        for i, frame in enumerate(frames):
            f.write(bytes((0x01, H2[i % 4])) + frame + b"\0")
    print(f"frames={FRAMES} audio={len(coded) // 57}", file=sys.stderr)


def decode(capture, out):
    with open(capture, "rb") as f:
        data = f.read()
    records = [data[i:i + 32] for i in range(0, len(data) - 31, 32)]
    valid = [r[30:32] != b"\0\0" for r in records]
    payload = [r[:30] for r in records]

    def score(start):
        return sum(payload[i][:1] == b"\x01" and payload[i][2:3] == b"\xad"
                   for i in range(start, len(records) - 1, 2))

    start = max((0, 1), key=score)
    good = bad = 0
    with open(out + ".sbc", "wb") as f:
        for i in range(start, len(records) - 1, 2):
            frame = payload[i] + payload[i + 1]
            ok = valid[i] and valid[i + 1] and frame[0] == 1 and frame[1] in H2 and frame[2] == 0xad
            good += ok
            bad += not ok
            f.write(frame[2:59] if ok else SILENCE)
    print(f"records={len(records)} invalid={valid.count(False)} start={start} "
          f"frames good={good} bad={bad}", file=sys.stderr)
    ffmpeg("-f", "sbc", "-c:a", "sbc", "-i", out + ".sbc", "-ar", "16000", out)
    os.remove(out + ".sbc")


if __name__ == "__main__":
    {"encode": encode, "decode": decode}[sys.argv[1]](sys.argv[2], sys.argv[3])
