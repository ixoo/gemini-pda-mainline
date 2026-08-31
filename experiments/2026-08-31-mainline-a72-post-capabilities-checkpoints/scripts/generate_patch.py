#!/usr/bin/env python3
"""Generate and audit the post-capabilities CPU8 checkpoint patch."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import source_edits


PATCH_NAME = "0458-arm64-refine-P30E-post-capabilities-checkpoints.patch"
SUBJECT = "arm64: refine P30E post-capabilities checkpoints"
SOURCE_FILES = source_edits.SOURCE_FILES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
            "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
            "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
            "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
            "GIT_AUTHOR_DATE": f"2026-08-31T20:{minute:02d}:00Z",
            "GIT_COMMITTER_DATE": f"2026-08-31T20:{minute:02d}:00Z",
        }
    )
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git",
        "commit",
        "--quiet",
        "--no-gpg-sign",
        "-m",
        subject,
        "-m",
        body,
        cwd=root,
        env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative in SOURCE_FILES:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent file is absent or unsafe: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid", cwd=root
    )
    commit(root, "Gemini post-0457 generation parent", "Synthetic parent only.", 9)


def combined_source(root: Path) -> str:
    return "\n".join(
        (root / relative).read_text(encoding="utf-8") for relative in SOURCE_FILES
    )


def operation_counts(root: Path) -> dict[str, int]:
    text = combined_source(root)
    return {
        "cpu_up": text.count("cpu_up("),
        "cpu_down": text.count("cpu_down("),
        "add_cpu": text.count("add_cpu("),
        "remove_cpu": text.count("remove_cpu("),
        "cpu_boot": text.count("cpu_boot("),
        "psci_cpu_on": text.count("psci_cpu_on"),
        "psci_cpu_off": text.count("psci_cpu_off"),
        "cpu_off": text.count("cpu_off("),
        "cpu9_operation": text.count(
            "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP"
        ),
        "regmap_write": text.count("regmap_write("),
        "writel": text.count("writel("),
        "writeq": text.count("writeq("),
        "memcpy_toio": text.count("memcpy_toio("),
    }


def validate(root: Path, parent_counts: dict[str, int]) -> list[str]:
    p30e_h = (root / source_edits.P30E_H).read_text(encoding="utf-8")
    p30e_c = (root / source_edits.P30E_C).read_text(encoding="utf-8")
    late_h = (root / source_edits.LATE_H).read_text(encoding="utf-8")
    late_c = (root / source_edits.LATE_C).read_text(encoding="utf-8")
    smp = (root / source_edits.SMP).read_text(encoding="utf-8")
    public = (root / source_edits.BINDER_PUBLIC).read_text(encoding="utf-8")
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    test = (root / source_edits.BINDER_TEST).read_text(encoding="utf-8")
    admission = (root / source_edits.ADMISSION).read_text(encoding="utf-8")
    counts = operation_counts(root)
    if counts != parent_counts:
        differences = {
            key: (parent_counts[key], counts[key])
            for key in parent_counts
            if parent_counts[key] != counts[key]
        }
        raise SystemExit(f"CPU/power/storage call inventory changed: {differences}")

    checkpoints = {
        "CPU_SETUP": 1,
        "TASK_READY": 2,
        "C_ENTRY": 3,
        "IDMAP_OFF": 4,
        "CAPABILITIES": 5,
        "CPU_OPS_READY": 6,
        "CPUINFO_READY": 7,
        "EXPECTATION_FAILED": 8,
        "EXPECTATION_VALID": 9,
        "TOPOLOGY_READY": 10,
        "IRQ_READY": 11,
    }
    for name, value in checkpoints.items():
        token = f"ARM64_MT6797_A72_P30E_CHECKPOINT_{name}"
        definitions = [
            line for line in p30e_h.splitlines() if line.startswith(f"#define {token}")
        ]
        if len(definitions) != 1 or not definitions[0].rstrip().endswith(str(value)):
            raise SystemExit(f"checkpoint definition changed: {token}")
        if name in {
            "CPU_OPS_READY",
            "CPUINFO_READY",
            "EXPECTATION_FAILED",
            "EXPECTATION_VALID",
            "TOPOLOGY_READY",
        } and smp.count(token) != 1:
            raise SystemExit(f"post-capabilities call inventory changed: {token}")

    mismatch_names = (
        "MPIDR",
        "MIDR",
        "REVIDR",
        "CNTFRQ",
        "CTR",
        "DCZID",
        "CLIDR_EL1",
        "AA64DFR0",
        "AA64ISAR0",
        "AA64ISAR1",
        "AA64MMFR0",
        "AA64MMFR1",
        "AA64PFR0",
        "AA64PFR1",
        "ISAR0",
        "ISAR1",
        "ISAR2",
        "ISAR3",
        "ISAR4",
        "ISAR5",
        "MMFR0",
        "MMFR1",
        "MMFR2",
        "MMFR3",
        "PFR0",
        "PFR1",
        "CURRENT_CPU",
        "PAIR_CONTRACT",
        "TARGET_SLOT",
    )
    for name in mismatch_names:
        token = f"ARM64_LATE_CPU_EXPECT_MISMATCH_{name}"
        if late_h.count(f"#define {token}") != 1:
            raise SystemExit(f"mismatch bit definition changed: {token}")
        if name not in {"CURRENT_CPU", "PAIR_CONTRACT", "TARGET_SLOT"}:
            if late_c.count(token) != 1:
                raise SystemExit(f"register comparison changed: {token}")
    if late_c.count("late_expected_target_compare(") != 27:
        raise SystemExit("expected exactly 26 register comparisons")

    required = {
        p30e_h: (
            "arm64_mt6797_a72_p30e_target_detail",
            "ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED",
        ),
        p30e_c: (
            "p30e_target_checkpoint",
            "ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD) != 0",
            "ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD) != 0",
            "ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD) != 0",
        ),
        late_h: (
            "ARM64_LATE_CPU_EXPECT_MISMATCH_ALLOWED_MASK",
            "u64 *mismatches",
        ),
        late_c: (
            "late_expected_target_mismatches",
            "return *mismatches ? -ERANGE : 0;",
        ),
        smp: (
            "&expectation_mismatches",
            "arm64_mt6797_a72_p30e_target_detail(",
            "mask=%#llx",
        ),
        public: (
            "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 5U",
            "u64 p30e_target_effects;",
            "u64 p30e_target_entry_pc;",
            "u64 p30e_target_entry_sp;",
        ),
        binder: (
            "ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD",
            "ARM64_MT6797_A72_P30E_TARGET_ENTRY_PC_WORD",
            "ARM64_MT6797_A72_P30E_TARGET_ENTRY_SP_WORD",
        ),
        test: (
            "ARM64_LATE_CPU_EXPECT_MISMATCH_CTR",
            "diagnostic.p30e_target_effects",
            "diagnostic.p30e_target_entry_pc",
            "diagnostic.p30e_target_entry_sp",
        ),
        admission: (
            "p30e_target_effects=0x%llx",
            "p30e_target_entry_pc=0x%llx",
            "p30e_target_entry_sp=0x%llx",
        ),
    }
    for text, tokens in required.items():
        for token in tokens:
            if token not in text:
                raise SystemExit(f"required post-capabilities token missing: {token}")

    details_index = p30e_c.index(
        "p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_EFFECTS_WORD,"
    )
    reason_index = p30e_c.index(
        "p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);"
    )
    if details_index > reason_index:
        raise SystemExit("checkpoint detail is not committed before reason")
    if public.count("MT6797_A72_BINDER_DIAGNOSTIC_ABI 5U") != 1:
        raise SystemExit("diagnostic ABI inventory changed")

    return [
        "post_capabilities_checkpoint_validation=pass",
        "checkpoint_values=0,1,2,3,4,5,6,7,8,9,10,11",
        "new_checkpoint_call_sites=5",
        "expectation_register_comparisons=26",
        "expectation_structural_bits=61,62,63",
        "failure_detail_words=effects,entry_pc,entry_sp",
        "detail_before_reason=yes",
        "diagnostic_abi=5",
        "new_cpu_request_paths=0",
        "new_cpu9_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_power_sequence_calls=0",
        "new_storage_writes=0",
    ]


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(SOURCE_FILES):
        raise SystemExit("generated patch file count changed")
    added = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for token in (
        "Signed-off-by:",
        "/Users/",
        "cpu_up(",
        "cpu_down(",
        "add_cpu(",
        "remove_cpu(",
        "psci_cpu_on",
        "psci_cpu_off",
        "cpu_off(",
        "reboot",
        "retry",
        "regmap_write(",
        "writel(",
        "writeq(",
        "memcpy_toio(",
        "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP",
    ):
        if token.lower() in added.lower():
            raise SystemExit(f"forbidden generated token: {token}")
    if added.count("ARM64_MT6797_A72_P30E_CHECKPOINT_EXPECTATION_FAILED") < 2:
        raise SystemExit("expectation-failure checkpoint inventory changed")
    if added.count("p30e_target_effects") < 4:
        raise SystemExit("target detail diagnostic inventory changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")
    if len(args.repository_commit) != 40 or any(
        char not in "0123456789abcdef" for char in args.repository_commit
    ):
        raise SystemExit("invalid repository commit")

    state = (source_root / ".gemini-source-state").read_text().strip()
    integrity = (source_root / ".gemini-source-integrity").read_text().strip()
    with tempfile.TemporaryDirectory(prefix="a72-post-cap-checkpoints-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        parent_counts = operation_counts(root)
        source_edits.apply(root)
        markers = validate(root, parent_counts)
        commit(
            root,
            SUBJECT,
            "CPU8 retained the P30E capability checkpoint but did not reach\n"
            "the existing target-valid checkpoint. The remaining interval\n"
            "contains CPU postboot, CPU-info, expectation, and topology work.\n\n"
            "Split those operations with target-owned monotonic checkpoints.\n"
            "On expectation failure, retain the exact mismatch bitmap and\n"
            "first expected/observed pair before the reason commit. Keep the\n"
            "CPU request, CPU9 veto, CPU_OFF, retry, and power sequence\n"
            "unchanged, and expose the detail through diagnostic ABI 5.",
            10,
        )
        changed = tuple(
            sorted(
                run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root)
                .splitlines()
            )
        )
        expected = tuple(sorted(str(path) for path in SOURCE_FILES))
        if changed != expected:
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = Path(name) / "generated"
        generated_dir.mkdir()
        generated = run(
            "git",
            "format-patch",
            "--no-signature",
            "--output-directory",
            str(generated_dir),
            f"{parent}..HEAD",
            cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated patch")
        patch = generated_dir / generated[0]
        validate_patch(patch)
        run(
            "perl",
            str(source_root / "scripts/checkpatch.pl"),
            "--strict",
            "--no-tree",
            f"--root={source_root}",
            "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE",
            str(patch),
            cwd=Path(name),
        )

        replay = Path(name) / "replay"
        shutil.copytree(root, replay)
        run("git", "reset", "--hard", parent, cwd=replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate(replay, parent_counts) != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text(
            "\n".join(
                [
                    "experiment=2026-08-31-mainline-a72-post-capabilities-checkpoints",
                    f"repository_commit={args.repository_commit}",
                    f"prepared_source_state={state}",
                    f"prepared_source_integrity={integrity}",
                    "canonical_parent=0457",
                    "generated_patch_count=1",
                    *markers,
                    "deterministic_replay=pass",
                    "native_vm_build=none",
                    "device_action=none",
                    "boot_candidate=false",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        sums = output / "SHA256SUMS"
        inputs = (target, output / "series", provenance)
        sums.write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in inputs),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
