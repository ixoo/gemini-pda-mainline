#!/usr/bin/env python3
"""Generate and audit the same-boot retained-cluster CPU9 controller patch."""

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

import controller_source_edits
import validate_controller_source


PATCH_NAME = "0469-soc-mediatek-chain-CPU9-after-exact-CPU8-proof.patch"
SUBJECT = "soc: mediatek: chain CPU9 after exact CPU8 proof"
CHANGED_PATHS = tuple(sorted((
    *controller_source_edits.PARENT_HASHES,
    *controller_source_edits.NEW_PATHS,
)))
FORBIDDEN_PATCH_TOKENS = (
    "Signed-off-by:", "/Users/", "cpu_down(", "remove_cpu(",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "kernel_restart(",
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
        "GIT_AUTHOR_DATE": f"2026-09-01T02:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-09-01T02:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run(
        "git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment,
    )


def prepare_parent(source_root: Path, root: Path) -> None:
    for relative, expected in controller_source_edits.PARENT_HASHES.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"managed parent source is absent: {relative}")
        if sha256(source) != expected:
            raise SystemExit(f"managed parent source changed: {relative}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in controller_source_edits.NEW_PATHS:
        if (source_root / relative).exists():
            raise SystemExit(f"CPU9 controller already exists in parent: {relative}")
    run("git", "init", "--quiet", cwd=root)
    run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=root)
    run("git", "config", "user.email", "gemini-mainline@example.invalid",
        cwd=root)
    commit(root, "Gemini post-0468 generation parent",
           "Synthetic exact-source parent only.", 8)


def validate_mutations(root: Path) -> int:
    mutations = (
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "proof->lifecycle_terminal && proof->terminal_exact &&",
            "proof->lifecycle_terminal && true &&",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "proof->cpu8_online &&\n\t       !proof->cpu9_online;",
            "proof->cpu8_online &&\n\t       proof->cpu9_online;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\tif (state->cpu8_ret)\n",
            "\tif (false)\n",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\tret = ops->publish_cpu9(context, &state->cpu9_transaction);",
            "\tret = 0;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\tret = ops->prepare_cpu9(context, &state->cpu9_request);",
            "\tret = 0;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)",
            "ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU8)",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\tstate->cpu9_requests = 1;",
            "\tstate->cpu9_requests = 2;",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-admission-controller.c",
            "diagnostic.retained_mask != MT6797_A72_CPU9_RETAINED_REQUIRED",
            "diagnostic.retained_mask == MT6797_A72_CPU9_RETAINED_REQUIRED",
        ),
        (
            "drivers/soc/mediatek/Kconfig",
            "\tdepends on MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER\n"
            "\tdepends on MTK_MT6797_A72_CPU9_BINDER",
            "\tdepends on MTK_MT6797_A72_ADMISSION_CONTROLLER\n"
            "\tdepends on MTK_MT6797_A72_CPU9_BINDER",
        ),
        (
            "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
            "\tif (ret)\n\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
            "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,\n"
            "\t\t\tret);",
            "\tif (ret) {\n\t\tcpu_down(MT6797_A72_CPU9_EXECUTOR_CPU9);\n"
            "\t\treturn mt6797_a72_cpu9_admission_terminal(\n"
            "\t\t\tstate, MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,\n"
            "\t\t\tret);\n\t}",
        ),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"mutation anchor changed: {relative}: {old}")
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            validate_controller_source.validate(root)
        except ValueError:
            rejected += 1
        else:
            raise SystemExit(
                f"CPU9 controller mutation escaped: {relative}: {old}"
            )
        finally:
            path.write_text(original, encoding="utf-8")
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
    if text.count("\ndiff --git ") != len(CHANGED_PATHS):
        raise SystemExit("generated patch file count changed")
    for relative in CHANGED_PATHS:
        if f" a/{relative}" not in text:
            raise SystemExit(f"generated patch path missing: {relative}")
    for token in FORBIDDEN_PATCH_TOKENS:
        if token in text:
            raise SystemExit(f"forbidden generated token: {token}")


def checkpatch_fix(source_root: Path, patch: Path, cwd: Path) -> None:
    result = subprocess.run(
        (
            "perl", str(source_root / "scripts/checkpatch.pl"),
            "--fix-inplace", "--strict", "--no-tree",
            f"--root={source_root}", "--ignore", CHECKPATCH_IGNORE,
            str(patch),
        ),
        cwd=cwd, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if not patch.is_file() or not patch.stat().st_size:
        if result.stdout:
            print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit("checkpatch fix did not preserve the generated patch")


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
    with tempfile.TemporaryDirectory(prefix="gemini-cpu9-controller-") as name:
        temp = Path(name)
        root = temp / "source"
        root.mkdir()
        prepare_parent(source_root, root)
        parent = run("git", "rev-parse", "HEAD", cwd=root)
        controller_source_edits.apply(root)
        markers = validate_controller_source.validate(root)
        mutations = validate_mutations(root)
        commit(
            root, SUBJECT,
            "Extend the one-shot live admission path with a separate CPU9\n"
            "controller. It runs the unchanged CPU8 controller first, requires\n"
            "its exact terminal proof, derives and publishes one CPU9\n"
            "transaction, stages the CPU9 binder, and issues add_cpu(9) once.\n\n"
            "Expose combined controller and binder diagnostics while retaining\n"
            "CPU8/provider/cluster state on every CPU9 failure. Add no CPU_OFF,\n"
            "retry, watchdog refresh, or repeated cluster effect.",
            9,
        )
        changed = run("git", "diff", "--name-only", f"{parent}..HEAD",
                      cwd=root).splitlines()
        if changed != list(CHANGED_PATHS):
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
        checkpatch_fix(source_root, patch, temp)
        validate_patch(patch)
        run(
            "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
            "--no-tree", f"--root={source_root}", "--ignore",
            CHECKPATCH_IGNORE, str(patch), cwd=temp,
        )

        replay = temp / "replay"
        replay.mkdir()
        prepare_parent(source_root, replay)
        run("git", "am", "--quiet", str(patch), cwd=replay)
        if validate_controller_source.validate(replay) != markers:
            raise SystemExit("replay validation markers changed")

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
            "canonical_parent=0468",
            "generated_patch_count=1",
            *markers,
            f"source_mutations_rejected={mutations}",
            "strict_checkpatch=pass",
            "checkpatch_ignored=missing-signoff-file-path-open-ended-line",
            "deterministic_replay=pass",
            "native_vm_build=none",
            "device_action=none",
            "physical_cpu_request=none",
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
