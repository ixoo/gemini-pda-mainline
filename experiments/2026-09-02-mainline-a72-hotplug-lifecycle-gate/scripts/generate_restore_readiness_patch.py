#!/usr/bin/env python3
"""Generate the exact bounded CPU9 restore-readiness patch."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_restore_readiness_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAME = "0506-soc-mediatek-gate-CPU9-restore-on-readiness.patch"
EXPECTED_SOURCE_STATE = (
    "95bdf01487ec09a7ed1e99aae0671117798887f16376340efe313e07f218ffc3"
)
PARENT_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c":
        "544c5dc79a0c4ed030255458584a713c91ecba055a28eb2ec27caccc27153e5a",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h":
        "92805d75ed8febdb1cb5973f56a28221007cfd0ebbfc5f8bc7986cb0b564c7c9",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c":
        "f6478ec0215ecc44e1ed5133315e8381fa1b81c84ad3445d9ed46de0663596c5",
    "fs/pstore/gemini_a72_hotplug_ledger.c":
        "e304dbebe48d3689f7300dc598e4697a4b8f2b75313e73254c9fbe98d23230e2",
    "fs/pstore/gemini_a72_hotplug_ledger_internal.h":
        "32020c335792fd068ba6ca7ab21ebdb407045e51343a5f54a2a66d60f00455ae",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c":
        "54a0eb827b6caa85d28d70649c2e80226284493bd9273b061ad52cc15d214809",
    "include/linux/gemini_a72_hotplug_ledger.h":
        "e5a3dbe56be03821104240e984c9efc9e07072c5ce980b9da11864586c7f81fd",
}
EXPECTED_PATHS = tuple(sorted(PARENT_HASHES))
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


def validate_patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    changed = tuple(sorted(
        line[6:] for line in text.splitlines() if line.startswith("+++ b/")
    ))
    checks = (
        ("Subject: [PATCH] soc: mediatek: gate CPU9 restore on readiness"
         in text, "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/Users/" not in text, "personal path leaked"),
        (changed == EXPECTED_PATHS, "changed path set changed"),
        ("MT6797_A72_RESTORE_READY_SAMPLES_MAX 51U" in added,
         "sample bound missing"),
        ("usleep_range(5000, 6000)" in added, "sleep bound missing"),
        ("mt6797_a72_platform_state_snapshot" in added,
         "read-only source missing"),
        ("GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010002U" in added,
         "retained format bump missing"),
        ("cpu_down(" not in added and "cpu_up(" not in added,
         "CPU request added"),
        ("writel(" not in added and "arm_smccc" not in added,
         "hardware effect added"),
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
    source_state = (source_root / ".gemini-source-state").read_text().strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    validate_parent(source_root)

    with tempfile.TemporaryDirectory(prefix="mt6797-a72-restore-readiness-") as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(
            source, "MT6797 post-0505 hotplug parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0505.", "2026-09-04T02:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        run("python3", str(SCRIPT_DIR / "restore_readiness_source_edits.py"),
            "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", str(SCRIPT_DIR / "validate_restore_readiness_source.py"),
            "--source-root", str(source), cwd=source,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_restore_readiness_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: gate CPU9 restore on readiness",
            "Observe CPU9's two raw SPM status words and per-core power-control\n"
            "word for at most 51 samples after completed down. Retain the first\n"
            "and last samples, and issue the existing sole CPU_ON only when both\n"
            "CPU9 status mirrors are clear. A timeout records zero CPU_ON calls.",
            "2026-09-04T02:01:00Z",
        )
        patch_dir = temp / "patches"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(patch_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("generated patch count changed")
        package = temp / "package"
        package.mkdir()
        patch = package / PATCH_NAME
        shutil.move(generated[0], patch)
        subprocess.run(
            ("perl", str(source_root / "scripts/checkpatch.pl"),
             "--fix-inplace", "--strict", "--no-tree", "--ignore",
             CHECKPATCH_IGNORE, str(patch)),
            cwd=source_root, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        validate_patch(patch)
        run("perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
            cwd=source_root)
        (package / "series").write_text(PATCH_NAME + "\n")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", str(SCRIPT_DIR / "validate_restore_readiness_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_restore_readiness_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + mutation_validation + "\n" +
            replay_validation + "\n" + replay_mutations + "\n"
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            "generated_patch_count=1\n"
            "readiness_samples_max=51\n"
            "readiness_sleeps_max=50\n"
            "readiness_sleep_us=5000-6000\n"
            "readiness_source=platform-state-read-only\n"
            "cpu_on_gate=both-CPU9-status-mirrors-clear\n"
            "retained_raw_fields=first-and-last-status-status2-cpu9-pwr-con\n"
            "ledger_version=0x00010002\n"
            "successful_ledger_writes_max=611\n"
            "binding_kunit_cases=13\n"
            "ledger_kunit_cases=14\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "cpu_off_calls_added=0\n"
            "cpu_on_calls_added=0\n"
            "affinity_calls_added=0\n"
            "retry_calls_added=0\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance)
        sums = [f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("readiness_samples_max=51")
    print("readiness_sleeps_max=50")
    print("readiness_sleep_us=5000-6000")
    print("readiness_source=platform-state-read-only")
    print("cpu_on_gate=both-CPU9-status-mirrors-clear")
    print("retained_raw_fields=first-and-last-status-status2-cpu9-pwr-con")
    print("ledger_version=0x00010002")
    print("successful_ledger_writes_max=611")
    print("binding_kunit_cases=13")
    print("ledger_kunit_cases=14")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("cpu_off_calls_added=0")
    print("cpu_on_calls_added=0")
    print("affinity_calls_added=0")
    print("retry_calls_added=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
