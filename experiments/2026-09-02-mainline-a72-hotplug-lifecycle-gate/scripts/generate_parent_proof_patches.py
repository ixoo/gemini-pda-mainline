#!/usr/bin/env python3
"""Generate the disconnected exact CPU8/CPU9 parent-proof patch pair."""

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
PATCH_NAMES = (
    "0490-arm64-mediatek-prove-exact-A72-terminal-parent.patch",
    "0491-soc-mediatek-prove-exact-A72-binder-parent.patch",
)
PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "37ceccdad257a3365933f0c3ad1576f876eef793af4291b50b84b6dfb68c9f40",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "757a907020c7693339d1488af779e4b026074e4c5ccc463dd0e222fe2737c417",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "747a6fb1ba8ecdba45b3b605d35ee32f6b136a7605a30b100e7ca4b68f6a1e90",
    "include/linux/soc/mediatek/mt6797-a72-binder.h":
        "1e4479343363e08df8641d9c037b77ff60b50de63daf8aab416c464dba97b894",
    "drivers/soc/mediatek/mt6797-a72-binder-internal.h":
        "1ecaf7c6a1e331c0d3fad5cc79a9201b61870b2ab894334247c4cea1d9e2ee98",
    "drivers/soc/mediatek/mt6797-a72-binder.c":
        "0c469e228e78b9c225fe1409cff2e0302b847267da24538c81035a3dd72405ea",
    "drivers/soc/mediatek/mt6797-a72-binder-test.c":
        "97b571cf9102110711a874e299d5ec533be0ec37c2e27f7d9e38876db7cb25cb",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
}
EXPECTED_SOURCE_STATE = (
    "c48bb939a7de2e633e9f4dbfd94e1dc179f46dd68a3fae504ec63e49d3a37dd5"
)
PARENT_SERIES_SHA256 = (
    "1a8751eb0285be3362b7434649e4cf8656056030529179f5ae3046b0bc3aa124"
)
PARENT_WATCHDOG_PATCH_SHA256 = (
    "940c2158c04376d856b7a0cc6b7aa69702883b5e88b2959b3d82589cfce18b91"
)
CHECKPATCH_IGNORE = (
    "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"
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


def normalize_patch_style(source_root: Path, path: Path) -> None:
    subprocess.run(
        (
            "perl", str(source_root / "scripts/checkpatch.pl"),
            "--fix-inplace", "--strict", "--no-tree", "--ignore",
            CHECKPATCH_IGNORE, str(path),
        ),
        cwd=source_root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"checkpatch style normalization lost {path.name}")


def validate_patch(path: Path, subject: str, expected_paths: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    changed = tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))
    checks = (
        ("Subject: [PATCH" in text and subject in text,
         "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        (changed == tuple(sorted(expected_paths)), "changed path set changed"),
        ("cpu_up(" not in added and "cpu_down(" not in added,
         "CPU request added"),
        ("psci_ops." not in added and "arm_smccc" not in added,
         "physical PSCI call added"),
        ("readl(" not in added and "writel(" not in added,
         "MMIO call added"),
        ("mtk_wdt_recovery_takeover(" not in added,
         "watchdog takeover added"),
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
        prefix="mt6797-a72-parent-proof-generation-"
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
            source, "MT6797 post-0489 parent-proof parent",
            "Exact relevant source copied from the canonical prepared tree through 0489.",
            "2026-09-03T16:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        editor = str(SCRIPT_DIR / "parent_proof_source_edits.py")
        validator = str(SCRIPT_DIR / "validate_parent_proof_source.py")
        mutations = str(SCRIPT_DIR / "test_parent_proof_source.py")
        run("python3", editor, "--source-root", str(source),
            "--stage", "membership", cwd=source)
        membership_validation = run(
            "python3", validator, "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "arm64: mediatek: prove exact A72 terminal parent",
            "Publish a locked read-only proof only for exact retired CPU8 and\n"
            "CPU9 success identities, a held matching provider, complete\n"
            "membership, and idle owner and hotplug controllers.",
            "2026-09-03T16:01:00Z",
        )

        run("python3", editor, "--source-root", str(source),
            "--stage", "binder", cwd=source)
        final_validation = run(
            "python3", validator, "--source-root", str(source),
            "--require-binder", cwd=source,
        )
        mutation_validation = run(
            "python3", mutations, "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: prove exact A72 binder parent",
            "Combine the terminal membership proof with the exact CPU8 binder\n"
            "terminal, all ten online CPUs, the matching provider identity,\n"
            "and a read-only validation of the recent watchdog owner. Keep\n"
            "the proof disconnected from production execution.",
            "2026-09-03T16:02:00Z",
        )

        patch_dir = temp / "patches"
        generated = sorted(run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines())
        if len(generated) != len(PATCH_NAMES):
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        subjects = (
            "arm64: mediatek: prove exact A72 terminal parent",
            "soc: mediatek: prove exact A72 binder parent",
        )
        paths = (
            (
                "arch/arm64/include/asm/mt6797_a72_membership.h",
                "arch/arm64/kernel/mt6797_a72_membership.c",
                "arch/arm64/kernel/mt6797_a72_membership_test.c",
            ),
            (
                "drivers/soc/mediatek/mt6797-a72-binder-internal.h",
                "drivers/soc/mediatek/mt6797-a72-binder-test.c",
                "drivers/soc/mediatek/mt6797-a72-binder.c",
                "include/linux/soc/mediatek/mt6797-a72-binder.h",
            ),
        )
        for generated_name, patch_name, subject, expected_paths in zip(
            generated, PATCH_NAMES, subjects, paths
        ):
            patch = package / patch_name
            shutil.move(generated_name, patch)
            normalize_patch_style(source_root, patch)
            validate_patch(patch, subject, expected_paths)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", "--ignore", CHECKPATCH_IGNORE,
                str(patch), cwd=source_root,
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
            "python3", validator, "--source-root", str(replay),
            "--require-binder", cwd=replay,
        )
        replay_mutations = run(
            "python3", mutations, "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            membership_validation + "\n" + final_validation + "\n" +
            mutation_validation + "\n" + replay_validation + "\n" +
            replay_mutations + "\n", encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"parent_series_sha256={PARENT_SERIES_SHA256}\n"
            f"parent_watchdog_patch_sha256={PARENT_WATCHDOG_PATCH_SHA256}\n"
            "generated_patch_count=2\n"
            "membership_parent_proof=exact-read-only\n"
            "binder_parent_proof=exact-read-only\n"
            "membership_kunit_cases=40\n"
            "binder_kunit_cases=10\n"
            "combined_kunit_cases=62\n"
            "watchdog_max_age_ms=5000\n"
            "source_mutation_rejections=20\n"
            "watchdog_takeovers_added=0\n"
            "production_callers=0\n"
            "physical_effect_calls=0\n"
            "mt6797_cpu_can_disable=false\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [f"{sha256(path)}  {path.name}"
                for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("membership_parent_proof=exact-read-only")
    print("binder_parent_proof=exact-read-only")
    print("membership_kunit_cases=40")
    print("binder_kunit_cases=10")
    print("combined_kunit_cases=62")
    print("watchdog_max_age_ms=5000")
    print("source_mutation_rejections=20")
    print("watchdog_takeovers_added=0")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("mt6797_cpu_can_disable=false")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
