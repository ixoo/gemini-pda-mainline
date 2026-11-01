#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Boot the GNSS DSP from the device's own libmnl.so and record what it sends.

Usage: gnss-minihost.py DEVICE PARAMS LIBMNL OUTPUT SECONDS
No network, no storage writes outside OUTPUT. Not a GNSS stack: position is computed offline.
PARAMS is a private JSON file with the image location and hash and the boot header.
"""

import errno
import fcntl
import hashlib
import json
import os
import queue
import signal
import sys
import threading
import time

PREAMBLE = b"\xaa\xf0"
TRAILER = b"\xaa\x0f"
GPS_EPOCH = 315964800
LEAP = 18
EXIT_BOOT, EXIT_SILENT = 4, 5


def stuff(data):
    return data.replace(b"\xde", b"\xde\xe0").replace(b"\xaa", b"\xde\xdf")


def unstuff(data):
    return data.replace(b"\xde\xdf", b"\xaa").replace(b"\xde\xe0", b"\xde")


def frame(ident, payload, seq=0):
    head = ((len(payload) + 4) | (seq << 12)).to_bytes(2, "little") + ident.to_bytes(2, "little")
    check = (sum(head) + sum(payload)) & 0xffff
    return PREAMBLE + stuff(head + payload + check.to_bytes(2, "little")) + TRAILER


class Link:
    """The vendor device has no poll and read always blocks, so one thread reads, as stock does."""

    def __init__(self, path, log):
        self.fd = os.open(path, os.O_RDWR)
        self.log = log
        self.frames = queue.Queue()
        self.lock = threading.Lock()
        self.last = b""
        threading.Thread(target=self.reader, daemon=True).start()

    def record(self, kind, data):
        with self.lock:
            self.log.write("%.3f %s %s\n" % (time.time(), kind, data.hex()))
            self.log.flush()

    def reader(self):
        pending = b""
        while True:
            data = os.read(self.fd, 4096)
            self.record("R", data)
            pending += data
            while True:
                start = pending.find(PREAMBLE)
                end = pending.find(TRAILER, start + 2) if start >= 0 else -1
                if end < 0:
                    pending = pending[start:] if start >= 0 else b""
                    break
                raw = unstuff(pending[start + 2:end])
                pending = pending[end + 2:]
                if len(raw) >= 6:
                    self.frames.put((int.from_bytes(raw[2:4], "little"), raw[4:-2]))

    def send(self, data):
        self.record("W", data)
        sent = 0
        deadline = time.monotonic() + 2
        while sent < len(data):
            try:
                sent += os.write(self.fd, data[sent:])
            except OSError as error:
                if error.errno != errno.ENOSPC or time.monotonic() > deadline:
                    raise
                time.sleep(0.01)

    def receive(self, wait):
        """Return the complete frames received, waiting up to wait seconds for the first."""
        frames = []
        try:
            frames.append(self.frames.get(timeout=wait))
            while True:
                frames.append(self.frames.get_nowait())
        except queue.Empty:
            return frames


def send_acked(link, data, ident, seq, retries=5):
    for attempt in range(retries):
        link.send(data)
        deadline = time.monotonic() + 0.2 * 2 ** attempt
        while time.monotonic() < deadline:
            for got, payload in link.receive(0.05):
                if got == ident and int.from_bytes(payload[:2], "little") == seq:
                    return True
    return False


def run_second(link, params, millis, first):
    now = time.time() - GPS_EPOCH + LEAP
    units = int((now % 604800) / 1.5)
    status = bytearray(17)
    status[4:6] = bytes.fromhex(params["status4"])
    status[11:15] = bytes(((units >> 16) & 255, (units >> 24) & 255, units & 255, (units >> 8) & 255))
    out = [frame(0xfe00, b"\0\0" + (millis & 0xffff).to_bytes(2, "little")), frame(0xfe01, bytes(status))]
    out += [frame(0xfe03, bytes.fromhex(item)) for item in params["lists"]]
    if first:
        out.append(frame(0xfe04, b"\xff" * 28))
    out.append(frame(0xfe08, bytes.fromhex(params["setting"])))
    if first:
        out.append(frame(0xfe08, bytes.fromhex(params["setting_first"])))
    out += [frame(0xfe1c, b""), frame(0xfe05, b"\x29\x00")]
    link.send(b"".join(out))


def stop_on_signal(_number, _frame):
    sys.exit(3)


def main():
    signal.signal(signal.SIGTERM, stop_on_signal)
    device, params_path, library, output, seconds = sys.argv[1:6]
    with open(params_path) as source:
        params = json.load(source)
    with open(library, "rb") as source:
        source.seek(params["image_offset"])
        image = source.read(params["image_size"])
    if hashlib.sha256(image).hexdigest() != params["image_sha256"]:
        print("image hash mismatch", flush=True)
        return EXIT_BOOT
    with open(output, "w") as log:
        link = Link(device, log)
        for number, size in ((11, 0), (10, 0), (7, 4), (8, 4)):
            result = fcntl.ioctl(link.fd, number, bytearray(size) if size else 0)
            print("ioctl", number, "ok", result if size == 0 else bytes(result).hex(), flush=True)
        status = 3
        try:
            status = session(link, params, image, float(seconds))
        finally:
            link.send(frame(0xfe05, b"\x04\x00"))
            time.sleep(0.5)
            print("stop sent", flush=True)
            # The reader sits in a blocking read: leaving the process closes the device.
            log.flush()
            os._exit(status)


def session(link, params, image, seconds):
    if not send_acked(link, frame(0xfe08, bytes.fromhex(params["header"])), 0xfe31, 0):
        print("no reply to the boot header", flush=True)
        return EXIT_BOOT
    count = (len(image) + 1399) // 1400
    for index in range(count):
        seq = index + 1
        part = image[index * 1400:(index + 1) * 1400]
        if not send_acked(link, frame(0xfe0c, seq.to_bytes(2, "little") + part), 0xfe32, seq):
            print("no acknowledgement for fragment", seq, flush=True)
            return EXIT_BOOT
    print("image sent,", count, "fragments", flush=True)
    for item in params["setup"]:
        link.send(frame(0xfe05, bytes.fromhex(item)))
    start = time.monotonic()
    next_tick = start
    millis = params["first_millis"]
    first = True
    seen = 0
    ids = {}
    while time.monotonic() - start < seconds:
        now = time.monotonic()
        if now >= next_tick:
            run_second(link, params, millis, first)
            first = False
            millis += 1000
            next_tick += 1
        for ident, _payload in link.receive(min(0.2, max(0.01, next_tick - now))):
            ids[ident] = ids.get(ident, 0) + 1
            seen = now
        if now - start > 30 and now - seen > 10:
            print("DSP silent for 10 s", flush=True)
            return EXIT_SILENT
    print("finished, frames by id", {hex(key): ids[key] for key in sorted(ids)}, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
