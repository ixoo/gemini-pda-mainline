#!/usr/bin/env python3
"""Validate Candidate AP's compile/link-only, never-assembled PM-audit package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True

PM_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-pm-audit"
)
PM_FRAGMENT = "configs/gemini-dvfsp-i2c6-consumer-pm-audit.fragment"
PM_CONFIG_INPUTS_SHA256 = (
    "929accb0641e94f7ee84f51a25abcfd2f79dccaadb8a221b3c323160ef4b23c2"
)
PM_PACKAGE_MEMBER_COUNT = 242
REQUIRED_PM_SYMBOLS = {
    "mt6797_dvfsp_handoff_is_ready_atomic",
    "mt6797_dvfsp_handoff_validate_clock_pm",
    "mt6797_dvfsp_handoff_suspend_late",
    "mt6797_dvfsp_handoff_resume_early",
    "mtk_i2c_suspend_late",
    "mtk_i2c_resume_early",
    "mtk_i2c_suspend_noirq",
    "mtk_i2c_resume_noirq",
}
REQUIRED_PM_CONFIG = {
    "CONFIG_SUSPEND=y",
    "CONFIG_PM_SLEEP=y",
    "CONFIG_SUSPEND_FREEZER=y",
    "# CONFIG_HIBERNATION is not set",
    "# CONFIG_PM_AUTOSLEEP is not set",
    "# CONFIG_PM_USERSPACE_AUTOSLEEP is not set",
}
FORBIDDEN_PM_CONFIG = {
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_PM_SLEEP is not set",
    "CONFIG_HIBERNATION=y",
    "CONFIG_PM_AUTOSLEEP=y",
    "CONFIG_PM_USERSPACE_AUTOSLEEP=y",
}


def load_main_validator() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location(
        "candidate_ap_pm_main_package_validator", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AP main package validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pm_fragments(main: ModuleType) -> list[str]:
    return [*main.FRAGMENTS, PM_FRAGMENT]


def config_inputs_digest(
    main: ModuleType, fragments: dict[str, bytes]
) -> str:
    records = [f"profile={PM_PROFILE}\n", "base=defconfig\n"]
    for relative in pm_fragments(main):
        records.append(f"{main.digest_bytes(fragments[relative])}  {relative}\n")
    return main.digest_bytes("".join(records).encode("ascii"))


def fragment_requests(
    main: ModuleType, fragments: dict[str, bytes]
) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in pm_fragments(main):
        for number, line in enumerate(
            fragments[relative].decode("utf-8").splitlines(), 1
        ):
            if not line or line == "#" or (
                line.startswith("# ") and not line.startswith("# CONFIG_")
            ):
                continue
            if line.startswith("CONFIG_") and "=" in line:
                symbol = line.split("=", 1)[0]
            elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
                symbol = line[2:-11]
            else:
                raise ValueError(
                    f"unsupported PM fragment line {relative}:{number}: {line}"
                )
            result[symbol] = line
    return result


def validate_manifest_contract(main: ModuleType, data: bytes) -> None:
    value = main.validate_manifest_contract(data, "Candidate AP PM-audit manifest")
    profiles = value["config"]["profiles"]
    expected = {
        "base": "defconfig",
        "patch_series": main.SERIES_REL,
        "fragments": pm_fragments(main),
    }
    if profiles.get(PM_PROFILE) != expected:
        raise ValueError("exact Candidate AP PM-audit profile changed")


def validate_fragments(
    main: ModuleType,
    repository: pathlib.Path,
    package: pathlib.Path,
    members: dict[str, pathlib.Path],
) -> dict[str, bytes]:
    fragments = pm_fragments(main)
    expected_members = {
        f"provenance/configs/{pathlib.PurePosixPath(relative).name}"
        for relative in fragments
    }
    actual_members = {
        relative
        for relative in members
        if relative.startswith("provenance/configs/")
    }
    if actual_members != expected_members:
        raise ValueError("PM-audit fragment inventory changed")

    result: dict[str, bytes] = {}
    for relative in fragments:
        name = pathlib.PurePosixPath(relative).name
        repository_data = main.read_regular(
            repository / relative, f"repository PM fragment {relative}"
        )
        packaged_data = main.read_regular(
            package / "provenance/configs" / name,
            f"packaged PM fragment {name}",
        )
        if packaged_data != repository_data:
            raise ValueError(f"packaged PM fragment differs: {relative}")
        result[relative] = packaged_data
    if config_inputs_digest(main, result) != PM_CONFIG_INPUTS_SHA256:
        raise ValueError("Candidate AP PM-audit configuration-input identity changed")
    return result


def validate_resolved_config(
    main: ModuleType, data: bytes, fragments: dict[str, bytes]
) -> None:
    resolved = main.config_map(data)
    for symbol, expected in fragment_requests(main, fragments).items():
        actual = resolved.get(symbol)
        if expected.startswith("CONFIG_"):
            if actual != expected:
                raise ValueError(
                    "PM-audit resolved config lost fragment request "
                    f"{symbol}: {expected}"
                )
        elif actual is not None and actual != expected:
            raise ValueError(
                f"PM-audit resolved config enabled disabled request {symbol}"
            )

    lines = set(data.decode("utf-8").splitlines())
    required_main = {
        line for line in main.REQUIRED_CONFIG if line != "# CONFIG_SUSPEND is not set"
    }
    missing = (required_main | REQUIRED_PM_CONFIG) - lines
    if missing:
        raise ValueError(f"PM-audit config line is missing: {sorted(missing)[0]}")
    forbidden = FORBIDDEN_PM_CONFIG & lines
    if forbidden:
        raise ValueError(f"PM-audit config enables forbidden policy: {sorted(forbidden)[0]}")
    if resolved.get("CONFIG_CMDLINE") != f'CONFIG_CMDLINE="{main.CMDLINE}"':
        raise ValueError("PM-audit command line differs from installed-profile input")


def validate_build(
    main: ModuleType,
    value: dict[str, Any],
    config_data: bytes,
    package: pathlib.Path,
) -> bytes:
    expected = {
        "schema": 1,
        "kernel_release": main.KERNEL_RELEASE,
        "build_profile": PM_PROFILE,
        "base_config": "defconfig",
        "config_fragments": pm_fragments(main),
        "config_inputs_sha256": PM_CONFIG_INPUTS_SHA256,
        "source_sha256": main.SOURCE_SHA256,
        "patchset_sha256": main.PATCHSET_SHA256,
        "config_sha256": main.digest_bytes(config_data),
        "modules_built": False,
        "compiler": main.COMPILER,
        "linker": main.LINKER,
    }
    if set(value) != set(expected) | {"generated_utc"}:
        raise ValueError("PM-audit build-provenance inventory changed")
    for key, wanted in expected.items():
        if type(value.get(key)) is not type(wanted) or value.get(key) != wanted:
            raise ValueError(f"PM-audit build provenance changed: {key}")
    normalized = main.normalized_build_bytes(value, "Candidate AP PM-audit build")
    wanted_name = (
        f"linux-7.1.3-gemini-{PM_PROFILE}-{main.PATCHSET_SHA256[:8]}-"
        f"{PM_CONFIG_INPUTS_SHA256[:8]}"
    )
    if package.name != wanted_name:
        raise ValueError("PM-audit package basename disagrees with exact inputs")
    return normalized


def validate_shape(
    main: ModuleType,
    members: dict[str, pathlib.Path],
    entries: list[str],
) -> int:
    required = {
        "SHA256SUMS",
        "Image",
        "Image.gz",
        "kernel.config",
        "System.map",
        "provenance/build.json",
        "provenance/kernel-manifest.json",
        "provenance/series",
        main.GEMINI_DTB,
        *(
            f"provenance/configs/{pathlib.PurePosixPath(item).name}"
            for item in pm_fragments(main)
        ),
        *(f"provenance/patches/{entry}" for entry in entries),
    }
    missing = required - set(members)
    if missing:
        raise ValueError(f"PM-audit package lacks member: {sorted(missing)[0]}")
    for relative in set(members) - required:
        path = pathlib.PurePosixPath(relative)
        if (
            path.parent != pathlib.PurePosixPath("dtbs/mediatek")
            or path.suffix != ".dtb"
        ):
            raise ValueError(f"PM-audit package contains unexpected member: {relative}")
    dtb_count = sum(
        relative.startswith("dtbs/mediatek/") and relative.endswith(".dtb")
        for relative in members
    )
    if len(members) != PM_PACKAGE_MEMBER_COUNT or dtb_count != main.PACKAGE_DTB_COUNT:
        raise ValueError(
            "PM-audit package inventory changed: "
            f"members={len(members)}, dtbs={dtb_count}"
        )
    return dtb_count


def validate_compiled_pm(
    main: ModuleType, package: pathlib.Path, system_map: bytes
) -> bytes:
    symbols = main.system_map_symbols(system_map)
    missing = REQUIRED_PM_SYMBOLS - symbols
    if missing:
        raise ValueError(f"PM-audit System.map lacks callback: {sorted(missing)[0]}")
    auditor = main.load_handoff_auditor()
    report = auditor.audit_kernel(
        package / "Image",
        package / "System.map",
        expect_pm=True,
    )
    expected = {
        *(
            set(main.REQUIRED_HANDOFF_AUDIT_SEMANTICS)
            - {b"pm_callbacks=disabled-config\n"}
        ),
        b"pm_callbacks=linked-call-order-plus-source-pinned-guards\n",
    }
    for required in expected:
        if required not in report:
            raise ValueError(f"PM-audit compiled report lacks: {required!r}")
    return report


def validate_package(
    main: ModuleType, repository: pathlib.Path, package: pathlib.Path
) -> dict[str, str | int]:
    members = main.validate_package_manifest(package)
    repository_manifest = main.read_regular(
        repository / "kernel/manifest.json", "repository kernel manifest"
    )
    packaged_manifest = main.read_regular(
        package / "provenance/kernel-manifest.json",
        "packaged PM-audit kernel manifest",
    )
    if packaged_manifest != repository_manifest:
        raise ValueError("packaged PM-audit manifest differs from repository")
    validate_manifest_contract(main, repository_manifest)

    entries = main.validate_series(repository, package, members)
    dtb_count = validate_shape(main, members, entries)
    fragments = validate_fragments(main, repository, package, members)
    config = main.read_regular(package / "kernel.config", "PM-audit config")
    validate_resolved_config(main, config, fragments)
    build = main.load_json(package / "provenance/build.json", "PM-audit build")
    normalized = validate_build(main, build, config, package)

    image = main.read_regular(package / "Image", "PM-audit Image")
    image_gz = main.read_regular(package / "Image.gz", "PM-audit Image.gz")
    if main.decompress_lk_image_gz(image_gz, "PM-audit Image.gz") != image:
        raise ValueError("PM-audit Image.gz does not expand to exact Image")
    main.validate_image(image, config)
    system_map = main.read_regular(package / "System.map", "PM-audit System.map")
    main.validate_system_map(system_map)
    gate_report = main.validate_compiled_gate(package)
    pm_report = validate_compiled_pm(main, package, system_map)
    main.validate_package_dtb(package / main.GEMINI_DTB)

    return {
        "members": len(members),
        "dtbs": dtb_count,
        "package_manifest_sha256": main.digest_path(package / "SHA256SUMS"),
        "normalized_build_sha256": main.digest_bytes(normalized),
        "config_sha256": main.digest_bytes(config),
        "image_sha256": main.digest_bytes(image),
        "image_gz_sha256": main.digest_bytes(image_gz),
        "system_map_sha256": main.digest_bytes(system_map),
        "compiled_gate_audit_sha256": main.digest_bytes(gate_report),
        "compiled_pm_audit_sha256": main.digest_bytes(pm_report),
        "package_dtb_sha256": main.digest_path(package / main.GEMINI_DTB),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validator = load_main_validator()
        repository = validator.resolve_directory(args.repository, "repository")
        package = validator.resolve_directory(args.package, "PM-audit package")
        calibration = validate_package(validator, repository, package)
        print("validation=candidate-ap-pm-audit-package")
        print(f"profile={PM_PROFILE}")
        print(f"series_path={validator.SERIES_REL}")
        print(f"config_inputs_sha256={PM_CONFIG_INPUTS_SHA256}")
        print("system_sleep_callbacks=compiled-linked-and-ordered")
        print("installed_profile_suspend=disabled")
        print("artifact_assembly=forbidden")
        print("device_install=forbidden")
        print("device_boot=forbidden")
        for key, value in calibration.items():
            print(f"calibration_{key}={value}")
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
