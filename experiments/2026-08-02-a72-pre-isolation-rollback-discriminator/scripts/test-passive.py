#!/usr/bin/env python3
"""Exercise ABI-v3 rollback capture validation and no-stimulus invariants."""

from __future__ import annotations

import importlib.util
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-passive.py"
REMOTE_PATH = ROOT / "scripts" / "remote-passive-capture.sh"
spec = importlib.util.spec_from_file_location("rollback_passive_validator", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def envelope(first: list[str], second: list[str], identical: str) -> str:
    lines = [
        "experiment=gemian-a72-preiso-rollback-passive",
        "kernel_release=3.18.41+",
        "architecture=aarch64",
        "build_identity=#1 SMP PREEMPT Sun Aug 2 22:29:57 UTC 2026",
        "root=/dev/mmcblk0p29",
        "possible=0-9",
        "present=0-9",
        "observer_path=/proc/mt6797_a72_transition",
        "observer_mode=400",
        "boot_id_before_sha256=" + "a" * 64,
        "state_changing_writes=none",
        "load_workers=0",
        "cpu_online_writes=none",
        "__OBSERVER_FIRST_BEGIN__",
        *first,
        "__OBSERVER_FIRST_END__",
        "__OBSERVER_SECOND_BEGIN__",
        *second,
        "__OBSERVER_SECOND_END__",
        f"observer_first_lines={len(first)}",
        f"observer_second_lines={len(second)}",
        f"observer_snapshots_identical={identical}",
        "cpu8=0",
        "cpu9=0",
        "online=0-7",
        "power=usb:1|status:Charging|capacity:99|health:Good",
        "boot_id_after_sha256=" + "a" * 64,
        "boot_id_stable=yes",
        "runtime_stimulus=none",
        "status=completed",
    ]
    return "\n".join(lines) + "\n"


def payload(event: str, phase: int, occurrence: int) -> str:
    if event == "lifecycle":
        result = 1 if phase == 16 else 0
        return f"result={result} arg0=0x0 arg1=0x0"
    if event == "clock":
        return "pll_con1=0xc1130000 muxsel=0x00000054 ckdiv=0x00042168 status=0 semaphore=0x000f"
    if event == "secure":
        zeros = " ".join(f"r{index}=0x00000000" for index in range(12))
        return f"valid=0xfff stable=1 sentinel_after=0x00000000 {zeros}"
    if event == "dcm":
        return "before=0x00000000 toggle=0x00000000 final=0x00000000 mask=0x0000007f on=0"
    if event == "da9214":
        states = {
            (6, 0): (0, 0, 0x5F),
            (10, 0): (0, 1, 0x5F),
            (11, 0): (1, 1, 0x5F),
            (13, 0): (1, 0, 0x5F),
            (16, 0): (0, 0, 0x5F),
            (16, 1): (0, 0, 0x1F),
        }
        before, after, valid = states[(phase, occurrence)]
        return (
            "page_before=0x80 page_selected=0x80 "
            f"buck_before=0x{before:02x} buck_after=0x{after:02x} "
            f"vsel=0x46 page_after=0x80 status=0 valid=0x{valid:04x}"
        )
    if event == "mutation":
        states = {
            (6, 0): (0x10006218, 0x10132, 0x10132, 0x10132),
            (6, 1): (0x10006290, 0x2, 0x2, 0x2),
            (7, 0): (0x10006218, 0x10132, 0x10133, 0x10133),
            (14, 0): (0x10006290, 0x2, 0x2, 0x2),
            (14, 1): (0x10006218, 0x10133, 0x10132, 0x10132),
            (16, 0): (0x10006218, 0x10132, 0x10132, 0x10132),
            (16, 1): (0x10006290, 0x2, 0x2, 0x2),
        }
        address, before, requested, after = states[(phase, occurrence)]
        return (
            f"address=0x{address:08x} before=0x{before:08x} "
            f"mask=0xffffffff requested=0x{requested:08x} "
            f"after=0x{after:08x} status=0"
        )
    if event == "toprgu":
        states = {
            6: (0, 0),
            9: (0, 1),
            15: (1, 0),
            16: (0, 0),
        }
        before, after = states[phase]
        return (
            f"before=0x{before * 0x800:08x} requested=0x{after * 0x800:08x} "
            f"after=0x{after * 0x800:08x} mask=0x00000800 status=0"
        )
    if event == "spm":
        return (
            "valid=0x3f r0=0x2a00005c r1=0x2a00004c "
            "r2=0x00350c08 r3=0x00350cff r4=0x00010132 r5=0x00000002"
        )
    raise AssertionError(f"unknown event {event}")


def snapshot(state: str, template: list[tuple[str, int]], terminal: int) -> list[str]:
    occurrences: dict[tuple[str, int], int] = {}
    records = []
    for sequence, (event, phase) in enumerate(template, 1):
        key = (event, phase)
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        body = payload(event, phase, occurrence)
        if sequence == len(template) and event == "lifecycle":
            body = f"result={terminal} arg0=0x0 arg1=0x0"
        records.append(
            f"seq={sequence} ns={sequence * 1000} tx=7 event={event} "
            f"phase={phase} target=8 actor=4 online=0x000000ff {body}"
        )
    return [
        f"abi=mt6797-a72-transition-observer-v3 state={state} "
        f"count={len(records)} overflow=0 up_tx=7 down_tx=0",
        *records,
    ]


def rolled() -> list[str]:
    return snapshot("rolled-back", validator.ROLLED_TEMPLATE, 1)


def rejected() -> list[str]:
    full = rolled()
    records = full[1:9] + full[25:30] + [full[30]]
    records[1] = records[1].replace("status=0 semaphore", "status=-16 semaphore")
    records[-1] = records[-1].replace("result=1", "result=3")
    records = [
        line.replace(f"seq={old} ", f"seq={new} ", 1)
        for new, (old, line) in enumerate(
            ((int(item.split(" ", 1)[0].split("=")[1]), item) for item in records),
            1,
        )
    ]
    return [
        "abi=mt6797-a72-transition-observer-v3 state=rejected-prestate "
        "count=14 overflow=0 up_tx=7 down_tx=0",
        *records,
    ]


def orchestration_failure(result: int) -> list[str]:
    records = [
        "seq=1 ns=1000 tx=7 event=lifecycle phase=1 target=8 actor=4 "
        "online=0x000000ff result=0 arg0=0x0 arg1=0x0",
        "seq=2 ns=2000 tx=7 event=lifecycle phase=2 target=8 actor=4 "
        f"online=0x000000ff result={result} arg0=0x0 arg1=0x0",
    ]
    return [
        "abi=mt6797-a72-transition-observer-v3 state=frozen-up-failed "
        "count=2 overflow=0 up_tx=7 down_tx=0",
        *records,
    ]


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation target count changed for {old!r}: {text.count(old)}")
    return text.replace(old, new, 1)


def mutate_line(snapshot_lines: list[str], index: int, old: str, new: str) -> list[str]:
    changed = snapshot_lines.copy()
    changed[index] = replace_once(changed[index], old, new)
    return changed


def reject(label: str, text: str) -> None:
    try:
        validator.validate(text)
    except validator.ValidationError:
        return
    raise AssertionError(f"{label} mutation was accepted")


def main() -> int:
    wait = [
        "abi=mt6797-a72-transition-observer-v3 state=wait-up "
        "count=0 overflow=0 up_tx=0 down_tx=0"
    ]
    result = validator.validate(envelope(wait, wait, "yes"))
    assert result["formal_disposition"] == "preserve-incomplete-no-stimulus"

    exact = rolled()
    accepted = envelope(exact, exact, "yes")
    result = validator.validate(accepted)
    assert result["formal_disposition"] == "accepted-pre-isolation-rollback"
    assert result["owner_transition_validation"] == "passed"

    prestate = rejected()
    result = validator.validate(envelope(prestate, prestate, "yes"))
    assert result["formal_disposition"] == "preserve-prestate-rejection-no-retry"

    fault = exact.copy()
    fault[0] = fault[0].replace("state=rolled-back", "state=fault-retain")
    fault[-1] = fault[-1].replace("result=1", "result=2")
    result = validator.validate(envelope(fault, fault, "yes"))
    assert result["formal_disposition"] == "preserve-fault-retain-reset-recovery"

    for errno, expected in (
        (-114, "EALREADY-pre-latch-one-shot-consumed"),
        (-11, "EAGAIN-observer-latch-not-active"),
    ):
        frozen = orchestration_failure(errno)
        result = validator.validate(envelope(frozen, frozen, "yes"))
        assert result["formal_disposition"] == "reject-latch-orchestration-no-retry"
        assert result["owner_transition_validation"] == "passed-no-owner-terminal"
        assert result["orchestration_failure"] == expected

    reject("ABI drift", accepted.replace("observer-v3", "observer-v2", 1))
    unstable = exact.copy()
    unstable[-1] = unstable[-1].replace("arg1=0x0", "arg1=0x1")
    reject("terminal instability", envelope(exact, unstable, "no"))
    reject("synthetic load", replace_once(accepted, "load_workers=0", "load_workers=2"))
    reject("CPU9 target", accepted.replace("target=8", "target=9", 1))
    reject("CPU online", accepted.replace("online=0x000000ff", "online=0x000001ff", 1))
    reject("host A72 online", replace_once(accepted, "online=0-7", "online=0-8"))
    reject("overflow", accepted.replace("overflow=0 up_tx=7", "overflow=1 up_tx=7", 1))
    reject("down transaction", accepted.replace("down_tx=0", "down_tx=8", 1))
    reject("sequence gap", accepted.replace("seq=2 ", "seq=99 ", 1))
    reject("forbidden isolation phase", accepted.replace("phase=12 ", "phase=17 ", 1))
    reject("missing inverse", accepted.replace("phase=13 ", "phase=10 ", 1))
    bad_da = mutate_line(
        exact,
        18,
        "buck_before=0x00 buck_after=0x00 vsel=0x46",
        "buck_before=0x00 buck_after=0x01 vsel=0x46",
    )
    reject("final DA921x state", envelope(bad_da, bad_da, "yes"))
    bad_spm = mutate_line(
        exact,
        26,
        "r4=0x00010132 r5=0x00000002",
        "r4=0x00010133 r5=0x00000002",
    )
    reject("final SPM state", envelope(bad_spm, bad_spm, "yes"))
    bad_clock = mutate_line(
        exact, 24, "pll_con1=0xc1130000", "pll_con1=0xc1130001"
    )
    reject("clock mismatch", envelope(bad_clock, bad_clock, "yes"))
    bad_terminal = mutate_line(
        exact, 30, "result=1 arg0=0x0 arg1=0x0", "result=2 arg0=0x0 arg1=0x0"
    )
    reject("terminal disposition", envelope(bad_terminal, bad_terminal, "yes"))
    reject("reported stability", replace_once(accepted, "observer_snapshots_identical=yes", "observer_snapshots_identical=no"))
    reject("build identity", replace_once(accepted, "22:29:57", "22:29:58"))

    unsafe_prestate = mutate_line(
        prestate,
        6,
        "address=0x10006218 before=0x00010132 mask=0xffffffff requested=0x00010132 after=0x00010132",
        "address=0x10006218 before=0x00010132 mask=0xffffffff requested=0x00010132 after=0x00010133",
    )
    reject("prestate write", envelope(unsafe_prestate, unsafe_prestate, "yes"))

    remote = REMOTE_PATH.read_text()
    for forbidden in (
        "yes >/dev/null",
        "/sys/devices/system/cpu/cpu8/online >",
        "/sys/devices/system/cpu/cpu9/online >",
        "i2cset",
        "devmem",
        "reboot",
        "poweroff",
        "stress",
    ):
        if forbidden in remote:
            raise AssertionError(f"remote capture contains forbidden action {forbidden!r}")
    first_copy = remote.index('cat "$observer" >"$first"')
    optional_power = remote.index("optional_read /sys/class/power_supply/usb/online")
    if first_copy >= optional_power:
        raise AssertionError("observer is not copied before optional power reporting")
    print(
        "PASS: passive rollback validation, 2 orchestration failures, "
        "and 19 fail-closed/no-stimulus checks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
