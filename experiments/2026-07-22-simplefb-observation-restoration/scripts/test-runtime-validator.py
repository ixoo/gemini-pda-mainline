#!/usr/bin/env python3
"""Exercise Candidate AG's runtime validator with one pass and focused rejects."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile


BOOT_ID = "123e4567-e89b-42d3-a456-426614174000"
INSTALLED_SHA256 = "63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14"
CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init"
)


def wrapped(name: str, body: str) -> str:
    return f"__AG_{name}_BEGIN__\n{body.rstrip()}\n__AG_{name}_END__\n"


def state(uptime: int) -> str:
    entries = [
        ("chosen_framebuffer_child_count", "1"),
        ("chosen_simplefb_compatible_count", "1"),
        ("simplefb_node_present", "1"),
        ("chosen_address_cells_hex", "00000002"),
        ("chosen_size_cells_hex", "00000002"),
        ("chosen_ranges_hex", ""),
        ("simplefb_compatible_hex", "73696d706c652d6672616d6562756666657200"),
        ("simplefb_reg_hex", "000000007dfb00000000000001f90000"),
        ("simplefb_width_hex", "00000438"),
        ("simplefb_height_hex", "00000870"),
        ("simplefb_stride_hex", "00001100"),
        ("simplefb_format_hex", "613872386738623800"),
        ("simplefb_clocks_hex", "000000030000002d0000000600000006"),
        ("simplefb_name_hex", "6672616d6562756666657200"),
        ("simplefb_memory_region_present", "0"),
        ("simplefb_child_count", "0"),
        ("simplefb_unexpected_entry_count", "0"),
        ("runtime_framebuffer_reservation_count", "1"),
        ("runtime_framebuffer_reservation_present", "1"),
        ("runtime_framebuffer_compatible_hex", "6d6564696174656b2c6672616d6562756666657200"),
        ("runtime_framebuffer_reg_hex", "000000007dfb00000000000001f90000"),
        (
            "runtime_framebuffer_name_hex",
            "6d626c6f636b2d332d6672616d6562756666657200",
        ),
        ("runtime_framebuffer_no_map_present", "1"),
        ("runtime_framebuffer_no_map_hex", ""),
        ("runtime_framebuffer_child_count", "0"),
        ("runtime_framebuffer_unexpected_entry_count", "0"),
        ("simplefb_platform_count", "1"),
        ("simplefb_platform_present", "1"),
        ("simplefb_platform_driver", "simple-framebuffer"),
        (
            "simplefb_platform_of_node",
            "/sys/firmware/devicetree/base/chosen/framebuffer@7dfb0000",
        ),
        ("fb_count", "1"),
        ("fb0_present", "1"),
        ("fb0_name", "simple"),
        ("fb0_virtual_size", "1080,2160"),
        ("fb0_bits_per_pixel", "32"),
        ("fb0_stride", "4352"),
        ("fb0_platform_device", "7dfb0000.framebuffer"),
        ("observer_device_present", "1"),
        ("observer_device_driver", "unbound"),
        ("observer_driver_present", "0"),
        ("observer_attr_count", "0"),
        ("i2c6_count", "1"),
        ("i2c6_device", "1100e000.i2c"),
        ("i2c6_driver", "mtk-i2c"),
        ("da9214_count", "1"),
        ("da9214_device", "6-0068"),
        ("da9214_compatible", "dlg,da9214"),
        ("da9214_parent", "i2c@1100e000"),
        ("da9214_driver", "da9211"),
        ("da9214_bucka_total", "1"),
        ("da9214_bucka_count", "1"),
        ("da9214_bucka_parent", "6-0068"),
        ("vproc_big_total", "1"),
        ("vproc_big_count", "1"),
        ("vproc_big_parent", "6-0068"),
        ("watchdog_fd_count", "0"),
        ("boot_id", BOOT_ID),
        ("uptime_seconds", str(uptime)),
        ("online", "0-7"),
        ("offline", "8-9"),
    ]
    return "\n".join(f"{key}={value}" for key, value in entries)


def stat_sample(increment: int) -> str:
    return "\n".join(
        f"cpu{cpu} {100 + cpu + increment} 2 3 4 5 6 7 8 9 10"
        for cpu in range(8)
    )


def exact_capture() -> str:
    host = "\n".join(
        (
            f"installed_full_sha256_input={INSTALLED_SHA256}",
            "attestation_basis=caller-supplied-prior-full-partition-readback",
            "device_partition_read_during_collection=no",
        )
    )
    identity = "\n".join(
        (
            f"boot_id={BOOT_ID}",
            "uptime_seconds=45",
            f"cmdline={CMDLINE}",
            "possible=0-9",
            "present=0-9",
            "online=0-7",
            "offline=8-9",
            "nproc=8",
            "kernel=7.1.3-gemini-observability-L",
            f'config_cmdline=CONFIG_CMDLINE="{CMDLINE}"',
            "config_force=CONFIG_CMDLINE_FORCE=y",
            "config_kallsyms=CONFIG_KALLSYMS=y",
            "config_da9211=CONFIG_REGULATOR_DA9211=y",
            "config_a72_observer=CONFIG_MTK_MT6797_A72_POWER=y",
            "config_simplefb=CONFIG_FB_SIMPLE=y",
            "cpu8_enable_method=mediatek,mt6797-psci",
            "cpu9_enable_method=mediatek,mt6797-psci",
        )
    )
    dmesg = "\n".join(
        (
            "[    0.000000] smp: Brought up 1 node, 8 CPUs",
            "[    0.000000] OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff (32320 KiB) nomap non-reusable mblock-3-framebuffer",
            "[    1.000000] calling simplefb_driver_init+0x0/0x18 @ 1",
            "[    1.010000] simple-framebuffer 7dfb0000.framebuffer: framebuffer at 0x7dfb0000, 0x1f90000 bytes",
            "[    1.020000] simple-framebuffer 7dfb0000.framebuffer: format=a8r8g8b8, mode=1080x2160x32, linelength=4352",
            "[    1.030000] simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
            "[    1.040000] initcall simplefb_driver_init+0x0/0x18 returned 0 after 40 usecs",
            "[    1.050000] calling da9211_regulator_driver_init+0x0/0x18 @ 1",
            "[    1.060000] initcall da9211_regulator_driver_init+0x0/0x18 returned 0 after 10 usecs",
            "[    1.070000] initcall mt6797_a72_power_driver_init blacklisted",
        )
    )
    return "".join(
        (
            wrapped("HOST", host),
            "GEMINI_USB_GADGET_ETHERNET_20260721_AC\n",
            wrapped("IDENTITY", identity),
            wrapped("STATE1", state(45)),
            wrapped("STAT1", stat_sample(0)),
            wrapped("STATE2", state(50)),
            wrapped("STAT2", stat_sample(20)),
            wrapped("DMESG", dmesg),
        )
    )


def replace_once(text: str, before: str, after: str) -> str:
    if before not in text:
        raise AssertionError(f"fixture replacement target is absent: {before}")
    return text.replace(before, after, 1)


def swap_adjacent_sections(text: str, first: str, second: str) -> str:
    first_begin = f"__AG_{first}_BEGIN__"
    first_end = f"__AG_{first}_END__\n"
    second_begin = f"__AG_{second}_BEGIN__"
    second_end = f"__AG_{second}_END__\n"
    start = text.index(first_begin)
    middle = text.index(second_begin, start)
    end = text.index(second_end, middle) + len(second_end)
    first_block = text[start:middle]
    second_block = text[middle:end]
    return text[:start] + second_block + first_block + text[end:]


def run_validator(validator: pathlib.Path, capture: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(validator), "--capture", str(capture)],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    validator = script_dir / "validate-runtime.py"
    base = exact_capture()
    mutations = {
        "wrong-installed-full-hash": lambda text: replace_once(
            text, INSTALLED_SHA256, "0" * 64
        ),
        "missing-chosen-width": lambda text: replace_once(
            text, "simplefb_width_hex=00000438", "simplefb_width_hex=missing"
        ),
        "nonempty-chosen-ranges": lambda text: replace_once(
            text, "chosen_ranges_hex=\n", "chosen_ranges_hex=00\n"
        ),
        "wrong-simplefb-clocks": lambda text: replace_once(
            text,
            "simplefb_clocks_hex=000000030000002d0000000600000006",
            "simplefb_clocks_hex=000000030000002d0000000600000007",
        ),
        "missing-runtime-no-map": lambda text: replace_once(
            text,
            "runtime_framebuffer_no_map_present=1",
            "runtime_framebuffer_no_map_present=0",
        ),
        "simplefb-child-node": lambda text: replace_once(
            text, "simplefb_child_count=0", "simplefb_child_count=1"
        ),
        "simplefb-extra-property": lambda text: replace_once(
            text,
            "simplefb_unexpected_entry_count=0",
            "simplefb_unexpected_entry_count=1",
        ),
        "reservation-extra-property": lambda text: replace_once(
            text,
            "runtime_framebuffer_unexpected_entry_count=0",
            "runtime_framebuffer_unexpected_entry_count=1",
        ),
        "unbound-simplefb": lambda text: replace_once(
            text,
            "simplefb_platform_driver=simple-framebuffer",
            "simplefb_platform_driver=unbound",
        ),
        "wrong-fb0-stride": lambda text: replace_once(
            text, "fb0_stride=4352", "fb0_stride=4320"
        ),
        "simplefb-clock-error": lambda text: replace_once(
            text,
            "[    1.040000] initcall simplefb_driver_init",
            "[    1.035000] simple-framebuffer 7dfb0000.framebuffer: failed to enable clock: -22\n"
            "[    1.040000] initcall simplefb_driver_init",
        ),
        "stalled-cpu3": lambda text: replace_once(
            text, "cpu3 123 2 3 4 5 6 7 8 9 10", "cpu3 103 2 3 4 5 6 7 8 9 10"
        ),
        "raw-framebuffer-beacon": lambda text: replace_once(
            text,
            "__AG_DMESG_END__",
            "GEMINI_AG_RAW_FRAMEBUFFER_BEACON\n__AG_DMESG_END__",
        ),
        "duplicate-host-marker": lambda text: text + "__AG_HOST_BEGIN__\n",
        "out-of-order-state-stat": lambda text: swap_adjacent_sections(
            text, "STATE1", "STAT1"
        ),
    }

    with tempfile.TemporaryDirectory(prefix="candidate-ag-runtime-test.") as temporary:
        root = pathlib.Path(temporary)
        exact_path = root / "exact.txt"
        exact_path.write_text(base, encoding="utf-8")
        passed = run_validator(validator, exact_path)
        if passed.returncode != 0 or "validation=candidate-ag-" not in passed.stdout:
            print("error: exact synthetic AG capture did not pass", file=sys.stderr)
            print(passed.stdout, file=sys.stderr)
            print(passed.stderr, file=sys.stderr)
            return 2

        rejected: list[str] = []
        for name, mutate in mutations.items():
            path = root / f"{name}.txt"
            path.write_text(mutate(base), encoding="utf-8")
            result = run_validator(validator, path)
            if result.returncode == 0 or not result.stderr.startswith("error: "):
                print(f"error: mutation unexpectedly passed: {name}", file=sys.stderr)
                return 2
            rejected.append(name)

    print("validation=candidate-ag-runtime-validator-fixtures")
    print("exact_fixture=passed")
    print(f"mutations_rejected={len(rejected)}")
    print("rejected=" + ",".join(rejected))
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
