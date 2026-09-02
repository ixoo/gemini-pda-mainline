#!/usr/bin/env python3
"""Generate the exact generic CPU-down lifecycle handoff patch."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PATCH_NAME = "0483-arm64-add-CPU-down-lifecycle-handoffs.patch"
PARENT_HASHES = {
    "include/linux/cpu.h":
        "555a9a2f854335be8126823faee5af771bcd536073297f43bb775dd9f1e32d84",
    "kernel/cpu.c":
        "bb87f455ebdd3e2b74befbd097a3a35723ac6350cafbd322aa3caffa4f6b7302",
    "arch/arm64/include/asm/cpu_ops.h":
        "8148d875ffa9110d8c7d9f4fe4121ac6441c541392d5c09381693fa02825ac64",
    "arch/arm64/kernel/smp.c":
        "90ca49f088b2ea697d7c35b1340a985e5119a5fe71dd9c0713e1c703632beb2f",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args, cwd=cwd, env=env, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if completed.returncode:
        if completed.stdout:
            print(completed.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(
            f"command failed ({completed.returncode}): {' '.join(args)}"
        )
    return completed.stdout.strip()


def commit(root: Path, subject: str, body: str, timestamp: str,
           check_diff: bool = True) -> None:
    run("git", "add", "--", ".", cwd=root)
    if check_diff:
        run("git", "diff", "--cached", "--check", cwd=root)
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": timestamp,
        "GIT_COMMITTER_DATE": timestamp,
    })
    run("git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=env)


def validate_patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    checks = (
        ("Subject: [PATCH] arm64: add CPU-down lifecycle handoffs" in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        ("mt6797_psci_cpu_can_disable" not in text,
         "MT6797 disable veto touched"),
        ("psci" not in text.lower(), "physical PSCI path touched"),
    )
    for passed, message in checks:
        if not passed:
            raise SystemExit(message)


def main() -> None:
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

    for relative, expected in PARENT_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-down-lifecycle-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        for relative in PARENT_HASHES:
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0482 down-lifecycle parent",
            "Exact relevant source copied from the canonical prepared tree through 0482.",
            "2026-09-02T23:10:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"),
            "--source-root", str(source), cwd=REPO_ROOT)
        source_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_source_validator.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source, "arm64: add CPU-down lifecycle handoffs",
            "Add no-op-by-default controller callbacks before CPU-map locking,\n"
            "after locked validation, and after full CPUHP down completion.\n\n"
            "No architecture operation table binds the callbacks in this patch.",
            "2026-09-02T23:11:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        patch = package / PATCH_NAME
        shutil.move(generated[0], patch)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", "--ignore", "MISSING_SIGN_OFF,FILE_PATH_CHANGES",
            str(patch), cwd=source_root,
        )
        (package / "series").write_text(PATCH_NAME + "\n", encoding="utf-8")

        replay = temp / "replay"
        for relative in PARENT_HASHES:
            target = replay / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + mutation_validation + "\n" +
            replay_validation + "\n", encoding="utf-8",
        )
        source_state = (source_root / ".gemini-source-state").read_text(
            encoding="utf-8").strip()
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_kernel_cpu_sha256={PARENT_HASHES['kernel/cpu.c']}\n"
            f"parent_arm64_smp_sha256={PARENT_HASHES['arch/arm64/kernel/smp.c']}\n"
            "generated_patch_count=1\n"
            "preflight=before-cpu-map-lock\n"
            "validate=after-cpu-map-lock-before-cpu-hotplug-write-lock\n"
            "complete=after-full-down-before-cpu-hotplug-write-unlock\n"
            "failed=after-cpu-map-lock-release-on-nonzero-result\n"
            "source_mutation_rejections=10\n"
            "weak_defaults=no-op\n"
            "mt6797_callbacks=unset\n"
            "mt6797_cpu_can_disable=false\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [f"{sha256(path)}  {path.name}"
                for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8")
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("preflight=before-cpu-map-lock")
    print("validate=after-cpu-map-lock-before-cpu-hotplug-write-lock")
    print("complete=after-full-down-before-cpu-hotplug-write-unlock")
    print("failed=after-cpu-map-lock-release-on-nonzero-result")
    print("source_mutation_rejections=10")
    print("weak_defaults=no-op")
    print("mt6797_callbacks=unset")
    print("mt6797_cpu_can_disable=false")
    print("physical_effect_calls=0")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
