#!/usr/bin/env python3
"""Generate and audit the CPU8 SRAM selector-mask contract repair."""

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


PATCH_NAME = "0453-soc-mediatek-mask-CPU8-SRAM-selector-result.patch"
SUBJECT = "soc: mediatek: mask CPU8 SRAM selector result"
SOURCE_FILES = source_edits.SOURCE_FILES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip()


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
            "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
            "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
            "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
            "GIT_AUTHOR_DATE": f"2026-08-31T13:{minute:02d}:00Z",
            "GIT_COMMITTER_DATE": f"2026-08-31T13:{minute:02d}:00Z",
        }
    )
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


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
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid", cwd=root
    )
    commit(root, "Gemini post-0452 generation parent", "Synthetic parent only.", 0)


def call_counts(root: Path) -> dict[str, int]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    return {
        "p27_acquire": binder.count("binder->backend->p27_acquire("),
        "p27_release": binder.count("binder->backend->p27_release("),
        "isolation_clear": binder.count("binder->backend->isolation_clear("),
        "sram_enable": binder.count("binder->backend->sram_enable("),
        "complete_p28": binder.count("binder->backend->membership_complete_p28("),
        "dcm_update": binder.count("binder->backend->dcm_update("),
        "cpu_boot": binder.count("binder->cpu_boot(cpu)"),
        "ipi_call": binder.count("binder->backend->ipi_call("),
    }


def validate(root: Path, parent_counts: dict[str, int]) -> list[str]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    test = (root / source_edits.BINDER_TEST).read_text(encoding="utf-8")
    current_counts = call_counts(root)
    if current_counts != parent_counts:
        raise SystemExit(
            f"hardware/request call counts changed: {parent_counts} -> {current_counts}"
        )
    if binder.count("& MT6797_BIGIDVFS_SRAM_SELECTOR_MASK) ==") != 2:
        raise SystemExit("masked selector predicate count is not two")
    for token in (
        "sram->selector_first == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED",
        "sram->selector_second == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED",
    ):
        if token in binder:
            raise SystemExit(f"unmasked selector predicate remains: {token}")
    required = (
        "#define TEST_SELECTOR_STATUS BIT(22)",
        "#define TEST_SELECTOR_LOW_MISMATCH BIT(0)",
        "static void mt6797_binder_sram_selector_mask_test(",
        "state->selector_status = TEST_SELECTOR_STATUS;",
        "state->selector_xor = TEST_SELECTOR_LOW_MISMATCH;",
        "KUNIT_CASE(mt6797_binder_sram_selector_mask_test)",
    )
    for token in required:
        if test.count(token) != 1:
            raise SystemExit(f"selector-mask test token changed: {token}")
    if test.count("KUNIT_CASE(") != 8:
        raise SystemExit("binder KUnit case count is not eight")
    return [
        "sram_selector_mask_contract_validation=pass",
        "selector_mask=0xfff",
        "selector_expected=0x8fb",
        "upper_status_bit_acceptance=covered",
        "low_selector_bit_rejection=covered",
        "binder_kunit_cases=8",
        "new_cpu_request_paths=0",
        "new_cpu9_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_physical_effect_calls=0",
        "retained_ram_writes=0",
        "storage_writes=0",
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
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for token in (
        "Signed-off-by:", "/Users/", "add_cpu(", "cpu_down(", "remove_cpu(",
        "psci_cpu_off", "cpu_off(", "reboot", "writel(", "writeq(",
        "write_sysreg(", "regmap_write(", "memcpy_toio(",
        "gemini_transition_ledger_checkpoint(",
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
    with tempfile.TemporaryDirectory(prefix="a72-sram-selector-mask-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        parent_counts = call_counts(root)
        source_edits.apply(root)
        markers = validate(root, parent_counts)
        commit(
            root,
            SUBJECT,
            "The CPU8 SRAM owner accepted, verified, and sealed selector\n"
            "reads of 0x4008fb because their low 12 bits equal the expected\n"
            "0x8fb. The binder then rejected both reads by comparing the\n"
            "complete register value to the low-bit expectation.\n\n"
            "Apply the owner's existing selector mask to both binder\n"
            "predicates while retaining the independent full-read stability\n"
            "proof. Cover valid upper status bits and an invalid low bit.\n"
            "No operation or request path changes.",
            1,
        )
        changed = tuple(sorted(
            run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root).splitlines()
        ))
        expected = tuple(sorted(str(path) for path in SOURCE_FILES))
        if changed != expected:
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

        replay = Path(name) / "replay"
        shutil.copytree(root, replay)
        run("git", "reset", "--hard", parent, cwd=replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate(replay, parent_counts) != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        provenance = output / "provenance.txt"
        provenance.write_text(
            "\n".join(
                [
                    "experiment=2026-08-31-mainline-a72-sram-selector-mask-contract-repair",
                    f"repository_commit={args.repository_commit}",
                    f"prepared_source_state={state}",
                    f"prepared_source_integrity={integrity}",
                    "canonical_parent=0452",
                    "generated_patch_count=1",
                    *markers,
                    "deterministic_replay=pass",
                    "native_vm_build=none",
                    "device_action=none",
                    "boot_candidate=false",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        sums = output / "SHA256SUMS"
        sums.write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in (target, provenance)),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
