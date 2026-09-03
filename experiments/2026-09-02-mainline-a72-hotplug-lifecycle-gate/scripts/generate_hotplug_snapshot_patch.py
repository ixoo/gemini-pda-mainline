#!/usr/bin/env python3
"""Generate the disconnected MT6797 A72 hotplug snapshot patch."""

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
PATCH_NAME = "0493-soc-mediatek-add-disconnected-A72-hotplug-snapshot.patch"
EXPECTED_SOURCE_STATE = (
    "2834dc3a5ecbe213cbc17578d8276d0c7cdcf949b8687fbd145012f697b7a23c"
)
PARENT_SERIES_SHA256 = (
    "aa79ec795dfd72e884ae7850fb5a8c0c27db89bf343f795fe5b491b0bdc51a12"
)
PARENT_PATCH_SHA256 = (
    "293c013301152bcb4ccf1035e6669d262c0d1f8bbb86259a8a739fbe3db47fe8"
)
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "48a486fa0acce306e0b6650b2a15bee06deb05841ec74f4c1266bd3ef92d3abf",
    "drivers/soc/mediatek/Makefile":
        "bf1787c118c7968af10e7215dfad3fa805599aa284171c7d7b7b4c58f82697e9",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h":
        "062a14e591c5f4122cfde31f208f2f3753c116c8a5fea3ae00ab23f948be02ab",
}
EXPECTED_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-internal.h",
    "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-test.c",
    "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot.c",
)))
CHECKPATCH_IGNORE = (
    "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=env,
    )


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
        cwd=source_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit("checkpatch style normalization lost generated patch")


def validate_patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    changed = tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))
    checks = (
        (
            "Subject: [PATCH] soc: mediatek: add disconnected A72 hotplug snapshot"
            in text,
            "patch subject changed",
        ),
        (
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            "synthetic archive identity changed",
        ),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        (changed == EXPECTED_PATHS, "changed path set changed"),
        (
            added.count("mt6797_a72_platform_state_snapshot(dev, snapshot)") == 1,
            "platform snapshot call count changed",
        ),
        (
            added.count("mt6797_a72_provider_snapshot(snapshot)") == 1,
            "provider snapshot call count changed",
        ),
        (
            added.count("mt6797_dvfsp_clock_backend_read(dev, snapshot)") == 1,
            "clock backend call count changed",
        ),
        (
            added.count("mt6797_bigidvfs_backend_read(dev, snapshot)") == 1,
            "BigiDVFS backend call count changed",
        ),
        (
            "gemini_protected_readback_ledger" not in added,
            "protected-readback ledger call added",
        ),
        (
            "smp_call_function" not in added,
            "retained-CPU callback belongs to a later patch",
        ),
        (
            "cpu_up(" not in added and "cpu_down(" not in added and
            "remove_cpu(" not in added and "add_cpu(" not in added,
            "CPU request added",
        ),
        (
            "psci_ops." not in added and "cpu_psci_ops." not in added and
            "arm_smccc" not in added,
            "physical PSCI or SMC call added",
        ),
        (
            "mt6797_psci_cpu_can_disable" not in added,
            "CPU-disable veto touched",
        ),
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
        encoding="utf-8"
    ).strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    for relative, expected in PARENT_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-hotplug-snapshot-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run(
            "git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source,
        )
        commit(
            source,
            "MT6797 post-0492 hotplug-snapshot parent",
            "Exact relevant source copied from the canonical prepared tree through 0492.",
            "2026-09-03T20:00:00Z",
            check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        editor = str(SCRIPT_DIR / "hotplug_snapshot_source_edits.py")
        validator = str(SCRIPT_DIR / "validate_hotplug_snapshot_source.py")
        mutations = str(SCRIPT_DIR / "test_hotplug_snapshot_source.py")
        run("python3", editor, "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", validator, "--source-root", str(source), cwd=source
        )
        mutation_validation = run(
            "python3", mutations, "--source-root", str(source), cwd=source
        )
        commit(
            source,
            "soc: mediatek: add disconnected A72 hotplug snapshot",
            "Map one stable platform, provider, protected-clock, and BigiDVFS\n"
            "sample into the CPU9 hotplug executor readback. Hold the three\n"
            "device references for the adapter lifetime, omit the historical\n"
            "protected-readback ledger, and keep every production caller off.",
            "2026-09-03T20:01:00Z",
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
            "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
            cwd=source_root,
        )
        (package / "series").write_text(PATCH_NAME + "\n", encoding="utf-8")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", validator, "--source-root", str(replay), cwd=replay
        )
        replay_mutations = run(
            "python3", mutations, "--source-root", str(replay), cwd=replay
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + mutation_validation + "\n" +
            replay_validation + "\n" + replay_mutations + "\n",
            encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_series_sha256={PARENT_SERIES_SHA256}\n"
            f"parent_patch_sha256={PARENT_PATCH_SHA256}\n"
            "generated_patch_count=1\n"
            "component_order=platform,provider,clock,bigidvfs\n"
            "component_calls_per_snapshot=1,1,1,1\n"
            "long_lived_device_references=3\n"
            "protected_readback_checkpoints=0\n"
            "clock_transport_writes_max=401\n"
            "bigidvfs_register_reads=8\n"
            "sample_generations_in_equality=0\n"
            "focused_kunit_cases=6\n"
            "unsafe_mutations_rejected=20\n"
            "production_callers=0\n"
            "device_tree_nodes=0\n"
            "mt6797_cpu_can_disable=false\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [
            f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("component_order=platform,provider,clock,bigidvfs")
    print("component_calls_per_snapshot=1,1,1,1")
    print("long_lived_device_references=3")
    print("protected_readback_checkpoints=0")
    print("clock_transport_writes_max=401")
    print("bigidvfs_register_reads=8")
    print("focused_kunit_cases=6")
    print("unsafe_mutations_rejected=20")
    print("production_callers=0")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
