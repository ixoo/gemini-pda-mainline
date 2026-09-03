#!/usr/bin/env python3
"""Generate the disconnected record-4 A72 hotplug ledger patch."""

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
PATCH_NAME = "0492-pstore-add-Gemini-A72-hotplug-record-4-ledger.patch"
EXPECTED_SOURCE_STATE = (
    "5dc7d6e1dad97896ec01271103ca69be53e0d54dbe7bb7600ea91628e8aca9ff"
)
PARENT_SERIES_SHA256 = (
    "a92ea548f9f1e0913df9c6dac05ec5a28adfc4e2db0403171859b1bc2144047e"
)
PARENT_PATCH_SHA256 = (
    "8cdd4e34cdb020b30736604c44fe728dd06b4f754694caf2625bfa02555a16fd"
)
PARENT_HASHES = {
    "fs/pstore/Kconfig":
        "03f520ec5f72469b4ced3c9f72dcb8f530c95fd1305ea08230b8c141c321fa84",
    "fs/pstore/Makefile":
        "9ec55d3df2a21d3d88197e7c31fdbddea2a1c5a81463856eee83f9f0ccab5494",
}
EXPECTED_PATHS = tuple(sorted((
    "fs/pstore/Kconfig",
    "fs/pstore/Makefile",
    "fs/pstore/gemini_a72_hotplug_ledger.c",
    "fs/pstore/gemini_a72_hotplug_ledger_internal.h",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c",
    "include/linux/gemini_a72_hotplug_ledger.h",
)))
CHECKPATCH_IGNORE = (
    "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"
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
        ("Subject: [PATCH] pstore: add Gemini A72 hotplug record-4 ledger" in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in text,
         "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        (changed == EXPECTED_PATHS, "changed path set changed"),
        (added.count("writel(") == 1 and added.count("readl(") == 1,
         "retained-MMIO wrapper count changed"),
        (added.count("ioremap_wc(") == 1,
         "record-4 mapping count changed"),
        ("cpu_up(" not in added and "cpu_down(" not in added and
         "remove_cpu(" not in added and "add_cpu(" not in added,
         "CPU request added"),
        ("psci_ops." not in added and "cpu_psci_ops." not in added and
         "arm_smccc" not in added, "physical PSCI call added"),
        ("smp_call_function" not in added, "retained-CPU callback added"),
        ("mtk_wdt_recovery_takeover(" not in added,
         "watchdog takeover added"),
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
        prefix="mt6797-a72-hotplug-ledger-generation-"
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
            source, "MT6797 post-0491 record-4 parent",
            "Exact relevant source copied from the canonical prepared tree through 0491.",
            "2026-09-03T19:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        editor = str(SCRIPT_DIR / "hotplug_ledger_source_edits.py")
        validator = str(SCRIPT_DIR / "validate_hotplug_ledger_source.py")
        mutations = str(SCRIPT_DIR / "test_hotplug_ledger_source.py")
        run("python3", editor, "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", validator, "--source-root", str(source), cwd=source,
        )
        mutation_validation = run(
            "python3", mutations, "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "pstore: add Gemini A72 hotplug record-4 ledger",
            "Add an empty-only, alternating two-copy CRC ledger for the exact\n"
            "CPU9 down-and-restore lifecycle. Preserve records 0--3, bound the\n"
            "successful path to 16 commits and 451 word writes, and keep the\n"
            "new API disconnected from every production caller.",
            "2026-09-03T19:01:00Z",
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
            "python3", validator, "--source-root", str(replay), cwd=replay,
        )
        replay_mutations = run(
            "python3", mutations, "--source-root", str(replay), cwd=replay,
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
            "record_index=4\n"
            "record_base=0x44414000\n"
            "preserved_record_indices=0,1,2,3\n"
            "wire_copy_words=27\n"
            "successful_records_max=16\n"
            "successful_word_writes_max=451\n"
            "kunit_cases=10\n"
            "unsafe_mutations_rejected=20\n"
            "production_callers=0\n"
            "physical_effect_calls=0\n"
            "mt6797_cpu_can_disable=false\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [f"{sha256(path)}  {path.name}"
                for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("record_index=4")
    print("record_base=0x44414000")
    print("successful_records_max=16")
    print("successful_word_writes_max=451")
    print("kunit_cases=10")
    print("unsafe_mutations_rejected=20")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
