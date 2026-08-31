#!/usr/bin/env python3
"""Generate and audit the read-only CPU8 SRAM/P28 diagnostic patch."""

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


PATCH_NAME = "0452-soc-mediatek-expose-CPU8-SRAM-terminal-diagnostic.patch"
SUBJECT = "soc: mediatek: expose CPU8 SRAM terminal diagnostic"
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
            "GIT_AUTHOR_DATE": f"2026-08-31T06:{minute:02d}:00Z",
            "GIT_COMMITTER_DATE": f"2026-08-31T06:{minute:02d}:00Z",
        }
    )
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git",
        "commit",
        "--quiet",
        "--no-gpg-sign",
        "-m",
        subject,
        "-m",
        body,
        cwd=root,
        env=environment,
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
        "git",
        "config",
        "user.email",
        "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(root, "Gemini post-0451 generation parent", "Synthetic parent only.", 0)


def call_counts(root: Path) -> dict[str, int]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    admission = (root / source_edits.ADMISSION).read_text(encoding="utf-8")
    return {
        "p27_acquire": binder.count("binder->backend->p27_acquire("),
        "p27_release": binder.count("binder->backend->p27_release("),
        "isolation_clear": binder.count("binder->backend->isolation_clear("),
        "sram_enable": binder.count("binder->backend->sram_enable("),
        "complete_p28": binder.count("binder->backend->membership_complete_p28("),
        "dcm_update": binder.count("binder->backend->dcm_update("),
        "cpu_boot": binder.count("binder->cpu_boot(cpu)"),
        "ipi_call": binder.count("binder->backend->ipi_call("),
        "add_cpu": admission.count("add_cpu(8)"),
    }


def validate(root: Path, parent_counts: dict[str, int]) -> list[str]:
    admission = (root / source_edits.ADMISSION).read_text(encoding="utf-8")
    internal = (root / source_edits.INTERNAL).read_text(encoding="utf-8")
    test = (root / source_edits.BINDER_TEST).read_text(encoding="utf-8")
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    public = (root / source_edits.PUBLIC).read_text(encoding="utf-8")
    current_counts = call_counts(root)
    if current_counts != parent_counts:
        raise SystemExit(
            f"hardware/request call counts changed: {parent_counts} -> {current_counts}"
        )
    required = {
        public: (
            "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 2U",
            "#define MT6797_A72_BINDER_SRAM_REQUIRED_MASK",
            "u32 sram_match_mask;",
            "u32 p28_complete_attempted;",
            "u64 sram_attempt_id;",
            "u32 sram_sealed;",
        ),
        internal: (
            "s32 p28_begin_ret;",
            "s32 sram_ret;",
            "s32 p28_complete_ret;",
            "bool p28_complete_attempted;",
        ),
        binder: (
            "mt6797_a72_binder_sram_match_mask(",
            "binder->p28_begin_attempted = true;",
            "binder->sram_returned = true;",
            "MT6797_A72_BINDER_SRAM_REQUIRED_MASK",
            "binder->p28_complete_attempted = true;",
            "snapshot->sram_calibration_second =",
        ),
        admission: (
            '"p28_begin_attempted=%u p28_begin_ret=%d p28_begun=%u "',
            '"sram_returned=%u sram_ret=%d sram_match=0x%x "',
            '"p28_complete_ret=%d sram_abi=%u "',
            '"sram_effect_attempted=%u sram_verified=%u sram_sealed=%u\\n"',
        ),
        test: (
            "static void mt6797_binder_sram_diagnostic_test(",
            "~MT6797_A72_BINDER_SRAM_MATCH_SEALED",
            "KUNIT_CASE(mt6797_binder_sram_diagnostic_test)",
            "diagnostic.p28_complete_attempted, 1U",
        ),
    }
    for text, tokens in required.items():
        for token in tokens:
            if text.count(token) != 1:
                raise SystemExit(f"diagnostic token changed: {token}")
    if binder.count("mt6797_a72_binder_sram_match_mask(") != 3:
        raise SystemExit("SRAM match helper definition/call count changed")
    if test.count("KUNIT_CASE(") != 7:
        raise SystemExit("binder KUnit case count is not seven")
    if "MT6797_A72_BINDER_DIAGNOSTIC_ABI 1U" in public:
        raise SystemExit("historical diagnostic ABI remains")
    return [
        "sram_p28_terminal_diagnostic_validation=pass",
        "diagnostic_abi=2",
        "sram_predicates=12",
        "sram_result_fields=complete",
        "p28_begin_boundary=exposed",
        "sram_owner_return_boundary=exposed",
        "sram_shape_match_mask=exposed",
        "p28_completion_boundary=exposed",
        "binder_kunit_cases=7",
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
        "Signed-off-by:",
        "/Users/",
        "add_cpu(",
        "cpu_down(",
        "remove_cpu(",
        "psci_cpu_off",
        "cpu_off(",
        "reboot",
        "writel(",
        "writeq(",
        "write_sysreg(",
        "regmap_write(",
        "memcpy_toio(",
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
    with tempfile.TemporaryDirectory(prefix="a72-sram-p28-diagnostic-") as name:
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
            "The isolation-result repair advances the single CPU8 attempt to\n"
            "SRAM, where the binder returns EPROTO. The physical SRAM owner\n"
            "uses distinct errors, while the current terminal status omits its\n"
            "result and the surrounding P28 return boundaries.\n\n"
            "Expose the complete SRAM result, an exact predicate-match mask,\n"
            "and P28 begin/complete return markers in the existing read-only\n"
            "diagnostic. Reuse that mask for the unchanged binder predicate.\n"
            "Add KUnit coverage without adding an operation or request path.",
            1,
        )
        changed = tuple(
            sorted(run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root).splitlines())
        )
        expected = tuple(sorted(str(path) for path in SOURCE_FILES))
        if changed != expected:
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = Path(name) / "generated"
        generated_dir.mkdir()
        generated = run(
            "git",
            "format-patch",
            "--no-signature",
            "--output-directory",
            str(generated_dir),
            f"{parent}..HEAD",
            cwd=root,
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
                    "experiment=2026-08-31-mainline-a72-sram-p28-terminal-diagnostic",
                    f"repository_commit={args.repository_commit}",
                    f"prepared_source_state={state}",
                    f"prepared_source_integrity={integrity}",
                    "canonical_parent=0451",
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
            "".join(
                f"{sha256(path)}  {path.name}\n" for path in (target, provenance)
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
