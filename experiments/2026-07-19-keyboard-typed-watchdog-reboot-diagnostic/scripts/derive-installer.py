#!/usr/bin/env python3
"""Derive Candidate Y's installer from the hash-pinned calibrated X installer."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


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
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived installer")
        text = args.source.read_text(encoding="utf-8")
        text = text.replace("Candidate W", "@PREDECESSOR_CANDIDATE@")
        text = text.replace("Candidate X", "Candidate Y")
        text = text.replace("@PREDECESSOR_CANDIDATE@", "Candidate X")
        text = text.replace("candidate-X", "candidate-Y")
        text = text.replace("candidate-x", "candidate-y")
        text = text.replace("keyboard-manual-reboot", "keyboard-typed-watchdog-reboot")
        text = text.replace("X_RAW", "Y_RAW")
        text = text.replace("X_PADDED", "Y_PADDED")
        text = text.replace("EXPECTED_CURRENT_W", "EXPECTED_CURRENT_X")
        if text.count("candidate_label=X") != 2:
            raise ValueError("installer foundation candidate-label count changed")
        text = text.replace("candidate_label=X", "candidate_label=Y")
        text = replace_once(text, "expected_previous_label=W", "expected_previous_label=X")
        text = replace_once(
            text,
            "readonly Y_RAW_SHA256=bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296",
            f"readonly Y_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(text, "readonly Y_RAW_SIZE=6864896",
                            f"readonly Y_RAW_SIZE={args.raw_size}")
        text = replace_once(
            text,
            "readonly Y_PADDED_SHA256=e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855",
            f"readonly Y_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            "readonly EXPECTED_CURRENT_X_PADDED_SHA256=0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608",
            "readonly EXPECTED_CURRENT_X_PADDED_SHA256=e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855",
        )
        root_block = re.compile(
            r'script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"\n'
            r'readonly script_dir\n'
            r'experiment_dir="\$\(cd -- "\$script_dir/\.\." && pwd -P\)"\n'
            r'readonly experiment_dir\n'
            r'repo_root="\$\(cd -- "\$experiment_dir/\.\./\.\." && pwd -P\)"\n'
            r'readonly repo_root\n'
        )
        text, count = root_block.subn(
            'repo_root=${GEMINI_REPO_ROOT:?missing wrapper-provided repository root}\n'
            'readonly repo_root\n', text
        )
        if count != 1:
            raise ValueError("installer repository-root block changed")
        if text.count('dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4') != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        if "reboot_or_shutdown_performed=no" not in text or "sysrq-trigger" in text:
            raise ValueError("derived installer reboot boundary changed")
        args.output.write_text(text, encoding="utf-8")
        args.output.chmod(0o700)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
