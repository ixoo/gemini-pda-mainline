#!/usr/bin/env python3
"""Generate and audit the read-only CPU8 P27 attribution patch."""

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
PATCH_NAME = "0449-soc-mediatek-expose-CPU8-P27-terminal-diagnostic.patch"
SUBJECT = "soc: mediatek: expose CPU8 P27 terminal diagnostic"
SOURCE_FILES = (
    source_edits.BINDER_HEADER,
    source_edits.BINDER_INTERNAL,
    source_edits.BINDER,
    source_edits.BINDER_TEST,
    source_edits.CONTROLLER,
)


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
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-08-31T03:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-31T03:{minute:02d}:00Z",
    })
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
    commit(root, "Gemini post-0448 generation parent", "Synthetic parent only.", 0)


def counts(root: Path) -> dict[str, int]:
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    controller = (root / source_edits.CONTROLLER).read_text(encoding="utf-8")
    combined = binder + controller
    return {
        "add_cpu": combined.count("return add_cpu(cpu);"),
        "p27_acquire": binder.count("binder->backend->p27_acquire("),
        "p27_release": binder.count("binder->backend->p27_release("),
        "cpu_off": combined.count("cpu_down(") + combined.count("remove_cpu("),
        "retry": combined.count("retry"),
    }


def validate(root: Path, parent_counts: dict[str, int]) -> list[str]:
    header = (root / source_edits.BINDER_HEADER).read_text(encoding="utf-8")
    internal = (root / source_edits.BINDER_INTERNAL).read_text(encoding="utf-8")
    binder = (root / source_edits.BINDER).read_text(encoding="utf-8")
    controller = (root / source_edits.CONTROLLER).read_text(encoding="utf-8")
    test = (root / source_edits.BINDER_TEST).read_text(encoding="utf-8")
    current_counts = counts(root)
    if current_counts != parent_counts:
        raise SystemExit(
            f"hardware or request call counts changed: {parent_counts} -> {current_counts}"
        )
    for token in (
        "MT6797_A72_BINDER_DIAGNOSTIC_ABI",
        "struct mt6797_a72_binder_diagnostic",
        "stage_errno",
        "rollback_errno",
        "p27_acquire_attempted",
        "p27_release_completed",
    ):
        if token not in header:
            raise SystemExit(f"public diagnostic token absent: {token}")
    if internal.count("struct mt6797_a72_platform_effect_result p27_release;") != 1:
        raise SystemExit("binder does not retain one P27 release result")
    if binder.count("mt6797_a72_binder_fill_diagnostic(") != 3:
        raise SystemExit("diagnostic fill helper call/definition count changed")
    if binder.count("mt6797_a72_binder_diagnostic_snapshot(") != 1:
        raise SystemExit("public diagnostic snapshot count changed")
    if binder.count("&binder->p27_release") != 4:
        raise SystemExit("P27 release result is not retained and validated exactly")
    for token in (
        "binder_snapshot_ret=%d",
        "stage_errno=%d",
        "rollback_errno=%d",
        "p27a_error=%d",
        "p27r_error=%d",
        "p27r_completed=0x%x",
    ):
        if controller.count(token) != 1:
            raise SystemExit(f"live status diagnostic token changed: {token}")
    if controller.count("mt6797_a72_binder_diagnostic_snapshot(&diagnostic)") != 1:
        raise SystemExit("live status has an unexpected diagnostic call count")
    if test.count("KUNIT_CASE(mt6797_binder_p27_diagnostic_test)") != 1:
        raise SystemExit("focused P27 diagnostic KUnit case is absent")
    for token in (
        "diagnostic.stage_errno, -EPROTO",
        "diagnostic.rollback_errno, -EPROTO",
        "diagnostic.p27_acquire_sealed, 0U",
        "diagnostic.p27_release_sealed, 1U",
    ):
        if token not in test:
            raise SystemExit(f"focused P27 assertion absent: {token}")
    return [
        "p27_runtime_attribution_validation=pass",
        "diagnostic_abi=1",
        "focused_binder_cases_added=1",
        "status_snapshot_calls=1",
        "p27_release_result_retained=true",
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
    with tempfile.TemporaryDirectory(prefix="a72-p27-runtime-attribution-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        parent_counts = counts(root)
        source_edits.apply(root)
        markers = validate(root, parent_counts)
        commit(
            root,
            SUBJECT,
            "The first request-bearing CPU8 attempt reached the binder P27\n"
            "stage and retained a pre-isolation rollback fault, but the\n"
            "ledger does not separate the initiating error from rollback.\n\n"
            "Retain the existing P27 release result in binder-owned memory\n"
            "and expose a serialized read-only snapshot of the transition\n"
            "and P27 acquire/release results through the candidate status.\n"
            "This adds no request, hardware operation, retry, retained-RAM\n"
            "write, storage access, or sequencing change.",
            1,
        )
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
        replay_markers = validate(replay, parent_counts)
        if replay_markers != markers:
            raise SystemExit("replay validation markers changed")

        output.mkdir(parents=True)
        target = output / PATCH_NAME
        shutil.copyfile(patch, target)
        provenance = output / "provenance.txt"
        provenance.write_text(
            "\n".join([
                "experiment=2026-08-30-mainline-a72-p27-runtime-attribution",
                f"repository_commit={args.repository_commit}",
                f"prepared_source_state={state}",
                f"prepared_source_integrity={integrity}",
                "canonical_parent=0448",
                "generated_patch_count=1",
                *markers,
                "deterministic_replay=pass",
                "native_vm_build=none",
                "device_action=none",
                "boot_candidate=false",
                "",
            ]),
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
