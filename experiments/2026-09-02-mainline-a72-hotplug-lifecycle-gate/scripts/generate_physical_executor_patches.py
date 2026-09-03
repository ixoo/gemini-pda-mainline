#!/usr/bin/env python3
"""Generate the disconnected CPU9 physical-executor patch pair."""

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
PATCH_NAMES = (
    "0487-soc-mediatek-add-hardware-free-CPU9-hotplug-executor.patch",
    "0488-soc-mediatek-test-hardware-free-CPU9-hotplug-executor.patch",
)
PARENT_HASHES = {
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
    "drivers/soc/mediatek/Kconfig":
        "0b5849a7e061cf9a79d687a5960ae31ba723edf5000ea18e84b7ee4aa9a22df8",
    "drivers/soc/mediatek/Makefile":
        "15795d607de9b991f289a15f52fb280f853beef4f4c6e50b6d8a73897443a066",
}
EXPECTED_SOURCE_STATE = (
    "d33e9545e32bea6eb7591b9eca2bb84a7a8a8c8ad0b2e2c0b7363c8a9c0e0a07"
)
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES,OPEN_ENDED_LINE"


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


def validate_patch(path: Path, subject: str) -> None:
    text = path.read_text(encoding="utf-8")
    checks = (
        ("Subject: [PATCH" in text and subject in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        ("psci_ops." not in text, "physical PSCI call added"),
        ("arm_smccc" not in text, "direct secure call added"),
        ("readl(" not in text and "writel(" not in text,
         "MMIO call added"),
        ("mtk_wdt_recovery_takeover" not in text,
         "watchdog mutation added"),
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
        prefix="mt6797-a72-physical-executor-generation-"
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
            source, "MT6797 post-0486 physical-executor parent",
            "Exact relevant source copied from the canonical prepared tree through 0486.",
            "2026-09-03T02:10:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "physical_executor_source_edits.py"),
            "--source-root", str(source), cwd=source)
        core_validation = run(
            "python3", str(SCRIPT_DIR / "validate_physical_executor_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: add hardware-free CPU9 hotplug executor",
            "Add a disconnected, operation-injected state machine for the\n"
            "split controller, target CPU9, and retained CPU8 lifecycle. It\n"
            "authorizes one CPU_OFF and validates one affinity result without\n"
            "binding callbacks or issuing PSCI, MMIO, watchdog, or CPU calls.",
            "2026-09-03T02:11:00Z",
        )

        run("python3", str(SCRIPT_DIR / "physical_executor_test_edits.py"),
            "--source-root", str(source), cwd=source)
        final_validation = run(
            "python3", str(SCRIPT_DIR / "validate_physical_executor_source.py"),
            "--source-root", str(source), "--require-tests", cwd=source,
        )
        mutation_validation = run(
            "python3",
            str(SCRIPT_DIR / "test_physical_executor_source_validator.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: test hardware-free CPU9 hotplug executor",
            "Cover exact success, entry rejection, pre- and post-commit\n"
            "failure, readback mismatch, call budgets, and one-shot ordering\n"
            "using injected memory-only operations.",
            "2026-09-03T02:12:00Z",
        )

        patch_dir = temp / "patches"
        generated = sorted(run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines())
        if len(generated) != len(PATCH_NAMES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "soc: mediatek: add hardware-free CPU9 hotplug executor",
            "soc: mediatek: test hardware-free CPU9 hotplug executor",
        )
        for generated_name, patch_name, subject in zip(
            generated, PATCH_NAMES, subjects
        ):
            patch = package / patch_name
            shutil.move(generated_name, patch)
            normalize_patch_style(source_root, patch)
            validate_patch(patch, subject)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", CHECKPATCH_IGNORE,
                str(patch), cwd=source_root,
            )
        (package / "series").write_text(
            "\n".join(PATCH_NAMES) + "\n", encoding="utf-8")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch_name in PATCH_NAMES:
            patch = package / patch_name
            run("git", "apply", "--check", str(patch), cwd=replay)
            run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_physical_executor_source.py"),
            "--source-root", str(replay), "--require-tests", cwd=replay,
        )
        replay_mutations = run(
            "python3",
            str(SCRIPT_DIR / "test_physical_executor_source_validator.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            core_validation + "\n" + final_validation + "\n" +
            mutation_validation + "\n" + replay_validation + "\n" +
            replay_mutations + "\n", encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_psci_sha256={PARENT_HASHES['arch/arm64/kernel/mt6797_psci.c']}\n"
            f"parent_kconfig_sha256={PARENT_HASHES['drivers/soc/mediatek/Kconfig']}\n"
            f"parent_makefile_sha256={PARENT_HASHES['drivers/soc/mediatek/Makefile']}\n"
            "generated_patch_count=2\n"
            "cpu_off_authorizations=1\n"
            "affinity_call_sites=1\n"
            "post_affinity_snapshots=1\n"
            "cpu8_callbacks=1\n"
            "watchdog_mutations=0\n"
            "focused_kunit_cases=8\n"
            "source_mutation_rejections=18\n"
            "production_callbacks_bound=false\n"
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
    print("generated_patch_count=2")
    print("cpu_off_authorizations=1")
    print("affinity_call_sites=1")
    print("post_affinity_snapshots=1")
    print("cpu8_callbacks=1")
    print("watchdog_mutations=0")
    print("focused_kunit_cases=8")
    print("source_mutation_rejections=18")
    print("production_callbacks_bound=false")
    print("mt6797_cpu_can_disable=false")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
