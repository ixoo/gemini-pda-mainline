#!/usr/bin/env python3
"""Generate and replay the named-device expected-pair activation patch."""

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

import activation_edits


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH = "0433-arm64-bind-Gemini-late-CPU-expected-pair.patch"
SUBJECT = "arm64: bind Gemini late CPU expected pair"


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
    for relative, expected in activation_edits.PARENT_HASHES.items():
        source = source_root / relative
        if (not source.is_file() or source.is_symlink() or
                sha256(source) != expected):
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
        "GIT_AUTHOR_DATE": "2026-08-30T01:01:00Z",
        "GIT_COMMITTER_DATE": "2026-08-30T01:01:00Z",
    })
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", SUBJECT,
        "-m", "Freeze the exact named-device prior-cycle capsule stream as a\n"
        "field-valid CPU8/CPU9 expectation before pure planning. Keep all\n"
        "current target observations empty and require the core-sealed current\n"
        "image, system, and policy inputs.\n\n"
        "Exercise the admitted planners while retaining ATTESTATION_USERS as\n"
        "the sole clean-path blocker. Publish no READY token and request no CPU.",
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
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in (
        "Signed-off-by:", "/Users/", "ARM64_LATE_CPU_PROFILE_READY",
        "arm64_get_late_cpu_ready_token", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_off", "psci_cpu_on", "boot2",
        "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID",
        "evidence->observed_target_mpidr[target] =",
        "evidence->observed_target_midr[target] =",
        "evidence->observed_target_revidr[target] =",
        "evidence->target_cap[target].valid =",
    ):
        if forbidden in added:
            raise SystemExit(f"forbidden generated patch token: {forbidden}")
    for required in (
        "mt6797_a72_expected_pair __initconst",
        "ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "0xe35596c52bc8b40b", "0x600c5e2d6733661d",
        "evidence->expected_pair = mt6797_a72_expected_pair",
        "mt6797_a72_evidence_is_bound_expectation",
        "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS",
        "mt6797_a72_effects_empty",
    ):
        if required not in added:
            raise SystemExit(f"required generated patch token absent: {required}")


def fix_patch_style(path: Path, source_root: Path, cwd: Path) -> None:
    result = subprocess.run(
        (
            "perl", str(source_root / "scripts/checkpatch.pl"),
            "--fix-inplace", "--strict", "--no-tree",
            f"--root={source_root}", "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE", str(path),
        ),
        cwd=cwd, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit("checkpatch style fix did not preserve the patch")


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

    state_path = source_root / ".gemini-source-state"
    integrity_path = source_root / ".gemini-source-integrity"
    if (not state_path.is_file() or state_path.is_symlink() or
            not integrity_path.is_file() or integrity_path.is_symlink()):
        raise SystemExit("prepared source identity unavailable")
    source_state = state_path.read_text().strip()
    source_integrity = integrity_path.read_text().strip()

    with tempfile.TemporaryDirectory(prefix="a72-expectation-activation-") as name:
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
            "GIT_AUTHOR_DATE": "2026-08-30T01:00:00Z",
            "GIT_COMMITTER_DATE": "2026-08-30T01:00:00Z",
        })
        run("git", "commit", "--quiet", "--no-gpg-sign", "-m",
            "A72 activation post-0432 parent", cwd=source, env=env)
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        activation_edits.apply(source)
        validation = run(
            "python3", str(SCRIPT_DIR / "validate_activation_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(source)
        mutation_result = run(
            "python3", str(SCRIPT_DIR / "test_activation_mutations.py"),
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
        checkpatch_work = temp / "checkpatch"
        checkpatch_work.mkdir()
        fix_patch_style(patch, source_root, checkpatch_work)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE",
            str(patch), cwd=checkpatch_work,
        )

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_activation_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        if replay_validation != validation:
            raise SystemExit("replay validation changed")

        output.mkdir(parents=True)
        shutil.copyfile(patch, output / PATCH)
        (output / "series").write_text(f"v7.1.3/{PATCH}\n")
        (output / "source-validation.txt").write_text(
            validation + "\n" + mutation_result + "\n")
        final_hash = sha256(replay / activation_edits.PROFILE)
        (output / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"prepared_source_integrity={source_integrity}\n"
            f"parent_profile_sha256="
            f"{activation_edits.PARENT_HASHES[activation_edits.PROFILE]}\n"
            f"activated_profile_sha256={final_hash}\n"
            f"patch_sha256={sha256(output / PATCH)}\n"
            "generated_patch_count=1\n" + validation + "\n" +
            mutation_result + "\n"
            "native_vm_build=none\n"
            "device_action=none\n"
            "boot_candidate=false\n"
        )
        checksums = []
        for item in sorted(output.iterdir()):
            if item.name != "SHA256SUMS":
                checksums.append(f"{sha256(item)}  {item.name}")
        (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
