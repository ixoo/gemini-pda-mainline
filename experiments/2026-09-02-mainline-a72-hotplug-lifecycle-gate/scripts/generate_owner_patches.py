#!/usr/bin/env python3
"""Regenerate the CPU9 owner pair and its terminal-parent fix."""

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
PATCH_NAMES = (
    "0484-arm64-mediatek-add-hardware-free-CPU9-hotplug-owner.patch",
    "0485-arm64-mediatek-test-hardware-free-CPU9-hotplug-owner.patch",
    "0486-arm64-mediatek-validate-finalized-CPU9-before-hotplug.patch",
)
CURRENT_SOURCE_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "37ceccdad257a3365933f0c3ad1576f876eef793af4291b50b84b6dfb68c9f40",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "4b036f0f28936421d50e89a3fdd0e314332438a233171ea79f4ad4aa622467a0",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "747a6fb1ba8ecdba45b3b605d35ee32f6b136a7605a30b100e7ca4b68f6a1e90",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
}
PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "8c19c6a8ffb8d4292f65791a6edc08c73cad11c79a26b6b88e296c9d1e241d16",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "17758faa2a96b6d4eb1535ee0068b3ebae3e64bcdafae4108605f8ba1867dace",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "e7e8007c31346808d5a359e622354ca1f623a8cfd03d3168a589e2878ccdde0c",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
}
CANONICAL_PATCH_HASHES = {
    PATCH_NAMES[0]:
        "7f78083783287d2a270197fc537c1a1eba41446a5eb2182be102d44e6995af27",
    PATCH_NAMES[1]:
        "443e2983110c743ecb3f93439f71ea2631a19cc0b66cb58cb208b162487e08e7",
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


def validate_patch(path: Path, subject: str) -> None:
    text = path.read_text(encoding="utf-8")
    checks = (
        (f"Subject: [PATCH" in text and subject in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        ("psci_ops.cpu_off" not in text, "physical CPU_OFF call added"),
        ("psci_ops.affinity_info" not in text,
         "active affinity call added"),
        ("readl(" not in text and "writel(" not in text,
         "MMIO call added"),
    )
    for passed, message in checks:
        if not passed:
            raise SystemExit(f"{path.name}: {message}")


def normalize_patch_style(source_root: Path, path: Path) -> None:
    command = (
        "perl", str(source_root / "scripts/checkpatch.pl"), "--fix-inplace",
        "--strict", "--no-tree", "--ignore",
        "MISSING_SIGN_OFF,FILE_PATH_CHANGES", str(path),
    )
    subprocess.run(
        command, cwd=source_root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"checkpatch style normalization lost {path.name}")


def copy_parent(source_root: Path, destination: Path) -> None:
    for relative in PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)


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
    for relative, expected in CURRENT_SOURCE_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-hotplug-owner-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        for patch_name in reversed(PATCH_NAMES[:2]):
            run("git", "apply", "--reverse",
                str(REPO_ROOT / "patches/v7.1.3" / patch_name), cwd=source)
        for relative, expected in PARENT_HASHES.items():
            if sha256(source / relative) != expected:
                raise SystemExit(f"reconstructed source changed: {relative}")
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0483 hotplug-owner parent",
            "Exact relevant source copied from the canonical prepared tree through 0483.",
            "2026-09-03T00:10:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "owner_source_edits.py"),
            "--source-root", str(source), cwd=REPO_ROOT)
        core_validation = run(
            "python3", str(SCRIPT_DIR / "validate_owner_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source, "arm64: mediatek: add hardware-free CPU9 hotplug owner",
            "Add one-shot software ownership for a CPU9-down transaction and\n"
            "a separately identified, parent-linked CPU9 restore. Invalid\n"
            "post-commit and restore states are terminal. No callback is bound\n"
            "and no PSCI, MMIO, watchdog, CPUHP, or device effect is issued.",
            "2026-09-03T00:11:00Z",
        )

        run("python3", str(SCRIPT_DIR / "owner_test_edits.py"),
            "--source-root", str(source), cwd=REPO_ROOT)
        final_validation = run(
            "python3", str(SCRIPT_DIR / "validate_owner_source.py"),
            "--source-root", str(source), "--require-tests", cwd=REPO_ROOT,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_owner_source_validator.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source, "arm64: mediatek: test hardware-free CPU9 hotplug owner",
            "Cover exact down/restore success, entry rejection, reversible\n"
            "pre-commit failure, terminal post-commit failure, and terminal\n"
            "restore failure without invoking any physical transition.",
            "2026-09-03T00:12:00Z",
        )
        owner_head = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "owner_terminal_parent_fix_edits.py"),
            "--source-root", str(source), cwd=REPO_ROOT)
        fixed_validation = run(
            "python3", str(SCRIPT_DIR / "validate_owner_source.py"),
            "--source-root", str(source), "--require-tests",
            "--require-terminal-parent-fix", cwd=REPO_ROOT,
        )
        fixed_mutation_validation = run(
            "python3",
            str(SCRIPT_DIR / "test_owner_terminal_parent_validator.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source,
            "arm64: mediatek: validate finalized CPU9 before hotplug",
            "Preserve the active CPU9 parent predicate and add a separate\n"
            "terminal validator for the finalized CPU8/CPU9 pair. This lets\n"
            "CPU9-down mint only from the intended post-bring-up state while\n"
            "continuing to reject missing, aliased, or malformed records.",
            "2026-09-03T00:13:00Z",
        )

        owner_patch_dir = temp / "owner-patches"
        owner_generated = sorted(run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(owner_patch_dir), f"{parent}..{owner_head}", cwd=source,
        ).splitlines())
        fix_patch_dir = temp / "fix-patch"
        fix_generated = sorted(run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(fix_patch_dir), f"{owner_head}..HEAD", cwd=source,
        ).splitlines())
        generated = owner_generated + fix_generated
        if len(generated) != len(PATCH_NAMES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "arm64: mediatek: add hardware-free CPU9 hotplug owner",
            "arm64: mediatek: test hardware-free CPU9 hotplug owner",
            "arm64: mediatek: validate finalized CPU9 before hotplug",
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
                "--no-tree", "--ignore", "MISSING_SIGN_OFF,FILE_PATH_CHANGES",
                str(patch), cwd=source_root,
            )
            canonical_hash = CANONICAL_PATCH_HASHES.get(patch_name)
            if canonical_hash and sha256(patch) != canonical_hash:
                raise SystemExit(f"canonical patch changed: {patch_name}")
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
            "python3", str(SCRIPT_DIR / "validate_owner_source.py"),
            "--source-root", str(replay), "--require-tests",
            "--require-terminal-parent-fix", cwd=REPO_ROOT,
        )
        (package / "source-validation.txt").write_text(
            core_validation + "\n" + final_validation + "\n" +
            mutation_validation + "\n" + fixed_validation + "\n" +
            fixed_mutation_validation + "\n" + replay_validation + "\n",
            encoding="utf-8",
        )
        source_state = (source_root / ".gemini-source-state").read_text(
            encoding="utf-8").strip()
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_membership_header_sha256="
            f"{PARENT_HASHES['arch/arm64/include/asm/mt6797_a72_membership.h']}\n"
            f"parent_membership_source_sha256="
            f"{PARENT_HASHES['arch/arm64/kernel/mt6797_a72_membership.c']}\n"
            f"parent_membership_test_sha256="
            f"{PARENT_HASHES['arch/arm64/kernel/mt6797_a72_membership_test.c']}\n"
            "generated_patch_count=3\n"
            f"canonical_patch_0484_sha256={CANONICAL_PATCH_HASHES[PATCH_NAMES[0]]}\n"
            f"canonical_patch_0485_sha256={CANONICAL_PATCH_HASHES[PATCH_NAMES[1]]}\n"
            "cpu9_down_attempts=1\n"
            "affinity_attempts=1\n"
            "cpu9_restore_attempts=1\n"
            "precommit_failure=rejected-without-membership-change\n"
            "postcommit_failure=reset-only-fault\n"
            "restore_identity=distinct-and-parent-linked\n"
            "focused_kunit_cases=5\n"
            "owner_source_mutation_rejections=21\n"
            "owner_terminal_parent_mutation_rejections=6\n"
            "terminal_parent_validation=pass\n"
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
    print("generated_patch_count=3")
    print("cpu9_down_attempts=1")
    print("affinity_attempts=1")
    print("cpu9_restore_attempts=1")
    print("precommit_failure=rejected-without-membership-change")
    print("postcommit_failure=reset-only-fault")
    print("restore_identity=distinct-and-parent-linked")
    print("focused_kunit_cases=5")
    print("owner_source_mutation_rejections=21")
    print("owner_terminal_parent_mutation_rejections=6")
    print("terminal_parent_validation=pass")
    print("mt6797_callbacks=unset")
    print("mt6797_cpu_can_disable=false")
    print("physical_effect_calls=0")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
