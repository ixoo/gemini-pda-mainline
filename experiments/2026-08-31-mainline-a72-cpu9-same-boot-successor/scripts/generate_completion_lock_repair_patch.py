#!/usr/bin/env python3
"""Generate and audit the CPU9 completion-path lock repair patch."""

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

import completion_lock_repair_source_edits
import validate_completion_lock_repair_source


PATCH_NAME = (
    "0481-arm64-mediatek-avoid-CPU9-completion-hotplug-lock-recursion.patch"
)
SUBJECT = "arm64: mediatek: avoid CPU9 completion lock recursion"
CHANGED_PATHS = tuple(sorted(completion_lock_repair_source_edits.PARENT_HASHES))
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "cpu_down(", "remove_cpu(",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "kernel_restart(", "orderly_poweroff(",
)
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, env=env, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode:
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(args)}"
        )
    return result.stdout.strip()


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-09-02T10:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-02T10:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in completion_lock_repair_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"managed CPU9 completion parent changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(
        root, "Gemini post-0480 CPU9 completion parent",
        "Synthetic exact-source parent only.", 30,
    )


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "arch/arm64/include/asm/mt6797_a72_membership.h",
            "int mt6797_a72_publish_cpu9_success_locked(struct mt6797_a72_transaction *transaction);",
            "int mt6797_a72_publish_cpu9_success_locked_missing(struct mt6797_a72_transaction *transaction);",
        ),
        (
            "arch/arm64/include/asm/mt6797_a72_membership.h",
            "int mt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction);",
            "int mt6797_a72_finalize_cpu9_success_locked_missing(struct mt6797_a72_transaction *transaction);",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "int\nmt6797_a72_publish_cpu9_success_locked(struct mt6797_a72_transaction *transaction)\n{\n\tlockdep_assert_cpus_held();",
            "int\nmt6797_a72_publish_cpu9_success_locked(struct mt6797_a72_transaction *transaction)\n{\n\t/* lock contract omitted */",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "int\nmt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction)\n{\n\tlockdep_assert_cpus_held();",
            "int\nmt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction)\n{\n\t/* lock contract omitted */",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\treturn mt6797_a72_publish_cpu9_success_state(transaction,\n\t\t\t\t\t       cpu_online(8), cpu_online(9));",
            "\treturn mt6797_a72_publish_cpu9_success_state(transaction,\n\t\t\t\t\t       cpu_online(9), cpu_online(8));",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\treturn mt6797_a72_finalize_cpu9_success_state(transaction,\n\t\t\t\t\t\tcpu_online(8), cpu_online(9));",
            "\treturn mt6797_a72_finalize_cpu9_success_state(transaction,\n\t\t\t\t\t\tcpu_online(9), cpu_online(8));",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\tlockdep_assert_cpus_held();\n"
            "\treturn mt6797_a72_publish_cpu9_success_state(transaction,",
            "\tlockdep_assert_cpus_held();\n"
            "\tcpus_read_lock();\n"
            "\treturn mt6797_a72_publish_cpu9_success_state(transaction,",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\tlockdep_assert_cpus_held();\n"
            "\treturn mt6797_a72_finalize_cpu9_success_state(transaction,",
            "\tlockdep_assert_cpus_held();\n"
            "\tcpus_read_lock();\n"
            "\treturn mt6797_a72_finalize_cpu9_success_state(transaction,",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction)\n{\n\tint ret;\n\n\tcpus_read_lock();",
            "mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction)\n{\n\tint ret;\n\n\t/* ordinary lock omitted */",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction)\n{\n\tint ret;\n\n\tcpus_read_lock();",
            "mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction)\n{\n\tint ret;\n\n\t/* ordinary lock omitted */",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\t\t\tmt6797_a72_publish_cpu9_success_locked,",
            "\t\t\tmt6797_a72_membership_publish_cpu9_success,",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\t\t\tmt6797_a72_finalize_cpu9_success_locked,",
            "\t\t\tmt6797_a72_membership_finalize_cpu9_success,",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"CPU9 completion mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_completion_lock_repair_source.validate(root)
        except (ValueError, IndexError):
            rejected += 1
        else:
            raise SystemExit(f"CPU9 completion mutation escaped: {relative}: {old}")
        finally:
            path.write_text(original, encoding="utf-8")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated CPU9 completion patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated CPU9 completion patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated CPU9 completion patch file count changed")
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated CPU9 completion path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden CPU9 completion patch token: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-completion-lock-") as name:
        temporary = Path(name)
        root = temporary / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        completion_lock_repair_source_edits.apply(root)
        markers = validate_completion_lock_repair_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "The retained CPU9 ledger proves generic CPU boot, secondary\n"
            "online wait, and an IPI round-trip return before execution stops\n"
            "at membership publication. This completion path runs under the\n"
            "CPU-hotplug write lock, while both publication and the immediately\n"
            "downstream finalization helpers acquire its read side.\n\n"
            "Add lock-held publication and finalization entry points that\n"
            "assert the existing contract and call the state transitions\n"
            "directly. Keep both ordinary lock-taking helpers unchanged.\n\n"
            "This changes no CPU request, CPU_OFF, retry, cluster, reset, or\n"
            "storage path.",
            31,
        )
        changed = run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root).splitlines()
        if changed != list(CHANGED_PATHS):
            raise SystemExit(f"generated CPU9 completion file set changed: {changed}")

        generated_dir = temporary / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one CPU9 completion patch")
        patch = generated_dir / generated[0]
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            CHECKPATCH_IGNORE, str(patch), cwd=temporary,
        )

        replay = temporary / "replay"
        replay.mkdir()
        prepare_parent(source_root, replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        replay_markers = validate_completion_lock_repair_source.validate(replay)
        if replay_markers != markers:
            raise SystemExit("CPU9 completion replay markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0480",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "checkpatch_ignored=missing-signoff-file-path",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "physical_cpu_request=none-during-generation",
            "retained_ram_write=none-during-generation",
            "boot_candidate=false",
            "",
        ]), encoding="utf-8")
        sums = output / "SHA256SUMS"
        sums.write_text("\n".join([
            f"{sha256(target)}  {target.name}",
            f"{sha256(output / 'series')}  series",
            f"{sha256(provenance)}  provenance.txt",
            "",
        ]), encoding="utf-8")
        print(provenance.read_text(), end="")
        print(f"patch_sha256={sha256(target)}")
        print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
