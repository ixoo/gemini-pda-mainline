#!/usr/bin/env python3
"""Validate the exact runtime-proven-to-thermal serviceability DT transform."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import struct
from pathlib import Path


PARSER_SHA256 = "0bec8097f36e2831a19239810d4faf2d1f74fe480f80e9391ecad703ccdf9191"
BASE_SHA256 = "e1e4eca289320533bad5c879e78055eaa86a295080b1154c13debe29ddd8ee4a"
OUTPUT_SHA256 = "f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366"
BASE_MODEL = b"Planet Computers Gemini PDA\0"
OUTPUT_MODEL = b"Planet Computers Gemini PDA (thermal serviceability)\0"
THERMAL = "/thermal@1100b000"
ZONE_ROOT = "/thermal-zones"
ZONE = "/thermal-zones/soc-thermal"


class DtbError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_parser(repository: Path):
    path = repository / "experiments/2026-09-04-mt6797-thermal-stage-ledger/scripts/validate_package.py"
    if digest(path.read_bytes()) != PARSER_SHA256:
        raise DtbError("pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("thermal_stage_package_validator", path)
    if spec is None or spec.loader is None:
        raise DtbError("cannot load pinned FDT parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_fdt


def exact(props: dict[tuple[str, str], bytes], path: str, name: str, value: bytes) -> None:
    if props.get((path, name)) != value:
        raise DtbError(f"property mismatch: {path}:{name}")


def validate(repository: Path, base_path: Path, output_path: Path) -> None:
    base_data = base_path.read_bytes()
    output_data = output_path.read_bytes()
    if digest(base_data) != BASE_SHA256:
        raise DtbError("runtime-proven base DT identity changed")
    if digest(output_data) != OUTPUT_SHA256:
        raise DtbError("selected output DT identity changed")
    parse_fdt = load_parser(repository)
    base_nodes, base = parse_fdt(base_data)
    output_nodes, output = parse_fdt(output_data)
    if output_nodes - base_nodes != {ZONE_ROOT, ZONE} or base_nodes - output_nodes:
        raise DtbError("DT node delta is not exactly the thermal zone pair")

    allowed = {
        ("/", "model"),
        (THERMAL, "phandle"),
        (THERMAL, "resets"),
        (THERMAL, "status"),
        (ZONE, "polling-delay-passive"),
        (ZONE, "polling-delay"),
        (ZONE, "thermal-sensors"),
    }
    changed = {
        key for key in set(base) | set(output)
        if base.get(key) != output.get(key)
    }
    if changed != allowed:
        raise DtbError(f"unexpected property delta: {sorted(changed ^ allowed)}")

    exact(base, "/", "model", BASE_MODEL)
    exact(output, "/", "model", OUTPUT_MODEL)
    exact(base, THERMAL, "status", b"disabled\0")
    exact(output, THERMAL, "status", b"okay\0")
    exact(output, THERMAL, "phandle", struct.pack(">I", 0x2E))
    exact(output, THERMAL, "resets", struct.pack(">II", 3, 0))
    exact(output, ZONE, "polling-delay-passive", struct.pack(">I", 0))
    exact(output, ZONE, "polling-delay", struct.pack(">I", 1000))
    exact(output, ZONE, "thermal-sensors", struct.pack(">I", 0x2E))

    phandles = []
    for (path, name), value in output.items():
        if name in {"phandle", "linux,phandle"}:
            if len(value) != 4:
                raise DtbError(f"malformed phandle: {path}")
            phandles.append(struct.unpack(">I", value)[0])
    if phandles.count(0x2E) != 1 or len(phandles) != len(set(phandles)):
        raise DtbError("thermal phandle is absent or collides")
    if any(path.startswith("/__symbols__") for path in output_nodes):
        raise DtbError("compiled overlay symbols leaked into output DT")

    serviceability = (
        ("/t-phy@11290000", "status", b"okay\0"),
        ("/t-phy@11290000/usb-phy@11290800", "status", b"okay\0"),
        ("/usb@11271000", "status", b"okay\0"),
        ("/keyboard-matrix", "status", b"okay\0"),
        ("/mmc@11230000", "status", b"okay\0"),
        ("/pwrap@1000d000", "resets", struct.pack(">II", 3, 1)),
    )
    for path, name, value in serviceability:
        exact(base, path, name, value)
        exact(output, path, name, value)
    if "/chosen/framebuffer@7dfb0000" not in output_nodes:
        raise DtbError("runtime-proven simple framebuffer is absent")
    exact(output, "/adc@11001000", "status", b"disabled\0")
    exact(output, THERMAL, "nvmem-cell-names", b"calibration-data\0")
    if output[(THERMAL, "nvmem-cells")] != output[("/firmware/atag-devinfo/calibration-data@0", "phandle")]:
        raise DtbError("thermal calibration reference changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    validate(
        args.repository.resolve(strict=True),
        args.base.resolve(strict=True),
        args.output.resolve(strict=True),
    )
    print("validation=mt6797-thermal-serviceability-dt-repair")
    print(f"base_dtb_sha256={BASE_SHA256}")
    print(f"output_dtb_sha256={OUTPUT_SHA256}")
    print("changed_nodes=2")
    print("changed_properties=7")
    print("thermal_phandle=0x2e-unique")
    print("thermal_reset=phandle-3-input-0")
    print("thermal_controller=enabled")
    print("standalone_auxadc=disabled")
    print("thermal_zones=1-policy-free")
    print("usb_keyboard_pwrap_emmc_simplefb=preserved")
    print("hardware_action=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
