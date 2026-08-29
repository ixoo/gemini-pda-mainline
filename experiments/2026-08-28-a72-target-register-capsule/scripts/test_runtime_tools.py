#!/usr/bin/env python3
"""Validate target-register deployment and observation contracts."""

from __future__ import annotations

import hashlib
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

import validate_capture as capsule


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parent.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
VALIDATOR = SCRIPT_DIR / "validate_capture.py"
PLAN = EXPERIMENT / "results/runtime-decision-map-20260828.txt"
PSTORE = REPO_ROOT / "scripts/collect-device-pstore"
PARENT_INSTALLER = (
    EXPERIMENT.parent / "2026-08-03-a72-scheduler-context/scripts/install-boot2.sh"
)
BASE_INSTALLER = (
    EXPERIMENT.parent / "2026-07-29-da921x-probe-isolation/scripts/install-boot2.sh"
)
PINS = (
    "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60",
    "f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f",
    "d3a2d9f30d36e9227abf327af27e52c418461236e00a41a705f4514bdfbfe562",
    "gemian-a72-target-register-capsule-d4ae9ee1b2f7",
)
REJECTIONS = {"installer": 0, "capture": 0}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_installer_rejection(source: str, token: str) -> None:
    assignment = 'script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"'
    require(source.count(assignment) == 1, "installer script-dir assignment changed")
    mutated = source.replace(token, "0" * len(token), 1).replace(
        assignment,
        f"script_dir={shlex.quote(str(SCRIPT_DIR))}",
        1,
    )
    with tempfile.TemporaryDirectory(prefix="a72-regcap-installer-") as temporary:
        wrapper = Path(temporary) / "install-boot2.sh"
        wrapper.write_text(mutated, encoding="utf-8")
        wrapper.chmod(0o700)
        result = subprocess.run(
            [str(wrapper), "--help"], capture_output=True, text=True, check=False
        )
    require(result.returncode == 2, f"installer mutation ran: {token}")
    require(
        "derived installer lacks:" in result.stderr and token in result.stderr,
        f"installer mutation failed at the wrong boundary: {token}",
    )
    REJECTIONS["installer"] += 1


def snapshot_mutation(text: str, mutate: object) -> str:
    lines = text.splitlines()
    begin = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("capsule_trace_snapshot_begin")
    )
    end = next(i for i, line in enumerate(lines) if line.startswith("capsule_trace_snapshot_end"))
    payload = lines[begin + 1 : end]
    assert callable(mutate)
    changed = mutate(list(payload))
    lines[begin] = f"capsule_trace_snapshot_begin sequence=1 lines={len(changed)}"
    lines[begin + 1 : end] = changed
    return "\n".join(lines) + "\n"


def expect_capture_rejection(name: str, text: str, reason: str) -> None:
    try:
        capsule.analyze_capture_text(text)
    except capsule.CaptureError as error:
        require(reason in str(error), f"{name} rejected for wrong reason: {error}")
        REJECTIONS["capture"] += 1
        return
    raise AssertionError(f"capture mutation accepted: {name}")


def payload_only(text: str) -> str:
    lines = text.splitlines()
    begin = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("capsule_trace_snapshot_begin")
    )
    end = next(i for i, line in enumerate(lines) if line.startswith("capsule_trace_snapshot_end"))
    return "\n".join(lines[begin + 1 : end]) + "\n"


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    validator = VALIDATOR.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    require(
        sha256(PARENT_INSTALLER)
        == "29236d880bf33377d77eee66183ad682016b1769ef0b541f519bdb3e90a503b3",
        "scheduler installer changed",
    )
    require(
        sha256(BASE_INSTALLER)
        == "0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7",
        "guarded base installer changed",
    )
    require(
        sha256(PSTORE)
        == "9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b",
        "changed-cycle pstore helper changed",
    )
    for token in PINS:
        require(installer.count(token) == 2, f"installer pin count changed: {token}")
        expect_installer_rejection(installer, token)
    for token in (
        "scheduler installer changed",
        "GEMINI_A72_REGCAP_PARENT_SCRIPT_DIR",
        "2026-08-28-a72-target-register-capsule",
        ".gemian-a72-register-capsule",
    ):
        require(token in installer, f"installer lacks: {token}")
    help_text = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    ).stdout
    for token in (
        "target-register capsule candidate",
        "without creating a partition",
        "matching full post-write readback",
        "shuts the device down cleanly",
    ):
        require(token in help_text, f"installer help lacks: {token}")
    base = BASE_INSTALLER.read_text(encoding="utf-8")
    for token in (
        "live GPT does not have exactly one boot2 row",
        "boot2 is mounted or not a block device",
        "fresh_predecessor_backup=no",
        "independent full readback checksum mismatch",
        "temporary_readback_removed=yes",
        "sudo -n systemctl poweroff",
        "shutdown=confirmed-unreachable",
    ):
        require(token in base, f"base installer safety gate changed: {token}")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require(
        "a72-target-register-capsule-attempt-N" in live_help,
        "live output contract changed",
    )
    device_program = live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    for forbidden in (
        r"/dev/mmc",
        r"/dev/block",
        r"/sys/devices/system/cpu/cpu[89]/online\s*>",
        r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b",
    ):
        require(
            re.search(forbidden, device_program) is None,
            f"live device program has forbidden operation: {forbidden}",
        )
    for token in (
        "gemini-a72-(pair-v[67] result=(pass|fault)|sc-phase|regcap-v1)",
        'regcap_lines" -eq 8',
        "regcap_terminal_line_",
        "__A72_REGCAP_TERMINAL_CAPTURED__",
        "evidence_priority=changed-cycle-pstore-primary",
        "usb_capture_role=read-only-secondary",
        "device_storage_writes=none",
        'python3 "$validator" --capture "$output"',
    ):
        require(token in live, f"live collector lacks: {token}")
    for token in (
        "successful trace does not have 43 records",
        "capsule identity mismatch",
        "capsule result disagrees with its exact field vector",
        "terminal lacks exactly eight capsule records",
        "passing terminal lacks ordered CPU8/CPU9 slots",
        "complete snapshots do not preserve one monotonic event history",
        "raw-terminal",
        "--raw-kernel-log",
    ):
        require(token in validator, f"validator lacks: {token}")

    complete = capsule.render_terminal_capture()
    result = capsule.analyze_capture_text(complete)
    require(result["capture_class"] == "terminal", "complete terminal misclassified")
    require(result["phase_records"] == 43, "complete phase count changed")
    require(result["capsule_records"] == 8, "complete capsule count changed")
    require(result["capsule_pass_slots"] == 2, "complete pass count changed")
    raw = capsule.analyze_capture_text(
        capsule.raw_capture(payload_only(complete)), raw_log=True
    )
    require(raw["capture_class"] == "raw-terminal", "raw terminal misclassified")

    prefix_lines = payload_only(complete).splitlines()[:-3]
    prefix = capsule.analyze_capture_text(
        capsule.raw_capture("\n".join(prefix_lines)), raw_log=True
    )
    require(prefix["capture_class"] == "capsule-prefix", "raw prefix misclassified")
    require(prefix["capsule_records"] == 5, "raw prefix capsule count changed")

    expect_capture_rejection(
        "duplicate-terminator",
        complete + "\n" + capsule.TERMINATOR + "\n",
        "terminator is duplicated",
    )
    metadata_lines = complete.splitlines()
    metadata_index = next(
        i for i, line in enumerate(metadata_lines) if line.startswith("regcap_terminal_line_1=")
    )
    metadata_lines[metadata_index] = metadata_lines[metadata_index].replace("cpu=8", "cpu=9", 1)
    expect_capture_rejection(
        "metadata-mismatch", "\n".join(metadata_lines), "metadata differs"
    )
    expect_capture_rejection(
        "missing-capture-phase",
        snapshot_mutation(
            complete,
            lambda lines: [line for line in lines if "cpu=8 phase=task-capture-after" not in line],
        ),
        "task phases are not an exact source-order prefix",
    )

    def terminal_before_exit(lines: list[str]) -> list[str]:
        exit_index = next(i for i, line in enumerate(lines) if "phase=run-exit" in line)
        pair_index = next(i for i, line in enumerate(lines) if "gemini-a72-pair-v6" in line)
        pair = lines.pop(pair_index)
        lines.insert(exit_index, pair)
        return lines

    expect_capture_rejection(
        "terminal-before-run-exit",
        snapshot_mutation(complete, terminal_before_exit),
        "pair-v6/pair-v7 terminals are not adjacent",
    )

    def swap_first_capsules(lines: list[str]) -> list[str]:
        indexes = [i for i, line in enumerate(lines) if "gemini-a72-regcap-v1" in line]
        lines[indexes[0]], lines[indexes[1]] = lines[indexes[1]], lines[indexes[0]]
        return lines

    expect_capture_rejection(
        "capsule-reorder",
        snapshot_mutation(complete, swap_first_capsules),
        "part order changed",
    )

    def duplicate_capsule(lines: list[str]) -> list[str]:
        record = next(line for line in lines if "gemini-a72-regcap-v1" in line)
        lines.append(record)
        return lines

    expect_capture_rejection(
        "capsule-duplicate",
        snapshot_mutation(complete, duplicate_capsule),
        "more than eight",
    )
    cpu8_identity = re.search(r"identity=([0-9a-f]{16})", capsule.synthetic_capsule(8)[0])
    assert cpu8_identity is not None
    old_identity = cpu8_identity.group(1)
    new_identity = ("0" if old_identity[0] != "0" else "1") + old_identity[1:]
    expect_capture_rejection(
        "identity-recompute",
        complete.replace(old_identity, new_identity),
        "identity mismatch",
    )
    aa64 = capsule.synthetic_capsule(8)[1]
    expect_capture_rejection(
        "mixed-identity",
        complete.replace(aa64, aa64.replace(old_identity, new_identity)),
        "mixed identities",
    )
    expect_capture_rejection(
        "malformed-width",
        complete.replace("midr=410fd083", "midr=410fd08"),
        "field malformed: midr",
    )
    expect_capture_rejection(
        "false-pass-vector",
        complete.replace("mpidr=0000000000000200", "mpidr=0000000000000201"),
        "identity mismatch",
    )

    def remove_pairs(lines: list[str]) -> list[str]:
        return [line for line in lines if "gemini-a72-pair-v" not in line]

    expect_capture_rejection(
        "capsule-without-pair",
        snapshot_mutation(complete, remove_pairs),
        "without its pair terminal",
    )
    expect_capture_rejection(
        "mixed-result",
        complete.replace(
            capsule.synthetic_capsule(8)[2],
            capsule.synthetic_capsule(8)[2].replace("result=pass", "result=fault"),
        ),
        "mixed result fields",
    )

    for token in (
        "f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f",
        "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60",
        "fresh_predecessor_backup=no",
        "Screen color, framebuffer availability",
        "43 unique phase records",
        "TWO-CAPSULE PASS",
        "repeat this artifact unchanged",
        "It does not publish",
    ):
        require(token in plan, f"runtime decision map lacks: {token}")

    print("validation=a72-target-register-runtime-tools")
    print(f"installer_mutations={REJECTIONS['installer']}-rejected")
    print(f"capture_mutations={REJECTIONS['capture']}-rejected")
    print("raw_pstore_terminal=pass")
    print("live_terminal=pass")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
