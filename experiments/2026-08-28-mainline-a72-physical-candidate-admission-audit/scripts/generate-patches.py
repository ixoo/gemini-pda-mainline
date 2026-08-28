#!/usr/bin/env python3
"""Generate the two-patch source-derived CPU8 admission series."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from source_edits import PARENT_HASHES


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
TEST_REFERENCE = EXPERIMENT / "kernel/mt6797-a72-derived-admission-test.c"
PATCHES = (
    "0407-arm64-mediatek-derive-CPU8-admission-from-current-boot-state.patch",
    "0408-arm64-mediatek-test-source-derived-CPU8-admission.patch",
)
SUBJECTS = (
    "arm64: mediatek: derive CPU8 admission from current-boot state",
    "arm64: mediatek: test source-derived CPU8 admission",
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


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(source)
        if actual != expected:
            raise SystemExit(
                f"source hash changed: {relative}: {actual} != {expected}"
            )
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


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
    patch = path.read_text(encoding="utf-8")
    require = (
        subject,
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>",
    )
    for token in require:
        if token not in patch:
            raise SystemExit(f"patch token changed in {path.name}: {token}")
    for forbidden in ("Signed-off-by:", "/Users/", "device_action="):
        if forbidden in patch:
            raise SystemExit(f"forbidden patch token in {path.name}: {forbidden}")


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
    state_path = source_root / ".gemini-source-state"
    if not state_path.is_file() or state_path.is_symlink():
        raise SystemExit("prepared source state is unavailable")
    if not TEST_REFERENCE.is_file() or TEST_REFERENCE.is_symlink():
        raise SystemExit("derived admission test reference is unavailable")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-derived-admission-generation-"
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
            source,
            "MT6797 source-derived admission post-0406 parent",
            "Exact relevant source copied from the canonical prepared tree through 0406.",
            "2026-08-28T16:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"),
            "--source-root", str(source), "--stage", "production",
            cwd=REPO_ROOT)
        production_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(source), "--stage", "production",
            cwd=REPO_ROOT,
        )
        commit(
            source, SUBJECTS[0],
            "Replace caller-predicted A36 recovery assertions with one exact\n"
            "owner-derived CPU8 transaction from the composed boot snapshot.",
            "2026-08-28T16:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "source_edits.py"),
            "--source-root", str(source), "--stage", "tests",
            "--test-reference", str(TEST_REFERENCE), cwd=REPO_ROOT)
        test_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(source), "--stage", "tests",
            cwd=REPO_ROOT,
        )
        commit(
            source, SUBJECTS[1],
            "Exercise exact derivation, source and READY rejection, obsolete\n"
            "assertion refusal, and repeat closure without a CPU operation.",
            "2026-08-28T16:02:00Z",
        )

        generated_dir = temp / "generated"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != len(PATCHES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        targets: list[Path] = []
        for generated_path, name_out, subject in zip(
            generated, PATCHES, SUBJECTS, strict=True
        ):
            target = package / name_out
            shutil.move(generated_path, target)
            validate_patch(target, subject)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"),
                "--strict", "--no-tree", "--ignore",
                "MISSING_SIGN_OFF,FILE_PATH_CHANGES", str(target),
                cwd=source_root,
            )
            targets.append(target)

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for target in targets:
            run("git", "apply", "--check", str(target), cwd=replay)
            run("git", "apply", str(target), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), "--stage", "tests",
            cwd=REPO_ROOT,
        )
        (package / "series").write_text(
            "\n".join(PATCHES) + "\n", encoding="utf-8"
        )
        (package / "source-validation.txt").write_text(
            production_validation + "\n" + test_validation + "\n" +
            replay_validation + "\n", encoding="utf-8"
        )
        (package / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={state_path.read_text(encoding='utf-8').strip()}\n"
            "generated_patch_count=2\n"
            "derived_production_entries=1\n"
            "derived_kunit_cases=5\n"
            "caller_identity_words=0\n"
            "caller_page_recovery_assertions=0\n"
            "production_cpu_requests=0\n"
            "cpu_off_call_sites=0\n"
            "retry_call_sites=0\n"
            "native_vm_build=none\n"
            "device_action=none\n"
            "boot_candidate=false\n",
            encoding="utf-8",
        )
        checksummed = [*targets, package / "series",
                       package / "source-validation.txt",
                       package / "provenance.txt"]
        (package / "SHA256SUMS").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
            encoding="utf-8",
        )
        shutil.copytree(package, output)


if __name__ == "__main__":
    main()
