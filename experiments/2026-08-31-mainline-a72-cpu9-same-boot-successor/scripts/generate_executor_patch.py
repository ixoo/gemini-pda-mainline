#!/usr/bin/env python3
"""Generate and audit the hardware-free retained-cluster CPU9 executor patch."""

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

import executor_source_edits
import validate_executor_source


PATCH_NAME = "0466-soc-mediatek-add-hardware-free-CPU9-executor.patch"
SUBJECT = "soc: mediatek: add hardware-free CPU9 executor"
CHANGED_PATHS = (
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    *executor_source_edits.NEW_PATHS,
)
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "add_cpu(", "cpu_up(", "cpu_down(",
    "remove_cpu(", "cpu_boot(", "psci_cpu_on", "psci_cpu_off",
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
        "GIT_AUTHOR_DATE": f"2026-09-01T00:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T00:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in executor_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent source is absent: {relative}")
        if sha256(source) != expected:
            raise SystemExit(f"managed parent source changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in executor_source_edits.NEW_PATHS:
        if (source_root / relative).exists():
            raise SystemExit(f"CPU9 executor already exists in parent: {relative}")
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run("git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root)
    commit(root, "Gemini post-0465 generation parent",
           "Synthetic exact-source parent only.", 45)


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "request->members == BIT(0)",
            "request->members == BIT(1)",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "request->retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED",
            "request->retained_mask != MT6797_A72_CPU9_RETAINED_REQUIRED",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "atomic_cmpxchg(&controller->consumed, 0, 1)",
            "atomic_read(&controller->consumed)",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "ops->cpu_on(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
            "ops->cpu_on(context, MT6797_A72_CPU9_EXECUTOR_CPU8)",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "result->cpu_requests++;",
            "result->cpu_off_requests++;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "result->retained_mask = MT6797_A72_CPU9_RETAINED_REQUIRED;",
            "result->retained_mask = MT6797_A72_CPU9_RETAINED_CPU8;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "result->membership_published = true;",
            "result->membership_published = false;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor-internal.h",
            "\tint (*terminal)(void *context,",
            "\tint (*watchdog_arm)(void *context);\n"
            "\tint (*terminal)(void *context,",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-executor.c",
            "ops->membership_commit && ops->terminal;",
            "ops->terminal;",
        ),
        (
            "drivers/soc/mediatek/Kconfig",
            "\tdepends on ARM64_MT6797_A72_CPU9_MEMBERSHIP",
            "\tdepends on MTK_MT6797_A72_TRANSITION_EXECUTOR",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_executor_source.validate(root)
        except ValueError:
            rejected += 1
        finally:
            path.write_text(original, encoding="utf-8")
    if rejected != len(mutations):
        raise SystemExit("CPU9 executor mutation was not rejected")
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
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated patch path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated token: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-executor-") as name:
        temp = Path(name)
        root = temp / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        executor_source_edits.apply(root)
        markers = validate_executor_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "Add a separate atomic one-shot coordinator for the retained-\n"
            "cluster CPU9 transition. Its only injected stages are prestate,\n"
            "CPU_ON, online completion, IPI, and membership; every failure\n"
            "retains CPU8, its provider, and the cluster state.\n\n"
            "Add focused memory-only tests and no production caller, physical\n"
            "backend, CPU request, cluster effect, CPU_OFF, or retry path.",
            46,
        )
        changed = run("git", "diff", "--name-only", f"{parent}..HEAD",
                      cwd=root).splitlines()
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
        if validate_executor_source.validate(replay) != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(
            f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0465",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
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
