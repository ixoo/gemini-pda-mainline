#!/usr/bin/env python3
"""Generate the disconnected CPU9 restore-executor patch pair."""

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
    "0495-soc-mediatek-add-disconnected-CPU9-restore-executor.patch",
    "0496-soc-mediatek-test-disconnected-CPU9-restore-executor.patch",
)
EXPECTED_SOURCE_STATE = (
    "751075a092cad2c6fedd39e599839e8881b076d808fc6e4bab30f322868603ae"
)
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "10f143fc6da8107ba74e637ed1c618e6cd408ec4906bfab726ea862fef014d45",
    "drivers/soc/mediatek/Makefile":
        "3757141478a0765a93456b93c65f4621d42d89b6dfc9c563f0b901b8908b4d3e",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "521d061e20584d518f027e40f0c8a1165a4ac11221c705227d260cbe04440dbb",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h":
        "062a14e591c5f4122cfde31f208f2f3753c116c8a5fea3ae00ab23f948be02ab",
}
IMPLEMENTATION_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h",
    "drivers/soc/mediatek/mt6797-a72-restore-executor.c",
)))
TEST_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c",
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
        ("cpu_up(" not in added and "cpu_down(" not in added and
         "add_cpu(" not in added and "remove_cpu(" not in added,
         "production CPU request added"),
        ("readl(" not in added and "writel(" not in added and
         "ioremap" not in added, "MMIO operation added"),
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
        prefix="mt6797-a72-restore-executor-generation-"
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
            source, "MT6797 post-0494 restore-executor parent",
            "Exact relevant source copied from the canonical prepared tree through 0494.",
            "2026-09-03T05:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "restore_executor_source_edits.py"),
            "--source-root", str(source), cwd=source)
        core_validation = run(
            "python3", str(SCRIPT_DIR / "validate_restore_executor_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: add disconnected CPU9 restore executor",
            "Add a one-shot, operation-injected state machine for the exact\n"
            "retired CPU9-down parent. Consume one CPU_ON budget only after\n"
            "its durable checkpoint and require secondary plus full restore\n"
            "completion, while keeping all physical operations disconnected.",
            "2026-09-03T05:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "restore_executor_test_edits.py"),
            "--source-root", str(source), cwd=source)
        final_validation = run(
            "python3", str(SCRIPT_DIR / "validate_restore_executor_source.py"),
            "--source-root", str(source), "--require-tests", cwd=source,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_restore_executor_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: test disconnected CPU9 restore executor",
            "Cover exact parent and restore identity, the one CPU_ON budget,\n"
            "checkpoint ordering, secondary and full completion, rollback\n"
            "ownership, one-shot behavior, and publication failures using\n"
            "injected memory-only operations.",
            "2026-09-03T05:02:00Z",
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
            "soc: mediatek: add disconnected CPU9 restore executor",
            "soc: mediatek: test disconnected CPU9 restore executor",
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
            "python3", str(SCRIPT_DIR / "validate_restore_executor_source.py"),
            "--source-root", str(replay), "--require-tests", cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_restore_executor_source.py"),
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
            f"parent_membership_sha256={PARENT_HASHES['arch/arm64/include/asm/mt6797_a72_membership.h']}\n"
            f"parent_down_executor_sha256={PARENT_HASHES['drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h']}\n"
            "generated_patch_count=2\n"
            "target_cpu=9\n"
            "identity=distinct-parent-linked-restore\n"
            "cpu_on_call_sites=1\n"
            "preterminal_checkpoints=3\n"
            "ledger_stages=14,15,16,17\n"
            "terminal_members=0x3\n"
            "rollback_suppresses_initial_p32=true\n"
            "focused_kunit_cases=10\n"
            f"unsafe_mutations_rejected={len(__import__('test_restore_executor_source').MUTATIONS)}\n"
            "production_callers=0\n"
            "device_tree_nodes=0\n"
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
    print("identity=distinct-parent-linked-restore")
    print("cpu_on_call_sites=1")
    print("preterminal_checkpoints=3")
    print("ledger_stages=14,15,16,17")
    print("terminal_members=0x3")
    print("rollback_suppresses_initial_p32=true")
    print("focused_kunit_cases=10")
    print("unsafe_mutations_rejected=32")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
