#!/usr/bin/env python3
"""Derive Candidate Z's installer from the exact calibrated Y installer."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys


Y_DERIVED_INSTALLER_SHA256 = (
    "923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67"
)
Y_PADDED_SHA256 = "dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17"
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
            raise ValueError("Candidate Y installer foundation is not a regular file")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived installer")
        if not HEX256.fullmatch(args.raw_sha256) or not \
                HEX256.fullmatch(args.padded_sha256):
            raise ValueError("Candidate Z installer hashes are not calibrated SHA-256 values")
        if not args.raw_size.isdecimal() or not 0 < int(args.raw_size) <= 16 * 1024 * 1024:
            raise ValueError("Candidate Z installer size is invalid or oversized")
        if args.padded_sha256 == Y_PADDED_SHA256:
            raise ValueError("Candidate Z padded hash equals the Candidate Y predecessor")

        source_data = args.source.read_bytes()
        if digest(source_data) != Y_DERIVED_INSTALLER_SHA256:
            raise ValueError("Candidate Y derived installer foundation changed")
        text = source_data.decode("utf-8")
        text = text.replace("Candidate X", "@PREDECESSOR_CANDIDATE@")
        text = text.replace("Candidate Y", "Candidate Z")
        text = text.replace("@PREDECESSOR_CANDIDATE@", "Candidate Y")
        text = text.replace("candidate-X", "@PREDECESSOR_LABEL@")
        text = text.replace("candidate-x", "@PREDECESSOR_LOWER@")
        text = text.replace("candidate-Y", "candidate-Z")
        text = text.replace("candidate-y", "candidate-z")
        text = text.replace("@PREDECESSOR_LABEL@", "candidate-Y")
        text = text.replace("@PREDECESSOR_LOWER@", "candidate-y")
        text = text.replace(
            "keyboard-typed-watchdog-reboot", "keyboard-reboot-dispatch"
        )
        text = text.replace("Y_RAW", "Z_RAW")
        text = text.replace("Y_PADDED", "Z_PADDED")
        text = text.replace("EXPECTED_CURRENT_X", "EXPECTED_CURRENT_Y")
        if text.count("candidate_label=Y") != 2:
            raise ValueError("installer foundation candidate-label count changed")
        text = text.replace("candidate_label=Y", "candidate_label=Z")
        text = replace_once(text, "expected_previous_label=X", "expected_previous_label=Y")
        text = replace_once(
            text,
            "readonly Z_RAW_SHA256="
            "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee",
            f"readonly Z_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(
            text, "readonly Z_RAW_SIZE=6866944",
            f"readonly Z_RAW_SIZE={args.raw_size}",
        )
        text = replace_once(
            text,
            "readonly Z_PADDED_SHA256="
            "dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17",
            f"readonly Z_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            "readonly EXPECTED_CURRENT_Y_PADDED_SHA256="
            "e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855",
            f"readonly EXPECTED_CURRENT_Y_PADDED_SHA256={Y_PADDED_SHA256}",
        )
        target_write = (
            'dd if="$root_stage_file" of="$target" bs=4M '
            "iflag=fullblock count=4"
        )
        if text.count(target_write) != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        if "reboot_or_shutdown_performed=no" not in text or \
                "sysrq-trigger" in text or re.search(
                    r"(?m)^[ \t]*(?:sudo[ \t]+)?"
                    r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)", text
                ):
            raise ValueError("derived installer reboot boundary changed")
        descriptor = os.open(
            args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
