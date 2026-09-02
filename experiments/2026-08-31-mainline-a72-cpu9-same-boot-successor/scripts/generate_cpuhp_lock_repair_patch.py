#!/usr/bin/env python3
"""Generate and audit the CPU9 CPU-hotplug lock repair patch."""

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

import cpuhp_lock_repair_source_edits
import validate_cpuhp_lock_repair_source


PATCH_NAME = "0478-arm64-mediatek-avoid-CPU9-hotplug-lock-recursion.patch"
SUBJECT = "arm64: mediatek: avoid CPU9 hotplug lock recursion"
CHANGED_PATHS = tuple(sorted(cpuhp_lock_repair_source_edits.PARENT_HASHES))
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
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-09-01T23:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T23:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in cpuhp_lock_repair_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"managed CPUHP-lock parent changed: {relative}")
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
        root, "Gemini post-0477 CPUHP-lock parent",
        "Synthetic exact-source parent only.", 40,
    )


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "#include <linux/cpuhplock.h>",
            "#include <linux/cpu.h>",
        ),
        (
            "arch/arm64/include/asm/mt6797_a72_membership.h",
            "int mt6797_a72_claim_cpu9_locked(struct mt6797_a72_transaction *transaction);",
            "int mt6797_a72_claim_cpu9_locked_missing(struct mt6797_a72_transaction *transaction);",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\tlockdep_assert_cpus_held();",
            "\t/* lock contract omitted */",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\treturn mt6797_a72_claim_cpu9_state(transaction,\n"
            "\t\t\t\t\t  cpu_online(8), cpu_online(9));",
            "\treturn mt6797_a72_membership_claim_cpu9(transaction);",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\tlockdep_assert_cpus_held();",
            "\tlockdep_assert_cpus_held();\n\tcpus_read_lock();",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction)\n"
            "{\n\tint ret;\n\n\tcpus_read_lock();",
            "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction)\n"
            "{\n\tint ret;\n\n\t/* ordinary lock omitted */",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\t.membership_claim = mt6797_a72_claim_cpu9_locked,",
            "\t.membership_claim = mt6797_a72_membership_claim_cpu9,",
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "\treturn mt6797_a72_claim_cpu9_state(transaction,\n"
            "\t\t\t\t\t  cpu_online(8), cpu_online(9));",
            "\treturn mt6797_a72_claim_cpu9_state(transaction,\n"
            "\t\t\t\t\t  cpu_online(9), cpu_online(8));",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"CPUHP-lock mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_cpuhp_lock_repair_source.validate(root)
        except (ValueError, IndexError):
            rejected += 1
        else:
            raise SystemExit(f"CPUHP-lock mutation escaped: {relative}: {old}")
        finally:
            path.write_text(original, encoding="utf-8")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated CPUHP-lock patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated CPUHP-lock patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated CPUHP-lock patch file count changed")
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated CPUHP-lock path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated CPUHP-lock token: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-cpuhp-lock-") as name:
        temporary = Path(name)
        root = temporary / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        cpuhp_lock_repair_source_edits.apply(root)
        markers = validate_cpuhp_lock_repair_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "The CPU9 binder runs from the _cpu_up() callback while the\n"
            "generic CPU-hotplug write lock is already held. Calling the\n"
            "ordinary membership helper there recursively acquires the read\n"
            "side and stalls before the CPU9 transition ledger can begin.\n\n"
            "Add an explicitly CPUHP-lock-held entry point that asserts the\n"
            "lock contract and calls the existing state transition directly.\n"
            "Keep the ordinary lock-taking helper unchanged for other callers.\n\n"
            "This changes no CPU request, CPU_OFF, retry, cluster, reset, or\n"
            "storage path.",
            41,
        )
        changed = run(
            "git", "diff", "--name-only", f"{parent}..HEAD", cwd=root
        ).splitlines()
        if changed != list(CHANGED_PATHS):
            raise SystemExit(f"generated CPUHP-lock file set changed: {changed}")

        generated_dir = temporary / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated CPUHP-lock patch")
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
        if validate_cpuhp_lock_repair_source.validate(replay) != markers:
            raise SystemExit("CPUHP-lock replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(
            f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8"
        )
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0477",
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
