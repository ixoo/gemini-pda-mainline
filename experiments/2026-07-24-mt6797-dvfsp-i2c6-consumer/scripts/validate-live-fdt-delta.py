#!/usr/bin/env python3
"""Validate Candidate AP's private post-LK live FDT without emitting secrets."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import stat
import struct
import sys
from types import ModuleType


sys.dont_write_bytecode = True

COMMON_VALIDATOR_SHA256 = (
    "c836847e7c3294f34c7a7fbdec4f0472be3aaf0ad5f32326803ff9d7521aa65e"
)
FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
EXPECTED_LIVE_FDT_SHA256 = (
    "7b00d5eee94307d9f78e48ea0d3aeaf7081e54ffae98e89168596f6ee4e4d6a7"
)
EXPECTED_LIVE_FDT_SIZE = 52655

HANDOFF = "/dvfsp-handoff@11015000"
OBSERVER = "/dvfsp-observer@11015000"
I2C6 = "/i2c@1100e000"
INFRACFG = "/syscon@10001000"
DA9214 = I2C6 + "/regulator@68"
A72_POWER = "/a72-power@10222000"
LEGACY_DVFSP = "/dvfsp@11015000"
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"

DYNAMIC_CMDLINE_MAX_LENGTHS = {
    "bootargs": 508,
}
ATAG_CMDLINE_MAX_LENGTH = 516
ATAG_CMDLINE_TAG = 0x54410009


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[ModuleType, ModuleType, ModuleType]:
    script = pathlib.Path(__file__).resolve()
    identity_path = script.with_name("candidate_ap.py")
    common_path = (
        script.parents[2]
        / "2026-07-24-mt6797-dvfsp-handoff-observer"
        / "scripts"
        / "validate-live-fdt-delta.py"
    )
    parser_path = (
        script.parents[2]
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    for path, label in (
        (identity_path, "Candidate AP identity module"),
        (common_path, "source-pinned LK live-FDT validator"),
        (parser_path, "source-pinned FDT parser"),
    ):
        require_regular(path, label)
    if digest(common_path) != COMMON_VALIDATOR_SHA256:
        raise ValueError("source-pinned LK live-FDT validator changed")
    if digest(parser_path) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    return (
        load_module(identity_path, "candidate_ap_live_fdt_identity"),
        load_module(common_path, "candidate_ap_live_fdt_common"),
        load_module(parser_path, "candidate_ap_live_fdt_parser"),
    )


def require_dynamic_cmdline_shapes(
    common: ModuleType,
    live: dict[str, dict[str, bytes]],
) -> None:
    chosen = live.get("/chosen", {})
    atag = chosen.get("atag,cmdline")
    if (
        atag is None
        or len(atag) < 12
        or len(atag) > ATAG_CMDLINE_MAX_LENGTH
        or len(atag) % 4
    ):
        raise ValueError("post-LK ATAG command-line shape differs")
    words, tag = struct.unpack("<2I", atag[:8])
    if words * 4 != len(atag) or tag != ATAG_CMDLINE_TAG:
        raise ValueError("post-LK ATAG command-line header differs")
    payload = atag[8:]
    try:
        terminator = payload.index(0)
    except ValueError as exc:
        raise ValueError("post-LK ATAG command line is unterminated") from exc
    if (
        terminator < 1
        or terminator < len(payload) - 4
        or any(byte < 0x20 or byte > 0x7E for byte in payload[:terminator])
    ):
        raise ValueError("post-LK ATAG command-line payload shape differs")

    for name, maximum in DYNAMIC_CMDLINE_MAX_LENGTHS.items():
        value = chosen.get(name)
        if value is None:
            raise ValueError(f"post-LK dynamic command line is absent: {name}")
        common.cstring(value, f"/chosen:{name}")
        if not 2 <= len(value) <= maximum:
            raise ValueError(f"post-LK dynamic command-line shape differs: {name}")
    if payload[:terminator] != chosen["bootargs"][:-1]:
        raise ValueError("post-LK ATAG command line and bootargs differ")


def require_live_shapes(
    common: ModuleType,
    fdt: ModuleType,
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> None:
    require_dynamic_cmdline_shapes(common, live)

    # Candidate AN established the remaining exact LK shape contract. Its two
    # command-line properties are boot-specific printable strings, so validate
    # their real values above and substitute length-only redacted fixtures
    # while reusing the source-pinned common shape and range checks.
    redacted = dict(live)
    redacted["/chosen"] = dict(live["/chosen"])
    redacted["/chosen"]["atag,cmdline"] = (
        b"x" * (ATAG_CMDLINE_MAX_LENGTH - 1) + b"\0"
    )
    for name, length in DYNAMIC_CMDLINE_MAX_LENGTHS.items():
        redacted["/chosen"][name] = b"x" * (length - 1) + b"\0"
    common.require_live_shapes(fdt, artifact, redacted)


def require_handoff_contract(
    fdt: ModuleType,
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> None:
    if live.get(HANDOFF) != artifact.get(HANDOFF):
        raise ValueError("post-LK handoff node is not byte-exact Candidate AP")
    fdt.require_prop(
        live,
        HANDOFF,
        "compatible",
        fdt.string("mediatek,mt6797-dvfsp-handoff"),
    )
    fdt.require_prop(live, HANDOFF, "reg", fdt.cells(0, 0x11015000, 0, 0x1000))
    fdt.require_prop(live, HANDOFF, "clocks", fdt.cells(0x3, 0x36))
    fdt.require_prop(live, HANDOFF, "clock-names", fdt.string("i2c"))
    fdt.require_prop(live, HANDOFF, "mediatek,infracfg", fdt.cells(0x3))
    fdt.require_prop(live, HANDOFF, "status", fdt.string("okay"))
    fdt.require_prop(live, HANDOFF, "#access-controller-cells", fdt.cells(0))
    fdt.require_prop(live, HANDOFF, "phandle", fdt.cells(0x2C))
    fdt.require_prop(
        live,
        INFRACFG,
        "compatible",
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    fdt.require_prop(live, INFRACFG, "phandle", fdt.cells(0x3))
    resolved = [
        path
        for path, properties in live.items()
        if properties.get("phandle") == fdt.cells(0x3)
    ]
    if resolved != [INFRACFG]:
        raise ValueError("post-LK handoff phandle does not resolve exactly")

    fdt.require_prop(live, I2C6, "status", fdt.string("okay"))
    fdt.require_prop(live, I2C6, "access-controllers", fdt.cells(0x2C))
    access_resolved = [
        path
        for path, properties in live.items()
        if properties.get("phandle") == fdt.cells(0x2C)
    ]
    if access_resolved != [HANDOFF]:
        raise ValueError("post-LK access-controller phandle does not resolve exactly")
    if any(path.startswith(I2C6 + "/") for path in live):
        raise ValueError("post-LK I2C6 unexpectedly gained a child")
    for path in (DA9214, A72_POWER, LEGACY_DVFSP, OBSERVER):
        if path in live:
            raise ValueError(f"post-LK forbidden active-resource node exists: {path}")
    for cpu in (CPU8, CPU9):
        fdt.require_prop(
            live,
            cpu,
            "enable-method",
            fdt.string("mediatek,mt6797-psci"),
        )


def validate(
    artifact_path: pathlib.Path,
    live_path: pathlib.Path,
) -> dict[str, int | str]:
    require_regular(artifact_path, "Candidate AP artifact DTB")
    require_regular(live_path, "private post-LK live FDT")
    identity, common, fdt = load_inputs()
    identity.require_artifact_pins()
    if (
        re.fullmatch(r"[0-9a-f]{64}", EXPECTED_LIVE_FDT_SHA256) is None
        or not str(EXPECTED_LIVE_FDT_SIZE).isdecimal()
        or int(EXPECTED_LIVE_FDT_SIZE) <= 0
    ):
        raise ValueError("Candidate AP private live-FDT identity is not pinned")
    if digest(artifact_path) != identity.FINAL_DTB_SHA256:
        raise ValueError("artifact DTB is not exact Candidate AP")
    if digest(live_path) != EXPECTED_LIVE_FDT_SHA256:
        raise ValueError("private live FDT is not the audited Candidate AP capture")
    if live_path.stat().st_size != int(EXPECTED_LIVE_FDT_SIZE):
        raise ValueError("private live FDT size differs from its audited identity")

    artifact, artifact_reservations, artifact_boot_cpu = fdt.parse_fdt(artifact_path)
    live, live_reservations, live_boot_cpu = fdt.parse_fdt(live_path)
    if live_reservations != artifact_reservations:
        raise ValueError("LK changed the FDT header reservation map")
    if live_boot_cpu != artifact_boot_cpu:
        raise ValueError("LK changed boot_cpuid_phys")

    common.require_exact_delta(artifact, live)
    require_live_shapes(common, fdt, artifact, live)
    require_handoff_contract(fdt, artifact, live)

    structural_entries = (
        len(common.EXPECTED_ADDED_NODES)
        + len(common.EXPECTED_REMOVED_NODES)
        + len(common.EXPECTED_ADDED_PROPERTIES)
        + len(common.EXPECTED_CHANGED_PROPERTIES)
    )
    return {
        "artifact_nodes": len(artifact),
        "live_nodes": len(live),
        "structural_entries": structural_entries,
        "artifact_sha256": identity.FINAL_DTB_SHA256,
        "live_sha256": EXPECTED_LIVE_FDT_SHA256,
        "live_size": int(EXPECTED_LIVE_FDT_SIZE),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--live", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(args.artifact, args.live)
    except (OSError, RuntimeError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-ap-post-lk-live-fdt-allowlisted")
    print(f"artifact_dtb_sha256={result['artifact_sha256']}")
    print(f"live_fdt_sha256={result['live_sha256']}")
    print(f"live_fdt_size={result['live_size']}")
    print(f"artifact_nodes={result['artifact_nodes']}")
    print(f"live_nodes={result['live_nodes']}")
    print(f"structural_delta_entries={result['structural_entries']}")
    print("added_nodes=10")
    print("removed_nodes=2")
    print("added_properties_on_existing_nodes=23")
    print("changed_properties=2")
    print("fdt_header_reservations_and_boot_cpu=unchanged")
    print("lk_dynamic_metadata=shape-validated-values-not-emitted")
    print("dynamic_cmdlines=bounded-printable-equal-values-not-emitted")
    print("device_unique_serial=validated-in-memory-not-emitted")
    print("handoff_node=byte-exact-pre-lk-candidate-ap")
    print("handoff_clock=exact-infracfg-i2c-appm-54")
    print("handoff_access_controller=exact-phandle-0x2c")
    print("i2c6=enabled-childless-access-controlled")
    print("observer_da9214_a72_power_legacy_dvfsp_nodes=absent")
    print("cpu8_cpu9_enable_method=unchanged-fail-closed")
    print("unexpected_semantic_delta=none")
    print("device_access=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
