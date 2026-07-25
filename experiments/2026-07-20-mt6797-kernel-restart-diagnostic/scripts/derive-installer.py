#!/usr/bin/env python3
"""Derive Candidate AB's guarded boot2 installer from exact AA r1."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys

from ab_contract import (
    AA_BOOT_SHA256,
    AA_BOOT_SIZE,
    AA_R1_INSTALLER_SHA256,
    AA_R1_PADDED_SHA256,
    BOOT2_CAPACITY,
    HEX256,
)


PREDECESSOR_LABEL = "AA-r1-hardware-passed"


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
            raise ValueError("Candidate AA r1 installer foundation is not a regular file")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived Candidate AB installer")
        if HEX256.fullmatch(args.raw_sha256) is None or HEX256.fullmatch(
            args.padded_sha256
        ) is None:
            raise ValueError("Candidate AB installer hashes are not calibrated SHA-256")
        if not args.raw_size.isdecimal() or not 0 < int(args.raw_size) <= BOOT2_CAPACITY:
            raise ValueError("Candidate AB installer size is invalid or oversized")
        if args.raw_sha256 == AA_BOOT_SHA256 or args.padded_sha256 == AA_R1_PADDED_SHA256:
            raise ValueError("Candidate AB identity equals the installed AA r1 predecessor")

        source_data = args.source.read_bytes()
        if digest(source_data) != AA_R1_INSTALLER_SHA256:
            raise ValueError("exact Candidate AA r1 installer foundation changed")
        text = source_data.decode("utf-8")

        text = text.replace("AA-r0-superseded-before-boot", PREDECESSOR_LABEL)
        text = text.replace("Candidate AA r1", "Candidate AB")
        text = text.replace(
            "EXPECTED_CURRENT_AA_R0_PADDED_SHA256", "@EXPECTED_CURRENT_PREDECESSOR@"
        )
        text = text.replace(
            "candidate-AA-keyboard-console-map", "candidate-AB-mt6797-kernel-restart"
        )
        text = text.replace("gemini-keyboard-console-map", "gemini-mt6797-kernel-restart")
        text = text.replace("candidate-aa-r1", "candidate-ab")
        text = text.replace(
            "2026-07-20-keyboard-console-map-diagnostic",
            "2026-07-20-mt6797-kernel-restart-diagnostic",
        )
        text = text.replace("AA_R1_RAW", "AB_RAW")
        text = text.replace("AA_R1_PADDED", "AB_PADDED")
        text = text.replace(
            "@EXPECTED_CURRENT_PREDECESSOR@", "EXPECTED_CURRENT_AA_R1_PADDED_SHA256"
        )
        text = text.replace("candidate_label=AA-r1", "candidate_label=AB")
        text = text.replace("install-candidate-aa-boot2.sh", "install-candidate-ab-boot2.sh")

        text = replace_once(
            text,
            f"readonly AB_RAW_SHA256={AA_BOOT_SHA256}",
            f"readonly AB_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(
            text,
            f"readonly AB_RAW_SIZE={AA_BOOT_SIZE}",
            f"readonly AB_RAW_SIZE={args.raw_size}",
        )
        text = replace_once(
            text,
            f"readonly AB_PADDED_SHA256={AA_R1_PADDED_SHA256}",
            f"readonly AB_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            "readonly EXPECTED_CURRENT_AA_R1_PADDED_SHA256="
            "157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa",
            "readonly EXPECTED_CURRENT_AA_R1_PADDED_SHA256=" + AA_R1_PADDED_SHA256,
        )

        sole_write = 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4'
        if text.count(sole_write) != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        required = (
            "gemini-mt6797-kernel-restart.boot.img",
            f"candidate-AB-mt6797-kernel-restart-final-${{AB_RAW_SHA256:0:8}}",
            "candidate-ab-padded-boot2.img",
            ".gemini-candidate-ab.",
            ".gemini-candidate-ab-root.",
            "boot2-before-candidate-ab.img",
            "boot2-after-candidate-ab.img",
            f"expected_previous_label={PREDECESSOR_LABEL}",
            "candidate_label=AB",
            "reboot_or_shutdown_performed=no",
        )
        if any(token not in text for token in required):
            raise ValueError("derived installer lost Candidate AB safety/evidence identity")
        forbidden = (
            "Candidate AA r1",
            "candidate-aa-r1",
            "AA_R1_RAW",
            "EXPECTED_CURRENT_AA_R0",
            "gemini-keyboard-console-map.boot.img",
        )
        if any(token in text for token in forbidden):
            raise ValueError("derived installer retained Candidate AA r1 target identity")
        if "sysrq-trigger" in text or re.search(
            r"(?m)^[ \t]*(?:sudo[ \t]+)?"
            r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
            text,
        ):
            raise ValueError("derived installer reboot boundary changed")

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
