#!/usr/bin/env python3
"""Generate and audit the READY-token expectation-contract patch."""

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


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PATCH_NAME = "0446-arm64-mediatek-require-empty-READY-observations.patch"
SUBJECT = "arm64: mediatek: require empty dormant READY observations"
SOURCE_FILES = (
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c",
    "arch/arm64/kernel/mt6797_a72_derived_admission_test.c",
    "arch/arm64/kernel/mt6797_a72_direct_state_test.c",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
    "drivers/regulator/da9213-legacy-membership-test.c",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c",
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
        "GIT_AUTHOR_DATE": f"2026-08-31T01:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-31T01:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run("git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment)


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative in SOURCE_FILES:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent file is absent or unsafe: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=root)
    commit(root, "Gemini post-0445 generation parent",
           "Synthetic generation parent only.", 0)


def validate(root: Path) -> list[str]:
    membership = (root / source_edits.MEMBERSHIP).read_text(encoding="utf-8")
    derived = (root / source_edits.DERIVED_TEST).read_text(encoding="utf-8")
    all_tests = "".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in (
            source_edits.MEMBERSHIP_TEST,
            source_edits.DERIVED_TEST,
            source_edits.REGULATOR_TEST,
        )
    )
    required = (
        "Dormant targets have expectations, but no target-local observations.",
        "if (ready->observed_target_mpidr[0] ||",
        "ready->observed_target_mpidr[1])",
        "mt6797_a72_derived_observed_target_rejected_test",
        "state->ready.expected_target_mpidr[target]",
    )
    for token in required:
        if token not in membership + derived:
            raise SystemExit(f"READY contract token absent: {token}")
    for forbidden in (
        "ready->observed_target_mpidr[0] != 0x200",
        "ready->observed_target_mpidr[1] != 0x201",
        "ready->observed_target_mpidr[slot] != expected_mpidr",
    ):
        if forbidden in membership:
            raise SystemExit(f"contradictory READY predicate remains: {forbidden}")
    if all_tests.count(".observed_target_mpidr = { 0, 0 },") != 3:
        raise SystemExit("not all exact READY fixtures use empty observations")
    if all_tests.count(".observed_target_mpidr = { 0x200, 0x201 },"):
        raise SystemExit("legacy pre-execution target observation remains")
    if membership.count("ready->expected_target_mpidr[0] != 0x200") != 1 or \
            membership.count("ready->expected_target_mpidr[1] != 0x201") != 1:
        raise SystemExit("expected target MPIDR contract changed")
    return [
        "ready_contract_validation=pass",
        "production_observation_contract=empty-before-target-execution",
        "expected_target_mpidrs=0x200,0x201",
        "focused_ready_cases=2",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
        "hardware_writes=0",
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
    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for token in (
        "Signed-off-by:", "/Users/", "cpu_down(", "remove_cpu(",
        "psci_cpu_off", "cpu_off(", "reboot", "retry", "writel(",
        "writeq(", "write_sysreg(", "regmap_write(", "memcpy_toio(",
    ):
        if token.lower() in added.lower():
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
    with tempfile.TemporaryDirectory(prefix="a72-ready-token-contract-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        source_edits.apply(root)
        markers = validate(root)
        commit(
            root, SUBJECT,
            "Production READY carries expectation-only evidence for dormant\n"
            "CPU8 and CPU9, so their target-local observed MPIDRs remain\n"
            "empty until those CPUs execute. The membership validator\n"
            "instead required those observations before its first request.\n\n"
            "Require the observations to remain empty while preserving the\n"
            "exact expected MPIDRs, target mask, ordering, identities, and\n"
            "one-shot request boundary. Update the exact fixtures and reject\n"
            "either premature target observation.", 1,
        )
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

        replay = Path(name) / "replay"
        shutil.copytree(root, replay)
        run("git", "reset", "--hard", parent, cwd=replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        markers += validate(replay)

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        provenance = output / "provenance.txt"
        provenance.write_text(
            "\n".join([
                "experiment=2026-08-30-mainline-a72-ready-token-contract-repair",
                f"repository_commit={args.repository_commit}",
                f"prepared_source_state={state}",
                f"prepared_source_integrity={integrity}",
                "canonical_parent=0445",
                "generated_patch_count=1",
                *markers[:9],
                "deterministic_replay=pass",
                "native_vm_build=none",
                "device_action=none",
                "boot_candidate=false",
                "",
            ]), encoding="utf-8",
        )
        sums = output / "SHA256SUMS"
        sums.write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in (target, provenance)),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
