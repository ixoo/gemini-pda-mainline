#!/usr/bin/env python3
"""Generate the exact behavior-neutral CPU9 readback bitmap patch."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_readback_bitmap_source import MUTATIONS


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_NAME = "0504-soc-mediatek-record-CPU9-readback-mismatch-bitmap.patch"
EXPECTED_SOURCE_STATE = (
    "91b3bdb345c962aa9c1b81d333520bef1e9f687574777ea069814377e4db33f0"
)
PARENT_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h":
        "062a14e591c5f4122cfde31f208f2f3753c116c8a5fea3ae00ab23f948be02ab",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c":
        "fef564fc32bb202aa984ef45aa545042ba3d0f089408ca6c0e1fe3f5701cbe56",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c":
        "bad8220778cad8efbc4fbed0b9fa3a857a849b97deb0a858e92ded8f2b68b143",
    "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c":
        "0453ae5835e559de87331c10688926043b923da164fafbc5b65244b7dd992e49",
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
        ("Subject: [PATCH] soc: mediatek: record CPU9 readback mismatch bitmap"
         in text, "patch subject changed"),
        ("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
         in text, "synthetic archive identity changed"),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/Users/" not in text, "personal path leaked"),
        (changed == EXPECTED_PATHS, "changed path set changed"),
        ("MT6797_A72_HOTPLUG_READBACK_BITMAP_V1" in added,
         "format marker missing"),
        (added.count("MT6797_A72_HOTPLUG_MISMATCH_") >= 72,
         "bitmap terms or tests missing"),
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

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-readback-bitmap-generation-"
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
            source, "MT6797 post-0503 readback parent",
            "Exact relevant source copied from the canonical prepared tree "
            "through 0503.", "2026-09-04T00:00:00Z", check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        run("python3", str(SCRIPT_DIR / "readback_bitmap_source_edits.py"),
            "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", str(SCRIPT_DIR / "validate_readback_bitmap_source.py"),
            "--source-root", str(source), cwd=source,
        )
        mutation_validation = run(
            "python3", str(SCRIPT_DIR / "test_readback_bitmap_source.py"),
            "--source-root", str(source), cwd=source,
        )
        commit(
            source,
            "soc: mediatek: record CPU9 readback mismatch bitmap",
            "Replace record 4's ambiguous readback Boolean with a self-\n"
            "describing bitmap of the exact already-enforced predicate terms.\n"
            "Keep the acceptance predicate and every hardware action unchanged.",
            "2026-09-04T00:01:00Z",
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
            "python3", str(SCRIPT_DIR / "validate_readback_bitmap_source.py"),
            "--source-root", str(replay), cwd=replay,
        )
        replay_mutations = run(
            "python3", str(SCRIPT_DIR / "test_readback_bitmap_source.py"),
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
            "mismatch_bits=24\n"
            "bitmap_format_bit=31\n"
            "wire_size_changed=false\n"
            "predicate_behavior_changed=false\n"
            "focused_kunit_cases=1\n"
            f"unsafe_mutations_rejected={len(MUTATIONS)}\n"
            "physical_effect_calls=0\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance)
        sums = [
            f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("mismatch_bits=24")
    print("bitmap_format_bit=31")
    print("wire_size_changed=false")
    print("predicate_behavior_changed=false")
    print("focused_kunit_cases=1")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    print("physical_effect_calls=0")
    print("native_vm_build=none")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
