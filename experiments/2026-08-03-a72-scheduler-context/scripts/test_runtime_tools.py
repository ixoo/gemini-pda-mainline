#!/usr/bin/env python3
"""Validate phase-attribution deployment and observation contracts."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import validate_phase_capture as phase_capture


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
PLAN = (
    EXPERIMENT
    / "results"
    / "runtime-decision-map-phase-attribution-20260804.txt"
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
PAIR5 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-multiline-integrity"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)
PINS = (
    ("2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3", 2),
    ("2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8", 2),
    ("e10e38baeb290d00e73e587111024ec7ddf96974604837e31e980c7c62618df4", 2),
    ("gemian-a72-scheduler-phase-attribution-d06e220da658", 2),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_marker_rejection(name: str, records: list[tuple[int | None, str]]) -> None:
    try:
        phase_capture.validate_success_sequence(records)
    except phase_capture.CaptureError:
        return
    raise AssertionError(f"marker mutation accepted: {name}")


def expect_capture_rejection(name: str, capture: str) -> None:
    try:
        phase_capture.analyze_capture_text(capture)
    except phase_capture.CaptureError:
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
    return "\n".join(
        (
            phase_capture.render_snapshot(
                1, records, pair_result=result, pair6_result=pair6_result
            ),
            f"pair6_terminal_line={pair6}",
            f"pair7_terminal_line={pair7}",
            phase_capture.TERMINATOR,
        )
    )


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    phase_patch = PHASE_PATCH.read_text(encoding="utf-8")
    scheduler_patch = SCHEDULER_PATCH.read_text(encoding="utf-8")
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

    for token, count in PINS:
        require(installer.count(token) == count, f"installer pin count changed: {token}")
        require(
            installer.replace(token, "0" * len(token), 1).count(token) == count - 1,
            f"installer identity mutation was not rejected: {token}",
        )
    for token in (
        "EXPECTED_PREDECESSOR_SHA256=2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3",
        "CANDIDATE_SHA256=2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8",
        "ARTIFACT_MANIFEST_SHA256=e10e38baeb290d00e73e587111024ec7ddf96974604837e31e980c7c62618df4",
        "ARTIFACT_NAME=gemian-a72-scheduler-phase-attribution-d06e220da658",
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
    require("phase-attribution scheduler" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-scheduler-phase-attempt-N" in live_help, "live output changed")
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
        "sc_readywait8=-?[0-9]+ sc_readywait9=-?[0-9]+",
        "sc_startwait8=-?[0-9]+ sc_startwait9=-?[0-9]+",
        "sc_done8=[0-9]+ sc_done9=[0-9]+ sc_ready=[0-9]+ sc_finished=[0-9]+",
        "sc_hash8=[0-9a-f]{16} sc_hash9=[0-9a-f]{16}",
        "__A72_SCHEDULER_PHASE_TERMINAL_CAPTURED__",
        "validation=a72-scheduler-phase-terminal-capture-pass",
        "validation=a72-scheduler-phase-prefix-structure-pass",
        "validation=a72-scheduler-phase-transport-truncated-preserved",
    ):
        require(token in live, f"live collector lacks: {token}")
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
    parent_source_phases = re.findall(
        r'^\+\s*pr_emerg\("gemini-a72-sc-phase phase=([a-z0-9-]+)\\n"',
        phase_patch,
        flags=re.MULTILINE,
    )
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

    for version, result_expression in ((6, "pass"), (7, "%s")):
        terminal = re.search(
            rf'gemini-a72-pair-v{version} result={result_expression} ([^"\\]+)\\n"',
            scheduler_patch,
        )
        require(terminal is not None, f"pair-v{version} source terminal is absent")
        source_fields = []
        source_exact = {}
        source_hex = set()
        for token in terminal.group(1).split():
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

    mutations: dict[str, list[tuple[int | None, str]]] = {}
    mutations["missing-marker"] = valid[:-1]
    mutations["unknown-phase"] = valid.copy()
    mutations["unknown-phase"][6] = (8, "task-unknown-before")
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
        "task-without-wake",
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
                "sc_wake8=0", "sc_wake8=1", 1
            )
    expect_capture_rejection(
        "snapshot-metadata-mismatch", "\n".join(mismatched_metadata_lines)
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
    ready_success_mismatch = terminal_capture(
        mutations["ready-completion-causal-order"], result="fault"
    ).replace("sc_readywait8=0", "sc_readywait8=1")
    expect_capture_rejection("fault-ready-success-causality", ready_success_mismatch)

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
    start_success_mismatch = terminal_capture(start_early, result="fault").replace(
        "sc_startwait8=0", "sc_startwait8=1"
    )
    expect_capture_rejection("fault-start-success-causality", start_success_mismatch)

    done_success_mismatch = terminal_capture(timeout_failure, result="fault").replace(
        "sc_wait9=0", "sc_wait9=1"
    )
    expect_capture_rejection("fault-done-success-causality", done_success_mismatch)
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
        "sc_wake8 and sc_wake9 must each be 0 or 1",
        "sc_readywait8=1 sc_readywait9=1",
        "sc_startwait8=1 sc_startwait9=1",
        "sc_wait8=1 sc_wait9=1",
        "sc_error8=0 sc_error9=0 sc_stop8=0 sc_stop9=0",
        "sc_done8=262144 sc_done9=262144 sc_ready=2 sc_finished=2",
        "sc_hash8=f678147669874ecd sc_hash9=c2274327e9c8104c",
        "One exact repeat is then earned",
    ):
        require(token in plan_words, f"runtime decision missing: {token}")

    print("validation=a72-scheduler-phase-runtime-tools")
    print("installer_identity_mutations=4-rejected")
    print("phase_marker_source=31-unique")
    print("phase_marker_success_path=39-records")
    print(f"phase_marker_mutations={len(mutations)}-rejected")
    print("capture_format=numbered-full-snapshots")
    print("pair_terminal_schemas=source-pinned")
    print("pair_terminal_semantics=exact-pass-field-conditioned-fault")
    print(f"capture_mutations={len(mutations) + 16}-rejected")
    print("fault_branches=create-failure-timeout-undispatched-accepted")
    print("installer=exact-predecessor-candidate-readback-shutdown")
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
