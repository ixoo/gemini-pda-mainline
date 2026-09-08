#!/usr/bin/env python3
"""One admitted Gemian boot: read IMU chip ID once; default is metadata only."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re


BOOT = "6a5395c2-71d0-4392-a397-be3be83b049b"
VERSION_SHA = "999f539c557b29fb34f1adc6a70992bae63f241e4a5ab4fd47b8d9baf8f81688"
CONFIG_SHA = "231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4"
DRIVER = Path("/sys/bus/platform/drivers/gsensor")
ORIGINAL = "reg=0X00, len=0\n"
SELECTED = "reg=0X00, len=1\n"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_live():
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == BOOT,
            "boot identity changed")
    require(os.uname().release == "3.18.41+", "unexpected kernel release")
    require(Path("/sys/bus/i2c/devices/1-0068/driver").resolve() ==
            Path("/sys/bus/i2c/drivers/bmi160_acc"), "unexpected bound driver")


def selector():
    return (DRIVER / "reg_sel").read_text()


def select(request):
    # The audited selector callback changes only two driver RAM fields.
    fd = os.open(str(DRIVER / "reg_sel"), os.O_WRONLY)
    try:
        require(os.write(fd, request) == len(request), "short selector write")
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-identity", action="store_true")
    args = parser.parse_args()
    result = {"boot_id": BOOT, "value_read_calls": 0, "selector_restored": False}
    try:
        check_live()
        require(hashlib.sha256(Path("/proc/version").read_bytes()).hexdigest() ==
                VERSION_SHA, "kernel version digest mismatch")
        config = gzip.decompress(Path("/proc/config.gz").read_bytes())
        require(hashlib.sha256(config).hexdigest() == CONFIG_SHA,
                "kernel configuration mismatch")
        require(selector() == ORIGINAL, "unexpected initial selector")
        result["initial_selector"] = ORIGINAL.strip()
        if args.read_identity:
            try:
                select(b"00 1")
                check_live()
                require(selector() == SELECTED, "selector verification failed")
                fd = os.open(str(DRIVER / "reg_val"), os.O_RDONLY)
                try:
                    result["value_read_calls"] += 1
                    raw = os.read(fd, 16)
                finally:
                    os.close(fd)
                require(re.fullmatch(b"[0-9A-F]{2}\n", raw) is not None,
                        "unexpected identity response")
                result["register"] = "0x00"
                result["value"] = hex(int(raw.strip(), 16))
            finally:
                check_live()
                current = selector()
                require(current in (ORIGINAL, SELECTED), "competing selector change")
                if current == SELECTED:
                    select(b"00 0")
                require(selector() == ORIGINAL, "selector restore failed")
                result["selector_restored"] = True
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
