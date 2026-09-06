#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive or execute the exact guarded passive-CONSYS boot2 installer.

Derivation reuses the pinned TOPRGU deployment transport and changes only the
candidate validator, receipt classifier, evidence identity, and experiment
label. ``--execute`` is the sole device/write switch; the derived shell retains
the live GPT, inactive/unmounted target, power, predecessor, full readback, and
clean-shutdown gates. It never reboots the device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import stat
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
PARENT_INSTALLER = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/scripts/installer.py"
PARENT_INSTALLER_SHA256 = "8aef9f6ed975fac3f09d7e3c057a601a444be854efb0ea6de26035adf288388a"
PARENT_VALIDATOR = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/scripts/validate-candidate.py"
PARENT_VALIDATOR_SHA256 = "de4199496f04110d018ba2d89bf747d495ee4106278bff1ac4ccdef114ce71d7"
PARENT_RECEIPT = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/scripts/deployment_receipt.py"
PARENT_RECEIPT_SHA256 = "794c221c42bf9cd127c84f978529b17ac571033a96621179d11c34e2ffaa9a05"
VALIDATOR = HERE / "scripts/validate-candidate.py"
VALIDATOR_SHA256 = "a79d7e3536a3987c3912e1366eeb3382d9e5543c967734f976d3540db2f81246"
RECEIPT = HERE / "scripts/deployment_receipt.py"
RECEIPT_SHA256 = "1d6699c4ab527da3e4aa7e6f2caa8c1796d5df0f36c6ff9ffd98845c7d08da18"
TARGET = "gemini@192.168.1.50"
CANDIDATE_SHA256 = "08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2"
EXPECTED_PREDECESSOR_SHA256 = "22edf533734ac52e56f3291c90264359fec2eaccc79cd68acf28b20d9cb216e8"
EXPERIMENT = "2026-09-06-mt6797-consys-passive-boot"
PARENT_EXPERIMENT = "2026-09-06-mt6797-toprgu-minimal-restart"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def regular(path: Path, limit: int = 32 * 1024 * 1024) -> bytes:
    info = path.lstat()
    require(not path.is_symlink() and stat.S_ISREG(info.st_mode) and
            info.st_nlink == 1 and info.st_size <= limit,
            "unsafe or oversized input: " + path.name)
    return path.read_bytes()


def source_pins() -> dict:
    pins = {
        PARENT_INSTALLER: PARENT_INSTALLER_SHA256,
        PARENT_VALIDATOR: PARENT_VALIDATOR_SHA256,
        PARENT_RECEIPT: PARENT_RECEIPT_SHA256,
        VALIDATOR: VALIDATOR_SHA256,
        RECEIPT: RECEIPT_SHA256,
    }
    for path, expected in pins.items():
        require(digest(regular(path, 512 * 1024)) == expected,
                "reviewed deployment source changed: " + str(path.relative_to(REPO)))
    return runpy.run_path(str(PARENT_INSTALLER))


def replace_count(source: str, old: str, new: str, count: int,
                  label: str) -> str:
    require(source.count(old) == count,
            "derived installer anchors changed: " + label)
    return source.replace(old, new)


def derive(candidate: Path, package: Path, foundation_initramfs: Path,
           userspace: Path, credentials: Path) -> str:
    """Return a fully validated, exact-candidate installer shell."""
    parent = source_pins()
    candidate = candidate.resolve(strict=True)
    package = package.resolve(strict=True)
    foundation_initramfs = foundation_initramfs.resolve(strict=True)
    userspace = userspace.resolve(strict=True)
    credentials = credentials.resolve(strict=True)
    require(candidate.name == "candidate-" + CANDIDATE_SHA256,
            "passive candidate directory identity changed")
    require(digest(regular(candidate / "boot2-padded.img")) == CANDIDATE_SHA256,
            "passive candidate checksum changed")
    require(foundation_initramfs.name ==
            "gemini-pwrap-reset-serviceability-initramfs.img",
            "foundation initramfs path changed")
    base_dtb = package / "dtbs/mediatek/mt6797-gemini-pda.dtb"

    validator = runpy.run_path(str(VALIDATOR))
    result = validator["validate"](candidate, package, foundation_initramfs,
                                   userspace, credentials)
    require(result.get("candidate") == CANDIDATE_SHA256 and
            result.get("result") == "pass",
            "passive candidate validator result changed")
    source = parent["derive"](
        candidate, foundation_initramfs.parent, userspace,
        EXPECTED_PREDECESSOR_SHA256, base_dtb=base_dtb,
        credentials=credentials)

    source = replace_count(source, str(PARENT_VALIDATOR), str(VALIDATOR), 2,
                           "candidate validator path")
    source = replace_count(source, PARENT_VALIDATOR_SHA256, VALIDATOR_SHA256, 1,
                           "candidate validator digest")
    source = replace_count(source, str(PARENT_RECEIPT), str(RECEIPT), 2,
                           "deployment receipt path")
    source = replace_count(source, PARENT_RECEIPT_SHA256, RECEIPT_SHA256, 1,
                           "deployment receipt digest")
    parent_name = "toprgu-minimal-restart-deployment-" + CANDIDATE_SHA256[:16]
    passive_name = "consys-passive-deployment-" + CANDIDATE_SHA256[:16]
    source = replace_count(source, parent_name, passive_name, 3,
                           "deployment evidence name")
    source = replace_count(source, PARENT_EXPERIMENT, EXPERIMENT, 2,
                           "deployment experiment")

    require(str(PARENT_VALIDATOR) not in source and
            PARENT_VALIDATOR_SHA256 not in source and
            str(PARENT_RECEIPT) not in source and
            PARENT_RECEIPT_SHA256 not in source,
            "stale parent deployment identity remains")
    require(source.count('of="$target"') == 1,
            "derived installer write inventory changed")
    for token in (
        "readonly CANDIDATE_SHA256=" + CANDIDATE_SHA256,
        "readonly EXPECTED_PREDECESSOR_SHA256=" + EXPECTED_PREDECESSOR_SHA256,
        'boot2_device_guard "$target" "$majmin" "$root_major_minor"',
        'dd if="$EXPECTED_STAGE" of="$target"',
        'blockdev --flushbufs "$target"',
        'cmp -s "$candidate" "$readback_tmp"',
        "fresh_predecessor_backup=no", "sudo -n systemctl poweroff",
        "post_shutdown_reachability=unreachable", "reboot=no",
    ):
        require(token in source, "derived installer lost closure: " + token)
    return source


def private_output(path: Path) -> Path:
    path = path.absolute()
    root = (REPO / "artifacts/consys-passive").absolute()
    require(path.is_relative_to(root) and path.parent != root and
            path.name not in {"", ".", ".."},
            "installer output must remain below passive private artifacts")
    artifacts = (REPO / "artifacts").absolute()
    for parent in (artifacts, root):
        require(not parent.is_symlink(), "symlink in installer output path")
        parent.mkdir(mode=0o700, exist_ok=True)
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and
                stat.S_IMODE(info.st_mode) == 0o700 and
                info.st_uid == os.getuid(), "installer output parent is not private")
    real_root = root.resolve(strict=True)
    require(real_root == root, "passive artifact root changed by resolution")
    relative_parent = path.parent.relative_to(root)
    require(all(part not in {"", ".", ".."} for part in relative_parent.parts),
            "installer output parent contains traversal")
    cursor = root
    for part in relative_parent.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), "symlink in installer output path")
        cursor.mkdir(mode=0o700, exist_ok=True)
        info = cursor.lstat()
        require(stat.S_ISDIR(info.st_mode) and
                stat.S_IMODE(info.st_mode) == 0o700 and
                info.st_uid == os.getuid(), "installer output parent is not private")
        require(cursor.resolve(strict=True).is_relative_to(real_root),
                "installer output parent escapes private artifacts")
    path = cursor / path.name
    ignored = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", "-q", "--", str(path)],
        check=False, timeout=5)
    require(ignored.returncode == 0, "installer output is not Git-ignored")
    require(not path.exists() and not path.is_symlink(),
            "refusing installer overwrite")
    return path


def write_exclusive(path: Path, data: bytes, mode: int = 0o700) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--foundation-initramfs", required=True, type=Path)
    parser.add_argument("--userspace", required=True, type=Path)
    parser.add_argument("--credentials", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--target")
    args = parser.parse_args()
    if args.execute:
        require(args.target == TARGET, "--execute requires exact target " + TARGET)
    else:
        require(args.target is None, "--target is accepted only with --execute")
    os.umask(0o077)
    parent = source_pins()
    source = derive(args.candidate, args.package, args.foundation_initramfs,
                    args.userspace, args.credentials)
    for program in ("bash", "shellcheck"):
        require(shutil.which(program) is not None,
                "local validator missing: " + program)
    managed = REPO / "artifacts/consys-passive/installer-work"
    managed.mkdir(mode=0o700, parents=True, exist_ok=True)
    managed.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix="derive-", dir=managed) as raw:
        checked = Path(raw) / "install.sh"
        write_exclusive(checked, source.encode("utf-8"))
        subprocess.run(["bash", "-n", str(checked)], check=True, timeout=15)
        subprocess.run(["shellcheck", str(checked)], check=True, timeout=30)
        if args.output is not None:
            write_exclusive(private_output(args.output), source.encode("utf-8"))
        if args.execute:
            parent["recovery_preflight"]()
            receipt_name = "consys-passive-deployment-" + CANDIDATE_SHA256[:16]
            evidence = REPO / "artifacts/device-install-evidence" / receipt_name
            parent["run_installer"]([
                "bash", str(checked), "--target", TARGET,
                "--candidate-dir", str(args.candidate.resolve()),
                "--evidence-dir", str(evidence),
            ])
    print(json.dumps({
        "classification": "installer-derivation-pass",
        "installer_sha256": digest(source.encode("utf-8")),
        "candidate_sha256": CANDIDATE_SHA256,
        "expected_predecessor_sha256": EXPECTED_PREDECESSOR_SHA256,
        "mode": "executed" if args.execute else "local-validation-only",
        "device_action": "boot2-verified-and-shutdown" if args.execute else "none",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
