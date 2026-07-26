#!/usr/bin/env python3
"""Validate Candidate AT's canonical Android-v0 container and safety boundary."""

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

import candidate_emmc as ar


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
    "regulator_ignore_unused initcall_blacklist=mt6797_a72_power_driver_init "
    'fw_devlink=rpm"'
)
REQUIRED_IMAGE_MARKERS = (
    b"mediatek,mt6797-dvfsp-handoff\0",
    b"mt6797-dvfsp-handoff\0",
    b"i2c6_policy=requires-ready",
    b"initial-gate-already-gated\0",
    b"late-revalidation-failed\0",
    b"state=provisional normalization=ungated-to-gated ",
    b"state=ready normalization=ungated-to-gated ",
    b"sample=%s timer=%08x/%08x con0=%08x con1=%08x ",
    b"dma_gate_valid=%u dma_gate=%08x",
    b"state=%s reason=%s initial_gate=%s supplier_bound=yes access_grant=%s ",
    b"suspend_checks=%d suspend_failures=%d resume_checks=%d ",
    b"pm_fault=%s consumer_ungated_checks=%d ",
    b"cleanup_attempts=%u cleanup_samples=%u cleanup_pcm_failures=%u ",
    b"cleanup_main_failures=%u cleanup_dma_invalid=%u cleanup_dma_gated=%u ",
    b"cleanup_selected=%u cleanup_result=%s ",
    b"attempts=%u samples=%u pcm_failures=%u main_failures=%u "
    b"dma_invalid=%u dma_gated=%u dma_unchanged=%u selected=%u result=%s\n",
    b"i=%02u main_valid=%d main=%08x dma_valid=%d dma=%08x\n",
    b"consumer_clock_check=held clocks=i2c-appm,ap-dma validation=passed ",
    b"consumer_clock_check=cleanup clocks=i2c-appm shared-ap-dma=preserved validation=passed ",
    b"supplier_bound=yes access_grant=ready state=ready late_validation=passed "
    b"access_controller=enabled",
    b"supplier_bound=yes access_grant=denied state=%s reason=%s "
    b"access_controller=enabled\n",
    b"GEMINI_MT6797_I2C6_GUARD handoff=ready "
    b"probe_attempts=%d init_attempts=%d ",
    b"clock_domains=i2c-appm,ap-dma ",
    b"runtime_pm_link=%d ",
    b"transfer_attempts=%d dma_starts=%d "
    b"nonzero_starts=%d irq_count=%d",
    b"GEMINI_MT6797_I2C6_GUARD handoff=denied "
    b"probe_attempts=%d reason=supplier-not-ready\n",
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
    "audit=mt6797-dvfsp-i2c6-consumer",
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
    "access_controller_exports=compiled",
    "access_controller_phandle_parser=compiled-inlined-wrapper-target",
    "pre_mmio_authorization_order=yes",
    "i2c_mmio_resources=two-after-ready",
    "consumer_clock_validation_order=compiled-cfg-held-disable-cleanup",
    "transfer_readiness_precedes_regulator_enable=yes",
    "explicit_device_link_add=compiled",
    "device_link_flags=autoremove-consumer-plus-pm-runtime-source-pinned",
    "explicit_add_clears_inferred=linux-7.1.3-source-pinned-core",
    "adapter_registration_precedes_status_publication=yes",
    "i2c_instrumentation_boundary_formats=compiled",
    "i2c_do_transfer_layout=fully-inlined-into-mtk_i2c_transfer",
    "i2c_transfer_region_words=542",
    (
        "i2c_inlined_transfer_call_geometry="
        "4-buffers-4-dma-maps-15-writew-1-wait-2-reinit"
    ),
    "instrumentation_sites=source-pinned-patch-contract",
    "cleanup_oracle=32-samples-31-intervals-all-valid-dma-gate-preserved-source-pinned",
    "read_only_dma_gate=infra1-0x094-bit18-source-pinned",
    "runtime_pm_link_publication=compiled",
    "protected_noirq_bypass=source-pinned-patch-contract",
    "pm_callbacks=disabled-config",
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
        "# CONFIG_CPU_IDLE is not set",
        "# CONFIG_MODULES is not set",
        "CONFIG_MMC=y",
        "CONFIG_MMC_BLOCK=y",
        "CONFIG_MMC_MTK=y",
        KERNEL_CMDLINE,
    }
    missing = sorted(required - set(lines))
    if missing:
        raise ValueError("kernel configuration contract changed: " + missing[0])
    unavailable_power = {
        "CONFIG_CPU_PM",
        "CONFIG_ARCH_HIBERNATION_POSSIBLE",
        "CONFIG_HIBERNATION",
    }
    present_unavailable = sorted(unavailable_power & symbols)
    if present_unavailable:
        raise ValueError(
            "kernel configuration unexpectedly resolves unavailable power policy: "
            + present_unavailable[0]
        )
    forbidden = {
        "CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER=y",
        "CONFIG_SUSPEND=y",
        "CONFIG_HIBERNATION=y",
        "CONFIG_PM_AUTOSLEEP=y",
        "CONFIG_PM_USERSPACE_AUTOSLEEP=y",
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
        "mt6797_dvfsp_handoff_get",
        "mt6797_dvfsp_handoff_require_ready",
        "mt6797_dvfsp_handoff_is_ready_atomic",
        "mt6797_dvfsp_handoff_validate_clock",
        "mt6797_dvfsp_handoff_validate_clock_pm",
        "mtk_i2c_probe",
        "mtk_i2c_init_hw",
        "mtk_i2c_transfer",
        "mtk_i2c_irq",
        "mt6797_a72_power_driver_init",
        "da9211_i2c_probe",
        "da9214_read_signature",
        "da9214_read_legacy_page2_reg",
        "msdc_drv_probe",
    }
    missing = sorted(required - symbols)
    if missing:
        raise ValueError("System.map lacks Candidate AT owner symbol: " + missing[0])
    if "mtk_i2c_do_transfer" in symbols:
        raise ValueError(
            "Candidate AT transfer helper is not fully inlined as compiled-audited"
        )
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
    script_dir: pathlib.Path, ao_dtb: pathlib.Path, candidate_dtb: pathlib.Path
) -> None:
    validator = script_dir / "validate-dtb-delta-emmc.py"
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(validator),
            "--ao",
            os.fspath(ao_dtb),
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
        raise ValueError("final DT semantic validator rejected Candidate AT: " + detail)


def run_compiled_audit(
    script_dir: pathlib.Path, image: bytes, system_map: pathlib.Path
) -> bytes:
    auditor = script_dir / "audit-compiled-handoff-emmc.py"
    auditor_data = read_regular(auditor, "compiled-handoff auditor")
    if digest(auditor_data) != ar.COMPILED_HANDOFF_AUDITOR_SHA256:
        raise ValueError("source-pinned compiled-handoff auditor changed")
    with tempfile.TemporaryDirectory(prefix="candidate-at-audit-") as temporary:
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
        raise ValueError("compiled AT dependency auditor rejected kernel: " + detail)
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
    parser.add_argument("--ao-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "Candidate AT boot")
        image_gz = read_regular(args.image_gz, "Candidate AT Image.gz")
        system_map = read_regular(args.system_map, "Candidate AT System.map")
        kernel_config = read_regular(args.kernel_config, "Candidate AT config")
        dtb = read_regular(args.dtb, "Candidate AT final DT")
        ao_dtb = read_regular(args.ao_dtb, "exact Candidate AO final DT")
        initramfs = read_regular(args.initramfs, "exact Candidate AO initramfs")

        if digest(ao_dtb) != ar.AO_DTB_SHA256:
            raise ValueError("exact Candidate AO final DT changed")
        pin_state = ar.artifact_pin_state()
        if pin_state == "source-pinned" and digest(dtb) != ar.FINAL_DTB_SHA256:
            raise ValueError("Candidate AT final-DT identity changed")
        if digest(initramfs) != ar.INITRAMFS_SHA256:
            raise ValueError("Candidate AT initramfs is not byte-exact Candidate AO")
        validate_config(kernel_config)
        validate_system_map(system_map)
        script_dir = pathlib.Path(__file__).resolve().parent
        run_dtb_validator(script_dir, args.ao_dtb, args.dtb)

        image = gzip.decompress(image_gz)
        for marker in REQUIRED_IMAGE_MARKERS:
            if marker not in image:
                raise ValueError(
                    f"Candidate AT kernel lacks handoff-owner marker: {marker!r}"
                )
        for marker in FORBIDDEN_IMAGE_MARKERS:
            if marker in image:
                raise ValueError(
                    f"Candidate AT kernel contains forbidden marker: {marker!r}"
                )
        compiled_audit = run_compiled_audit(script_dir, image, args.system_map)

        if not 0 < len(candidate) <= ar.BOOT2_SIZE:
            raise ValueError("Candidate AT size is invalid or exceeds boot2")
        if len(candidate) < PAGE_SIZE or candidate[:8] != b"ANDROID!":
            raise ValueError("Candidate AT is not Android boot image v0")
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
            raise ValueError("kernel field is not AT Image.gz plus final AT DT")
        if candidate[ramdisk_offset:ramdisk_end] != initramfs:
            raise ValueError("ramdisk field is not byte-exact Candidate AO initramfs")
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

        print("validation=candidate-at-emmc-development-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={digest(image_gz)}")
        print(f"system_map_sha256={digest(system_map)}")
        print(f"config_sha256={digest(kernel_config)}")
        print(f"dtb_sha256={digest(dtb)}")
        print(f"initramfs_sha256={ar.INITRAMFS_SHA256}")
        print(f"compiled_handoff_audit_sha256={digest(compiled_audit)}")
        print("dtb_lineage=exact-ao-plus-access-controlled-legacy-da9214-i2c6")
        print("handoff_access_controller=compiled")
        print("fw_devlink=rpm")
        print("installed_system_sleep=disabled")
        print("pm_callback_compile_audit=separate-noninstalled-profile")
        print("suspend_request=none")
        print("i2c6=enabled-with-legacy-da9214-child")
        print("i2c6_transfer_start_irq=runtime-must-remain-zero")
        print("da9214_node=present-read-only-identity")
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
