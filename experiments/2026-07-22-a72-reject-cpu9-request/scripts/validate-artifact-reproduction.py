#!/usr/bin/env python3
"""Validate two independently assembled Candidate AK artifact trees."""

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
from collections.abc import Mapping
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_ak as ak


AUDIT_MEMBER = "mt6797-psci-cpu-boot-audit.txt"
MANIFEST_MEMBER = "SHA256SUMS"
EXECUTABLE_MEMBERS = frozenset(
    {
        "console-keymap-verify",
        "console-unicode-mode",
        "input-event-capture",
    }
)
EXPECTED_MEMBERS = frozenset(
    {
        "Image.gz",
        MANIFEST_MEMBER,
        "System.map",
        "analysis.txt",
        "boot-validation.txt",
        "console-keymap-verify",
        "console-unicode-mode",
        ak.BOOT_MEMBER,
        ak.INITRAMFS_MEMBER,
        "gemini-us.bkeymap",
        "input-event-capture",
        "kernel.config",
        "lineage-validation.txt",
        ak.DTB_MEMBER,
        AUDIT_MEMBER,
        "package-validation.txt",
        "provenance.txt",
        "serializer.txt",
        "series-validation.txt",
        "source-build.json",
    }
)
PRE_MANIFEST_MEMBERS = EXPECTED_MEMBERS - {MANIFEST_MEMBER}
BOUND_PACKAGE_MEMBERS = ("Image.gz", "System.map", "kernel.config")
LK_ANALYZER_SHA256 = (
    "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
)
LK_GATE_COUNT = 32

# Each entry is (mode, size, SHA-256).
Inventory = dict[str, tuple[int, int, str]]

FIXED_PROVENANCE = {
    "experiment": ak.EXPERIMENT,
    "candidate_label": ak.CANDIDATE,
    "kernel_profile": ak.PROFILE,
    "series_path": ak.SERIES_REL,
    "series_sha256": ak.SERIES_SHA256,
    "patchset_sha256": ak.PATCHSET_SHA256,
    "patch_delta_from_aj": "none",
    "config_delta_from_aj": "maxcpus-9-to-maxcpus-10-only",
    "config_inputs_sha256": ak.CONFIG_INPUTS_SHA256,
    "config_sha256": ak.CONFIG_SHA256,
    "candidate_dtb_sha256": ak.FINAL_DTB_SHA256,
    "candidate_initramfs_sha256": ak.INITRAMFS_SHA256,
    "final_dtb_lineage": "byte-exact-candidate-aj",
    "initramfs_helpers_lineage": "byte-exact-candidate-aj",
    "cpu_policy": "maxcpus-10-cpu8-and-cpu9-rejection-request",
    "expected_gate_result": "cpu8-and-cpu9-eagain-minus-11",
    "regulator_reset_observer_paths": "absent",
    "storage_access": "none",
    "watchdog_userspace": "none",
    "userspace_automatic_reboot": "none",
    "artifact_builder_device_access": "none",
    "flash": "none",
    "runtime_result": "not-tested",
}
DYNAMIC_PROVENANCE = frozenset(
    {
        "candidate_sha256",
        "candidate_size",
        "candidate_image_gz_sha256",
        "candidate_system_map_sha256",
        "candidate_source_build_sha256",
        "compiled_gate_audit_sha256",
    }
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def expected_mode(member: str) -> int:
    return 0o755 if member in EXECUTABLE_MEMBERS else 0o600


def canonical_manifest_bytes(inventory: Mapping[str, tuple[int, int, str]]) -> bytes:
    """Return the only accepted manifest encoding for a complete inventory."""

    if set(inventory) != EXPECTED_MEMBERS:
        raise ValueError("cannot serialize a non-exact Candidate AK inventory")
    return "".join(
        f"{inventory[member][2]}  ./{member}\n"
        for member in sorted(PRE_MANIFEST_MEMBERS)
    ).encode("ascii")


def inspect_artifact_tree(root: pathlib.Path) -> Inventory:
    """Require one flat, exact, canonical 20-member artifact tree."""

    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe Candidate AK artifact tree: {root}")
    inventory: Inventory = {}
    for path in sorted(root.iterdir()):
        member_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(member_info.st_mode):
            raise ValueError(f"artifact member is not a regular file: {path.name}")
        inventory[path.name] = (
            stat.S_IMODE(member_info.st_mode),
            member_info.st_size,
            digest_path(path),
        )
    if set(inventory) != EXPECTED_MEMBERS or len(inventory) != 20:
        missing = sorted(EXPECTED_MEMBERS - set(inventory))
        extra = sorted(set(inventory) - EXPECTED_MEMBERS)
        raise ValueError(
            "Candidate AK artifact inventory changed: "
            f"missing={missing}, extra={extra}"
        )
    for member, (mode, _size, _checksum) in inventory.items():
        wanted = expected_mode(member)
        if mode != wanted:
            raise ValueError(
                f"Candidate AK artifact mode changed: {member}: "
                f"expected {wanted:04o}, found {mode:04o}"
            )
    manifest = ak.read_regular(
        root / MANIFEST_MEMBER, "Candidate AK artifact manifest"
    )
    if manifest != canonical_manifest_bytes(inventory):
        raise ValueError("Candidate AK artifact manifest is not exact and canonical")
    return inventory


def compare_artifact_trees(
    first_root: pathlib.Path,
    first: Inventory,
    second_root: pathlib.Path,
    second: Inventory,
) -> None:
    """Require complete byte and file-mode equality, not selected-member equality."""

    if first_root == second_root or first_root.samefile(second_root):
        raise ValueError("artifact reproduction requires two distinct trees")
    if first != second:
        changed = sorted(
            member
            for member in set(first) | set(second)
            if first.get(member) != second.get(member)
        )
        raise ValueError("Candidate AK artifact metadata differs: " + ",".join(changed))
    for member in sorted(EXPECTED_MEMBERS):
        if (first_root / member).read_bytes() != (second_root / member).read_bytes():
            raise ValueError(f"Candidate AK artifact bytes differ: {member}")


def validate_binding_bytes(
    artifact: Mapping[str, bytes],
    package: Mapping[str, bytes],
    normalized_build: bytes,
    reproduced_audit: bytes,
) -> None:
    """Pure pair-binding check used by the real validator and mutation suite."""

    for member in BOUND_PACKAGE_MEMBERS:
        if artifact.get(member) != package.get(member):
            raise ValueError(f"Candidate AK artifact/package binding changed: {member}")
    if artifact.get("source-build.json") != normalized_build:
        raise ValueError("Candidate AK normalized build/package binding changed")
    if artifact.get(AUDIT_MEMBER) != reproduced_audit:
        raise ValueError("Candidate AK compiled-gate/package binding changed")


def parse_provenance(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in data.decode("ascii").splitlines():
        key, separator, value = line.partition("=")
        if (
            not separator
            or re.fullmatch(r"[a-z0-9_]+", key) is None
            or not value
            or key in result
        ):
            raise ValueError("Candidate AK provenance is malformed or duplicated")
        result[key] = value
    return result


def validate_provenance(data: bytes, inventory: Inventory) -> None:
    provenance = parse_provenance(data)
    if set(provenance) != set(FIXED_PROVENANCE) | DYNAMIC_PROVENANCE:
        raise ValueError("Candidate AK provenance inventory changed")
    for key, expected in FIXED_PROVENANCE.items():
        if provenance[key] != expected:
            raise ValueError(f"Candidate AK provenance changed: {key}")
    dynamic_members = {
        "candidate_sha256": ak.BOOT_MEMBER,
        "candidate_image_gz_sha256": "Image.gz",
        "candidate_system_map_sha256": "System.map",
        "candidate_source_build_sha256": "source-build.json",
        "compiled_gate_audit_sha256": AUDIT_MEMBER,
    }
    for key, member in dynamic_members.items():
        if provenance[key] != inventory[member][2]:
            raise ValueError(f"Candidate AK dynamic provenance disagrees: {key}")
    if provenance["candidate_size"] != str(inventory[ak.BOOT_MEMBER][1]):
        raise ValueError("Candidate AK dynamic provenance disagrees: candidate_size")


def validate_artifact_basename(root: pathlib.Path, inventory: Inventory) -> None:
    expected = f"candidate-AK-a72-reject-cpu9-{inventory[ak.BOOT_MEMBER][2][:8]}"
    if root.name != expected:
        raise ValueError("Candidate AK artifact basename disagrees with raw boot hash")


def validate_selected_identities(inventory: Inventory) -> None:
    if inventory[ak.BOOT_MEMBER][2] != ak.RAW_SHA256:
        raise ValueError("Candidate AK raw boot SHA-256 differs from the selected pin")
    if inventory[ak.BOOT_MEMBER][1] != int(ak.RAW_SIZE):
        raise ValueError("Candidate AK raw boot size differs from the selected pin")
    if inventory[MANIFEST_MEMBER][2] != ak.ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AK artifact manifest differs from the selected pin")


def load_local_module(filename: str, module_name: str) -> ModuleType:
    path = pathlib.Path(__file__).resolve().with_name(filename)
    ak.read_regular(path, f"Candidate AK {filename}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Candidate AK {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_capture(command: list[str], label: str) -> bytes:
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
        detail = result.stderr.decode(errors="replace").strip()
        if not detail:
            detail = result.stdout.decode(errors="replace").strip() or "no diagnostic"
        raise ValueError(f"{label} rejected input: {detail}")
    if result.stderr:
        raise ValueError(f"{label} emitted unexpected stderr")
    return result.stdout


def normalized_package_build(package: pathlib.Path, package_validator: ModuleType) -> bytes:
    value = package_validator.load_json(
        package / "provenance/build.json", "Candidate AK package build"
    )
    package_validator.require_build(value)
    normalized = dict(value)
    del normalized["generated_utc"]
    return (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode()


def validate_pair_binding(
    artifact: pathlib.Path,
    package: pathlib.Path,
    package_validator: ModuleType,
    reproduced_audit: bytes,
) -> None:
    artifact_bytes = {
        member: ak.read_regular(
            artifact / member, f"Candidate AK artifact member {member}"
        )
        for member in (*BOUND_PACKAGE_MEMBERS, "source-build.json", AUDIT_MEMBER)
    }
    package_bytes = {
        member: ak.read_regular(
            package / member, f"Candidate AK package member {member}"
        )
        for member in BOUND_PACKAGE_MEMBERS
    }
    validate_binding_bytes(
        artifact_bytes,
        package_bytes,
        normalized_package_build(package, package_validator),
        reproduced_audit,
    )


def validate_exact_aj_artifact(root: pathlib.Path) -> None:
    validator = ak.load_aj_module(
        "validate-artifact-pins.py", "candidate_ak_reproduction_aj_artifact_pins"
    )
    validator.validate_candidate(root)
    if root.name != ak.AJ_ARTIFACT_DIR:
        raise ValueError("Candidate AJ artifact basename changed")
    if digest_path(root / MANIFEST_MEMBER) != ak.AJ_ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AJ artifact manifest identity changed")
    if digest_path(root / ak.AJ_BOOT_MEMBER) != ak.AJ_RAW_SHA256:
        raise ValueError("Candidate AJ raw boot identity changed")


def baseline_boots(
    ad: pathlib.Path,
    ah: pathlib.Path,
    af: pathlib.Path,
    ai: pathlib.Path,
    aj: pathlib.Path,
) -> list[tuple[str, pathlib.Path]]:
    aj_identity = ak.load_aj_identity("candidate_ak_baseline_aj_identity")
    return [
        ("--ad-boot", ad / "gemini-smp8.boot.img"),
        ("--ah-boot", ah / "gemini-ad-contract-af-kernel-split.boot.img"),
        ("--af-boot", af / "gemini-a72-observer-initcall-diagnostic.boot.img"),
        ("--ai-boot", ai / aj_identity.AI_BOOT_MEMBER),
        ("--aj-boot", aj / ak.AJ_BOOT_MEMBER),
    ]


def reproduce_lk_analysis(root: pathlib.Path, analyzer: pathlib.Path) -> bytes:
    return run_capture(
        [
            sys.executable,
            os.fspath(analyzer),
            "--validate-lk",
            "--expected-image-gz",
            os.fspath(root / "Image.gz"),
            "--expected-ramdisk",
            os.fspath(root / ak.INITRAMFS_MEMBER),
            "--expected-dtb",
            os.fspath(root / ak.DTB_MEMBER),
            "--expected-name",
            "gemini-obs-L",
            "--expected-cmdline",
            "bootopt=64S3,32N2,64N2",
            os.fspath(root / ak.BOOT_MEMBER),
        ],
        "source-pinned LK analyzer",
    )


def validate_lk_analysis(root: pathlib.Path, analyzer: pathlib.Path) -> None:
    reproduced = reproduce_lk_analysis(root, analyzer)
    if reproduced != ak.read_regular(root / "analysis.txt", "Candidate AK LK analysis"):
        raise ValueError("Candidate AK preserved LK analysis does not reproduce")
    gates = [line for line in reproduced.splitlines() if line.startswith(b"gate_")]
    if len(gates) != LK_GATE_COUNT or any(not line.endswith(b"=yes") for line in gates):
        raise ValueError("Candidate AK LK analysis is not an exact 32-gate pass")
    if b"lk_validation=passed\n" not in reproduced:
        raise ValueError("Candidate AK LK analysis lacks its passed result")


def validate_artifact(
    root: pathlib.Path,
    package: pathlib.Path,
    inventory: Inventory,
    finalizer: ModuleType,
    package_validator: ModuleType,
    boot_validator_path: pathlib.Path,
    gate_auditor_path: pathlib.Path,
    analyzer: pathlib.Path,
    baselines: list[tuple[str, pathlib.Path]],
) -> None:
    finalized = finalizer.verify(root)
    if set(finalized) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AK finalizer inventory contract changed")
    validate_artifact_basename(root, inventory)
    validate_provenance(
        ak.read_regular(root / "provenance.txt", "Candidate AK provenance"), inventory
    )

    boot_command = [
        sys.executable,
        os.fspath(boot_validator_path),
        "--candidate",
        os.fspath(root / ak.BOOT_MEMBER),
        "--image-gz",
        os.fspath(root / "Image.gz"),
        "--dtb",
        os.fspath(root / ak.DTB_MEMBER),
        "--initramfs",
        os.fspath(root / ak.INITRAMFS_MEMBER),
        "--kernel-config",
        os.fspath(root / "kernel.config"),
        "--system-map",
        os.fspath(root / "System.map"),
    ]
    for option, path in baselines:
        boot_command.extend((option, os.fspath(path)))
    boot_report = run_capture(boot_command, "Candidate AK Android-v0 validator")
    if boot_report != ak.read_regular(
        root / "boot-validation.txt", "Candidate AK boot-validation record"
    ):
        raise ValueError("Candidate AK preserved Android-v0 validation does not reproduce")

    gate_report = run_capture(
        [
            sys.executable,
            os.fspath(gate_auditor_path),
            "--image",
            os.fspath(package / "Image"),
            "--system-map",
            os.fspath(package / "System.map"),
        ],
        "source-pinned compiled-gate auditor",
    )
    package_validator.validate_audit_semantics(gate_report)
    if gate_report != ak.read_regular(
        root / AUDIT_MEMBER, "Candidate AK compiled-gate audit"
    ):
        raise ValueError("Candidate AK preserved compiled-gate audit does not reproduce")
    validate_pair_binding(root, package, package_validator, gate_report)
    validate_lk_analysis(root, analyzer)


def resolve_distinct(
    first: pathlib.Path, second: pathlib.Path, label: str
) -> tuple[pathlib.Path, pathlib.Path]:
    left = ak.resolve_directory(first, f"first Candidate AK {label}")
    right = ak.resolve_directory(second, f"second Candidate AK {label}")
    if left == right or left.samefile(right):
        raise ValueError(f"reproduction requires two distinct {label} trees")
    return left, right


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "validate artifact semantics after package pins close, emit raw and "
            "manifest identities, and deliberately do not consult artifact pins"
        ),
    )
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--first-package", type=pathlib.Path, required=True)
    parser.add_argument("--second-package", type=pathlib.Path, required=True)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ah-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ai-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--aj-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        # Bootstrap is intentionally only an artifact-identity bootstrap. Both
        # independent package builds must already have reproduced and been pinned.
        if args.bootstrap:
            ak.require_package_pins()
        else:
            ak.require_artifact_pins()

        first, second = resolve_distinct(args.first, args.second, "artifact")
        first_package, second_package = resolve_distinct(
            args.first_package, args.second_package, "package"
        )
        ad = ak.resolve_directory(args.ad_artifact, "Candidate AD artifact")
        ah = ak.resolve_directory(args.ah_artifact, "Candidate AH artifact")
        af = ak.resolve_directory(args.af_artifact, "Candidate AF artifact")
        ai = ak.resolve_directory(args.ai_artifact, "Candidate AI artifact")
        aj = ak.resolve_directory(args.aj_artifact, "Candidate AJ artifact")

        script_dir = pathlib.Path(__file__).resolve().parent
        repository = script_dir.parents[2]
        package_pin_path = script_dir / "validate-package-pins.py"
        boot_validator_path = script_dir / "validate-boot.py"
        aj_identity = ak.load_aj_identity("candidate_ak_artifact_aj_identity")
        gate_auditor_path = aj_identity.ai_script("audit-mt6797-psci-cpu-boot.py")
        lineage_path = aj_identity.ai_script("validate-lineage.py")
        analyzer = (
            repository
            / "experiments/2026-07-12-boot-contract-recovery/scripts/"
            "analyze-lk-boot-image.py"
        )
        for path, label in (
            (package_pin_path, "Candidate AK package-pin validator"),
            (boot_validator_path, "Candidate AK Android-v0 validator"),
            (gate_auditor_path, "Candidate AI compiled-gate auditor"),
            (lineage_path, "Candidate AI lineage validator"),
            (analyzer, "source-pinned LK analyzer"),
        ):
            ak.read_regular(path, label)
        if digest_path(analyzer) != LK_ANALYZER_SHA256:
            raise ValueError("source-pinned LK analyzer changed")

        # Run the exact post-reproduction package-pin gate for both bound packages.
        for package in (first_package, second_package):
            run_capture(
                [
                    sys.executable,
                    os.fspath(package_pin_path),
                    "--package",
                    os.fspath(package),
                ],
                "Candidate AK package-pin validator",
            )
        package_manifests = {
            digest_path(first_package / MANIFEST_MEMBER),
            digest_path(second_package / MANIFEST_MEMBER),
        }
        if package_manifests != set(ak.PACKAGE_MANIFEST_SHA256S):
            raise ValueError("bound packages are not the exact two selected reproductions")

        package_reproduction = load_local_module(
            "validate-package-reproduction.py",
            "candidate_ak_artifact_package_reproduction",
        )
        package_reproduction.compare(first_package, second_package)
        package_validator = load_local_module(
            "validate-package.py", "candidate_ak_artifact_package_validator"
        )
        finalizer = load_local_module(
            "finalize-artifact.py", "candidate_ak_artifact_finalizer"
        )

        validate_exact_aj_artifact(aj)
        lineage_report = run_capture(
            [
                sys.executable,
                os.fspath(lineage_path),
                "--ad-artifact",
                os.fspath(ad),
                "--ah-artifact",
                os.fspath(ah),
                "--af-artifact",
                os.fspath(af),
            ],
            "source-pinned Candidate AI lineage validator",
        )

        first_inventory = inspect_artifact_tree(first)
        second_inventory = inspect_artifact_tree(second)
        for root in (first, second):
            if lineage_report != ak.read_regular(
                root / "lineage-validation.txt", "Candidate AK lineage record"
            ):
                raise ValueError("Candidate AK preserved AI lineage report changed")

        baselines = baseline_boots(ad, ah, af, ai, aj)
        validate_artifact(
            first,
            first_package,
            first_inventory,
            finalizer,
            package_validator,
            boot_validator_path,
            gate_auditor_path,
            analyzer,
            baselines,
        )
        validate_artifact(
            second,
            second_package,
            second_inventory,
            finalizer,
            package_validator,
            boot_validator_path,
            gate_auditor_path,
            analyzer,
            baselines,
        )
        compare_artifact_trees(first, first_inventory, second, second_inventory)
        if not args.bootstrap:
            validate_selected_identities(first_inventory)

        print("validation=candidate-ak-artifact-reproduction")
        print(f"mode={'bootstrap' if args.bootstrap else 'pinned'}")
        print(f"members={len(first_inventory)}")
        print(f"boot_sha256={first_inventory[ak.BOOT_MEMBER][2]}")
        print(f"boot_size={first_inventory[ak.BOOT_MEMBER][1]}")
        print(f"artifact_manifest_sha256={first_inventory[MANIFEST_MEMBER][2]}")
        print("artifact_bytes_identical=yes")
        print("artifact_modes_identical=yes")
        print("artifact_inventories=exact-20-members-twice")
        print("artifact_package_binding=pairwise-exact-twice")
        print("package_pins=validated-twice")
        print("android_v0=validated-twice")
        print("compiled_gate_audit=reproduced-twice")
        print("ai_lineage=validated")
        print("lk_analysis=reproduced-twice")
        print("artifact_identity_selection=bootstrap-output" if args.bootstrap else "artifact_identity_selection=pinned")
        print("independent_build_execution=requires-external-fresh-root-record")
        print("device_access=none")
        return 0
    except (
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
