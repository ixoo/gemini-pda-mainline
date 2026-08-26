#!/usr/bin/env python3
"""Generate exact MT6797 watchdog recovery-takeover format patches."""

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
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PARENT_HASHES = {
    "drivers/watchdog/Kconfig":
        "2980fd0c63cc4a0039ab7ad1bb2a4149db74c6dedf6cadca1fcd96b281e58455",
    "drivers/watchdog/mtk_wdt.c":
        "6d17ddc7289c20c5e5427b58ad32b5475f4b298646db899380cf520d629349c7",
    "include/linux/mtk_wdt.h":
        "4f1b5a6d4cc929d5f4c7b960852bc8d9312c82618304e4cbe89901cfb99cf194",
}
PATCHES = (
    "0386-watchdog-mediatek-add-one-shot-recovery-takeover.patch",
    "0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch",
)


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


def commit(root: Path, subject: str, body: str, timestamp: str) -> None:
    run("git", "add", "--", ".", cwd=root)
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


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"exact parent changed: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def validate_patch_text(path: Path, expected_subject: str) -> None:
    text = path.read_text(encoding="utf-8")
    if f"Subject: {expected_subject}" not in text:
        raise SystemExit(f"subject changed: {path.name}")
    expected_from = (
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    )
    if expected_from not in text:
        raise SystemExit(f"synthetic archive identity changed: {path.name}")
    if "Signed-off-by:" in text:
        raise SystemExit(f"synthetic sign-off forbidden: {path.name}")
    if "device_action" in text or "/Users/" in text:
        raise SystemExit(f"private or generated evidence leaked: {path.name}")


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

    with tempfile.TemporaryDirectory(prefix="mtk-wdt-recovery-generation-") as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MediaTek watchdog post-0385 parent",
            "Exact relevant source copied from the canonical prepared tree through 0385.",
            "2026-08-27T01:10:00Z",
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT)
        production_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT,
        )
        commit(
            source, "watchdog: mediatek: add one-shot recovery takeover",
            "Add a default-off MT6797-only 15-second recovery owner that blocks\n"
            "ordinary watchdog mutations after irreversible takeover.",
            "2026-08-27T01:11:00Z",
        )

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT)
        test_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT,
        )
        commit(
            source, "watchdog: mediatek: test one-shot recovery takeover",
            "Cover exact write order, refusal, one-shot, and retained ownership\n"
            "after either hardware readback mismatch with an in-memory transport.",
            "2026-08-27T01:12:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 2:
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "[PATCH 1/2] watchdog: mediatek: add one-shot recovery takeover",
            "[PATCH 2/2] watchdog: mediatek: test one-shot recovery takeover",
        )
        for generated_name, final_name, subject in zip(
            generated, PATCHES, subjects
        ):
            target = package / final_name
            shutil.move(generated_name, target)
            validate_patch_text(target, subject)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", "MISSING_SIGN_OFF,FILE_PATH_CHANGES",
                str(target), cwd=source_root,
            )
        (package / "series").write_text(
            "\n".join(PATCHES) + "\n", encoding="utf-8"
        )

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch in PATCHES:
            run("git", "apply", "--check", str(package / patch), cwd=replay)
            run("git", "apply", str(package / patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(replay), "--phase", "tests", cwd=REPO_ROOT,
        )
        (package / "source-validation.txt").write_text(
            production_validation + "\n" + test_validation + "\n" +
            replay_validation + "\n", encoding="utf-8"
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={(source_root / '.gemini-source-state').read_text(encoding='utf-8').strip()}\n"
            f"parent_kconfig_sha256={PARENT_HASHES['drivers/watchdog/Kconfig']}\n"
            f"parent_driver_sha256={PARENT_HASHES['drivers/watchdog/mtk_wdt.c']}\n"
            f"parent_header_sha256={PARENT_HASHES['include/linux/mtk_wdt.h']}\n"
            "generated_patch_count=2\n"
            "recovery_timeout_ms=15000\n"
            "competing_operation_gates=5\n"
            "focused_kunit_cases=5\n"
            "physical_watchdog_calls=0\n"
            "production_callers=0\n"
            "native_vm_build=none\n"
            "device_action=none\n"
            "boot_candidate=false\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("focused_kunit_cases=5")
    print("physical_watchdog_calls=0")
    print("production_callers=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
