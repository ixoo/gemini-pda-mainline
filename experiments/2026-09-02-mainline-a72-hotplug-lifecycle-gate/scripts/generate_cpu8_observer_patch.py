#!/usr/bin/env python3
"""Generate the disconnected MT6797 retained-CPU8 observer patch."""

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
PATCH_NAME = "0494-soc-mediatek-add-bounded-retained-CPU8-observer.patch"
EXPECTED_SOURCE_STATE = (
    "fa3ac2028c2b325c380cb0ca41ec537e9039cc16fdea8cfacc490e7edd5ebd27"
)
RECONSTRUCTED_PARENT_STATE = (
    "cb7d204abbf314d61b8f740cfa8bc6b3878fa8febec00fd7889684db414f2e55"
)
PARENT_SERIES_SHA256 = (
    "5443137c4363ee685639942e2625732061b5ad5f5c1bfe05c5b5437d29f1e2f4"
)
PARENT_PATCH_SHA256 = (
    "54d4d38d7fd9f7337a41a771ab82d06a5ce90d36808a411feae044d5fe97b8d7"
)
PREPARED_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "be44f0d71be519b34faa5ed7f4f4e2e60b053b475fed9fe862cbef72afa6be4c",
    "drivers/soc/mediatek/Makefile":
        "3757141478a0765a93456b93c65f4621d42d89b6dfc9c563f0b901b8908b4d3e",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "521d061e20584d518f027e40f0c8a1165a4ac11221c705227d260cbe04440dbb",
}
RECONSTRUCTED_PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "fe4e40699e056da8551ce59ba814bc5cde02cf483d6e3e08e39c263ae667abc3",
    "drivers/soc/mediatek/Makefile":
        "8a7dbb840fd4939fa40186ceee71620a203852b3ee6bff49a009c92ae8d0009a",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "521d061e20584d518f027e40f0c8a1165a4ac11221c705227d260cbe04440dbb",
}
EXPECTED_PATHS = tuple(sorted((
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-cpu8-observer-internal.h",
    "drivers/soc/mediatek/mt6797-a72-cpu8-observer-test.c",
    "drivers/soc/mediatek/mt6797-a72-cpu8-observer.c",
)))
CHECKPATCH_IGNORE = (
    "MISSING_SIGN_OFF,FILE_PATH_CHANGES,LONG_LINE,OPEN_ENDED_LINE"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=env,
    )


def copy_parent(source_root: Path, destination: Path) -> None:
    for relative in PREPARED_HASHES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    kconfig = destination / "drivers/soc/mediatek/Kconfig"
    text = kconfig.read_text(encoding="utf-8")
    start_marker = "\nconfig MTK_MT6797_A72_CPU8_OBSERVER\n"
    end_marker = "\nconfig MTK_MMSYS\n"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise SystemExit("cannot reconstruct exact pre-0494 Kconfig parent")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    kconfig.write_text(text[:start] + text[end:], encoding="utf-8")
    makefile = destination / "drivers/soc/mediatek/Makefile"
    text = makefile.read_text(encoding="utf-8")
    observer_lines = (
        "obj-$(CONFIG_MTK_MT6797_A72_CPU8_OBSERVER) += "
        "mt6797-a72-cpu8-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU8_OBSERVER_KUNIT_TEST) += "
        "mt6797-a72-cpu8-observer-test.o\n"
    )
    if text.count(observer_lines) != 1:
        raise SystemExit("cannot reconstruct exact pre-0494 Makefile parent")
    makefile.write_text(text.replace(observer_lines, "", 1), encoding="utf-8")
    for relative, expected in RECONSTRUCTED_PARENT_HASHES.items():
        if sha256(destination / relative) != expected:
            raise SystemExit(f"reconstructed parent changed: {relative}")


def normalize_patch_style(source_root: Path, path: Path) -> None:
    subprocess.run(
        (
            "perl", str(source_root / "scripts/checkpatch.pl"),
            "--fix-inplace", "--strict", "--no-tree", "--ignore",
            CHECKPATCH_IGNORE, str(path),
        ),
        cwd=source_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit("checkpatch style normalization lost generated patch")


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
        (
            "Subject: [PATCH] soc: mediatek: add bounded retained-CPU8 observer"
            in text,
            "patch subject changed",
        ),
        (
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            "synthetic archive identity changed",
        ),
        ("Signed-off-by:" not in text, "synthetic sign-off forbidden"),
        ("/" + "Users/" not in text, "personal path leaked"),
        (changed == EXPECTED_PATHS, "changed path set changed"),
        (
            added.count("smp_call_function_single(cpu, function, info, 0)") == 1,
            "asynchronous IPI call count changed",
        ),
        (
            added.count("wait_for_completion_timeout(completion, timeout)") == 1,
            "bounded completion call count changed",
        ),
        ("wait_for_completion(" not in added, "unbounded wait added"),
        ("platform_driver" not in added, "production driver caller added"),
        (
            "cpu_up(" not in added and "cpu_down(" not in added and
            "remove_cpu(" not in added and "add_cpu(" not in added,
            "CPU request added",
        ),
        (
            "psci_ops." not in added and "cpu_psci_ops." not in added and
            "arm_smccc" not in added,
            "PSCI or SMC call added",
        ),
        (
            "mt6797_psci_cpu_can_disable" not in added,
            "CPU-disable veto touched",
        ),
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
        encoding="utf-8"
    ).strip()
    if source_state != EXPECTED_SOURCE_STATE:
        raise SystemExit("prepared source state changed")
    for relative, expected in PREPARED_HASHES.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise SystemExit(f"prepared source changed: {relative}")

    with tempfile.TemporaryDirectory(
        prefix="mt6797-a72-cpu8-observer-generation-"
    ) as name:
        temp = Path(name)
        source = temp / "source"
        copy_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run(
            "git", "config", "user.email", "gemini-mainline@example.invalid",
            cwd=source,
        )
        commit(
            source,
            "MT6797 post-0493 CPU8-observer parent",
            "Exact relevant source copied from the canonical prepared tree through 0493.",
            "2026-09-03T04:00:00Z",
            check_diff=False,
        )
        parent = run("git", "rev-parse", "HEAD", cwd=source)
        editor = str(SCRIPT_DIR / "cpu8_observer_source_edits.py")
        validator = str(SCRIPT_DIR / "validate_cpu8_observer_source.py")
        mutations = str(SCRIPT_DIR / "test_cpu8_observer_source.py")
        run("python3", editor, "--source-root", str(source), cwd=source)
        source_validation = run(
            "python3", validator, "--source-root", str(source), cwd=source
        )
        mutation_validation = run(
            "python3", mutations, "--source-root", str(source), cwd=source
        )
        commit(
            source,
            "soc: mediatek: add bounded retained-CPU8 observer",
            "Queue one asynchronous callback to CPU8, validate the exact active\n"
            "CPU9-down identity at OFF_COMMITTED, and bound controller waiting\n"
            "to 250 ms. Keep the one-shot context disconnected from callers.",
            "2026-09-03T04:01:00Z",
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
        normalize_patch_style(source_root, patch)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", "--ignore", CHECKPATCH_IGNORE, str(patch),
            cwd=source_root,
        )
        (package / "series").write_text(PATCH_NAME + "\n", encoding="utf-8")

        replay = temp / "replay"
        copy_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        run("git", "apply", "--check", str(patch), cwd=replay)
        run("git", "apply", str(patch), cwd=replay)
        replay_validation = run(
            "python3", validator, "--source-root", str(replay), cwd=replay
        )
        replay_mutations = run(
            "python3", mutations, "--source-root", str(replay), cwd=replay
        )
        (package / "source-validation.txt").write_text(
            source_validation + "\n" + mutation_validation + "\n" +
            replay_validation + "\n" + replay_mutations + "\n",
            encoding="utf-8",
        )
        provenance = (
            f"repository_commit={args.repository_commit}\n"
            f"prepared_source_state={source_state}\n"
            f"reconstructed_parent_state={RECONSTRUCTED_PARENT_STATE}\n"
            f"parent_series_sha256={PARENT_SERIES_SHA256}\n"
            f"parent_patch_sha256={PARENT_PATCH_SHA256}\n"
            "generated_patch_count=1\n"
            "target_cpu=8\n"
            "dispatch=smp_call_function_single-wait-0\n"
            "dispatch_calls=1\n"
            "controller_wait_timeout_ms=250\n"
            "context_lifetime=binder-owned-one-shot\n"
            "identity=exact-down-off-committed\n"
            "retry_calls=0\n"
            "synchronous_wait_1_calls=0\n"
            "focused_kunit_cases=7\n"
            "unsafe_mutations_rejected=21\n"
            "production_callers=0\n"
            "device_tree_nodes=0\n"
            "runtime_ipis=0\n"
            "mt6797_cpu_can_disable=false\n"
            "native_vm_build=none\n"
            "boot_candidate=false\n"
            "device_action=none\n"
        )
        (package / "provenance.txt").write_text(provenance, encoding="utf-8")
        sums = [
            f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text(
            "\n".join(sums) + "\n", encoding="utf-8"
        )
        shutil.copytree(package, output)

    print(f"generated_package={output}")
    print("generated_patch_count=1")
    print("target_cpu=8")
    print("dispatch=smp_call_function_single-wait-0")
    print("dispatch_calls=1")
    print("controller_wait_timeout_ms=250")
    print("context_lifetime=binder-owned-one-shot")
    print("identity=exact-down-off-committed")
    print("focused_kunit_cases=7")
    print("unsafe_mutations_rejected=21")
    print("production_callers=0")
    print("runtime_ipis=0")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
