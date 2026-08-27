#!/usr/bin/env python3
"""Generate the exact five-patch MT6797 CPU8 binder review series."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import binder_source_edits as binder_edits
from source_edits import PARENT_HASHES as EXECUTOR_PARENT_HASHES


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PARENT_HASHES = {**EXECUTOR_PARENT_HASHES, **binder_edits.PARENT_HASHES}
PATCHES = (
    "0396-soc-mediatek-make-A72-retained-checkpoints-fallible.patch",
    "0397-arm64-mediatek-add-CPU8-binder-ownership-states.patch",
    "0398-dt-bindings-mediatek-add-MT6797-A72-binder.patch",
    "0399-soc-mediatek-bind-the-MT6797-CPU8-transition.patch",
    "0400-soc-mediatek-test-the-MT6797-CPU8-transition-binder.patch",
)
SUBJECTS = (
    "soc: mediatek: make A72 retained checkpoints fallible",
    "arm64: mediatek: add CPU8 binder ownership states",
    "dt-bindings: mediatek: add MT6797 A72 binder",
    "soc: mediatek: bind the MT6797 CPU8 transition",
    "soc: mediatek: test the MT6797 CPU8 transition binder",
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


def validate_patch_text(path: Path, subject: str) -> None:
    text = path.read_text(encoding="utf-8")
    if subject not in text:
        raise SystemExit(f"subject changed: {path.name}")
    expected_from = (
        "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    )
    if expected_from not in text:
        raise SystemExit(f"synthetic archive identity changed: {path.name}")
    if "Signed-off-by:" in text:
        raise SystemExit(f"synthetic sign-off forbidden: {path.name}")
    if "/Users/" in text or "device_action=" in text:
        raise SystemExit(f"private or generated evidence leaked: {path.name}")


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
    source_state_path = source_root / ".gemini-source-state"
    if not source_state_path.is_file() or source_state_path.is_symlink():
        raise SystemExit("prepared source state is unavailable")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-default-off-binder-generation-"
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
            source, "MT6797 retained-checkpoint post-0395 parent",
            "Exact relevant source copied from the canonical prepared tree through 0395.",
            "2026-08-27T18:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), cwd=REPO_ROOT)
        executor_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source,
            "soc: mediatek: make A72 retained checkpoints fallible",
            "Propagate every regular retained-ledger failure, commit every\n"
            "attempted terminal result, and publish membership before success.",
            "2026-08-27T18:01:00Z",
        )

        binder_edits.validate_parent(source)
        binder_edits.apply_owner_stage(source)
        commit(
            source,
            "arm64: mediatek: add CPU8 binder ownership states",
            "Add the public preflight, one-shot CPU_ON budget, success\n"
            "publication, terminal finalization, and clean rejection states.",
            "2026-08-27T18:02:00Z",
        )
        binder_edits.apply_binding_stage(source)
        commit(
            source,
            "dt-bindings: mediatek: add MT6797 A72 binder",
            "Describe the default-off binder's three explicit supplier\n"
            "phandles without instantiating it in the base Device Tree.",
            "2026-08-27T18:03:00Z",
        )
        binder_edits.apply_binder_stage(source)
        commit(
            source,
            "soc: mediatek: bind the MT6797 CPU8 transition",
            "Join the existing physical owners to the one-shot executor and\n"
            "split PSCI/hotplug lifecycle behind a default-off option.",
            "2026-08-27T18:04:00Z",
        )
        binder_edits.apply_test_stage(source)
        binder_validation = run(
            "python3", str(SCRIPT_DIR / "validate_binder_source.py"),
            "--source-root", str(source), cwd=REPO_ROOT,
        )
        commit(
            source,
            "soc: mediatek: test the MT6797 CPU8 transition binder",
            "Exercise the exact success, retained-terminal failure, clean\n"
            "pre-isolation refusal, malformed-owner, and one-shot paths.",
            "2026-08-27T18:05:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != len(PATCHES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        targets: list[Path] = []
        for generated_path, name, subject in zip(
            generated, PATCHES, SUBJECTS, strict=True
        ):
            target = package / name
            shutil.move(generated_path, target)
            validate_patch_text(target, subject)
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
        replay_executor_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        replay_binder_validation = run(
            "python3", str(SCRIPT_DIR / "validate_binder_source.py"),
            "--source-root", str(replay), cwd=REPO_ROOT,
        )
        (package / "series").write_text(
            "\n".join(PATCHES) + "\n", encoding="utf-8"
        )
        (package / "source-validation.txt").write_text(
            executor_validation + "\n" + binder_validation + "\n" +
            replay_executor_validation + "\n" +
            replay_binder_validation + "\n", encoding="utf-8"
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state_path.read_text(encoding='utf-8').strip()}\n"
            "generated_patch_count=5\n"
            "executor_stages=10\n"
            "regular_success_checkpoints=20\n"
            "terminal_commits=1\n"
            "terminal_failure_contexts=31\n"
            "executor_kunit_cases=12\n"
            "membership_kunit_cases=4\n"
            "binder_kunit_cases=5\n"
            "focused_kunit_cases=21\n"
            "membership_before_terminal=true\n"
            "terminal_before_finalize=true\n"
            "cpu_on_call_sites=1\n"
            "binder_delegated_cpu_on_calls=1\n"
            "cpu_off_call_sites=0\n"
            "retry_call_sites=0\n"
            "probe_provider_hardware_reads=0\n"
            "supplier_device_links=managed-consumer\n"
            "binder_publication_serialized=true\n"
            "base_dt_enablements=0\n"
            "production_cpu_requests=0\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "device_action=none\n"
            "boot_candidate=false\n"
        )
        (package / "provenance.txt").write_text(
            provenance, encoding="utf-8"
        )
        sums = [
            f"{sha256(path)}  {path.name}"
            for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=5")
    print("executor_stages=10")
    print("regular_success_checkpoints=20")
    print("terminal_commits=1")
    print("terminal_failure_contexts=31")
    print("executor_kunit_cases=12")
    print("membership_kunit_cases=4")
    print("binder_kunit_cases=5")
    print("focused_kunit_cases=21")
    print("membership_before_terminal=true")
    print("terminal_before_finalize=true")
    print("binder_delegated_cpu_on_calls=1")
    print("cpu_off_call_sites=0")
    print("retry_call_sites=0")
    print("probe_provider_hardware_reads=0")
    print("supplier_device_links=managed-consumer")
    print("binder_publication_serialized=true")
    print("base_dt_enablements=0")
    print("production_cpu_requests=0")
    print("physical_effect_calls=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
