#!/usr/bin/env python3
"""Generate and replay the READY-candidate repair series."""

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
PATCHES = (
    "0435-arm64-keep-late-CPU-preflight-build-safe-when-disabled.patch",
    "0436-arm64-bind-Gemini-CPU8-admission-configuration.patch",
)
SUBJECTS = (
    "arm64: keep late CPU preflight build-safe when disabled",
    "arm64: bind Gemini CPU8 admission configuration",
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
            f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in source_edits.PARENT_HASHES.items():
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
        "GIT_AUTHOR_DATE": f"2026-08-30T03:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-30T03:{minute:02d}:00Z",
    })
    return env


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=deterministic_env(minute),
    )


def added_text(path: Path) -> str:
    return "\n".join(
        line[1:] for line in path.read_text().splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate_patch(path: Path, index: int) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECTS[index] not in str(message["Subject"] or ""):
        raise SystemExit(f"generated patch subject changed: {path.name}")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit(f"generated patch From changed: {path.name}")
    added = added_text(path)
    for forbidden in (
        "Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
        "cpu_off(", "psci_cpu_on", "psci_cpu_off", "boot2",
        "CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=",
    ):
        if forbidden in added:
            raise SystemExit(f"forbidden generated token: {forbidden}")
    required = (
        (
            "int arm64_late_cpu_validate_boot_caps(void);",
            "arm64_validate_late_cpu_preflight(unsigned int cpu)",
            "return 0;",
        ),
        (
            "0x5968c24f1904c055",
            "0x9dea25480c41fbc7",
            "0xdb49e822dc3600d1",
            "0xbdd7632330853f40",
        ),
    )
    for token in required[index]:
        if token not in added:
            raise SystemExit(f"required generated token absent: {token}")


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

    with tempfile.TemporaryDirectory(prefix="a72-ready-admission-") as name:
        temp = Path(name)
        source = temp / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(source, "A72 READY admission post-0434 parent",
               "Synthetic generation parent only.", 0)
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        source_edits.apply_config_off(source)
        config_off_validation = "\n".join(
            __import__("validate_source").validate_config_off(source)
        )
        commit(
            source, SUBJECTS[0],
            "Keep the always-built boot-capability preflight prototype visible\n"
            "when the optional late-CPU profile is disabled. Provide the same\n"
            "zero-effect pass-through used by the other disabled-profile hooks.\n\n"
            "This repairs generic arm64 builds without activating a profile or\n"
            "adding any CPU request path.", 1,
        )

        source_edits.apply_identity(source)
        validation = run(
            sys.executable, str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source, SUBJECTS[1],
            "Bind the production MT6797 late-CPU profile to the exact\n"
            "configuration inputs of the serviceability-first CPU8 live-trigger\n"
            "candidate. Preserve the separate historical fixture identity.\n\n"
            "The change opens no gate by itself and adds no CPU9, retry, or\n"
            "CPU_OFF path.", 2,
        )
        mutation_result = run(
            sys.executable, str(SCRIPT_DIR / "test_mutations.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
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
        checkpatch_work = temp / "checkpatch"
        checkpatch_work.mkdir()
        for index, (generated_path, patch_name) in enumerate(
                zip(generated, PATCHES, strict=True)):
            patch = package / patch_name
            shutil.move(generated_path, patch)
            validate_patch(patch, index)
            fix_patch_style(patch, source_root, checkpatch_work)
            validate_patch(patch, index)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", f"--root={source_root}", "--ignore",
                "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE", str(patch),
                cwd=checkpatch_work,
            )

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch_name in PATCHES:
            patch = package / patch_name
            run("git", "apply", "--check", str(patch), cwd=replay)
            run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            sys.executable, str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        if replay_validation != validation:
            raise SystemExit("replay validation changed")

        output.mkdir(parents=True)
        for patch_name in PATCHES:
            shutil.copyfile(package / patch_name, output / patch_name)
        (output / "series").write_text(
            "".join(f"v7.1.3/{patch_name}\n" for patch_name in PATCHES)
        )
        (output / "source-validation.txt").write_text(
            config_off_validation + "\n" + validation + "\n" +
            mutation_result + "\n"
        )
        provenance = [
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={source_state}",
            f"prepared_source_integrity={source_integrity}",
        ]
        for relative, expected in source_edits.PARENT_HASHES.items():
            key = relative.replace("/", "_").replace(".", "_")
            provenance.append(f"parent_{key}_sha256={expected}")
            provenance.append(f"final_{key}_sha256={sha256(replay / relative)}")
        for patch_name in PATCHES:
            provenance.append(
                f"patch_{patch_name}_sha256={sha256(output / patch_name)}"
            )
        provenance.extend((
            "generated_patch_count=2",
            validation,
            mutation_result,
            "profile_fragments_changed=0",
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
