#!/usr/bin/env python3
"""Generate exact CPU8 PSCI/generic-hotplug lifecycle bridge patches."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PARENT_HASHES = {
    "include/linux/cpu.h":
        "3fdaade4c37c0a5d401c658803b1d34d3c18083af6454a2fd899477139434034",
    "kernel/cpu.c":
        "e19271407d0aadf6aab38d21fe41b940b08c46b8db5b6bb5bf3f4d1bf56295f9",
    "arch/arm64/include/asm/cpu_ops.h":
        "8ab08fe399dd7385edffd1dc226ce7a242aa3eb39134c0f4d2d08bbb4e23039b",
    "arch/arm64/kernel/smp.c":
        "f9f23ef0702733df793e969f200a4237bd28ebc5e3d5069e413f32e95b5e6599",
    "arch/arm64/kernel/mt6797_psci.c":
        "7e3329797e0f2eebc4372aa47c84c09e3c2ed85e5121f9492898727db5e4f83d",
    "drivers/soc/mediatek/mt6797-a72-transition.c":
        "fdae9e70e2a97b2f6a7ef92abec7597758696a2115696055166581c1480024a2",
    "drivers/soc/mediatek/mt6797-a72-transition-internal.h":
        "a46a55729fdfe3ccf6f10d1e9dacaeb1371e4dd7180b7a8ce234f3bab15705b8",
    "drivers/soc/mediatek/mt6797-a72-transition-test.c":
        "83a73871e4d62c405b8ee15cfb813b811c4b04a0fd06c04af23a4bf62f3bc95d",
}
PATCHES = (
    "0394-arm64-add-CPU-up-lifecycle-completion-bridge.patch",
    "0395-soc-mediatek-test-split-A72-CPU-up-lifecycle.patch",
)
CANONICAL_PATCH_DIR = REPO_ROOT / "patches/v7.1.3"


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


def prepare_parent(source_root: Path, destination: Path) -> None:
    parent_ready = all(
        (source_root / relative).is_file()
        and not (source_root / relative).is_symlink()
        and sha256(source_root / relative) == expected
        for relative, expected in PARENT_HASHES.items()
    )
    for relative in PARENT_HASHES:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"source path is not an exact regular file: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if parent_ready:
        return

    for patch in reversed(PATCHES):
        canonical = CANONICAL_PATCH_DIR / patch
        if not canonical.is_file() or canonical.is_symlink():
            raise SystemExit(f"canonical patch unavailable: {patch}")
        run("git", "apply", "--reverse", "--check", str(canonical),
            cwd=destination)
        run("git", "apply", "--reverse", str(canonical), cwd=destination)
    for relative, expected in PARENT_HASHES.items():
        if sha256(destination / relative) != expected:
            raise SystemExit(f"reconstructed parent changed: {relative}")


def validate_patch_text(path: Path, expected_subject: str) -> None:
    text = path.read_text(encoding="utf-8")
    if f"Subject: {expected_subject}" not in text:
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

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-hotplug-lifecycle-generation-"
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
            source, "MT6797 lifecycle post-0393 parent",
            "Exact relevant source copied from the canonical prepared tree through 0393.",
            "2026-08-27T11:00:00Z",
            check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT)
        production_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "production", cwd=REPO_ROOT,
        )
        commit(
            source, "arm64: add CPU-up lifecycle completion bridge",
            "Add no-op operation hooks at secondary and full CPUHP completion\n"
            "and split the injected MT6797 executor at those boundaries.",
            "2026-08-27T11:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT)
        test_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(source), "--phase", "tests", cwd=REPO_ROOT,
        )
        commit(
            source, "soc: mediatek: test split A72 CPU-up lifecycle",
            "Prove pause, both resumes, generic failures, phase guards,\n"
            "one-shot CPU_ON, and retained no-CPU_OFF behavior in memory.",
            "2026-08-27T11:02:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 2:
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "[PATCH 1/2] arm64: add CPU-up lifecycle completion bridge",
            "[PATCH 2/2] soc: mediatek: test split A72 CPU-up lifecycle",
        )
        for generated_name, final_name, subject in zip(
            generated, PATCHES, subjects
        ):
            target = package / final_name
            shutil.move(generated_name, target)
            validate_patch_text(target, subject)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", "MISSING_SIGN_OFF,FILE_PATH_CHANGES",
                str(target), cwd=source_root,
            )
        (package / "series").write_text(
            "\n".join(PATCHES) + "\n", encoding="utf-8"
        )

        replay = temp / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch in PATCHES:
            run("git", "apply", "--check", str(package / patch), cwd=replay)
            run("git", "apply", str(package / patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root",
            str(replay), "--phase", "tests", cwd=REPO_ROOT,
        )
        (package / "source-validation.txt").write_text(
            production_validation + "\n" + test_validation + "\n" +
            replay_validation + "\n", encoding="utf-8"
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={(source_root / '.gemini-source-state').read_text(encoding='utf-8').strip()}\n"
            f"parent_kernel_cpu_sha256={PARENT_HASHES['kernel/cpu.c']}\n"
            f"parent_arm64_smp_sha256={PARENT_HASHES['arch/arm64/kernel/smp.c']}\n"
            f"parent_executor_sha256={PARENT_HASHES['drivers/soc/mediatek/mt6797-a72-transition.c']}\n"
            "generated_patch_count=2\n"
            "secondary_hook=after-successful-__cpu_up\n"
            "full_hook=after-successful-cpuhp-up-callbacks\n"
            "generic_secondary_timeout_ms=5000\n"
            "focused_kunit_cases=10\n"
            "cpu_on_maximum=1\n"
            "cpu_off_maximum=0\n"
            "retry_maximum=0\n"
            "mt6797_production_lifecycle_callbacks=0\n"
            "production_callers=0\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "device_action=none\n"
            "boot_candidate=false\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("secondary_hook=after-successful-__cpu_up")
    print("full_hook=after-successful-cpuhp-up-callbacks")
    print("focused_kunit_cases=10")
    print("cpu_on_maximum=1")
    print("cpu_off_maximum=0")
    print("retry_maximum=0")
    print("mt6797_production_lifecycle_callbacks=0")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
