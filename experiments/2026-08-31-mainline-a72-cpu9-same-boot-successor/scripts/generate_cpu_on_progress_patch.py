#!/usr/bin/env python3
"""Generate and audit the CPU9 CPU_ON substage progress patch."""

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

import cpu_on_progress_source_edits
import validate_cpu_on_progress_source


PATCH_NAME = "0479-soc-mediatek-trace-CPU9-CPU_ON-substages.patch"
SUBJECT = "soc: mediatek: trace CPU9 CPU_ON substages"
CHANGED_PATHS = tuple(sorted(cpu_on_progress_source_edits.PARENT_HASHES))
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "cpu_down(", "remove_cpu(",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "kernel_restart(", "orderly_poweroff(",
)
CHECKPATCH_IGNORE = (
    "MISSING_SIGN_OFF,FILE_PATH_CHANGES,OPEN_ENDED_LINE,"
    "PARENTHESIS_ALIGNMENT,LINE_SPACING"
)


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
        "GIT_AUTHOR_DATE": f"2026-09-02T02:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-02T02:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in cpu_on_progress_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"managed CPU_ON-progress parent changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(
        root, "Gemini post-0478 CPU_ON-progress parent",
        "Synthetic exact-source parent only.", 10,
    )


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "fs/pstore/gemini_cpu9_progress_ledger.c",
            "latest.stage != GEMINI_CPU9_LEDGER_CPU_ON",
            "latest.stage != GEMINI_CPU9_LEDGER_PRESTATE",
        ),
        (
            "fs/pstore/gemini_cpu9_progress_ledger.c",
            "GEMINI_CPU9_PROGRESS_CPU8_BASE + 3 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE",
            "GEMINI_CPU9_PROGRESS_CPU8_BASE + 4 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE",
        ),
        (
            "fs/pstore/gemini_cpu9_progress_ledger.c",
            "latest.stage != GEMINI_CPU9_LEDGER_CPU_ON || latest.terminal",
            "latest.stage != GEMINI_CPU9_LEDGER_CPU_ON",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\t       ops->cpu_on_progress_checkpoint && ops->ledger_begin &&",
            "\t       ops->ledger_begin &&",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\t\t.cpu_on_progress_checkpoint =\n"
            "\t\t\tgemini_cpu9_cpu_on_progress_checkpoint,",
            "\t\t.cpu_on_progress_checkpoint = NULL,",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c",
            "\tret = binder->cpu_boot(cpu);",
            "\tret = binder->cpu_boot(cpu);\n\tret = binder->cpu_boot(cpu);",
        ),
        (
            "fs/pstore/gemini_cpu9_progress_ledger_test.c",
            "\tKUNIT_CASE(cpu9_cpu_on_progress_sequence_test),",
            "\t/* sequence test omitted */",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c",
            "\tKUNIT_CASE(mt6797_cpu9_binder_cpu_on_progress_failures_test),",
            "\t/* progress failure test omitted */",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(
                f"CPU_ON-progress mutation anchor changed: {relative}: {old}"
            )
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_cpu_on_progress_source.validate(root)
        except (ValueError, IndexError):
            rejected += 1
        else:
            raise SystemExit(
                f"CPU_ON-progress mutation escaped: {relative}: {old}"
            )
        finally:
            path.write_text(original, encoding="utf-8")
    return rejected


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated CPU_ON-progress patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated CPU_ON-progress patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated CPU_ON-progress patch file count changed")
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated CPU_ON-progress path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated CPU_ON-progress token: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-cpu-on-progress-") as name:
        temporary = Path(name)
        root = temporary / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        cpu_on_progress_source_edits.apply(root)
        markers = validate_cpu_on_progress_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "The first CPU9 attempt after repairing the CPU-hotplug lock\n"
            "recursion opens the CPU9 ledger, completes PRESTATE, and stops\n"
            "inside its CPU_ON binder operation. The current retained records\n"
            "cannot distinguish P30E prepare, membership begin, P30E arm, or\n"
            "the existing CPU boot callback.\n\n"
            "Use the still-empty fourth ramoops record for eight ordered\n"
            "before/after checkpoints around those exact calls. Require the\n"
            "CPU9 transition ledger at BEFORE CPU_ON before claiming the lane,\n"
            "and fail closed on any diagnostic error.\n\n"
            "This does not add a CPU request, CPU_OFF, retry, cluster effect,\n"
            "reset, storage, or boot-policy path.",
            11,
        )
        changed = run(
            "git", "diff", "--name-only", f"{parent}..HEAD", cwd=root
        ).splitlines()
        if changed != list(CHANGED_PATHS):
            raise SystemExit(f"generated CPU_ON-progress file set changed: {changed}")

        generated_dir = temporary / "generated"
        generated_dir.mkdir()
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=root,
        ).splitlines()
        if len(generated) != 1:
            raise SystemExit("expected exactly one generated CPU_ON-progress patch")
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
        if validate_cpu_on_progress_source.validate(replay) != markers:
            raise SystemExit("CPU_ON-progress replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        (output / "series").write_text(
            f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8"
        )
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0478",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "checkpatch_ignored=missing-signoff-file-path-open-ended-line-"
            "parenthesis-alignment-line-spacing",
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
