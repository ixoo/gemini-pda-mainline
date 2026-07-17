#!/usr/bin/env python3
"""Validate the Candidate J kernel package as a one-config-line derivative."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


BASELINE_PROFILE = "usbdiag"
CANDIDATE_PROFILE = "usbdiag-clkignore"
BASELINE_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
)
CANDIDATE_FRAGMENTS = BASELINE_FRAGMENTS + (
    "configs/gemini-clk-ignore-unused.fragment",
)
BASELINE_CMDLINE = (
    'CONFIG_CMDLINE="console=tty0 console=ttyS0,921600n8 earlycon maxcpus=1 '
    "nokaslr ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug "
    "rdinit=/init panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-LK-USB-Diagnostic-B "
    'g_ether.iSerialNumber=GEMINI_USB_DIAG_20260716_B"'
)
CANDIDATE_CMDLINE = BASELINE_CMDLINE[:-1] + ' clk_ignore_unused"'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_digest(value: str, option: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{option} must be an exact 64-digit SHA-256")
    return normalized


def read(path: pathlib.Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or "read failed"
        raise ValueError(f"cannot read {label}: {detail}") from exc


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} top level is not an object")
    return value


def require_key(value: dict[str, Any], key: str, label: str) -> Any:
    if key not in value:
        raise ValueError(f"{label} is missing {key}")
    return value[key]


def listed_files(root: pathlib.Path, label: str) -> dict[str, bytes]:
    if not root.is_dir():
        raise ValueError(f"{label} directory is missing")
    result: dict[str, bytes] = {}
    try:
        paths = sorted(root.rglob("*"))
    except OSError as exc:
        raise ValueError(f"cannot enumerate {label}: {exc}") from exc
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"{label} contains a symlink: {path.relative_to(root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"{label} contains a non-file: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        result[relative] = read(path, f"{label}/{relative}")
    return result


def parse_series(data: bytes) -> list[str]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("patch series is not UTF-8") from exc
    result: list[str] = []
    for number, line in enumerate(lines, 1):
        if not line or line.startswith("#"):
            continue
        if any(character.isspace() for character in line):
            raise ValueError(f"unsafe whitespace in patch series line {number}")
        path = pathlib.PurePosixPath(line)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe patch path in series line {number}")
        result.append(line)
    if not result:
        raise ValueError("patch series is empty")
    if len(result) != len(set(result)):
        raise ValueError("patch series contains a duplicate path")
    return result


def patchset_digest(series: bytes, series_path: str, patches: dict[str, bytes]) -> str:
    result = bytearray()
    result.extend(f"{digest(series)}  {series_path}\n".encode())
    for relative in parse_series(series):
        if relative not in patches:
            raise ValueError(f"patch tree is missing {relative}")
        result.extend(f"{digest(patches[relative])}  {relative}\n".encode())
    return digest(bytes(result))


def config_inputs_digest(
    profile: str,
    fragments: tuple[str, ...],
    fragment_data: dict[str, bytes],
) -> str:
    result = bytearray(f"profile={profile}\nbase=defconfig\n".encode())
    for relative in fragments:
        name = pathlib.PurePosixPath(relative).name
        if name not in fragment_data:
            raise ValueError(f"package provenance is missing {name}")
        result.extend(f"{digest(fragment_data[name])}  {relative}\n".encode())
    return digest(bytes(result))


def require_manifest_boundary(
    current: dict[str, Any], packaged: dict[str, Any], profiles: tuple[str, ...], label: str
) -> None:
    for key in ("schema", "kernel", "architecture", "patch_series"):
        if require_key(packaged, key, label) != require_key(current, key, "current manifest"):
            raise ValueError(f"{label} differs at {key}")
    current_config = require_key(current, "config", "current manifest")
    packaged_config = require_key(packaged, "config", label)
    if not isinstance(current_config, dict) or not isinstance(packaged_config, dict):
        raise ValueError("manifest config field is not an object")
    current_profiles = require_key(current_config, "profiles", "current manifest config")
    packaged_profiles = require_key(packaged_config, "profiles", f"{label} config")
    if not isinstance(current_profiles, dict) or not isinstance(packaged_profiles, dict):
        raise ValueError("manifest profiles field is not an object")
    for profile in profiles:
        if packaged_profiles.get(profile) != current_profiles.get(profile):
            raise ValueError(f"{label} differs at config.profiles.{profile}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-package", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-package", type=pathlib.Path, required=True)
    parser.add_argument("--current-manifest", type=pathlib.Path, required=True)
    parser.add_argument("--clk-fragment", type=pathlib.Path, required=True)
    parser.add_argument("--expected-baseline-image-sha256", required=True)
    parser.add_argument("--expected-baseline-image-gz-sha256", required=True)
    parser.add_argument("--expected-candidate-image-sha256", required=True)
    parser.add_argument("--expected-candidate-image-gz-sha256", required=True)
    parser.add_argument("--expected-candidate-config-sha256", required=True)
    args = parser.parse_args()

    try:
        expected = {
            "baseline Image": expected_digest(
                args.expected_baseline_image_sha256,
                "--expected-baseline-image-sha256",
            ),
            "baseline Image.gz": expected_digest(
                args.expected_baseline_image_gz_sha256,
                "--expected-baseline-image-gz-sha256",
            ),
            "candidate Image": expected_digest(
                args.expected_candidate_image_sha256,
                "--expected-candidate-image-sha256",
            ),
            "candidate Image.gz": expected_digest(
                args.expected_candidate_image_gz_sha256,
                "--expected-candidate-image-gz-sha256",
            ),
            "candidate config": expected_digest(
                args.expected_candidate_config_sha256,
                "--expected-candidate-config-sha256",
            ),
        }
        baseline = args.baseline_package.resolve(strict=True)
        candidate = args.candidate_package.resolve(strict=True)
        current_manifest = load_json(args.current_manifest, "current manifest")
        baseline_manifest = load_json(
            baseline / "provenance/kernel-manifest.json", "baseline package manifest"
        )
        candidate_manifest = load_json(
            candidate / "provenance/kernel-manifest.json", "candidate package manifest"
        )
        require_manifest_boundary(
            current_manifest, baseline_manifest, (BASELINE_PROFILE,), "baseline manifest"
        )
        require_manifest_boundary(
            current_manifest,
            candidate_manifest,
            (BASELINE_PROFILE, CANDIDATE_PROFILE),
            "candidate manifest",
        )

        current_config = current_manifest["config"]
        profiles = current_config["profiles"]
        expected_profile_values = {
            BASELINE_PROFILE: {
                "base": "defconfig",
                "fragments": list(BASELINE_FRAGMENTS),
            },
            CANDIDATE_PROFILE: {
                "base": "defconfig",
                "fragments": list(CANDIDATE_FRAGMENTS),
            },
        }
        for profile, value in expected_profile_values.items():
            if profiles.get(profile) != value:
                raise ValueError(f"current manifest has an unexpected {profile} profile")

        baseline_build = load_json(
            baseline / "provenance/build.json", "baseline build provenance"
        )
        candidate_build = load_json(
            candidate / "provenance/build.json", "candidate build provenance"
        )
        if baseline_build.get("build_profile") != BASELINE_PROFILE:
            raise ValueError("baseline package is not usbdiag profile")
        if candidate_build.get("build_profile") != CANDIDATE_PROFILE:
            raise ValueError("candidate package is not usbdiag-clkignore profile")
        if baseline_build.get("base_config") != "defconfig" or candidate_build.get(
            "base_config"
        ) != "defconfig":
            raise ValueError("package base configuration is not defconfig")
        if baseline_build.get("config_fragments") != list(BASELINE_FRAGMENTS):
            raise ValueError("baseline fragment provenance is not exact usbdiag")
        if candidate_build.get("config_fragments") != list(CANDIDATE_FRAGMENTS):
            raise ValueError("candidate fragment provenance is not exact clkignore profile")
        for key in ("source_sha256", "patchset_sha256", "compiler", "linker"):
            if baseline_build.get(key) != candidate_build.get(key):
                raise ValueError(f"package build provenance differs at {key}")
        if baseline_build.get("kernel_release") != candidate_build.get("kernel_release"):
            raise ValueError("kernel release changed")
        if baseline_build.get("modules_built", False) or candidate_build.get(
            "modules_built", False
        ):
            raise ValueError("modules unexpectedly built")

        manifest_kernel = current_manifest["kernel"]
        if not isinstance(manifest_kernel, dict):
            raise ValueError("current manifest kernel field is not an object")
        if baseline_build.get("source_sha256") != manifest_kernel.get("sha256"):
            raise ValueError("package source SHA-256 is not the current pinned source")

        repo_root = args.current_manifest.resolve().parent.parent
        series_relative = current_manifest["patch_series"]
        if series_relative != "patches/series":
            raise ValueError("unexpected current patch-series path")
        current_series = read(repo_root / series_relative, "current patch series")
        baseline_series = read(baseline / "provenance/series", "baseline patch series")
        candidate_series = read(candidate / "provenance/series", "candidate patch series")
        if baseline_series != current_series or candidate_series != current_series:
            raise ValueError("package patch series differs from current repository")
        current_patches = listed_files(repo_root / "patches", "current patches")
        current_patches.pop("series", None)
        baseline_patches = listed_files(
            baseline / "provenance/patches", "baseline packaged patches"
        )
        candidate_patches = listed_files(
            candidate / "provenance/patches", "candidate packaged patches"
        )
        expected_patch_names = set(parse_series(current_series))
        current_selected = {
            name: value for name, value in current_patches.items() if name in expected_patch_names
        }
        if set(current_selected) != expected_patch_names:
            raise ValueError("current patch tree is missing a listed patch")
        if baseline_patches != current_selected or candidate_patches != current_selected:
            raise ValueError("packaged patch tree is not exactly the current series")
        patchset = patchset_digest(current_series, series_relative, current_selected)
        if baseline_build.get("patchset_sha256") != patchset or candidate_build.get(
            "patchset_sha256"
        ) != patchset:
            raise ValueError("package patchset SHA-256 is not exact")

        baseline_fragments = listed_files(
            baseline / "provenance/configs", "baseline config fragments"
        )
        candidate_fragments = listed_files(
            candidate / "provenance/configs", "candidate config fragments"
        )
        if set(baseline_fragments) != {
            pathlib.PurePosixPath(path).name for path in BASELINE_FRAGMENTS
        }:
            raise ValueError("baseline config-fragment tree is not exact")
        if set(candidate_fragments) != {
            pathlib.PurePosixPath(path).name for path in CANDIDATE_FRAGMENTS
        }:
            raise ValueError("candidate config-fragment tree is not exact")
        for relative in BASELINE_FRAGMENTS:
            name = pathlib.PurePosixPath(relative).name
            current_bytes = read(repo_root / relative, f"current {relative}")
            if baseline_fragments[name] != current_bytes or candidate_fragments[name] != current_bytes:
                raise ValueError(f"packaged fragment differs from current {relative}")
        clk_bytes = read(args.clk_fragment, "clk-ignore-unused fragment")
        clk_name = args.clk_fragment.name
        if candidate_fragments.get(clk_name) != clk_bytes:
            raise ValueError("candidate clk-ignore-unused fragment is not exact")
        fragment_text = clk_bytes.decode("utf-8")
        fragment_requests = [
            line
            for line in fragment_text.splitlines()
            if line.startswith("CONFIG_") or line.startswith("# CONFIG_")
        ]
        if fragment_requests != [CANDIDATE_CMDLINE]:
            raise ValueError("clk-ignore-unused fragment requests more than exact CONFIG_CMDLINE")

        baseline_config = read(baseline / "kernel.config", "baseline kernel config")
        candidate_config = read(candidate / "kernel.config", "candidate kernel config")
        try:
            baseline_lines = baseline_config.decode("utf-8").splitlines()
            candidate_lines = candidate_config.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError("kernel config is not UTF-8") from exc
        if len(baseline_lines) != len(candidate_lines):
            raise ValueError("resolved config line count changed")
        differences = [
            (number, old, new)
            for number, (old, new) in enumerate(
                zip(baseline_lines, candidate_lines, strict=True), 1
            )
            if old != new
        ]
        if len(differences) != 1:
            raise ValueError(f"resolved config has {len(differences)} differing lines")
        config_line, old_line, new_line = differences[0]
        if old_line != BASELINE_CMDLINE or new_line != CANDIDATE_CMDLINE:
            raise ValueError("resolved config delta is not the exact CONFIG_CMDLINE append")
        if "CONFIG_CMDLINE_FORCE=y" not in baseline_lines or "CONFIG_CMDLINE_FORCE=y" not in candidate_lines:
            raise ValueError("CONFIG_CMDLINE_FORCE=y is not retained")

        baseline_input_hash = config_inputs_digest(
            BASELINE_PROFILE, BASELINE_FRAGMENTS, baseline_fragments
        )
        candidate_input_hash = config_inputs_digest(
            CANDIDATE_PROFILE, CANDIDATE_FRAGMENTS, candidate_fragments
        )
        if baseline_build.get("config_inputs_sha256") != baseline_input_hash:
            raise ValueError("baseline config-input SHA-256 is not exact")
        if candidate_build.get("config_inputs_sha256") != candidate_input_hash:
            raise ValueError("candidate config-input SHA-256 is not exact")
        if baseline_build.get("config_sha256") != digest(baseline_config):
            raise ValueError("baseline resolved-config SHA-256 is not exact")
        if candidate_build.get("config_sha256") != digest(candidate_config):
            raise ValueError("candidate resolved-config SHA-256 is not exact")

        baseline_image = read(baseline / "Image", "baseline Image")
        baseline_image_gz = read(baseline / "Image.gz", "baseline Image.gz")
        candidate_image = read(candidate / "Image", "candidate Image")
        candidate_image_gz = read(candidate / "Image.gz", "candidate Image.gz")
        actual = {
            "baseline Image": digest(baseline_image),
            "baseline Image.gz": digest(baseline_image_gz),
            "candidate Image": digest(candidate_image),
            "candidate Image.gz": digest(candidate_image_gz),
            "candidate config": digest(candidate_config),
        }
        for label, value in expected.items():
            if actual[label] != value:
                raise ValueError(f"{label} SHA-256 is not pinned")
        if baseline_image == candidate_image or baseline_image_gz == candidate_image_gz:
            raise ValueError("candidate kernel payload did not change")

        baseline_dtbs = listed_files(baseline / "dtbs", "baseline DTBs")
        candidate_dtbs = listed_files(candidate / "dtbs", "candidate DTBs")
        if baseline_dtbs != candidate_dtbs:
            raise ValueError("DTB tree changed despite config-only kernel delta")
        base_dtb_name = "mediatek/mt6797-gemini-pda.dtb"
        if base_dtb_name not in baseline_dtbs:
            raise ValueError("Gemini base DTB is missing")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=usbdiag-clkignore-package-delta")
    print(f"baseline_profile={BASELINE_PROFILE}")
    print(f"candidate_profile={CANDIDATE_PROFILE}")
    print(f"source_sha256={candidate_build['source_sha256']}")
    print(f"patchset_sha256={candidate_build['patchset_sha256']}")
    print(f"baseline_config_sha256={digest(baseline_config)}")
    print(f"candidate_config_sha256={digest(candidate_config)}")
    print(f"resolved_config_delta_line={config_line}")
    print("resolved_config_delta=CONFIG_CMDLINE-append-clk_ignore_unused")
    print("config_cmdline_force=yes")
    print(f"baseline_image_sha256={digest(baseline_image)}")
    print(f"candidate_image_sha256={digest(candidate_image)}")
    print(f"baseline_image_gz_sha256={digest(baseline_image_gz)}")
    print(f"candidate_image_gz_sha256={digest(candidate_image_gz)}")
    print(f"gemini_base_dtb_sha256={digest(baseline_dtbs[base_dtb_name])}")
    print(f"dtb_file_count={len(baseline_dtbs)}")
    print("source_and_patchset_equal=yes")
    print("compiler_and_linker_equal=yes")
    print("dtb_tree_equal=yes")
    print("single_resolved_config_delta=passed")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
