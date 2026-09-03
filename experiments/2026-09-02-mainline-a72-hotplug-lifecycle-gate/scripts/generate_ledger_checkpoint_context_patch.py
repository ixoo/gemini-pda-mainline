#!/usr/bin/env python3
"""Generate the record-4 target-context safety repair patch."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_ledger_checkpoint_context_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAME = "0500-pstore-make-A72-hotplug-checkpoints-nonsleeping.patch"
EXPECTED_SOURCE_STATE = (
    "4eed9151230d8187396cb73ae92b5cd70f7238cc0eb979270abb5c807d8626dd"
)
LEDGER = "fs/pstore/gemini_a72_hotplug_ledger.c"
PARENT_HASH = "74ad2662ccfa8c0a4251b9a6a8dd9c077de0dc880ef9e7a975ab52cd5a851eda"
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
    parent_path = source_root / LEDGER
    if (not parent_path.is_file() or parent_path.is_symlink() or
            sha256(parent_path) != PARENT_HASH):
        raise SystemExit("prepared ledger source changed")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-ledger-context-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        path = source / LEDGER
        path.parent.mkdir(parents=True)
        shutil.copyfile(parent_path, path)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0499 record-4 parent",
            "Exact ledger source copied from the canonical prepared tree "
            "through patch 0499.",
            "2026-09-03T18:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        run(
            "python3",
            str(SCRIPT_DIR / "ledger_checkpoint_context_source_edits.py"),
            "--source-root", str(source), cwd=source,
        )
        validation = run(
            "python3",
            str(SCRIPT_DIR / "validate_ledger_checkpoint_context_source.py"),
            "--source-root", str(source), cwd=source,
        )
        mutations = run(
            "python3",
            str(SCRIPT_DIR / "test_ledger_checkpoint_context_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "pstore: make A72 hotplug checkpoints non-sleeping",
            "Keep record-4 setup in process context, then serialize its one-shot\n"
            "checkpoint writes with a raw spin lock so the CPU9 target can\n"
            "durably publish CPU_OFF commit immediately before the PSCI call.\n"
            "Retain the fixed 4 KiB mapping until the experiment resets.",
            "2026-09-03T18:01:00Z",
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
        checkpatch = source_root / "scripts/checkpatch.pl"
        subprocess.run(
            ("perl", str(checkpatch), "--fix-inplace", "--strict", "--no-tree",
             "--ignore", CHECKPATCH_IGNORE, str(patch)),
            cwd=source_root, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        text = patch.read_text(encoding="utf-8")
        if "Signed-off-by:" in text or "/Users/" in text:
            raise SystemExit("generated patch metadata is unsafe")
        if tuple(
            line[6:] for line in text.splitlines() if line.startswith("+++ b/")
        ) != (LEDGER,):
            raise SystemExit("generated path set changed")
        run(
            "perl", str(checkpatch), "--strict", "--no-tree", "--ignore",
            CHECKPATCH_IGNORE, str(patch), cwd=source_root,
        )
        (package / "series").write_text(PATCH_NAME + "\n", encoding="utf-8")

        replay = temp / "replay"
        replay_path = replay / LEDGER
        replay_path.parent.mkdir(parents=True)
        shutil.copyfile(parent_path, replay_path)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3",
            str(SCRIPT_DIR / "validate_ledger_checkpoint_context_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        replay_mutations = run(
            "python3",
            str(SCRIPT_DIR / "test_ledger_checkpoint_context_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            validation + "\n" + mutations + "\n" + replay_validation +
            "\n" + replay_mutations + "\n", encoding="utf-8",
        )
        (package / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_ledger_sha256={PARENT_HASH}\n"
            "generated_patch_count=1\n"
            "checkpoint_lock=raw-spin-irqsave\n"
            "checkpoint_sleeping_calls=0\n"
            "terminal_iounmap_calls=0\n"
            "mapping_lifetime=one-shot-until-reset\n"
            "wire_format_changed=false\n"
            "successful_records_max=16\n"
            "successful_word_writes_max=451\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "production_callers_added=0\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n",
            encoding="utf-8",
        )
        sums = [
            f"{sha256(item)}  {item.name}"
            for item in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8",
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("checkpoint_lock=raw-spin-irqsave")
    print("checkpoint_sleeping_calls=0")
    print("terminal_iounmap_calls=0")
    print("mapping_lifetime=one-shot-until-reset")
    print("wire_format_changed=false")
    print("successful_records_max=16")
    print("successful_word_writes_max=451")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("production_callers_added=0")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
