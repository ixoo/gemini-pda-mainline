#!/usr/bin/env python3
"""Generate and audit the CPU9 pre-ledger progress wiring patch."""

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

import progress_wiring_source_edits
import validate_progress_wiring_source


PATCH_NAME = "0472-soc-mediatek-wire-CPU9-pre-ledger-progress.patch"
SUBJECT = "soc: mediatek: wire CPU9 pre-ledger progress"
CHANGED_PATHS = tuple(sorted(progress_wiring_source_edits.PARENT_HASHES))
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "cpu_down(", "remove_cpu(",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "kernel_restart(", "orderly_poweroff(",
)
CHECKPATCH_IGNORE = "MISSING_SIGN_OFF,FILE_PATH_CHANGES,OPEN_ENDED_LINE"


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
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-09-01T21:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T21:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in progress_wiring_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"managed wiring parent changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run("git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root)
    commit(root, "Gemini post-0471 wiring parent",
           "Synthetic exact-source parent only.", 20)


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "drivers/soc/mediatek/Kconfig",
            "depends on PSTORE_GEMINI_ADMISSION_TRACE=y || "
            "PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y",
            "depends on PSTORE_GEMINI_ADMISSION_TRACE=y",
        ),
        (
            "drivers/soc/mediatek/Kconfig",
            "\tdepends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y\n\tdefault n",
            "\tdefault n",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "GEMINI_CPU9_PROGRESS_CPU8_PROOF, true",
            "GEMINI_CPU9_PROGRESS_CPU8_PROOF, false",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH, false",
            "GEMINI_CPU9_PROGRESS_PREPARE, false",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
            "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU8)",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "GEMINI_CPU9_PROGRESS_BINDER_ENTRY",
            "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            ".progress_checkpoint = gemini_cpu9_progress_checkpoint",
            ".progress_checkpoint = gemini_cpu9_ledger_checkpoint",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN",
            "GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-test.c",
            "stage <= GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH",
            "stage < GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\treturn mt6797_a72_cpu9_admission_terminal(\n"
            "\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_NONE, 0);",
            "\tcpu_down(MT6797_A72_CPU9_EXECUTOR_CPU9);\n"
            "\treturn mt6797_a72_cpu9_admission_terminal(\n"
            "\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_NONE, 0);",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"wiring mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_progress_wiring_source.validate(root)
        except ValueError:
            rejected += 1
        else:
            raise SystemExit(f"wiring mutation escaped: {relative}: {old}")
        finally:
            path.write_text(original, encoding="utf-8")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated wiring patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated wiring patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated wiring patch file count changed")
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated wiring path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated wiring token: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-progress-wiring-") as name:
        temporary = Path(name)
        root = temporary / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        progress_wiring_source_edits.apply(root)
        markers = validate_progress_wiring_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "Record each CPU8-proof-to-CPU9-ledger boundary in the bounded\n"
            "third-record progress lane. Require durable stages 1 through 6\n"
            "before dispatch, stages 7 through 9 in the binder, and stage 10\n"
            "only after add_cpu() returns.\n\n"
            "Keep the single existing CPU9 request and add no CPU_OFF, retry,\n"
            "watchdog, cluster, reset, storage, or automatic boot action.",
            21,
        )
        changed = run("git", "diff", "--name-only", f"{parent}..HEAD",
                      cwd=root).splitlines()
        if changed != list(CHANGED_PATHS):
            raise SystemExit(f"generated wiring file set changed: {changed}")

        generated_dir = temporary / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated wiring patch")
        patch = generated_dir / generated[0]
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            CHECKPATCH_IGNORE, str(patch), cwd=temporary,
        )

        replay = temporary / "replay"
        replay.mkdir()
        prepare_parent(source_root, replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate_progress_wiring_source.validate(replay) != markers:
            raise SystemExit("wiring replay validation markers changed")

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
            "canonical_parent=0471",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "checkpatch_ignored=missing-signoff-file-path-open-ended-line",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "physical_cpu_request=none-during-generation",
            "retained_ram_write=none-during-generation",
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
