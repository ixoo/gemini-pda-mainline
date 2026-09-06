#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive and optionally run the exact reviewed boot2 installer.

The default operation is local derivation and validation only. ``--execute``
is the sole transport/write switch and still inherits every live GPT, block
identity, power, predecessor, readback and shutdown gate from the reviewed A53
installer. No device command is implemented independently here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import shlex
import signal
import stat
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]

BASELINE_INSTALLER = REPO / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/installer.py"
BASELINE_INSTALLER_SHA256 = "ef9cf896f9b62b903b7d16176b5da40096e54cc839c5001fd2f5047638f72a6f"
BASELINE_VALIDATOR = REPO / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/validate-candidate.py"
BASELINE_VALIDATOR_SHA256 = "ef76e8b99aeb94dc56651752855efdb493bdfabbd31fbd91a0cba07f1a7f22bb"
BASELINE_RECEIPT = REPO / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/deployment_receipt.py"
BASELINE_RECEIPT_SHA256 = "a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23"
RECOVERY_HOSTS_SHA256 = "d43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f"
RECOVERY_TOOL_SHA256 = "9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b"
PARTITION_INVENTORY_TOOL_SHA256 = "306062ab82a4e0e173f241e1bfec72960057d67ac957319b378f80c5eaaedf08"
INSTALL_BASE_SHA256 = "deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8"
INSTALL_DERIVER_SHA256 = "9c72675e3043dcf735c8a368800ce9297ca6c343d81283505e7030de82253211"
BOOT2_GUARD_SHA256 = "0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf"
TARGET = "gemini@192.168.1.50"
BOOT2_SIZE = 0x01000000
SHA = re.compile(r"[0-9a-f]{64}")

# The completed authenticated-baseline adapter remains immutable evidence.  The
# TOPRGU deployment deliberately replaces only its historical staging-swap
# predicate after verifying that exact adapter.  The owner accepts that a
# credential-bearing tmpfs page may transiently enter this RAM-only zram; disk
# backed swap, zram writeback, a used zram, and every other swap layout refuse.
TOPRGU_SWAP_POLICY = r'''a53_no_swap() {
    local swap_table row_count canonical node_identity sys_device disk_size
    swap_table="$(cat -- /proc/swaps)" || return 1
    printf '%s\n' "$swap_table" | awk '
        NR == 1 {
            if (NF != 5 || $1 != "Filename" || $2 != "Type" ||
                $3 != "Size" || $4 != "Used" || $5 != "Priority") bad=1
            next
        }
        NR == 2 {
            if (NF != 5 || $1 != "/dev/block/zram0" || $2 != "partition" ||
                $3 != "1930336" || $4 != "0" || $5 != "-1") bad=1
            next
        }
        { bad=1 }
        END { exit (bad || (NR != 1 && NR != 2)) }
    ' || return 1
    row_count="$(printf '%s\n' "$swap_table" | awk 'END {print NR}')" || return 1
    if [[ "$row_count" == 1 ]]; then
        [[ "$(cat -- /proc/swaps)" == "$swap_table" ]]
        return
    fi
    [[ "$row_count" == 2 ]] || return 1
    canonical="$(readlink -f -- /dev/block/zram0)" || return 1
    [[ "$canonical" == /dev/zram0 ]] || return 1
    node_identity="$(stat -Lc '%F %t:%T' -- "$canonical")" || return 1
    [[ "$node_identity" == 'block special file fe:0' ]] || return 1
    sys_device="$(cat -- /sys/class/block/zram0/dev)" || return 1
    disk_size="$(cat -- /sys/class/block/zram0/disksize)" || return 1
    [[ "$sys_device" == 254:0 && "$disk_size" == 1976668160 ]] || return 1
    [[ ! -e /sys/class/block/zram0/backing_dev &&
       ! -L /sys/class/block/zram0/backing_dev &&
       ! -e /sys/block/zram0/backing_dev &&
       ! -L /sys/block/zram0/backing_dev &&
       ! -e /sys/class/block/zram0/writeback_limit_enable &&
       ! -L /sys/class/block/zram0/writeback_limit_enable &&
       ! -e /sys/block/zram0/writeback_limit_enable &&
       ! -L /sys/block/zram0/writeback_limit_enable ]] || return 1
    [[ "$(cat -- /proc/swaps)" == "$swap_table" ]]
}'''

BASELINE_SWAP_POLICY = r'''a53_no_swap() {
    awk 'NR != 1 || NF != 5 || $1 != "Filename" || $2 != "Type" || $3 != "Size" || $4 != "Used" || $5 != "Priority" {bad=1} END {exit (bad || NR != 1)}' /proc/swaps
}'''

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def regular(path: Path, limit: int = 32 * 1024 * 1024) -> bytes:
    path = Path(path)
    info = path.lstat()
    require(not path.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            "unsafe regular input: " + path.name)
    require(info.st_size <= limit, "input exceeds bound: " + path.name)
    return path.read_bytes()


def source_pins() -> None:
    pins = {
        BASELINE_INSTALLER: BASELINE_INSTALLER_SHA256,
        BASELINE_VALIDATOR: BASELINE_VALIDATOR_SHA256,
        BASELINE_RECEIPT: BASELINE_RECEIPT_SHA256,
        REPO / "scripts/collect-device-pstore": RECOVERY_TOOL_SHA256,
        REPO / "scripts/backup-device-mmc": PARTITION_INVENTORY_TOOL_SHA256,
        REPO / "experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh": INSTALL_BASE_SHA256,
        REPO / "experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py": INSTALL_DERIVER_SHA256,
        REPO / "scripts/boot2-device-guard.sh": BOOT2_GUARD_SHA256,
    }
    for path, expected in pins.items():
        require(digest(regular(path, 512 * 1024)) == expected,
                "reviewed deployment source changed: " + str(path.relative_to(REPO)))


def recovery_preflight() -> dict[str, str]:
    """Validate immutable recovery inputs without opening the private key."""
    source_pins()
    host = REPO / "artifacts/credentials/a53-recovery-known_hosts"
    key = REPO / "artifacts/credentials/gemini_ed25519"
    require(digest(regular(host, 16 * 1024)) == RECOVERY_HOSTS_SHA256,
            "recovery host pin changed")
    info = key.lstat()
    require(not key.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
            stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.getuid(),
            "recovery device key metadata changed")
    return {"collector_sha256": RECOVERY_TOOL_SHA256,
            "known_hosts_sha256": RECOVERY_HOSTS_SHA256,
            "device_key": "present-owner-mode-0600-not-read", "result": "pass"}


def replace_once(source: str, old: str, new: str, label: str) -> str:
    require(source.count(old) == 1, "derived installer anchor changed: " + label)
    return source.replace(old, new)


def replace_count(source: str, old: str, new: str, count: int, label: str) -> str:
    require(source.count(old) == count, "derived installer anchors changed: " + label)
    return source.replace(old, new)


def derive(candidate: Path, foundation: Path, userspace: Path,
           expected_predecessor: str, *, base_dtb: Path | None = None,
           credentials: Path | None = None) -> str:
    """Return one complete candidate/predecessor-bound installer shell."""
    source_pins()
    require(SHA.fullmatch(expected_predecessor) is not None,
            "exact predecessor SHA-256 is required")
    require(base_dtb is not None and credentials is not None,
            "complete independent candidate-validation inputs are required")
    candidate = Path(candidate).resolve(strict=True)
    foundation = Path(foundation).resolve(strict=True)
    userspace = Path(userspace).resolve(strict=True)
    base_dtb = Path(base_dtb).resolve(strict=True)
    credentials = Path(credentials).resolve(strict=True)
    padded = regular(candidate / "boot2-padded.img")
    manifest_raw = regular(candidate / "candidate.json", 4 * 1024 * 1024)
    manifest = json.loads(manifest_raw)
    padded_sha = digest(padded)
    require(len(padded) == BOOT2_SIZE and manifest.get("padded_sha256") == padded_sha,
            "candidate size/checksum changed")
    require(candidate.name == "candidate-" + padded_sha,
            "candidate directory must use the full padded SHA-256")
    require(manifest.get("physical_admission") is False and
            manifest.get("secret_bearing") is True,
            "candidate preparation/admission state changed")

    # Verify the historical Python before executing it. Its derivation already
    # embeds the complete reviewed installer and guard sources named above.
    baseline = runpy.run_path(str(BASELINE_INSTALLER))
    baseline_derive = baseline["derive"]
    baseline_globals = baseline_derive.__globals__
    historical_library = baseline_globals["STAGE_LIBRARY"]
    historical_stage_function = baseline_globals["STAGE_FUNCTION"]
    require(historical_library.count(BASELINE_SWAP_POLICY) == 1,
            "historical staging-swap policy changed")
    active_library = historical_library.replace(BASELINE_SWAP_POLICY,
                                                TOPRGU_SWAP_POLICY)
    require(historical_stage_function.count(historical_library) == 1,
            "historical staging function changed")
    active_stage_function = historical_stage_function.replace(historical_library,
                                                              active_library)
    # The historical deriver reads these two immutable templates from its own
    # execution globals.  Override them only for this synchronous derivation,
    # and restore them even if a pin or text anchor refuses.
    baseline_globals["STAGE_LIBRARY"] = active_library
    baseline_globals["STAGE_FUNCTION"] = active_stage_function
    try:
        source = baseline_derive(
            baseline["pinned_sources"](), REPO, candidate, foundation, userspace)
    finally:
        baseline_globals["STAGE_LIBRARY"] = historical_library
        baseline_globals["STAGE_FUNCTION"] = historical_stage_function
    require(source.count("a53_no_swap") == 8,
            "derived staging-swap call inventory changed")
    source = source.replace("a53_no_swap", "toprgu_staging_swap_policy")
    source = replace_count(source, "stat swapon sync uname", "stat sync uname", 1,
                           "unused swap utility requirement")
    require("a53_no_swap" not in source and "swapoff" not in source and
            "swapon" not in source,
            "derived installer contains obsolete or mutating swap operation")

    new_validator = HERE / "scripts/validate-candidate.py"
    validator_sha = digest(regular(new_validator, 512 * 1024))
    source = replace_count(source, str(BASELINE_VALIDATOR), str(new_validator), 2,
                           "candidate validator path")
    source = replace_once(source, BASELINE_VALIDATOR_SHA256, validator_sha,
                          "candidate validator digest")
    old_invocation = re.compile(
        re.escape("python3 " + str(new_validator)) +
        r"\s+--foundation\s+\S+\s+--userspace\s+\S+\s+--candidate \"\$candidate_dir\"")
    foundation_initramfs = foundation / "gemini-pwrap-reset-serviceability-initramfs.img"
    validation_command = ("python3 " + shlex.quote(str(new_validator)) +
                          ' --candidate "$candidate_dir" --base-dtb ' + shlex.quote(str(base_dtb)) +
                          " --foundation-initramfs " + shlex.quote(str(foundation_initramfs)) +
                          " --userspace " + shlex.quote(str(userspace)) +
                          " --credentials " + shlex.quote(str(credentials)))
    source, count = old_invocation.subn(validation_command, source)
    require(count == 1, "derived validator invocation changed")

    new_receipt = HERE / "scripts/deployment_receipt.py"
    receipt_sha = digest(regular(new_receipt, 512 * 1024))
    source = replace_count(source, str(BASELINE_RECEIPT), str(new_receipt), 2,
                           "deployment receipt parser path")
    source = replace_once(source, BASELINE_RECEIPT_SHA256, receipt_sha,
                          "deployment receipt parser digest")

    receipt_name = "toprgu-minimal-restart-deployment-" + padded_sha[:16]
    require(source.count("a53-authenticated-baseline-deployment-2") == 3,
            "deployment receipt-name anchors changed")
    source = source.replace("a53-authenticated-baseline-deployment-2", receipt_name)
    require(source.count("a53-authenticated-baseline") == 2,
            "deployment experiment anchors changed")
    source = source.replace("a53-authenticated-baseline",
                            "2026-09-06-mt6797-toprgu-minimal-restart")

    candidate_line = "readonly CANDIDATE_SHA256=" + padded_sha + "\n"
    source = replace_once(
        source, candidate_line,
        candidate_line + "readonly EXPECTED_PREDECESSOR_SHA256=" + expected_predecessor + "\n",
        "candidate constant")
    receipt_invocation = (
        "python3 " + str(new_receipt) + " --candidate-sha256 " + padded_sha +
        " --candidate-manifest-sha256 " + digest(manifest_raw) +
        ' --receipt "$summary"')
    source = replace_once(
        source, receipt_invocation,
        receipt_invocation + " --expected-predecessor-sha256 " + expected_predecessor,
        "deployment receipt predecessor binding")
    predecessor_line = (
        'already_current="$(single_value already_current "$probe_output")" || '
        "die 'invalid current-state evidence'\n")
    predecessor_gate = predecessor_line + (
        '[[ "$already_current" == yes || "$predecessor_sha256" == '
        '"$EXPECTED_PREDECESSOR_SHA256" ]] ||\n'
        "\tdie 'boot2 predecessor differs from the admitted exact checksum'\n")
    source = replace_once(source, predecessor_line, predecessor_gate,
                          "exact predecessor admission")

    require(source.count('of="$target"') == 1,
            "derived installer write inventory changed")
    for token in (
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
    root = REPO / "artifacts"
    require(path.is_relative_to(root) and path.parent != root,
            "derived installer must remain below a private artifacts child")
    for parent in (root, path.parent):
        require(not parent.is_symlink(), "symlink in installer output path")
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent.chmod(0o700)
        info = parent.stat()
        require(stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
                "installer output parent is not private")
    ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "--", str(path)],
                             check=False, timeout=5)
    require(ignored.returncode == 0, "installer output is not Git-ignored")
    require(not path.exists() and not path.is_symlink(), "refusing installer overwrite")
    return path


def write_exclusive(path: Path, data: bytes, mode: int = 0o700) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def run_installer(command: list[str]) -> None:
    """Run one complete installer process group inside a fixed outer bound."""
    process = subprocess.Popen(command, start_new_session=True)
    received: list[int] = []
    previous: dict[int, object] = {}

    def forward(number, _frame):
        received.append(number)
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            pass

    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.signal(number, forward)
    try:
        try:
            status = process.wait(timeout=360)
        except subprocess.TimeoutExpired:
            forward(signal.SIGTERM, None)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            raise ValueError("deployment deadline expired; inspect private evidence") from None
        require(not received, "deployment interrupted; inspect private evidence")
        if status:
            raise subprocess.CalledProcessError(status, command)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--foundation", required=True, type=Path)
    parser.add_argument("--userspace", required=True, type=Path)
    parser.add_argument("--base-dtb", required=True, type=Path)
    parser.add_argument("--credentials", required=True, type=Path)
    parser.add_argument("--expected-predecessor-sha256", required=True)
    parser.add_argument("--output", type=Path,
                        help="new ignored private path for the derived installer")
    parser.add_argument("--execute", action="store_true",
                        help="run the derived installer after all local gates")
    parser.add_argument("--target")
    args = parser.parse_args()
    if args.execute:
        require(args.target == TARGET, "--execute requires exact target " + TARGET)
    else:
        require(args.target is None, "--target is accepted only with --execute")
    os.umask(0o077)

    validator_path = HERE / "scripts/validate-candidate.py"
    validator_raw = regular(validator_path, 512 * 1024)
    validator = runpy.run_path(str(validator_path))
    foundation_initramfs = (args.foundation.resolve(strict=True) /
                            "gemini-pwrap-reset-serviceability-initramfs.img")
    validator["validate"](args.candidate.resolve(strict=True),
                          base_dtb=args.base_dtb.resolve(strict=True),
                          foundation_initramfs=foundation_initramfs.resolve(strict=True),
                          userspace=args.userspace.resolve(strict=True),
                          credentials=args.credentials.resolve(strict=True))
    require(digest(regular(validator_path, 512 * 1024)) == digest(validator_raw),
            "candidate validator changed during validation")
    source = derive(args.candidate, args.foundation, args.userspace,
                    args.expected_predecessor_sha256,
                    base_dtb=args.base_dtb, credentials=args.credentials)

    for program in ("bash", "shellcheck"):
        require(shutil.which(program) is not None, "local validator missing: " + program)
    managed = REPO / "artifacts/toprgu/installer-work"
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
            manifest = json.loads(regular(args.candidate / "candidate.json", 4 * 1024 * 1024))
            receipt_name = "toprgu-minimal-restart-deployment-" + manifest["padded_sha256"][:16]
            evidence = REPO / "artifacts/device-install-evidence" / receipt_name
            run_installer(["bash", str(checked), "--target", TARGET,
                           "--candidate-dir", str(args.candidate.resolve()),
                           "--evidence-dir", str(evidence)])
    print(json.dumps({"classification": "installer-derivation-pass",
                      "installer_sha256": digest(source.encode("utf-8")),
                      "mode": "executed" if args.execute else "local-validation-only",
                      "device_action": "boot2-verified-and-shutdown" if args.execute else "none"},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
