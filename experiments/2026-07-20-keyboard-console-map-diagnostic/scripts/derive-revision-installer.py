#!/usr/bin/env python3
"""Derive Candidate AA r1's installer from exact installed AA r0."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys


AA_R0_DERIVED_INSTALLER_SHA256 = (
    "c920eca1207dfe1362f947a74935a50fd934574f7becae4d056b09f362d46196"
)
AA_R0_RAW_SHA256 = (
    "a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c"
)
AA_R0_PADDED_SHA256 = (
    "157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa"
)
PREDECESSOR_LABEL = "AA-r0-superseded-before-boot"
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
            raise ValueError("Candidate AA r0 installer foundation is not a regular file")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived installer")
        if not HEX256.fullmatch(args.raw_sha256) or not HEX256.fullmatch(
            args.padded_sha256
        ):
            raise ValueError(
                "Candidate AA r1 installer hashes are not calibrated SHA-256 values"
            )
        if (
            not args.raw_size.isdecimal()
            or not 0 < int(args.raw_size) <= 16 * 1024 * 1024
        ):
            raise ValueError("Candidate AA r1 installer size is invalid or oversized")
        if (
            args.raw_sha256 == AA_R0_RAW_SHA256
            or args.padded_sha256 == AA_R0_PADDED_SHA256
        ):
            raise ValueError(
                "Candidate AA r1 identity equals the installed AA r0 predecessor"
            )

        source_data = args.source.read_bytes()
        if digest(source_data) != AA_R0_DERIVED_INSTALLER_SHA256:
            raise ValueError("exact Candidate AA r0 derived installer changed")
        text = source_data.decode("utf-8")

        # Preserve the artifact's established Candidate-AA basename while
        # making deployment lineage, evidence files, staging namespaces, and
        # predecessor identity revision-specific.
        text = text.replace("Candidate Z", "@PREDECESSOR_DISPLAY@")
        text = text.replace("Candidate AA", "Candidate AA r1")
        text = text.replace("@PREDECESSOR_DISPLAY@", PREDECESSOR_LABEL)
        text = text.replace("AA_RAW_SHA256", "AA_R1_RAW_SHA256")
        text = text.replace("AA_RAW_SIZE", "AA_R1_RAW_SIZE")
        text = text.replace("AA_PADDED_SHA256", "AA_R1_PADDED_SHA256")
        text = text.replace(
            "EXPECTED_CURRENT_Z_PADDED_SHA256",
            "EXPECTED_CURRENT_AA_R0_PADDED_SHA256",
        )
        text = text.replace(
            "candidate-aa-padded-boot2.img", "candidate-aa-r1-padded-boot2.img"
        )
        text = text.replace(".gemini-candidate-aa.", ".gemini-candidate-aa-r1.")
        text = text.replace(
            ".gemini-candidate-aa-root.", ".gemini-candidate-aa-r1-root."
        )
        text = text.replace(
            "boot2-before-candidate-aa", "boot2-before-candidate-aa-r1"
        )
        text = text.replace(
            "boot2-after-candidate-aa", "boot2-after-candidate-aa-r1"
        )
        if text.count("candidate_label=AA") != 2:
            raise ValueError("installer foundation candidate-label count changed")
        text = text.replace("candidate_label=AA", "candidate_label=AA-r1")
        text = replace_once(
            text,
            "expected_previous_label=Z",
            f"expected_previous_label={PREDECESSOR_LABEL}",
        )
        text = replace_once(
            text,
            "readonly AA_R1_RAW_SHA256=" + AA_R0_RAW_SHA256,
            f"readonly AA_R1_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(
            text,
            "readonly AA_R1_RAW_SIZE=7120896",
            f"readonly AA_R1_RAW_SIZE={args.raw_size}",
        )
        text = replace_once(
            text,
            "readonly AA_R1_PADDED_SHA256=" + AA_R0_PADDED_SHA256,
            f"readonly AA_R1_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            "readonly EXPECTED_CURRENT_AA_R0_PADDED_SHA256="
            "ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40",
            "readonly EXPECTED_CURRENT_AA_R0_PADDED_SHA256="
            + AA_R0_PADDED_SHA256,
        )

        target_write = (
            'dd if="$root_stage_file" of="$target" bs=4M '
            "iflag=fullblock count=4"
        )
        if text.count(target_write) != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        forbidden_predecessor_tokens = (
            "Candidate Z",
            "expected_previous_label=Z",
            "EXPECTED_CURRENT_Z",
            "ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40",
            "boot2-before-candidate-aa.img",
            "boot2-after-candidate-aa.img",
        )
        if any(token in text for token in forbidden_predecessor_tokens):
            raise ValueError("derived installer retained Candidate Z predecessor state")
        required_revision_tokens = (
            "candidate-aa-r1-padded-boot2.img",
            ".gemini-candidate-aa-r1.",
            ".gemini-candidate-aa-r1-root.",
            "boot2-before-candidate-aa-r1.img",
            "boot2-after-candidate-aa-r1.img",
            f"expected_previous_label={PREDECESSOR_LABEL}",
        )
        if any(token not in text for token in required_revision_tokens):
            raise ValueError("derived installer lost Candidate AA r1 evidence identity")
        if (
            "reboot_or_shutdown_performed=no" not in text
            or "sysrq-trigger" in text
            or re.search(
                r"(?m)^[ \t]*(?:sudo[ \t]+)?"
                r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
                text,
            )
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
