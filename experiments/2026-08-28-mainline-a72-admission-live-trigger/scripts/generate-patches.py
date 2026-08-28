#!/usr/bin/env python3
"""Generate and replay the two admission live-trigger patches."""

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

from source_edits import PARENT_HASHES


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCHES = (
    "0419-soc-mediatek-arm-CPU8-admission-after-live-service.patch",
    "0420-soc-mediatek-test-live-CPU8-admission-trigger.patch",
)
SUBJECTS = (
    "soc: mediatek: arm CPU8 admission after live service",
    "soc: mediatek: test live CPU8 admission trigger",
)


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
            f"command failed ({result.returncode}): {' '.join(args)}"
        )
    return result.stdout.strip()


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"source path is not exact: {relative}")
        if sha256(source) != expected:
            raise SystemExit(f"source hash changed: {relative}")
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
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=env,
    )


def validate_patch(path: Path, subject: str) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if subject not in str(message["Subject"] or ""):
        raise SystemExit(f"patch subject changed: {path.name}")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit(f"patch From changed: {path.name}")
    text = path.read_text(encoding="utf-8")
    for forbidden in ("Signed-off-by:", "/Users/", "device_action="):
        if forbidden in text:
            raise SystemExit(f"forbidden patch token {forbidden}: {path.name}")


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
    state = source_root / ".gemini-source-state"
    integrity = source_root / ".gemini-source-integrity"
    if not state.is_file() or state.is_symlink():
        raise SystemExit("prepared source state unavailable")
    if not integrity.is_file() or integrity.is_symlink():
        raise SystemExit("prepared source integrity unavailable")

    with tempfile.TemporaryDirectory(prefix="mt6797-admission-live-") as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 admission live-trigger post-0418 parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0418.",
            "2026-08-28T23:40:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        validations: list[str] = []
        stages = (
            (
                "production", SUBJECTS[0],
                "Keep probe inert, consume one exact root-only token before "
                "supplier resolution, and expose bounded status.",
                "2026-08-28T23:41:00Z",
            ),
            (
                "tests", SUBJECTS[1],
                "Prove invalid-token refusal, terminal result capture, and "
                "repeat closure with injected operations.",
                "2026-08-28T23:42:00Z",
            ),
        )
        for stage, subject, body, timestamp in stages:
            run(
                "python3", str(SCRIPT_DIR / "source_edits.py"),
                "--source-root", str(source), "--stage", stage,
                cwd=REPO_ROOT,
            )
            validations.append(run(
                "python3", str(SCRIPT_DIR / "validate_source.py"),
                "--source-root", str(source), "--stage", stage,
                cwd=REPO_ROOT,
            ))
            commit(source, subject, body, timestamp)

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
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore",
                "MISSING_SIGN_OFF,FILE_PATH_CHANGES,SPLIT_STRING",
                str(target), cwd=source_root,
            )
            targets.append(target)

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for target in targets:
            run("git", "apply", "--check", str(target), cwd=replay)
            run("git", "apply", str(target), cwd=replay)
        validations.append(run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), "--stage", "tests",
            cwd=REPO_ROOT,
        ))

        (package / "series").write_text(
            "\n".join(PATCHES) + "\n", encoding="utf-8"
        )
        (package / "source-validation.txt").write_text(
            "\n".join(validations) + "\n", encoding="utf-8"
        )
        (package / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={state.read_text(encoding='utf-8').strip()}\n"
            f"prepared_source_integrity="
            f"{integrity.read_text(encoding='utf-8').strip()}\n"
            "generated_patch_count=2\nautomatic_probe_action=0\n"
            "trigger_execution_maximum=1\nadmission_core_maximum=1\n"
            "cpu8_request_maximum=1\ncpu9_request_paths=0\n"
            "cpu_off_paths=0\nretry_paths=0\nfocused_kunit_cases=9\n"
            "native_vm_build=none\ndevice_action=none\n"
            "boot_candidate=false\n",
            encoding="utf-8",
        )
        checksummed = [
            *targets, package / "series", package / "source-validation.txt",
            package / "provenance.txt",
        ]
        (package / "SHA256SUMS").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
            encoding="utf-8",
        )
        shutil.copytree(package, output)


if __name__ == "__main__":
    main()
