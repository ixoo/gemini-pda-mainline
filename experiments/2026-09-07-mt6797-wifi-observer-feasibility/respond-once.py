#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Experimental WMT responder; requires a separately admitted controller/capture."""

import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import select
import stat
import struct
import sys
import time


GET_CHIP_INFO = 0x8004A00C
SET_PATCH_NUM = 0x4004A00E
SET_PATCH_INFO = 0x4008A00F


def check_deadline(deadline):
    remaining = deadline - time.monotonic_ns()
    if remaining <= 0:
        raise TimeoutError("response deadline expired")
    return remaining


def serve(fd, deadline, records, chip, version):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    remaining = check_deadline(deadline)
    events = poller.poll((remaining + 999999) // 1000000)
    check_deadline(deadline)
    if events != [(fd, select.POLLIN)]:
        raise RuntimeError("missing command or unexpected poll event")
    command = os.read(fd, 256)
    check_deadline(deadline)
    if command != b"srh_patch":
        raise RuntimeError("unexpected command; no reply sent")
    if fcntl.ioctl(fd, GET_CHIP_INFO, 0) != chip:
        raise RuntimeError("chip identity mismatch")
    check_deadline(deadline)
    if fcntl.ioctl(fd, GET_CHIP_INFO, 2) != version:
        raise RuntimeError("firmware version mismatch")
    check_deadline(deadline)
    if fcntl.ioctl(fd, SET_PATCH_NUM, len(records)) != 0:
        raise RuntimeError("patch-count publication failed")
    for row in records:
        check_deadline(deadline)
        record = bytearray(struct.pack("<I4s256s", row["sequence"],
                                      bytes.fromhex(row["address_bytes_hex"]),
                                      row["name"].encode("ascii")))
        if fcntl.ioctl(fd, SET_PATCH_INFO, record, True) != 0:
            raise RuntimeError("patch-info publication failed")
    check_deadline(deadline)
    if os.write(fd, b"ok") != 2:
        raise RuntimeError("short reply write; do not retry")
    try:
        check_deadline(deadline)
    except TimeoutError as error:
        raise TimeoutError("reply was written but completed after deadline") from error
    return {"stage": "reply-written", "kernel_acceptance": "requires capture"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fd", type=int, required=True, help="inherited /dev/stpwmt descriptor")
    parser.add_argument("--deadline-ns", type=int, required=True, help="absolute CLOCK_MONOTONIC deadline")
    parser.add_argument("--chip", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--version", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--firmware-directory", required=True)
    args = parser.parse_args()
    if sys.platform != "linux" or sys.byteorder != "little" or struct.calcsize("P") != 8:
        raise RuntimeError("requires the reviewed Linux 64-bit little-endian ABI")
    if args.chip not in (0x0279, 0x6797) or not 0 <= args.version <= 0xffff or args.version & 0xff:
        raise ValueError("unsupported chip/version selection")
    info = os.fstat(args.fd)
    if not stat.S_ISCHR(info.st_mode):
        raise ValueError("descriptor is not a character device")
    if fcntl.fcntl(args.fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDWR:
        raise ValueError("descriptor must permit both reading and writing")
    identity = Path(f"/sys/dev/char/{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}/uevent")
    if "DEVNAME=stpwmt" not in identity.read_text().splitlines():
        raise ValueError("descriptor is not the stpwmt device")
    if not os.statvfs(args.firmware_directory).f_flag & os.ST_RDONLY:
        raise ValueError("firmware filesystem must be read-only")
    spec = importlib.util.spec_from_file_location(
        "retained_patches", Path(__file__).with_name("check-retained-patches.py"))
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    records = checker.check_directory(args.firmware_directory)
    if check_deadline(args.deadline_ns) > 1500000000:
        raise ValueError("remaining response budget exceeds 1500 ms")
    print(json.dumps({"stage": "ready", "deadline_ns": args.deadline_ns}), flush=True)
    print(json.dumps(serve(args.fd, args.deadline_ns, records, args.chip, args.version)), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"stage": "failed", "reason": str(error),
                          "effects": "may be partial; inspect kernel capture",
                          "recovery": "not performed"}), flush=True)
        raise SystemExit(1) from error
