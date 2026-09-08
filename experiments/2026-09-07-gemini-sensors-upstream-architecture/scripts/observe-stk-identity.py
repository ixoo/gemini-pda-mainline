#!/usr/bin/env python3
"""One admitted Gemian boot: two STK ID reads, never sensor configuration.

Without --read-identity, validate metadata and kernel-log access only. The
explicit action writes register addresses to the audited vendor recv attribute;
that callback performs one-byte I2C reads with at most three attempts each.
It does not use the separate send, reg, allreg, or cached recv-show interfaces.
"""

import argparse
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time


BOOT = "6a5395c2-71d0-4392-a397-be3be83b049b"
VERSION_SHA = "999f539c557b29fb34f1adc6a70992bae63f241e4a5ab4fd47b8d9baf8f81688"
CONFIG_SHA = "231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4"
DRIVER = Path("/sys/bus/platform/drivers/als_ps")
DEVICE = Path("/sys/bus/i2c/devices/1-0048")
BOOT_PATH = Path("/proc/sys/kernel/random/boot_id")
RECORD = re.compile(r"\[ALS/PS\] recv\(([0-9A-F]{2})\) = (-?\d+), 0x([0-9A-F]{2})$")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_live():
    require(BOOT_PATH.read_text().strip() == BOOT, "boot identity changed")
    require(os.uname().release == "3.18.41+", "unexpected kernel release")
    require(DEVICE.joinpath("driver").resolve() == Path("/sys/bus/i2c/drivers/stk3x1x"),
            "unexpected bound I2C driver")
    require(DEVICE.joinpath("name").read_text().strip() == "alsps", "unexpected client name")
    config = DRIVER.joinpath("config").read_text()
    require(re.fullmatch(r"\((-?\d+)(?: -?\d+){5}\)\n", config) is not None,
            "unexpected cached configuration format")
    require(int(config.split()[0][1:]) == 3, "retry count must remain three")


def log_cursor():
    fd = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
    try:
        require(stat.S_ISCHR(os.fstat(fd).st_mode), "kernel log is not a character device")
        os.lseek(fd, 0, os.SEEK_END)
    except Exception:
        os.close(fd)
        raise
    return fd


def read_identity_byte(address, result):
    check_live()
    fd = log_cursor()
    try:
        # Open only the audited read-request callback, never the register writer.
        request = format(address, "02x").encode("ascii")
        out = os.open(str(DRIVER / "recv"), os.O_WRONLY)
        try:
            result["requests_issued"] += 1
            written = os.write(out, request)
        finally:
            os.close(out)
        require(written == len(request), "short sysfs request")
        records = []
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            try:
                record = os.read(fd, 8192).decode("utf-8", errors="replace")
            except OSError as exc:
                if exc.errno != errno.EAGAIN:
                    raise
                time.sleep(0.02)
                continue
            require(record, "kernel log closed")
            header, body = record.split(";", 1)
            first_line = body.splitlines()[0]
            if "[ALS/PS] recv(" in first_line:
                match = RECORD.fullmatch(first_line)
                require(match is not None, "unexpected receive-log format")
                fields = header.split(",")
                records.append((int(fields[1]), int(fields[2]), match))
        require(len(records) == 1, "missing or competing receive-log record")
        sequence, timestamp, match = records[0]
        require(int(match.group(1), 16) == address, "receive-log address mismatch")
        require(int(match.group(2)) == 1, "I2C transfer did not succeed")
        check_live()
        return {"register": hex(address), "value": hex(int(match.group(3), 16)),
                "transfer_return": 1, "kmsg_sequence": sequence,
                "kmsg_monotonic_us": timestamp}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-identity", action="store_true")
    args = parser.parse_args()
    result = {"boot_id": BOOT, "requests_issued": 0, "observations": []}
    try:
        require(hashlib.sha256(Path("/proc/version").read_bytes()).hexdigest() == VERSION_SHA,
                "kernel version digest mismatch")
        config = gzip.decompress(Path("/proc/config.gz").read_bytes())
        require(hashlib.sha256(config).hexdigest() == CONFIG_SHA, "kernel configuration mismatch")
        check_live()
        os.close(log_cursor())
        if args.read_identity:
            for address in (0x3e, 0x3f):
                result["observations"].append(read_identity_byte(address, result))
            result["result"] = "identity-observed"
        else:
            result["result"] = "preflight-only"
    except Exception as exc:
        result["result"] = "refused-or-incomplete"
        result["reason"] = str(exc)
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
