#!/usr/bin/env python3
"""Generate and replay the one-entry classified-universe closure."""

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

import source_edits


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH = "0441-arm64-complete-Gemini-late-CPU-classified-universe.patch"
SUBJECT = "arm64: complete Gemini late CPU classified universe"
PATCH_0440_SHA256 = "b629ff9589748131a72928942c23f25765054cea4be977c2623956b6d84726cc"


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
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def prepare_parent(source_root: Path, destination: Path) -> None:
    source = source_root / source_edits.TARGET
    if (not source.is_file() or source.is_symlink() or
            sha256(source) != source_edits.PARENT_SHA256):
        raise SystemExit("prepared post-0440 source changed")
    target = destination / source_edits.TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    patch = REPO_ROOT / "patches/v7.1.3/0440-arm64-repair-Gemini-late-CPU-plan-expectations.patch"
    if sha256(patch) != PATCH_0440_SHA256:
        raise SystemExit("canonical patch 0440 changed")


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-08-30T23:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-30T23:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run("git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment)


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
            "Gemini Mainline Experiment <gemini-mainline@example.invalid>"):
        raise SystemExit("generated patch author changed")
    text = path.read_text(encoding="utf-8")
    target = source_edits.TARGET.as_posix()
    if text.count("\ndiff --git ") != 1:
        raise SystemExit("generated patch file count changed")
    if text.count(f"diff --git a/{target} b/{target}") != 1:
        raise SystemExit("generated patch path changed")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    deleted = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    if added.count("ARM64_MISMATCHED_CACHE_TYPE,") != 1 or deleted:
        raise SystemExit("classified-universe delta changed")
    for token in (
        "Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
        "add_cpu(", "remove_cpu(", "psci_cpu_on", "psci_cpu_off",
        "cpu_off(", "reboot", "retry", "writel(", "writeq(",
        "write_sysreg(", "regmap_write(", "memcpy_toio(",
    ):
        if token.lower() in added.lower():
            raise SystemExit(f"forbidden generated token: {token}")


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
            char not in "0123456789abcdef" for char in args.repository_commit):
        raise SystemExit("invalid repository commit")
    state = (source_root / ".gemini-source-state").read_text().strip()
    integrity = (source_root / ".gemini-source-integrity").read_text().strip()
    with tempfile.TemporaryDirectory(prefix="a72-classified-closure-") as name:
        temporary = Path(name)
        source = temporary / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(source, "Gemini classified universe post-0440 parent",
               "Synthetic generation parent only.", 0)
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        source_edits.apply(source)
        validation = run(sys.executable, str(SCRIPT_DIR / "validate_source.py"),
                         "--source-root", str(source), cwd=REPO_ROOT)
        mutation = run(sys.executable, str(SCRIPT_DIR / "test_mutations.py"),
                       "--source-root", str(source), cwd=REPO_ROOT)
        commit(
            source, SUBJECT,
            "The exact post-0440 live plan fails only the global and per-target\n"
            "classified-capability weight checks. MISMATCHED_CACHE_TYPE is\n"
            "classified by the producer but absent from each target bitmap.\n\n"
            "List it in the expected-absent universe. Preserve producers,\n"
            "effects, policy, validator return, and all CPU-action behavior.", 1,
        )
        generated_dir = temporary / "generated"
        generated = run("git", "format-patch", "--no-signature",
                        "--output-directory", str(generated_dir),
                        f"{parent}..HEAD", cwd=source).splitlines()
        if len(generated) != 1:
            raise SystemExit("generated patch count changed")
        package = temporary / "package"
        package.mkdir()
        patch = package / PATCH
        shutil.move(generated[0], patch)
        validate_patch(patch)
        run("perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE", str(patch),
            cwd=temporary)
        replay = temporary / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            sys.executable, str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT)
        if replay_validation != validation:
            raise SystemExit("replay validation changed")
        output.mkdir(parents=True)
        shutil.copyfile(patch, output / PATCH)
        (output / "series").write_text(f"v7.1.3/{PATCH}\n")
        (output / "source-validation.txt").write_text(
            validation + "\n" + mutation + "\n")
        (output / "provenance.txt").write_text("\n".join((
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            f"parent_mt6797_psci_sha256={source_edits.PARENT_SHA256}",
            f"final_mt6797_psci_sha256={sha256(replay / source_edits.TARGET)}",
            f"patch_sha256={sha256(output / PATCH)}",
            "generated_patch_count=1", validation, mutation,
            "profile_fragments_changed=0", "native_vm_build=none",
            "device_action=none", "boot_candidate=false",
        )) + "\n")
        checksums = [
            f"{sha256(item)}  {item.name}" for item in sorted(output.iterdir())
            if item.name != "SHA256SUMS"
        ]
        (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
