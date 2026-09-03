#!/usr/bin/env python3
"""Generate the exact production CPU9 hotplug binding patch pair."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_hotplug_binding_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAMES = (
    "0501-soc-mediatek-bind-one-shot-CPU9-hotplug-transaction.patch",
    "0502-soc-mediatek-test-private-CPU9-hotplug-transition.patch",
)
EXPECTED_SOURCE_STATE = (
    "6104a904d318ee2061c918793cdae640ce206aa57f7a31720617fdd74902b001"
)
PARENT_HASHES = {
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
    "arch/arm64/include/asm/cpu_ops.h":
        "2a463bd0ce39c4855959c0de437887c3a2deb99fcff49f8b70019308ddd81ead",
    "arch/arm64/kernel/smp.c":
        "50c9255d48ce5cb62df5a4ed064cb092de09512c08a3d90153c384c07eb781ab",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "521d061e20584d518f027e40f0c8a1165a4ac11221c705227d260cbe04440dbb",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "7592a814f23ef948c9306ef9b43ca472b6aa7de2f077f5fa0097767ff1edc1a0",
    "include/linux/cpu.h":
        "845d3d82ef99679782e3b881e83dfb563b5e1df70e8a0c60101d5858712b7337",
    "kernel/cpu.c":
        "84fc7f9af337eb193cddcf6e942f31868ab88d4c2fa0dde4d616e9b65de706ce",
    "include/linux/device.h":
        "68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe",
    "drivers/base/core.c":
        "8810cf8a16706ef8f86fcc4944e1bfd8158012af415a6ec2e47a9bf02d9a3b09",
    "include/linux/psci.h":
        "f642acf4edff8f82f99ba2cb576589e61f1b74ef9d0ad3cd03415e90ab74c288",
    "drivers/soc/mediatek/Kconfig":
        "12609a978a55f3f60e0f81f928353a04f72d0a76a95cf6faab27cc33880cc44f",
    "drivers/soc/mediatek/Makefile":
        "9724ccf7c4994dfe350c926fd1402583c85633bf406b28d7abeca5f0575b2d54",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "df7e85df73b5101f67fec8041aaa403822a4d4494a10822db49a4302e269c44a",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-internal.h":
        "370bc0883e7ced1daa5f92488130d127463d7e4dd6e4b45076936da32a483cb4",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core-internal.h":
        "a99747145c411782f33c65b5465f755d0215ebe819fff8d7bbbf1f96c857c3b8",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binder-core.c":
        "bdb3f7013418664304e4baced6887fdfb3823135a2bf085c54ebefb831c41d28",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h":
        "062a14e591c5f4122cfde31f208f2f3753c116c8a5fea3ae00ab23f948be02ab",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c":
        "fef564fc32bb202aa984ef45aa545042ba3d0f089408ca6c0e1fe3f5701cbe56",
    "drivers/soc/mediatek/mt6797-a72-restore-executor-internal.h":
        "9b13ef4b20f85cfb638d2e47b01cb4f767b6c34d39d5006de10f11df6258c79b",
    "drivers/soc/mediatek/mt6797-a72-restore-executor.c":
        "7f7eb389e206dbb9913d2d70be1c8cf99e4560dcfe04a329c9ab57dd9250780c",
    "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-internal.h":
        "890bcd75e968188815e0c476592abf32476dbb809462e7f9ad44c50c90f0470d",
    "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot.c":
        "4ca819533da168346cddcd526c0ac2f3fe05fc3c8de92e7c66f8174afdce53a9",
    "drivers/soc/mediatek/mt6797-a72-cpu8-observer-internal.h":
        "72ff885debf9284e114983b3bf006e5097a3dd9bb31bfc830b763e30417b341b",
    "drivers/soc/mediatek/mt6797-a72-cpu8-observer.c":
        "238522d9041eac10c0503d92d2396bd2490175c97f5a508fae0989848680a7d9",
    "include/linux/soc/mediatek/mt6797-a72-binder.h":
        "0a18e4e05394c3425e43636eed4be3ab420648f16e9919ad2cc5960f43e72086",
    "drivers/soc/mediatek/mt6797-a72-binder.c":
        "9b6d07653e40d7338aeb945c04c3f02f56aad29224bc8530364d2d1b56d18042",
    "include/linux/gemini_a72_hotplug_ledger.h":
        "e5a3dbe56be03821104240e984c9efc9e07072c5ce980b9da11864586c7f81fd",
    "fs/pstore/gemini_a72_hotplug_ledger.c":
        "e304dbebe48d3689f7300dc598e4697a4b8f2b75313e73254c9fbe98d23230e2",
}
IMPLEMENTATION_PATHS = tuple(sorted((
    "arch/arm64/kernel/mt6797_psci.c",
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c",
    "include/linux/soc/mediatek/mt6797-a72-hotplug-binding.h",
)))
TEST_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c",
)))
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


def normalize_patch(source_root: Path, patch: Path) -> None:
    subprocess.run(
        ("perl", str(source_root / "scripts/checkpatch.pl"),
         "--fix-inplace", "--strict", "--no-tree", "--ignore",
         CHECKPATCH_IGNORE, str(patch)),
        cwd=source_root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not patch.is_file() or patch.is_symlink():
        raise SystemExit(f"checkpatch normalization lost {patch.name}")


def validate_patch(path: Path, subject: str,
                   expected_paths: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    changed = tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))
    checks = (
        ("Subject: [PATCH" in text and subject in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/Users/" not in text, "personal path leaked"),
        (changed == expected_paths, "changed path set changed"),
        ("mediatek,mt6797-a72-hotplug-binding" not in text,
         "new Device Tree interface added"),
        ("cpu_can_disable(unsigned int cpu)\n+{\n+\treturn cpu == 9" not in text,
         "public CPU9 disable gate opened"),
    )
    for passed, message in checks:
        if not passed:
            raise SystemExit(f"{path.name}: {message}")


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
    source_state = (source_root / ".gemini-source-state").read_text(
        encoding="utf-8").strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    for relative, expected in PARENT_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-hotplug-binding-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment",
            cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source)
        commit(
            source, "MT6797 post-0500 hotplug-binding parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through patch 0500.",
            "2026-09-03T20:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "hotplug_binding_source_edits.py"),
            "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", str(SCRIPT_DIR / "validate_hotplug_binding_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: bind one-shot CPU9 hotplug transaction",
            "Keep the public MT6797 A72 disable veto closed while one exact\n"
            "admission-task request temporarily opens CPU9's cached device\n"
            "gate under the hotplug lock. Bind the proven down, retained\n"
            "observation, record-4, and parent-linked restore callbacks.",
            "2026-09-03T20:01:00Z",
        )

        run("python3", str(SCRIPT_DIR / "hotplug_binding_test_edits.py"),
            "--source-root", str(source), cwd=source)
        final_validation = run(
            "python3", str(SCRIPT_DIR / "validate_hotplug_binding_source.py"),
            "--source-root", str(source), "--require-tests", cwd=source,
        )
        mutations = run(
            "python3", str(SCRIPT_DIR / "test_hotplug_binding_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: test private CPU9 hotplug transition",
            "Exercise the exact CPU and task gate, device-hotplug lock scope,\n"
            "temporary offline-disabled transition, restoration on success\n"
            "and failure, and down/restore route discrimination in memory.",
            "2026-09-03T20:02:00Z",
        )

        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != len(PATCH_NAMES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "soc: mediatek: bind one-shot CPU9 hotplug transaction",
            "soc: mediatek: test private CPU9 hotplug transition",
        )
        path_sets = (IMPLEMENTATION_PATHS, TEST_PATHS)
        for generated_name, patch_name, subject, paths in zip(
            generated, PATCH_NAMES, subjects, path_sets
        ):
            patch = package / patch_name
            shutil.move(generated_name, patch)
            normalize_patch(source_root, patch)
            validate_patch(patch, subject, paths)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
                cwd=source_root,
            )
        (package / "series").write_text(
            "\n".join(PATCH_NAMES) + "\n", encoding="utf-8"
        )

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch_name in PATCH_NAMES:
            patch = package / patch_name
            run("git", "apply", "--check", str(patch), cwd=replay)
            run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_hotplug_binding_source.py"),
            "--source-root", str(replay), "--require-tests", cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_hotplug_binding_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + final_validation + "\n" + mutations +
            "\n" + replay_validation + "\n" + replay_mutations + "\n",
            encoding="utf-8",
        )
        (package / "provenance.txt").write_text(
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"prepared_interfaces={len(PARENT_HASHES)}\n"
            "generated_patch_count=2\n"
            "public_cpu_can_disable=false\n"
            "private_transition=device-hotplug-lock-scoped-cpu9-only\n"
            "private_offline_calls=1\n"
            "restore_add_cpu_calls=1\n"
            "cpu_off_calls=one-direct-target-callback\n"
            "affinity_info_calls=one-direct-level0\n"
            "cpu_on_calls=one-restore-boot\n"
            "successful_ledger_stages=1-7,9-17\n"
            "cpu_off_return_stage=8-terminal-only\n"
            "focused_kunit_cases=9\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n",
            encoding="utf-8",
        )
        sums = [
            f"{sha256(item)}  {item.name}"
            for item in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print(f"prepared_interfaces={len(PARENT_HASHES)}")
    print("public_cpu_can_disable=false")
    print("private_transition=device-hotplug-lock-scoped-cpu9-only")
    print("private_offline_calls=1")
    print("restore_add_cpu_calls=1")
    print("cpu_off_calls=one-direct-target-callback")
    print("affinity_info_calls=one-direct-level0")
    print("cpu_on_calls=one-restore-boot")
    print("successful_ledger_stages=1-7,9-17")
    print("cpu_off_return_stage=8-terminal-only")
    print("focused_kunit_cases=9")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
