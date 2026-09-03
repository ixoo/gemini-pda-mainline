#!/usr/bin/env python3
"""Generate the exact CPU9 P30E rearm and restore-integration patches."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_p30e_rearm_source import FINAL_MUTATIONS, PRIMITIVE_MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAMES = (
    "0507-arm64-mediatek-add-exact-CPU9-P30E-rearm.patch",
    "0508-soc-mediatek-rearm-P30E-before-CPU9-restore.patch",
)
EXPECTED_SOURCE_STATE = (
    "abcf68148338da888a861232052528a3881ce33fea4fc257289981b0bebe3450"
)
PARENT_HASHES = {
    "arch/arm64/Kconfig":
        "9cc3dec4c17431a707b7bd561d94e9716a0119602538ca41ec7a2e5861695224",
    "arch/arm64/include/asm/mt6797_a72_p30e.h":
        "5769b8cf17a703b733039633b4b3c719bff9516da629e427bb365b360abba6bb",
    "arch/arm64/kernel/Makefile":
        "2b04a7f2266f3984617a07f42c0e42982693451c284ef99f3445eabba732ce5e",
    "arch/arm64/kernel/head.S":
        "d233bacbac922938ef816420ae32b9506b36c3b63e2462572ecc51929988490e",
    "arch/arm64/kernel/mt6797_a72_p30e.c":
        "556d622075d63dc03e9f3e31afb0cb3642b4b673621300b4fe49ed031d30fda3",
    "arch/arm64/kernel/mt6797_a72_p30e_asm.S":
        "db60d9bf6b7557b0c6dfbb4ebd57c7e6397a9960a0ca35946316d7ae090cb5dd",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h":
        "6e2cd6d2f02f283f0b59c2a81819859fc54806dd864c71bdf781becd68949109",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c":
        "1b98bf02189746bf1e31511fb88cf4d91db623bce73e1da3b8d8074d365253b4",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c":
        "522a6eb12feea37a93ccf51ce4afa29f1637f751fd659b307bb3171206466a89",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h":
        "9b13ef4b20f85cfb638d2e47b01cb4f767b6c34d39d5006de10f11df6258c79b",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c":
        "d8d50b4fb70ba552a8fea42b6c0f6b8873bd2bc56e7f644c0768171fcfb15d82",
    "drivers/soc/mediatek/mt6797-a72-restore-executor.c":
        "7f7eb389e206dbb9913d2d70be1c8cf99e4560dcfe04a329c9ab57dd9250780c",
    "fs/pstore/gemini_a72_hotplug_ledger.c":
        "c45e5c50c9f183d8b3e05216b4a3d18e2febc399164029a4d968a384162149ae",
    "fs/pstore/gemini_a72_hotplug_ledger_internal.h":
        "3220a1a3f2889d6403eaf375de8dc26015a102c7c154785529217d1142bacabc",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c":
        "3ce8d3a0eae2952f589671ce24f1c8a326465e6cce17dc3ce11035df6d40189a",
    "include/linux/gemini_a72_hotplug_ledger.h":
        "b1f160569bd1ec7d8b57ae8374b5cd7d05be5c2d411d743d6b6a53aba4fa817c",
}
PATCH_PATHS = (
    tuple(sorted((
        "arch/arm64/Kconfig",
        "arch/arm64/include/asm/mt6797_a72_p30e.h",
        "arch/arm64/kernel/Makefile",
        "arch/arm64/kernel/mt6797_a72_p30e.c",
        "arch/arm64/kernel/mt6797_a72_p30e_test.c",
    ))),
    tuple(sorted((
        "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h",
        "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c",
        "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c",
        "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h",
        "drivers/soc/mediatek/mt6797-a72-restore-executor-test.c",
        "drivers/soc/mediatek/mt6797-a72-restore-executor.c",
        "fs/pstore/gemini_a72_hotplug_ledger_internal.h",
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "include/linux/gemini_a72_hotplug_ledger.h",
    ))),
)
SUBJECTS = (
    "arm64: mediatek: add exact CPU9 P30E rearm",
    "soc: mediatek: rearm P30E before CPU9 restore",
)
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"


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


def copy_parent(source_root: Path, destination: Path) -> None:
    for relative in PARENT_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)


def validate_parent(source_root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")
    new_test = source_root / "arch/arm64/kernel/mt6797_a72_p30e_test.c"
    if new_test.exists():
        raise SystemExit("prepared source unexpectedly has P30E rearm test")


def changed_paths(text: str) -> tuple[str, ...]:
    return tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))


def validate_patch(path: Path, index: int) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    checks = (
        (f"Subject: [PATCH {index + 1}/2] {SUBJECTS[index]}" in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/Users/" not in text, "personal path leaked"),
        (changed_paths(text) == PATCH_PATHS[index], "changed path set changed"),
        ("arch/arm64/kernel/head.S" not in text,
         "target-side park path must remain unchanged"),
        ("mt6797_a72_p30e_asm.S" not in text,
         "target-side claim must remain unchanged"),
        ("cpu_up(" not in added and "cpu_down(" not in added,
         "extra CPU request added"),
        ("arm_smccc" not in added and "psci_ops" not in added,
         "extra firmware operation added"),
    )
    for passed, message in checks:
        if not passed:
            raise SystemExit(f"{path.name}: {message}")
    if index == 0:
        if "arm64_mt6797_a72_p30e_rearm_cpu9" not in added:
            raise SystemExit(f"{path.name}: rearm primitive missing")
        if "smp_store_release" not in added:
            raise SystemExit(f"{path.name}: ordered EMPTY publication missing")
    else:
        for marker in (
            "MT6797_A72_RESTORE_STAGE_P30E_REARMED",
            ".p30e_rearm = mt6797_a72_hotplug_restore_p30e_rearm",
            "GEMINI_A72_HOTPLUG_P30E_REARMED",
            "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 17U",
        ):
            if marker not in added:
                raise SystemExit(f"{path.name}: integration marker missing: {marker}")


def validate_source(root: Path, phase: str) -> str:
    return run("python3", str(SCRIPT_DIR / "validate_p30e_rearm_source.py"),
               "--source-root", str(root), "--phase", phase, cwd=root)


def test_source(root: Path, phase: str) -> str:
    return run("python3", str(SCRIPT_DIR / "test_p30e_rearm_source.py"),
               "--source-root", str(root), "--phase", phase, cwd=root)


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
    source_state = (source_root / ".gemini-source-state").read_text().strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    validate_parent(source_root)

    with tempfile.TemporaryDirectory(prefix="mt6797-a72-p30e-rearm-") as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0506 P30E rearm parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0506.", "2026-09-04T03:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "p30e_rearm_source_edits.py"),
            "--source-root", str(source), "--phase", "primitive", cwd=source)
        primitive_validation = validate_source(source, "primitive")
        primitive_mutations = test_source(source, "primitive")
        commit(
            source, SUBJECTS[0],
            "Validate the exact consumed CPU9 P30E publication and rebuild its\n"
            "immutable request as a one-shot sequence-2 EMPTY target. Preserve\n"
            "the target-side fail-closed claim and issue no CPU operation.",
            "2026-09-04T03:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "p30e_rearm_source_edits.py"),
            "--source-root", str(source), "--phase", "integration", cwd=source)
        final_validation = validate_source(source, "final")
        final_mutations = test_source(source, "final")
        commit(
            source, SUBJECTS[1],
            "Accept the proven primary-off and per-core-off CPU9 state, rearm\n"
            "the exact P30E slot, and retain that boundary before the existing\n"
            "single restore CPU_ON. Fail with zero CPU_ON calls on any error.",
            "2026-09-04T03:02:00Z",
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
        patches: list[Path] = []
        for index, generated_path in enumerate(generated):
            patch = package / PATCH_NAMES[index]
            shutil.move(generated_path, patch)
            subprocess.run(
                ("perl", str(source_root / "scripts/checkpatch.pl"),
                 "--fix-inplace", "--strict", "--no-tree", "--ignore",
                 CHECKPATCH_IGNORE, str(patch)),
                cwd=source_root, check=False, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            validate_patch(patch, index)
            run("perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
                cwd=source_root)
            patches.append(patch)
        (package / "series").write_text("\n".join(PATCH_NAMES) + "\n")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patches[0]), cwd=replay)
        run("git", "apply", str(patches[0]), cwd=replay)
        replay_primitive = validate_source(replay, "primitive")
        run("git", "apply", "--check", str(patches[1]), cwd=replay)
        run("git", "apply", str(patches[1]), cwd=replay)
        replay_final = validate_source(replay, "final")
        replay_mutations = test_source(replay, "final")
        (package / "source-validation.txt").write_text(
            primitive_validation + "\n" + primitive_mutations + "\n" +
            final_validation + "\n" + final_mutations + "\n" +
            replay_primitive + "\n" + replay_final + "\n" +
            replay_mutations + "\n"
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            "generated_patch_count=2\n"
            "target_cpu=9\n"
            "p30e_controller_sequence_after=2\n"
            "target_claim_changed=false\n"
            "head_S_changed=false\n"
            f"primitive_mutations_rejected={len(PRIMITIVE_MUTATIONS)}\n"
            f"final_mutations_rejected={len(FINAL_MUTATIONS)}\n"
            "restore_cpu_on_calls_max=1\n"
            "rearm_failure_cpu_on_calls=0\n"
            "retry_calls_added=0\n"
            "ledger_version=0x00010003\n"
            "ledger_stages=14,15,16,17,18\n"
            "successful_ledger_writes_max=649\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance)
        sums = [f"{sha256(path)}  {path.name}"
                for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("target_cpu=9")
    print("p30e_controller_sequence_after=2")
    print("target_claim_changed=false")
    print("head_S_changed=false")
    print(f"primitive_mutations_rejected={len(PRIMITIVE_MUTATIONS)}")
    print(f"final_mutations_rejected={len(FINAL_MUTATIONS)}")
    print("restore_cpu_on_calls_max=1")
    print("rearm_failure_cpu_on_calls=0")
    print("retry_calls_added=0")
    print("ledger_version=0x00010003")
    print("ledger_stages=14,15,16,17,18")
    print("successful_ledger_writes_max=649")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
