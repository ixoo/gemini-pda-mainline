#!/usr/bin/env python3
"""Derive the guarded AQ boot2 installer from the source-pinned AP chain."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

AP_DERIVER_SHA256 = "a20198cb8e5cc8804a2fa218f9187ff30ab8cfac6e370a4f6792b86ba632918e"
AP_INSTALLER_SHA256 = "3504a5b591ad4b952c577b5ecb08eaedac5027c97431152023a2d28afef7b937"
AP_PADDED_SHA256 = "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
TARGET = "gemini@192.168.1.50"


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing or unsafe")


def derive_ap(root: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    source = root / "experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts/derive-installer.py"
    regular(source, "AP installer deriver")
    if digest(source) != AP_DERIVER_SHA256:
        raise ValueError("AP installer deriver changed")
    output = work / "install-candidate-ap-boot2.sh"
    result = subprocess.run(
        [sys.executable, os.fspath(source), "--output", os.fspath(output)],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode or digest(output) != AP_INSTALLER_SHA256:
        raise ValueError(result.stderr.strip() or "AP installer reconstruction failed")
    return output


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected one installer token: {old}")
    return text.replace(old, new)


def transform(source: str, raw: str, size: str, manifest: str, padded: str, artifact: str) -> str:
    text = source
    for old, new in (
        ("Candidate AP", "Candidate AQ"),
        ("candidate-ap", "candidate-aq"),
        ("2026-07-24-mt6797-dvfsp-i2c6-consumer", "2026-07-24-mt6797-ap-dma-owner-observer"),
        ("candidate_label=AP", "candidate_label=AQ"),
        ("AO-installed-readback-verified", "AP-installed-readback-verified"),
        ("AP_RAW", "AQ_RAW"),
        ("AP_PADDED", "AQ_PADDED"),
        ("AP_ARTIFACT", "AQ_ARTIFACT"),
        ("EXPECTED_CURRENT_AO", "EXPECTED_CURRENT_AP"),
        ("gemini-mt6797-dvfsp-i2c6-consumer.boot.img", "gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img"),
        ("candidate-AP-mt6797-dvfsp-i2c6-consumer-127e5117", artifact),
    ):
        text = text.replace(old, new)
    text = replace_once(text, "readonly AQ_RAW_SHA256=127e511711bc06a91fcfc3c716aaad2084cc42ffc6452046a582bd53f54b2924", f"readonly AQ_RAW_SHA256={raw}")
    text = replace_once(text, "readonly AQ_RAW_SIZE=7391232", f"readonly AQ_RAW_SIZE={size}")
    text = replace_once(text, "readonly AQ_PADDED_SHA256=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9", f"readonly AQ_PADDED_SHA256={padded}")
    text = replace_once(text, "readonly AQ_ARTIFACT_MANIFEST_SHA256=dae6d5b891dfccdfc7831cea18fff2b4f43de345333f07e50303619dadd07f7a", f"readonly AQ_ARTIFACT_MANIFEST_SHA256={manifest}")
    text = replace_once(text, "readonly EXPECTED_CURRENT_AP_PADDED_SHA256=3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb", f"readonly EXPECTED_CURRENT_AP_PADDED_SHA256={AP_PADDED_SHA256}")
    required = (
        f"readonly AQ_RAW_SHA256={raw}", f"readonly AQ_PADDED_SHA256={padded}",
        f'expected_artifact_name="{artifact}"',
        '[[ "$candidate_name" == gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img ]]',
        f"--target {TARGET}", "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived AQ installer lost safety token: {token}")
    for stale in ("Candidate AP", "candidate-ap", "readonly AP_RAW_SHA256=", "readonly AP_PADDED_SHA256=", "readonly AP_ARTIFACT_MANIFEST_SHA256=", "gemini-mt6797-dvfsp-i2c6-consumer.boot.img"):
        if stale in text:
            raise ValueError(f"derived AQ installer retains stale token: {stale}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[3]
    artifact = args.artifact.resolve(strict=True)
    candidate = artifact / "gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img"
    manifest_file = artifact / "SHA256SUMS"
    regular(candidate, "AQ candidate")
    regular(manifest_file, "AQ manifest")
    raw = digest(candidate)
    size = str(candidate.stat().st_size)
    manifest = digest(manifest_file)
    padded = "TO_CALIBRATE_PADDED_SHA256"
    if not re.fullmatch(r"[0-9a-f]{64}", raw) or int(size) > 16 * 1024 * 1024:
        raise ValueError("AQ candidate size or hash is invalid")
    # The padded identity is supplied after the local calibration pass.
    if not re.fullmatch(r"[0-9a-f]{64}", os.environ.get("AQ_PADDED_SHA256", "")):
        raise ValueError("AQ_PADDED_SHA256 must be supplied for installer derivation")
    padded = os.environ["AQ_PADDED_SHA256"]
    artifact_name = artifact.name
    with tempfile.TemporaryDirectory(prefix=".aq-installer-") as name:
        ap = derive_ap(root, pathlib.Path(name))
        text = transform(ap.read_text(encoding="utf-8"), raw, size, manifest, padded, artifact_name)
    output = args.output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("installer output already exists")
    output.write_text(text, encoding="utf-8")
    output.chmod(0o700)
    print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
    print(f"candidate_raw_sha256={raw}")
    print(f"candidate_raw_size={size}")
    print(f"candidate_manifest_sha256={manifest}")
    print(f"candidate_padded_sha256={padded}")
    print(f"expected_predecessor_sha256={AP_PADDED_SHA256}")
    print(f"artifact_directory={artifact_name}")
    print("reboot_or_slot_selection=none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
