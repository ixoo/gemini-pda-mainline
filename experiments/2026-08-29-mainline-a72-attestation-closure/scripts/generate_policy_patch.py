#!/usr/bin/env python3
"""Generate and replay the conservative-policy patch."""

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

import policy_edits


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH = "0432-arm64-plan-late-CPU-conservative-system-policy.patch"
SUBJECT = "arm64: plan conservative late CPU system policy"
SUPPORT_HASHES = {
    "arch/arm64/kernel/head.S":
        "17dac1b2a499bb21f8a0e160aff9fd9fd24343c0f6d0dc12a4f4cbafb99d0749",
    "arch/arm64/kernel/smp.c":
        "b8d0f94cb2c2c90b3fe5af178ae7c0a068720ba1e574495eeee8be4297c94f7c",
}


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
    hashes = policy_edits.PARENT_HASHES | SUPPORT_HASHES
    for relative, expected in hashes.items():
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
        "GIT_AUTHOR_DATE": "2026-08-30T00:31:00Z",
        "GIT_COMMITTER_DATE": "2026-08-30T00:31:00Z",
    })
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", SUBJECT,
        "-m", "Record the two unused early GIC capabilities from the current\n"
        "system and keep a present state unresolved without target controller\n"
        "evidence. Derive the recovered Cortex-A72 Spectre state only from the\n"
        "field-valid expected MIDR/PFR pair, choosing vulnerable no-callback\n"
        "effects when firmware workaround results remain unknown.\n\n"
        "Activate no expected pair, publish no READY token, and request no CPU.",
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
        "Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_off", "psci_cpu_on", "boot2",
        "expected_pair.abi =", "observed_target_", "smccc_wa1",
        "smccc_wa2", "smccc_wa3", "ARM64_LATE_CPU_V2_CALLBACK_SMC",
        "ARM64_LATE_CPU_V2_CALLBACK_HVC",
    ):
        if forbidden in added:
            raise SystemExit(f"forbidden generated patch token: {forbidden}")
    for required in (
        "ARM64_LATE_CPU_SYSTEM_CAP_EARLY_LOCAL_VALID",
        "arm64_late_cpu_early_system_cap_state",
        "arm64_late_cpu_expected_effects",
        "ARM64_LATE_CPU_MITIGATION_VULNERABLE",
        "ARM64_LATE_CPU_BHB_STATE_VULNERABLE",
        "ARM64_LATE_CPU_V2_CALLBACK_NONE",
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
    state = source_root / ".gemini-source-state"
    integrity = source_root / ".gemini-source-integrity"
    if not state.is_file() or state.is_symlink():
        raise SystemExit("prepared source state unavailable")
    if not integrity.is_file() or integrity.is_symlink():
        raise SystemExit("prepared source integrity unavailable")

    with tempfile.TemporaryDirectory(prefix="a72-conservative-policy-") as name:
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
            "GIT_AUTHOR_DATE": "2026-08-30T00:30:00Z",
            "GIT_COMMITTER_DATE": "2026-08-30T00:30:00Z",
        })
        run("git", "commit", "--quiet", "--no-gpg-sign", "-m",
            "A72 conservative-policy post-0431 parent", cwd=source, env=env)
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        policy_edits.apply(source)
        validation = run(
            "python3", str(SCRIPT_DIR / "validate_policy_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(source)
        mutation_result = run(
            "python3", str(SCRIPT_DIR / "test_policy_mutations.py"),
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
            "python3", str(SCRIPT_DIR / "validate_policy_source.py"),
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
            "canonical_parent_patch=0431-arm64-preflight-late-CPU-strict-verification.patch\n"
            "generated_patch_count=1\n"
            "early_gic_owner=finalized-system-capability-bitmap\n"
            "early_gic_absent=planned-absent\n"
            "early_gic_present=unresolved\n"
            "expected_spectre_fields=midr,pfr0,pfr1\n"
            "unknown_wa1=vulnerable-no-callback\n"
            "unknown_wa2=vulnerable-no-callback\n"
            "vulnerable_v2_bhb=vulnerable-no-method\n"
            "missing_modern_ids=not-consumed\n"
            "expected_pair_activation=absent\n"
            "ready_publication=unchanged\n"
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
        expected_files = {
            PATCH, "series", "source-validation.txt", "provenance.txt",
            "SHA256SUMS",
        }
        actual_files = {path.name for path in package.iterdir() if path.is_file()}
        if actual_files != expected_files:
            raise SystemExit("generated package file set changed")
        shutil.copytree(package, output)

    print(f"Generated conservative policy at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
