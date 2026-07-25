#!/usr/bin/env python3
"""Derive a calibrated Candidate AB outer installer wrapper."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

from ab_contract import (
    AA_BOOT_SHA256,
    AA_R1_PADDED_SHA256,
    AB_INSTALLER_WRAPPER_TEMPLATE_SHA256,
    BOOT2_CAPACITY,
    HEX256,
    digest_path,
    read_regular,
)


PLACEHOLDERS = {
    "raw_sha256": "REPLACE_AFTER_CALIBRATION_AB_RAW_SHA256",
    "raw_size": "REPLACE_AFTER_CALIBRATION_AB_RAW_SIZE",
    "padded_sha256": "REPLACE_AFTER_CALIBRATION_AB_PADDED_SHA256",
    "inner_sha256": "REPLACE_AFTER_CALIBRATION_AB_INNER_INSTALLER_SHA256",
    "materializer_sha256": "REPLACE_AFTER_CALIBRATION_MATERIALIZER_SHA256",
    "deriver_sha256": "REPLACE_AFTER_CALIBRATION_DERIVER_SHA256",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--raw-sha256", required=True)
    parser.add_argument("--raw-size", required=True)
    parser.add_argument("--padded-sha256", required=True)
    parser.add_argument("--inner-sha256", required=True)
    parser.add_argument("--materializer-sha256", required=True)
    parser.add_argument("--deriver-sha256", required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    template = script_dir / "install-candidate-ab-boot2.sh.in"
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite calibrated Candidate AB wrapper")
        if not args.output.parent.is_dir() or args.output.parent.is_symlink():
            raise ValueError("wrapper output parent is missing or unsafe")
        if digest_path(template) != AB_INSTALLER_WRAPPER_TEMPLATE_SHA256:
            raise ValueError("Candidate AB installer wrapper template changed")
        values = {
            "raw_sha256": args.raw_sha256,
            "raw_size": args.raw_size,
            "padded_sha256": args.padded_sha256,
            "inner_sha256": args.inner_sha256,
            "materializer_sha256": args.materializer_sha256,
            "deriver_sha256": args.deriver_sha256,
        }
        for name in (
            "raw_sha256",
            "padded_sha256",
            "inner_sha256",
            "materializer_sha256",
            "deriver_sha256",
        ):
            if HEX256.fullmatch(values[name]) is None:
                raise ValueError(f"wrapper calibration hash is malformed: {name}")
        if not args.raw_size.isdecimal() or not 0 < int(args.raw_size) <= BOOT2_CAPACITY:
            raise ValueError("wrapper Candidate AB size is invalid or oversized")
        if args.raw_sha256 == AA_BOOT_SHA256 or args.padded_sha256 == AA_R1_PADDED_SHA256:
            raise ValueError("wrapper Candidate AB identity equals AA r1 predecessor")

        text = read_regular(template, "AB wrapper template", 0o755).decode("utf-8")
        for name, placeholder in PLACEHOLDERS.items():
            if text.count(placeholder) != 1:
                raise ValueError(f"wrapper placeholder count changed: {placeholder}")
            text = text.replace(placeholder, values[name])
        if any(placeholder in text for placeholder in PLACEHOLDERS.values()):
            raise ValueError("wrapper calibration placeholder remains")
        required = (
            "materialize-aa-r1-installer.py",
            "derive-installer.py",
            f'"$AB_INNER_INSTALLER_SHA256"',
            'export GEMINI_REPO_ROOT="$repo_root"',
            '"$ab_inner" "${installer_args[@]}"',
        )
        if any(token not in text for token in required):
            raise ValueError("calibrated wrapper lost installer safety identity")
        if 'of="$target"' in text:
            raise ValueError("outer wrapper gained a direct target write")
        if "sysrq-trigger" in text or re.search(
            r"(?m)^[ \t]*(?:sudo[ \t]+)?"
            r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
            text,
        ):
            raise ValueError("outer wrapper gained reboot or power-off behavior")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o700)
            stream.write(text)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
