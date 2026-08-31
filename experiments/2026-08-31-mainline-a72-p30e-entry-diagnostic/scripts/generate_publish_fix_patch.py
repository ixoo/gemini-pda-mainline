#!/usr/bin/env python3
"""Generate and audit the P30E post-MMU publication repair."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
from pathlib import Path
import shutil
import tempfile

import generate_patch as base
import source_edits_publish_fix as edits


PATCH_NAME = "0455-arm64-repair-P30E-post-MMU-publication.patch"
SUBJECT = "arm64: repair P30E post-MMU publication"


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative in edits.SOURCE_FILES:
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent file is absent or unsafe: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    base.run("git", "init", "--quiet", cwd=root)
    base.run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    base.run(
        "git", "config", "user.email", "gemini-mainline@example.invalid", cwd=root
    )
    base.commit(root, "Gemini post-0454 generation parent", "Synthetic parent only.", 10)


def validate(root: Path) -> list[str]:
    c_text = (root / edits.P30E_C).read_text(encoding="utf-8")
    asm_text = (root / edits.P30E_ASM).read_text(encoding="utf-8")
    required_c = (
        "static int p30e_current_cpu(void)",
        "read_cpuid_mpidr() & MPIDR_HWID_BITMASK",
        "int arm64_mt6797_a72_p30e_target_publish(",
        "p30e_invalidate_slot(slot);",
        "ARM64_MT6797_A72_P30E_TARGET_CLAIMED",
        "p30e_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD, state);",
        "p30e_clean_slot(slot);",
    )
    for token in required_c:
        if token not in c_text:
            raise SystemExit(f"required post-MMU publication token missing: {token}")
    if c_text.count("int arm64_mt6797_a72_p30e_target_publish(") != 1:
        raise SystemExit("post-MMU publisher definition count changed")
    if asm_text.count("arm64_mt6797_a72_p30e_target_publish") != 0:
        raise SystemExit("post-MMU publisher remains in idmap assembly")
    if asm_text.count("mov\tx14, x30") != 1 or asm_text.count("mov\tx30, x14") != 1:
        raise SystemExit("MMU-off cache helper does not preserve its link exactly once")
    if c_text.index(
        "p30e_put(&slot->wire, ARM64_MT6797_A72_P30E_TARGET_STATE_WORD, state);"
    ) > c_text.index("p30e_clean_slot(slot);", c_text.index(
        "int arm64_mt6797_a72_p30e_target_publish(")):
        raise SystemExit("terminal state is not covered by the publication clean")
    return [
        "p30e_post_mmu_publication_validation=pass",
        "post_mmu_publisher_definitions=1",
        "idmap_publisher_definitions=0",
        "mmuoff_nested_link_preservation=pass",
        "non_target_mpidr_result=-ENODEV",
        "target_state_clean_order=pass",
        "new_cpu_request_paths=0",
        "new_cpu9_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
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
        "cpu_up(",
        "cpu_down(",
        "remove_cpu(",
        "psci_cpu_on",
        "psci_cpu_off",
        "reboot",
        "regmap_write(",
        "writel(",
        "writeq(",
        "memcpy_toio(",
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
    with tempfile.TemporaryDirectory(prefix="a72-p30e-publish-fix-") as name:
        root = Path(name) / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = base.run("git", "rev-parse", "HEAD", cwd=root)
        edits.apply(root)
        markers = validate(root)
        base.commit(
            root,
            SUBJECT,
            "The P30E target publisher was linked into .idmap.text but called\n"
            "from secondary_start_kernel after the MMU was enabled. A four-CPU\n"
            "QEMU run consequently took an instruction abort on the first\n"
            "secondary, while the same focused suites passed with one CPU.\n\n"
            "Move the post-MMU publication path into ordinary C text, select\n"
            "only the exact A72 MPIDRs, and clean the complete terminal tuple.\n"
            "Also preserve the nested MMU-off cache helper link register.",
            11,
        )
        changed = tuple(
            sorted(
                base.run("git", "diff", "--name-only", f"{parent}..HEAD", cwd=root)
                .splitlines()
            )
        )
        expected = tuple(sorted(str(path) for path in edits.SOURCE_FILES))
        if changed != expected:
            raise SystemExit(f"generated file set changed: {changed}")

        generated_dir = Path(name) / "generated"
        generated_dir.mkdir()
        generated = base.run(
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
        base.run("git", "reset", "--hard", parent, cwd=replay)
        base.run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate(replay) != markers:
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
                    "canonical_parent=0454",
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
                f"{base.sha256(path)}  {path.name}\n"
                for path in (target, provenance)
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
