#!/usr/bin/env python3
"""Generate and audit the owner-local Gemini CPU9 membership patch."""

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

import membership_source_edits
import validate_membership_source


PATCH_NAME = "0464-arm64-mediatek-add-owner-local-CPU9-membership.patch"
SUBJECT = "arm64: mediatek: add owner-local CPU9 membership"
CHANGED_PATHS = membership_source_edits.CHANGED_PATHS
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "add_cpu(", "cpu_up(", "cpu_down(",
    "cpu_boot(", "psci_cpu_on", "psci_cpu_off", "cpu_off(",
    "arm_smccc", "regmap_write(", "kernel_restart(",
)


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
        "GIT_AUTHOR_DATE": f"2026-09-01T01:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T01:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in membership_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent source is absent or unsafe: {relative}")
        if sha256(source) != expected:
            raise SystemExit(f"managed parent source changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(root, "Gemini post-0463 generation parent",
           "Synthetic exact-source parent only.", 10)


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "parent->members != BIT(0)", "parent->members != 0", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "(parent->attempts_consumed & MT6797_A72_ATTEMPT_CPU9_UP)",
            "!(parent->attempts_consumed & MT6797_A72_ATTEMPT_CPU9_UP)", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "!cpu8->cpu8_success_published || cpu8->cpu9_success_published",
            "cpu8->cpu8_success_published || cpu8->cpu9_success_published", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "topology->cpu8_online != 1 || topology->cpu9_online",
            "topology->cpu8_online != 1 || !topology->cpu9_online", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "budgets->preparation == MT6797_A72_BUDGET_NONE",
            "budgets->preparation == MT6797_A72_BUDGET_AVAILABLE", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "!a72_owner.active.cpu9_success_published &&\n"
            "\t    cpu8_online && !cpu9_online) {\n"
            "\t\ta72_owner.active.budgets.cpu_on = "
            "MT6797_A72_BUDGET_CONSUMED;",
            "!a72_owner.active.cpu9_success_published &&\n"
            "\t    cpu8_online && !cpu9_online) {\n"
            "\t\ta72_owner.active.budgets.cpu_on = "
            "MT6797_A72_BUDGET_AVAILABLE;", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "a72_owner.active.cpu9_success_published = 1;",
            "a72_owner.active.cpu9_success_published = 0;", 1,
        ),
        (
            "arch/arm64/kernel/mt6797_a72_membership.c",
            "a72_owner.members = BIT(0) | BIT(1);",
            "a72_owner.members = BIT(0);", 1,
        ),
    )
    rejected = 0
    for relative, old, new, count in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != count:
            raise SystemExit(f"mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_membership_source.validate(root)
        except (SystemExit, ValueError):
            rejected += 1
        finally:
            path.write_text(original, encoding="utf-8")
    if rejected != len(mutations):
        raise SystemExit("CPU9 membership mutation was not rejected")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated patch file count changed")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated token: {token}")
    removals = [
        line for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    if removals != ["-#define MT6797_A72_TRANSACTION_ABI 3"]:
        raise SystemExit(f"unexpected parent source removal: {removals}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-membership-") as name:
        temp = Path(name)
        root = temp / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        membership_source_edits.apply(root)
        markers = validate_membership_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "Derive one CPU9 transaction only from the exact retired CPU8\n"
            "success, held provider identity, member bit 0, live CPU8, and a\n"
            "fresh CPU9 attempt. Add CPU9-specific publish, claim, reject,\n"
            "CPU_ON-budget, and success-finalization owner entry points.\n\n"
            "Give CPU9 no cluster-effect, provider, CPU_OFF, retry, watchdog,\n"
            "or physical request path, and preserve the CPU8 function bodies.",
            11,
        )
        changed = run(
            "git", "diff", "--name-only", f"{parent}..HEAD", cwd=root
        ).splitlines()
        if changed != sorted(CHANGED_PATHS):
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = temp / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated patch")
        patch = generated_dir / generated[0]
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES", str(patch), cwd=temp,
        )

        replay = temp / "replay"
        replay.mkdir()
        prepare_parent(source_root, replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        replay_markers = validate_membership_source.validate(replay)
        if replay_markers != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        series = output / "series"
        series.write_text(f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0463",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "cpu8_function_bodies=unchanged",
            "pstore_record0=unchanged",
            "pstore_record1=unchanged",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "boot_candidate=false",
            "",
        ]), encoding="utf-8")
        sums = output / "SHA256SUMS"
        inputs = (target, series, provenance)
        sums.write_text("".join(
            f"{sha256(path)}  {path.name}\n" for path in inputs
        ), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
