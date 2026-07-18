#!/usr/bin/env python3
"""Validate Candidate O's exact N kernel/DT CPU1-7 sweep foundation."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import pathlib
import sys


CPUS = "/cpus"
PSCI = "/psci"
WATCHDOG = "/watchdog@10007000"
CPU_LAYOUT = (
    (0, "0", "arm,cortex-a53", 0x000),
    (1, "1", "arm,cortex-a53", 0x001),
    (2, "2", "arm,cortex-a53", 0x002),
    (3, "3", "arm,cortex-a53", 0x003),
    (4, "100", "arm,cortex-a53", 0x100),
    (5, "101", "arm,cortex-a53", 0x101),
    (6, "102", "arm,cortex-a53", 0x102),
    (7, "103", "arm,cortex-a53", 0x103),
    (8, "200", "arm,cortex-a72", 0x200),
    (9, "201", "arm,cortex-a72", 0x201),
)
EXPECTED_IMAGE_GZ_SHA256 = (
    "0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3"
)
EXPECTED_DTB_SHA256 = (
    "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379"
)
EXPECTED_CONFIG_SHA256 = (
    "5a0c442c67b64cbabd4d030c93d50837bfc93e34d8878b413805457bfcd8e7cd"
)
EXPECTED_CMDLINE = (
    'CONFIG_CMDLINE="console=tty0 console=ttyS0,921600n8 earlycon maxcpus=1 '
    "nokaslr ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug "
    "rdinit=/init panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    'g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused"'
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_fdt_validator() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    spec = importlib.util.spec_from_file_location("gemini_lk_fdt_validator", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_config(image_gz: bytes) -> bytes:
    image = gzip.decompress(image_gz)
    start_magic = b"IKCFG_ST"
    end_magic = b"IKCFG_ED"
    start = image.find(start_magic)
    if start < 0:
        raise ValueError("Image lacks IKCONFIG start marker")
    start += len(start_magic)
    end = image.find(end_magic, start)
    if end < 0:
        raise ValueError("Image lacks IKCONFIG end marker")
    if image.find(start_magic, start) >= 0:
        raise ValueError("Image contains multiple IKCONFIG start markers")
    return gzip.decompress(image[start:end])


def parse_config(config: bytes) -> set[str]:
    try:
        text = config.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("embedded kernel config is not UTF-8") from exc
    return set(text.splitlines())


def validate(image_path: pathlib.Path, dtb_path: pathlib.Path) -> int:
    image_gz = image_path.read_bytes()
    dtb_data = dtb_path.read_bytes()
    if digest(image_gz) != EXPECTED_IMAGE_GZ_SHA256:
        raise ValueError("Image.gz is not exact Candidate N")
    if digest(dtb_data) != EXPECTED_DTB_SHA256:
        raise ValueError("DTB is not exact Candidate N")

    config = extract_config(image_gz)
    if digest(config) != EXPECTED_CONFIG_SHA256:
        raise ValueError("embedded config is not exact Candidate N")
    lines = parse_config(config)
    required = {
        "CONFIG_IKCONFIG=y",
        "CONFIG_IKCONFIG_PROC=y",
        "CONFIG_SMP=y",
        "CONFIG_HOTPLUG_CPU=y",
        "CONFIG_ARM_PSCI_FW=y",
        "CONFIG_SYSFS=y",
        "CONFIG_WATCHDOG=y",
        "CONFIG_MEDIATEK_WATCHDOG=y",
        "CONFIG_CMDLINE_FORCE=y",
        EXPECTED_CMDLINE,
    }
    missing = sorted(required - lines)
    if missing:
        raise ValueError("embedded config lacks exact requirements: " + ", ".join(missing))
    nr_cpus_line = next((line for line in lines if line.startswith("CONFIG_NR_CPUS=")), "")
    if not nr_cpus_line:
        raise ValueError("embedded config lacks CONFIG_NR_CPUS")
    try:
        nr_cpus = int(nr_cpus_line.split("=", 1)[1])
    except ValueError as exc:
        raise ValueError("embedded CONFIG_NR_CPUS is invalid") from exc
    if nr_cpus < 10:
        raise ValueError("embedded CONFIG_NR_CPUS cannot represent all Gemini CPUs")

    fdt = load_fdt_validator()
    tree, _, _ = fdt.parse_fdt(dtb_path)
    fdt.require_prop(tree, CPUS, "#address-cells", fdt.cells(1))
    fdt.require_prop(tree, CPUS, "#size-cells", fdt.cells(0))
    for logical, node_name, compatible, mpidr in CPU_LAYOUT:
        path = f"{CPUS}/cpu@{node_name}"
        fdt.require_prop(tree, path, "device_type", fdt.string("cpu"))
        fdt.require_prop(tree, path, "compatible", fdt.string(compatible))
        fdt.require_prop(tree, path, "enable-method", fdt.string("psci"))
        fdt.require_prop(tree, path, "reg", fdt.cells(mpidr))
        if logical <= 7 and compatible != "arm,cortex-a53":
            raise ValueError(f"logical CPU{logical} is not in the A53 sweep set")
        if logical >= 8 and compatible != "arm,cortex-a72":
            raise ValueError(f"logical CPU{logical} is not in the deferred A72 set")
    fdt.require_prop(tree, PSCI, "compatible", fdt.string("arm,psci-0.2"))
    fdt.require_prop(tree, PSCI, "method", fdt.string("smc"))
    if "interrupts" in tree[WATCHDOG]:
        raise ValueError("exact Candidate N watchdog unexpectedly has an interrupt")
    return nr_cpus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        nr_cpus = validate(args.image_gz, args.dtb)
    except (EOFError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=a53-sweep-foundation")
    print(f"image_gz_sha256={EXPECTED_IMAGE_GZ_SHA256}")
    print(f"dtb_sha256={EXPECTED_DTB_SHA256}")
    print(f"config_sha256={EXPECTED_CONFIG_SHA256}")
    print("forced_maxcpus=1")
    print("config_smp=y")
    print("config_hotplug_cpu=y")
    print("config_arm_psci_fw=y")
    print(f"config_nr_cpus={nr_cpus}")
    for logical, node_name, compatible, mpidr in CPU_LAYOUT:
        role = "sweep" if logical in range(1, 8) else "boot" if logical == 0 else "deferred"
        print(
            f"cpu{logical}=cpu@{node_name},compatible={compatible},"
            f"mpidr=0x{mpidr:x},enable_method=psci,role={role}"
        )
    print("psci_method=smc")
    print("watchdog_interrupts=absent")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
