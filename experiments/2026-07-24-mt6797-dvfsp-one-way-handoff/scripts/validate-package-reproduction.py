#!/usr/bin/env python3
"""Compare AO packages and tie each one to a distinct surviving live build."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import stat
import struct
import sys
import zlib
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True
DYNAMIC_MEMBERS = {"SHA256SUMS", "provenance/build.json"}
LIVE_OUTPUTS = {
    "Image": "arch/arm64/boot/Image",
    "Image.gz": "arch/arm64/boot/Image.gz",
    "kernel.config": ".config",
    "System.map": "System.map",
}
LIVE_ROOT_LABELS = (
    "first source",
    "first build",
    "first artifacts",
    "second source",
    "second build",
    "second artifacts",
)
REPRODUCED_CALIBRATION_KEYS = (
    "normalized_build_sha256",
    "config_sha256",
    "image_sha256",
    "image_size",
    "image_gz_sha256",
    "image_gz_size",
    "system_map_sha256",
    "compiled_gate_audit_sha256",
    "compiled_handoff_audit_sha256",
    "package_dtb_sha256",
)


def load_validator() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location(
        "candidate_ao_package_validator", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AO package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_source_state(validator: ModuleType) -> str:
    return digest_bytes(
        (
            "7.1.3\n"
            f"{validator.SOURCE_SHA256}\n"
            f"{validator.PATCHSET_SHA256}\n"
        ).encode("ascii")
    )


def expected_build_state(validator: ModuleType) -> str:
    source_state = expected_source_state(validator)
    gcc_version = validator.COMPILER.rsplit(maxsplit=1)[-1]
    return digest_bytes(
        (
            f"{source_state}\n"
            f"{validator.CONFIG_INPUTS_SHA256}\n"
            f"{gcc_version}\n"
            f"{validator.LINKER}\n"
        ).encode("ascii")
    )


def live_dtb_inventory(root: pathlib.Path, label: str) -> dict[str, pathlib.Path]:
    output: dict[str, pathlib.Path] = {}
    for path in root.rglob("*.dtb"):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
            raise ValueError(f"{label} contains unsafe DTB output: {relative}")
        output[relative] = path
    if not output:
        raise ValueError(f"{label} has no MediaTek DTB outputs")
    return output


def validate_live_build(
    validator: ModuleType,
    package: pathlib.Path,
    source_dir: pathlib.Path,
    build_dir: pathlib.Path,
    artifact_root: pathlib.Path,
    label: str,
) -> dict[str, str]:
    if package.parent != artifact_root:
        raise ValueError(f"{label} package is not an exact child of its artifact root")

    wanted_source_state = expected_source_state(validator)
    wanted_build_state = expected_build_state(validator)
    if validator.read_regular(
        source_dir / ".gemini-source-state", f"{label} source state"
    ) != f"{wanted_source_state}\n".encode("ascii"):
        raise ValueError(f"{label} live source-state identity changed")
    if validator.read_regular(
        build_dir / ".gemini-build-state", f"{label} build state"
    ) != f"{wanted_build_state}\n".encode("ascii"):
        raise ValueError(f"{label} live build-state identity changed")

    for member, relative in LIVE_OUTPUTS.items():
        package_data = validator.read_regular(
            package / member, f"{label} package {member}"
        )
        live_data = validator.read_regular(
            build_dir / relative, f"{label} live {relative}"
        )
        if package_data != live_data:
            raise ValueError(
                f"{label} package member is not exact live build output: {member}"
            )

    package_dtbs = {
        relative.removeprefix("dtbs/mediatek/"): path
        for relative, path in validator.inventory(package).items()
        if relative.startswith("dtbs/mediatek/") and relative.endswith(".dtb")
    }
    live_dtb_root = build_dir / "arch/arm64/boot/dts/mediatek"
    live_dtbs = live_dtb_inventory(live_dtb_root, f"{label} live build")
    if set(package_dtbs) != set(live_dtbs):
        missing = sorted(set(live_dtbs) - set(package_dtbs))
        extra = sorted(set(package_dtbs) - set(live_dtbs))
        raise ValueError(
            f"{label} packaged/live DTB inventories differ: "
            f"missing={missing[:1]}, extra={extra[:1]}"
        )
    for relative in sorted(live_dtbs):
        if validator.read_regular(
            package_dtbs[relative], f"{label} package DTB {relative}"
        ) != validator.read_regular(
            live_dtbs[relative], f"{label} live DTB {relative}"
        ):
            raise ValueError(
                f"{label} package DTB is not exact live build output: {relative}"
            )

    return {
        "source_state_sha256": wanted_source_state,
        "build_state_sha256": wanted_build_state,
        "live_dtb_inventory_sha256": digest_bytes(
            "".join(f"{relative}\n" for relative in sorted(live_dtbs)).encode(
                "utf-8"
            )
        ),
    }


def require_distinct_live_roots(paths: dict[str, pathlib.Path]) -> None:
    if set(paths) != set(LIVE_ROOT_LABELS):
        raise ValueError("independent build-root inventory changed")
    items = list(paths.items())
    for index, (left_label, left) in enumerate(items):
        for right_label, right in items[index + 1 :]:
            if (
                left == right
                or left.samefile(right)
                or left in right.parents
                or right in left.parents
            ):
                raise ValueError(
                    "independent build roots alias or overlap: "
                    f"{left_label} and {right_label}"
                )


def normalized_build(
    validator: ModuleType, path: pathlib.Path, label: str
) -> tuple[bytes, str]:
    value = validator.load_json(path, f"{label} build provenance")
    generated = value.get("generated_utc")
    normalized = validator.normalized_build_bytes(value, f"{label} build")
    if not isinstance(generated, str):
        raise ValueError(f"{label} build generation timestamp is malformed")
    return normalized, generated


def compare_packages(
    validator: ModuleType,
    first: pathlib.Path,
    second: pathlib.Path,
) -> dict[str, pathlib.Path]:
    if first == second or first.samefile(second):
        raise ValueError("reproduction requires two distinct package trees")
    left = validator.validate_package_manifest(first)
    right = validator.validate_package_manifest(second)
    if set(left) != set(right):
        raise ValueError("Candidate AO package inventories differ")

    changed: set[str] = set()
    for relative in sorted(left):
        left_mode = stat.S_IMODE(left[relative].lstat().st_mode)
        right_mode = stat.S_IMODE(right[relative].lstat().st_mode)
        if left_mode != right_mode:
            raise ValueError(f"reproduced package mode differs: {relative}")
        if left[relative].read_bytes() != right[relative].read_bytes():
            changed.add(relative)
    if changed != DYNAMIC_MEMBERS:
        raise ValueError(
            "package differences are not only generated_utc and its manifest: "
            f"unexpected={sorted(changed - DYNAMIC_MEMBERS)}, "
            f"missing={sorted(DYNAMIC_MEMBERS - changed)}"
        )

    left_build, left_generated = normalized_build(
        validator, first / "provenance/build.json", "first"
    )
    right_build, right_generated = normalized_build(
        validator, second / "provenance/build.json", "second"
    )
    if left_build != right_build:
        raise ValueError("normalized Candidate AO build provenance differs")
    if left_generated == right_generated:
        raise ValueError(
            "package generation timestamps are identical; independent execution "
            "is not attributable"
        )

    left_manifest = validator.manifest_map(first / "SHA256SUMS")
    right_manifest = validator.manifest_map(second / "SHA256SUMS")
    if set(left_manifest) != set(right_manifest):
        raise ValueError("Candidate AO manifest inventories differ")
    changed_entries = {
        relative
        for relative in left_manifest
        if left_manifest[relative] != right_manifest[relative]
    }
    if changed_entries != {"provenance/build.json"}:
        raise ValueError(
            "Candidate AO manifests differ outside generated build provenance"
        )
    if (
        left_manifest["provenance/build.json"]
        != digest_bytes(left["provenance/build.json"].read_bytes())
        or right_manifest["provenance/build.json"]
        != digest_bytes(right["provenance/build.json"].read_bytes())
    ):
        raise ValueError("Candidate AO manifest build entries are inconsistent")
    return left


def validate_reproduction(
    validator: ModuleType,
    repository: pathlib.Path,
    first: pathlib.Path,
    second: pathlib.Path,
    live_roots: dict[str, pathlib.Path],
) -> tuple[
    dict[str, str | int],
    dict[str, str | int],
    dict[str, pathlib.Path],
    dict[str, str],
]:
    require_distinct_live_roots(live_roots)
    first_calibration = validator.validate_package(repository, first)
    second_calibration = validator.validate_package(repository, second)
    members = compare_packages(validator, first, second)
    first_live = validate_live_build(
        validator,
        first,
        live_roots["first source"],
        live_roots["first build"],
        live_roots["first artifacts"],
        "first",
    )
    second_live = validate_live_build(
        validator,
        second,
        live_roots["second source"],
        live_roots["second build"],
        live_roots["second artifacts"],
        "second",
    )
    if first_live != second_live:
        raise ValueError("independent live build state or DTB inventory differs")
    for key in REPRODUCED_CALIBRATION_KEYS:
        if first_calibration[key] != second_calibration[key]:
            raise ValueError(f"reproduced calibration differs: {key}")
    return first_calibration, second_calibration, members, first_live


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=pathlib.Path, required=True)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--first-source-dir", type=pathlib.Path, required=True)
    parser.add_argument("--first-build-dir", type=pathlib.Path, required=True)
    parser.add_argument("--first-artifact-root", type=pathlib.Path, required=True)
    parser.add_argument("--second-source-dir", type=pathlib.Path, required=True)
    parser.add_argument("--second-build-dir", type=pathlib.Path, required=True)
    parser.add_argument("--second-artifact-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        validator = load_validator()
        repository = validator.resolve_directory(args.repository, "repository")
        first = validator.resolve_directory(args.first, "first Candidate AO package")
        second = validator.resolve_directory(
            args.second, "second Candidate AO package"
        )
        live_roots = {
            "first source": validator.resolve_directory(
                args.first_source_dir, "first live source"
            ),
            "first build": validator.resolve_directory(
                args.first_build_dir, "first live build"
            ),
            "first artifacts": validator.resolve_directory(
                args.first_artifact_root, "first live artifact root"
            ),
            "second source": validator.resolve_directory(
                args.second_source_dir, "second live source"
            ),
            "second build": validator.resolve_directory(
                args.second_build_dir, "second live build"
            ),
            "second artifacts": validator.resolve_directory(
                args.second_artifact_root, "second live artifact root"
            ),
        }
        first_calibration, _, members, first_live = validate_reproduction(
            validator, repository, first, second, live_roots
        )

        normalized, _ = normalized_build(
            validator, first / "provenance/build.json", "first"
        )
        print("validation=candidate-ao-package-reproduction-calibration")
        print(f"profile={validator.PROFILE}")
        print(f"members={len(members)}")
        print("substantive_bytes_identical=yes")
        print("modes_identical=yes")
        print("normalized_build_provenance=identical")
        print("generation_timestamps=distinct")
        print("only_permitted_difference=generated_utc-and-derived-manifest-entry")
        print("live_source_roots=distinct-and-state-linked")
        print("live_build_roots=distinct-and-state-linked")
        print("live_artifact_roots=distinct-and-package-linked")
        print("live_outputs=exact-package-members")
        print("live_dtb_inventory_and_bytes=exact-package-members")
        print(f"source_state_sha256={first_live['source_state_sha256']}")
        print(f"build_state_sha256={first_live['build_state_sha256']}")
        print(
            "live_dtb_inventory_sha256="
            f"{first_live['live_dtb_inventory_sha256']}"
        )
        print(
            "calibration_package_manifest_sha256_first="
            f"{validator.digest_path(first / 'SHA256SUMS')}"
        )
        print(
            "calibration_package_manifest_sha256_second="
            f"{validator.digest_path(second / 'SHA256SUMS')}"
        )
        print(f"calibration_normalized_build_sha256={digest_bytes(normalized)}")
        for key in REPRODUCED_CALIBRATION_KEYS[1:]:
            print(f"calibration_{key}={first_calibration[key]}")
        print("output_hashes_pinned=no")
        print("independent_build_execution=distinct-live-roots-linked")
        print("historical_root_absence=requires-external-preflight-record")
        print("artifact_build=none")
        print("device_access=none")
        print("storage_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
