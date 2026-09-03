#!/usr/bin/env python3
"""Generate the record-4 terminal-boundary repair patch."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_ledger_terminal_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAME = "0499-pstore-allow-preidentity-A72-hotplug-terminals.patch"
EXPECTED_SOURCE_STATE = (
    "2e81454fff42315501eaba41aa2b177671b7e178233e8039f63f0d35cb5a27dd"
)
PARENT_HASHES = {
    "include/linux/gemini_a72_hotplug_ledger.h":
        "e5a3dbe56be03821104240e984c9efc9e07072c5ce980b9da11864586c7f81fd",
    "fs/pstore/gemini_a72_hotplug_ledger_internal.h":
        "32020c335792fd068ba6ca7ab21ebdb407045e51343a5f54a2a66d60f00455ae",
    "fs/pstore/gemini_a72_hotplug_ledger.c":
        "a8b42d9e1c5d60e69246df38b59f55c0bc7f923042bed60cec6f8694c97bb68c",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c":
        "27a89ddb27924cf82ecab637f919e6de5d1dfcf71f371a1e1f05b8ef9584d63c",
}
EXPECTED_PATHS = tuple(sorted((
    "fs/pstore/gemini_a72_hotplug_ledger.c",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c",
)))
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"


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
            "Subject: [PATCH] pstore: allow preidentity A72 hotplug terminals"
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
            added.count("hotplug_down_prepare_terminal_test") == 2,
            "down-preparation proof changed",
        ),
        (
            added.count("hotplug_off_commit_terminal_test") == 2,
            "CPU_OFF-commit proof changed",
        ),
        (
            added.count("hotplug_restore_prepare_terminal_test") == 2,
            "restore-preparation proof changed",
        ),
        (
            "cpu_up(" not in added and "cpu_down(" not in added and
            "remove_cpu(" not in added and "add_cpu(" not in added,
            "CPU request added",
        ),
        (
            "psci_ops." not in added and "cpu_psci_ops." not in added and
            "arm_smccc" not in added,
            "PSCI or secure operation added",
        ),
        (
            "readl(" not in added and "writel(" not in added and
            "ioremap" not in added,
            "retained-memory operation added",
        ),
        ("smp_call_function" not in added, "retained-CPU callback added"),
        (
            "mtk_wdt_recovery_" not in added,
            "watchdog operation added",
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
        prefix="mt6797-a72-ledger-terminal-generation-"
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
            source,
            "MT6797 post-0498 hotplug-ledger parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0498.",
            "2026-09-03T20:00:00Z",
            check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run(
            "python3", str(SCRIPT_DIR / "ledger_terminal_source_edits.py"),
            "--source-root", str(source), cwd=source,
        )
        source_validation = run(
            "python3", str(SCRIPT_DIR / "validate_ledger_terminal_source.py"),
            "--source-root", str(source), cwd=source,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_ledger_terminal_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "pstore: allow preidentity A72 hotplug terminals",
            "Permit the exact terminal records emitted when down preparation,\n"
            "CPU_OFF membership commit, or restore preparation fails before\n"
            "its next identity exists. Keep normal records and all later\n"
            "terminal shapes strict, without changing the retained wire ABI.",
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
            "python3", str(SCRIPT_DIR / "validate_ledger_terminal_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_ledger_terminal_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + mutation_validation + "\n" +
            replay_validation + "\n" + replay_mutations + "\n",
            encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_public_header_sha256={PARENT_HASHES['include/linux/gemini_a72_hotplug_ledger.h']}\n"
            f"parent_internal_header_sha256={PARENT_HASHES['fs/pstore/gemini_a72_hotplug_ledger_internal.h']}\n"
            f"parent_ledger_source_sha256={PARENT_HASHES['fs/pstore/gemini_a72_hotplug_ledger.c']}\n"
            f"parent_ledger_test_sha256={PARENT_HASHES['fs/pstore/gemini_a72_hotplug_ledger_test.c']}\n"
            "generated_patch_count=1\n"
            "terminal_boundaries=down-prepare,cpu-off-commit,restore-prepare\n"
            "wire_format_changed=false\n"
            "successful_records_max=16\n"
            "successful_word_writes_max=451\n"
            "focused_kunit_cases=13\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "production_callers_added=0\n"
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
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("terminal_boundaries=down-prepare,cpu-off-commit,restore-prepare")
    print("wire_format_changed=false")
    print("successful_records_max=16")
    print("successful_word_writes_max=451")
    print("focused_kunit_cases=13")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("production_callers_added=0")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
