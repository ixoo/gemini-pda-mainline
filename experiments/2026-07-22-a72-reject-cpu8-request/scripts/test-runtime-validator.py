#!/usr/bin/env python3
"""Exercise Candidate AJ's live USB attribution mutation boundaries."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True


TEST_INSTALLED_SHA256 = (
    "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
)


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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
    dmesg: list[str] = []
    for cpu, mpidr in validator.EXPECTED_BOOT_NODES.items():
        dmesg.append(
            f"CPU{cpu}: Booted secondary processor 0x{mpidr} [0x410fd034]\n"
        )
        dmesg.append(f"GICv3: CPU{cpu}: found redistributor\n")
    dmesg.extend(
        [
            f"[    2.000000] {validator.EXPECTED_CPU8_GATE}\n",
            f"<4>[    2.010000] {validator.EXPECTED_CPU8_FAILURE}\n",
            "smp: Brought up 1 node, 8 CPUs\n",
        ]
    )
    # The inherited service records its marker in status and dmesg. Together
    # with its one standalone banner this fixture has the preserved 15-marker
    # Candidate AD/AI transport cardinality.
    status_lines = "".join(
        f"{validator.EXPECTED_USB_MARKER} status-line-{index}\n"
        for index in range(1, 5)
    )
    dmesg.extend(
        f"{validator.EXPECTED_USB_MARKER} dmesg-line-{index}\n"
        for index in range(1, 11)
    )
    text = (
        f"__AJ_HOST_BEGIN__\n{host_text}__AJ_HOST_END__\n"
        f"{validator.EXPECTED_USB_MARKER}\n"
        f"{status_lines}"
        f"{validator.EXPECTED_USB_PROMPT}__AJ_IDENTITY_BEGIN__\n"
        f"{identity_text}{validator.EXPECTED_USB_PROMPT}__AJ_IDENTITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AJ_STAT1_BEGIN__\n{first}__AJ_STAT1_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AJ_STAT2_BEGIN__\n{second}__AJ_STAT2_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AJ_STABILITY_BEGIN__\n"
        f"{stability_text}{validator.EXPECTED_USB_PROMPT}__AJ_STABILITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AJ_DMESG_BEGIN__\n"
        f"{''.join(dmesg)}__AJ_DMESG_END__\n"
    )
    return text.replace("\n", "\r\n")


def expect_rejected(
    validator: object,
    text: str,
    expected_hash: str = TEST_INSTALLED_SHA256,
    synthetic_override: str | None = TEST_INSTALLED_SHA256,
) -> None:
    try:
        validator.validate(
            text,
            expected_hash,
            synthetic_installed_full_sha256_override=synthetic_override,
        )
    except (ValueError, KeyError, OverflowError):
        return
    raise ValueError("runtime mutation unexpectedly passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    validator = load_module(
        pathlib.Path(__file__).resolve().parent / "validate-runtime.py",
        "gemini_aj_runtime_tests",
    )
    with tempfile.TemporaryDirectory(prefix="candidate-aj-runtime-source-pin-") as raw:
        temporary = pathlib.Path(raw)
        validator_source = pathlib.Path(validator.__file__).read_bytes()
        candidate_source = (pathlib.Path(validator.__file__).parent / "candidate_aj.py").read_bytes()
        (temporary / "validate-runtime.py").write_bytes(validator_source)
        (temporary / "candidate_aj.py").write_bytes(candidate_source + b"\n")
        try:
            load_module(temporary / "validate-runtime.py", "gemini_aj_runtime_bad_source")
        except ValueError as exc:
            if "identity module source changed" not in str(exc):
                raise
        else:
            raise ValueError("mutated Candidate AJ identity module was accepted")
    if validator.VALIDATION_LABEL != "candidate-aj-usb-cpu-runtime-subgate":
        raise ValueError("runtime subgate label changed")
    if validator.SEPARATE_OVERALL_GATES != (
        "visible-console",
        "native-reboot-cycle",
        "recovery-attribution",
        "post-cycle-boot2-integrity",
    ):
        raise ValueError("independent overall evidence gates changed")
    if validator.AJ.PADDED_SHA256 != TEST_INSTALLED_SHA256:
        raise ValueError("production padded Candidate AJ identity changed")
    validator.AJ.require_artifact_pins()
    baseline = fixture(validator)
    if baseline.count(validator.EXPECTED_USB_MARKER) != 15:
        raise ValueError("realistic inherited USB marker fixture cardinality changed")
    validator.validate(
        baseline,
        TEST_INSTALLED_SHA256,
        synthetic_installed_full_sha256_override=TEST_INSTALLED_SHA256,
    )
    # The production path has no synthetic override and accepts only the exact
    # reproduced full-partition identity selected in candidate_aj.py.
    validator.validate(baseline, TEST_INSTALLED_SHA256)

    gate = validator.EXPECTED_CPU8_GATE
    failure = validator.EXPECTED_CPU8_FAILURE
    reversed_rejections = baseline.replace(gate, "__GATE_PLACEHOLDER__", 1)
    reversed_rejections = reversed_rejections.replace(
        failure, gate, 1
    ).replace("__GATE_PLACEHOLDER__", failure, 1)

    mutations = [
        ("wrong-production-caller-hash", baseline, "b" * 64, None),
        ("malformed-production-caller-hash", baseline, "A" * 64, None),
        (
            "host-hash-not-accepted",
            baseline.replace(TEST_INSTALLED_SHA256, "b" * 64, 1),
            "b" * 64,
            TEST_INSTALLED_SHA256,
        ),
        ("malformed-synthetic-override", baseline, TEST_INSTALLED_SHA256, "B" * 64),
        (
            "route-interface",
            baseline.replace("route_interface=en7", "route_interface=en8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "partition-read",
            baseline.replace(
                "device_partition_read_during_collection=no",
                "device_partition_read_during_collection=yes",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-banner",
            baseline.replace(
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER} not-a-banner\r\n",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-banner",
            baseline.replace(
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER}\r\n"
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "config",
            baseline.replace(validator.EXPECTED_CONFIG_SHA256, "0" * 64, 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "maxcpus-eight",
            baseline.replace("maxcpus=9", "maxcpus=8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "possible-mask",
            baseline.replace("possible=0-9", "possible=0-8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "present-mask",
            baseline.replace("present=0-9", "present=0-8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "online-mask",
            baseline.replace("online=0-7", "online=0-8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "offline-mask",
            baseline.replace("offline=8-9", "offline=9", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "nproc",
            baseline.replace("nproc=8", "nproc=9", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "enable-method",
            baseline.replace(
                "cpu8_enable_method=mediatek,mt6797-psci",
                "cpu8_enable_method=psci",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "gate-symbol",
            baseline.replace("boot_gate_symbol_count=1", "boot_gate_symbol_count=0", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-online-control",
            baseline.replace("cpu8_online_control=absent", "cpu8_online_control=present", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "stability-mask",
            baseline.replace("online_after=0-7", "online_after=0-8", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "stalled-accounting",
            baseline.replace(
                "cpu3 104 2 3 4 5 6 7 8 9 10",
                "cpu3 103 2 3 4 5 6 7 8 9 10",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu8-gate",
            baseline.replace(gate, "", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-cpu8-gate",
            baseline.replace(
                "__AJ_DMESG_END__", f"{gate}\r\n__AJ_DMESG_END__", 1
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu8-gate",
            baseline.replace(
                gate,
                "mt6797-psci: CPU8 boot rejected: synthetic wrong reason",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu8-failure",
            baseline.replace(failure, "", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-cpu8-failure",
            baseline.replace(
                "__AJ_DMESG_END__", f"{failure}\r\n__AJ_DMESG_END__", 1
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu8-errno",
            baseline.replace(failure, "CPU8: failed to boot: -5", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "rejection-order",
            reversed_rejections,
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-attempt",
            baseline.replace(
                "__AJ_DMESG_END__",
                "mt6797-psci: CPU9 boot rejected: A72 power sequence inactive\r\n"
                "__AJ_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-failure",
            baseline.replace(
                "__AJ_DMESG_END__",
                "CPU9: failed to boot: -11\r\n__AJ_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-a72-boot",
            baseline.replace(
                "__AJ_DMESG_END__",
                "CPU8: Booted secondary processor 0x200 [0x410fd080]\r\n"
                "__AJ_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-a72-boot",
            baseline.replace(
                "__AJ_DMESG_END__",
                "CPU9: Booted secondary processor 0x201 [0x410fd080]\r\n"
                "__AJ_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "panic",
            baseline.replace(
                "__AJ_DMESG_END__", "Kernel panic - synthetic\r\n__AJ_DMESG_END__", 1
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-a53-boot",
            baseline.replace(
                "CPU4: Booted secondary processor 0x0000000100 [0x410fd034]\r\n",
                "",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "early-uptime",
            baseline.replace("uptime_before=45.50", "uptime_before=44.99", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "short-window",
            baseline.replace("uptime_after=50.60", "uptime_after=49.99", 1),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "changed-boot-id",
            baseline.replace(
                "boot_id_after=01234567-89ab-cdef-0123-456789abcdef",
                "boot_id_after=11234567-89ab-cdef-0123-456789abcdef",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "identity-inventory",
            baseline.replace(
                "__AJ_IDENTITY_END__", "unexpected=value\r\n__AJ_IDENTITY_END__", 1
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicated-section",
            baseline
            + "__AJ_STABILITY_BEGIN__\r\nuptime_after=51.0\r\n"
            "__AJ_STABILITY_END__\r\n",
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-smp-line",
            baseline.replace(
                "__AJ_DMESG_END__",
                "smp: Brought up 1 node, 8 CPUs\r\n__AJ_DMESG_END__",
                1,
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
    ]
    for label, mutation, expected_hash, synthetic_override in mutations:
        try:
            expect_rejected(
                validator, mutation, expected_hash, synthetic_override
            )
        except ValueError as exc:
            raise ValueError(f"mutation passed: {label}") from exc

    print("validation=candidate-aj-usb-cpu-runtime-subgate-mutations")
    print("positive_fixture=passed")
    print("production_pinned_gate=accepted-exact-padded-hash")
    print("transport=crlf-with-15-inherited-marker-occurrences")
    print(f"mutations_rejected={len(mutations)}")
    print("cpu8_gate_and_minus11=exact-one-each")
    print("cpu9_attempt_and_a72_boot=rejected")
    print("candidate_aj_source_pin=mutation-rejected")
    print("overall_candidate_pass=requires-four-separate-evidence-gates")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
