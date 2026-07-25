#!/usr/bin/env python3
"""Storage-inert Candidate AI finalization and reproduction smoke tests."""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(
    command: list[str],
    *,
    expect_success: bool,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_environment:
        environment.update(extra_environment)
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if expect_success and result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "command failed")
    if not expect_success and result.returncode == 0:
        raise ValueError("mutation unexpectedly passed")
    return result


def populate_stage(root: pathlib.Path, finalizer: object) -> None:
    root.mkdir()
    for member in sorted(finalizer.PRE_MANIFEST_MEMBERS):
        path = root / member
        path.write_bytes(f"synthetic Candidate AI member: {member}\n".encode())
        path.chmod(0o700 if member in finalizer.EXECUTABLE_MEMBERS else 0o640)


def write_package_manifest(root: pathlib.Path, package_validator: object) -> None:
    members = package_validator.inventory(root)
    lines = [
        f"{package_validator.digest_bytes(members[name].read_bytes())}  ./{name}\n"
        for name in sorted(set(members) - {"SHA256SUMS"})
    ]
    (root / "SHA256SUMS").write_text("".join(lines), encoding="ascii")
    (root / "SHA256SUMS").chmod(0o644)


def populate_package(
    root: pathlib.Path, generated: str, package_validator: object
) -> None:
    (root / "provenance").mkdir(parents=True)
    root.chmod(package_validator.PACKAGE_DIRECTORY_MODE)
    (root / "provenance").chmod(package_validator.PACKAGE_DIRECTORY_MODE)
    (root / "payload.bin").write_bytes(b"substantive payload\n")
    (root / "Image.gz").write_bytes(b"synthetic Image.gz\n")
    (root / "System.map").write_bytes(b"synthetic System.map\n")
    (root / "kernel.config").write_bytes(b"synthetic kernel.config\n")
    (root / "provenance/build.json").write_text(
        json.dumps(
            {"schema": 1, "generated_utc": generated, "identity": "same"},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(0o644)
    write_package_manifest(root, package_validator)


def expect_function_rejected(function: object, *args: object) -> None:
    try:
        function(*args)  # type: ignore[operator]
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return
    raise ValueError("mutation unexpectedly passed")


def minimal_fdt() -> bytes:
    reserve_offset = 40
    struct_offset = 56
    structure = struct.pack(">I4sII", 1, b"\0\0\0\0", 2, 9)
    total = struct_offset + len(structure)
    header = struct.pack(
        ">10I",
        0xD00DFEED,
        total,
        struct_offset,
        total,
        reserve_offset,
        17,
        16,
        0,
        0,
        len(structure),
    )
    return header + b"\0" * 16 + structure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    script_dir = pathlib.Path(__file__).resolve().parent
    finalizer_path = script_dir / "finalize-artifact.py"
    builder_path = script_dir / "build-candidate-ai.sh"
    finalizer = load_module(finalizer_path, "gemini_ai_finalizer_smoke")
    artifact_validator = load_module(
        script_dir / "validate-artifact-reproduction.py",
        "gemini_ai_artifact_reproduction_smoke",
    )
    boot_tests = load_module(
        script_dir / "test-boot-validator.py", "gemini_ai_boot_tests_smoke"
    )
    boot_validator = boot_tests.load_validator()
    package_validator = load_module(
        script_dir / "validate-package.py", "gemini_ai_package_smoke"
    )
    package_reproduction = load_module(
        script_dir / "validate-package-reproduction.py",
        "gemini_ai_package_reproduction_smoke",
    )
    rejected = 0

    with tempfile.TemporaryDirectory(prefix="candidate-ai-builder-smoke-") as raw:
        work = pathlib.Path(raw)
        first_stage = work / "first-stage"
        populate_stage(first_stage, finalizer)
        run(
            [sys.executable, str(finalizer_path), "--stage", str(first_stage)],
            expect_success=True,
        )
        if set(path.name for path in first_stage.iterdir()) != finalizer.EXPECTED_MEMBERS:
            raise ValueError("finalizer did not create the exact final inventory")

        output = work / "published-artifact"
        run(
            [
                sys.executable,
                str(finalizer_path),
                "--publish",
                str(first_stage),
                "--output",
                str(output),
            ],
            expect_success=True,
        )
        if first_stage.exists() or not output.is_dir():
            raise ValueError("successful publication did not atomically consume stage")
        run(
            [sys.executable, str(finalizer_path), "--verify", str(output)],
            expect_success=True,
        )

        failing_stage = work / "failing-published-stage"
        populate_stage(failing_stage, finalizer)
        run(
            [sys.executable, str(finalizer_path), "--stage", str(failing_stage)],
            expect_success=True,
        )
        failed_output = work / "failed-canonical-output"
        run(
            [
                sys.executable,
                str(finalizer_path),
                "--publish",
                str(failing_stage),
                "--output",
                str(failed_output),
            ],
            expect_success=False,
            extra_environment={"CANDIDATE_AI_TEST_FAIL_AFTER_PUBLISH": "1"},
        )
        if failed_output.exists() or failed_output.is_symlink():
            raise ValueError("failed post-publication verification left canonical output")
        run(
            [sys.executable, str(finalizer_path), "--verify", str(failing_stage)],
            expect_success=True,
        )
        rejected += 1

        second_stage = work / "second-stage"
        populate_stage(second_stage, finalizer)
        run(
            [sys.executable, str(finalizer_path), "--stage", str(second_stage)],
            expect_success=True,
        )
        second = work / "second-artifact"
        second_stage.rename(second)
        first_inventory = artifact_validator.inventory(output)
        second_inventory = artifact_validator.inventory(second)
        artifact_validator.compare_reproduction(first_inventory, second_inventory)

        for mutation in ("content", "mode", "extra", "manifest"):
            mutant = work / f"artifact-{mutation}"
            shutil.copytree(second, mutant, copy_function=shutil.copy2)
            if mutation == "content":
                (mutant / "Image.gz").write_bytes(b"changed\n")
            elif mutation == "mode":
                (mutant / "Image.gz").chmod(0o644)
            elif mutation == "extra":
                (mutant / "unexpected").write_bytes(b"extra\n")
            else:
                (mutant / "SHA256SUMS").write_text("malformed\n", encoding="ascii")
            run(
                [sys.executable, str(finalizer_path), "--verify", str(mutant)],
                expect_success=False,
            )
            rejected += 1

        for mutation in ("preexisting-manifest", "missing", "extra", "symlink", "nested"):
            stage = work / f"pre-{mutation}"
            populate_stage(stage, finalizer)
            if mutation == "preexisting-manifest":
                (stage / "SHA256SUMS").write_bytes(b"premature\n")
            elif mutation == "missing":
                (stage / sorted(finalizer.PRE_MANIFEST_MEMBERS)[0]).unlink()
            elif mutation == "extra":
                (stage / "unexpected").write_bytes(b"extra\n")
            elif mutation == "symlink":
                victim = stage / sorted(finalizer.PRE_MANIFEST_MEMBERS)[0]
                victim.unlink()
                victim.symlink_to(stage / sorted(finalizer.PRE_MANIFEST_MEMBERS)[1])
            else:
                (stage / "nested").mkdir()
            run(
                [sys.executable, str(finalizer_path), "--stage", str(stage)],
                expect_success=False,
            )
            if mutation != "preexisting-manifest" and (stage / "SHA256SUMS").exists():
                raise ValueError("failed pre-inventory gate created a manifest")
            rejected += 1

        first_package = work / "package-first"
        second_package = work / "package-second"
        populate_package(first_package, "2026-07-22T12:00:00Z", package_validator)
        populate_package(second_package, "2026-07-22T12:00:01Z", package_validator)
        package_reproduction.compare_substantive(
            first_package, second_package, package_validator
        )
        for mutation in (
            "payload",
            "mode",
            "directory-mode",
            "inventory",
            "empty-directory",
            "build",
            "manifest",
            "symlink",
        ):
            mutant = work / f"package-{mutation}"
            shutil.copytree(second_package, mutant, copy_function=shutil.copy2)
            if mutation == "payload":
                (mutant / "payload.bin").write_bytes(b"different payload\n")
                write_package_manifest(mutant, package_validator)
            elif mutation == "mode":
                (mutant / "payload.bin").chmod(0o600)
            elif mutation == "directory-mode":
                (mutant / "provenance").chmod(0o755)
            elif mutation == "inventory":
                (mutant / "extra.bin").write_bytes(b"extra\n")
                (mutant / "extra.bin").chmod(0o644)
                write_package_manifest(mutant, package_validator)
            elif mutation == "empty-directory":
                (mutant / "unmanifested-empty-directory").mkdir(mode=0o777)
                (mutant / "unmanifested-empty-directory").chmod(0o777)
            elif mutation == "build":
                value = json.loads((mutant / "provenance/build.json").read_text())
                value["identity"] = "different"
                (mutant / "provenance/build.json").write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n"
                )
                write_package_manifest(mutant, package_validator)
            elif mutation == "manifest":
                (mutant / "SHA256SUMS").write_text("malformed\n", encoding="ascii")
            else:
                (mutant / "payload.bin").unlink()
                (mutant / "payload.bin").symlink_to("provenance/build.json")
            expect_function_rejected(
                package_reproduction.compare_substantive,
                first_package,
                mutant,
                package_validator,
            )
            rejected += 1

        cloned_package = work / "package-cloned"
        shutil.copytree(first_package, cloned_package, copy_function=shutil.copy2)
        expect_function_rejected(
            package_reproduction.compare_substantive,
            first_package,
            cloned_package,
            package_validator,
        )
        rejected += 1

        bound_artifact = work / "bound-artifact"
        bound_artifact.mkdir()
        for member in ("Image.gz", "System.map", "kernel.config"):
            shutil.copyfile(first_package / member, bound_artifact / member)
        (bound_artifact / "source-build.json").write_bytes(
            package_validator.normalized_build_bytes(
                package_validator.load_json(
                    first_package / "provenance/build.json", "synthetic package build"
                ),
                "synthetic package build",
            )
        )
        artifact_validator.validate_package_binding(
            bound_artifact, first_package, package_validator
        )
        unpassed_package = work / "unpassed-package"
        shutil.copytree(first_package, unpassed_package, copy_function=shutil.copy2)
        (unpassed_package / "Image.gz").write_bytes(b"unpassed package kernel\n")
        expect_function_rejected(
            artifact_validator.validate_package_binding,
            bound_artifact,
            unpassed_package,
            package_validator,
        )
        rejected += 1

        analyzer = (
            repository
            / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
        )
        if artifact_validator.digest(analyzer) != artifact_validator.LK_ANALYZER_SHA256:
            raise ValueError("source-pinned LK analyzer changed")
        lk_root = work / "lk-analysis"
        lk_root.mkdir()
        image_gz = gzip.compress(boot_tests.synthetic_arm64_image(boot_validator), mtime=0)
        dtb = minimal_fdt()
        initramfs = b"synthetic Candidate AI initramfs"
        boot = boot_tests.serialize(boot_validator, image_gz, dtb, initramfs)
        (lk_root / "Image.gz").write_bytes(image_gz)
        (lk_root / artifact_validator.DTB_MEMBER).write_bytes(dtb)
        (lk_root / artifact_validator.INITRAMFS_MEMBER).write_bytes(initramfs)
        (lk_root / artifact_validator.BOOT_MEMBER).write_bytes(boot)
        analysis = artifact_validator.reproduce_lk_analysis(lk_root, analyzer)
        (lk_root / "analysis.txt").write_bytes(analysis)
        artifact_validator.run_lk_analyzer(lk_root, analyzer)
        (lk_root / "analysis.txt").write_bytes(analysis + b"mutation\n")
        expect_function_rejected(
            artifact_validator.run_lk_analyzer,
            lk_root,
            analyzer,
        )
        rejected += 1

    builder = builder_path.read_text(encoding="utf-8")
    ordered_markers = [
        'boot_cmdline=bootopt=64S3,32N2,64N2',
        'python3 "$finalizer" --stage "$stage"',
        'output_name="candidate-AI-a72-reject-gate-${candidate_sha256:0:8}"',
        '[[ ! -e "$output" && ! -L "$output" ]]',
        'python3 "$finalizer" --publish "$stage" --output "$output"',
        'rmdir "$workdir"',
    ]
    positions = [builder.index(marker) for marker in ordered_markers]
    if positions != sorted(positions):
        raise ValueError("builder finalization/publication ordering changed")
    if 'expected_inventory=' in builder or '>"$stage/SHA256SUMS"' in builder:
        raise ValueError("builder reintroduced its pre-manifest ordering bug")
    if builder.count('--cmdline "$boot_cmdline"') != 1 or builder.count(
        '--expected-cmdline "$boot_cmdline"'
    ) != 1:
        raise ValueError("builder Android header command line is not exact")
    if 'python3 "$gate_auditor"' not in builder:
        raise ValueError("builder no longer preserves the compiled function audit")

    if repository not in builder_path.resolve().parents:
        raise ValueError("builder is not below the selected repository")
    print("validation=candidate-ai-storage-inert-builder-smoke")
    print("synthetic_finalize_publish_verify=passed")
    print("synthetic_two_artifact_reproduction=passed")
    print("synthetic_two_package_substantive_reproduction=passed")
    print("publication_order=passed")
    print("post_publication_failure_rollback=passed")
    print("synthetic_pinned_lk_analysis_reproduction=passed")
    print(f"mutations_rejected={rejected}")
    print("vm_required=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
