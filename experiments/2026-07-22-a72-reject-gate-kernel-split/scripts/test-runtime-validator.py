#!/usr/bin/env python3
"""Exercise Candidate AI's live USB attribution mutation boundaries."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

sys.dont_write_bytecode = True


TEST_INSTALLED_SHA256 = (
    "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
)


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(validator: object) -> str:
    host = {
        "installed_full_sha256_input": TEST_INSTALLED_SHA256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "installed_full_hash_reverified_during_collection": "no",
        "device_partition_read_during_collection": "no",
        "interface": "en7",
        "mac": validator.EXPECTED_HOST_MAC,
        "host_address": validator.EXPECTED_HOST_ADDRESS,
        "route_interface": "en7",
        "device_endpoint": validator.EXPECTED_DEVICE_ENDPOINT,
    }
    identity = {
        "cmdline": validator.EXPECTED_CMDLINE,
        "possible": "0-9",
        "present": "0-9",
        "online": "0-7",
        "offline": "8-9",
        "nproc": "8",
        "kernel": "7.1.3-gemini-observability-L",
        "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
        "uptime_before": "45.50",
        "config_sha256": validator.EXPECTED_CONFIG_SHA256,
        "cpu8_enable_method": "mediatek,mt6797-psci",
        "cpu9_enable_method": "mediatek,mt6797-psci",
        "boot_gate_symbol_count": "1",
        "disable_gate_symbol_count": "1",
        "ops_symbol_count": "1",
        "cpu8_online_control": "absent",
        "cpu9_online_control": "absent",
    }
    stability = {
        "boot_id_after": identity["boot_id"],
        "uptime_after": "50.60",
        "online_after": "0-7",
        "offline_after": "8-9",
        "cpu8_online_control_after": "absent",
        "cpu9_online_control_after": "absent",
    }
    host_text = "".join(f"{key}={value}\n" for key, value in host.items())
    identity_text = "".join(
        f"{validator.EXPECTED_USB_PROMPT}{key}={value}\n"
        for key, value in identity.items()
    )
    stability_text = "".join(
        f"{validator.EXPECTED_USB_PROMPT}{key}={value}\n"
        for key, value in stability.items()
    )
    first = "".join(
        f"cpu{cpu} {100 + cpu} 2 3 4 5 6 7 8 9 10\n" for cpu in range(8)
    )
    second = "".join(
        f"cpu{cpu} {101 + cpu} 2 3 4 5 6 7 8 9 10\n" for cpu in range(8)
    )
    dmesg = ["smp: Brought up 1 node, 8 CPUs\n"]
    for cpu, mpidr in validator.EXPECTED_BOOT_NODES.items():
        dmesg.append(
            f"CPU{cpu}: Booted secondary processor 0x{mpidr} [0x410fd034]\n"
        )
        dmesg.append(f"GICv3: CPU{cpu}: found redistributor\n")
    # The inherited service records its marker in status and dmesg. Together
    # with its one standalone banner this fixture has 15 marker occurrences,
    # matching the cardinality observed in the preserved Candidate AD capture.
    status_lines = "".join(
        f"{validator.EXPECTED_USB_MARKER} status-line-{index}\n"
        for index in range(1, 5)
    )
    dmesg.extend(
        f"{validator.EXPECTED_USB_MARKER} dmesg-line-{index}\n"
        for index in range(1, 11)
    )
    text = (
        f"__AI_HOST_BEGIN__\n{host_text}__AI_HOST_END__\n"
        f"{validator.EXPECTED_USB_MARKER}\n"
        f"{status_lines}"
        f"{validator.EXPECTED_USB_PROMPT}__AI_IDENTITY_BEGIN__\n"
        f"{identity_text}{validator.EXPECTED_USB_PROMPT}__AI_IDENTITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AI_STAT1_BEGIN__\n{first}__AI_STAT1_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AI_STAT2_BEGIN__\n{second}__AI_STAT2_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AI_STABILITY_BEGIN__\n"
        f"{stability_text}{validator.EXPECTED_USB_PROMPT}__AI_STABILITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AI_DMESG_BEGIN__\n"
        f"{''.join(dmesg)}__AI_DMESG_END__\n"
    )
    return text.replace("\n", "\r\n")


def expect_rejected(validator: object, text: str, expected_hash: str = TEST_INSTALLED_SHA256) -> None:
    try:
        validator.validate(text, expected_hash)
    except (ValueError, KeyError, OverflowError):
        return
    raise ValueError("runtime mutation unexpectedly passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    validator = load_module(
        pathlib.Path(__file__).resolve().parent / "validate-runtime.py",
        "gemini_ai_runtime_tests",
    )
    baseline = fixture(validator)
    if baseline.count(validator.EXPECTED_USB_MARKER) != 15:
        raise ValueError("realistic inherited USB marker fixture cardinality changed")
    validator.validate(baseline, TEST_INSTALLED_SHA256)

    mutations = [
        (baseline, "b" * 64),
        (baseline, "A" * 64),
        (
            baseline.replace(TEST_INSTALLED_SHA256, "b" * 64, 1),
            "b" * 64,
        ),
        (baseline.replace(TEST_INSTALLED_SHA256, "b" * 64, 1), TEST_INSTALLED_SHA256),
        (baseline.replace("route_interface=en7", "route_interface=en8", 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace(
                "device_partition_read_during_collection=no",
                "device_partition_read_during_collection=yes",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER} not-a-banner\r\n",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER}\r\n{validator.EXPECTED_USB_MARKER}\r\n",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (baseline.replace(validator.EXPECTED_CONFIG_SHA256, "0" * 64, 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace(
                "cpu8_enable_method=mediatek,mt6797-psci",
                "cpu8_enable_method=psci",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (baseline.replace("boot_gate_symbol_count=1", "boot_gate_symbol_count=0", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("disable_gate_symbol_count=1", "disable_gate_symbol_count=0", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("online=0-7", "online=0-8", 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace("cpu8_online_control=absent", "cpu8_online_control=present", 1),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                "cpu8_online_control_after=absent",
                "cpu8_online_control_after=present",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (baseline.replace("online_after=0-7", "online_after=0-8", 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace(
                "cpu3 104 2 3 4 5 6 7 8 9 10",
                "cpu3 103 2 3 4 5 6 7 8 9 10",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                "__AI_DMESG_END__",
                "CPU8: Booted secondary processor 0x200 [0x410fd080]\r\n__AI_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                "__AI_DMESG_END__",
                "mt6797-psci: CPU8 boot rejected: A72 power sequence inactive\r\n__AI_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline.replace(
                "__AI_DMESG_END__", "Kernel panic - synthetic\r\n__AI_DMESG_END__", 1
            ),
            TEST_INSTALLED_SHA256,
        ),
        (baseline.replace("uptime_before=45.50", "uptime_before=44.99", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("uptime_after=50.60", "uptime_after=49.00", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("uptime_before=45.50", "uptime_before=nan", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("uptime_before=45.50", "uptime_before=inf", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("uptime_before=45.50", "uptime_before=4.55e1", 1), TEST_INSTALLED_SHA256),
        (baseline.replace("uptime_after=50.60", "uptime_after=40.00", 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace(
                "boot_id_after=01234567-89ab-cdef-0123-456789abcdef",
                "boot_id_after=11234567-89ab-cdef-0123-456789abcdef",
                1,
            ),
            TEST_INSTALLED_SHA256,
        ),
        (baseline.replace("maxcpus=8", "maxcpus=1", 1), TEST_INSTALLED_SHA256),
        (
            baseline.replace("__AI_IDENTITY_END__", "unexpected=value\r\n__AI_IDENTITY_END__", 1),
            TEST_INSTALLED_SHA256,
        ),
        (
            baseline + "__AI_STABILITY_BEGIN__\r\nuptime_after=51.0\r\n__AI_STABILITY_END__\r\n",
            TEST_INSTALLED_SHA256,
        ),
    ]
    for mutation, expected_hash in mutations:
        expect_rejected(validator, mutation, expected_hash)

    print("validation=candidate-ai-runtime-attribution-mutations")
    print("positive_fixture=passed")
    print("transport=crlf-with-15-inherited-marker-occurrences")
    print(f"mutations_rejected={len(mutations)}")
    print("nan_inf_exponent_uptime=rejected")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
