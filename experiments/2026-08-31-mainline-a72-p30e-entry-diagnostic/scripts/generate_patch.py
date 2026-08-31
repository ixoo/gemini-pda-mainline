#!/usr/bin/env python3
"""Generate and audit the CPU8 P30E entry-diagnostic integration."""

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


PATCH_NAME = "0454-soc-mediatek-wire-CPU8-P30E-entry-diagnostic.patch"
SUBJECT = "soc: mediatek: wire CPU8 P30E entry diagnostic"
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
            "GIT_AUTHOR_DATE": f"2026-08-31T15:{minute:02d}:00Z",
            "GIT_COMMITTER_DATE": f"2026-08-31T15:{minute:02d}:00Z",
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
        "git", "config", "user.email", "gemini-mainline@example.invalid", cwd=root
    )
    commit(root, "Gemini post-0453 generation parent", "Synthetic parent only.", 0)


def operation_counts(root: Path) -> dict[str, int]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    return {
        "cpu_boot": binder.count("binder->cpu_boot(cpu)"),
        "p27_acquire": binder.count("binder->backend->p27_acquire("),
        "p27_release": binder.count("binder->backend->p27_release("),
        "provider_acquire": binder.count("membership_provider_acquire("),
        "provider_abort": binder.count("membership_provider_abort("),
        "isolation_clear": binder.count("binder->backend->isolation_clear("),
        "sram_enable": binder.count("binder->backend->sram_enable("),
        "dcm_update": binder.count("binder->backend->dcm_update("),
        "ipi_call": binder.count("binder->backend->ipi_call("),
        "p30e_prepare": binder.count("mt6797_a72_membership_prepare_p30e_handoff("),
        "p30e_arm": binder.count("arm64_mt6797_a72_p30e_arm("),
        "p30e_readback": binder.count("arm64_mt6797_a72_p30e_readback("),
    }


def validate(root: Path, parent_counts: dict[str, int]) -> list[str]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    membership = (root / source_edits.MEMBERSHIP).read_text(encoding="utf-8")
    public = (root / source_edits.BINDER_PUBLIC).read_text(encoding="utf-8")
    admission = (root / source_edits.ADMISSION).read_text(encoding="utf-8")
    test = (root / source_edits.BINDER_TEST).read_text(encoding="utf-8")
    counts = operation_counts(root)
    unchanged = (
        "cpu_boot",
        "p27_acquire",
        "p27_release",
        "provider_acquire",
        "provider_abort",
        "isolation_clear",
        "sram_enable",
        "dcm_update",
        "ipi_call",
    )
    for name in unchanged:
        if counts[name] != parent_counts[name]:
            raise SystemExit(
                f"physical/request call count changed for {name}: "
                f"{parent_counts[name]} -> {counts[name]}"
            )
    for name in ("p30e_prepare", "p30e_arm", "p30e_readback"):
        if counts[name] != parent_counts[name] + 1:
            raise SystemExit(
                f"expected one new {name} call: {parent_counts[name]} -> {counts[name]}"
            )
    required = {
        binder: (
            "mt6797_a72_binder_p30e_readback_once",
            "binder->p30e_prepare_attempted = true;",
            "binder->p30e_arm_attempted = true;",
            "if (cpu != MT6797_A72_TRANSITION_CPU8 ||",
            "handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP",
        ),
        membership: (
            "bool cpu8_on_ready;",
            "a72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE",
            "identity->operation ==\n\t\tARM64_LATE_CPU_STARTUP_OP_CPU8_UP",
        ),
        public: (
            "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 3U",
            "u32 p30e_target_state;",
            "u32 p30e_controller_sequence;",
        ),
        admission: (
            "p30e_prepare_attempted=%u",
            "p30e_target_state=%u",
            "p30e_controller_sequence=%u",
        ),
        test: (
            "static void mt6797_binder_p30e_readback_test(",
            "ARM64_MT6797_A72_P30E_EMPTY",
            "ARM64_MT6797_A72_P30E_TARGET_CLAIMED",
            "ARM64_MT6797_A72_P30E_TARGET_PUBLISHED",
        ),
    }
    for text, tokens in required.items():
        for token in tokens:
            if token not in text:
                raise SystemExit(f"required P30E integration token missing: {token}")
    if test.count("KUNIT_CASE(") != 9:
        raise SystemExit("binder KUnit case count is not nine")
    if binder.count("mt6797_a72_binder_p30e_readback_once(binder, cpu);") != 2:
        raise SystemExit("P30E readback-on-error/rollback call inventory changed")
    return [
        "p30e_cpu8_entry_diagnostic_validation=pass",
        "p30e_prepare_calls_added=1",
        "p30e_arm_calls_added=1",
        "p30e_readback_calls_added=1",
        "p30e_states_covered=armed,claimed,published",
        "binder_kunit_cases=9",
        "new_cpu_request_paths=0",
        "new_cpu9_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_power_sequence_calls=0",
        "retained_ram_arm_writes=1",
        "controller_readback_maximum=1",
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
        "regmap_write(",
        "writel(",
        "writeq(",
        "memcpy_toio(",
        "ARM64_MT6797_A72_P30E_OPERATION_CPU9_UP",
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
    with tempfile.TemporaryDirectory(prefix="a72-p30e-entry-diagnostic-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        parent_counts = operation_counts(root)
        source_edits.apply(root)
        markers = validate(root, parent_counts)
        commit(
            root,
            SUBJECT,
            "The exact CPU8 power transaction now reaches a zero-returning\n"
            "CPU_ON callback but times out waiting for generic arm64 secondary\n"
            "completion. The existing P30E wire can distinguish whether the\n"
            "target reached secondary_entry, but no controller arms it.\n\n"
            "Prepare and arm the existing CPU8-only P30E object immediately\n"
            "before CPU_ON, then take one controller readback on an error or\n"
            "rollback. Expose EMPTY, CLAIMED, and PUBLISHED states through the\n"
            "existing read-only admission status. Keep CPU9, CPU_OFF, retries,\n"
            "and all power-sequence calls unchanged.",
            1,
        )
        changed = tuple(
            sorted(
                run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root)
                .splitlines()
            )
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
                    "experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic",
                    f"repository_commit={args.repository_commit}",
                    f"prepared_source_state={state}",
                    f"prepared_source_integrity={integrity}",
                    "canonical_parent=0453",
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
