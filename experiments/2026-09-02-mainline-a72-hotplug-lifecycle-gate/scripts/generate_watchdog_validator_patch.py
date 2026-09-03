#!/usr/bin/env python3
"""Generate the disconnected read-only watchdog-validator patch."""

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
PATCH_NAME = "0489-watchdog-mediatek-validate-recovery-owner-read-only.patch"
PARENT_HASHES = {
    "include/linux/mtk_wdt.h":
        "609b3dfcf4dd5974bc7fcd40a447896dc2e05a725460c10126f746b00e0ad565",
    "drivers/watchdog/mtk_wdt.c":
        "7daf615c14e7eebb065ea7a9e963e715fb163a27ddbc6a52d048ad0f0f744441",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
}
EXPECTED_SOURCE_STATE = (
    "2bde772bf62bb81910f94fcd02b814f9026c89490f6c1caae95818153e22ae47"
)
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES"


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


def copy_parent(source_root: Path, destination: Path) -> None:
    for relative in PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)


def normalize_patch_style(source_root: Path, path: Path) -> None:
    subprocess.run(
        (
            "perl", str(source_root / "scripts/checkpatch.pl"),
            "--fix-inplace", "--strict", "--no-tree", "--ignore",
            CHECKPATCH_IGNORE, str(path),
        ),
        cwd=source_root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"checkpatch style normalization lost {path.name}")


def validate_patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    checks = (
        ("watchdog: mediatek: validate recovery owner read-only" in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        ("mtk_wdt_recovery_validate" in added, "validator missing"),
        ("ops->write" not in added and "iowrite" not in added and
         "writel" not in added, "validator write added"),
        ("recovery_cancel" not in added and "recovery_refresh" not in added and
         "recovery_release" not in added, "watchdog mutation API added"),
        ("arch/arm64/kernel/mt6797_psci.c" not in text,
         "production caller changed"),
    )
    for passed, message in checks:
        if not passed:
            raise SystemExit(f"{path.name}: {message}")


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
    source_state = (source_root / ".gemini-source-state").read_text(
        encoding="utf-8").strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    for relative, expected in PARENT_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mtk-watchdog-validator-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0488 watchdog-validator parent",
            "Exact relevant source copied from the canonical prepared tree through 0488.",
            "2026-09-03T15:30:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "watchdog_validator_source_edits.py"),
            "--source-root", str(source), cwd=source)
        validation = run(
            "python3", str(SCRIPT_DIR / "validate_watchdog_validator_source.py"),
            "--source-root", str(source), "--require-tests", cwd=source,
        )
        mutations = run(
            "python3", str(SCRIPT_DIR / "test_watchdog_validator_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "watchdog: mediatek: validate recovery owner read-only",
            "Expose a locked validation call for an existing recovery owner.\n"
            "It compares the exact identity and current recovery mode and\n"
            "length using two reads and no write, reload, refresh, release,\n"
            "or ownership mutation. Keep it disconnected from CPU hotplug.",
            "2026-09-03T15:31:00Z",
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
        normalize_patch_style(source_root, patch)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", "--ignore", CHECKPATCH_IGNORE,
            str(patch), cwd=source_root,
        )
        (package / "series").write_text(PATCH_NAME + "\n", encoding="utf-8")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_watchdog_validator_source.py"),
            "--source-root", str(replay), "--require-tests", cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_watchdog_validator_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            validation + "\n" + mutations + "\n" + replay_validation +
            "\n" + replay_mutations + "\n", encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_header_sha256={PARENT_HASHES['include/linux/mtk_wdt.h']}\n"
            f"parent_driver_sha256={PARENT_HASHES['drivers/watchdog/mtk_wdt.c']}\n"
            f"parent_psci_sha256={PARENT_HASHES['arch/arm64/kernel/mt6797_psci.c']}\n"
            "generated_patch_count=1\n"
            "validation_reads=2\n"
            "validation_writes=0\n"
            "watchdog_mutations=0\n"
            "focused_kunit_cases=2\n"
            "total_watchdog_kunit_cases=7\n"
            "source_mutation_rejections=12\n"
            "production_callers=0\n"
            "mt6797_cpu_can_disable=false\n"
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
    print("validation_reads=2")
    print("validation_writes=0")
    print("watchdog_mutations=0")
    print("focused_kunit_cases=2")
    print("total_watchdog_kunit_cases=7")
    print("source_mutation_rejections=12")
    print("production_callers=0")
    print("mt6797_cpu_can_disable=false")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
