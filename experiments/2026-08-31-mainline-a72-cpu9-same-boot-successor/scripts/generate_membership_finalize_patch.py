#!/usr/bin/env python3
"""Generate and audit the CPU9 post-success membership-finalization repair."""

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


PATCH_NAME = "0465-arm64-mediatek-fix-CPU9-success-finalization.patch"
SUBJECT = "arm64: mediatek: fix CPU9 success finalization"
SOURCE = Path("arch/arm64/kernel/mt6797_a72_membership.c")
PARENT_SHA256 = "c7ff10844d624b027e3cf11278c969732ed825c69bed13b05bb7f987444023c1"
FORBIDDEN_ADDITIONS = (
    "add_cpu(", "cpu_up(", "cpu_down(", "cpu_boot(", "psci_cpu_on",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "kernel_restart(", "gemini_cpu9_ledger_", "watchdog",
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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label} anchor changed: count={text.count(old)}")
    return text.replace(old, new)


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
        raise SystemExit("managed parent membership source is absent or unsafe")
    if sha256(source) != PARENT_SHA256:
        raise SystemExit("managed parent membership source changed")
    target = root / SOURCE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run(
        "git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root,
    )
    commit(root, "Gemini post-0464 generation parent",
           "Synthetic exact-source parent only.", 28)


def apply_fix(root: Path) -> None:
    path = root / SOURCE
    text = path.read_text(encoding="utf-8")
    marker = "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)"
    if text.count(marker) != 2:
        raise SystemExit("CPU9 membership block marker changed")
    prefix = text.split(marker, 1)[0]

    text = replace_once(
        text,
        "static bool mt6797_a72_cpu9_retired_parent_valid_locked(void)",
        "static bool\n"
        "mt6797_a72_cpu9_retired_parent_valid_locked(u32 expected_members)",
        "retired-parent signature",
    )
    text = replace_once(
        text,
        "\t\ta72_owner.members == BIT(0) &&\n"
        "\t\ta72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&",
        "\t\ta72_owner.members == expected_members &&\n"
        "\t\ta72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&",
        "retired-parent membership",
    )
    text = replace_once(
        text,
        "\tconst struct mt6797_a72_transaction *active = &a72_owner.active;\n\n"
        "\treturn transaction && active->valid && active->a36_valid &&",
        "\tconst struct mt6797_a72_transaction *active = &a72_owner.active;\n"
        "\tu32 expected_members = BIT(0);\n\n"
        "\tif (active->cpu9_success_published)\n"
        "\t\texpected_members |= BIT(1);\n\n"
        "\treturn transaction && active->valid && active->a36_valid &&",
        "active expected membership",
    )
    text = replace_once(
        text,
        "\t\tmt6797_a72_cpu9_retired_parent_valid_locked() &&",
        "\t\tmt6797_a72_cpu9_retired_parent_valid_locked(expected_members) &&",
        "active retired-parent call",
    )
    text = replace_once(
        text,
        "\t    mt6797_a72_cpu9_retired_parent_valid_locked() &&",
        "\t    mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0)) &&",
        "publish retired-parent call",
    )
    if text.split(marker, 1)[0] != prefix:
        raise SystemExit("source before the CPU9 membership block changed")
    path.write_text(text, encoding="utf-8")


def validate(root: Path) -> tuple[str, ...]:
    text = (root / SOURCE).read_text(encoding="utf-8")
    required = (
        "mt6797_a72_cpu9_retired_parent_valid_locked(u32 expected_members)",
        "a72_owner.members == expected_members",
        "u32 expected_members = BIT(0);",
        "if (active->cpu9_success_published)\n"
        "\t\texpected_members |= BIT(1);",
        "mt6797_a72_cpu9_retired_parent_valid_locked(expected_members)",
        "mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0))",
    )
    for token in required:
        if text.count(token) != 1:
            raise ValueError(f"required repair token changed: {token}")
    if "mt6797_a72_cpu9_retired_parent_valid_locked()" in text:
        raise ValueError("unqualified CPU9 retired-parent validation remains")
    for token in FORBIDDEN_ADDITIONS:
        if token in "\n".join(
            line[1:] for line in text.splitlines() if line.startswith("+")
        ):
            raise ValueError(f"forbidden source addition: {token}")
    return (
        "cpu9_finalize_validation=pass",
        "pre_success_members=bit0",
        "post_success_members=bits0-1",
        "cpu8_source_prefix=unchanged",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
        "production_callers=0",
    )


def validate_mutations(root: Path) -> int:
    mutations = (
        ("a72_owner.members == expected_members",
         "a72_owner.members == BIT(0)"),
        ("if (active->cpu9_success_published)",
         "if (false && active->cpu9_success_published)"),
        ("expected_members |= BIT(1);", "expected_members |= BIT(0);"),
        ("mt6797_a72_cpu9_retired_parent_valid_locked(expected_members)",
         "mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0))"),
        ("mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0))",
         "mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0) | BIT(1))"),
    )
    path = root / SOURCE
    rejected = 0
    for old, new in mutations:
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"mutation anchor changed: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate(root)
        except ValueError:
            rejected += 1
        finally:
            path.write_text(original, encoding="utf-8")
    if rejected != len(mutations):
        raise SystemExit("CPU9 finalization mutation was not rejected")
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
    additions = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for token in FORBIDDEN_ADDITIONS:
        if token in additions:
            raise SystemExit(f"forbidden generated addition: {token}")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-finalize-") as name:
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
            "Preserve the exact CPU8 retired parent while distinguishing the\n"
            "CPU9 active transaction's pre-success member bit 0 from its\n"
            "post-publication member bits 0 and 1. This lets the owner retire\n"
            "a successful CPU9 transaction without adding a caller or effect.",
            29,
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
            f"v7.1.3/{PATCH_NAME}\n", encoding="utf-8"
        )
        (output / "provenance.txt").write_text("\n".join([
            "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "canonical_parent=0464",
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
        entries = (target, output / "series", output / "provenance.txt")
        sums.write_text("".join(
            f"{sha256(path)}  {path.name}\n" for path in entries
        ), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
