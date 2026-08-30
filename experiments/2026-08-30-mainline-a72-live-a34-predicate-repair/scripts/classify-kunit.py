#!/usr/bin/env python3
"""Classify the exact hardware-free KUnit coverage for the A34 repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"

LATE_CPU_CASES = (
    "late_cpu_startup_bootstrap_claim_excludes_prepare_test",
    "late_cpu_startup_bootstrap_claim_identity_test",
    "late_cpu_startup_bootstrap_claim_rejects_nonpristine_test",
    "late_cpu_startup_invalid_token_test",
    "late_cpu_startup_abort_is_one_shot_test",
    "late_cpu_startup_unproven_cpu_on_test",
    "late_cpu_startup_cpu_on_fault_test",
    "late_cpu_startup_cancel_wins_test",
    "late_cpu_startup_cpu8_then_cpu9_test",
    "late_cpu_startup_armed_quarantine_test",
    "late_cpu_startup_publishing_quarantine_test",
    "late_cpu_startup_publishing_wrong_target_test",
    "late_cpu_startup_online_mismatch_test",
    "late_cpu_startup_premature_retire_test",
    "late_cpu_startup_terminal_branches_test",
    "late_cpu_startup_k_to_c_immutability_test",
    "late_cpu_startup_panic_order_test",
    "late_cpu_startup_target_tuple_test",
    "late_cpu_startup_invalid_failure_branch_test",
    "late_cpu_startup_prearmed_target_claim_test",
)

PROFILES = {
    "a72-admission-live-trigger-kunit": {
        "options": (
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST=y",
            "CONFIG_PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST=y",
        ),
        "suites": (
            ("gemini-admission-trace", (
                "gemini_admission_trace_entry_commit_test",
                "gemini_admission_trace_entry_reentry_test",
                "gemini_admission_trace_foreign_refusal_test",
                "gemini_admission_trace_terminal_records_test",
                "gemini_admission_trace_terminal_gates_test",
                "gemini_admission_trace_torn_write_test",
            )),
            ("mt6797-a72-admission-controller", (
                "mt6797_a72_admission_trigger_invalid_test",
                "mt6797_a72_admission_trigger_terminal_test",
                "mt6797_a72_admission_trigger_repeat_closed_test",
                "mt6797_a72_admission_success_test",
                "mt6797_a72_admission_preconsume_gates_test",
                "mt6797_a72_admission_terminal_failures_test",
                "mt6797_a72_admission_request_failure_test",
                "mt6797_a72_admission_trace_failures_test",
                "mt6797_a72_admission_live_trace_softfail_test",
                "mt6797_a72_admission_repeat_closed_test",
            )),
        ),
    },
    "a72-a34-v2-kunit": {
        "options": (
            "CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST=y",
            "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST=y",
            "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST=y",
        ),
        "suites": (
            ("arm64-late-cpu-startup", LATE_CPU_CASES),
            ("mt6797-a72-a34-eligibility", (
                "mt6797_a34_exact_direct_replay_test",
                "mt6797_a34_null_test",
                "mt6797_a34_irrelevant_payload_test",
                "mt6797_a34_relevant_mutation_test",
                "mt6797_a34_missing_replay_test",
                "mt6797_a34_admission_remains_closed_test",
            )),
            ("mt6797-a72-direct-state", (
                "direct_snapshot_success",
                "direct_registry_guards",
                "direct_callback_failure_zeroes",
                "direct_source_mutations_rejected",
                "direct_topology_mutations_rejected",
                "direct_open_owner_rejected",
                "direct_unregister_closes_source",
            )),
        ),
    },
    "a72-derived-admission-kunit": {
        "options": ("CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST=y",),
        "suites": (("mt6797-a72-derived-admission", (
            "mt6797_a72_derived_success_test",
            "mt6797_a72_derived_source_rejections_test",
            "mt6797_a72_derived_ready_rejection_test",
            "mt6797_a72_legacy_assertions_rejected_test",
            "mt6797_a72_derived_repeat_rejected_test",
        )),),
    },
    "a72-atomic-publication-kunit": {
        "options": (
            "CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST=y",
            "CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST=y",
            "CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST=y",
        ),
        "suites": (
            ("arm64-late-cpu-startup", LATE_CPU_CASES),
            ("mt6797-a72-atomic-publication", (
                "atomic_finalizer_success_test",
                "atomic_finalizer_failure_identity_test",
                "atomic_publication_success_repeat_test",
                "atomic_publication_replay_rejections_test",
                "atomic_publication_source_rejections_test",
                "atomic_publication_topology_rejection_test",
                "atomic_publication_p30_busy_test",
                "atomic_publication_final_owner_mismatch_test",
            )),
        ),
    },
}


class ClassificationError(RuntimeError):
    """Raised when runtime evidence does not prove the exact contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClassificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_checksum(path: Path, entry: str) -> str:
    matches = re.findall(
        rf"^([0-9a-f]{{64}})  {re.escape(entry)}$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(len(matches) == 1, f"checksum entry absent or duplicated: {entry}")
    return matches[0]


def clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.replace("\r", "").splitlines():
        line = re.sub(r"^\[\s*\d+\.\d+\]\s*", "", line)
        lines.append(line.strip())
    return lines


def validate_config(config: Path, expected: tuple[str, ...]) -> None:
    text = config.read_text(encoding="utf-8")
    for token in (
        "CONFIG_KUNIT=y",
        "CONFIG_KUNIT_DEFAULT_ENABLED=y",
        "CONFIG_KUNIT_AUTORUN_ENABLED=y",
        "CONFIG_CMDLINE_FORCE=y",
    ):
        require(token in text.splitlines(), f"configuration missing: {token}")
    observed = tuple(sorted(re.findall(
        r"^CONFIG_.*_KUNIT_TEST=y$", text, re.MULTILINE
    )))
    require(observed == tuple(sorted(expected)),
            f"focused KUnit inventory changed: {observed}")


def classify_runtime(raw: str, release: str,
                     suites: tuple[tuple[str, tuple[str, ...]], ...]) -> None:
    lines = clean_lines(raw)
    require(re.findall(r"Linux version ([^ ]+)", raw) == [release],
            "kernel release mismatch")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    ktap = lines[lines.index("KTAP version 1"):]
    require(ktap.count("KTAP version 1") == len(suites) + 1,
            "unexpected KTAP header count")
    plans = [line for line in ktap if re.fullmatch(r"1\.\.\d+", line)]
    expected_plans = [f"1..{len(suites)}"] + [
        f"1..{len(cases)}" for _, cases in suites
    ]
    require(plans == expected_plans, f"KUnit plans changed: {plans}")
    require([line for line in ktap if line.startswith("# Subtest: ")] ==
            [f"# Subtest: {suite}" for suite, _ in suites],
            "focused suite inventory changed")
    require(not any(line.startswith("not ok ") for line in ktap),
            "KTAP contains a failing result")

    expected_ok = []
    for suite_index, (suite, cases) in enumerate(suites, start=1):
        expected_ok.extend(
            f"ok {case_index} {case}"
            for case_index, case in enumerate(cases, start=1)
        )
        expected_ok.append(f"ok {suite_index} {suite}")
        summary = f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        totals = f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        require(ktap.count(summary) == 1,
                f"suite summary is not an exact pass: {suite}")
        require(ktap.count(totals) == 1,
                f"suite totals are not an exact pass: {suite}")
    observed_ok = [line for line in ktap if re.fullmatch(r"ok \d+ \S+", line)]
    require(observed_ok == expected_ok,
            f"case or suite inventory changed: {observed_ok}")

    result_index = ktap.index(f"ok {len(suites)} {suites[-1][0]}")
    panics = [i for i, line in enumerate(ktap) if line.startswith(PANIC_PREFIX)]
    require(len(panics) == 1 and panics[0] > result_index,
            "expected post-test rootfs panic absent or reordered")
    panic_ends = [
        i for i, line in enumerate(ktap) if line.startswith(PANIC_END_PREFIX)
    ]
    require(len(panic_ends) == 1 and panic_ends[0] > panics[0],
            "terminal panic marker absent or reordered")
    for forbidden in (
        "BUG:", "Unable to handle kernel", "SError Interrupt",
        "stack overflow", "stack-protector",
    ):
        require(forbidden not in raw, f"unexpected kernel fault: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--harness-commit", required=True)
    parser.add_argument("--termination", choices=("harness-after-terminal-marker",),
                        required=True)
    args = parser.parse_args()
    for commit in (args.repository_commit, args.harness_commit):
        require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
                "invalid commit identity")

    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build_path = package / "provenance/build.json"
    image = package / "Image"
    config = package / "kernel.config"
    system_map = package / "System.map"
    sums = package / "SHA256SUMS"
    for path in (build_path, image, config, system_map, sums, raw_log):
        require(path.is_file() and not path.is_symlink(),
                f"required regular file absent or unsafe: {path.name}")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    require(build["repository_commit"] == args.repository_commit,
            "package repository commit mismatch")
    require(build["repository_dirty"] is False, "package source was dirty")
    profile = build["build_profile"]
    require(profile in PROFILES, "package profile mismatch")
    require(build["target_architecture"] == "arm64", "target is not arm64")
    require(build["modules_built"] is False, "unexpected module build")
    contract = PROFILES[profile]
    validate_config(config, contract["options"])

    checksums = {
        "image": sha256(image),
        "config": sha256(config),
        "system_map": sha256(system_map),
    }
    for label, entry in (
        ("image", "./Image"),
        ("config", "./kernel.config"),
        ("system_map", "./System.map"),
    ):
        require(checksums[label] == manifest_checksum(sums, entry),
                f"{label} checksum mismatch")
    require(checksums["config"] == build["config_sha256"],
            "configuration provenance mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, build["kernel_release"], contract["suites"])
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")
    total = sum(len(cases) for _, cases in contract["suites"])

    print("experiment=2026-08-30-mainline-a72-live-a34-predicate-repair")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"harness_commit={args.harness_commit}")
    print(f"profile={profile}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    print(f"image_sha256={checksums['image']}")
    print(f"config_sha256={checksums['config']}")
    print(f"system_map_sha256={checksums['system_map']}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-single-thread-no-network")
    print(f"suites={len(contract['suites'])}")
    print(f"tests={total}")
    print("failed=0")
    print("skipped=0")
    for suite, cases in contract["suites"]:
        print(f"suite_{suite}=pass-{len(cases)}-of-{len(cases)}")
    print(f"tap_summary=pass:{total}_fail:0_skip:0_total:{total}")
    print("post_test_state=expected_vm_rootfs_panic")
    print("termination=harness-after-terminal-marker")
    print("result=pass")
    print("physical_cpu_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("network=false")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
