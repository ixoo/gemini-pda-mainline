#!/usr/bin/env python3
"""Generate the disconnected CPU9 one-task binder-core patch pair."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from test_binder_core_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAMES = (
    "0497-soc-mediatek-add-disconnected-A72-hotplug-binder-core.patch",
    "0498-soc-mediatek-test-disconnected-A72-hotplug-binder-core.patch",
)
EXPECTED_SOURCE_STATE = (
    "febbcbb48905cdba86af117b2774bfcc79d1126ca80620126adaecac2a83ac89"
)
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "3b5986c9887cbe6e94f661ecd6d53d76756d27d0ae11a076746989c389699f58",
    "drivers/soc/mediatek/Makefile":
        "5c48e82dd073c7268f4daf4641278c853e73c1b6346af291e699b96d80af2446",
    "include/linux/soc/mediatek/mt6797-a72-binder.h":
        "0a18e4e05394c3425e43636eed4be3ab420648f16e9919ad2cc5960f43e72086",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "521d061e20584d518f027e40f0c8a1165a4ac11221c705227d260cbe04440dbb",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h":
        "062a14e591c5f4122cfde31f208f2f3753c116c8a5fea3ae00ab23f948be02ab",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h":
        "9b13ef4b20f85cfb638d2e47b01cb4f767b6c34d39d5006de10f11df6258c79b",
}
IMPLEMENTATION_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c",
)))
TEST_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-test.c",
)))
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"


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


def validate_patch(path: Path, subject: str,
                   expected_paths: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    changed = tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))
    direct_cpu_call = re.search(
        r"(?m)^[ \t]*(?:return[ \t]+)?"
        r"(?:cpu_up|cpu_down|add_cpu|remove_cpu)[ \t]*\(",
        added,
    )
    checks = (
        ("Subject: [PATCH" in text and subject in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        (changed == expected_paths, "changed path set changed"),
        ("psci_ops." not in added and "cpu_psci_ops." not in added,
         "physical PSCI operation added"),
        ("arm_smccc" not in added, "direct secure call added"),
        (direct_cpu_call is None, "production CPU request added"),
        ("readl(" not in added and "writel(" not in added and
         "ioremap" not in added, "MMIO operation added"),
        ("mtk_wdt_recovery_" not in added,
         "production watchdog operation added"),
        ("gemini_a72_hotplug_ledger_owner_" not in added,
         "production retained-memory operation added"),
        ("platform_driver" not in added, "production caller added"),
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
        prefix="mt6797-a72-hotplug-binder-core-generation-"
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
            source, "MT6797 post-0496 hotplug-binder parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0496.",
            "2026-09-03T12:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "binder_core_source_edits.py"),
            "--source-root", str(source), cwd=source)
        core_validation = run(
            "python3", str(SCRIPT_DIR / "validate_binder_core_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: add disconnected A72 hotplug binder core",
            "Add an operation-injected, one-shot coordinator for one exact\n"
            "same-task CPU9 down and parent-linked CPU9 restore sequence.\n"
            "Validate the parent, down, and restore identities while keeping\n"
            "all physical and production operations disconnected.",
            "2026-09-03T12:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "binder_core_test_edits.py"),
            "--source-root", str(source), cwd=source)
        final_validation = run(
            "python3", str(SCRIPT_DIR / "validate_binder_core_source.py"),
            "--source-root", str(source), "--require-tests", cwd=source,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_binder_core_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: test disconnected A72 hotplug binder core",
            "Cover exact parent linkage, same-task and one-shot ownership,\n"
            "ordered checkpoints, precommit rejection, postcommit and restore\n"
            "faults, terminal publication, and injected operation counts.",
            "2026-09-03T12:02:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != len(PATCH_NAMES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "soc: mediatek: add disconnected A72 hotplug binder core",
            "soc: mediatek: test disconnected A72 hotplug binder core",
        )
        expected_paths = (IMPLEMENTATION_PATHS, TEST_PATHS)
        for generated_name, patch_name, subject, paths in zip(
            generated, PATCH_NAMES, subjects, expected_paths
        ):
            patch = package / patch_name
            shutil.move(generated_name, patch)
            normalize_patch_style(source_root, patch)
            validate_patch(patch, subject, paths)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
                cwd=source_root,
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
            "python3", str(SCRIPT_DIR / "validate_binder_core_source.py"),
            "--source-root", str(replay), "--require-tests", cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_binder_core_source.py"),
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
            f"parent_kconfig_sha256={PARENT_HASHES['drivers/soc/mediatek/Kconfig']}\n"
            f"parent_makefile_sha256={PARENT_HASHES['drivers/soc/mediatek/Makefile']}\n"
            f"parent_binder_header_sha256={PARENT_HASHES['include/linux/soc/mediatek/mt6797-a72-binder.h']}\n"
            f"parent_membership_sha256={PARENT_HASHES['arch/arm64/include/asm/mt6797_a72_membership.h']}\n"
            f"parent_down_executor_sha256={PARENT_HASHES['drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h']}\n"
            f"parent_restore_executor_sha256={PARENT_HASHES['drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h']}\n"
            "generated_patch_count=2\n"
            "target_cpu=9\n"
            "same_task_required=true\n"
            "ordered_requests=remove9,add9-restore\n"
            "parent_proof_calls=1\n"
            "ledger_begin_calls=1\n"
            "checkpoint_stages=1,13,17\n"
            "remove_cpu_call_sites=1\n"
            "restore_add_cpu_call_sites=1\n"
            "focused_kunit_cases=9\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "production_callers=0\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [
            f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8")
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("target_cpu=9")
    print("same_task_required=true")
    print("ordered_requests=remove9,add9-restore")
    print("parent_proof_calls=1")
    print("ledger_begin_calls=1")
    print("checkpoint_stages=1,13,17")
    print("remove_cpu_call_sites=1")
    print("restore_add_cpu_call_sites=1")
    print("focused_kunit_cases=9")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
