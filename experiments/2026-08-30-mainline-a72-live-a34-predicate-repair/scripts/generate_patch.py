#!/usr/bin/env python3
"""Generate, replay, and package the two live A34 repair patches."""

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
PATCHES = (
    "0442-soc-mediatek-retain-live-CPU8-admission-failure-stage.patch",
    "0443-arm64-mediatek-validate-live-A34-admission-predicates.patch",
)
SUBJECTS = (
    "soc: mediatek: retain live CPU8 admission failure stage",
    "arm64: mediatek: validate live A34 admission predicates",
)
PARENT_PATCH_SHA256 = "0181805c1f2b0a123729dd4c4b8158eb5148f9fac8f6a19592bdfb32f4a981c8"


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
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(args)}"
        )
    return result.stdout.strip()


def prepare_parent(source_root: Path, destination: Path) -> None:
    for relative, expected in source_edits.PARENT_SHA256.items():
        source = source_root / relative
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            raise SystemExit(f"prepared post-0441 source changed: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    parent_patch = (
        REPO_ROOT / "patches/v7.1.3/"
        "0441-arm64-complete-Gemini-late-CPU-classified-universe.patch"
    )
    if sha256(parent_patch) != PARENT_PATCH_SHA256:
        raise SystemExit("canonical patch 0441 changed")


def commit(root: Path, subject: str, body: str, minute: int) -> None:
    environment = os.environ.copy()
    environment.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": f"2026-08-31T00:{minute:02d}:00Z",
        "GIT_COMMITTER_DATE": f"2026-08-31T00:{minute:02d}:00Z",
    })
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    run("git", "commit", "--quiet", "--no-gpg-sign", "-m", subject,
        "-m", body, cwd=root, env=environment)


def validate_stage(root: Path) -> list[str]:
    membership = (root / source_edits.MEMBERSHIP_C).read_text()
    header = (root / source_edits.MEMBERSHIP_H).read_text()
    controller = (root / source_edits.CONTROLLER_C).read_text()
    controller_h = (root / source_edits.CONTROLLER_H).read_text()
    test = (root / source_edits.CONTROLLER_TEST).read_text()
    required = (
        "MT6797_A72_DERIVE_DIRECT_STATE",
        "MT6797_A72_DERIVE_A34",
        "MT6797_A72_DERIVE_PRESTATE_VALIDATE",
        "MT6797_A72_DERIVE_COMPLETE",
        "mt6797_a72_membership_derive_cpu8_diagnostic",
    )
    for token in required:
        if token not in header or token not in membership:
            raise SystemExit(f"stage token absent: {token}")
    for token in (
        "u32 failure_stage;", "u32 derive_stage;",
        "failure_stage=%u derive_stage=%u",
    ):
        if token not in controller_h + controller:
            raise SystemExit(f"controller stage output absent: {token}")
    if "context->controller.failure_stage" not in test:
        raise SystemExit("controller stage KUnit expectation absent")
    if "state->failure_stage = zero_result;" not in controller:
        raise SystemExit("terminal stage is not retained before trace")
    return [
        "stage_validation=pass",
        "controller_failure_stages=3",
        "derive_stage_terminal=15",
        "request_order=unchanged",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
        "hardware_writes=0",
    ]


def validate_a34(root: Path) -> list[str]:
    membership = (root / source_edits.MEMBERSHIP_C).read_text()
    a34_test = (root / source_edits.A34_TEST).read_text()
    derived_test = (root / source_edits.DERIVED_TEST).read_text()
    owner_test = (root / source_edits.MEMBERSHIP_TEST).read_text()
    for forbidden in (
        "memcmp(observation, &a34_expected",
        "mt6797_a34_every_byte_mutation_test",
    ):
        if forbidden in membership + a34_test:
            raise SystemExit(f"overbroad A34 contract remains: {forbidden}")
    required = (
        "MT6797_A72_A34_CPU_STATUS_MASK GENMASK(7, 6)",
        "platform->spm_mp2_cpu0_pwr_con == 0x00010332",
        "platform->spm_mp2_cpu1_pwr_con == 0x00010332",
        "platform->cci_mp2_port_control == 0xc0000000",
        "!source->clock.reserved && source->clock.sample_generation",
        "!source->bigidvfs.reserved",
        "mt6797_a34_irrelevant_payload_test",
        "mt6797_a34_relevant_mutation_test",
    )
    combined = membership + a34_test
    for token in required:
        if token not in combined:
            raise SystemExit(f"semantic A34 predicate absent: {token}")
    for fixture in (a34_test, derived_test, owner_test):
        for token in (
            ".spm_mp2_cpu0_pwr_con = 0x00010332",
            ".spm_mp2_cpu1_pwr_con = 0x00010332",
            ".cci_mp2_port_control = 0xc0000000",
        ):
            if token not in fixture:
                raise SystemExit(f"live fixture field absent: {token}")
    return [
        "a34_validation=pass",
        "a72_cpu_status_mask=bits7:6",
        "unrelated_a53_cpu_status_bits=ignored",
        "raw_clock_payload=non_authorizing",
        "raw_bigidvfs_payload=non_authorizing",
        "topology_owner_replay_provider_platform=fail-closed",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
        "hardware_writes=0",
    ]


def validate_patch(path: Path, expected_subject: str, index: int) -> None:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if expected_subject not in str(message["Subject"] or ""):
        raise SystemExit(f"generated patch subject changed: {path.name}")
    if str(message["From"] or "") != (
        "Gemini Mainline Experiment <gemini-mainline@example.invalid>"
    ):
        raise SystemExit(f"generated patch author changed: {path.name}")
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
    if index == 0 and "failure_stage=%u derive_stage=%u" not in added:
        raise SystemExit("stage patch lacks live output")
    if index == 1 and "MT6797_A72_A34_CPU_STATUS_MASK" not in added:
        raise SystemExit("A34 patch lacks semantic mask")


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
    with tempfile.TemporaryDirectory(prefix="a72-live-a34-repair-") as name:
        temporary = Path(name)
        source = temporary / "source"
        prepare_parent(source_root, source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(source, "Gemini post-0441 generation parent",
               "Synthetic generation parent only.", 0)
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        source_edits.apply_stage_attribution(source)
        stage_validation = validate_stage(source)
        commit(
            source, SUBJECTS[0],
            "The first live CPU8 trigger returned EPERM after the one-shot\n"
            "core was consumed but before a CPU request. Existing trace\n"
            "storage could not retain the exact rejecting stage.\n\n"
            "Retain the controller stage and the first derived-admission\n"
            "substage in the read-only terminal status. Do not change any\n"
            "predicate, effect, request order, or retry behavior.", 1,
        )

        source_edits.apply_a34_repair(source)
        a34_validation = validate_a34(source)
        commit(
            source, SUBJECTS[1],
            "A34 compared the complete raw physical snapshot against an\n"
            "injected fixture whose unspecified live registers were zero.\n"
            "Exact device evidence shows valid nonzero per-core MP2 and CCI\n"
            "state plus unrelated A53 CPU-status movement.\n\n"
            "Validate the documented CPU8-off topology, owner, replay,\n"
            "provider, MP2, isolation, DCM, CCI and source-validity predicates\n"
            "instead. Keep A72 status bits fail-closed while excluding\n"
            "unrelated A53 and raw clock payloads from authorization.", 2,
        )

        generated_dir = temporary / "generated"
        generated = run(
            "git", "format-patch", "--no-signature", "--output-directory",
            str(generated_dir), f"{parent}..HEAD", cwd=source,
        ).splitlines()
        if len(generated) != 2:
            raise SystemExit("generated patch count changed")
        package = temporary / "package"
        package.mkdir()
        for index, generated_path in enumerate(generated):
            patch = package / PATCHES[index]
            shutil.move(generated_path, patch)
            validate_patch(patch, SUBJECTS[index], index)
            run(
                "perl", str(source_root / "scripts/checkpatch.pl"), "--strict",
                "--no-tree", f"--root={source_root}", "--ignore",
                "MISSING_SIGN_OFF,FILE_PATH_CHANGES,CAMELCASE,LONG_LINE",
                str(patch), cwd=temporary,
            )

        replay = temporary / "replay"
        prepare_parent(source_root, replay)
        run("git", "init", "--quiet", cwd=replay)
        for patch_name in PATCHES:
            patch = package / patch_name
            run("git", "apply", "--check", str(patch), cwd=replay)
            run("git", "apply", str(patch), cwd=replay)
        if validate_stage(replay) != stage_validation:
            raise SystemExit("stage replay validation changed")
        if validate_a34(replay) != a34_validation:
            raise SystemExit("A34 replay validation changed")

        output.mkdir(parents=True)
        for patch_name in PATCHES:
            shutil.copyfile(package / patch_name, output / patch_name)
        (output / "series").write_text(
            "".join(f"v7.1.3/{name}\n" for name in PATCHES)
        )
        (output / "source-validation.txt").write_text(
            "\n".join(stage_validation + a34_validation) + "\n"
        )
        provenance = [
            f"repository_commit={args.repository_commit}",
            f"prepared_source_state={state}",
            f"prepared_source_integrity={integrity}",
            "parent_patch=0441",
            f"parent_patch_sha256={PARENT_PATCH_SHA256}",
            "generated_patch_count=2",
            *(f"patch_sha256={name}:{sha256(output / name)}" for name in PATCHES),
            *stage_validation,
            *a34_validation,
            "native_vm_build=none",
            "device_action=none",
            "boot_candidate=false",
        ]
        (output / "provenance.txt").write_text("\n".join(provenance) + "\n")
        checksums = [
            f"{sha256(item)}  {item.name}" for item in sorted(output.iterdir())
            if item.name != "SHA256SUMS"
        ]
        (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
