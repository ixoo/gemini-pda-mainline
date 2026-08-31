#!/usr/bin/env python3
"""Generate and audit the late-CPU expected-pair model-contract repair."""

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

import source_edits


PATCH_NAME = "0462-arm64-match-late-CPU-expected-pair-by-model.patch"
SUBJECT = "arm64: match late CPU expected pair by model"
ACTION_TOKENS = (
    "cpu_up(", "cpu_down(", "add_cpu(", "remove_cpu(", "cpu_boot(",
    "psci_cpu_on", "psci_cpu_off", "cpu_off(", "regmap_write(",
    "writel(", "writeq(", "memcpy_toio(", "kernel_restart(",
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
        "GIT_AUTHOR_DATE": f"2026-08-31T23:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-31T23:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    source = source_root / source_edits.TARGET
    if not source.is_file() or source.is_symlink():
        raise SystemExit("managed parent source is absent or unsafe")
    target = root / source_edits.TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(root, "Gemini post-0461 generation parent", "Synthetic parent only.", 41)


def operation_counts(text: str) -> dict[str, int]:
    return {token: text.count(token) for token in ACTION_TOKENS}


def validate_mutations(text: str) -> int:
    mutations = (
        (source_edits.NEW, source_edits.OLD),
        ("MIDR_CPU_MODEL_MASK", "MIDR_REVISION_MASK"),
        ("MIDR_CPU_MODEL_MASK", "MIDR_VARIANT_MASK"),
        ("(expected->midr & MIDR_CPU_MODEL_MASK) !=", "expected->midr !="),
        (" !=\n\t\t\t    plan->evidence.expected_target_midr[target])",
         " ==\n\t\t\t    plan->evidence.expected_target_midr[target])"),
        ("plan->evidence.expected_target_midr[target])",
         "(plan->evidence.expected_target_midr[target] & MIDR_CPU_MODEL_MASK))"),
        ("late_expected_target_compare(pair->midr, info->reg_midr,",
         "late_expected_target_compare(pair->midr & MIDR_CPU_MODEL_MASK, "
         "info->reg_midr,")
    )
    rejected = 0
    for old, new in mutations:
        if text.count(old) != 1:
            raise SystemExit(f"mutation anchor changed: {old}")
        mutant = text.replace(old, new, 1)
        try:
            source_edits.validate_result(mutant)
        except SystemExit:
            rejected += 1
    if rejected != len(mutations):
        raise SystemExit("expected-pair model-contract mutation was not rejected")
    return rejected


def validate_result(root: Path, parent_counts: dict[str, int]) -> list[str]:
    text = (root / source_edits.TARGET).read_text(encoding="utf-8")
    source_edits.validate_result(text)
    if operation_counts(text) != parent_counts:
        raise SystemExit("CPU, power, storage, or reboot call inventory changed")
    mutations = validate_mutations(text)
    return [
        "expected_pair_model_contract_validation=pass",
        "a72_r0p1_model_match=accept",
        "a72_other_revision_model_match=accept",
        "a53_r0p1_model_match=reject",
        "revision_bearing_target_model=reject",
        "exact_late_target_midr=unchanged",
        "changed_source_lines=1",
        f"source_mutations_rejected={mutations}",
        "new_cpu_request_paths=0",
        "new_cpu9_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_power_sequence_calls=0",
        "new_storage_writes=0",
        "new_retained_ram_writes=0",
        "new_reboot_paths=0",
    ]


def validate_patch(path: Path) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if SUBJECT not in str(message["Subject"] or ""):
        raise SystemExit("generated patch subject changed")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit("generated patch author changed")
    text = path.read_text(encoding="utf-8")
    if text.count("\ndiff --git ") != 1:
        raise SystemExit("generated patch must change exactly one file")
    added = [
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:] for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    if added != [source_edits.NEW.splitlines()[0]] or removed != [
        source_edits.OLD.splitlines()[0]
    ]:
        raise SystemExit("generated source-line delta changed")
    lowered = "\n".join(added).lower()
    for token in (
        "signed-off-by:", "/users/", "cpu9", "cpu_off", "retry", "reboot",
        *ACTION_TOKENS,
    ):
        if token.lower() in lowered:
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
    with tempfile.TemporaryDirectory(prefix="a72-expected-pair-model-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        parent_text = (root / source_edits.TARGET).read_text(encoding="utf-8")
        source_edits.validate_parent(parent_text)
        parent_counts = operation_counts(parent_text)
        source_edits.apply(root)
        markers = validate_result(root, parent_counts)
        commit(
            root,
            SUBJECT,
            "The exact expected pair carries the prior-cycle MIDR revision,\n"
            "while expected_target_midr records the CPU model used by\n"
            "capability classification. Generic completeness incorrectly\n"
            "required the two representations to be byte-identical.\n\n"
            "Compare them at their shared model granularity. Keep the exact\n"
            "pair and later target-register comparison unchanged, along with\n"
            "every CPU, power, retry, storage, and CPU9 path.",
            42,
        )
        changed = run(
            "git", "diff", "--name-only", f"{parent}..HEAD", cwd=root
        ).splitlines()
        if changed != [str(source_edits.TARGET)]:
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = Path(name) / "generated"
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
            "MISSING_SIGN_OFF,FILE_PATH_CHANGES", str(patch), cwd=Path(name),
        )

        replay = Path(name) / "replay"
        shutil.copytree(root, replay)
        run("git", "reset", "--hard", parent, cwd=replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate_result(replay, parent_counts) != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        series = output / "series"
        series.write_text(f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8")
        provenance = output / "provenance.txt"
        provenance.write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-expected-pair-model-contract-repair",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0461",
            "generated_patch_count=1",
            *markers,
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "boot_candidate=false",
            "",
        ]), encoding="utf-8")
        sums = output / "SHA256SUMS"
        inputs = (target, series, provenance)
        sums.write_text("".join(
            f"{sha256(path)}  {path.name}\n" for path in inputs
        ), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
