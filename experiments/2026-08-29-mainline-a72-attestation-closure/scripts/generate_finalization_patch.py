#!/usr/bin/env python3
"""Generate and replay the architecture-owned late-CPU finalization patch."""

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

import finalization_edits


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH = "0434-arm64-finalize-Gemini-late-CPU-profile.patch"
SUBJECT = "arm64: finalize Gemini late CPU profile"


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
    for relative, expected in finalization_edits.PARENT_HASHES.items():
        source = source_root / relative
        if (not source.is_file() or source.is_symlink() or
                sha256(source) != expected):
            raise SystemExit(f"prepared source changed: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def deterministic_env(minute: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-08-30T02:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-30T02:{minute:02d}:00Z",
    })
    return env


def commit(root: Path) -> str:
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", SUBJECT,
        "-m", "Verify the frozen late-CPU local-capability set and the exact\n"
        "applied-alternatives and mitigation state after architecture\n"
        "finalization. Reduce native and compat userspace HWCAPs one way to\n"
        "the frozen common plan before READY publication.\n\n"
        "Wire the named MT6797 profile to those architecture-owned callbacks\n"
        "and clear its final production attestation blocker. Keep the fixture\n"
        "blocked and add no CPU request, retry, or CPU_OFF path.",
        cwd=root, env=deterministic_env(1),
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
        "Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_off", "psci_cpu_on", "boot2",
        "arm64_get_late_cpu_ready_token",
        "receipt->user_hwcaps_finalized =",
    ):
        if forbidden in added:
            raise SystemExit(f"forbidden generated patch token: {forbidden}")
    for required in (
        "arm64_verify_late_cpu_system",
        "arm64_verify_late_cpu_mitigations",
        "arm64_finalize_late_cpu_hwcaps",
        "alternative_is_applied(cap)",
        "bitmap_subset(expected, elf_hwcap, MAX_CPU_FEATURES)",
        "bitmap_copy(elf_hwcap, expected, MAX_CPU_FEATURES)",
        ".verify_system = mt6797_a72_verify_system",
        ".finalize_user = mt6797_a72_finalize_user",
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

    with tempfile.TemporaryDirectory(prefix="a72-finalization-") as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        run("git", "add", "--", ".", cwd=source)
        run("git", "commit", "--quiet", "--no-gpg-sign", "-m",
            "A72 finalization post-0433 parent", cwd=source,
            env=deterministic_env(0))
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        finalization_edits.apply(source)
        validation = run(
            "python3", str(SCRIPT_DIR / "validate_finalization_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(source)
        mutation_result = run(
            "python3", str(SCRIPT_DIR / "test_finalization_mutations.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
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
            "python3", str(SCRIPT_DIR / "validate_finalization_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        if replay_validation != validation:
            raise SystemExit("replay validation changed")

        output.mkdir(parents=True)
        shutil.copyfile(patch, output / PATCH)
        (output / "series").write_text(f"v7.1.3/{PATCH}\n")
        (output / "source-validation.txt").write_text(
            validation + "\n" + mutation_result + "\n")
        provenance = [
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={source_state}",
            f"prepared_source_integrity={source_integrity}",
        ]
        for relative, expected in finalization_edits.PARENT_HASHES.items():
            key = relative.replace("/", "_").replace(".", "_")
            provenance.append(f"parent_{key}_sha256={expected}")
            provenance.append(f"final_{key}_sha256={sha256(replay / relative)}")
        provenance.extend((
            f"patch_sha256={sha256(output / PATCH)}",
            "generated_patch_count=1",
            validation,
            mutation_result,
            "native_vm_build=none",
            "device_action=none",
            "boot_candidate=false",
        ))
        (output / "provenance.txt").write_text("\n".join(provenance) + "\n")
        checksums = []
        for item in sorted(output.iterdir()):
            if item.name != "SHA256SUMS":
                checksums.append(f"{sha256(item)}  {item.name}")
        (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
