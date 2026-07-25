#!/usr/bin/env python3
"""Validate Candidate W's repository-derived kernel package foundation.

Run the repository's generic ``scripts/validate-kernel-artifact`` first.  This
validator adds the experiment-specific profile, patch-series, configuration,
and built-in-controller checks without pinning not-yet-known build outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


PROFILE = "observability-fbcon-rotation-keyboard-wrrd"
PATCH_COUNT = 87
LAST_PATCH = "v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
CONTROLLER_LINE = (
    '\t{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },'
)
CONTROLLER_DIFF = "\n".join(
    (
        "diff --git a/drivers/i2c/busses/i2c-mt65xx.c "
        "b/drivers/i2c/busses/i2c-mt65xx.c",
        "--- a/drivers/i2c/busses/i2c-mt65xx.c",
        "+++ b/drivers/i2c/busses/i2c-mt65xx.c",
        "@@ -527,6 +527,7 @@ static const struct of_device_id "
        "mtk_i2c_of_match[] = {",
        ' \t{ .compatible = "mediatek,mt2712-i2c", .data = &mt2712_compat },',
        ' \t{ .compatible = "mediatek,mt6577-i2c", .data = &mt6577_compat },',
        ' \t{ .compatible = "mediatek,mt6589-i2c", .data = &mt6589_compat },',
        f"+{CONTROLLER_LINE}",
        ' \t{ .compatible = "mediatek,mt7622-i2c", .data = &mt7622_compat },',
        ' \t{ .compatible = "mediatek,mt7981-i2c", .data = &mt7981_compat },',
        ' \t{ .compatible = "mediatek,mt7986-i2c", .data = &mt7986_compat },',
    )
)
EXPECTED_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
)
REQUIRED_CONFIG = frozenset(
    {
        "CONFIG_I2C=y",
        "CONFIG_I2C_MT65XX=y",
        "CONFIG_REGMAP_I2C=y",
        "CONFIG_PINCTRL_AW9523=y",
        "CONFIG_KEYBOARD_MATRIX=y",
        "CONFIG_FRAMEBUFFER_CONSOLE=y",
        "CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y",
        "CONFIG_FONT_TER16x32=y",
        "CONFIG_CMDLINE_FORCE=y",
        "# CONFIG_MODULES is not set",
        "# CONFIG_I2C_CHARDEV is not set",
    }
)
HEX256 = re.compile(r"^[0-9a-f]{64}$")
SYSTEM_MAP_MATCH = re.compile(
    r"^[0-9a-fA-F]+\s+[A-Za-z]\s+mtk_i2c_of_match$", re.MULTILINE
)
VIRTUAL_CONSOLE = re.compile(r"^console=tty[0-9]+$")


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_file(path: pathlib.Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{label} is missing or empty: {path}")


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def series_entries(series: pathlib.Path) -> list[str]:
    entries: list[str] = []
    for number, line in enumerate(
        series.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line or line.startswith("#"):
            continue
        candidate = pathlib.PurePosixPath(line)
        if (
            any(character.isspace() for character in line)
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) < 2
        ):
            raise ValueError(f"unsafe patch-series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        raise ValueError("duplicate patch-series entry")
    return entries


def patchset_digest(series: pathlib.Path, patch_root: pathlib.Path) -> str:
    records = [f"{digest(series)}  patches/series\n"]
    for entry in series_entries(series):
        patch = patch_root / entry
        require_file(patch, f"series patch {entry}")
        records.append(f"{digest(patch)}  {entry}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def config_inputs_digest(
    profile: str,
    base: str,
    fragments: tuple[str, ...],
    repo_root: pathlib.Path,
) -> str:
    records = [f"profile={profile}\n", f"base={base}\n"]
    for relative in fragments:
        fragment = repo_root / relative
        require_file(fragment, f"configuration fragment {relative}")
        records.append(f"{digest(fragment)}  {relative}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def validate_controller_patch(patch: pathlib.Path) -> None:
    text = patch.read_text(encoding="utf-8")
    source_diff: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            capture = True
        if capture and line == "-- ":
            break
        if capture:
            source_diff.append(line)
    if "\n".join(source_diff) != CONTROLLER_DIFF:
        raise ValueError("patch 0086 is not the exact one-line controller match")


def validate_patch_provenance(
    package: pathlib.Path, repo_root: pathlib.Path
) -> tuple[str, str]:
    repo_series = repo_root / "patches/series"
    packaged_series = package / "provenance/series"
    require_file(repo_series, "repository patch series")
    require_file(packaged_series, "packaged patch series")
    if packaged_series.read_bytes() != repo_series.read_bytes():
        raise ValueError("packaged patch series differs from the repository")

    entries = series_entries(repo_series)
    if len(entries) != PATCH_COUNT:
        raise ValueError(f"patch count is not exactly {PATCH_COUNT}")
    if entries[-1] != LAST_PATCH:
        raise ValueError(f"patch series does not end with {LAST_PATCH}")

    repo_patch_root = repo_root / "patches"
    packaged_patch_root = package / "provenance/patches"
    expected_inventory = set(entries)
    actual_inventory = {
        path.relative_to(packaged_patch_root).as_posix()
        for path in packaged_patch_root.rglob("*")
        if path.is_file()
    }
    if actual_inventory != expected_inventory:
        missing = sorted(expected_inventory - actual_inventory)
        extra = sorted(actual_inventory - expected_inventory)
        raise ValueError(
            "packaged patch inventory differs from the series: "
            f"missing={missing[:1]} extra={extra[:1]}"
        )
    for entry in entries:
        repository_patch = repo_patch_root / entry
        packaged_patch = packaged_patch_root / entry
        require_file(repository_patch, f"repository patch {entry}")
        if packaged_patch.read_bytes() != repository_patch.read_bytes():
            raise ValueError(f"packaged patch differs from repository: {entry}")

    validate_controller_patch(repo_patch_root / LAST_PATCH)
    repo_hash = patchset_digest(repo_series, repo_patch_root)
    packaged_hash = patchset_digest(packaged_series, packaged_patch_root)
    if packaged_hash != repo_hash:
        raise ValueError("packaged patchset identity differs from the repository")
    return repo_hash, digest(repo_patch_root / LAST_PATCH)


def validate_config_provenance(
    package: pathlib.Path,
    repo_root: pathlib.Path,
    manifest: dict[str, Any],
) -> str:
    try:
        profile = manifest["config"]["profiles"][PROFILE]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"manifest lacks profile {PROFILE}") from exc
    if not isinstance(profile, dict):
        raise ValueError("W profile is not an object")
    base = profile.get("base")
    fragments_value = profile.get("fragments")
    if base != "defconfig" or fragments_value != list(EXPECTED_FRAGMENTS):
        raise ValueError("W profile is not the exact ordered fragment stack")

    packaged_config_root = package / "provenance/configs"
    expected_names = {pathlib.PurePosixPath(item).name for item in EXPECTED_FRAGMENTS}
    if len(expected_names) != len(EXPECTED_FRAGMENTS):
        raise ValueError("W profile has colliding fragment basenames")
    actual_names = {
        path.relative_to(packaged_config_root).as_posix()
        for path in packaged_config_root.rglob("*")
        if path.is_file()
    }
    if actual_names != expected_names:
        raise ValueError("packaged configuration-fragment inventory changed")
    for relative in EXPECTED_FRAGMENTS:
        repo_fragment = repo_root / relative
        packaged_fragment = packaged_config_root / pathlib.PurePosixPath(relative).name
        require_file(repo_fragment, f"repository fragment {relative}")
        if packaged_fragment.read_bytes() != repo_fragment.read_bytes():
            raise ValueError(f"packaged configuration fragment differs: {relative}")

    return config_inputs_digest(PROFILE, base, EXPECTED_FRAGMENTS, repo_root)


def validate_resolved_config(config: pathlib.Path) -> tuple[str, str]:
    lines = config.read_text(encoding="utf-8").splitlines()
    line_set = set(lines)
    missing = sorted(REQUIRED_CONFIG - line_set)
    if missing:
        raise ValueError(f"required resolved configuration is missing: {missing[0]}")

    cmdline_lines = [line for line in lines if line.startswith("CONFIG_CMDLINE=")]
    if len(cmdline_lines) != 1:
        raise ValueError("resolved configuration must contain one CONFIG_CMDLINE")
    try:
        command_line = json.loads(cmdline_lines[0].split("=", 1)[1])
    except json.JSONDecodeError as exc:
        raise ValueError("CONFIG_CMDLINE is not a valid quoted string") from exc
    if not isinstance(command_line, str):
        raise ValueError("CONFIG_CMDLINE did not decode to text")
    tokens = command_line.split()

    virtual_consoles = [token for token in tokens if VIRTUAL_CONSOLE.fullmatch(token)]
    if virtual_consoles != ["console=tty2"]:
        raise ValueError("foreground logging console must be exactly tty2")
    if tokens.count("console=ttyS0,921600n8") != 1:
        raise ValueError("serial console contract changed")
    font_options = [token for token in tokens if token.startswith("fbcon=font:")]
    if font_options != ["fbcon=font:TER16x32"]:
        raise ValueError("forced command line must select exactly one TER16x32 font")
    for token in (
        "maxcpus=1",
        "rdinit=/init",
        "panic=0",
        "clk_ignore_unused",
        "fbcon=rotate:3",
        "consoleblank=0",
    ):
        if tokens.count(token) != 1:
            raise ValueError(f"forced command-line token is not exact: {token}")
    return command_line, digest(config)


def validate_built_in_identity(
    package: pathlib.Path, explicit_modinfo: pathlib.Path | None
) -> str:
    image = package / "Image"
    marker = b"mediatek,mt6797-i2c\x00"
    if marker not in image.read_bytes():
        raise ValueError("packaged Image lacks the built-in MT6797 I2C match string")

    candidates: list[pathlib.Path] = []
    if explicit_modinfo is not None:
        candidates.append(explicit_modinfo.resolve(strict=True))
    candidates.extend(
        path
        for path in (
            package / "modules.builtin.modinfo",
            package / "provenance/modules.builtin.modinfo",
        )
        if path.is_file()
    )
    if not candidates:
        return "not-packaged-image-string-present"
    aliases = candidates[0].read_bytes()
    if b"i2c_mt65xx.alias=of:N*T*Cmediatek,mt6797-i2c" not in aliases:
        raise ValueError("modules.builtin.modinfo lacks the MT6797 I2C OF alias")
    return "mt6797-of-alias-present"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument(
        "--built-in-modinfo",
        type=pathlib.Path,
        help="optional build-tree modules.builtin.modinfo for direct alias checking",
    )
    args = parser.parse_args()

    try:
        package = args.package.resolve(strict=True)
        manifest_path = args.manifest.resolve(strict=True)
        repo_root = manifest_path.parent.parent
        required_files = (
            package / "Image",
            package / "Image.gz",
            package / "System.map",
            package / "kernel.config",
            package / "SHA256SUMS",
            package / "provenance/build.json",
            package / "provenance/kernel-manifest.json",
            package / "provenance/series",
        )
        for path in required_files:
            require_file(path, "required package input")

        manifest = load_json(manifest_path, "repository kernel manifest")
        packaged_manifest_path = package / "provenance/kernel-manifest.json"
        if packaged_manifest_path.read_bytes() != manifest_path.read_bytes():
            raise ValueError("packaged kernel manifest differs from the repository")
        if manifest.get("architecture") != "arm64":
            raise ValueError("kernel architecture pin is not arm64")
        if manifest.get("patch_series") != "patches/series":
            raise ValueError("manifest patch-series path changed")
        kernel = manifest.get("kernel")
        if not isinstance(kernel, dict) or kernel.get("version") != "7.1.3":
            raise ValueError("kernel version pin is not Linux 7.1.3")
        source_sha256 = kernel.get("sha256")
        if (
            not isinstance(source_sha256, str)
            or HEX256.fullmatch(source_sha256) is None
        ):
            raise ValueError("kernel source SHA-256 pin is invalid")

        patchset_sha256, controller_patch_sha256 = validate_patch_provenance(
            package, repo_root
        )
        config_inputs_sha256 = validate_config_provenance(
            package, repo_root, manifest
        )
        command_line, config_sha256 = validate_resolved_config(
            package / "kernel.config"
        )

        build = load_json(package / "provenance/build.json", "build provenance")
        expected_package_name = (
            f"linux-7.1.3-gemini-{PROFILE}-"
            f"{patchset_sha256[:8]}-{config_inputs_sha256[:8]}"
        )
        if package.name != expected_package_name:
            raise ValueError(
                "package basename does not match current patch/config identities"
            )
        if build.get("schema") != 1:
            raise ValueError("build provenance schema changed")
        if build.get("build_profile") != PROFILE:
            raise ValueError("package was not built with the Candidate W profile")
        if build.get("base_config") != "defconfig":
            raise ValueError("package base configuration changed")
        if build.get("config_fragments") != list(EXPECTED_FRAGMENTS):
            raise ValueError("package configuration-fragment order changed")
        if build.get("source_sha256") != source_sha256:
            raise ValueError("package source identity differs from the manifest")
        if build.get("patchset_sha256") != patchset_sha256:
            raise ValueError("package patchset differs from the current repository")
        if build.get("config_inputs_sha256") != config_inputs_sha256:
            raise ValueError("package config inputs differ from the current repository")
        if build.get("config_sha256") != config_sha256:
            raise ValueError("package resolved-config digest is inconsistent")
        if build.get("modules_built") is not False:
            raise ValueError("Candidate W package must remain built-in-only")
        if build.get("kernel_release") != "7.1.3-gemini-observability-L":
            raise ValueError("kernel release changed from the observability foundation")
        if not isinstance(build.get("compiler"), str) or not build["compiler"]:
            raise ValueError("compiler identity is missing")
        if not isinstance(build.get("linker"), str) or not build["linker"]:
            raise ValueError("linker identity is missing")

        system_map_text = (package / "System.map").read_text(
            encoding="utf-8", errors="replace"
        )
        if SYSTEM_MAP_MATCH.search(system_map_text) is None:
            raise ValueError("System.map lacks built-in mtk_i2c_of_match")
        alias_result = validate_built_in_identity(package, args.built_in_modinfo)

        print("validation=candidate-w-kernel-package-foundation")
        print(f"package={expected_package_name}")
        print(f"build_profile={PROFILE}")
        print(f"source_sha256={source_sha256}")
        print(f"patchset_sha256={patchset_sha256}")
        print(f"controller_patch_sha256={controller_patch_sha256}")
        print(f"patch_count={PATCH_COUNT}")
        print(f"config_inputs_sha256={config_inputs_sha256}")
        print(f"config_sha256={config_sha256}")
        print(f"forced_cmdline={command_line}")
        print("controller_match=mediatek,mt6797-i2c-to-mt8173-compat")
        print(f"built_in_alias={alias_result}")
        print("package_source_match=manifest-series-patches-configs")
        print("generic_artifact_validation=required-separately")
        print("hardware_write=none")
        return 0
    except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
