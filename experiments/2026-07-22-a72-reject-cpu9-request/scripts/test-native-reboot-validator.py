#!/usr/bin/env python3
"""Storage-inert mutation tests for AK's native reboot validator."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys

sys.dont_write_bytecode = True

PADDED = "1" * 64
AJ_PADDED = "2" * 64
BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
RUNTIME_TEXT = f"fixture=candidate-ak-runtime\nboot_id={BOOT_ID}\n"


def load(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeAk:
    PADDED_SHA256 = PADDED
    AJ_PADDED_SHA256 = AJ_PADDED

    @staticmethod
    def require_artifact_pins() -> None:
        return None


class FakeRuntime:
    @staticmethod
    def validate(text: str, expected_hash: str) -> None:
        if text != RUNTIME_TEXT or expected_hash != PADDED:
            raise ValueError("runtime fixture changed")

    @staticmethod
    def section(text: str, name: str) -> str:
        if text != RUNTIME_TEXT or name != "IDENTITY":
            raise ValueError("runtime identity fixture changed")
        return f"boot_id={BOOT_ID}"

    @staticmethod
    def key_values(text: str, label: str) -> dict[str, str]:
        if text != f"boot_id={BOOT_ID}" or label != "runtime identity":
            raise ValueError("runtime identity parsing changed")
        return {"boot_id": BOOT_ID}


def fixture(native: object) -> str:
    runtime_sha = hashlib.sha256(RUNTIME_TEXT.encode()).hexdigest()
    return "".join(
        (
            "__AK_NATIVE_HOST_BEGIN__\n",
            f"installed_full_sha256_input={PADDED}\n",
            "attestation_basis=caller-supplied-prior-full-partition-readback\n",
            "installed_full_hash_reverified_during_request=no\n",
            "device_partition_read_during_request=no\n",
            f"runtime_capture_sha256={runtime_sha}\n",
            "runtime_validation=candidate-ak-usb-cpu-runtime-subgate\n",
            "native_runtime_preflight=candidate-ak-native-reboot-preflight\n",
            "interface=en9\n",
            "mac=42:00:15:19:82:00\n",
            "host_address=10.15.19.1/24\n",
            "route_interface=en9\n",
            "device_endpoint=10.15.19.82:2323\n",
            "storage_access=none\n",
            "__AK_NATIVE_HOST_END__\n",
            "GEMINI_USB_GADGET_ETHERNET_20260721_AC\n",
            *(f"{line}\n" for line in native.EXPECTED_USB_PRELUDE),
            "GEMINI-AC-USB# __AK_NATIVE_REQUEST_BEGIN__\n",
            f"GEMINI-AC-USB# candidate_boot_id={BOOT_ID}\n",
            f"GEMINI-AC-USB# live_boot_id={BOOT_ID}\n",
            f"GEMINI-AC-USB# reboot_sha256={native.REBOOT_SHA256}\n",
            "GEMINI-AC-USB# reboot_dispatch=/bin/reboot\n",
            "GEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n",
            "GEMINI-AC-USB# > > > > request_authorized=yes\n",
            "GEMINI-AC-USB# storage_access=none\n",
            "GEMINI-AC-USB# sync_requested=no\n",
            "GEMINI-AC-USB# watchdog_userspace=none\n",
            "GEMINI-AC-USB# request_count=1\n",
            "GEMINI-AC-USB# __AK_NATIVE_REQUEST_END__\n",
            f"GEMINI-AC-USB# > > GEMINI-AC-USB# {native.WRAPPER_LINE}\n",
            "__AK_NATIVE_RESULT_BEGIN__\n",
            "nc_exit_status=0\n",
            "connection_closed_after_request=yes\n",
            "mac_absence_observation_1=absent\n",
            "mac_absence_observation_2=absent\n",
            "disconnect_confirmed=yes\n",
            "requestor_reboot_command_issued=yes\n",
            "device_partition_reads=none\n",
            "device_write_operations=none\n",
            "__AK_NATIVE_RESULT_END__\n",
        )
    )


def with_prelude(native: object, text: str, prelude: list[str]) -> str:
    banner = native.USB_BANNER + "\n"
    request = "GEMINI-AC-USB# __AK_NATIVE_REQUEST_BEGIN__\n"
    start = text.index(banner) + len(banner)
    finish = text.index(request, start)
    return text[:start] + "".join(f"{line}\n" for line in prelude) + text[finish:]


def rejected(native: object, text: str, runtime_text: str = RUNTIME_TEXT) -> None:
    try:
        native.validate(
            text,
            runtime_text,
            PADDED,
            dependencies=(FakeAk, FakeRuntime),
        )
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
        return
    raise ValueError("native reboot mutation unexpectedly passed")


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    native = load(script_dir / "validate-native-reboot.py", "ak_native_test_validator")
    text = fixture(native)
    result = native.validate(
        text,
        RUNTIME_TEXT,
        PADDED,
        dependencies=(FakeAk, FakeRuntime),
    )
    if result != BOOT_ID:
        raise ValueError("valid native reboot fixture lost its boot ID")

    prelude = list(native.EXPECTED_USB_PRELUDE)
    if len(prelude) != 17:
        raise ValueError("inherited USB prelude cardinality changed")
    if sum("usb_shell=session-entry" in line for line in prelude) != 2:
        raise ValueError("inherited session-entry cardinality changed")
    if sum("usb_shell=ready" in line for line in prelude) != 2:
        raise ValueError("inherited session-ready cardinality changed")
    reordered_prelude = prelude.copy()
    reordered_prelude[4], reordered_prelude[5] = (
        reordered_prelude[5],
        reordered_prelude[4],
    )
    policy_prelude = prelude.copy()
    policy_prelude[3] = policy_prelude[3].replace(
        "storage_access=none", "storage_access=boot2"
    )
    port_prelude = prelude.copy()
    port_prelude[7] = port_prelude[7].replace("port=2323", "port=22")
    security_prelude = prelude.copy()
    security_prelude[9] = security_prelude[9].replace(
        "authentication=none", "authentication=password"
    )
    busybox_prelude = prelude.copy()
    busybox_prelude[14] = busybox_prelude[14].replace(
        "v1.36.1", "v1.36.2"
    )
    blank_prelude = prelude.copy()
    del blank_prelude[12]

    mutations = (
        text.replace(
            f"live_boot_id={BOOT_ID}",
            "live_boot_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            1,
        ),
        text.replace(native.REBOOT_SHA256, "0" * 64, 1),
        text.replace("request_authorized=yes", "request_authorized=no", 1),
        text.replace("request_count=1", "request_count=2", 1),
        text.replace("disconnect_confirmed=yes", "disconnect_confirmed=no", 1),
        text.replace(native.WRAPPER_LINE + "\n", "", 1),
        text.replace(
            "__AK_NATIVE_RESULT_BEGIN__",
            "__AK_NATIVE_REBOOT_RETURNED__\n__AK_NATIVE_RESULT_BEGIN__",
            1,
        ),
        text.replace(
            "mac_absence_observation_2=absent",
            "mac_absence_observation_2=present",
            1,
        ),
        text.replace("runtime_capture_sha256=", "runtime_capture_sha256=0", 1),
        text.replace(
            "device_partition_reads=none", "device_partition_reads=boot2", 1
        ),
        text.replace(
            "> > > > request_authorized=yes",
            "> > > > injected request_authorized=yes",
            1,
        ),
        text.replace(
            "> > > > request_authorized=yes",
            "> > > > request_authorized=> yes",
            1,
        ),
        (
            text.split("__AK_NATIVE_HOST_BEGIN__\n", 1)[0]
            + text.split("__AK_NATIVE_HOST_END__\n", 1)[1]
            + "__AK_NATIVE_HOST_BEGIN__\n"
            + text.split("__AK_NATIVE_HOST_BEGIN__\n", 1)[1].split(
                "__AK_NATIVE_HOST_END__\n", 1
            )[0]
            + "__AK_NATIVE_HOST_END__\n"
        ),
        "unexpected-envelope-line\n" + text,
        text + "unexpected-envelope-line\n",
        text.replace(
            "__AK_NATIVE_HOST_END__\n",
            "__AK_NATIVE_HOST_END__\ndevice_write_operations=boot2\n",
            1,
        ),
        text.replace(
            "GEMINI_USB_GADGET_ETHERNET_20260721_AC\n",
            "GEMINI_USB_GADGET_ETHERNET_20260721_AC\n"
            "device_write_operations=boot2\n",
            1,
        ),
        text.replace(
            "GEMINI-AC-USB# __AK_NATIVE_REQUEST_END__\n",
            "GEMINI-AC-USB# __AK_NATIVE_REQUEST_END__\n"
            "device_write_operations=boot2\n",
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
        with_prelude(native, text, prelude[:10] + prelude[8:10] + prelude[10:]),
        with_prelude(native, text, policy_prelude),
        with_prelude(native, text, port_prelude),
        with_prelude(native, text, security_prelude),
        with_prelude(native, text, busybox_prelude),
        with_prelude(native, text, blank_prelude),
    )
    for mutation in mutations:
        rejected(native, mutation)
    rejected(native, text, RUNTIME_TEXT + "mutated=yes\n")

    # This synthetic fixture must never pass through production dependencies.
    # Before calibration it is rejected by unresolved source pins; after
    # calibration the exact production runtime validator rejects the fixture.
    unresolved = (
        native.HEX256.fullmatch(native.CANDIDATE_AK_SHA256) is None
        or native.HEX256.fullmatch(native.RUNTIME_VALIDATOR_SHA256) is None
    )
    try:
        native.validate(text, RUNTIME_TEXT, PADDED)
    except ValueError as exc:
        if unresolved and "unresolved" not in str(exc):
            raise
    else:
        raise ValueError("synthetic fixture unexpectedly passed production dependencies")

    print("validation=candidate-ak-native-reboot-mutations")
    print("fresh_runtime_boot_id_gate=passed")
    print("exact_reboot_wrapper_hash_and_dispatch=passed")
    print(f"mutations_rejected={len(mutations) + 1}")
    print(f"unresolved_production_pins={str(unresolved).lower()}")
    print("synthetic_fixture_passed_production_dependencies=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
