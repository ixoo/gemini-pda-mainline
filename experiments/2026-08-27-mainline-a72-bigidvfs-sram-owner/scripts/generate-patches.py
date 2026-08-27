#!/usr/bin/env python3
"""Generate exact MT6797 A72 BigiDVFS SRAM-owner patches."""

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
    "drivers/soc/mediatek/Kconfig":
        "4567a39059d3193f1f2dce80d5dd9a4f314e75a0ac3a8c3c6ce3c7e7ef8bba1f",
    "drivers/soc/mediatek/Makefile":
        "f7c94397db290f8181c08f38fee8c2e509db7c0d4e11680a3144cbada26fa710",
    "drivers/soc/mediatek/mt6797-bigidvfs-backend.c":
        "454c4bf3d3d049d0586a86784d0a101067005863b1e18190f9d0ddaf5be8932d",
    "include/linux/soc/mediatek/mt6797-bigidvfs-backend.h":
        "ba3430ec9e3fe54448d1c93ed744ae06e4b5c6113f800de03226105fc26f3329",
}
NEW_PATHS = (
    "drivers/soc/mediatek/mt6797-bigidvfs-sram-internal.h",
    "drivers/soc/mediatek/mt6797-bigidvfs-sram-owner-test.c",
)
PATCHES = (
    "0392-soc-mediatek-add-one-shot-A72-SRAM-LDO-owner.patch",
    "0393-soc-mediatek-test-one-shot-A72-SRAM-LDO-owner.patch",
)
CANONICAL_PATCH_DIR = REPO_ROOT / "patches/v7.1.3"


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
    parent_ready = all(
        (source_root / relative).is_file()
        and not (source_root / relative).is_symlink()
        and sha256(source_root / relative) == expected
        for relative, expected in PARENT_HASHES.items()
    ) and all(not (source_root / relative).exists() for relative in NEW_PATHS)
    for relative in PARENT_HASHES:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"source path is not an exact regular file: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if parent_ready:
        return

    for relative in NEW_PATHS:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"admitted source path is not exact: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for patch in reversed(PATCHES):
        canonical = CANONICAL_PATCH_DIR / patch
        if not canonical.is_file() or canonical.is_symlink():
            raise SystemExit(f"canonical patch unavailable: {patch}")
        run("git", "apply", "--reverse", "--check", str(canonical),
            cwd=destination)
        run("git", "apply", "--reverse", str(canonical), cwd=destination)
    for relative, expected in PARENT_HASHES.items():
        if sha256(destination / relative) != expected:
            raise SystemExit(f"reconstructed parent changed: {relative}")
    for relative in NEW_PATHS:
        if (destination / relative).exists():
            raise SystemExit(f"reconstructed parent retained new path: {relative}")


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
    if "/Users/" in text or "device_action=" in text:
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

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-bigidvfs-sram-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 BigiDVFS post-0391 parent",
            "Exact relevant source copied from the canonical prepared tree through 0391.",
            "2026-08-27T05:00:00Z",
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT)
        production_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT,
        )
        commit(
            source, "soc: mediatek: add one-shot A72 SRAM-LDO owner",
            "Extend the serialized BigiDVFS backend with one exact CPU8 SRAM\n"
            "service and independent stable selector/calibration proof.",
            "2026-08-27T05:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT)
        test_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT,
        )
        commit(
            source, "soc: mediatek: test one-shot A72 SRAM-LDO owner",
            "Cover exact order, prerequisites, one-shot sealing, all transport\n"
            "failures, instability, selector, and calibration validation.",
            "2026-08-27T05:02:00Z",
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
            "[PATCH 1/2] soc: mediatek: add one-shot A72 SRAM-LDO owner",
            "[PATCH 2/2] soc: mediatek: test one-shot A72 SRAM-LDO owner",
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
            f"parent_bigidvfs_source_sha256={PARENT_HASHES['drivers/soc/mediatek/mt6797-bigidvfs-backend.c']}\n"
            "generated_patch_count=2\n"
            "serialized_resource_owner=bigidvfs-backend\n"
            "sram_target_mv_x100=110000\n"
            "selector_expected=0x8fb\n"
            "calibration_samples=2\n"
            "focused_kunit_cases=8\n"
            "physical_effect_calls=0\n"
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
    print("serialized_resource_owner=bigidvfs-backend")
    print("focused_kunit_cases=8")
    print("physical_effect_calls=0")
    print("production_callers=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
