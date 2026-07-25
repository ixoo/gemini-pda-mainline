#!/usr/bin/env python3
"""Validate Candidate AO's canonical Android-v0 container and safety boundary."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import pathlib
import stat
import struct
import subprocess
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True

import candidate_ao as ao


PAGE_SIZE = 2048
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"
KERNEL_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr '
    "ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init "
    "panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    'regulator_ignore_unused initcall_blacklist=mt6797_a72_power_driver_init"'
)
REQUIRED_IMAGE_MARKERS = (
    b"mediatek,mt6797-dvfsp-handoff\0",
    b"mt6797-dvfsp-handoff\0",
    b"state=validating operation=one-way-handoff i2c6_policy=disabled\n\0",
    b"initial-gate-already-gated\0",
    b"late-revalidation-failed\0",
    b"state=provisional normalization=ungated-to-gated ",
    b"state=ready normalization=ungated-to-gated ",
    b"sample=%s timer=%08x/%08x con0=%08x con1=%08x ",
    b"i2c6_policy=disabled\n\0",
)
FORBIDDEN_IMAGE_MARKERS = (
    b"mediatek,mt6797-dvfsp-handoff-observer\0",
    b"mt6797-dvfsp-handoff-observer\0",
    b"mediatek,mt6797-dvfsp\0",
    b"quiescent-stopped\0",
    b"active-v1\n\0",
    b"fixed-vproc-firmware-clock\n\0",
    b"CPU%u fixed-state A72 power sequence prepared\n\0",
)
REQUIRED_AUDIT_RESULTS = {
    "audit=mt6797-dvfsp-one-way-handoff",
    "probe_present=yes",
    "clk_prepare_enable_calls=1",
    "clk_disable_unprepare_calls=1",
    "every_successful_enable_balanced=yes",
    "late_worker_clock_mutation=absent",
    "direct_mmio_write=absent",
    "regmap_write_or_update=absent",
    "i2c_regulator_cpu_control_calls=absent",
    "restart_unpause_userspace_api=absent",
    "remove_or_unbind_path=absent",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def put_string(header: bytearray, offset: int, size: int, value: str) -> None:
    encoded = value.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("canonical string is oversized")
    header[offset : offset + size] = encoded + b"\0" * (size - len(encoded))


def validate_config(data: bytes) -> None:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("kernel configuration is not ASCII") from exc
    symbols: set[str] = set()
    for line in lines:
        if line.startswith("CONFIG_") and "=" in line:
            symbol = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            symbol = line[2:-11]
        else:
            continue
        if symbol in symbols:
            raise ValueError(f"kernel configuration duplicates {symbol}")
        symbols.add(symbol)
    required = {
        "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
        "CONFIG_MTK_MT6797_A72_POWER=y",
        "CONFIG_CMDLINE_FORCE=y",
        "# CONFIG_SUSPEND is not set",
        "# CONFIG_MODULES is not set",
        KERNEL_CMDLINE,
    }
    missing = sorted(required - set(lines))
    if missing:
        raise ValueError("kernel configuration contract changed: " + missing[0])
    forbidden = {
        "CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER=y",
        "CONFIG_SUSPEND=y",
        "CONFIG_MODULES=y",
    }
    present = sorted(forbidden & set(lines))
    if present:
        raise ValueError("kernel configuration enables forbidden policy: " + present[0])


def parse_system_map(data: bytes) -> set[str]:
    try:
        symbols = {
            line.split(maxsplit=2)[2]
            for line in data.decode("ascii").splitlines()
            if len(line.split(maxsplit=2)) == 3
        }
    except UnicodeError as exc:
        raise ValueError("System.map is not ASCII") from exc
    return symbols


def validate_system_map(data: bytes) -> None:
    symbols = parse_system_map(data)
    required = {
        "mt6797_dvfsp_handoff_probe",
        "mt6797_dvfsp_late_work",
        "mt6797_dvfsp_handoff_driver",
        "mt6797_dvfsp_handoff_driver_init",
        "mt6797_a72_power_driver_init",
    }
    missing = sorted(required - symbols)
    if missing:
        raise ValueError("System.map lacks Candidate AO owner symbol: " + missing[0])
    forbidden = {
        "mt6797_dvfsp_observer_probe",
        "mt6797_dvfsp_observer_driver",
        "mt6797_dvfsp_observer_driver_init",
        "mt6797_dvfsp_handoff_remove",
        "mt6797_a72_power_cpu_boot_ready",
        "mt6797_a72_power_cpu_on_complete",
        "mt6797_a72_power_cpu_on_failed",
        "mt6797_a72_power_prepare_first",
        "mt6797_a72_power_cpu_startup",
        "mt6797_a72_power_cpu_teardown",
    }
    present = sorted(forbidden & symbols)
    if present:
        raise ValueError("forbidden control symbol is present: " + present[0])
    writable = sorted(
        symbol
        for symbol in symbols
        if symbol.startswith("mt6797_dvfsp_") and symbol.endswith("_store")
    )
    if writable:
        raise ValueError("DVFSP owner exposes a writable callback: " + writable[0])
    observer = sorted(symbol for symbol in symbols if "dvfsp_observer" in symbol)
    if observer:
        raise ValueError("old DVFSP observer remains compiled: " + observer[0])


def run_dtb_validator(
    script_dir: pathlib.Path, ah_dtb: pathlib.Path, candidate_dtb: pathlib.Path
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(script_dir / "validate-dtb-delta.py"),
            "--ah",
            os.fspath(ah_dtb),
            "--candidate",
            os.fspath(candidate_dtb),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError("final DT semantic validator rejected Candidate AO: " + detail)


def run_compiled_audit(
    script_dir: pathlib.Path, image: bytes, system_map: pathlib.Path
) -> bytes:
    auditor = script_dir / "audit-compiled-handoff.py"
    read_regular(auditor, "compiled-handoff auditor")
    with tempfile.TemporaryDirectory(prefix="candidate-ao-audit-") as temporary:
        image_path = pathlib.Path(temporary) / "Image"
        image_path.write_bytes(image)
        image_path.chmod(0o600)
        result = subprocess.run(
            [
                sys.executable,
                os.fspath(auditor),
                "--image",
                os.fspath(image_path),
                "--system-map",
                os.fspath(system_map),
            ],
            check=False,
            capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    if result.returncode:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
            or "no diagnostic"
        )
        raise ValueError("compiled one-way handoff auditor rejected kernel: " + detail)
    try:
        lines = set(result.stdout.decode("ascii").splitlines())
    except UnicodeError as exc:
        raise ValueError("compiled-handoff audit is not ASCII") from exc
    missing = sorted(REQUIRED_AUDIT_RESULTS - lines)
    if missing:
        raise ValueError("compiled-handoff audit result changed: " + missing[0])
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--system-map", required=True, type=pathlib.Path)
    parser.add_argument("--kernel-config", required=True, type=pathlib.Path)
    parser.add_argument("--dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ah-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "Candidate AO boot")
        image_gz = read_regular(args.image_gz, "Candidate AO Image.gz")
        system_map = read_regular(args.system_map, "Candidate AO System.map")
        kernel_config = read_regular(args.kernel_config, "Candidate AO config")
        dtb = read_regular(args.dtb, "Candidate AO final DT")
        ah_dtb = read_regular(args.ah_dtb, "exact Candidate AH final DT")
        initramfs = read_regular(args.initramfs, "exact Candidate AH initramfs")

        if digest(ah_dtb) != ao.AH_DTB_SHA256:
            raise ValueError("exact Candidate AH final DT changed")
        pin_state = ao.artifact_pin_state()
        if pin_state == "source-pinned" and digest(dtb) != ao.FINAL_DTB_SHA256:
            raise ValueError("Candidate AO final-DT identity changed")
        if digest(initramfs) != ao.INITRAMFS_SHA256:
            raise ValueError("Candidate AO initramfs is not byte-exact Candidate AH")
        validate_config(kernel_config)
        validate_system_map(system_map)
        script_dir = pathlib.Path(__file__).resolve().parent
        run_dtb_validator(script_dir, args.ah_dtb, args.dtb)

        image = gzip.decompress(image_gz)
        for marker in REQUIRED_IMAGE_MARKERS:
            if marker not in image:
                raise ValueError(
                    f"Candidate AO kernel lacks handoff-owner marker: {marker!r}"
                )
        for marker in FORBIDDEN_IMAGE_MARKERS:
            if marker in image:
                raise ValueError(
                    f"Candidate AO kernel contains forbidden marker: {marker!r}"
                )
        compiled_audit = run_compiled_audit(script_dir, image, args.system_map)

        if not 0 < len(candidate) <= ao.BOOT2_SIZE:
            raise ValueError("Candidate AO size is invalid or exceeds boot2")
        if len(candidate) < PAGE_SIZE or candidate[:8] != b"ANDROID!":
            raise ValueError("Candidate AO is not Android boot image v0")
        fields = struct.unpack_from("<10I", candidate, 8)
        (
            kernel_size,
            kernel_addr,
            ramdisk_size,
            ramdisk_addr,
            second_size,
            second_addr,
            tags_addr,
            page_size,
            dt_size,
            unused,
        ) = fields
        if (
            kernel_addr != KERNEL_ADDR
            or ramdisk_addr != RAMDISK_ADDR
            or second_addr != SECOND_ADDR
            or tags_addr != TAGS_ADDR
            or page_size != PAGE_SIZE
            or second_size
            or dt_size
            or unused
        ):
            raise ValueError("Android-v0 address or layout contract changed")

        kernel = image_gz + dtb
        if kernel_size != len(kernel) or ramdisk_size != len(initramfs):
            raise ValueError("Android-v0 payload sizes changed")
        kernel_offset = PAGE_SIZE
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if candidate[kernel_offset:kernel_end] != kernel:
            raise ValueError("kernel field is not AO Image.gz plus final AO DT")
        if candidate[ramdisk_offset:ramdisk_end] != initramfs:
            raise ValueError("ramdisk field is not byte-exact Candidate AH initramfs")
        if any(candidate[kernel_end:ramdisk_offset]) or any(candidate[ramdisk_end:]):
            raise ValueError("Android-v0 padding is not zero")
        if len(candidate) != align(ramdisk_end):
            raise ValueError("Android-v0 trailing length changed")

        image_id = hashlib.sha1(usedforsecurity=False)
        for payload in (kernel, initramfs, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header = bytearray(PAGE_SIZE)
        struct.pack_into("<8s10I", expected_header, 0, b"ANDROID!", *fields)
        put_string(expected_header, 48, 16, NAME)
        command_line = CMDLINE.encode("ascii")
        expected_header[64:576] = command_line[:512].ljust(512, b"\0")
        expected_header[608:1632] = command_line[512:].ljust(1024, b"\0")
        expected_header[576:596] = image_id.digest()
        if candidate[:PAGE_SIZE] != expected_header:
            raise ValueError("Android-v0 header is not canonical")

        print("validation=candidate-ao-mt6797-dvfsp-handoff-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={digest(image_gz)}")
        print(f"system_map_sha256={digest(system_map)}")
        print(f"config_sha256={digest(kernel_config)}")
        print(f"dtb_sha256={digest(dtb)}")
        print(f"initramfs_sha256={ao.INITRAMFS_SHA256}")
        print(f"compiled_handoff_audit_sha256={digest(compiled_audit)}")
        print("dtb_lineage=exact-candidate-ah-plus-one-way-handoff-owner-only")
        print("handoff_normalization=one-way-ccf-temporary-reference")
        print("ccf_normalization_attempts_max=1")
        print("handoff_retry=none")
        print("successful_ccf_enable_disable_balanced=yes")
        print("late_read_only_revalidation_ms=45000")
        print("i2c6=disabled")
        print("da9214_node=absent")
        print("a72_power_node=absent")
        print("cpu_operation=none")
        print("regulator_operation=none")
        print("storage_access=none")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        for line in compiled_audit.decode("ascii").splitlines():
            print(f"compiled_{line}")
        return 0
    except (
        OSError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        subprocess.SubprocessError,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
