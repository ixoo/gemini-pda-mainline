#!/usr/bin/env python3
"""Storage-inert structured mutations for AP's native reboot validator."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import pathlib
import sys
from types import SimpleNamespace


sys.dont_write_bytecode = True

AP_PADDED = (
    "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
)
AO_PADDED = "2" * 64
CONFIG = "3" * 64
LIVE_FDT = "4" * 64
BOOT_ID = "01234567-89ab-4def-8123-456789abcdef"
RUNTIME_TEXT = (
    "__AP_HOST_BEGIN__\n"
    "interface=en9\n"
    "route_interface=en9\n"
    "__AP_HOST_END__\n"
    "__AP_IDENTITY_BEGIN__\n"
    f"boot_id={BOOT_ID}\n"
    "__AP_IDENTITY_END__\n"
    "__AP_STATE1_BEGIN__\n"
    "ac_ready_count=1\n"
    "__AP_STATE1_END__\n"
)


def load(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeIdentity:
    PADDED_SHA256 = AP_PADDED
    AO_PADDED_SHA256 = AO_PADDED
    CONFIG_SHA256 = CONFIG

    @staticmethod
    def require_artifact_pins() -> None:
        return None


class FakeRuntime:
    @staticmethod
    def normalize_capture(text: str) -> str:
        return text.replace("\r", "")

    @staticmethod
    def validate_structure(text: str) -> None:
        for name in ("HOST", "IDENTITY"):
            if (
                text.count(f"__AP_{name}_BEGIN__") != 1
                or text.count(f"__AP_{name}_END__") != 1
            ):
                raise ValueError("runtime fixture structure changed")

    @staticmethod
    def section(text: str, name: str) -> str:
        begin = f"__AP_{name}_BEGIN__\n"
        end = f"\n__AP_{name}_END__"
        return text.split(begin, 1)[1].split(end, 1)[0]

    @staticmethod
    def key_values(text: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in text.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key in values:
                raise ValueError("runtime fixture key/value changed")
            values[key] = value
        return values

    @staticmethod
    def validate(
        text: str,
        installed: str,
        config: str,
        live_fdt: str,
        boot_id: str,
    ) -> SimpleNamespace:
        if (
            text != RUNTIME_TEXT
            or installed != AP_PADDED
            or config != CONFIG
            or live_fdt != LIVE_FDT
            or boot_id != BOOT_ID
        ):
            raise ValueError("runtime fixture binding changed")
        return SimpleNamespace(outcome="PASS", boot_id=BOOT_ID)


class FakeLiveFdt:
    EXPECTED_LIVE_FDT_SHA256 = LIVE_FDT
    EXPECTED_LIVE_FDT_SIZE = "4096"


def dependencies(native: object) -> object:
    return native.Dependencies(
        identity=FakeIdentity,
        runtime=FakeRuntime,
        live_fdt=FakeLiveFdt,
        identity_sha256="a" * 64,
        runtime_sha256="b" * 64,
        live_fdt_sha256="c" * 64,
        collector_path=None,
    )


def fixture(native: object, selected: object) -> str:
    runtime_sha = hashlib.sha256(RUNTIME_TEXT.encode()).hexdigest()
    return "".join(
        (
            "__AP_NATIVE_HOST_BEGIN__\n",
            f"installed_full_sha256_input={AP_PADDED}\n",
            "attestation_basis=caller-supplied-prior-full-partition-readback\n",
            "installed_full_hash_reverified_during_request=no\n",
            "device_partition_read_during_request=no\n",
            f"runtime_capture_sha256={runtime_sha}\n",
            "runtime_validation=candidate-ap-mt6797-dvfsp-i2c6-consumer-runtime\n",
            "runtime_outcome=PASS\n",
            f"runtime_boot_id={BOOT_ID}\n",
            f"candidate_identity_source_sha256={selected.identity_sha256}\n",
            f"runtime_validator_source_sha256={selected.runtime_sha256}\n",
            f"live_fdt_validator_source_sha256={selected.live_fdt_sha256}\n",
            f"live_fdt_sha256={LIVE_FDT}\n",
            "live_fdt_size=4096\n",
            "native_runtime_preflight=candidate-ap-native-reboot-preflight\n",
            "direct_usb_binding=yes\n",
            "interface=en9\n",
            "mac=42:00:15:19:82:00\n",
            "host_address=10.15.19.1/24\n",
            "route_interface=en9\n",
            "device_endpoint=10.15.19.82:2323\n",
            "storage_access=none\n",
            "watchdog_access=none\n",
            "i2c_access=none\n",
            "regulator_access=none\n",
            "cpu_control_access=none\n",
            "power_state_access=none\n",
            "__AP_NATIVE_HOST_END__\n",
            f"{native.USB_BANNER}\n",
            *(f"{line}\n" for line in native.EXPECTED_USB_PRELUDE),
            "GEMINI-AC-USB# __AP_NATIVE_REQUEST_BEGIN__\n",
            f"GEMINI-AC-USB# candidate_boot_id={BOOT_ID}\n",
            f"GEMINI-AC-USB# live_boot_id={BOOT_ID}\n",
            f"GEMINI-AC-USB# reboot_sha256={native.REBOOT_SHA256}\n",
            "GEMINI-AC-USB# reboot_dispatch=/bin/reboot\n",
            "GEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n",
            "GEMINI-AC-USB# > > > request_authorized=yes\n",
            "GEMINI-AC-USB# storage_access=none\n",
            "GEMINI-AC-USB# device_partition_reads=none\n",
            "GEMINI-AC-USB# watchdog_access=none\n",
            "GEMINI-AC-USB# i2c_access=none\n",
            "GEMINI-AC-USB# regulator_access=none\n",
            "GEMINI-AC-USB# cpu_control_access=none\n",
            "GEMINI-AC-USB# power_state_access=none\n",
            "GEMINI-AC-USB# sync_requested=no\n",
            "GEMINI-AC-USB# request_count=1\n",
            "GEMINI-AC-USB# __AP_NATIVE_REQUEST_END__\n",
            f"GEMINI-AC-USB# > > GEMINI-AC-USB# {native.WRAPPER_LINE}\n",
            "__AP_NATIVE_RESULT_BEGIN__\n",
            "nc_exit_status=0\n",
            "connection_closed_after_request=yes\n",
            "return_marker_observed=no\n",
            "mac_absence_observation_1=absent\n",
            "mac_absence_observation_2=absent\n",
            "disconnect_confirmed=yes\n",
            "requestor_reboot_command_issued=yes\n",
            "device_partition_reads=none\n",
            "device_write_operations=none\n",
            "watchdog_access=none\n",
            "i2c_access=none\n",
            "regulator_access=none\n",
            "cpu_control_access=none\n",
            "power_state_access=none\n",
            "__AP_NATIVE_RESULT_END__\n",
        )
    )


def with_prelude(native: object, text: str, prelude: list[str]) -> str:
    banner = native.USB_BANNER + "\n"
    request = "GEMINI-AC-USB# __AP_NATIVE_REQUEST_BEGIN__\n"
    start = text.index(banner) + len(banner)
    finish = text.index(request, start)
    return text[:start] + "".join(f"{line}\n" for line in prelude) + text[finish:]


def swap_lines(text: str, first: str, second: str) -> str:
    token = "__AP_NATIVE_SWAP_SENTINEL__\n"
    if text.count(first) != 1 or text.count(second) != 1 or token in text:
        raise ValueError("mutation fixture line is not unique")
    return text.replace(first, token).replace(second, first).replace(token, second)


def rejected(
    native: object,
    text: str,
    selected: object,
    runtime_text: str = RUNTIME_TEXT,
    expected_outcome: str = "PASS",
) -> None:
    try:
        native.validate(
            text,
            runtime_text,
            AP_PADDED,
            expected_outcome,
            dependencies=selected,
        )
    except (
        AttributeError,
        KeyError,
        OSError,
        OverflowError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        return
    raise ValueError("native reboot mutation unexpectedly passed")


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    native = load(
        script_dir / "validate-native-reboot.py",
        "candidate_ap_native_reboot_test_validator",
    )
    selected = dependencies(native)
    text = fixture(native, selected)
    binding = native.validate(
        text,
        RUNTIME_TEXT,
        AP_PADDED,
        "PASS",
        dependencies=selected,
    )
    if (
        binding.boot_id != BOOT_ID
        or binding.live_fdt_sha256 != LIVE_FDT
        or binding.interface != "en9"
    ):
        raise ValueError("valid native reboot fixture lost its exact binding")

    class FailedRuntime(FakeRuntime):
        @staticmethod
        def validate(
            text: str,
            installed: str,
            config: str,
            live_fdt: str,
            boot_id: str,
        ) -> SimpleNamespace:
            FakeRuntime.validate(text, installed, config, live_fdt, boot_id)
            return SimpleNamespace(outcome="FAIL", boot_id=BOOT_ID)

    failed = dataclasses.replace(selected, runtime=FailedRuntime)
    failed_text = text.replace("runtime_outcome=PASS", "runtime_outcome=FAIL", 1)
    failed_binding = native.validate(
        failed_text,
        RUNTIME_TEXT,
        AP_PADDED,
        "FAIL",
        dependencies=failed,
    )
    if failed_binding.outcome != "FAIL":
        raise ValueError("exact fail-closed runtime was not rebound for recovery")
    rejected(native, failed_text, failed, expected_outcome="PASS")

    prelude = list(native.EXPECTED_USB_PRELUDE)
    if (
        len(prelude) != 17
        or sum("usb_shell=session-entry" in line for line in prelude) != 2
        or sum("usb_shell=ready" in line for line in prelude) != 2
    ):
        raise ValueError("inherited USB prelude cardinality changed")
    reordered_prelude = prelude.copy()
    reordered_prelude[4], reordered_prelude[5] = (
        reordered_prelude[5],
        reordered_prelude[4],
    )
    storage_prelude = prelude.copy()
    storage_prelude[3] = storage_prelude[3].replace(
        "storage_access=none", "storage_access=boot2"
    )
    security_prelude = prelude.copy()
    security_prelude[9] = security_prelude[9].replace(
        "authentication=none", "authentication=password"
    )
    busybox_prelude = prelude.copy()
    busybox_prelude[14] = busybox_prelude[14].replace("v1.36.1", "v1.36.2")

    mutations = (
        text.replace(
            f"live_boot_id={BOOT_ID}",
            "live_boot_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            1,
        ),
        text.replace(native.REBOOT_SHA256, "0" * 64, 1),
        text.replace("request_authorized=yes", "request_authorized=no", 1),
        text.replace("request_count=1", "request_count=2", 1),
        text.replace(
            "connection_closed_after_request=yes",
            "connection_closed_after_request=no",
            1,
        ),
        text.replace("return_marker_observed=no", "return_marker_observed=yes", 1),
        text.replace(
            "__AP_NATIVE_RESULT_BEGIN__",
            "__AP_NATIVE_REBOOT_RETURNED__\n__AP_NATIVE_RESULT_BEGIN__",
            1,
        ),
        text.replace(
            "mac_absence_observation_2=absent",
            "mac_absence_observation_2=present",
            1,
        ),
        text.replace("runtime_capture_sha256=", "runtime_capture_sha256=0", 1),
        text.replace(f"runtime_boot_id={BOOT_ID}", "runtime_boot_id=bad", 1),
        text.replace(f"live_fdt_sha256={LIVE_FDT}", "live_fdt_sha256=" + "5" * 64, 1),
        text.replace("live_fdt_size=4096", "live_fdt_size=4097", 1),
        text.replace(
            "runtime_validator_source_sha256=" + "b" * 64,
            "runtime_validator_source_sha256=" + "0" * 64,
            1,
        ),
        text.replace("direct_usb_binding=yes", "direct_usb_binding=no", 1),
        text.replace("route_interface=en9", "route_interface=en8", 1),
        text.replace("device_partition_reads=none", "device_partition_reads=boot2", 1),
        text.replace("watchdog_access=none", "watchdog_access=opened", 1),
        text.replace("i2c_access=none", "i2c_access=transfer", 1),
        text.replace("regulator_access=none", "regulator_access=read", 1),
        text.replace("cpu_control_access=none", "cpu_control_access=online", 1),
        text.replace("power_state_access=none", "power_state_access=suspend", 1),
        text.replace(native.WRAPPER_LINE + "\n", "", 1),
        swap_lines(
            text,
            "runtime_outcome=PASS\n",
            f"runtime_boot_id={BOOT_ID}\n",
        ),
        swap_lines(
            text,
            "GEMINI-AC-USB# storage_access=none\n",
            "GEMINI-AC-USB# device_partition_reads=none\n",
        ),
        swap_lines(
            text,
            "connection_closed_after_request=yes\n",
            "return_marker_observed=no\n",
        ),
        "unexpected-envelope-line\n" + text,
        text + "unexpected-envelope-line\n",
        text.replace(
            "__AP_NATIVE_HOST_END__\n",
            "__AP_NATIVE_HOST_END__\ndevice_write_operations=boot2\n",
            1,
        ),
        text.replace(
            native.WRAPPER_LINE + "\n",
            native.WRAPPER_LINE + "\ndevice_write_operations=boot2\n",
            1,
        ),
        with_prelude(
            native,
            text,
            [*prelude[:1], "unexpected inherited chatter", *prelude[1:]],
        ),
        with_prelude(native, text, reordered_prelude),
        with_prelude(native, text, prelude[:10] + prelude[12:]),
        with_prelude(native, text, storage_prelude),
        with_prelude(native, text, security_prelude),
        with_prelude(native, text, busybox_prelude),
    )
    for mutation in mutations:
        rejected(native, mutation, selected)
    rejected(native, text, selected, RUNTIME_TEXT + "mutated=yes\n")

    bad_sources = dataclasses.replace(selected, runtime_sha256="unresolved")
    rejected(native, text, bad_sources)

    class InconclusiveRuntime(FakeRuntime):
        @staticmethod
        def validate(*_args: object) -> SimpleNamespace:
            return SimpleNamespace(outcome="INCONCLUSIVE", boot_id=BOOT_ID)

    inconclusive = dataclasses.replace(selected, runtime=InconclusiveRuntime)
    rejected(native, text, inconclusive)

    class UnpinnedLiveFdt:
        EXPECTED_LIVE_FDT_SHA256 = "TO_PIN_PRIVATE_LIVE_FDT_SHA256"
        EXPECTED_LIVE_FDT_SIZE = "TO_PIN_PRIVATE_LIVE_FDT_SIZE"

    unpinned_live = dataclasses.replace(selected, live_fdt=UnpinnedLiveFdt)
    rejected(native, text, unpinned_live)

    production_values = (
        native.CANDIDATE_AP_SHA256,
        native.RUNTIME_VALIDATOR_SHA256,
        native.LIVE_FDT_VALIDATOR_SHA256,
    )
    resolved = tuple(
        native.HEX256.fullmatch(value) is not None
        for value in production_values
    )
    if resolved == (False, False, False):
        production_pins = "unresolved"
    elif resolved == (True, True, True):
        production_pins = "calibrated"
        expected_sources = (
            script_dir / "candidate_ap.py",
            script_dir / "validate-runtime.py",
            script_dir / "validate-live-fdt-delta.py",
        )
        actual = tuple(
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in expected_sources
        )
        if production_values != actual:
            raise ValueError("calibrated production source pin changed")
    else:
        raise ValueError("production source pins are partially calibrated")
    try:
        native.validate(text, RUNTIME_TEXT, AP_PADDED, "PASS")
    except ValueError as exc:
        if production_pins == "unresolved" and "unresolved" not in str(exc):
            raise
    else:
        raise ValueError("synthetic fixture passed production dependencies")

    print("validation=candidate-ap-native-reboot-structured-mutations")
    print("exact_runtime_boot_id_and_live_fdt_binding=passed")
    print("exact_reboot_wrapper_hash_and_dispatch=passed")
    print(f"mutations_rejected={len(mutations) + 5}")
    print("pass_and_fail_closed_runtime_outcomes=explicitly_bound")
    print(f"production_source_pins={production_pins}")
    print("synthetic_fixture_passed_production_dependencies=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
