#!/usr/bin/env python3
"""Derive Candidate AA's installer from the exact calibrated Z installer."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys


Z_DERIVED_INSTALLER_SHA256 = "38b5956e3f5146bc2c8e8ddc3cec9cfb8be25bd3661949b5bd8fb5dbdba51b76"
Z_PADDED_SHA256 = "ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40"
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"installer foundation token count changed: {old!r}")
    return text.replace(old, new)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--raw-sha256", required=True)
    parser.add_argument("--raw-size", required=True)
    parser.add_argument("--padded-sha256", required=True)
    args = parser.parse_args()
    try:
        source_info = args.source.lstat()
        if args.source.is_symlink() or not stat.S_ISREG(source_info.st_mode):
            raise ValueError("Candidate Z installer foundation is not a regular file")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived installer")
        if not HEX256.fullmatch(args.raw_sha256) or not HEX256.fullmatch(args.padded_sha256):
            raise ValueError("Candidate AA installer hashes are not calibrated SHA-256 values")
        if not args.raw_size.isdecimal() or not 0 < int(args.raw_size) <= 16 * 1024 * 1024:
            raise ValueError("Candidate AA installer size is invalid or oversized")
        if args.padded_sha256 == Z_PADDED_SHA256:
            raise ValueError("Candidate AA padded hash equals the Candidate Z predecessor")

        source_data = args.source.read_bytes()
        if digest(source_data) != Z_DERIVED_INSTALLER_SHA256:
            raise ValueError("exact Candidate Z derived installer changed")
        text = source_data.decode("utf-8")
        text = text.replace("Candidate Y", "@PREDECESSOR_CANDIDATE@")
        text = text.replace("Candidate Z", "Candidate AA")
        text = text.replace("@PREDECESSOR_CANDIDATE@", "Candidate Z")
        text = text.replace("candidate-Y", "@PREDECESSOR_LABEL@")
        text = text.replace("candidate-y", "@PREDECESSOR_LOWER@")
        text = text.replace("candidate-Z", "candidate-AA")
        text = text.replace("candidate-z", "candidate-aa")
        text = text.replace("@PREDECESSOR_LABEL@", "candidate-Z")
        text = text.replace("@PREDECESSOR_LOWER@", "candidate-z")
        text = text.replace(
            "2026-07-19-keyboard-reboot-dispatch-diagnostic",
            "2026-07-20-keyboard-console-map-diagnostic",
        )
        text = text.replace("keyboard-reboot-dispatch", "keyboard-console-map")
        text = text.replace("Z_RAW", "AA_RAW")
        text = text.replace("Z_PADDED", "AA_PADDED")
        text = text.replace("EXPECTED_CURRENT_Y", "EXPECTED_CURRENT_Z")
        if text.count("candidate_label=Z") != 2:
            raise ValueError("installer foundation candidate-label count changed")
        text = text.replace("candidate_label=Z", "candidate_label=AA")
        text = replace_once(text, "expected_previous_label=Y", "expected_previous_label=Z")
        text = replace_once(
            text,
            "readonly AA_RAW_SHA256="
            "985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9",
            f"readonly AA_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(text, "readonly AA_RAW_SIZE=6866944", f"readonly AA_RAW_SIZE={args.raw_size}")
        text = replace_once(
            text,
            "readonly AA_PADDED_SHA256="
            "ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40",
            f"readonly AA_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            "readonly EXPECTED_CURRENT_Z_PADDED_SHA256="
            "dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17",
            f"readonly EXPECTED_CURRENT_Z_PADDED_SHA256={Z_PADDED_SHA256}",
        )
        target_write = 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4'
        if text.count(target_write) != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        if "reboot_or_shutdown_performed=no" not in text or "sysrq-trigger" in text or re.search(
            r"(?m)^[ \t]*(?:sudo[ \t]+)?(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
            text,
        ):
            raise ValueError("derived installer reboot boundary changed")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
