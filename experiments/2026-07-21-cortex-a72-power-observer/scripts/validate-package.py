#!/usr/bin/env python3
"""Validate Candidate AE's observer-only kernel package and reproduction."""

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
    "smp8-a72-observer"
)
BASELINE_PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
AD_PATCHSET_SHA256 = "efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93"
AD_CONFIG_SHA256 = "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46"
AD_IMAGE_GZ_SHA256 = "1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b"
AD_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
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
]
AD_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
AE_CMDLINE = AD_CMDLINE + " regulator_ignore_unused"
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
OBSERVER_SOURCE_REQUIRED = (
    'sysfs_emit(buf, "0\\n")',
    'sysfs_emit(buf, "observer-v1\\n")',
    'sysfs_emit(buf, "observe-only\\n")',
    "regulator_is_enabled(power->vproc_big)",
    "regulator_get_voltage(power->vproc_big)",
    "regmap_read(power->spm",
    "readl(power->mcucfg",
    ".suppress_bind_attrs = true",
)
ACTIVE_SOURCE = re.compile(
    r"\b(?:regulator_(?:enable|disable|set_voltage)|"
    r"reset_control_(?:assert|deassert|reset)|regmap_(?:write|update_bits)|"
    r"writel(?:_relaxed)?|arm_smccc_smc|cpu_up|cpuhp_setup_state)\s*\("
)


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


def config_inputs_digest(repo_root: pathlib.Path) -> str:
    records = [f"profile={PROFILE}\n", "base=defconfig\n"]
    for relative in FRAGMENTS:
        data = read_regular(repo_root / relative, f"fragment {relative}")
        records.append(f"{digest_bytes(data)}  {relative}\n")
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


def added_file_lines(patch: str, target: str) -> str:
    current = ""
    output: list[str] = []
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            fields = line.split()
            current = fields[3].removeprefix("b/") if len(fields) == 4 else ""
            continue
        if current == target and line.startswith("+") and not line.startswith("+++"):
            output.append(line[1:])
    return "\n".join(output)


def validate_observer_source(patch_root: pathlib.Path, entries: list[str]) -> None:
    target = "drivers/soc/mediatek/mt6797-a72-power.c"
    sources: list[str] = []
    for entry in entries:
        patch = read_regular(patch_root / entry, entry).decode("utf-8")
        added = added_file_lines(patch, target)
        if added:
            sources.append(added)
    if len(sources) != 1:
        raise ValueError("observer driver must be introduced by exactly one patch")
    source = sources[0]
    for token in OBSERVER_SOURCE_REQUIRED:
        if token not in source:
            raise ValueError(f"observer source contract is missing: {token}")
    active = ACTIVE_SOURCE.search(source)
    if active is not None:
        raise ValueError(f"observer source contains active operation: {active.group(0)}")
    if "DEVICE_ATTR_RW" in source or "DEVICE_ATTR_WO" in source:
        raise ValueError("observer source exposes a writable sysfs attribute")
    if source.count("DEVICE_ATTR_RO(") != 6:
        raise ValueError("observer read-only sysfs ABI changed")


def validate_patch_provenance(
    baseline: pathlib.Path, candidate: pathlib.Path, repo_root: pathlib.Path
) -> tuple[str, int]:
    base_series = read_regular(baseline / "provenance/series", "AD series")
    new_series = read_regular(candidate / "provenance/series", "AE series")
    repo_series = read_regular(repo_root / "patches/series", "repository series")
    if new_series != repo_series:
        raise ValueError("Candidate AE packaged series differs from repository")
    base_entries = series_entries(base_series)
    new_entries = series_entries(new_series)
    if len(new_entries) <= len(base_entries) or new_entries[: len(base_entries)] != base_entries:
        raise ValueError("Candidate AE patch stack is not an append-only AD extension")
    base_root = baseline / "provenance/patches"
    new_root = candidate / "provenance/patches"
    repo_root_patches = repo_root / "patches"
    base_members = inventory(base_root)
    new_members = inventory(new_root)
    if set(base_members) != set(base_entries) or set(new_members) != set(new_entries):
        raise ValueError("packaged patch provenance inventory differs from series")
    if patchset_digest(base_series, base_root) != AD_PATCHSET_SHA256:
        raise ValueError("baseline patch provenance is not exact Candidate AD")
    for entry in new_entries:
        packaged = read_regular(new_root / entry, f"packaged patch {entry}")
        repository = read_regular(repo_root_patches / entry, f"repository patch {entry}")
        if packaged != repository:
            raise ValueError(f"packaged patch differs from repository: {entry}")
        if entry in base_members and packaged != read_regular(base_root / entry, entry):
            raise ValueError(f"Candidate AE changed inherited AD patch: {entry}")
    patchset = patchset_digest(new_series, new_root)
    validate_observer_source(new_root, new_entries)
    return patchset, len(new_entries) - len(base_entries)


def validate_package(
    baseline: pathlib.Path, candidate: pathlib.Path, manifest_path: pathlib.Path
) -> None:
    validate_manifest(baseline)
    validate_manifest(candidate)
    repo_root = manifest_path.parent.parent
    manifest_data = read_regular(manifest_path, "repository manifest")
    manifest = json.loads(manifest_data.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("repository manifest is not an object")
    if read_regular(
        candidate / "provenance/kernel-manifest.json", "packaged manifest"
    ) != manifest_data:
        raise ValueError("Candidate AE packaged manifest differs from repository")
    try:
        profile = manifest["config"]["profiles"][PROFILE]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"repository manifest lacks profile {PROFILE}") from exc
    if profile != {"base": "defconfig", "fragments": FRAGMENTS}:
        raise ValueError("Candidate AE manifest profile boundary changed")

    old_build = load_json(baseline / "provenance/build.json", "AD build")
    new_build = load_json(candidate / "provenance/build.json", "AE build")
    if old_build.get("build_profile") != BASELINE_PROFILE:
        raise ValueError("baseline is not the Candidate AD profile")
    if old_build.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("Candidate AD source identity changed")
    if old_build.get("patchset_sha256") != AD_PATCHSET_SHA256:
        raise ValueError("Candidate AD patch identity changed")
    if old_build.get("config_sha256") != AD_CONFIG_SHA256:
        raise ValueError("Candidate AD config identity changed")
    if old_build.get("config_fragments") != FRAGMENTS[:-1]:
        raise ValueError("Candidate AD fragment stack changed")
    if digest_bytes(read_regular(baseline / "Image.gz", "AD Image.gz")) != AD_IMAGE_GZ_SHA256:
        raise ValueError("Candidate AD Image.gz identity changed")
    if digest_bytes(
        read_regular(baseline / "dtbs/mediatek/mt6797-gemini-pda.dtb", "AD DTB")
    ) != AD_DTB_SHA256:
        raise ValueError("Candidate AD packaged Gemini DTB changed")

    patchset, added_patch_count = validate_patch_provenance(
        baseline, candidate, repo_root
    )
    config_inputs = config_inputs_digest(repo_root)
    expected_build = {
        "schema": 1,
        "build_profile": PROFILE,
        "base_config": "defconfig",
        "config_fragments": FRAGMENTS,
        "source_sha256": SOURCE_SHA256,
        "patchset_sha256": patchset,
        "config_inputs_sha256": config_inputs,
        "modules_built": False,
    }
    for key, expected in expected_build.items():
        if new_build.get(key) != expected:
            raise ValueError(f"Candidate AE build provenance changed: {key}")
    for key in ("kernel_release", "compiler", "linker"):
        if new_build.get(key) != old_build.get(key):
            raise ValueError(f"Candidate AE build property differs from AD: {key}")
    expected_package_name = (
        f"linux-7.1.3-gemini-{PROFILE}-{patchset[:8]}-{config_inputs[:8]}"
    )
    if candidate.name != expected_package_name:
        raise ValueError("Candidate AE package basename disagrees with its identities")

    packaged_configs = inventory(candidate / "provenance/configs")
    expected_names = {pathlib.PurePosixPath(item).name for item in FRAGMENTS}
    if set(packaged_configs) != expected_names:
        raise ValueError("Candidate AE packaged fragment inventory changed")
    for relative in FRAGMENTS:
        name = pathlib.PurePosixPath(relative).name
        if read_regular(packaged_configs[name], name) != read_regular(
            repo_root / relative, relative
        ):
            raise ValueError(f"packaged fragment differs from repository: {relative}")

    old_config_data = read_regular(baseline / "kernel.config", "AD config")
    new_config_data = read_regular(candidate / "kernel.config", "AE config")
    if digest_bytes(old_config_data) != AD_CONFIG_SHA256:
        raise ValueError("baseline resolved config is not exact Candidate AD")
    old_config = config_map(old_config_data)
    new_config = config_map(new_config_data)
    changed = {
        key: (old_config.get(key), new_config.get(key))
        for key in old_config.keys() | new_config.keys()
        if old_config.get(key) != new_config.get(key)
    }
    expected_changed = {
        "CONFIG_CMDLINE": (
            f'CONFIG_CMDLINE="{AD_CMDLINE}"',
            f'CONFIG_CMDLINE="{AE_CMDLINE}"',
        ),
        "CONFIG_REGULATOR_DA9211": (
            "# CONFIG_REGULATOR_DA9211 is not set",
            "CONFIG_REGULATOR_DA9211=y",
        ),
        "CONFIG_MTK_MT6797_A72_POWER": (None, "CONFIG_MTK_MT6797_A72_POWER=y"),
    }
    if changed != expected_changed:
        raise ValueError(f"resolved config delta is not observer-only: {changed}")
    missing = REQUIRED_CONFIG - set(new_config_data.decode("utf-8").splitlines())
    if missing:
        raise ValueError(f"required config line is missing: {sorted(missing)[0]}")
    if AE_CMDLINE.split().count("maxcpus=8") != 1:
        raise ValueError("internal Candidate AE CPU-cap contract is invalid")
    if AE_CMDLINE.split().count("regulator_ignore_unused") != 1:
        raise ValueError("internal regulator preservation contract is invalid")
    if new_build.get("config_sha256") != digest_bytes(new_config_data):
        raise ValueError("Candidate AE resolved config hash disagrees with provenance")

    image = read_regular(candidate / "Image", "Candidate AE Image")
    image_gz = read_regular(candidate / "Image.gz", "Candidate AE Image.gz")
    if gzip.decompress(image_gz) != image:
        raise ValueError("Candidate AE Image.gz does not expand to Image")
    for marker in (
        b"mediatek,mt6797-a72-power\0",
        b"mediatek,mt6797-psci\0",
        b"mt6797-a72-power\0",
        b"observer-v1\n\0",
        b"observe-only\n\0",
    ):
        if marker not in image:
            raise ValueError(f"Candidate AE Image lacks observer marker: {marker!r}")
    if image_gz == read_regular(baseline / "Image.gz", "AD Image.gz"):
        raise ValueError("Candidate AE kernel did not change from AD")
    system_map = read_regular(candidate / "System.map", "Candidate AE System.map").decode(
        "ascii"
    )
    for symbol in ("mt6797_a72_power", "da9211"):
        if symbol not in system_map:
            raise ValueError(f"Candidate AE System.map lacks built-in symbol: {symbol}")
    dtb = read_regular(
        candidate / "dtbs/mediatek/mt6797-gemini-pda.dtb", "Candidate AE DTB"
    )
    if digest_bytes(dtb) == AD_DTB_SHA256:
        raise ValueError("Candidate AE retained Candidate AD DTB")
    for marker in (
        b"mediatek,mt6797-a72-power\0",
        b"mediatek,mt6797-psci\0",
        b"dlg,da9214\0",
        b"vproc-big\0",
        b"BUCKA\0",
        b"BUCKB\0",
    ):
        if marker not in dtb:
            raise ValueError(f"Candidate AE DTB lacks resource marker: {marker!r}")

    print("validation=candidate-ae-a72-observer-package")
    print(f"package={candidate.name}")
    print(f"profile={PROFILE}")
    print(f"patchset_sha256={patchset}")
    print(f"appended_patches={added_patch_count}")
    print(f"config_inputs_sha256={config_inputs}")
    print(f"config_sha256={digest_bytes(new_config_data)}")
    print("resolved_config_delta=da9211-plus-a72-observer-plus-regulator-ignore-unused")
    print("cpu_policy=maxcpus-8")
    print("observer_source=read-only-no-active-operation")
    print("hardware_write=none")


def validate_reproduction(first: pathlib.Path, second: pathlib.Path) -> None:
    left = inventory(first)
    right = inventory(second)
    if set(left) != set(right):
        raise ValueError("reproduced package inventories differ")
    dynamic = {"SHA256SUMS", "provenance/build.json"}
    for relative in sorted(set(left) - dynamic):
        if stat.S_IMODE(left[relative].stat().st_mode) != stat.S_IMODE(
            right[relative].stat().st_mode
        ):
            raise ValueError(f"reproduced mode differs: {relative}")
        if read_regular(left[relative], relative) != read_regular(
            right[relative], relative
        ):
            raise ValueError(f"reproduced bytes differ: {relative}")
    left_build = load_json(first / "provenance/build.json", "first build")
    right_build = load_json(second / "provenance/build.json", "second build")
    left_build.pop("generated_utc", None)
    right_build.pop("generated_utc", None)
    if left_build != right_build:
        raise ValueError("normalized build provenance differs")
    print("validation=candidate-ae-a72-observer-package-reproduction")
    print("payloads=byte-identical")
    print("modes=identical")
    print("normalized_build_provenance=identical")
    print("hardware_write=none")


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
