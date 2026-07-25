#!/usr/bin/env python3
"""Validate Candidate AD's one-line SMP8 package delta and reproduction."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import stat
import sys
from typing import Any


PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8"
BASELINE_PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot"
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
]
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93"
SERIES_SHA256 = "124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a"
PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
OLD_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=1 nokaslr '
    'ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init '
    'panic=0 g_ether.dev_addr=42:00:15:19:82:01 '
    'g_ether.host_addr=42:00:15:19:82:00 '
    'g_ether.iManufacturer=gemini-pda-mainline '
    'g_ether.iProduct=Gemini-L-Observability '
    'g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L '
    'clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"'
)
NEW_CMDLINE = OLD_CMDLINE.replace("maxcpus=1", "maxcpus=8")
REQUIRED_CONFIG = {
    "CONFIG_SMP=y",
    "CONFIG_NR_CPUS=512",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_ARM_ARCH_TIMER=y",
    "CONFIG_ARM_GIC_V3=y",
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_IKCONFIG=y",
    "CONFIG_IKCONFIG_PROC=y",
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


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    value = json.loads(read_regular(path, label).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def files(root: pathlib.Path) -> dict[str, pathlib.Path]:
    output: dict[str, pathlib.Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"package contains symlink: {relative}")
        if path.is_file():
            output[relative] = path
        elif not path.is_dir():
            raise ValueError(f"package contains special entry: {relative}")
    return output


def validate_manifest(package: pathlib.Path) -> None:
    inventory = files(package)
    lines = read_regular(package / "SHA256SUMS", "SHA256SUMS").decode("ascii").splitlines()
    seen: set[str] = set()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or len(fields[0]) != 64:
            raise ValueError("malformed package manifest")
        relative = fields[1].removeprefix("*").removeprefix("./")
        if relative in seen or relative == "SHA256SUMS" or relative not in inventory:
            raise ValueError("unsafe, duplicate, or missing package manifest path")
        if digest(read_regular(inventory[relative], relative)) != fields[0]:
            raise ValueError(f"package checksum mismatch: {relative}")
        seen.add(relative)
    if seen != set(inventory) - {"SHA256SUMS"}:
        raise ValueError("package manifest is not an exact inventory")


def compare_tree(left: pathlib.Path, right: pathlib.Path, label: str) -> None:
    left_files = files(left)
    right_files = files(right)
    if set(left_files) != set(right_files):
        raise ValueError(f"{label} inventory changed")
    for relative in left_files:
        if read_regular(left_files[relative], relative) != read_regular(right_files[relative], relative):
            raise ValueError(f"{label} changed: {relative}")


def validate_candidate(baseline: pathlib.Path, candidate: pathlib.Path, manifest: pathlib.Path) -> None:
    for root, label in ((baseline, "baseline"), (candidate, "candidate")):
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"{label} package is unsafe")
        validate_manifest(root)

    old_build = load_json(baseline / "provenance/build.json", "baseline build")
    new_build = load_json(candidate / "provenance/build.json", "candidate build")
    if old_build.get("build_profile") != BASELINE_PROFILE:
        raise ValueError("baseline profile changed")
    if new_build.get("build_profile") != PROFILE:
        raise ValueError("Candidate AD profile changed")
    if new_build.get("config_fragments") != FRAGMENTS:
        raise ValueError("Candidate AD fragment order changed")
    if old_build.get("config_fragments") != FRAGMENTS[:-1]:
        raise ValueError("baseline fragment order changed")
    for key, expected in (("source_sha256", SOURCE_SHA256), ("patchset_sha256", PATCHSET_SHA256)):
        if old_build.get(key) != expected or new_build.get(key) != expected:
            raise ValueError(f"{key} changed")
    for key in ("kernel_release", "base_config", "modules_built", "compiler", "linker"):
        if old_build.get(key) != new_build.get(key):
            raise ValueError(f"build property changed: {key}")

    old_lines = read_regular(baseline / "kernel.config", "baseline config").decode().splitlines()
    new_lines = read_regular(candidate / "kernel.config", "candidate config").decode().splitlines()
    if len(old_lines) != len(new_lines):
        raise ValueError("resolved configuration line count changed")
    changed = [(old, new) for old, new in zip(old_lines, new_lines, strict=True) if old != new]
    if changed != [(OLD_CMDLINE, NEW_CMDLINE)]:
        raise ValueError("resolved config is not the exact maxcpus=1 to maxcpus=8 delta")
    new_set = set(new_lines)
    if not REQUIRED_CONFIG <= new_set:
        raise ValueError("Candidate AD required SMP or safety configuration is missing")
    if sum("maxcpus=" in line for line in new_lines) != 1 or "maxcpus=8" not in NEW_CMDLINE:
        raise ValueError("Candidate AD CPU cap is not exact")

    compare_tree(baseline / "dtbs", candidate / "dtbs", "packaged DTBs")
    dtb = read_regular(candidate / "dtbs/mediatek/mt6797-gemini-pda.dtb", "Gemini DTB")
    if digest(dtb) != PACKAGE_DTB_SHA256:
        raise ValueError("packaged Gemini DTB changed")
    compare_tree(baseline / "provenance/patches", candidate / "provenance/patches", "patch provenance")
    if digest(read_regular(candidate / "provenance/series", "series")) != SERIES_SHA256:
        raise ValueError("patch series changed")
    if read_regular(candidate / "provenance/kernel-manifest.json", "packaged manifest") != read_regular(manifest, "repository manifest"):
        raise ValueError("packaged manifest is not the selected repository manifest")
    for fragment in FRAGMENTS[:-1]:
        name = pathlib.Path(fragment).name
        if read_regular(candidate / "provenance/configs" / name, name) != read_regular(baseline / "provenance/configs" / name, name):
            raise ValueError(f"inherited config fragment changed: {name}")
    smp_name = pathlib.Path(FRAGMENTS[-1]).name
    repo_root = manifest.parent.parent
    if read_regular(candidate / "provenance/configs" / smp_name, smp_name) != read_regular(repo_root / FRAGMENTS[-1], "repository SMP8 fragment"):
        raise ValueError("packaged SMP8 fragment changed")

    image = read_regular(candidate / "Image", "Candidate AD Image")
    image_gz = read_regular(candidate / "Image.gz", "Candidate AD Image.gz")
    if gzip.decompress(image_gz) != image:
        raise ValueError("Candidate AD Image.gz does not expand to Image")
    if image_gz == read_regular(baseline / "Image.gz", "baseline Image.gz"):
        raise ValueError("Candidate AD kernel did not change")
    print("validation=candidate-ad-package-delta")
    print(f"package={candidate.name}")
    print(f"profile={PROFILE}")
    print("resolved_config_delta=maxcpus-1-to-maxcpus-8-only")
    print(f"image_gz_sha256={digest(image_gz)}")
    print(f"config_sha256={digest(read_regular(candidate / 'kernel.config', 'candidate config'))}")
    print("dtb_lineage=byte-exact-candidate-ab-package")
    print("hardware_write=none")


def validate_reproduction(first: pathlib.Path, second: pathlib.Path) -> None:
    left = files(first)
    right = files(second)
    if set(left) != set(right):
        raise ValueError("reproduced package inventories differ")
    dynamic = {"SHA256SUMS", "provenance/build.json"}
    for relative in sorted(set(left) - dynamic):
        if stat.S_IMODE(left[relative].stat().st_mode) != stat.S_IMODE(right[relative].stat().st_mode):
            raise ValueError(f"reproduced mode differs: {relative}")
        if read_regular(left[relative], relative) != read_regular(right[relative], relative):
            raise ValueError(f"reproduced bytes differ: {relative}")
    left_build = load_json(first / "provenance/build.json", "first build")
    right_build = load_json(second / "provenance/build.json", "second build")
    left_build.pop("generated_utc", None)
    right_build.pop("generated_utc", None)
    if left_build != right_build:
        raise ValueError("normalized build provenance differs")
    print("validation=candidate-ad-package-reproduction")
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
            if args.first is None or args.second is None or any((args.baseline, args.candidate, args.manifest)):
                raise ValueError("reproduction mode requires exactly --first and --second")
            validate_reproduction(args.first.resolve(strict=True), args.second.resolve(strict=True))
        else:
            if args.baseline is None or args.candidate is None or args.manifest is None:
                raise ValueError("delta mode requires --baseline, --candidate, and --manifest")
            validate_candidate(
                args.baseline.resolve(strict=True),
                args.candidate.resolve(strict=True),
                args.manifest.resolve(strict=True),
            )
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, gzip.BadGzipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
