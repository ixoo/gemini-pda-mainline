#!/usr/bin/env python3
"""Validate Candidate AF's one-symbol config delta from exact Candidate AE."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import re
import stat
import sys
from typing import Any


PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-observer-initcall-blacklist"
)
BASELINE_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-observer"
)
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
AE_PATCHSET_SHA256 = "7e675c84798314651c46109e5161cf62190445acaa9272502edf094523245e67"
AE_CONFIG_SHA256 = "bdece76d4b23bfe2e14cc01dc0981b0123109bd206f1016bb4d73fe37c7de9bb"
AE_IMAGE_GZ_SHA256 = "4c04a781080fc2dbb8557e967fd0d4e8e198bcd6a7c4982f38a20aa3e191b96f"
AE_DTB_SHA256 = "3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b"
AE_SOURCE_BUILD_SHA256 = "b61e539bf4d67710f3ef5557055a878b49e6f099477f3e0e508dfc153b052c1e"
AE_CONFIG_INPUTS_SHA256 = "962e77cf4f8ebe502402b50486d9628db946f65301297fcfbefe7086f604208c"
AF_CONFIG_INPUTS_SHA256 = "f109158b6d3681d21afce8a7cb997ce89f0c4fdfe3b213ac3d890ff47f668b36"
KERNEL_RELEASE = "7.1.3-gemini-observability-L"
COMPILER = "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
LINKER = "GNU ld (GNU Binutils for Ubuntu) 2.42"
FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-observer.fragment",
    "configs/gemini-a72-observer-initcall-blacklist.fragment",
]
AE_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused"
)
BLACKLIST_TOKEN = "initcall_blacklist=mt6797_a72_power_driver_init"
AF_CMDLINE = f"{AE_CMDLINE} {BLACKLIST_TOKEN}"
REQUIRED_CONFIG = {
    "CONFIG_REGULATOR_DA9211=y",
    "CONFIG_MTK_MT6797_A72_POWER=y",
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_SMP=y",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_I2C=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_REGULATOR=y",
    "CONFIG_RESET_CONTROLLER=y",
    "CONFIG_KALLSYMS=y",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_THERMAL is not set",
    "# CONFIG_MODULES is not set",
    "# CONFIG_MMC is not set",
    "# CONFIG_MTD is not set",
    "# CONFIG_SCSI is not set",
    "# CONFIG_ATA is not set",
    "# CONFIG_USB_MASS_STORAGE is not set",
}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    value = json.loads(read_regular(path, label).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def normalized_build_bytes(value: dict[str, Any], label: str) -> bytes:
    if "generated_utc" not in value:
        raise ValueError(f"{label} lacks generated_utc")
    normalized = dict(value)
    del normalized["generated_utc"]
    return (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode()


def validate_manifest_contract(
    data: bytes, label: str, *, require_af: bool
) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    expected_kernel = {
        "version": "7.1.3",
        "released": "2026-07-04",
        "source_url": "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz",
        "sha256": SOURCE_SHA256,
    }
    if (
        value.get("schema") != 1
        or value.get("kernel") != expected_kernel
        or value.get("architecture") != "arm64"
        or value.get("patch_series") != "patches/series"
    ):
        raise ValueError(f"{label} global kernel contract changed")
    config = value.get("config")
    if not isinstance(config, dict) or config.get("default_profile") != "full":
        raise ValueError(f"{label} global config contract changed")
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError(f"{label} profiles are absent")
    expected_ae = {"base": "defconfig", "fragments": FRAGMENTS[:-1]}
    expected_af = {"base": "defconfig", "fragments": FRAGMENTS}
    if profiles.get(BASELINE_PROFILE) != expected_ae:
        raise ValueError(f"{label} Candidate AE profile changed")
    if require_af and profiles.get(PROFILE) != expected_af:
        raise ValueError(f"{label} Candidate AF profile changed")
    if PROFILE in profiles and profiles[PROFILE] != expected_af:
        raise ValueError(f"{label} present Candidate AF profile changed")
    return value


def validate_ae_build(value: dict[str, Any]) -> None:
    expected = {
        "build_profile": BASELINE_PROFILE,
        "source_sha256": SOURCE_SHA256,
        "patchset_sha256": AE_PATCHSET_SHA256,
        "config_sha256": AE_CONFIG_SHA256,
        "config_inputs_sha256": AE_CONFIG_INPUTS_SHA256,
        "config_fragments": FRAGMENTS[:-1],
        "modules_built": False,
        "kernel_release": KERNEL_RELEASE,
        "compiler": COMPILER,
        "linker": LINKER,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"baseline package is not exact Candidate AE: {key}")
    if digest_bytes(normalized_build_bytes(value, "AE build")) != AE_SOURCE_BUILD_SHA256:
        raise ValueError("baseline normalized source provenance is not exact Candidate AE")


def inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"unsafe package tree: {root}")
    result: dict[str, pathlib.Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"package contains symlink: {relative}")
        if path.is_file():
            result[relative] = path
        elif not path.is_dir():
            raise ValueError(f"package contains special entry: {relative}")
    return result


def validate_manifest(package: pathlib.Path) -> None:
    members = inventory(package)
    lines = read_regular(package / "SHA256SUMS", "package SHA256SUMS").decode(
        "ascii"
    ).splitlines()
    seen: set[str] = set()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("malformed package manifest")
        relative = fields[1].removeprefix("*").removeprefix("./")
        if relative in seen or relative == "SHA256SUMS" or relative not in members:
            raise ValueError("unsafe, duplicate, or missing manifest member")
        if digest_bytes(read_regular(members[relative], relative)) != fields[0]:
            raise ValueError(f"package checksum mismatch: {relative}")
        seen.add(relative)
    if seen != set(members) - {"SHA256SUMS"}:
        raise ValueError("package manifest is not an exact inventory")


def series_entries(data: bytes) -> list[str]:
    entries: list[str] = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        path = pathlib.PurePosixPath(line)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) < 2
            or any(character.isspace() for character in line)
        ):
            raise ValueError(f"unsafe patch-series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        raise ValueError("duplicate patch-series entry")
    return entries


def patchset_digest(series: bytes, root: pathlib.Path) -> str:
    records = [f"{digest_bytes(series)}  patches/series\n"]
    for entry in series_entries(series):
        records.append(
            f"{digest_bytes(read_regular(root / entry, f'patch {entry}'))}  {entry}\n"
        )
    return digest_bytes("".join(records).encode("ascii"))


def config_inputs_digest(
    profile: str, fragments: list[str], data: dict[str, bytes]
) -> str:
    records = [f"profile={profile}\n", "base=defconfig\n"]
    for relative in fragments:
        records.append(f"{digest_bytes(data[relative])}  {relative}\n")
    return digest_bytes("".join(records).encode("ascii"))


def config_map(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if line.startswith("CONFIG_"):
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
        else:
            continue
        if key in result:
            raise ValueError(f"duplicate resolved-config symbol: {key}")
        result[key] = line
    return result


def fragment_inventory(
    package: pathlib.Path, fragments: list[str], label: str
) -> dict[str, bytes]:
    packaged = inventory(package / "provenance/configs")
    expected = {pathlib.PurePosixPath(item).name for item in fragments}
    if set(packaged) != expected:
        raise ValueError(f"{label} packaged fragment inventory changed")
    result: dict[str, bytes] = {}
    for relative in fragments:
        name = pathlib.PurePosixPath(relative).name
        result[relative] = read_regular(packaged[name], f"{label} fragment {name}")
    return result


def validate_config_maps(
    ae_fragments: dict[str, bytes], af_fragments: dict[str, bytes]
) -> str:
    ae_digest = config_inputs_digest(BASELINE_PROFILE, FRAGMENTS[:-1], ae_fragments)
    af_digest = config_inputs_digest(PROFILE, FRAGMENTS, af_fragments)
    if ae_digest != AE_CONFIG_INPUTS_SHA256:
        raise ValueError("packaged AE config inputs are not exact Candidate AE")
    if af_digest != AF_CONFIG_INPUTS_SHA256:
        raise ValueError("packaged AF config inputs are not exact Candidate AF")
    for relative in FRAGMENTS[:-1]:
        if ae_fragments[relative] != af_fragments[relative]:
            raise ValueError(f"Candidate AF changed inherited AE fragment: {relative}")
    return af_digest


def validate_config_provenance(
    baseline: pathlib.Path, candidate: pathlib.Path
) -> str:
    ae_fragments = fragment_inventory(baseline, FRAGMENTS[:-1], "AE")
    af_fragments = fragment_inventory(candidate, FRAGMENTS, "AF")
    return validate_config_maps(ae_fragments, af_fragments)


def validate_patch_provenance(
    baseline: pathlib.Path, candidate: pathlib.Path
) -> str:
    base_series = read_regular(baseline / "provenance/series", "AE series")
    new_series = read_regular(candidate / "provenance/series", "AF series")
    if base_series != new_series:
        raise ValueError("Candidate AF patch series is not byte-exact Candidate AE")
    entries = series_entries(new_series)
    base_root = baseline / "provenance/patches"
    new_root = candidate / "provenance/patches"
    base_members = inventory(base_root)
    new_members = inventory(new_root)
    if set(base_members) != set(entries) or set(new_members) != set(entries):
        raise ValueError("packaged patch provenance inventory differs from series")
    for entry in entries:
        baseline_data = read_regular(base_root / entry, f"AE patch {entry}")
        candidate_data = read_regular(new_root / entry, f"AF patch {entry}")
        if baseline_data != candidate_data:
            raise ValueError(f"Candidate AF changed inherited AE patch: {entry}")
    patchset = patchset_digest(new_series, new_root)
    if patchset != AE_PATCHSET_SHA256:
        raise ValueError("Candidate AF patchset is not exact Candidate AE")
    return patchset


def validate_package(
    baseline: pathlib.Path, candidate: pathlib.Path, manifest_path: pathlib.Path
) -> None:
    validate_manifest(baseline)
    validate_manifest(candidate)
    manifest_data = read_regular(manifest_path, "repository manifest")
    validate_manifest_contract(manifest_data, "repository manifest", require_af=True)
    validate_manifest_contract(
        read_regular(
            baseline / "provenance/kernel-manifest.json", "AE packaged manifest"
        ),
        "AE packaged manifest",
        require_af=False,
    )
    validate_manifest_contract(
        read_regular(
            candidate / "provenance/kernel-manifest.json", "AF packaged manifest"
        ),
        "AF packaged manifest",
        require_af=True,
    )

    old_build = load_json(baseline / "provenance/build.json", "AE build")
    new_build = load_json(candidate / "provenance/build.json", "AF build")
    validate_ae_build(old_build)
    ae_image_gz = read_regular(baseline / "Image.gz", "AE Image.gz")
    ae_dtb = read_regular(
        baseline / "dtbs/mediatek/mt6797-gemini-pda.dtb", "AE DTB"
    )
    if digest_bytes(ae_image_gz) != AE_IMAGE_GZ_SHA256:
        raise ValueError("baseline Image.gz is not exact Candidate AE")
    if digest_bytes(ae_dtb) != AE_DTB_SHA256:
        raise ValueError("baseline DTB is not exact Candidate AE")

    patchset = validate_patch_provenance(baseline, candidate)
    config_inputs = validate_config_provenance(baseline, candidate)
    expected_build = {
        "schema": 1,
        "build_profile": PROFILE,
        "base_config": "defconfig",
        "config_fragments": FRAGMENTS,
        "source_sha256": SOURCE_SHA256,
        "patchset_sha256": patchset,
        "config_inputs_sha256": config_inputs,
        "modules_built": False,
        "kernel_release": KERNEL_RELEASE,
        "compiler": COMPILER,
        "linker": LINKER,
    }
    for key, expected in expected_build.items():
        if new_build.get(key) != expected:
            raise ValueError(f"Candidate AF build provenance changed: {key}")
    expected_package_name = (
        f"linux-7.1.3-gemini-{PROFILE}-{patchset[:8]}-{config_inputs[:8]}"
    )
    if candidate.name != expected_package_name:
        raise ValueError("Candidate AF package basename disagrees with its identities")

    old_config_data = read_regular(baseline / "kernel.config", "AE config")
    new_config_data = read_regular(candidate / "kernel.config", "AF config")
    if digest_bytes(old_config_data) != AE_CONFIG_SHA256:
        raise ValueError("baseline resolved config is not exact Candidate AE")
    old_config = config_map(old_config_data)
    new_config = config_map(new_config_data)
    changed = {
        key: (old_config.get(key), new_config.get(key))
        for key in old_config.keys() | new_config.keys()
        if old_config.get(key) != new_config.get(key)
    }
    expected_changed = {
        "CONFIG_CMDLINE": (
            f'CONFIG_CMDLINE="{AE_CMDLINE}"',
            f'CONFIG_CMDLINE="{AF_CMDLINE}"',
        )
    }
    if changed != expected_changed:
        raise ValueError(f"resolved config delta is not blacklist-only: {changed}")
    lines = set(new_config_data.decode("utf-8").splitlines())
    missing = REQUIRED_CONFIG - lines
    if missing:
        raise ValueError(f"required config line is missing: {sorted(missing)[0]}")
    tokens = AF_CMDLINE.split()
    for token in ("maxcpus=8", "regulator_ignore_unused", BLACKLIST_TOKEN):
        if tokens.count(token) != 1:
            raise ValueError(f"forced-command-line token is not exact: {token}")
    if "maxcpus=1" in tokens or "nosmp" in tokens or any(
        token.startswith("nr_cpus=") for token in tokens
    ):
        raise ValueError("forced command line contains a conflicting CPU cap")
    if new_build.get("config_sha256") != digest_bytes(new_config_data):
        raise ValueError("Candidate AF resolved config hash disagrees with provenance")

    image = read_regular(candidate / "Image", "Candidate AF Image")
    image_gz = read_regular(candidate / "Image.gz", "Candidate AF Image.gz")
    if gzip.decompress(image_gz) != image:
        raise ValueError("Candidate AF Image.gz does not expand to Image")
    if image_gz == ae_image_gz:
        raise ValueError("Candidate AF kernel did not change from AE")
    for marker in (
        b"mediatek,mt6797-a72-power\0",
        b"mediatek,mt6797-psci\0",
        b"mt6797-a72-power\0",
        b"observer-v1\n\0",
        b"observe-only\n\0",
        BLACKLIST_TOKEN.encode("ascii"),
    ):
        if marker not in image:
            raise ValueError(f"Candidate AF Image lacks required marker: {marker!r}")
    system_map = read_regular(
        candidate / "System.map", "Candidate AF System.map"
    ).decode("ascii")
    system_map_lines = system_map.splitlines()
    if not any(line.endswith(" mt6797_a72_power_driver_init") for line in system_map_lines):
        raise ValueError("Candidate AF System.map lacks observer initcall function")
    if not any(
        "__initcall" in line and "mt6797_a72_power_driver_init" in line
        for line in system_map_lines
    ):
        raise ValueError("Candidate AF System.map lacks observer initcall entry")
    if not any(line.endswith(" da9211_regulator_driver_init") for line in system_map_lines):
        raise ValueError("Candidate AF System.map lacks independent DA9211 initcall")

    dtb = read_regular(
        candidate / "dtbs/mediatek/mt6797-gemini-pda.dtb", "Candidate AF DTB"
    )
    if dtb != ae_dtb or digest_bytes(dtb) != AE_DTB_SHA256:
        raise ValueError("Candidate AF DTB is not byte-exact Candidate AE")
    for marker in (
        b"mediatek,mt6797-a72-power\0",
        b"mediatek,mt6797-psci\0",
        b"dlg,da9214\0",
        b"vproc-big\0",
        b"BUCKA\0",
        b"BUCKB\0",
        b"i2c@1100e000\0",
    ):
        if marker not in dtb:
            raise ValueError(f"Candidate AF DTB lacks AE resource marker: {marker!r}")

    print("validation=candidate-af-a72-observer-initcall-package")
    print(f"package={candidate.name}")
    print(f"profile={PROFILE}")
    print(f"patchset_sha256={patchset}")
    print("patch_delta_from_ae=none")
    print(f"config_inputs_sha256={config_inputs}")
    print(f"config_sha256={digest_bytes(new_config_data)}")
    print("resolved_config_delta=cmdline-initcall-blacklist-only")
    print("dtb_lineage=byte-exact-candidate-ae")
    print("cpu_policy=maxcpus-8")
    print("cpu8_cpu9=offline-not-requested")
    print("active_a72_power_write=none")
    print("regulator_voltage_or_enable_request=none")
    print("known_supplier_side_effects=da9211-page-selector-write+scpsys-clock-gating")
    print("validator_device_access=none")


def validate_reproduction(first: pathlib.Path, second: pathlib.Path) -> None:
    if first == second or first.samefile(second):
        raise ValueError("reproduction requires two independent package trees")
    validate_manifest(first)
    validate_manifest(second)
    left = inventory(first)
    right = inventory(second)
    if set(left) != set(right):
        raise ValueError("reproduced package inventories differ")
    dynamic = {"SHA256SUMS", "provenance/build.json"}
    for relative in sorted(left):
        if stat.S_IMODE(left[relative].stat().st_mode) != stat.S_IMODE(
            right[relative].stat().st_mode
        ):
            raise ValueError(f"reproduced mode differs: {relative}")
        if relative not in dynamic and read_regular(
            left[relative], relative
        ) != read_regular(right[relative], relative):
            raise ValueError(f"reproduced bytes differ: {relative}")
    left_build = load_json(first / "provenance/build.json", "first build")
    right_build = load_json(second / "provenance/build.json", "second build")
    if "generated_utc" not in left_build or "generated_utc" not in right_build:
        raise ValueError("reproduced build provenance lacks generated_utc")
    left_build.pop("generated_utc", None)
    right_build.pop("generated_utc", None)
    if left_build != right_build:
        raise ValueError("normalized build provenance differs")
    print("validation=candidate-af-a72-observer-initcall-package-reproduction")
    print("payloads=byte-identical")
    print("modes=identical")
    print("normalized_build_provenance=identical")
    print("validator_device_access=none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path)
    parser.add_argument("--candidate", type=pathlib.Path)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--first", type=pathlib.Path)
    parser.add_argument("--second", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.first is not None or args.second is not None:
            if args.first is None or args.second is None or any(
                (args.baseline, args.candidate, args.manifest)
            ):
                raise ValueError("reproduction mode requires exactly --first and --second")
            validate_reproduction(
                args.first.resolve(strict=True), args.second.resolve(strict=True)
            )
        else:
            if args.baseline is None or args.candidate is None or args.manifest is None:
                raise ValueError(
                    "package mode requires --baseline, --candidate, and --manifest"
                )
            validate_package(
                args.baseline.resolve(strict=True),
                args.candidate.resolve(strict=True),
                args.manifest.resolve(strict=True),
            )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        gzip.BadGzipFile,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
