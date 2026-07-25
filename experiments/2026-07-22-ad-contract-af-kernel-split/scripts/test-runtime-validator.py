#!/usr/bin/env python3
"""Exercise Candidate AH's runtime validator with exact and mutated fixtures."""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Callable


BOOT_ID = "12345678-1234-4abc-8def-123456789abc"
INSTALLED_SHA256 = (
    "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"
)


def load_validator(path: pathlib.Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("candidate_ah_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AH runtime validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def key_value_block(values: dict[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in values.items())


def exact_capture(runtime) -> str:
    # Anchor the externally meaningful identities independently of the fixture
    # construction below so changing a validator constant cannot silently
    # redefine the synthetic candidate.
    assert runtime.EXPECTED_CONFIG_SHA256 == (
        "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
    )
    assert runtime.REJECTING_METHOD == "mediatek,mt6797-psci"
    assert runtime.EXPECTED_STATE["i2c6_status_hex"] == "64697361626c656400"
    assert runtime.EXPECTED_STATE["observer_device_present"] == "0"
    assert runtime.EXPECTED_STATE["aw9523_driver"] == "aw9523-pinctrl"
    assert runtime.EXPECTED_STATE["matrix_event_node"] == "/dev/input/event0"

    host = {
        "installed_full_sha256_input": INSTALLED_SHA256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "interface": "en99",
        "mac": "42:00:15:19:82:00",
        "host_address": "10.15.19.1",
        "route_interface": "en99",
    }
    identity = dict(runtime.EXPECTED_IDENTITY)
    identity["boot_id"] = BOOT_ID
    identity["uptime_seconds"] = "50"
    state1 = dict(runtime.EXPECTED_STATE)
    state1["boot_id"] = BOOT_ID
    state1["uptime_seconds"] = "50"
    state2 = dict(runtime.EXPECTED_STATE)
    state2["boot_id"] = BOOT_ID
    state2["uptime_seconds"] = "55"
    stat1 = "\n".join(
        f"cpu{cpu} 100 2 3 4 5 6 7 8 9 10" for cpu in range(8)
    )
    stat2 = "\n".join(
        f"cpu{cpu} 110 2 3 4 5 6 7 8 9 10" for cpu in range(8)
    )
    dmesg_lines = [
        "[    0.100000] initcall mt6797_a72_power_driver_init blacklisted",
        "[    0.200000] smp: Brought up 1 node, 8 CPUs",
    ]
    for cpu, mpidr in runtime.EXPECTED_BOOT_NODES.items():
        dmesg_lines.extend(
            [
                f"[    0.3{cpu}0000] GICv3: CPU{cpu}: found redistributor 1 region 0:0x000000000c0{cpu}0000",
                f"[    0.4{cpu}0000] CPU{cpu}: Booted secondary processor 0x{mpidr} [0x410fd034]",
            ]
        )
    dmesg_lines.extend(
        [
            "[    0.900000] OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff (32320 KiB) nomap non-reusable mblock-3-framebuffer",
            "[    1.000000] calling  simplefb_driver_init+0x0/0x28 @ 1",
            "[    1.010000] simple-framebuffer 7dfb0000.framebuffer: framebuffer at 0x7dfb0000, 0x1f90000 bytes",
            "[    1.020000] simple-framebuffer 7dfb0000.framebuffer: format=a8r8g8b8, mode=1080x2160x32, linelength=4352",
            "[    1.030000] simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
            "[    1.040000] initcall simplefb_driver_init+0x0/0x28 returned 0 after 40 usecs",
            "[    1.100000] calling  da9211_regulator_driver_init+0x0/0x28 @ 1",
            "[    1.110000] initcall da9211_regulator_driver_init+0x0/0x28 returned 0 after 10 usecs",
            "[    2.000000] input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
            "[    2.010000] matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
            "[    2.020000] GEMINI_MT6797_KERNEL_RESTART_20260720_AB aw9523_client=0-005b driver=aw9523-pinctrl",
            "[    2.030000] GEMINI_MT6797_KERNEL_RESTART_20260720_AB keyboard_map=loaded origin=loaded-now format=busybox-bkeymap sha256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c unicode_mode=verified tty1_shell=ready foreground_vt=selected prompt=GEMINI-AB# reboot_dispatch=validated",
            "[    2.040000] GEMINI_MT6797_KERNEL_RESTART_20260720_AB matrix_platform_device=keyboard-matrix driver=matrix-keypad",
            "[    2.050000] GEMINI_MT6797_KERNEL_RESTART_20260720_AB matrix_input_name=keyboard-matrix event_node=/dev/input/event0 identity_anchor=keyboard-matrix discovery_wait=0s",
            "[    2.100000] GEMINI_USB_GADGET_ETHERNET_20260721_AC services=launched usb_network=background worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 local_console=unchanged watchdog_userspace=none",
            "[    2.110000] GEMINI_USB_GADGET_ETHERNET_20260721_AC usb0=configured address=10.15.19.82/24 operstate=down carrier=1 udc=11271000.usb udc_state=configured",
            "[    2.120000] GEMINI_USB_GADGET_ETHERNET_20260721_AC service=nc status=listening address=10.15.19.82 port=2323 shell=/bin/usb-shell authentication=none encryption=none direct_link_only=yes",
            "[   45.000000] GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes",
        ]
    )
    sections = [
        "__AH_HOST_BEGIN__\n" + key_value_block(host) + "\n__AH_HOST_END__",
        runtime.USB_MARKER,
        "Direct USB link only: device 10.15.19.82/24, TCP port 2323.",
        "__AH_IDENTITY_BEGIN__\n"
        + key_value_block(identity)
        + "\n__AH_IDENTITY_END__",
        "__AH_STATE1_BEGIN__\n" + key_value_block(state1) + "\n__AH_STATE1_END__",
        "__AH_STAT1_BEGIN__\n" + stat1 + "\n__AH_STAT1_END__",
        "__AH_STATE2_BEGIN__\n" + key_value_block(state2) + "\n__AH_STATE2_END__",
        "__AH_STAT2_BEGIN__\n" + stat2 + "\n__AH_STAT2_END__",
        "__AH_DMESG_BEGIN__\n"
        + "\n".join(dmesg_lines)
        + "\n__AH_DMESG_END__",
    ]
    return "\n".join(sections) + "\n"


def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"fixture token is absent: {old}")
    return text.replace(old, new, 1)


def remove_standalone_banner(text: str) -> str:
    return replace_first(text, "\nGEMINI_USB_GADGET_ETHERNET_20260721_AC\n", "\n")


def swap_state_and_stat(text: str) -> str:
    first_begin = "__AH_STATE1_BEGIN__"
    first_end = "__AH_STATE1_END__"
    second_begin = "__AH_STAT1_BEGIN__"
    second_end = "__AH_STAT1_END__"
    start = text.index(first_begin)
    middle = text.index(second_begin, start)
    end = text.index(second_end, middle) + len(second_end)
    return text[:start] + text[middle:end] + "\n" + text[start:middle].rstrip() + text[end:]


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
    runtime = load_validator(validator)
    base = exact_capture(runtime)
    mutations: dict[str, Callable[[str], str]] = {
        "malformed-installed-hash": lambda text: replace_first(text, INSTALLED_SHA256, "A" * 64),
        "wrong-well-formed-installed-hash": lambda text: replace_first(
            text, INSTALLED_SHA256, "0" * 64
        ),
        "wrong-route-interface": lambda text: replace_first(text, "route_interface=en99", "route_interface=en98"),
        "missing-usb-banner": remove_standalone_banner,
        "wrong-config-hash": lambda text: replace_first(text, runtime.EXPECTED_CONFIG_SHA256, "0" * 64),
        "wrong-ad-init-hash": lambda text: replace_first(
            text,
            "c938a65e963dae815c5fa9e51442026b8464d470a10bb9615d8de73599295222",
            "1" * 64,
        ),
        "wrong-cmdline": lambda text: replace_first(text, "maxcpus=8", "maxcpus=9"),
        "generic-cpu8-method": lambda text: replace_first(text, "cpu8_enable_method=mediatek,mt6797-psci", "cpu8_enable_method=psci"),
        "observer-device-present": lambda text: replace_first(text, "observer_device_present=0", "observer_device_present=1"),
        "i2c6-enabled": lambda text: replace_first(text, "i2c6_status_hex=64697361626c656400", "i2c6_status_hex=6f6b617900"),
        "da9214-client-present": lambda text: replace_first(text, "da9214_client_count=0", "da9214_client_count=1"),
        "wrong-simplefb-clocks": lambda text: replace_first(text, "simplefb_clocks_hex=000000030000002d0000000600000006", "simplefb_clocks_hex=000000030000002d0000000600000007"),
        "unbound-aw9523": lambda text: replace_first(text, "aw9523_driver=aw9523-pinctrl", "aw9523_driver=unbound"),
        "missing-matrix-event": lambda text: replace_first(text, "matrix_event_count=1", "matrix_event_count=0"),
        "keymap-readback-failed": lambda text: replace_first(text, "keymap_verify_rc=0", "keymap_verify_rc=1"),
        "usb-carrier-down": lambda text: replace_first(text, "usb0_carrier=1", "usb0_carrier=0"),
        "wrong-udc-state": lambda text: replace_first(text, "udc_state=configured", "udc_state=not-attached"),
        "watchdog-owner": lambda text: replace_first(text, "watchdog_fd_count=0", "watchdog_fd_count=1"),
        "cpu8-online": lambda text: replace_first(text, "offline=8-9", "offline=9"),
        "stalled-cpu3": lambda text: replace_first(text, "cpu3 110 2 3 4 5 6 7 8 9 10", "cpu3 100 2 3 4 5 6 7 8 9 10"),
        "early-capture": lambda text: replace_first(text, "uptime_seconds=50", "uptime_seconds=44"),
        "changed-state-boot-id": lambda text: replace_first(text, f"boot_id={BOOT_ID}\nuptime_seconds=55", "boot_id=22345678-1234-4abc-8def-123456789abc\nuptime_seconds=55"),
        "missing-blacklist-log": lambda text: replace_first(text, runtime.BLACKLIST_DMESG, "observer initcall status unavailable"),
        "observer-probed": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] mt6797-a72-power probe resources ready\n__AH_DMESG_END__"),
        "da9214-client-activity": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] da9211 6-0068: regulator client ready\n__AH_DMESG_END__"),
        "missing-usb-listener": lambda text: replace_first(text, "service=nc status=listening address=10.15.19.82 port=2323", "service=nc status=not-listening address=10.15.19.82 port=2323"),
        "a72-rejection": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] mt6797-psci: CPU8 boot rejected\n__AH_DMESG_END__"),
        "a72-cpu-on": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] CPU_ON requested for CPU8\n__AH_DMESG_END__"),
        "kernel-fault": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] Kernel panic - not syncing\n__AH_DMESG_END__"),
        "simplefb-clock-error": lambda text: replace_first(text, "__AH_DMESG_END__", "[   50.0] simple-framebuffer failed to enable clock\n__AH_DMESG_END__"),
        "duplicate-host-marker": lambda text: text + "__AH_HOST_BEGIN__\n",
        "out-of-order-sections": swap_state_and_stat,
    }

    with tempfile.TemporaryDirectory(prefix="candidate-ah-runtime-test.") as temporary:
        root = pathlib.Path(temporary)
        exact_path = root / "exact.txt"
        exact_path.write_text(base, encoding="utf-8")
        passed = run_validator(validator, exact_path)
        if passed.returncode != 0 or "validation=candidate-ah-" not in passed.stdout:
            print("error: exact synthetic Candidate AH capture did not pass", file=sys.stderr)
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
                print(result.stdout, file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                return 2
            rejected.append(name)

    print("validation=candidate-ah-runtime-validator-fixtures")
    print("exact_fixture=passed")
    print(f"mutations_rejected={len(rejected)}")
    print("rejected=" + ",".join(rejected))
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
