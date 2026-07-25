#!/usr/bin/env python3
"""Require two Candidate AI artifacts to be byte- and mode-identical."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


BOOT_MEMBER = "gemini-a72-reject-gate-kernel-split.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-a72-reject-gate-kernel-split.dtb"
INITRAMFS_MEMBER = "gemini-a72-reject-gate-kernel-split-initramfs.img"
AUDIT_MEMBER = "mt6797-psci-cpu-boot-audit.txt"
EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
EXPECTED_MEMBERS = {
    "Image.gz", "SHA256SUMS", "System.map", "analysis.txt",
    "boot-validation.txt", "console-keymap-verify", "console-unicode-mode",
    BOOT_MEMBER, INITRAMFS_MEMBER, "gemini-us.bkeymap", "input-event-capture",
    "kernel.config", "lineage-validation.txt", DTB_MEMBER,
    AUDIT_MEMBER, "package-validation.txt", "provenance.txt", "serializer.txt",
    "series-validation.txt", "source-build.json",
}
FIXED_HASHES = {
    "kernel.config": "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46",
    DTB_MEMBER: "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845",
    INITRAMFS_MEMBER: "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3",
    "gemini-us.bkeymap": "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c",
    "console-keymap-verify": "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238",
    "console-unicode-mode": "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650",
    "input-event-capture": "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602",
}
FIXED_PROVENANCE = {
    "experiment": "2026-07-22-a72-reject-gate-kernel-split",
    "candidate_label": "AI",
    "kernel_profile": "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate",
    "series_path": "patches/series-a72-reject-gate",
    "series_sha256": "b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00",
    "patchset_sha256": "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd",
    "patch_delta_from_ad": "corrected-0092-only",
    "patches_0088_0091": "absent",
    "config_inputs_sha256": "ad93d6669bd261cf1171237328dd9209fd45b2c3ed2154e441a1951908da4ba1",
    "config_sha256": FIXED_HASHES["kernel.config"],
    "candidate_dtb_sha256": FIXED_HASHES[DTB_MEMBER],
    "candidate_initramfs_sha256": FIXED_HASHES[INITRAMFS_MEMBER],
    "final_dtb_lineage": "byte-exact-candidate-ah",
    "initramfs_helpers_lineage": "byte-exact-candidate-ad",
    "cpu_policy": "maxcpus-8-cpu8-cpu9-not-requested",
    "regulator_reset_observer_paths": "absent",
    "active_cpu_request": "none",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "userspace_automatic_reboot": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = {
    "candidate_sha256",
    "candidate_size",
    "candidate_image_gz_sha256",
    "candidate_system_map_sha256",
    "candidate_source_build_sha256",
    "compiled_gate_audit_sha256",
}
LK_ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
LK_GATE_COUNT = 32


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str]]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe artifact directory: {root}")
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        path_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(path_info.st_mode):
            raise ValueError(f"unexpected non-regular artifact member: {relative}")
        result[relative] = (stat.S_IMODE(path_info.st_mode), digest(path))
    return result


def parse_manifest(
    root: pathlib.Path, members: dict[str, tuple[int, str]]
) -> None:
    seen: set[str] = set()
    lines = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("Candidate AI artifact manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError("Candidate AI manifest path is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"Candidate AI artifact checksum mismatch: {member}")
        seen.add(member)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AI manifest is not the exact artifact inventory")


def parse_provenance(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("Candidate AI provenance is malformed or duplicated")
        result[key] = value
    return result


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_validator(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["LC_ALL"] = "C"
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"validator rejected artifact: {detail}")


def normalized_package_build(
    package: pathlib.Path, package_validator: object
) -> bytes:
    value = package_validator.load_json(
        package / "provenance/build.json", "Candidate AI package build"
    )
    return package_validator.normalized_build_bytes(value, "Candidate AI package build")


def validate_package_binding(
    root: pathlib.Path, package: pathlib.Path, package_validator: object
) -> None:
    for member in ("Image.gz", "System.map", "kernel.config"):
        if (root / member).read_bytes() != (package / member).read_bytes():
            raise ValueError(f"Candidate AI artifact is not bound to its package: {member}")
    if (root / "source-build.json").read_bytes() != normalized_package_build(
        package, package_validator
    ):
        raise ValueError("Candidate AI artifact build record is not bound to its package")


def reproduce_lk_analysis(root: pathlib.Path, analyzer: pathlib.Path) -> bytes:
    command = [
        sys.executable,
        os.fspath(analyzer),
        "--validate-lk",
        "--expected-image-gz",
        os.fspath(root / "Image.gz"),
        "--expected-ramdisk",
        os.fspath(root / INITRAMFS_MEMBER),
        "--expected-dtb",
        os.fspath(root / DTB_MEMBER),
        "--expected-name",
        "gemini-obs-L",
        "--expected-cmdline",
        "bootopt=64S3,32N2,64N2",
        os.fspath(root / BOOT_MEMBER),
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["LC_ALL"] = "C"
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        env=environment,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip() or "no diagnostic"
        raise ValueError(f"pinned LK analyzer rejected artifact: {detail}")
    return result.stdout


def run_lk_analyzer(root: pathlib.Path, analyzer: pathlib.Path) -> None:
    analysis = reproduce_lk_analysis(root, analyzer)
    if analysis != (root / "analysis.txt").read_bytes():
        raise ValueError("preserved LK analysis does not reproduce")
    gate_lines = [line for line in analysis.splitlines() if line.startswith(b"gate_")]
    if len(gate_lines) != LK_GATE_COUNT or any(
        not line.endswith(b"=yes") for line in gate_lines
    ):
        raise ValueError("reproduced LK gate inventory is not an all-pass result")
    if b"lk_validation=passed\n" not in analysis:
        raise ValueError("reproduced LK analysis lacks its passed result")


def validate_tree(
    root: pathlib.Path,
    members: dict[str, tuple[int, str]],
    package: pathlib.Path,
    package_validator: object,
    gate_auditor: object,
    analyzer: pathlib.Path,
) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AI artifact inventory changed")
    for member, (mode, _) in members.items():
        expected_mode = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"Candidate AI artifact mode changed: {member}")
    parse_manifest(root, members)
    for member, expected in FIXED_HASHES.items():
        if members[member][1] != expected:
            raise ValueError(f"Candidate AI exact component changed: {member}")

    boot_hash = members[BOOT_MEMBER][1]
    if root.name != f"candidate-AI-a72-reject-gate-{boot_hash[:8]}":
        raise ValueError("Candidate AI artifact basename disagrees with boot hash")
    provenance = parse_provenance(root / "provenance.txt")
    if set(provenance) != set(FIXED_PROVENANCE) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AI provenance inventory changed")
    for key, expected in FIXED_PROVENANCE.items():
        if provenance[key] != expected:
            raise ValueError(f"Candidate AI provenance changed: {key}")
    dynamic_members = {
        "candidate_sha256": BOOT_MEMBER,
        "candidate_image_gz_sha256": "Image.gz",
        "candidate_system_map_sha256": "System.map",
        "candidate_source_build_sha256": "source-build.json",
        "compiled_gate_audit_sha256": AUDIT_MEMBER,
    }
    for key, member in dynamic_members.items():
        if provenance[key] != members[member][1]:
            raise ValueError(f"Candidate AI dynamic provenance disagrees: {key}")
    if provenance["candidate_size"] != str((root / BOOT_MEMBER).stat().st_size):
        raise ValueError("Candidate AI provenance size changed")

    build = json.loads((root / "source-build.json").read_text(encoding="utf-8"))
    if not isinstance(build, dict) or "generated_utc" in build:
        raise ValueError("Candidate AI normalized build provenance is malformed")
    package_validator.require_build_fields(
        build,
        package_validator.PROFILE,
        package_validator.AI_PATCHSET_SHA256,
        package_validator.AI_CONFIG_INPUTS_SHA256,
        "AI artifact",
    )
    validate_package_binding(root, package, package_validator)
    image = package_validator.decompress_lk_image_gz(
        (root / "Image.gz").read_bytes(), "Candidate AI artifact Image.gz"
    )
    package_validator.validate_kernel_policy(
        image,
        (root / "System.map").read_bytes(),
        (root / "kernel.config").read_bytes(),
    )
    with tempfile.TemporaryDirectory(prefix="candidate-ai-gate-audit-") as raw:
        image_path = pathlib.Path(raw) / "Image"
        image_path.write_bytes(image)
        reproduced_audit = gate_auditor.audit_kernel(
            image_path, root / "System.map"
        )
    if reproduced_audit != (root / AUDIT_MEMBER).read_bytes():
        raise ValueError("preserved compiled-gate audit does not reproduce")
    run_lk_analyzer(root, analyzer)


def compare_reproduction(
    first: dict[str, tuple[int, str]], second: dict[str, tuple[int, str]]
) -> None:
    if first != second:
        names = set(first) | set(second)
        changed = sorted(name for name in names if first.get(name) != second.get(name))
        raise ValueError("Candidate AI artifacts differ: " + ",".join(changed[:4]))


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--first-package", type=pathlib.Path, required=True)
    parser.add_argument("--second-package", type=pathlib.Path, required=True)
    parser.add_argument("--ad-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ah-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        roots = {
            "first": resolve_directory(args.first, "first artifact"),
            "second": resolve_directory(args.second, "second artifact"),
            "first-package": resolve_directory(args.first_package, "first package"),
            "second-package": resolve_directory(args.second_package, "second package"),
            "AD-package": resolve_directory(args.ad_package, "AD package"),
            "AD": resolve_directory(args.ad_artifact, "AD artifact"),
            "AH": resolve_directory(args.ah_artifact, "AH artifact"),
            "AF": resolve_directory(args.af_artifact, "AF artifact"),
        }
        if roots["first"] == roots["second"] or roots["first"].samefile(roots["second"]):
            raise ValueError("reproduction requires two distinct artifact trees")
        script_dir = pathlib.Path(__file__).resolve().parent
        repository = script_dir.parents[2]
        lineage_validator = script_dir / "validate-lineage.py"
        boot_validator = script_dir / "validate-boot.py"
        analyzer = (
            repository
            / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
        )
        analyzer_info = analyzer.lstat()
        if (
            analyzer.is_symlink()
            or not stat.S_ISREG(analyzer_info.st_mode)
            or digest(analyzer) != LK_ANALYZER_SHA256
        ):
            raise ValueError("source-pinned LK analyzer changed or is unsafe")
        patch_info = args.patch_0092.lstat()
        if args.patch_0092.is_symlink() or not stat.S_ISREG(patch_info.st_mode):
            raise ValueError("corrected patch 0092 path is unsafe")
        patch = args.patch_0092.resolve(strict=True)
        package_validator = load_module(
            script_dir / "validate-package.py", "gemini_ai_reproduction_package"
        )
        package_reproduction = load_module(
            script_dir / "validate-package-reproduction.py",
            "gemini_ai_reproduction_package_comparison",
        )
        gate_auditor = load_module(
            script_dir / "audit-mt6797-psci-cpu-boot.py",
            "gemini_ai_reproduction_gate_auditor",
        )
        run_validator(
            [
                sys.executable,
                os.fspath(lineage_validator),
                "--ad-artifact",
                os.fspath(roots["AD"]),
                "--ah-artifact",
                os.fspath(roots["AH"]),
                "--af-artifact",
                os.fspath(roots["AF"]),
            ]
        )

        package_validator.validate_package(
            roots["AD-package"], roots["first-package"], patch
        )
        package_validator.validate_package(
            roots["AD-package"], roots["second-package"], patch
        )
        package_reproduction.compare_substantive(
            roots["first-package"],
            roots["second-package"],
            package_validator,
        )

        first = inventory(roots["first"])
        second = inventory(roots["second"])
        for root, members, package in (
            (roots["first"], first, roots["first-package"]),
            (roots["second"], second, roots["second-package"]),
        ):
            validate_tree(
                root,
                members,
                package,
                package_validator,
                gate_auditor,
                analyzer,
            )
            run_validator(
                [
                    sys.executable,
                    os.fspath(boot_validator),
                    "--candidate",
                    os.fspath(root / BOOT_MEMBER),
                    "--image-gz",
                    os.fspath(root / "Image.gz"),
                    "--dtb",
                    os.fspath(root / DTB_MEMBER),
                    "--initramfs",
                    os.fspath(root / INITRAMFS_MEMBER),
                    "--kernel-config",
                    os.fspath(root / "kernel.config"),
                    "--system-map",
                    os.fspath(root / "System.map"),
                    "--ad-boot",
                    os.fspath(roots["AD"] / "gemini-smp8.boot.img"),
                    "--ah-boot",
                    os.fspath(
                        roots["AH"] / "gemini-ad-contract-af-kernel-split.boot.img"
                    ),
                    "--af-boot",
                    os.fspath(
                        roots["AF"] / "gemini-a72-observer-initcall-diagnostic.boot.img"
                    ),
                ]
            )
        compare_reproduction(first, second)
        print("validation=candidate-ai-artifact-reproduction")
        print(f"members={len(first)}")
        print(f"boot_sha256={first[BOOT_MEMBER][1]}")
        print(f"image_gz_sha256={first['Image.gz'][1]}")
        print(f"system_map_sha256={first['System.map'][1]}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        print("android_v0_validated_twice=yes")
        print("compiled_gate_audit_reproduced_twice=yes")
        print("lk_analysis_reproduced_twice=yes")
        print("artifact_package_binding=exact-twice")
        print("independent_build_execution=requires-external-fresh-root-record")
        print("new_output_identities=ready-for-evidence-record")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
