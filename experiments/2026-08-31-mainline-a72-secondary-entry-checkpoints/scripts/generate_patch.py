#!/usr/bin/env python3
"""Generate and audit the monotonic P30E secondary-entry checkpoints."""

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


PATCH_NAME = "0457-arm64-add-P30E-secondary-entry-checkpoints.patch"
SUBJECT = "arm64: add P30E secondary entry checkpoints"
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
    commit(root, "Gemini post-0456 generation parent", "Synthetic parent only.", 0)


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
    header = (root / source_edits.P30E_H).read_text(encoding="utf-8")
    assembly = (root / source_edits.P30E_ASM).read_text(encoding="utf-8")
    head = (root / source_edits.HEAD).read_text(encoding="utf-8")
    p30e = (root / source_edits.P30E_C).read_text(encoding="utf-8")
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

    checkpoint_names = (
        "CPU_SETUP",
        "TASK_READY",
        "C_ENTRY",
        "IDMAP_OFF",
        "CAPABILITIES",
        "TARGET_VALID",
        "IRQ_READY",
    )
    for value, name in enumerate(checkpoint_names, start=1):
        token = f"ARM64_MT6797_A72_P30E_CHECKPOINT_{name}"
        if header.count(f"#define {token}") != 1:
            raise SystemExit(f"checkpoint constant inventory changed: {token}")
        if f"{token}\t" not in header and f"{token} " not in header:
            raise SystemExit(f"checkpoint constant is malformed: {token}")
        if name == "CPU_SETUP":
            if assembly.count(token) != 1 or head.count(token) != 1:
                raise SystemExit("MMU-off checkpoint call inventory changed")
        elif name == "TASK_READY":
            if head.count(token) != 1:
                raise SystemExit("task-ready checkpoint call inventory changed")
        elif smp.count(token) != 1:
            raise SystemExit(f"C checkpoint call inventory changed: {token}")
        definition = next(
            line for line in header.splitlines() if line.startswith(f"#define {token}")
        )
        if not definition.rstrip().endswith(str(value)):
            raise SystemExit(f"checkpoint value changed: {token}")

    required = {
        header: (
            "#define ARM64_MT6797_A72_P30E_CHECKPOINT_NONE",
            "int arm64_mt6797_a72_p30e_target_checkpoint_mmuoff(u64 checkpoint);",
            "int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint);",
        ),
        assembly: (
            "SYM_FUNC_START(arm64_mt6797_a72_p30e_target_checkpoint_mmuoff)",
            "ARM64_MT6797_A72_P30E_TARGET_REASON_OFF",
            "bl\tp30e_clean_slot",
        ),
        head: (
            "mov\tx21, x0\t\t\t// preserve the SCTLR value",
            "mov\tx0, x21",
            "bl\tarm64_mt6797_a72_p30e_target_checkpoint",
        ),
        p30e: (
            "int arm64_mt6797_a72_p30e_target_checkpoint(u64 checkpoint)",
            "checkpoint <= previous",
            "ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD) != 0",
            "p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);",
        ),
        smp: ("asmlinkage notrace void secondary_start_kernel(void)",),
        public: (
            "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 4U",
            "u32 p30e_target_reason;",
        ),
        binder: (
            "const __le64 *p30e = binder->p30e_snapshot.word;",
            "snapshot->p30e_target_reason =",
            "le64_to_cpu(p30e[ARM64_MT6797_A72_P30E_TARGET_REASON_WORD]);",
            "ARM64_MT6797_A72_P30E_TARGET_REASON_WORD",
        ),
        test: (
            "u32 p30e_target_reason;",
            "cpu_to_le64(state->p30e_target_reason)",
            "KUNIT_EXPECT_EQ(test, diagnostic.p30e_target_reason,",
        ),
        admission: (
            "p30e_target_reason=%u",
            "diagnostic.p30e_target_reason,",
        ),
    }
    for text, tokens in required.items():
        for token in tokens:
            if token not in text:
                raise SystemExit(f"required checkpoint token missing: {token}")

    if assembly.count("str\tx16, [x1, #ARM64_MT6797_A72_P30E_TARGET_REASON_OFF]") != 1:
        raise SystemExit("MMU-off reason write inventory changed")
    if p30e.count(
        "p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);"
    ) != 1:
        raise SystemExit("normal-text reason write inventory changed")
    if public.count("MT6797_A72_BINDER_DIAGNOSTIC_ABI 4U") != 1:
        raise SystemExit("diagnostic ABI inventory changed")

    return [
        "secondary_entry_checkpoint_validation=pass",
        "checkpoint_values=0,1,2,3,4,5,6,7",
        "mmuoff_checkpoint_writes=1",
        "normal_text_checkpoint_writes=1",
        "checkpoint_call_sites=7",
        "diagnostic_abi=4",
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
    if added.count(
        "str\tx16, [x1, #ARM64_MT6797_A72_P30E_TARGET_REASON_OFF]"
    ) != 1:
        raise SystemExit("generated MMU-off reason write inventory changed")
    if added.count(
        "p30e_put(wire, ARM64_MT6797_A72_P30E_TARGET_REASON_WORD, checkpoint);"
    ) != 1:
        raise SystemExit("generated normal-text reason write inventory changed")


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
    with tempfile.TemporaryDirectory(prefix="a72-secondary-checkpoints-") as name:
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
            "CPU8 reached the P30E CLAIMED boundary but did not publish its\n"
            "later secondary-start result. That state spans processor setup,\n"
            "MMU enablement, task setup, and architecture C initialization.\n\n"
            "Record monotonic target-owned checkpoints in the existing P30E\n"
            "reason word while the target remains CLAIMED. Expose the reason\n"
            "through diagnostic ABI 4. Keep the CPU request, CPU9 veto,\n"
            "CPU_OFF, retry, and power-sequence inventories unchanged.",
            1,
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
                    "experiment=2026-08-31-mainline-a72-secondary-entry-checkpoints",
                    f"repository_commit={args.repository_commit}",
                    f"prepared_source_state={state}",
                    f"prepared_source_integrity={integrity}",
                    "canonical_parent=0456",
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
