#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Offline tests for gnss-mt6797d. No hardware.

usage: test-offline.py HOST_CAPTURE FIX_CAPTURE
  HOST_CAPTURE  a frames.log from gnss-minihost.c on /dev/gnss0 (T5), whose writes the
                daemon's must match
  FIX_CAPTURE   a frames.log with enough satellites for fixes (step 6), replayed through
                the daemon's live loop against a fake device

Captures hold position and stay private; this prints only counts.
"""
import importlib.machinery
import importlib.util
import os
import pty
import signal
import subprocess
import sys
import time
import tty

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader("daemon", os.path.join(HERE, "gnss-mt6797d"))
spec = importlib.util.spec_from_loader("daemon", loader)
d = importlib.util.module_from_spec(spec)
loader.exec_module(d)
failed = 0


def check(name, ok, detail=""):
    global failed
    print("%s %s %s" % ("ok  " if ok else "FAIL", name, detail))
    failed += not ok


def lines(path, kind):
    for line in open(path):
        p = line.split()
        if len(p) == 3 and p[1] == kind:
            yield float(p[0]), bytes.fromhex(p[2])


# 1. Framing: what frame() builds, Deframer reads back, also split into small pieces.
items = [(0xFE05, bytes(range(256))), (0xFE08, b"\xaa\xde" * 40), (0xFE1C, b"")]
stream = b"junk" + b"".join(d.frame(i, p) for i, p in items) + b"\xaa\xf0\x01"
got = []
de = d.Deframer()
for i in range(0, len(stream), 3):
    got += de.feed(stream[i:i + 3])
check("frames round trip in 3-byte pieces", got == items and de.bad == 0)
broken = bytearray(d.frame(0xFE05, b"\x29\x00"))
broken[-4] ^= 1
check("a bad sum is dropped", d.Deframer().feed(bytes(broken)) == [])

# 2. The host's writes: the daemon's setup and per-second frames against the C host's,
# except FE01's time bytes and the search list, which the daemon builds itself.
host = d.Deframer()
written = [f for _, b in lines(sys.argv[1], "W") for f in host.feed(b)]
ours = d.Deframer().feed(b"".join(d.frame(0xFE05, bytes.fromhex(s)) for s in d.SETUP) +
                         d.second_frames(d.FIRST_MILLIS, True, 0) +
                         d.second_frames(d.FIRST_MILLIS + 1000, False, 0))
start = next(i for i, f in enumerate(written) if f[0] == 0xFE05 and f[1][:1] == b"\x32")
theirs = written[start:start + len(ours)]


def comparable(f):
    ident, p = f
    if ident == 0xFE01:
        return ident, p[:11] + p[15:]
    if ident == 0xFE03 and p[:1] == b"\x01":
        return ident, p[:2]
    return f


check("setup and two seconds match the C host", [comparable(f) for f in ours] == [comparable(f) for f in theirs],
      "%d frames" % len(ours))
listed = sorted(d.LISTS[1][2 + 2 * i:4 + 2 * i] for i in range(60))
stock = [f[1] for f in theirs if f[0] == 0xFE03 and f[1][:1] == b"\x01"][0]
check("search list holds the same satellites as stock's", listed == sorted(stock[2 + 2 * i:4 + 2 * i] for i in range(60)))

# 3. The live loop against a fake device: a pty that plays the capture's DSP bytes.
fake, dev = pty.openpty()
tty.setraw(dev)
tty.setraw(fake)
link = os.path.join(os.environ.get("TMPDIR", "/tmp"), "gnss-test-nmea-%d" % os.getpid())
proc = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "gnss-mt6797d"), "--device", os.ttyname(dev),
                         "--link", link], stdout=subprocess.PIPE, text=True,
                        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
for _ in range(50):
    if os.path.islink(link):
        break
    time.sleep(0.1)
reader = os.open(link, os.O_RDONLY | os.O_NONBLOCK)
tty.setraw(reader)
received = bytearray()
nmea = bytearray()
os.set_blocking(fake, False)


def drain():
    for fd, buf in ((fake, received), (reader, nmea)):
        try:
            buf += os.read(fd, 65536)
        except BlockingIOError:
            pass


for _, b in lines(sys.argv[2], "R"):
    while b:
        try:
            b = b[os.write(fake, b):]
        except BlockingIOError:
            time.sleep(0.01)
        drain()
time.sleep(2.5)
drain()
proc.send_signal(signal.SIGTERM)
out, _ = proc.communicate(timeout=10)
time.sleep(0.2)
try:
    received += os.read(fake, 65536)
except (BlockingIOError, OSError):
    pass
sent = d.Deframer().feed(bytes(received))
text = nmea.decode(errors="replace")
fixes = sum(1 for l in text.splitlines() if l.startswith("$GPGGA") and l.split(",")[6] == "1")
check("live loop sent the setup", [f for f in sent if f[0] == 0xFE05][:8] ==
      [(0xFE05, bytes.fromhex(s)) for s in d.SETUP])
check("live loop sent per-second frames", sum(f[0] == 0xFE00 for f in sent) >= 2)
check("live loop sent stop last", sent[-1:] == [(0xFE05, b"\x04\x00")])
check("live loop wrote fixes to the pty", fixes > 100, "%d GGA fixes" % fixes)
check("checksums of every sentence", all(
    "%02X" % eval("0" + "".join("^%d" % ord(c) for c in l[1:l.index("*")])) == l[l.index("*") + 1:l.index("*") + 3]
    for l in text.splitlines() if l.startswith("$") and "*" in l))
check("daemon exited 0 and removed its link", proc.returncode == 0 and not os.path.lexists(link), out.strip().splitlines()[-1:])
sys.exit(1 if failed else 0)
