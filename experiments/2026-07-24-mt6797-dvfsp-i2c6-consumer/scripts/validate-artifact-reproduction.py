#!/usr/bin/env python3
"""Tie two AP artifacts to validated packages and require exact reproduction."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_ap as ap


EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
EXPECTED_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "dtb-validation.txt",
    ap.BOOT_MEMBER,
    ap.INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    ap.DTB_MEMBER,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
FIXED_PROVENANCE = {
    "experiment": ap.EXPERIMENT,
    "candidate_label": ap.CANDIDATE,
    "kernel_profile": ap.PROFILE,
    "ao_raw_sha256": ap.AO_RAW_SHA256,
    "ao_dtb_sha256": ap.AO_DTB_SHA256,
    "candidate_initramfs_sha256": ap.INITRAMFS_SHA256,
    "candidate_keymap_sha256": ap.KEYMAP_SHA256,
    "patch_0094_sha256": ap.PATCH_0094_SHA256,
    "patch_0095_sha256": ap.PATCH_0095_SHA256,
    "patch_0097_sha256": ap.PATCH_0097_SHA256,
    "patch_0098_sha256": ap.PATCH_0098_SHA256,
    "patch_0099_sha256": ap.PATCH_0099_SHA256,
    "patch_0100_sha256": ap.PATCH_0100_SHA256,
    "patch_0101_sha256": ap.PATCH_0101_SHA256,
    "patch_0102_sha256": ap.PATCH_0102_SHA256,
    "functional_baseline": "exact-hardware-passed-candidate-ao-contract",
    "final_dtb_baseline": "exact-candidate-ao-final-dtb",
    "final_dtb_delta": "access-controller-link-and-childless-i2c6-enable-only",
    "initramfs_keyboard_console_usb_reboot": "byte-exact-candidate-ao",
    "handoff_initial_contract": "exact-candidate-ao-ready-late-passed",
    "handoff_access_controller": "enabled",
    "fw_devlink": "rpm",
    "i2c6": "enabled-childless",
    "i2c6_clients": "0",
    "i2c6_transfer_start_irq": "0",
    "installed_suspend": "disabled",
    "pm_callbacks": "separate-noninstalled-compile-audit",
    "da9214_node": "absent",
    "regulators": "absent",
    "a72_power_node": "absent",
    "maxcpus": "8",
    "a72_power_initcall": "blacklisted",
    "dvfsp_handoff_initcall": "enabled",
    "cpu8_cpu9_request": "none",
    "cpu_operation": "none",
    "regulator_operation": "none",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "automatic_reboot": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = {
    "candidate_sha256",
    "candidate_size",
    "candidate_image_gz_sha256",
    "candidate_system_map_sha256",
    "candidate_dtb_sha256",
    "candidate_config_sha256",
    "candidate_source_build_sha256",
}


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"Candidate AP validation module is unsafe: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Candidate AP validation module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_package_validator(script_dir: pathlib.Path) -> ModuleType:
    validator = load_module(
        script_dir / "validate-package.py",
        "candidate_ap_artifact_package_validator",
    )
    auditor = script_dir / "audit-compiled-handoff.py"
    if (
        ap.digest_path(auditor)
        != validator.COMPILED_HANDOFF_AUDITOR_SHA256
        or validator.COMPILED_HANDOFF_AUDITOR_SHA256
        != ap.COMPILED_HANDOFF_AUDITOR_SHA256
    ):
        raise ValueError("source-pinned compiled-handoff auditor changed")
    return validator


def load_package_reproduction(script_dir: pathlib.Path) -> ModuleType:
    return load_module(
        script_dir / "validate-package-reproduction.py",
        "candidate_ap_artifact_package_reproduction",
    )


def fixed_provenance(script_dir: pathlib.Path) -> dict[str, str]:
    auditor = script_dir / "audit-compiled-handoff.py"
    info = auditor.lstat()
    if auditor.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError("compiled-handoff auditor is missing, empty, or unsafe")
    return {
        **FIXED_PROVENANCE,
        "compiled_handoff_auditor_sha256": ap.digest_path(auditor),
    }


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str, int]]:
    output: dict[str, tuple[int, str, int]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ValueError(f"unexpected non-regular artifact member: {relative}")
        output[relative] = (
            stat.S_IMODE(info.st_mode),
            ap.digest_path(path),
            info.st_size,
        )
    return output


def parse_manifest(
    root: pathlib.Path, members: dict[str, tuple[int, str, int]]
) -> None:
    seen: set[str] = set()
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("Candidate AP artifact manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError("Candidate AP manifest member is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"Candidate AP artifact checksum differs: {member}")
        seen.add(member)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AP manifest inventory changed")


def parse_provenance(path: pathlib.Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in output:
            raise ValueError("Candidate AP provenance is malformed or duplicated")
        output[key] = value
    return output


def validate_ao_manifest(root: pathlib.Path) -> None:
    manifest = ap.read_regular(root / "SHA256SUMS", "Candidate AO manifest")
    if hashlib.sha256(manifest).hexdigest() != ap.AO_MANIFEST_SHA256:
        raise ValueError("Candidate AO artifact manifest changed")
    seen: set[str] = set()
    for number, line in enumerate(manifest.decode("ascii").splitlines(), 1):
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError(f"Candidate AO manifest line {number} is malformed")
        raw = fields[1]
        if not raw.startswith("./"):
            raise ValueError(f"Candidate AO manifest line {number} is non-canonical")
        relative = raw[2:]
        pure = pathlib.PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != relative
            or relative == "SHA256SUMS"
            or relative in seen
        ):
            raise ValueError(f"Candidate AO manifest line {number} is unsafe")
        data = ap.read_regular(root / relative, f"Candidate AO member {relative}")
        if hashlib.sha256(data).hexdigest() != fields[0]:
            raise ValueError(f"Candidate AO artifact checksum differs: {relative}")
        seen.add(relative)


def parse_key_values(path: pathlib.Path, label: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in ap.read_regular(path, label).decode("ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in output:
            raise ValueError(f"{label} is malformed or duplicated")
        output[key] = value
    return output


def expected_package_report(
    package: pathlib.Path,
    package_calibration: dict[str, str | int],
    validator: ModuleType,
) -> dict[str, str]:
    return {
        "validation": "candidate-ap-package-calibration",
        "package": package.name,
        "profile": validator.PROFILE,
        "series_path": validator.SERIES_REL,
        "patch_count": "101",
        "series_sha256": validator.SERIES_SHA256,
        "patchset_sha256": validator.PATCHSET_SHA256,
        "series_entries": (
            "0001-through-corrected-0092-with-0057a-plus-0094-0095-"
            "0097-0098-0099-0100-0101-0102"
        ),
        "patches_0093_0096": "absent",
        "config_inputs_sha256": validator.CONFIG_INPUTS_SHA256,
        "forced_cmdline": "exact-maxcpus8-a72-initcall-blacklist-fw-devlink-rpm",
        "handoff_owner_config": "built-in",
        "handoff_owner_image_markers": "present",
        "handoff_owner_system_map_symbols": "present",
        "predecessor_observer_markers_symbols": "absent",
        "active_0093_markers_symbols": "absent",
        "compiled_reject_gate": "fail-closed-no-cpu-on",
        "compiled_handoff": (
            "provider-balance-pre-mmio-link-instrumentation-and-pm-api-audited"
        ),
        "package_dtb_i2c6": "enabled-childless-access-controlled",
        "package_dtb_handoff_owner": "enabled-access-controller",
        "package_dtb_handoff_clock": "infracfg-i2c-appm-54",
        "package_dtb_role": "nonfinal-build-output",
        "calibration_members": str(package_calibration["members"]),
        "calibration_dtbs": str(package_calibration["dtbs"]),
        "calibration_package_manifest_sha256": (
            "validated-build-specific-generation-manifest"
        ),
        "calibration_normalized_build_sha256": str(
            package_calibration["normalized_build_sha256"]
        ),
        "calibration_config_sha256": str(package_calibration["config_sha256"]),
        "calibration_image_sha256": str(package_calibration["image_sha256"]),
        "calibration_image_size": str(package_calibration["image_size"]),
        "calibration_image_gz_sha256": str(
            package_calibration["image_gz_sha256"]
        ),
        "calibration_image_gz_size": str(package_calibration["image_gz_size"]),
        "calibration_system_map_sha256": str(
            package_calibration["system_map_sha256"]
        ),
        "calibration_compiled_gate_audit_sha256": str(
            package_calibration["compiled_gate_audit_sha256"]
        ),
        "calibration_compiled_handoff_audit_sha256": str(
            package_calibration["compiled_handoff_audit_sha256"]
        ),
        "calibration_package_dtb_sha256": str(
            package_calibration["package_dtb_sha256"]
        ),
        "output_hashes_pinned": "no",
        "artifact_build": "none",
        "device_access": "none",
        "storage_access": "none",
    }


def validate_package_link(
    root: pathlib.Path,
    members: dict[str, tuple[int, str, int]],
    package: pathlib.Path,
    package_calibration: dict[str, str | int],
    validator: ModuleType,
    label: str,
) -> None:
    exact_members = {
        "Image.gz": "image_gz_sha256",
        "System.map": "system_map_sha256",
        "kernel.config": "config_sha256",
    }
    for member, calibration_key in exact_members.items():
        if members[member][1] != package_calibration[calibration_key]:
            raise ValueError(
                f"{label} artifact {member} is not its validated package output"
            )
        if ap.digest_path(package / member) != members[member][1]:
            raise ValueError(
                f"{label} artifact {member} differs from its exact package member"
            )

    build = validator.load_json(
        package / "provenance/build.json", f"{label} package build provenance"
    )
    normalized_build = validator.normalized_build_bytes(
        build, f"{label} package build"
    )
    if ap.read_regular(
        root / "source-build.json", f"{label} artifact source build"
    ) != normalized_build:
        raise ValueError(
            f"{label} artifact normalized build is not its validated package provenance"
        )
    if (
        members["source-build.json"][1]
        != package_calibration["normalized_build_sha256"]
    ):
        raise ValueError(f"{label} normalized-build calibration is discontinuous")

    image_gz = ap.read_regular(root / "Image.gz", f"{label} artifact Image.gz")
    image = validator.decompress_lk_image_gz(
        image_gz, f"{label} artifact Image.gz"
    )
    if image != ap.read_regular(package / "Image", f"{label} package Image"):
        raise ValueError(f"{label} artifact Image.gz does not reproduce package Image")
    config = ap.read_regular(root / "kernel.config", f"{label} artifact config")
    if validator.extract_ikconfig(image) != config:
        raise ValueError(f"{label} artifact embedded IKCONFIG is not exact config")

    with tempfile.TemporaryDirectory(prefix=f"candidate-ap-{label}-audit-") as raw:
        audit_root = pathlib.Path(raw)
        image_path = audit_root / "Image"
        map_path = audit_root / "System.map"
        image_path.write_bytes(image)
        map_path.write_bytes(
            ap.read_regular(root / "System.map", f"{label} artifact System.map")
        )
        image_path.chmod(0o600)
        map_path.chmod(0o600)
        gate_report = validator.validate_compiled_gate(audit_root)
        handoff_report = validator.validate_compiled_handoff(audit_root)
    reports = {
        "compiled_gate_audit_sha256": gate_report,
        "compiled_handoff_audit_sha256": handoff_report,
    }
    for calibration_key, report in reports.items():
        if hashlib.sha256(report).hexdigest() != package_calibration[calibration_key]:
            raise ValueError(
                f"{label} artifact {calibration_key} differs from package audit"
            )

    package_report = parse_key_values(
        root / "package-validation.txt", f"{label} package-validation report"
    )
    expected_report = expected_package_report(package, package_calibration, validator)
    if set(package_report) != set(expected_report):
        missing = sorted(set(expected_report) - set(package_report))
        extra = sorted(set(package_report) - set(expected_report))
        raise ValueError(
            f"{label} package-validation report inventory changed: "
            f"missing={missing[:1]}, extra={extra[:1]}"
        )
    for key, wanted in expected_report.items():
        if package_report[key] != wanted:
            raise ValueError(
                f"{label} package-validation report is not linked: {key}"
            )


def padded_digest(path: pathlib.Path, raw_size: int) -> str:
    if not 0 < raw_size <= ap.BOOT2_SIZE:
        raise ValueError("Candidate AP boot size exceeds the boot2 boundary")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    remaining = ap.BOOT2_SIZE - raw_size
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        block = zeros[: min(remaining, len(zeros))]
        hasher.update(block)
        remaining -= len(block)
    return hasher.hexdigest()


def run_boot_validator(
    root: pathlib.Path, ao_artifact: pathlib.Path, script_dir: pathlib.Path
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(script_dir / "validate-boot.py"),
            "--candidate",
            os.fspath(root / ap.BOOT_MEMBER),
            "--image-gz",
            os.fspath(root / "Image.gz"),
            "--system-map",
            os.fspath(root / "System.map"),
            "--kernel-config",
            os.fspath(root / "kernel.config"),
            "--dtb",
            os.fspath(root / ap.DTB_MEMBER),
            "--ao-dtb",
            os.fspath(ao_artifact / ap.AO_DTB_MEMBER),
            "--initramfs",
            os.fspath(root / ap.INITRAMFS_MEMBER),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError("Candidate AP boot validator rejected artifact: " + detail)


def validate_tree(
    root: pathlib.Path,
    members: dict[str, tuple[int, str, int]],
    ao_artifact: pathlib.Path,
    script_dir: pathlib.Path,
    package: pathlib.Path,
    package_calibration: dict[str, str | int],
    package_validator: ModuleType,
    label: str,
) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AP artifact inventory changed")
    for member, (mode, _, _) in members.items():
        expected = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected:
            raise ValueError(f"Candidate AP artifact mode changed: {member}")
    parse_manifest(root, members)

    fixed = {
        ap.INITRAMFS_MEMBER: ap.INITRAMFS_SHA256,
        "gemini-us.bkeymap": ap.KEYMAP_SHA256,
    }
    if ap.artifact_pin_state() == "source-pinned":
        fixed[ap.DTB_MEMBER] = ap.FINAL_DTB_SHA256
    for member, wanted in fixed.items():
        if members[member][1] != wanted:
            raise ValueError(f"Candidate AP fixed payload changed: {member}")
    for helper in EXECUTABLE_MEMBERS:
        if members[helper][1] != ap.digest_path(ao_artifact / helper):
            raise ValueError(f"Candidate AP Candidate AO helper changed: {helper}")

    boot_hash = members[ap.BOOT_MEMBER][1]
    if root.name != ap.ARTIFACT_PREFIX + boot_hash[:8]:
        raise ValueError("Candidate AP artifact basename disagrees with boot hash")
    provenance = parse_provenance(root / "provenance.txt")
    expected_fixed = fixed_provenance(script_dir)
    if set(provenance) != set(expected_fixed) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AP provenance inventory changed")
    for key, wanted in expected_fixed.items():
        if provenance[key] != wanted:
            raise ValueError(f"Candidate AP provenance changed: {key}")
    dynamic = {
        "candidate_sha256": boot_hash,
        "candidate_size": str(members[ap.BOOT_MEMBER][2]),
        "candidate_image_gz_sha256": members["Image.gz"][1],
        "candidate_system_map_sha256": members["System.map"][1],
        "candidate_dtb_sha256": members[ap.DTB_MEMBER][1],
        "candidate_config_sha256": members["kernel.config"][1],
        "candidate_source_build_sha256": members["source-build.json"][1],
    }
    for key, wanted in dynamic.items():
        if provenance[key] != wanted:
            raise ValueError(f"Candidate AP dynamic provenance changed: {key}")
    validate_package_link(
        root,
        members,
        package,
        package_calibration,
        package_validator,
        label,
    )
    run_boot_validator(root, ao_artifact, script_dir)


def validate_calibration(
    members: dict[str, tuple[int, str, int]], root: pathlib.Path
) -> tuple[str, str]:
    boot_hash = members[ap.BOOT_MEMBER][1]
    boot_size = members[ap.BOOT_MEMBER][2]
    padded = padded_digest(root / ap.BOOT_MEMBER, boot_size)
    state = ap.artifact_pin_state()
    if state == "source-pinned":
        wanted = {
            "Image.gz": (ap.IMAGE_GZ_SHA256, members["Image.gz"][1]),
            "System.map": (ap.SYSTEM_MAP_SHA256, members["System.map"][1]),
            "kernel.config": (ap.CONFIG_SHA256, members["kernel.config"][1]),
            "source-build.json": (
                ap.SOURCE_BUILD_SHA256,
                members["source-build.json"][1],
            ),
            "raw": (ap.RAW_SHA256, boot_hash),
            "raw size": (int(ap.RAW_SIZE), boot_size),
            "artifact manifest": (
                ap.ARTIFACT_MANIFEST_SHA256,
                members["SHA256SUMS"][1],
            ),
            "padded": (ap.PADDED_SHA256, padded),
        }
        for label, (expected, actual) in wanted.items():
            if expected != actual:
                raise ValueError(f"source-pinned Candidate AP {label} differs")
    return state, padded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=pathlib.Path)
    parser.add_argument("--second", required=True, type=pathlib.Path)
    parser.add_argument("--ao-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--first-package", required=True, type=pathlib.Path)
    parser.add_argument("--second-package", required=True, type=pathlib.Path)
    parser.add_argument("--first-source-dir", required=True, type=pathlib.Path)
    parser.add_argument("--first-build-dir", required=True, type=pathlib.Path)
    parser.add_argument("--first-artifact-root", required=True, type=pathlib.Path)
    parser.add_argument("--second-source-dir", required=True, type=pathlib.Path)
    parser.add_argument("--second-build-dir", required=True, type=pathlib.Path)
    parser.add_argument("--second-artifact-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        first_root = resolve_directory(args.first, "first AP artifact")
        second_root = resolve_directory(args.second, "second AP artifact")
        ao_artifact = resolve_directory(args.ao_artifact, "Candidate AO artifact")
        if first_root == second_root or first_root.samefile(second_root):
            raise ValueError("reproduction requires two independent AP trees")
        if ao_artifact.name != ap.AO_ARTIFACT_DIR:
            raise ValueError("Candidate AO artifact basename changed")

        script_dir = pathlib.Path(__file__).resolve().parent
        package_validator = load_package_validator(script_dir)
        package_reproduction = load_package_reproduction(script_dir)
        repository = package_validator.resolve_directory(
            args.repository, "repository"
        )
        first_package = package_validator.resolve_directory(
            args.first_package, "first Candidate AP package"
        )
        second_package = package_validator.resolve_directory(
            args.second_package, "second Candidate AP package"
        )
        live_roots = {
            "first source": package_validator.resolve_directory(
                args.first_source_dir, "first live source"
            ),
            "first build": package_validator.resolve_directory(
                args.first_build_dir, "first live build"
            ),
            "first artifacts": package_validator.resolve_directory(
                args.first_artifact_root, "first live artifact root"
            ),
            "second source": package_validator.resolve_directory(
                args.second_source_dir, "second live source"
            ),
            "second build": package_validator.resolve_directory(
                args.second_build_dir, "second live build"
            ),
            "second artifacts": package_validator.resolve_directory(
                args.second_artifact_root, "second live artifact root"
            ),
        }
        (
            first_package_calibration,
            second_package_calibration,
            _,
            live_evidence,
        ) = package_reproduction.validate_reproduction(
            package_validator,
            repository,
            first_package,
            second_package,
            live_roots,
        )
        validate_ao_manifest(ao_artifact)
        first = inventory(first_root)
        second = inventory(second_root)
        validate_tree(
            first_root,
            first,
            ao_artifact,
            script_dir,
            first_package,
            first_package_calibration,
            package_validator,
            "first",
        )
        validate_tree(
            second_root,
            second,
            ao_artifact,
            script_dir,
            second_package,
            second_package_calibration,
            package_validator,
            "second",
        )
        if first != second:
            names = sorted(set(first) | set(second))
            changed = [name for name in names if first.get(name) != second.get(name)]
            raise ValueError(
                "Candidate AP artifacts differ: " + ",".join(changed[:3])
            )
        calibration, padded = validate_calibration(first, first_root)

        print("validation=candidate-ap-artifact-reproduction")
        print(f"first_artifact={first_root}")
        print(f"second_artifact={second_root}")
        print(f"first_package={first_package}")
        print(f"second_package={second_package}")
        print(
            "first_package_manifest_sha256="
            f"{first_package_calibration['package_manifest_sha256']}"
        )
        print(
            "second_package_manifest_sha256="
            f"{second_package_calibration['package_manifest_sha256']}"
        )
        print(f"members={len(first)}")
        print(f"boot_sha256={first[ap.BOOT_MEMBER][1]}")
        print(f"boot_size={first[ap.BOOT_MEMBER][2]}")
        print(f"image_gz_sha256={first['Image.gz'][1]}")
        print(f"system_map_sha256={first['System.map'][1]}")
        print(f"config_sha256={first['kernel.config'][1]}")
        print(f"source_build_sha256={first['source-build.json'][1]}")
        print(f"dtb_sha256={first[ap.DTB_MEMBER][1]}")
        print(f"manifest_sha256={first['SHA256SUMS'][1]}")
        print(f"padded_sha256={padded}")
        print(f"calibration={calibration}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        print("compiled_handoff_audit=passed")
        print("compiled_a72_gate_audit=continuous-from-packages")
        print("embedded_ikconfig=exact-package-config")
        print("package_artifact_linkage=exact-members-and-normalized-provenance")
        print("live_package_reproduction=distinct-roots-state-output-dtb-linked")
        print(f"source_state_sha256={live_evidence['source_state_sha256']}")
        print(f"build_state_sha256={live_evidence['build_state_sha256']}")
        print(
            "live_dtb_inventory_sha256="
            f"{live_evidence['live_dtb_inventory_sha256']}"
        )
        print("handoff_access_controller=enabled")
        print("i2c6=enabled-childless")
        print("i2c6_transfer_start_irq=runtime-must-remain-zero")
        print("da9214_node=absent")
        print("a72_power_node=absent")
        print("cpu_regulator_storage_operation=none")
        print("device_access=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
