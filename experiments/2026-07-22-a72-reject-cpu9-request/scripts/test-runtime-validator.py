#!/usr/bin/env python3
"""Exercise Candidate AK's live USB/CPU runtime mutation boundaries."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


TEST_INSTALLED_SHA256 = "a1" * 32


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
            f"[    2.020000] {validator.EXPECTED_CPU9_GATE}\n",
            f"<4>[    2.030000] {validator.EXPECTED_CPU9_FAILURE}\n",
            f"{validator.EXPECTED_SMP_COMPLETION}\n",
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
        f"__AK_HOST_BEGIN__\n{host_text}__AK_HOST_END__\n"
        f"{validator.EXPECTED_USB_MARKER}\n"
        f"{status_lines}"
        f"{validator.EXPECTED_USB_PROMPT}__AK_IDENTITY_BEGIN__\n"
        f"{identity_text}{validator.EXPECTED_USB_PROMPT}__AK_IDENTITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AK_STAT1_BEGIN__\n{first}__AK_STAT1_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AK_STAT2_BEGIN__\n{second}__AK_STAT2_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AK_STABILITY_BEGIN__\n"
        f"{stability_text}{validator.EXPECTED_USB_PROMPT}__AK_STABILITY_END__\n"
        f"{validator.EXPECTED_USB_PROMPT}__AK_DMESG_BEGIN__\n"
        f"{''.join(dmesg)}__AK_DMESG_END__\n"
    )
    return text.replace("\n", "\r\n")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"test mutation source is not unique: {old!r}")
    return text.replace(old, new, 1)


def swap_once(text: str, first: str, second: str) -> str:
    placeholder = "__CANDIDATE_AK_RUNTIME_SWAP_PLACEHOLDER__"
    if placeholder in text:
        raise ValueError("test swap placeholder collides with fixture")
    return replace_once(
        replace_once(replace_once(text, first, placeholder), second, first),
        placeholder,
        second,
    )


def append_dmesg(text: str, line: str) -> str:
    return replace_once(text, "__AK_DMESG_END__", f"{line}\r\n__AK_DMESG_END__")


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


def assert_production_pin_gate(
    validator: object, baseline: str, script_dir: pathlib.Path
) -> None:
    validator.AK.require_artifact_pins()
    if validator.AK.PADDED_SHA256 == TEST_INSTALLED_SHA256:
        raise ValueError("synthetic identity collapsed to production Candidate AK")

    # Imported validation without the explicit synthetic override must also
    # stop before accepting the fixture.
    expect_rejected(validator, baseline, synthetic_override=None)

    # The CLI rejects a non-AK installed identity before reading its capture
    # path, even after all production identities are calibrated.
    with tempfile.TemporaryDirectory(prefix="candidate-ak-runtime-failclosed-") as raw:
        missing_capture = pathlib.Path(raw) / "must-not-be-read.txt"
        process = subprocess.run(
            [
                sys.executable,
                str(script_dir / "validate-runtime.py"),
                "--capture",
                str(missing_capture),
                "--expected-installed-full-sha256",
                TEST_INSTALLED_SHA256,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 2 or "is not Candidate AK" not in process.stderr:
            raise ValueError("production validator did not fail closed on wrong identity")
        if "No such file" in process.stderr:
            raise ValueError("production validator read the capture before pin rejection")


def assert_collector_static(script_dir: pathlib.Path) -> None:
    collector = script_dir / "collect-runtime.sh"
    source = collector.read_text(encoding="utf-8")
    process = subprocess.run(
        ["bash", "-n", str(collector)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        raise ValueError(f"AK runtime collector shell syntax failed: {process.stderr}")
    required = (
        "module.require_artifact_pins()",
        "device_partition_read_during_collection=no",
        "online_control_state",
        "/proc/stat",
        "/bin/busybox dmesg",
        "nc -4 -b",
        "--expected-installed-full-sha256",
    )
    for marker in required:
        if marker not in source:
            raise ValueError(f"AK runtime collector lacks fail-closed marker: {marker}")
    forbidden = (
        "/dev/mmc",
        "blockdev",
        "reboot",
        "poweroff",
        "shutdown",
        "kexec",
        "flash",
        "cpu8/online\" >",
        "cpu9/online\" >",
    )
    for marker in forbidden:
        if marker in source:
            raise ValueError(f"AK runtime collector contains forbidden action: {marker}")
    with tempfile.TemporaryDirectory(prefix="candidate-ak-collector-failclosed-") as raw:
        output = pathlib.Path(raw) / "runtime.txt"
        process = subprocess.run(
            [
                "bash",
                str(collector),
                "--interface",
                "en7",
                "--output",
                str(output),
                "--installed-full-sha256",
                TEST_INSTALLED_SHA256,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 2 or "is not Candidate AK" not in process.stderr:
            raise ValueError("production collector did not fail closed on wrong identity")
        if output.exists():
            raise ValueError("production collector created output before pin rejection")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    validator = load_module(
        script_dir / "validate-runtime.py",
        "gemini_ak_runtime_tests",
    )
    with tempfile.TemporaryDirectory(prefix="candidate-ak-runtime-source-pin-") as raw:
        temporary = pathlib.Path(raw)
        validator_source = pathlib.Path(validator.__file__).read_bytes()
        candidate_source = (script_dir / "candidate_ak.py").read_bytes()
        (temporary / "validate-runtime.py").write_bytes(validator_source)
        (temporary / "candidate_ak.py").write_bytes(candidate_source + b"\n")
        try:
            load_module(temporary / "validate-runtime.py", "gemini_ak_runtime_bad_source")
        except ValueError as exc:
            if "identity module source changed" not in str(exc):
                raise
        else:
            raise ValueError("mutated Candidate AK identity module was accepted")

    if validator.VALIDATION_LABEL != "candidate-ak-usb-cpu-runtime-subgate":
        raise ValueError("runtime subgate label changed")
    if validator.SEPARATE_OVERALL_GATES != (
        "visible-console",
        "native-reboot-cycle",
        "recovery-attribution",
        "post-cycle-boot2-integrity",
    ):
        raise ValueError("independent overall evidence gates changed")
    validator.AK.require_artifact_pins()

    baseline = fixture(validator)
    if baseline.count(validator.EXPECTED_USB_MARKER) != 15:
        raise ValueError("realistic inherited USB marker fixture cardinality changed")
    validator.validate(
        baseline,
        TEST_INSTALLED_SHA256,
        synthetic_installed_full_sha256_override=TEST_INSTALLED_SHA256,
    )
    assert_production_pin_gate(validator, baseline, script_dir)
    assert_collector_static(script_dir)

    cpu8_gate = validator.EXPECTED_CPU8_GATE
    cpu8_failure = validator.EXPECTED_CPU8_FAILURE
    cpu9_gate = validator.EXPECTED_CPU9_GATE
    cpu9_failure = validator.EXPECTED_CPU9_FAILURE
    mutations = [
        ("wrong-caller-hash", baseline, "b2" * 32, TEST_INSTALLED_SHA256),
        ("malformed-caller-hash", baseline, "A" * 64, TEST_INSTALLED_SHA256),
        ("malformed-synthetic-override", baseline, TEST_INSTALLED_SHA256, "B" * 64),
        (
            "host-hash",
            replace_once(baseline, TEST_INSTALLED_SHA256, "b2" * 32),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "host-mac",
            replace_once(
                baseline,
                f"mac={validator.EXPECTED_HOST_MAC}",
                "mac=42:00:15:19:82:99",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "host-address",
            replace_once(baseline, validator.EXPECTED_HOST_ADDRESS, "10.15.19.2/24"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "device-endpoint",
            replace_once(baseline, validator.EXPECTED_DEVICE_ENDPOINT, "10.15.19.82:2324"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "route-interface",
            replace_once(baseline, "route_interface=en7", "route_interface=en8"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "partition-read",
            replace_once(
                baseline,
                "device_partition_read_during_collection=no",
                "device_partition_read_during_collection=yes",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-banner",
            replace_once(
                baseline,
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER} not-a-banner\r\n",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-banner",
            replace_once(
                baseline,
                f"{validator.EXPECTED_USB_MARKER}\r\n",
                f"{validator.EXPECTED_USB_MARKER}\r\n"
                f"{validator.EXPECTED_USB_MARKER}\r\n",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "config",
            replace_once(baseline, validator.EXPECTED_CONFIG_SHA256, "0" * 64),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "maxcpus-nine",
            replace_once(baseline, "maxcpus=10", "maxcpus=9"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "possible-mask",
            replace_once(baseline, "possible=0-9", "possible=0-8"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "present-mask",
            replace_once(baseline, "present=0-9", "present=0-8"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "online-mask",
            replace_once(baseline, "online=0-7", "online=0-8"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "offline-mask",
            replace_once(baseline, "offline=8-9", "offline=9"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "nproc",
            replace_once(baseline, "nproc=8", "nproc=9"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-enable-method",
            replace_once(
                baseline,
                "cpu8_enable_method=mediatek,mt6797-psci",
                "cpu8_enable_method=psci",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-enable-method",
            replace_once(
                baseline,
                "cpu9_enable_method=mediatek,mt6797-psci",
                "cpu9_enable_method=psci",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "gate-symbol",
            replace_once(baseline, "boot_gate_symbol_count=1", "boot_gate_symbol_count=0"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-online-control",
            replace_once(baseline, "cpu8_online_control=absent", "cpu8_online_control=present"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-online-control-after",
            replace_once(
                baseline,
                "cpu9_online_control_after=absent",
                "cpu9_online_control_after=present",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "stability-mask",
            replace_once(baseline, "online_after=0-7", "online_after=0-8"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "stalled-accounting",
            replace_once(
                baseline,
                "cpu3 104 2 3 4 5 6 7 8 9 10",
                "cpu3 103 2 3 4 5 6 7 8 9 10",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "extra-cpu-accounting",
            replace_once(
                baseline,
                "__AK_STAT2_END__",
                "cpu8 1 2 3 4 5 6 7 8 9 10\r\n__AK_STAT2_END__",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu8-gate",
            replace_once(baseline, cpu8_gate, ""),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-cpu8-gate",
            append_dmesg(baseline, cpu8_gate),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu8-gate",
            replace_once(
                baseline,
                cpu8_gate,
                "mt6797-psci: CPU8 boot rejected: synthetic wrong reason",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu8-failure",
            replace_once(baseline, cpu8_failure, ""),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu8-errno",
            replace_once(baseline, cpu8_failure, "CPU8: failed to boot: -5"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu9-gate",
            replace_once(baseline, cpu9_gate, ""),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-cpu9-gate",
            append_dmesg(baseline, cpu9_gate),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu9-gate",
            replace_once(
                baseline,
                cpu9_gate,
                "mt6797-psci: CPU9 boot rejected: synthetic wrong reason",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-cpu9-failure",
            replace_once(baseline, cpu9_failure, ""),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-cpu9-failure",
            append_dmesg(baseline, cpu9_failure),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "wrong-cpu9-errno",
            replace_once(baseline, cpu9_failure, "CPU9: failed to boot: -5"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-pair-order",
            swap_once(baseline, cpu8_gate, cpu8_failure),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-before-cpu8",
            swap_once(baseline, cpu8_gate, cpu9_gate),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-pair-order",
            swap_once(baseline, cpu9_gate, cpu9_failure),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "smp-before-rejections",
            swap_once(baseline, cpu9_failure, validator.EXPECTED_SMP_COMPLETION),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-secondary",
            append_dmesg(
                baseline,
                "CPU8: Booted secondary processor 0x0000000200 [0x410fd080]",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-secondary",
            append_dmesg(
                baseline,
                "CPU9: Booted secondary processor 0x0000000201 [0x410fd080]",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-gic",
            append_dmesg(baseline, "GICv3: CPU8: found redistributor"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-psci",
            append_dmesg(baseline, "psci: CPU_ON for CPU9 returned SUCCESS"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "mpidr-psci",
            append_dmesg(baseline, "psci: CPU_ON(0x201) returned SUCCESS"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-started",
            append_dmesg(baseline, "CPU8 started"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu9-reset",
            append_dmesg(baseline, "CPU9 reset deasserted"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "cpu8-fault",
            append_dmesg(baseline, "CPU8 fault synthetic"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "panic",
            append_dmesg(baseline, "Kernel panic - synthetic"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-a53-boot",
            replace_once(
                baseline,
                "CPU4: Booted secondary processor 0x0000000100 [0x410fd034]\r\n",
                "",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "missing-a53-gic",
            replace_once(baseline, "GICv3: CPU6: found redistributor\r\n", ""),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "early-uptime",
            replace_once(baseline, "uptime_before=45.50", "uptime_before=44.99"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "short-window",
            replace_once(baseline, "uptime_after=50.60", "uptime_after=49.99"),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "changed-boot-id",
            replace_once(
                baseline,
                "boot_id_after=01234567-89ab-cdef-0123-456789abcdef",
                "boot_id_after=11234567-89ab-cdef-0123-456789abcdef",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "identity-inventory",
            replace_once(
                baseline,
                "__AK_IDENTITY_END__",
                "unexpected=value\r\n__AK_IDENTITY_END__",
            ),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicated-section",
            baseline
            + "__AK_STABILITY_BEGIN__\r\nuptime_after=51.0\r\n"
            "__AK_STABILITY_END__\r\n",
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
        (
            "duplicate-smp-line",
            append_dmesg(baseline, validator.EXPECTED_SMP_COMPLETION),
            TEST_INSTALLED_SHA256,
            TEST_INSTALLED_SHA256,
        ),
    ]
    for label, mutation, expected_hash, synthetic_override in mutations:
        try:
            expect_rejected(validator, mutation, expected_hash, synthetic_override)
        except ValueError as exc:
            raise ValueError(f"mutation passed: {label}") from exc

    print("validation=candidate-ak-usb-cpu-runtime-subgate-mutations")
    print("positive_fixture=passed")
    print("production_pinned_gate=exact-candidate-ak-before-capture-read")
    print("transport=crlf-with-15-inherited-marker-occurrences")
    print(f"mutations_rejected={len(mutations)}")
    print("cpu8_cpu9_gate_and_minus11=exact-one-each-in-order")
    print("cpu8_cpu9_secondary_gic_psci_fault_reset=rejected")
    print("candidate_ak_source_pin=mutation-rejected")
    print("collector_static_policy=storage-inert")
    print("overall_candidate_pass=requires-four-separate-evidence-gates")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
