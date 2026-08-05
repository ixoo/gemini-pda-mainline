#!/usr/bin/env python3
"""Validate kthread-unpark deployment and observation contracts."""

import hashlib
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import validate_phase_capture as phase_capture


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parent.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
PSTORE = REPO_ROOT / "scripts" / "collect-device-pstore"
PLAN = (
    EXPERIMENT
    / "results"
    / "runtime-decision-map-unpark-20260804.txt"
)
PHASE_PATCH = (
    EXPERIMENT
    / "patches"
    / "0002-diagnostic-add-A72-scheduler-phase-attribution.patch"
)
SCHEDULER_PATCH = (
    EXPERIMENT
    / "patches"
    / "0001-diagnostic-add-bounded-A72-scheduler-context-execution.patch"
)
UNPARK_PATCH = (
    EXPERIMENT
    / "patches"
    / "0003-diagnostic-unpark-A72-scheduler-context-tasks.patch"
)
PAIR5 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-multiline-integrity"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)
PINS = (
    ("2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8", 2),
    ("5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5", 2),
    ("9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5", 2),
    ("gemian-a72-scheduler-unpark-f3e235f3c196", 2),
)
REJECTION_COUNTS = {"installer": 0, "marker": 0, "capture": 0}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_installer_identity_rejection(installer: str, token: str) -> None:
    """Execute one mutated wrapper and require its derived-output guard."""
    script_dir_assignment = (
        'script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"'
    )
    require(
        installer.count(script_dir_assignment) == 1,
        "installer script-dir assignment changed",
    )
    mutated = installer.replace(token, "0" * len(token), 1).replace(
        script_dir_assignment,
        f"script_dir={shlex.quote(str(SCRIPT_DIR))}",
        1,
    )
    with tempfile.TemporaryDirectory(
        prefix=".runtime-installer-test."
    ) as temporary:
        wrapper = Path(temporary) / "install-boot2.sh"
        wrapper.write_text(mutated, encoding="utf-8")
        wrapper.chmod(0o700)
        result = subprocess.run(
            [str(wrapper), "--help"], capture_output=True, text=True, check=False
        )
    require(result.returncode == 2, f"installer identity mutation ran: {token}")
    require(
        "derived installer lacks:" in result.stderr and token in result.stderr,
        f"installer identity mutation failed at the wrong boundary: {token}",
    )
    REJECTION_COUNTS["installer"] += 1


def expect_marker_rejection(name: str, records: list[tuple[int | None, str]]) -> None:
    try:
        phase_capture.validate_success_sequence(records)
    except phase_capture.CaptureError:
        REJECTION_COUNTS["marker"] += 1
        return
    raise AssertionError(f"marker mutation accepted: {name}")


def expect_capture_rejection(
    name: str, capture: str, expected_reason: str | None = None
) -> None:
    try:
        phase_capture.analyze_capture_text(capture)
    except phase_capture.CaptureError as error:
        if expected_reason is not None and expected_reason not in str(error):
            raise AssertionError(
                f"capture mutation rejected for the wrong reason: {name}: {error}"
            ) from error
        REJECTION_COUNTS["capture"] += 1
        return
    raise AssertionError(f"capture mutation accepted: {name}")


def terminal_capture(
    records: list[tuple[int | None, str]],
    result: str = "pass",
    pair6_result: str = "pass",
) -> str:
    pair6 = phase_capture.synthetic_pair_line(6, pair6_result)
    pair7 = phase_capture.synthetic_pair_line(
        7, result, parent_pass=int(bool(records))
    )
    snapshot = phase_capture.render_snapshot(
        1, records, pair_result=result, pair6_result=pair6_result
    )
    if result == "fault":
        for cpu in (8, 9):
            if (None, f"unpark{cpu}-after") in records:
                snapshot = snapshot.replace(
                    f"sc_unpark{cpu}=0", f"sc_unpark{cpu}=1"
                )
                pair7 = pair7.replace(
                    f"sc_unpark{cpu}=0", f"sc_unpark{cpu}=1", 1
                )
    return "\n".join(
        (
            snapshot,
            f"pair6_terminal_line={pair6}",
            f"pair7_terminal_line={pair7}",
            phase_capture.TERMINATOR,
        )
    )


def unterminated_terminal_capture(
    records: list[tuple[int | None, str]],
    result: str = "pass",
    pair6_result: str = "pass",
) -> str:
    """Remove only host metadata/terminator after one complete pair snapshot."""
    return terminal_capture(records, result, pair6_result).split(
        "\npair6_terminal_line=", 1
    )[0]


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    phase_patch = PHASE_PATCH.read_text(encoding="utf-8")
    scheduler_patch = SCHEDULER_PATCH.read_text(encoding="utf-8")
    unpark_patch = UNPARK_PATCH.read_text(encoding="utf-8")
    validator_source = (SCRIPT_DIR / "validate_phase_capture.py").read_text(
        encoding="utf-8"
    )
    require(
        hashlib.sha256((PAIR5 / "scripts/install-boot2.sh").read_bytes()).hexdigest()
        == "a2a3f292f0bb857be0251c7bacabecfa9157b2034d3a7ecc1ccd6b5541b672c9",
        "pair-v5 installer changed",
    )
    require(
        hashlib.sha256(BASE_INSTALLER.read_bytes()).hexdigest()
        == "0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7",
        "guarded base installer changed",
    )
    require(
        hashlib.sha256(UNPARK_PATCH.read_bytes()).hexdigest()
        == "7b05002ff89f53a15e1eeb7d3b9588ac08443902626da4b706045d418513f486",
        "unpark patch changed",
    )
    pstore_source = PSTORE.read_text(encoding="utf-8")
    require(
        hashlib.sha256(PSTORE.read_bytes()).hexdigest()
        == "9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b",
        "changed-cycle pstore helper changed",
    )
    pstore_help = subprocess.run(
        [str(PSTORE), "--help"], check=True, capture_output=True, text=True
    ).stdout
    for token in (
        "--wait-for-cycle",
        "--wait-seconds N",
        "Require SSH to go down and return before capture",
        "The capture does not write or delete pstore entries",
        "Waiting for $target to remain disconnected across two probes",
        "known-good OS and a new boot ID",
        "Pstore entries and partitions were not modified or removed",
    ):
        require(
            token in pstore_help or token in pstore_source,
            f"pstore helper contract lacks: {token}",
        )

    for token, count in PINS:
        require(installer.count(token) == count, f"installer pin count changed: {token}")
        expect_installer_identity_rejection(installer, token)
    for token in (
        "EXPECTED_PREDECESSOR_SHA256=2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8",
        "CANDIDATE_SHA256=5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5",
        "ARTIFACT_MANIFEST_SHA256=9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5",
        "ARTIFACT_NAME=gemian-a72-scheduler-unpark-f3e235f3c196",
        "source pair-v5 installer changed",
        "GEMINI_A72_SCHEDULER_SCRIPT_DIR",
    ):
        require(token in installer, f"installer derivation lacks: {token}")

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
    help_text = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    ).stdout
    require("scheduler kthread-unpark" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-scheduler-unpark-attempt-N" in live_help, "live output changed")
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
        "gemini-a72-sc-phase",
        "gemini-a72-pair-v6 result=(pass|fault)",
        "gemini-a72-pair-v7 result=(pass|fault)",
        "phase_trace_snapshot_begin sequence=%s lines=%s",
        "phase_trace_snapshot_end sequence=%s",
        'if [ "$i" -eq 0 ]; then printf \'\\n\'; fi',
        "validate_phase_capture.py",
        'python3 "$phase_validator" --capture "$output"',
        "evidence_priority=changed-cycle-pstore-primary",
        "usb_capture_role=read-only-secondary",
        "phase_capture_class=phase-prefix",
        "sc_iterations=262144 sc_rescheds=64",
        "sc_task8=-?[0-9]+ sc_task9=-?[0-9]+",
        "sc_unpark8=-?[0-9]+ sc_unpark9=-?[0-9]+",
        "sc_readywait8=-?[0-9]+ sc_readywait9=-?[0-9]+",
        "sc_startwait8=-?[0-9]+ sc_startwait9=-?[0-9]+",
        "sc_done8=[0-9]+ sc_done9=[0-9]+ sc_ready=[0-9]+ sc_finished=[0-9]+",
        "sc_hash8=[0-9a-f]{16} sc_hash9=[0-9a-f]{16}",
        "__A72_SCHEDULER_UNPARK_TERMINAL_CAPTURED__",
        "validation=a72-scheduler-unpark-terminal-capture-pass",
        "validation=a72-scheduler-unpark-prefix-structure-pass",
        "validation=a72-scheduler-unpark-transport-truncated-preserved",
    ):
        require(token in live, f"live collector lacks: {token}")
    for legacy in (
        "sc_wake8",
        "sc_wake9",
        "phase=wake8",
        "phase=wake9",
        "__A72_SCHEDULER_PHASE_TERMINAL_CAPTURED__",
    ):
        require(legacy not in live, f"live collector retains legacy token: {legacy}")
    for legacy in ("sc_wake8", "sc_wake9", '"wake8-before"', '"wake9-before"'):
        require(
            legacy not in validator_source,
            f"capture validator retains legacy token: {legacy}",
        )
    for token in (
        "snapshot sequence is not contiguous from one",
        "snapshot payload line count changed",
        "does not contain exactly one phase-marker occurrence",
        "parent phase history is not a prefix of a reachable source path",
        "task phases are not an exact source-order prefix",
        "complete snapshots do not preserve one monotonic event history",
        "pair-v6/pair-v7 terminals are not the adjacent final events",
        "terminal field count changed",
        "terminal metadata differs from the latest complete snapshot",
        "successful trace does not have 39 records",
        "transport-truncated-valid-snapshot",
    ):
        require(token in validator_source, f"capture validator lacks: {token}")

    task_source_phases = re.findall(
        r'^\+\s*pr_emerg\("gemini-a72-sc-phase cpu=%d phase=([a-z0-9-]+)\\n"',
        phase_patch,
        flags=re.MULTILINE,
    )
    phase_parent_source_phases = re.findall(
        r'^\+\s*pr_emerg\("gemini-a72-sc-phase phase=([a-z0-9-]+)\\n"',
        phase_patch,
        flags=re.MULTILINE,
    )
    removed_parent_phases = re.findall(
        r'^-\s*pr_emerg\("gemini-a72-sc-phase phase=([a-z0-9-]+)\\n"',
        unpark_patch,
        flags=re.MULTILINE,
    )
    added_parent_phases = re.findall(
        r'^\+\s*pr_emerg\("gemini-a72-sc-phase phase=([a-z0-9-]+)\\n"',
        unpark_patch,
        flags=re.MULTILINE,
    )
    require(
        tuple(removed_parent_phases)
        == ("wake8-before", "wake8-after", "wake9-before", "wake9-after"),
        "unpark patch removed phase inventory changed",
    )
    require(
        tuple(added_parent_phases)
        == ("unpark8-before", "unpark8-after", "unpark9-before", "unpark9-after"),
        "unpark patch added phase inventory changed",
    )
    phase_replacements = dict(zip(removed_parent_phases, added_parent_phases))
    parent_source_phases = [
        phase_replacements.get(phase, phase) for phase in phase_parent_source_phases
    ]
    source_phases = parent_source_phases + task_source_phases
    require(len(source_phases) == 31, "phase source marker count changed")
    require(len(set(source_phases)) == 31, "phase source markers are not unique")
    require(
        tuple(parent_source_phases) == phase_capture.PARENT_PHASES,
        "parent phase source order changed",
    )
    require(
        tuple(task_source_phases) == phase_capture.TASK_PHASES,
        "task phase source order changed",
    )

    removed_pair7 = re.search(
        r'^-\s*pr_emerg\("gemini-a72-pair-v7 result=%s ([^"\\]+)\\n"',
        unpark_patch,
        flags=re.MULTILINE,
    )
    require(removed_pair7 is not None, "legacy pair-v7 terminal is absent")
    require(
        "sc_wake8=%d sc_wake9=%d" in removed_pair7.group(1)
        and "sc_unpark" not in removed_pair7.group(1),
        "legacy pair-v7 terminal schema changed",
    )
    for version, result_expression in ((6, "pass"), (7, "%s")):
        terminal_source = scheduler_patch if version == 6 else unpark_patch
        line_prefix = r"^[ +]\s*" if version == 6 else r"^\+\s*"
        terminal_matches = re.findall(
            rf'{line_prefix}pr_emerg\("gemini-a72-pair-v{version} '
            rf'result={result_expression} ([^"\\]+)\\n"',
            terminal_source,
            flags=re.MULTILINE,
        )
        require(
            len(terminal_matches) == 1,
            f"pair-v{version} source terminal is absent or ambiguous",
        )
        source_fields = []
        source_exact = {}
        source_hex = set()
        for token in terminal_matches[0].split():
            name, separator, value = token.partition("=")
            require(separator == "=" and bool(value), "source terminal token malformed")
            source_fields.append(name)
            if value == "%016llx":
                source_hex.add(name)
            elif not value.startswith("%"):
                source_exact[name] = value
            else:
                require(value == "%d", f"source terminal format changed: {name}")
        require(
            tuple(source_fields) == phase_capture.PAIR_FIELDS[version],
            f"pair-v{version} parser field schema differs from source",
        )
        require(
            source_exact == phase_capture.PAIR_EXACT[version],
            f"pair-v{version} parser fixed fields differ from source",
        )
        require(
            source_hex == phase_capture.PAIR_HEX[version],
            f"pair-v{version} parser hexadecimal fields differ from source",
        )

    valid = phase_capture.valid_complete_trace()
    require(len(valid) == 39, "successful runtime marker count changed")
    phase_capture.validate_success_sequence(valid)
    phase_capture.validate_structural_sequence(valid[:18])

    alternate = valid.copy()
    cpu8_pre_release = alternate[6:9]
    del alternate[6:9]
    alternate[11:11] = cpu8_pre_release
    phase_capture.validate_success_sequence(alternate)
    early_cpu8 = valid.copy()
    early_cpu8_prefix = [
        (8, "task-ready-before"),
        (8, "task-ready-after"),
        (8, "task-start-wait-before"),
    ]
    early_cpu8 = [record for record in early_cpu8 if record not in early_cpu8_prefix]
    unpark8_before = early_cpu8.index((None, "unpark8-before")) + 1
    early_cpu8[unpark8_before:unpark8_before] = early_cpu8_prefix
    phase_capture.validate_success_sequence(early_cpu8)

    mutations: dict[str, list[tuple[int | None, str]]] = {}
    mutations["missing-marker"] = valid[:-1]
    mutations["unknown-phase"] = valid.copy()
    mutations["unknown-phase"][6] = (8, "task-unknown-before")
    for cpu in (8, 9):
        for boundary in ("before", "after"):
            name = f"legacy-wake{cpu}-{boundary}-marker"
            mutations[name] = valid.copy()
            legacy_index = mutations[name].index(
                (None, f"unpark{cpu}-{boundary}")
            )
            mutations[name][legacy_index] = (None, f"wake{cpu}-{boundary}")
    mutations["duplicate-marker"] = valid[:7] + [valid[6]] + valid[7:]
    mutations["parent-reversal"] = valid.copy()
    mutations["parent-reversal"][0], mutations["parent-reversal"][1] = (
        mutations["parent-reversal"][1],
        mutations["parent-reversal"][0],
    )
    mutations["task-reversal"] = valid.copy()
    mutations["task-reversal"][7], mutations["task-reversal"][8] = (
        mutations["task-reversal"][8],
        mutations["task-reversal"][7],
    )
    mutations["wrong-task-cpu"] = valid.copy()
    mutations["wrong-task-cpu"][6] = (7, "task-ready-before")
    mutations["task-without-cpu"] = valid.copy()
    mutations["task-without-cpu"][6] = (None, "task-ready-before")
    mutations["parent-with-cpu"] = valid.copy()
    mutations["parent-with-cpu"][0] = (8, "create8-before")
    mutations["impossible-causal-order"] = valid.copy()
    cpu9_pre_release = [
        (9, "task-ready-before"),
        (9, "task-ready-after"),
        (9, "task-start-wait-before"),
    ]
    mutations["impossible-causal-order"] = [
        record
        for record in mutations["impossible-causal-order"]
        if record not in cpu9_pre_release
    ]
    release_index = mutations["impossible-causal-order"].index(
        (None, "release-before")
    )
    mutations["impossible-causal-order"][release_index + 1 : release_index + 1] = (
        cpu9_pre_release
    )
    mutations["ready-completion-causal-order"] = valid.copy()
    cpu8_ready_prefix = mutations["ready-completion-causal-order"][6:9]
    del mutations["ready-completion-causal-order"][6:9]
    ready8_after = mutations["ready-completion-causal-order"].index(
        (None, "ready8-wait-after")
    )
    mutations["ready-completion-causal-order"][ready8_after + 1 : ready8_after + 1] = (
        cpu8_ready_prefix
    )
    for name, records in mutations.items():
        expect_marker_rejection(name, records)
        expect_capture_rejection(name, terminal_capture(records))

    prefix_capture = phase_capture.render_snapshot(1, valid[:18])
    prefix_result = phase_capture.analyze_capture_text(prefix_capture)
    require(prefix_result["capture_class"] == "valid-prefix", "prefix class changed")
    require(prefix_result["phase_records"] == 18, "prefix record count changed")
    delayed_prefix_result = phase_capture.analyze_capture_text(
        "\n".join(
            (
                phase_capture.render_snapshot(1, []),
                phase_capture.render_snapshot(2, valid[:18]),
            )
        )
    )
    require(
        delayed_prefix_result["snapshot_count"] == 2,
        "pre-marker empty snapshot was rejected",
    )
    prompt_framed_result = phase_capture.analyze_capture_text(
        "GEMINI-AC-USB# > > \n" + prefix_capture
    )
    require(
        prompt_framed_result["capture_class"] == "valid-prefix",
        "USB prompt framing was not isolated from the first snapshot",
    )

    terminal_result = phase_capture.analyze_capture_text(terminal_capture(valid))
    require(terminal_result["capture_class"] == "terminal", "terminal class changed")
    require(terminal_result["phase_records"] == 39, "terminal record count changed")
    phase_capture.analyze_capture_text(terminal_capture(alternate))

    create_failure = [
        (None, "create8-before"),
        (None, "create8-after"),
        (None, "create9-before"),
        (None, "create9-after"),
        (None, "stop8-before"),
        (None, "stop8-after"),
        (None, "run-exit"),
    ]
    create_result = phase_capture.analyze_capture_text(
        terminal_capture(create_failure, result="fault")
    )
    require(create_result["capture_class"] == "terminal", "create-fault rejected")

    timeout_failure = [record for record in valid if record[0] != 9]
    timeout_insert = timeout_failure.index((None, "done9-wait-after")) + 1
    timeout_failure[timeout_insert:timeout_insert] = [
        (9, phase) for phase in phase_capture.TASK_PHASES
    ]
    timeout_result = phase_capture.analyze_capture_text(
        terminal_capture(timeout_failure, result="fault")
    )
    require(timeout_result["capture_class"] == "terminal", "timeout-fault rejected")

    undispatched_failure = [(None, phase) for phase in phase_capture.PARENT_PHASES]
    undispatched_result = phase_capture.analyze_capture_text(
        terminal_capture(undispatched_failure, result="fault")
    )
    require(
        undispatched_result["capture_class"] == "terminal",
        "undispatched-stop fault was rejected",
    )

    parent_fault_capture = terminal_capture([], result="fault", pair6_result="fault")
    parent_fault_result = phase_capture.analyze_capture_text(parent_fault_capture)
    require(
        parent_fault_result["capture_class"] == "terminal",
        "marker-free parent fault was rejected",
    )

    unterminated_pass = unterminated_terminal_capture(valid)
    unterminated_pass_result = phase_capture.analyze_capture_text(unterminated_pass)
    require(
        unterminated_pass_result["capture_class"]
        == "transport-truncated-valid-snapshot"
        and unterminated_pass_result["terminal_result"] == "pass",
        "valid unterminated pair terminal changed",
    )
    unterminated_fault = unterminated_terminal_capture(
        undispatched_failure, result="fault"
    )
    unterminated_fault_result = phase_capture.analyze_capture_text(
        unterminated_fault
    )
    require(
        unterminated_fault_result["capture_class"]
        == "transport-truncated-valid-snapshot"
        and unterminated_fault_result["terminal_result"] == "fault",
        "valid unterminated fault terminal changed",
    )
    expect_capture_rejection(
        "unterminated-pass-unpark-not-issued",
        unterminated_pass.replace("sc_unpark8=1", "sc_unpark8=0"),
        "pair-v7 pass field changed: sc_unpark8",
    )
    expect_capture_rejection(
        "unterminated-fault-unpark-out-of-domain",
        unterminated_fault.replace("sc_unpark8=1", "sc_unpark8=2"),
        "sc_unpark8 is outside the source domain",
    )
    expect_capture_rejection(
        "unterminated-fault-unpark-marker-without-issued",
        unterminated_fault.replace("sc_unpark8=1", "sc_unpark8=0"),
        "sc_unpark8=0 contradicts its after marker",
    )

    doubled = prefix_capture.replace(
        "gemini-a72-sc-phase phase=create8-before",
        "gemini-a72-sc-phase phase=create8-before "
        "gemini-a72-sc-phase phase=create8-before",
        1,
    )
    expect_capture_rejection("double-occurrence-line", doubled)
    expect_capture_rejection(
        "nonmonotonic-snapshots",
        "\n".join(
            (
                phase_capture.render_snapshot(1, valid[:18]),
                phase_capture.render_snapshot(2, valid[:17]),
            )
        ),
    )
    expect_capture_rejection(
        "no-complete-snapshot",
        phase_capture.render_snapshot(1, valid[:18]).rsplit("\n", 1)[0],
    )
    expect_capture_rejection(
        "later-parent-after-unmatched-before",
        phase_capture.render_snapshot(
            1,
            [
                (None, "create8-before"),
                (None, "create9-before"),
            ],
        ),
    )
    expect_capture_rejection(
        "task-without-unpark",
        phase_capture.render_snapshot(
            1,
            [
                (None, "create8-before"),
                (None, "create8-after"),
                (None, "create9-before"),
                (None, "create9-after"),
                (8, "task-ready-before"),
            ],
        ),
    )

    def terminals_before_markers(capture: str) -> str:
        lines = capture.splitlines()
        snapshot_end = lines.index("phase_trace_snapshot_end sequence=1")
        pair_lines = lines[snapshot_end - 2 : snapshot_end]
        marker_lines = lines[1 : snapshot_end - 2]
        return "\n".join(
            [lines[0], *pair_lines, *marker_lines, *lines[snapshot_end:]]
        )

    expect_capture_rejection(
        "pass-terminal-before-run-exit",
        terminals_before_markers(terminal_capture(valid)),
    )
    expect_capture_rejection(
        "fault-terminal-before-run-exit",
        terminals_before_markers(terminal_capture(create_failure, result="fault")),
    )
    expect_capture_rejection(
        "unreachable-parent-block-skip",
        phase_capture.render_snapshot(
            1,
            [
                (None, "create8-before"),
                (None, "create8-after"),
                (None, "release-before"),
            ],
        ),
    )
    incomplete_pair6 = terminal_capture(valid).replace(
        f" pl_actual={'0' * 16}", ""
    )
    expect_capture_rejection("incomplete-pair-v6", incomplete_pair6)
    mismatched_metadata_lines = terminal_capture(valid).splitlines()
    for index, line in enumerate(mismatched_metadata_lines):
        if line.startswith("pair7_terminal_line="):
            mismatched_metadata_lines[index] = line.replace(
                "sc_unpark8=1", "sc_unpark8=0", 1
            )
    expect_capture_rejection(
        "snapshot-metadata-mismatch", "\n".join(mismatched_metadata_lines)
    )
    for cpu in (8, 9):
        expect_capture_rejection(
            f"legacy-wake{cpu}-field-schema",
            terminal_capture(valid).replace(
                f"sc_unpark{cpu}=1", f"sc_wake{cpu}=1"
            ),
            f"field order changed at sc_unpark{cpu}",
        )
    expect_capture_rejection(
        "pass-unpark-not-issued",
        terminal_capture(valid).replace("sc_unpark8=1", "sc_unpark8=0"),
        "pair-v7 pass field changed: sc_unpark8",
    )
    expect_capture_rejection(
        "fault-unpark-marker-without-issued",
        terminal_capture(undispatched_failure, result="fault").replace(
            "sc_unpark8=1", "sc_unpark8=0"
        ),
        "sc_unpark8=0 contradicts its after marker",
    )
    expect_capture_rejection(
        "fault-unpark-issued-without-markers",
        parent_fault_capture.replace("sc_unpark8=0", "sc_unpark8=1"),
        "sc_unpark8=1 lacks causal marker",
    )
    expect_capture_rejection(
        "fault-unpark-out-of-domain",
        parent_fault_capture.replace("sc_unpark8=0", "sc_unpark8=2"),
        "sc_unpark8 is outside the source domain",
    )
    expect_capture_rejection(
        "pair-history-disappears",
        "\n".join(
            (
                phase_capture.render_snapshot(1, valid, pair_result="pass"),
                phase_capture.render_snapshot(2, valid),
            )
        ),
    )
    expect_capture_rejection(
        "pair-v7-pass-semantic-mismatch",
        terminal_capture(valid).replace("sc_reported=1", "sc_reported=0"),
    )
    expect_capture_rejection(
        "pair-v6-pass-semantic-mismatch",
        terminal_capture(valid).replace("hps_reported=1", "hps_reported=0"),
    )
    ready_fault_baseline = terminal_capture(
        mutations["ready-completion-causal-order"], result="fault"
    )
    require(
        phase_capture.analyze_capture_text(ready_fault_baseline)["capture_class"]
        == "terminal",
        "ready-fault baseline was rejected",
    )
    ready_success_mismatch = ready_fault_baseline.replace(
        "sc_readywait8=0", "sc_readywait8=1"
    )
    expect_capture_rejection(
        "fault-ready-success-causality",
        ready_success_mismatch,
        "sc_readywait8=1 contradicts causal marker order",
    )

    start_early = valid.copy()
    cpu8_after_start = [
        record
        for record in start_early
        if record[0] == 8
        and record[1]
        in (
            "task-start-wait-after",
            "task-work-before",
            "task-work-after",
            "task-done-before",
            "task-done-after",
        )
    ]
    start_early = [record for record in start_early if record not in cpu8_after_start]
    release_before = start_early.index((None, "release-before"))
    start_early[release_before:release_before] = cpu8_after_start
    start_fault_baseline = terminal_capture(start_early, result="fault")
    require(
        phase_capture.analyze_capture_text(start_fault_baseline)["capture_class"]
        == "terminal",
        "start-fault baseline was rejected",
    )
    start_success_mismatch = start_fault_baseline.replace(
        "sc_startwait8=0", "sc_startwait8=1"
    )
    expect_capture_rejection(
        "fault-start-success-causality",
        start_success_mismatch,
        "sc_startwait8=1 contradicts causal marker order",
    )

    done_success_mismatch = terminal_capture(timeout_failure, result="fault").replace(
        "sc_wait9=0", "sc_wait9=1"
    )
    expect_capture_rejection(
        "fault-done-success-causality",
        done_success_mismatch,
        "sc_wait9=1 contradicts causal marker order",
    )
    truncated_result = phase_capture.analyze_capture_text(
        "\n".join(
            (
                prefix_capture,
                "phase_trace_snapshot_begin sequence=2 lines=1",
                phase_capture.marker_line(valid[18]),
            )
        )
    )
    require(
        truncated_result["capture_class"]
        == "transport-truncated-valid-snapshot",
        "transport-truncated class changed",
    )

    plan_words = " ".join(plan.split())
    for token in (
        "Changed-cycle pstore is primary",
        "PASS",
        "FIRST UNMATCHED PHASE BOUNDARY",
        "EXPLICIT PAIR-V7 FAULT",
        "INHERITED PAIR-V6 REGRESSION",
        "RUN-EXIT OR TERMINAL-PUBLICATION BOUNDARY",
        "MARKER CONTRACT VIOLATION",
        "ATTRIBUTABLE RESTART WITH INCOMPLETE TRACE",
        "NO ATTRIBUTABLE MARKER OR EVIDENCE LOSS",
        "LOST RECOVERY OR SAFETY FAILURE",
        "Compile package boot-candidate field: false",
        "d36a6a12e2ef4d0501df78f8fa9a94e763c1907f155c5f008182eed2d1f0b7f2",
        "No prior one-image override is reused",
        "a72-scheduler-unpark-attempt-1",
        "--wait-for-cycle --wait-seconds 900",
        "without a fresh backup",
        "matching full-partition readback",
        "shut the device down cleanly",
        "known-good Gemian root",
        "CPUs 8/9 offline",
        "unchanged full boot2 checksum",
        "39 runtime records",
        "31 unique source strings",
        "no global CPU8-versus-CPU9 order",
        "head-truncated evidence",
        "A terminal before run-exit violates the source contract",
        "Screen color or an automatic restart alone is not classifying evidence",
        "adjacent complete pair-v6 pass",
        "gemini-a72-pair-v7 result=pass parent_pass=1",
        "sc_reported=1 sc_iterations=262144 sc_rescheds=64",
        "sc_expected8=8 sc_start8=8 sc_end8=8",
        "sc_expected9=9 sc_start9=9 sc_end9=9",
        "sc_task8=1 sc_task9=1 sc_create8=0 sc_create9=0",
        "sc_unpark8=1 sc_unpark9=1",
        "sc_readywait8=1 sc_readywait9=1",
        "sc_startwait8=1 sc_startwait9=1",
        "sc_wait8=1 sc_wait9=1",
        "sc_error8=0 sc_error9=0 sc_stop8=0 sc_stop9=0",
        "sc_done8=262144 sc_done9=262144 sc_ready=2 sc_finished=2",
        "sc_hash8=f678147669874ecd sc_hash9=c2274327e9c8104c",
        "One exact repeat is then earned",
    ):
        require(token in plan_words, f"runtime decision missing: {token}")

    require(
        REJECTION_COUNTS == {"installer": 4, "marker": 14, "capture": 39},
        f"negative coverage changed: {REJECTION_COUNTS}",
    )
    print("validation=a72-scheduler-unpark-runtime-tools")
    print(
        f"installer_identity_mutations={REJECTION_COUNTS['installer']}-rejected"
    )
    print("phase_marker_source=31-unique")
    print("phase_marker_success_path=39-records")
    print(f"phase_marker_mutations={REJECTION_COUNTS['marker']}-rejected")
    print("capture_format=numbered-full-snapshots")
    print("pair_terminal_schemas=source-pinned")
    print("pair_terminal_semantics=exact-pass-field-conditioned-fault")
    print(f"capture_mutations={REJECTION_COUNTS['capture']}-rejected")
    print("fault_branches=create-failure-timeout-undispatched-accepted")
    print("unpark_fields=domain-bidirectional-marker-causality")
    print("installer=exact-predecessor-candidate-readback-shutdown")
    print("pstore=read-only-changed-cycle-helper-pinned")
    print("live_collector=read-only-pstore-primary-usb-secondary")
    print("result_classes=9-complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        AssertionError,
        OSError,
        phase_capture.CaptureError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
