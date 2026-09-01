#!/usr/bin/env python3
"""Generate and audit the CPU9 executor KUnit fixture-type repair."""

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


PATCH_NAME = "0467-soc-mediatek-fix-CPU9-executor-test-fixture-type.patch"
SUBJECT = "soc: mediatek: fix CPU9 executor test fixture type"
SOURCE = Path("drivers/soc/mediatek/mt6797-a72-cpu9-executor-test.c")
PARENT_SHA256 = "94fed63551a7c2b43254898e9c76b6ba1768224b88e57fcb8409873f05867e8c"
WRONG_TYPE = "struct mt6797_cpu9_executor_test_state"
FIXED_TYPE = "struct mt6797_a72_cpu9_executor_test_state"


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


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-09-01T00:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T00:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    source = source_root / SOURCE
    if not source.is_file() or source.is_symlink():
        raise SystemExit("managed parent CPU9 executor test is absent or unsafe")
    if sha256(source) != PARENT_SHA256:
        raise SystemExit("managed parent CPU9 executor test changed")
    target = root / SOURCE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(root, "Gemini post-0466 generation parent",
           "Synthetic exact-source parent only.", 54)


def apply_fix(root: Path) -> None:
    path = root / SOURCE
    text = path.read_text(encoding="utf-8")
    if text.count(WRONG_TYPE) != 10 or text.count(FIXED_TYPE) != 11:
        raise SystemExit("CPU9 executor fixture-type anchors changed")
    path.write_text(text.replace(WRONG_TYPE, FIXED_TYPE), encoding="utf-8")


def validate(root: Path) -> tuple[str, ...]:
    text = (root / SOURCE).read_text(encoding="utf-8")
    if WRONG_TYPE in text:
        raise ValueError("inconsistent CPU9 executor fixture type remains")
    if text.count(FIXED_TYPE) != 21:
        raise ValueError("CPU9 executor fixture type inventory changed")
    if text.count("KUNIT_CASE(mt6797_cpu9_executor_") != 10:
        raise ValueError("focused CPU9 executor case inventory changed")
    return (
        "cpu9_executor_fixture_validation=pass",
        "fixture_type=mt6797_a72_cpu9_executor_test_state",
        "fixture_type_references=21",
        "focused_kunit_cases=10",
        "production_files_changed=0",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
        "production_callers=0",
    )


def validate_mutations(root: Path) -> int:
    mutations = (
        (f"{FIXED_TYPE} {{", f"{WRONG_TYPE} {{"),
        (f"state = ({FIXED_TYPE}){{", f"state = ({WRONG_TYPE}){{"),
    )
    path = root / SOURCE
    rejected = 0
    for old, new in mutations:
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"fixture mutation anchor changed: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate(root)
        except ValueError:
            rejected += 1
        finally:
            path.write_text(original, encoding="utf-8")
    if rejected != len(mutations):
        raise SystemExit("CPU9 executor fixture mutation was not rejected")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != 1 or f" a/{SOURCE}" not in text:
        raise SystemExit("generated patch file set changed")
    for token in ("Signed-off-by:", "/Users/", "cpu_up(", "cpu_down(",
                  "psci_cpu_on", "psci_cpu_off", "arm_smccc"):
        if token in text:
            raise SystemExit(f"forbidden generated token: {token}")


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

    state = (source_root / ".gemini-source-state").read_text().strip()
    integrity = (source_root / ".gemini-source-integrity").read_text().strip()
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-fixture-fix-") as name:
        temp = Path(name)
        root = temp / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        apply_fix(root)
        markers = validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "Use the declared A72-qualified fixture type consistently in the\n"
            "hardware-free CPU9 executor tests. This repairs compilation only\n"
            "and changes no executor behavior or production source.",
            55,
        )
        changed = run(
            "git", "diff", "--name-only", f"{parent}..HEAD", cwd=root
        ).splitlines()
        if changed != [str(SOURCE)]:
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = temp / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated patch")
        patch = generated_dir / generated[0]
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES", str(patch), cwd=temp,
        )

        replay = temp / "replay"
        replay.mkdir()
        prepare_parent(source_root, replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate(replay) != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(
            f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0466",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "boot_candidate=false",
            "",
        ]), encoding="utf-8")
        sums = output / "SHA256SUMS"
        sums.write_text("\n".join([
            f"{sha256(target)}  {target.name}",
            f"{sha256(output / 'series')}  series",
            f"{sha256(provenance)}  provenance.txt",
            "",
        ]), encoding="utf-8")
        print(provenance.read_text(), end="")
        print(f"patch_sha256={sha256(target)}")
        print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
