#!/usr/bin/env python3
"""Generate and replay the source-only slice-4 planner patch."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import planner_edits


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH = "0428-arm64-finalize-late-CPU-pure-plan-identities.patch"
SUBJECT = "arm64: finalize late CPU pure plan identities"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, env=env, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode:
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in planner_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"prepared source changed: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def commit(root: Path) -> str:
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": "2026-08-29T19:00:00Z",
        "GIT_COMMITTER_DATE": "2026-08-29T19:00:00Z",
    })
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", SUBJECT,
        "-m", "Compute prospective native and compat HWCAP intersections from\n"
        "sanitized system state and complete per-target register images. Hash\n"
        "evidence and pure plan outputs using domain-separated named fields.\n\n"
        "Keep architecture commit, READY, and every CPU request absent.",
        cwd=root, env=env,
    )
    return run("git", "rev-parse", "HEAD", cwd=root)


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated patch From changed")
    text = path.read_text()
    for forbidden in (
        "Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_off", "boot2", "ARM64_LATE_CPU_PROFILE_READY +",
    ):
        if forbidden in text:
            raise SystemExit(f"forbidden generated patch token: {forbidden}")


def main() -> int:
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
    state = source_root / ".gemini-source-state"
    integrity = source_root / ".gemini-source-integrity"
    if not state.is_file() or state.is_symlink():
        raise SystemExit("prepared source state unavailable")
    if not integrity.is_file() or integrity.is_symlink():
        raise SystemExit("prepared source integrity unavailable")

    with tempfile.TemporaryDirectory(prefix="a72-slice4-planner-") as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        run("git", "add", "--", ".", cwd=source)
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
            "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
            "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
            "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
            "GIT_AUTHOR_DATE": "2026-08-29T18:59:00Z",
            "GIT_COMMITTER_DATE": "2026-08-29T18:59:00Z",
        })
        run("git", "commit", "--quiet", "--no-gpg-sign", "-m",
            "A72 slice-4 post-0427 parent", cwd=source, env=env)
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        planner_edits.apply(source)
        validation = run(
            "python3", str(SCRIPT_DIR / "validate_planner_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(source)
        mutation_result = run(
            "python3", str(SCRIPT_DIR / "test_planner_mutations.py"),
            "--source-root", str(source_root), cwd=REPO_ROOT,
        )

        generated_dir = temp / "generated"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        patch = package / PATCH
        shutil.move(generated[0], patch)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", "--ignore", "MISSING_SIGN_OFF,FILE_PATH_CHANGES",
            str(patch), cwd=source_root,
        )

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_planner_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )

        (package / "series").write_text(PATCH + "\n")
        (package / "source-validation.txt").write_text(
            validation + "\n" + mutation_result + "\n" +
            replay_validation + "\n"
        )
        (package / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={state.read_text().strip()}\n"
            f"prepared_source_integrity={integrity.read_text().strip()}\n"
            "canonical_parent_patch=0427-arm64-capture-late-CPU-system-policy-evidence.patch\n"
            "generated_patch_count=1\n"
            "planner_outputs=capabilities-effects-hwcaps-identities\n"
            "identity_encoding=sha256-big-endian-named-fields\n"
            "hwcap_scope=sanitized-system-and-all-targets\n"
            "target_cap_producer=absent\n"
            "architecture_commit=absent\nready_publication=unchanged\n"
            "cpu_request_paths=0\ncpu9_request_paths=0\ncpu_off_paths=0\n"
            "native_vm_build=none\ndevice_action=none\nboot_candidate=false\n"
        )
        checksummed = (
            patch, package / "series", package / "source-validation.txt",
            package / "provenance.txt",
        )
        (package / "SHA256SUMS").write_text("".join(
            f"{sha256(path)}  {path.name}\n" for path in checksummed
        ))
        shutil.copytree(package, output)

    print(f"Generated slice-4 planner patch at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
