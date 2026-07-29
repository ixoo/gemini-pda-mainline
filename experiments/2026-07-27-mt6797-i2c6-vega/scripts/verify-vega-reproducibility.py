#!/usr/bin/env python3
"""Verify two Vega packages and their complete 2x2 candidate matrix offline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import sys
from dataclasses import dataclass
from types import ModuleType

sys.dont_write_bytecode = True


class ContractError(ValueError):
    """A reproducibility input or result was not exact."""


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CANDIDATE_MODULE_SHA256 = (
    "225d134cf36cd025162bf99ef3a3ea0ad83c462b43577b95f933a3b297f0d379"
)
PACKAGE_VALIDATOR_SHA256 = (
    "ef07f12d82c4db233f30a535500e0a688bcb13228b94fea7f8618fa4a6344eee"
)
LK_ANALYZER_RELATIVE = pathlib.Path(
    "experiments/2026-07-12-boot-contract-recovery/"
    "scripts/analyze-lk-boot-image.py"
)
LK_ANALYZER_SHA256 = (
    "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
)
LK_EXPECTED_NAME = "gemini-vega"
LK_EXPECTED_CMDLINE = "bootopt=64S3,32N2,64N2"
LK_GATE_COUNT = 32


def source_bytes(path: pathlib.Path, wanted_sha256: str, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} is missing or unsafe") from exc
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ContractError(f"{label} is missing, empty, or unsafe")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != wanted_sha256:
        raise ContractError(f"{label} source identity changed")
    return data


def load_source_pinned_module(
    path: pathlib.Path,
    wanted_sha256: str,
    label: str,
    module_name: str,
) -> ModuleType:
    data = source_bytes(path, wanted_sha256, label)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        exec(compile(data, os.fspath(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


co = load_source_pinned_module(
    SCRIPT_DIR / "candidate_vega.py",
    CANDIDATE_MODULE_SHA256,
    "Vega candidate contract",
    "candidate_vega",
)


DYNAMIC_PACKAGE_MEMBERS = frozenset(
    {
        "SHA256SUMS",
        "provenance/build.json",
    }
)
MATRIX_LANES = (
    "package-a/cassini-a",
    "package-a/cassini-b",
    "package-b/cassini-a",
    "package-b/cassini-b",
)


@dataclass(frozen=True)
class InventoryMember:
    mode: int
    size: int
    sha256: str


@dataclass(frozen=True)
class PackageResult:
    directory_name: str
    manifest_sha256: str
    generated_utc: str
    normalized_build: bytes
    normalized_inventory: dict[str, InventoryMember]


@dataclass(frozen=True)
class CandidateResult:
    directory_name: str
    inventory: dict[str, InventoryMember]
    raw_size: int
    raw_sha256: str
    padded_sha256: str
    manifest_sha256: str
    analysis_sha256: str


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ContractError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ContractError(f"{label} is missing or unsafe")
    return path


def inventory(root: pathlib.Path, label: str) -> dict[str, InventoryMember]:
    directory(root, label)
    members: dict[str, InventoryMember] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink():
            raise ContractError(f"{label} contains symlink: {relative}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or not info.st_size:
            raise ContractError(f"{label} contains unsafe member: {relative}")
        members[relative] = InventoryMember(
            mode=stat.S_IMODE(info.st_mode),
            size=info.st_size,
            sha256=digest(path.read_bytes()),
        )
    if not members:
        raise ContractError(f"{label} inventory is empty")
    return members


def inventory_digest(members: dict[str, InventoryMember]) -> str:
    lines = [
        f"{relative}\t{member.mode:04o}\t{member.size}\t{member.sha256}\n"
        for relative, member in sorted(members.items())
    ]
    return digest("".join(lines).encode("ascii"))


def require_distinct_lanes(
    packages: tuple[pathlib.Path, ...],
    candidates: tuple[pathlib.Path, ...],
) -> None:
    if len(packages) != 2 or len(candidates) != 4:
        raise ContractError("Vega reproducibility requires two package lanes and four matrix lanes")
    package_paths = tuple(path.resolve(strict=True) for path in packages)
    candidate_paths = tuple(path.resolve(strict=True) for path in candidates)
    if len(set(package_paths)) != 2:
        raise ContractError("Vega package lanes are not distinct")
    if len(set(candidate_paths)) != 4:
        raise ContractError("Vega candidate matrix lanes are not distinct")
    if set(package_paths) & set(candidate_paths):
        raise ContractError("Vega package and candidate lanes overlap")


def require_identical(
    label: str,
    values: tuple[object, ...],
) -> object:
    if not values or any(value != values[0] for value in values[1:]):
        raise ContractError(f"{label} mismatch")
    return values[0]


def load_package_validator() -> ModuleType:
    return load_source_pinned_module(
        SCRIPT_DIR / "validate-package-vega.py",
        PACKAGE_VALIDATOR_SHA256,
        "Vega package validator",
        "vega_reproducibility_package_validator",
    )


def load_lk_analyzer(repository: pathlib.Path) -> ModuleType:
    return load_source_pinned_module(
        repository / LK_ANALYZER_RELATIVE,
        LK_ANALYZER_SHA256,
        "Gemini LK analyzer",
        "vega_reproducibility_lk_analyzer",
    )


def verify_checksum_manifest(
    root: pathlib.Path,
    members: dict[str, InventoryMember],
    label: str,
) -> str:
    manifest = regular(root / "SHA256SUMS", f"{label} checksum manifest")
    seen: set[str] = set()
    for line in manifest.decode("ascii").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise ContractError(f"{label} checksum line is malformed")
        wanted = line[:64]
        name = line[66:]
        if not name.startswith("./"):
            raise ContractError(f"{label} checksum path is not canonical")
        relative = name[2:]
        path = pathlib.PurePosixPath(relative)
        if (
            len(wanted) != 64
            or any(character not in "0123456789abcdef" for character in wanted)
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != relative
            or relative == "SHA256SUMS"
            or relative in seen
        ):
            raise ContractError(f"{label} checksum entry is unsafe")
        seen.add(relative)
        if relative not in members or members[relative].sha256 != wanted:
            raise ContractError(f"{label} checksum failed: {relative}")
    if seen != set(members) - {"SHA256SUMS"}:
        raise ContractError(f"{label} checksum inventory is incomplete")
    return digest(manifest)


def normalize_build(path: pathlib.Path) -> tuple[bytes, str]:
    try:
        build = json.loads(regular(path, "package build provenance"))
    except json.JSONDecodeError as exc:
        raise ContractError("package build provenance is not valid JSON") from exc
    generated_utc = build.pop("generated_utc", None)
    if not isinstance(generated_utc, str) or not generated_utc:
        raise ContractError("package build provenance lacks generated_utc")
    if set(build).intersection({"build_dir", "source_dir", "artifact_dir"}):
        raise ContractError("package build provenance contains host paths")
    normalized = (json.dumps(build, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return normalized, generated_utc


def verify_package(
    repository: pathlib.Path,
    package: pathlib.Path,
    validator: ModuleType,
    label: str,
) -> PackageResult:
    validator.validate(repository, package)
    members = inventory(package, label)
    manifest_sha256 = verify_checksum_manifest(package, members, label)
    normalized_build, generated_utc = normalize_build(
        package / "provenance/build.json"
    )
    normalized_inventory = {
        relative: member
        for relative, member in members.items()
        if relative not in DYNAMIC_PACKAGE_MEMBERS
    }
    if len(normalized_inventory) + len(DYNAMIC_PACKAGE_MEMBERS) != len(members):
        raise ContractError(f"{label} dynamic inventory changed")
    return PackageResult(
        directory_name=package.name,
        manifest_sha256=manifest_sha256,
        generated_utc=generated_utc,
        normalized_build=normalized_build,
        normalized_inventory=normalized_inventory,
    )


def verify_lk_artifact(
    raw: pathlib.Path,
    image_gz: pathlib.Path,
    initramfs: pathlib.Path,
    dtb: pathlib.Path,
    analysis: pathlib.Path,
    analyzer: ModuleType,
    label: str,
) -> str:
    try:
        result, failures = analyzer.parse(
            raw,
            expected_dtb=dtb,
            expected_image_gz=image_gz,
            expected_ramdisk=initramfs,
            expected_name=LK_EXPECTED_NAME,
            expected_cmdline=LK_EXPECTED_CMDLINE,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ContractError(f"{label} LK analysis failed") from exc
    gates = {
        key: value
        for key, value in result.items()
        if key.startswith("gate_")
    }
    if (
        failures
        or len(gates) != LK_GATE_COUNT
        or set(gates.values()) != {"yes"}
        or result.get("lk_validation") != "passed"
        or result.get("lk_validation_failures") != "none"
    ):
        raise ContractError(f"{label} failed the source-pinned LK gates")
    reproduced = (
        "".join(f"{key}={value}\n" for key, value in result.items())
        + "hardware_write=none\n"
    ).encode("ascii")
    if regular(analysis, f"{label} LK analysis") != reproduced:
        raise ContractError(f"{label} stored LK analysis is not reproducible")
    return digest(reproduced)


def verify_padded_construction(
    raw: pathlib.Path,
    padded: pathlib.Path,
    raw_size: int,
    padded_size: int,
    label: str,
) -> None:
    if not 0 < raw_size <= padded_size:
        raise ContractError(f"{label} raw and padded sizes are invalid")
    with raw.open("rb") as raw_stream, padded.open("rb") as padded_stream:
        remaining = raw_size
        while remaining:
            expected = raw_stream.read(min(1024 * 1024, remaining))
            actual = padded_stream.read(len(expected))
            if not expected or actual != expected:
                raise ContractError(f"{label} padded prefix differs from raw image")
            remaining -= len(expected)
        if raw_stream.read(1):
            raise ContractError(f"{label} raw image size changed during validation")
        tail_size = 0
        while True:
            block = padded_stream.read(1024 * 1024)
            if not block:
                break
            tail_size += len(block)
            if any(block):
                raise ContractError(f"{label} padded tail is not all zero")
    if tail_size != padded_size - raw_size:
        raise ContractError(f"{label} padded image size changed during validation")


def verify_candidate(
    candidate: pathlib.Path,
    package: pathlib.Path,
    normalized_build: bytes,
    analyzer: ModuleType,
    label: str,
) -> CandidateResult:
    members = inventory(candidate, label)
    manifest_sha256 = verify_checksum_manifest(candidate, members, label)
    required = {
        co.BOOT_MEMBER,
        co.PADDED_MEMBER,
        co.DTB_MEMBER,
        co.INITRAMFS_MEMBER,
        "Image.gz",
        "System.map",
        "analysis.txt",
        "kernel.config",
        "source-build.json",
        "provenance.txt",
    }
    if not required <= set(members):
        raise ContractError(f"{label} required inventory changed")
    if regular(candidate / "source-build.json", f"{label} normalized build") != (
        normalized_build
    ):
        raise ContractError(f"{label} normalized build does not match its package")
    for member in ("Image.gz", "System.map", "kernel.config"):
        if regular(candidate / member, f"{label} {member}") != regular(
            package / member,
            f"{label} source package {member}",
        ):
            raise ContractError(f"{label} package payload changed: {member}")
    if members[co.DTB_MEMBER].sha256 != co.ORION_BOOT_DTB_SHA256:
        raise ContractError(f"{label} boot DT differs from exact Orion")
    if members[co.INITRAMFS_MEMBER].sha256 != co.HUBBLE_INITRAMFS_SHA256:
        raise ContractError(f"{label} initramfs differs from exact Hubble")
    raw = members[co.BOOT_MEMBER]
    padded = members[co.PADDED_MEMBER]
    if padded.size != co.BOOT2_SIZE:
        raise ContractError(f"{label} padded boot2 size changed")
    analysis_sha256 = verify_lk_artifact(
        candidate / co.BOOT_MEMBER,
        candidate / "Image.gz",
        candidate / co.INITRAMFS_MEMBER,
        candidate / co.DTB_MEMBER,
        candidate / "analysis.txt",
        analyzer,
        label,
    )
    verify_padded_construction(
        candidate / co.BOOT_MEMBER,
        candidate / co.PADDED_MEMBER,
        raw.size,
        padded.size,
        label,
    )
    expected_name = f"{co.ARTIFACT_PREFIX}{raw.sha256[:8]}"
    if candidate.name != expected_name:
        raise ContractError(f"{label} directory name is not content-addressed")
    provenance = regular(
        candidate / "provenance.txt",
        f"{label} provenance",
    ).decode("ascii")
    required_provenance = (
        f"experiment={co.EXPERIMENT}\n",
        "candidate=Vega\n",
        f"kernel_profile={co.PROFILE}\n",
        f"patch_series={co.SERIES}\n",
        f"candidate_raw_sha256={raw.sha256}\n",
        f"candidate_raw_size={raw.size}\n",
        f"candidate_padded_boot2_sha256={padded.sha256}\n",
        "runtime_result=not-tested\n",
    )
    for marker in required_provenance:
        if provenance.count(marker) != 1:
            raise ContractError(f"{label} provenance marker changed: {marker.strip()}")
    return CandidateResult(
        directory_name=candidate.name,
        inventory=members,
        raw_size=raw.size,
        raw_sha256=raw.sha256,
        padded_sha256=padded.sha256,
        manifest_sha256=manifest_sha256,
        analysis_sha256=analysis_sha256,
    )


def render_record(
    verifier_sha256: str,
    packages: tuple[PackageResult, PackageResult],
    candidates: tuple[
        CandidateResult,
        CandidateResult,
        CandidateResult,
        CandidateResult,
    ],
) -> bytes:
    package_name = require_identical(
        "Vega package directory identity",
        tuple(result.directory_name for result in packages),
    )
    package_inventory = require_identical(
        "Vega normalized package mode-byte inventory",
        tuple(result.normalized_inventory for result in packages),
    )
    normalized_build = require_identical(
        "Vega normalized build provenance",
        tuple(result.normalized_build for result in packages),
    )
    if packages[0].generated_utc == packages[1].generated_utc:
        raise ContractError("Vega package lanes do not have distinct build timestamps")
    candidate_name = require_identical(
        "Vega candidate directory identity",
        tuple(result.directory_name for result in candidates),
    )
    candidate_inventory = require_identical(
        "Vega candidate mode-byte inventory",
        tuple(result.inventory for result in candidates),
    )
    raw_size = require_identical(
        "Vega candidate raw size",
        tuple(result.raw_size for result in candidates),
    )
    raw_sha256 = require_identical(
        "Vega candidate raw identity",
        tuple(result.raw_sha256 for result in candidates),
    )
    padded_sha256 = require_identical(
        "Vega candidate padded identity",
        tuple(result.padded_sha256 for result in candidates),
    )
    manifest_sha256 = require_identical(
        "Vega candidate manifest identity",
        tuple(result.manifest_sha256 for result in candidates),
    )
    analysis_sha256 = require_identical(
        "Vega candidate LK analysis identity",
        tuple(result.analysis_sha256 for result in candidates),
    )
    package_inventory_sha256 = inventory_digest(package_inventory)
    normalized_build_sha256 = digest(normalized_build)
    candidate_inventory_sha256 = inventory_digest(candidate_inventory)
    lines = (
        "validation=vega-two-build-2x2-reproducibility",
        f"experiment={co.EXPERIMENT}",
        f"verifier_sha256={verifier_sha256}",
        f"candidate_module_sha256={CANDIDATE_MODULE_SHA256}",
        f"package_validator_sha256={PACKAGE_VALIDATOR_SHA256}",
        f"lk_analyzer_sha256={LK_ANALYZER_SHA256}",
        "package_lane_count=2",
        "candidate_lane_count=4",
        "matrix=" + ",".join(MATRIX_LANES),
        f"package_directory_name={package_name}",
        f"package_a_manifest_sha256={packages[0].manifest_sha256}",
        f"package_b_manifest_sha256={packages[1].manifest_sha256}",
        f"package_a_generated_utc={packages[0].generated_utc}",
        f"package_b_generated_utc={packages[1].generated_utc}",
        f"package_normalized_file_count={len(package_inventory)}",
        f"package_normalized_inventory_sha256={package_inventory_sha256}",
        f"package_a_normalized_inventory_sha256={package_inventory_sha256}",
        f"package_b_normalized_inventory_sha256={package_inventory_sha256}",
        f"package_normalized_build_sha256={normalized_build_sha256}",
        f"package_a_normalized_build_sha256={normalized_build_sha256}",
        f"package_b_normalized_build_sha256={normalized_build_sha256}",
        f"candidate_directory_name={candidate_name}",
        f"candidate_file_count={len(candidate_inventory)}",
        f"candidate_inventory_sha256={candidate_inventory_sha256}",
        f"candidate_a_a_inventory_sha256={candidate_inventory_sha256}",
        f"candidate_a_b_inventory_sha256={candidate_inventory_sha256}",
        f"candidate_b_a_inventory_sha256={candidate_inventory_sha256}",
        f"candidate_b_b_inventory_sha256={candidate_inventory_sha256}",
        f"candidate_raw_member={co.BOOT_MEMBER}",
        f"candidate_raw_size={raw_size}",
        f"candidate_raw_sha256={raw_sha256}",
        f"candidate_padded_member={co.PADDED_MEMBER}",
        f"candidate_padded_size={co.BOOT2_SIZE}",
        f"candidate_padded_sha256={padded_sha256}",
        f"candidate_manifest_sha256={manifest_sha256}",
        f"candidate_boot_dtb_sha256={co.ORION_BOOT_DTB_SHA256}",
        f"candidate_initramfs_sha256={co.HUBBLE_INITRAMFS_SHA256}",
        f"candidate_lk_analysis_sha256={analysis_sha256}",
        "package_a_candidate_lanes=2",
        "package_b_candidate_lanes=2",
        "package_mode_byte_equality=exact",
        "candidate_mode_byte_equality=exact",
        "normalized_build_provenance=exact-except-generated_utc",
        "candidate_lk_validation=source-pinned-32-gates",
        "candidate_padded_construction=raw-prefix-zero-tail",
        "device_access=none",
        "runtime_result=not-tested",
    )
    return ("\n".join(lines) + "\n").encode("ascii")


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ContractError("reproducibility-record output is invalid or exists")
    directory(path.parent, "reproducibility-record output parent")
    return path.parent.resolve(strict=True) / path.name


def write_output(path: pathlib.Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def verify(
    repository: pathlib.Path,
    packages: tuple[pathlib.Path, pathlib.Path],
    candidates: tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path],
) -> bytes:
    require_distinct_lanes(packages, candidates)
    validator = load_package_validator()
    analyzer = load_lk_analyzer(repository)
    package_results = (
        verify_package(repository, packages[0], validator, "Vega package A"),
        verify_package(repository, packages[1], validator, "Vega package B"),
    )
    candidate_results = (
        verify_candidate(
            candidates[0],
            packages[0],
            package_results[0].normalized_build,
            analyzer,
            "Vega package-A/Cassini-A candidate",
        ),
        verify_candidate(
            candidates[1],
            packages[0],
            package_results[0].normalized_build,
            analyzer,
            "Vega package-A/Cassini-B candidate",
        ),
        verify_candidate(
            candidates[2],
            packages[1],
            package_results[1].normalized_build,
            analyzer,
            "Vega package-B/Cassini-A candidate",
        ),
        verify_candidate(
            candidates[3],
            packages[1],
            package_results[1].normalized_build,
            analyzer,
            "Vega package-B/Cassini-B candidate",
        ),
    )
    verifier_sha256 = digest(pathlib.Path(__file__).read_bytes())
    return render_record(verifier_sha256, package_results, candidate_results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--package-a", required=True, type=pathlib.Path)
    parser.add_argument("--package-b", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-a-a", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-a-b", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-b-a", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-b-b", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = args.repository.resolve(strict=True)
        packages = (
            args.package_a.resolve(strict=True),
            args.package_b.resolve(strict=True),
        )
        candidates = (
            args.candidate_a_a.resolve(strict=True),
            args.candidate_a_b.resolve(strict=True),
            args.candidate_b_a.resolve(strict=True),
            args.candidate_b_b.resolve(strict=True),
        )
        output = validate_output(args.output)
        record = verify(repository, packages, candidates)
        write_output(output, record)
        print(record.decode("ascii"), end="")
        print(f"record_sha256={digest(record)}")
        print(f"output={output}")
        return 0
    except (
        ContractError,
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
